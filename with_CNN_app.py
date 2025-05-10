# app.py

import os
import json
import numpy as np
import face_recognition
from flask import Flask, render_template_string, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from functools import wraps

import threading
from PIL import Image  # Pillow library for image manipulations


app = Flask(__name__)
app.secret_key = 'a-very-secret-key'  # Replace with a real secret

CONFIG_FILE = 'config.json'

precompute_lock = threading.Lock()
precompute_progress = {
    'running': False,
    'total': 0,
    'current': 0,
    'message': ''
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        default = {'title': 'Face Search CNN App', 'photo_dir': 'photos', 'encodings_file': 'encodings.json'}
        with open(CONFIG_FILE, 'w') as f:
            json.dump(default, f)
        return default
    with open(CONFIG_FILE) as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f)

config = load_config()

os.makedirs(config['photo_dir'], exist_ok=True)

# Authentication decorator simplified
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'logged_in' not in session:
            flash("Login required", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=="POST":
        if request.form.get('username')=='admin' and request.form.get('password')=='password':
            session['logged_in']=True
            flash("Logged in successfully","success")
            return redirect(url_for('admin'))
        else:
            flash("Invalid credentials","danger")
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash("Logged out","info")
    return redirect(url_for('index'))

@app.route('/')
def index():
    title = config.get('title', 'Face Search CNN App')
    return render_template_string(INDEX_HTML, title=title)

@app.route('/gallery')
def gallery():
    title = config.get('title', 'Face Search CNN App')
    photo_dir = config.get('photo_dir', 'photos')
    matched = session.get('search_results')
    if matched:
        images = matched
        if not images:
            flash("No matches found.", "info")
    else:
        images = []
    return render_template_string(GALLERY_HTML, title=title, images=images, photo_dir=photo_dir)

@app.route('/photos/<filename>')
def photos(filename):
    photo_dir = config.get('photo_dir', 'photos')
    return send_from_directory(photo_dir, filename)

def generate_thumbnail(image_path, thumbnail_path, size=(80,80)):
    try:
        with Image.open(image_path) as img:
            img.thumbnail(size)
            os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)
            img.save(thumbnail_path)
            return True
    except Exception as e:
        print(f"Error generating thumbnail for {image_path}: {e}")
        return False

# Update gallery page to load thumbnails if exist
@app.route('/photos/thumbnails/<filename>')
def photos_thumbnail(filename):
    photo_dir = config.get('photo_dir', 'photos')
    thumbnail_dir = os.path.join(photo_dir, ".thumbnails")
    return send_from_directory(thumbnail_dir, filename)

@app.route('/clear_search')
def clear_search():
    session.pop('search_results', None)
    flash('Cleared search results.', 'success')
    return redirect(url_for('gallery'))

@app.route('/admin', methods=['GET','POST'])
@login_required
def admin():
    error = None
    if request.method == 'POST':
        title = request.form.get('title','').strip()
        photo_dir = request.form.get('photo_dir','').strip()
        if not title or not photo_dir:
            error = "Both fields are required."
        elif not os.path.isdir(photo_dir):
            error = f"Directory does not exist: {photo_dir}"
        else:
            config['title'] = title
            config['photo_dir'] = photo_dir
            save_config(config)
            flash("Configuration updated.", "success")
            return redirect(url_for('admin'))
    return render_template_string(ADMIN_HTML, config=config, error=error)

# # precompute with chunks (CNN)
# def precompute_encodings_with_progress():
#     global precompute_progress
#     with precompute_lock:
#         precompute_progress['running'] = True
#         precompute_progress['total'] = 0
#         precompute_progress['current'] = 0
#         precompute_progress['message'] = 'Starting precomputation...'
#     photo_dir = config.get('photo_dir', 'photos')
#     thumbnail_dir = os.path.join(photo_dir, ".thumbnails")
#     files = [f for f in os.listdir(photo_dir) if f.lower().endswith(('.jpg','.jpeg','.png'))]
#     with precompute_lock:
#         precompute_progress['total'] = len(files)
#         precompute_progress['message'] = 'Processing images...'
#     # Instead of building huge list in memory, yield items or save progressively
#     images = []
#     encodings = []
#     for i, fname in enumerate(files):
#         with precompute_lock:
#             precompute_progress['current'] = i + 1
#             precompute_progress['message'] = f'Processing {fname} ({i+1}/{len(files)})'
#         path = os.path.join(photo_dir, fname)
#         # Load & process image one at a time:
#         image = face_recognition.load_image_file(path)
#         boxes = face_recognition.face_locations(image, model='cnn')
#         if not boxes:
#             print(f"No face found in {fname}, skipping")
#             continue
#         encoding = face_recognition.face_encodings(image, boxes)[0]
#         images.append(fname)
#         encodings.append(encoding.tolist())
#         # Generate thumbnail immediately and save to disk then discard
#         thumbnail_path = os.path.join(thumbnail_dir, fname)
#         if not os.path.exists(thumbnail_path):
#             generate_thumbnail(path, thumbnail_path)
        
#     # Optional: if memory is still high, you can save periodically here and clear lists
#     # Save all encodings at the end
#     encodings_path = config.get('encodings_file','encodings.json')
#     with open(encodings_path, 'w') as f:
#         json.dump({'images': images, 'encodings': encodings}, f)
#     with precompute_lock:
#         precompute_progress['running'] = False
#         precompute_progress['message'] = 'Precomputation completed.'

# # 

# # precompute no chunks
# def precompute_encodings_with_progress():
#     global precompute_progress
#     with precompute_lock:
#         precompute_progress['running'] = True
#         precompute_progress['total'] = 0
#         precompute_progress['current'] = 0
#         precompute_progress['message'] = 'Starting precomputation...'
#     photo_dir = config.get('photo_dir', 'photos')
#     encodings = []
#     images = []
#     thumbnail_dir = os.path.join(photo_dir, ".thumbnails")
#     files = [f for f in os.listdir(photo_dir) if f.lower().endswith(('.jpg','.jpeg','.png'))]
#     with precompute_lock:
#         precompute_progress['total'] = len(files)
#         precompute_progress['message'] = 'Processing images...'
#     for i, fname in enumerate(files):
#         with precompute_lock:
#             precompute_progress['current'] = i + 1
#             precompute_progress['message'] = f'Processing {fname} ({i+1}/{len(files)})'
#         fpath = os.path.join(photo_dir, fname)
#         image = face_recognition.load_image_file(fpath)
#         boxes = face_recognition.face_locations(image, model="cnn")

#         if not boxes:
#             print(f"No face found in {fname}, skipping")
#             continue
#         encoding = face_recognition.face_encodings(image, boxes)[0]
#         images.append(fname)
#         encodings.append(encoding.tolist())
#         # Generate thumbnail
#         thumbnail_path = os.path.join(thumbnail_dir, fname)
#         if not os.path.exists(thumbnail_path):
#             generate_thumbnail(fpath, thumbnail_path)

#     with open(config.get('encodings_file', 'encodings.json'), 'w') as f:
#         json.dump({'images': images, 'encodings': encodings}, f)

#     with precompute_lock:
#         precompute_progress['running'] = False
#         precompute_progress['message'] = 'Precomputation completed.'
# # 

# Endpoint to start precompute asynchronously
@app.route('/admin/precompute')
@login_required
def admin_precompute():
    if precompute_progress['running']:
        flash("Precomputation is already running.", "warning")
        return redirect(url_for('admin'))
    thread = threading.Thread(target=precompute_encodings_with_progress)
    thread.start()
    flash("Started encoding precomputation.", "info")
    return redirect(url_for('admin'))

# API to get current progress
@app.route('/admin/precompute_progress')
@login_required
def precompute_progress_api():
    with precompute_lock:
        return jsonify(precompute_progress)

# # Precompute face encodings from images in photo directory
# def precompute_encodings():
#     images = []
#     encodings = []
#     photo_dir = config.get('photo_dir', 'photos')

#     for fname in os.listdir(photo_dir):
#         fpath = os.path.join(photo_dir, fname)
#         if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
#             continue
#         image = face_recognition.load_image_file(fpath)
#         # Use CNN model for detection
#         boxes = face_recognition.face_locations(image, model="cnn")
#         if not boxes:
#             print(f"No faces found in {fname}")
#             continue
#         # We just take the first detected face encoding (if multiple faces, could be improved)
#         encoding = face_recognition.face_encodings(image, boxes)[0]
#         images.append(fname)
#         encodings.append(encoding.tolist())
#         print(f"Encoded {fname}")

#     # Save as JSON
#     encodings_path = config.get('encodings_file','encodings.json')
#     with open(encodings_path, 'w') as f:
#         json.dump({'images': images, 'encodings': encodings}, f)
#     print("Precomputation complete and saved.")

# Load the saved encodings
def load_encodings():
    encodings_path = config.get('encodings_file','encodings.json')
    if not os.path.exists(encodings_path):
        print("Encodings file not found, please run precompute_encodings() first.")
        return [], []
    with open(encodings_path) as f:
        data = json.load(f)
    images = data.get('images', [])
    encodings = [np.array(e) for e in data.get('encodings',[])]
    return images, encodings

# API endpoint for face search
@app.route('/api/search_face', methods=['POST'])
def search_face():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    img_data = file.read()
    npimg = np.frombuffer(img_data, np.uint8)
    # Decode image + convert to RGB (face_recognition expects RGB)
    import cv2
    img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Detect face locations using CNN
    boxes = face_recognition.face_locations(rgb_img, model="cnn")
    if not boxes:
        return jsonify({'results': [], 'message': 'No faces found'}), 200

    query_encodings = face_recognition.face_encodings(rgb_img, boxes)
    query_encoding = query_encodings[0]  # Take first face only

    stored_images, stored_encodings = load_encodings()
    if not stored_encodings:
        return jsonify({'results': [], 'message': 'No stored encodings found. Run precompute.'}), 500

    # Compute distances and pick best matches
    distances = face_recognition.face_distance(stored_encodings, query_encoding)
    # Sort by ascending distance (lower means closer)
    sorted_idx = np.argsort(distances)
    top_matches = []
    for idx in sorted_idx[:10]:
        top_matches.append({'filename': stored_images[idx], 'distance': float(distances[idx])})

    # Save matched filenames in session for gallery display
    session['search_results'] = [m['filename'] for m in top_matches]

    return jsonify(results=top_matches)

# # Route to run precompute (protected behind admin)
# @app.route('/admin/precompute')
# @login_required
# def admin_precompute():
#     precompute_encodings()
#     flash("Encoding precomputation completed.", "success")
#     return redirect(url_for('admin'))

# --- Templates ---

LOGIN_HTML = """
<!DOCTYPE html>
<html><head><title>Login</title></head>
<body><h2>Admin Login</h2>
{% with messages = get_flashed_messages(with_categories=true) %}
  {% for cat, msg in messages %}
  <div>{{ msg }}</div>
  {% endfor %}
{% endwith %}
<form method="POST">
  <label>Username <input name="username" required></label><br>
  <label>Password <input name="password" type="password" required></label><br>
  <input type="submit" value="Login">
</form>
<a href="{{ url_for('index') }}">Home</a>
</body></html>
"""

ADMIN_HTML = """
<!DOCTYPE html>
<html><head><title>Admin Panel</title></head><body>
<nav>
<a href="{{ url_for('index') }}">Home</a> |
<a href="{{ url_for('gallery') }}">Gallery</a> |
<a href="{{ url_for('logout') }}">Logout</a>
</nav>
<h2>Admin Panel</h2>
{% with messages=get_flashed_messages(with_categories=true) %}
  {% for cat,msg in messages %}
  <div>{{ msg }}</div>
  {% endfor %}
{% endwith %}
{% if error %}
<p style="color:red;">{{ error }}</p>
{% endif %}
<form method="POST">
  <label>Site Title <input name="title" value="{{ config.title }}" required></label><br>
  <label>Photo Directory <input name="photo_dir" value="{{ config.photo_dir }}" required></label><br>
  <button type="submit">Save Config</button>
</form>
<hr>
<a href="{{ url_for('admin_precompute') }}">Run Encoding Precomputation</a>
<div id="progressContainer" style="margin-top:20px; display:none;">
    <p id="progressMsg"></p>
    <progress id="progressBar" value="0" max="100" style="width:100%;"></progress>
</div>
<script>
  let progressContainer = document.getElementById('progressContainer');
  let progressBar = document.getElementById('progressBar');
  let progressMsg = document.getElementById('progressMsg');
  let timer;
  function pollProgress() {
    fetch('/admin/precompute_progress')
      .then(res => res.json())
      .then(data => {
        console.log(data)
        if(data.running){
          progressContainer.style.display = 'block';
          let percent = 0;
          if(data.total > 0){
            percent = Math.round((data.current / data.total) * 100);
          }
          progressBar.value = percent;
          progressMsg.textContent = data.message + ` (${percent}%)`;
          timer = setTimeout(pollProgress, 1000);
        } else {
          progressBar.value = 100;
          progressMsg.textContent = data.message;
          setTimeout(() => { progressContainer.style.display = 'none'; }, 3000);
          clearTimeout(timer);
        }
      }).catch(err => {
        progressMsg.textContent = 'Error fetching progress.';
        clearTimeout(timer);
      });
  }
  // Start polling if "Run Encoding Precomputation" was clicked (flash message)
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for category, msg in messages %}
      {% if 'Started encoding precomputation' in msg %}
        pollProgress();
      {% endif %}
    {% endfor %}
  {% endwith %}
</script>
</body></html>
"""

INDEX_HTML = """
<!DOCTYPE html>
<html><head><title>{{ title }}</title>
<style>
body {display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;margin:0;font-family:sans-serif;background:#f8f9fa;}
#video {border:1px solid #ccc;border-radius:8px;}
button {margin-top:15px;padding:10px 20px;background:#007bff;color:#fff;border:none;border-radius:5px;font-size:16px;cursor:pointer;}
button:disabled {background:#aaa;cursor:not-allowed;}
#loading {margin-top:10px;color:#555;display:none;}

nav {margin-top:30px;}
nav a {margin:0 15px;text-decoration:none;color:#007bff;font-weight:bold;}
</style>
</head>
<body>
<h1>{{ title }}</h1>
<video id="video" autoplay playsinline width="320" height="240"></video>
<button id="captureBtn">Capture & Search Face</button>
<div id="loading">Processing, please wait...</div>
<nav>
  <a href="{{ url_for('gallery') }}">Gallery</a>
  {% if session.logged_in %}
  | <a href="{{ url_for('admin') }}">Admin Panel</a>
  | <a href="{{ url_for('logout') }}">Logout</a>
  {% else %}
  | <a href="{{ url_for('login') }}">Admin Login</a>
  {% endif %}
</nav>
<script>
const video = document.getElementById('video');
const captureBtn = document.getElementById('captureBtn');
const loading = document.getElementById('loading');

navigator.mediaDevices.getUserMedia({ video:true }).then(stream => {
  video.srcObject = stream;
}).catch(() => alert("Cannot access camera."));

captureBtn.onclick = () => {
  loading.style.display = '';
  captureBtn.disabled = true;

  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth || 320;
  canvas.height = video.videoHeight || 240;
  canvas.getContext('2d').drawImage(video,0,0,canvas.width,canvas.height);

  canvas.toBlob(blob => {
    const formData = new FormData();
    formData.append('image', blob, 'capture.png');

    fetch('/api/search_face', {method:'POST', body: formData})
    .then(res => res.json())
    .then(data => {
      loading.style.display = 'none';
      captureBtn.disabled = false;
      if(data.results.length === 0){
        alert(data.message || "No faces recognized.");
      } else {
        window.location.href = '/gallery';
      }
    }).catch(() => {
      loading.style.display = 'none';
      captureBtn.disabled = false;
      alert('Error during face search.');
    });
  }, 'image/png');
};
</script>
</body>
</html>
"""

GALLERY_HTML = """
<!DOCTYPE html>
<html><head><title>{{ title }} - Gallery</title>
<style>
body {font-family:sans-serif; margin:2rem auto; max-width:900px; text-align:center;}
.gallery {display:flex; flex-wrap:wrap; justify-content:center; gap:10px;}
.thumb {width:80px; height:80px; object-fit:cover; border-radius:6px; cursor:pointer; box-shadow:0 0 6px rgba(0,0,0,0.15);}
#modal {display:none; position:fixed; z-index:1000; left:0;top:0;width:100%;height:100%;background: rgba(0,0,0,0.7);}
#modal img {max-width:90%; max-height:80vh; border-radius:8px; margin:5% auto; display:block;}
#modal .close {color:#fff; font-size:2rem; position:absolute; top:20px; right:40px; cursor:pointer; user-select:none;}
nav {margin-bottom:20px;}
nav a {margin:0 10px; color:#007bff; text-decoration:none; font-weight:bold;}
</style>
</head>
<body>
<nav>
  <a href="{{ url_for('index') }}">Home</a>
  {% if session.logged_in %}
  | <a href="{{ url_for('admin') }}">Admin Panel</a>
  | <a href="{{ url_for('logout') }}">Logout</a>
  {% else %}
  | <a href="{{ url_for('login') }}">Admin Login</a>
  {% endif %}
</nav>
<h1>Search Results Gallery</h1>
{% if images %}
<div class="gallery">
  {% for img in images %}
  <img 
    src="{{ url_for('photos_thumbnail', filename=img) }}" 
    onerror="this.onerror=null;this.src='{{ url_for('photos', filename=img) }}';" 
    class="thumb" onclick="openModal(this.src)" alt="{{ img }}">
  {% endfor %}
</div>
{% else %}
<p>No face matches found. <a href="{{ url_for('index') }}">Try again</a>.</p>
{% endif %}
<!-- Modal -->
<div id="modal" onclick="closeModal()">
  <span class="close" onclick="closeModal()">&times;</span>
  <img id="modal-img" src="" alt="">
</div>
<script>
const modal = document.getElementById('modal');
const modalImg = document.getElementById('modal-img');
function openModal(src){
  modal.style.display = 'block';
  modalImg.src = src;
}
function closeModal(){
  modal.style.display = 'none';
  modalImg.src = '';
}
</script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(debug=True)
