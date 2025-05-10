import os
import json
import numpy as np
import face_recognition
from flask import Flask, render_template_string, request, redirect, url_for, session, flash, jsonify, send_from_directory
from flask import session
from functools import wraps
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Change this in production

# Default config file path
CONFIG_FILE = 'config.json'

# Load or initialize config with defaults
def load_config():
    if not os.path.exists(CONFIG_FILE):
        default_config = {'title': 'Face Search App', 'photo_dir': 'uploads'}
        with open(CONFIG_FILE, 'w') as f:
            json.dump(default_config, f)
        return default_config
    else:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

config = load_config()

# Ensure photo directory exists
os.makedirs(config['photo_dir'], exist_ok=True)

# Authentication helpers
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- ROUTES ---

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # VERY simple authentication for demo
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'password':
            session['logged_in'] = True
            flash('Logged in successfully.', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Invalid credentials.', 'danger')
    return render_template_string(LOGIN_HTML)

# Logout route
@app.route('/logout')
@login_required
def logout():
    session.pop('logged_in', None)
    flash('Logged out.', 'success')
    return redirect(url_for('index'))

# Admin page to change title and photo directory
@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    global config
    error = None
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        photo_dir = request.form.get('photo_dir', '').strip()
        if not title or not photo_dir:
            error = 'Both fields are required.'
        else:
            # Validate photo_dir: must exist directory
            if not os.path.isdir(photo_dir):
                error = 'Photo directory does not exist.'
            else:
                config['title'] = title
                config['photo_dir'] = photo_dir
                save_config(config)
                flash('Configuration updated.', 'success')
                return redirect(url_for('admin'))
    return render_template_string(ADMIN_HTML, config=config, error=error)

# Home route — shows camera capture interface
@app.route('/')
def index():
    title = config.get('title', 'Face Search App')
    return render_template_string(INDEX_HTML, title=title)

# Gallery route — display thumbnails with modal zoom
@app.route('/gallery')
def gallery():
    title = config.get('title', 'Face Search App')
    photo_dir = config.get('photo_dir', 'uploads')

    # Get matched images from session if available
    matched = session.get('search_results', None)
    if matched is not None:
        images = matched
        if not images:
            flash("No results found for your search.", "info")
    else:
        images = []  # start empty if no search

    return render_template_string(GALLERY_HTML, title=title, images=images, photo_dir=photo_dir)

# Serve images from configured photo directory
@app.route('/photos/<filename>')
def photos(filename):
    photo_dir = config.get('photo_dir', 'uploads')
    return send_from_directory(photo_dir, filename)

# API endpoint to simulate face search (stub)
@app.route('/api/search_face', methods=['POST'])
def search_face():
    # For real use, implement face detection & search on uploaded image or camera capture
    # Here we simulate a delay and return sample matches
    import time
    time.sleep(2)  # Simulate processing delay

    # Return example similar images - for demo just return all from photo dir as "matches"
    photo_dir = config.get('photo_dir', 'uploads')
    try:
        files = os.listdir(photo_dir)
    except:
        files = []
    images = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]

    # Dummy similarity results
    results = [{'filename': img, 'similarity': round(0.5 + 0.5 * i / max(1,len(images)), 2)} for i, img in enumerate(images[:10])]
    
    # Store filenames of matched images in session
    session['search_results'] = [r['filename'] for r in results]
    
    return jsonify(results=results)

# Upload endpoint for user camera capture (optional)
@app.route('/upload_capture', methods=['POST'])
def upload_capture():
    if 'image' not in request.files:
        return jsonify({'error': 'No image part'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = secure_filename(file.filename)
    photo_dir = config.get('photo_dir', 'uploads')
    path = os.path.join(photo_dir, filename)
    file.save(path)
    return jsonify({'message': 'Image uploaded successfully', 'filename': filename})

@app.route('/clear_search')
def clear_search():
    session.pop('search_results', None)
    flash('Search results cleared.', 'success')
    return redirect(url_for('gallery'))

# --- HTML TEMPLATES ---

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Login - Face Search Admin</title>
    <style>
        body { font-family: Arial, sans-serif; text-align:center; margin-top:50px; }
        form { display: inline-block; text-align:left; }
        .flash { color: red; }
    </style>
</head>
<body>
    <h2>Admin Login</h2>
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% for category, msg in messages %}
            <div class="flash">{{msg}}</div>
        {% endfor %}
    {% endwith %}
    <form method="post">
        <label>Username: <input name="username"></label><br><br>
        <label>Password: <input type="password" name="password"></label><br><br>
        <input type="submit" value="Login">
    </form>
    <a href="{{ url_for('index') }}">Back to Home</a>
</body>
</html>
"""

ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Panel - Face Search</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 2em auto; max-width: 400px; }
        label { display: block; margin: 1em 0 0.5em; }
        input[type=text] { width: 100%; padding: 0.5em; }
        .flash { color: green; }
        .error { color: red; }
        nav { margin-bottom: 1.5em; }
    </style>
</head>
<body>
    <nav>
        <a href="{{ url_for('index') }}">Home</a> | 
        <a href="{{ url_for('gallery') }}">Gallery</a> | 
        <a href="{{ url_for('logout') }}">Logout</a>
    </nav>
    <h2>Admin Panel</h2>
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% for category, msg in messages %}
            <div class="flash">{{ msg }}</div>
        {% endfor %}
    {% endwith %}
    {% if error %}
        <div class="error">{{ error }}</div>
    {% endif %}
    <form method="post">
        <label for="title">Site Title:</label>
        <input id="title" name="title" value="{{ config.title }}" required>
        <label for="photo_dir">Photo Directory:</label>
        <input id="photo_dir" name="photo_dir" value="{{ config.photo_dir }}" required>
        <br><br>
        <button type="submit">Save Configuration</button>
    </form>
</body>
</html>
"""

INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <style>
        body {
            display:flex;
            justify-content:center;
            align-items:center;
            height:100vh;
            flex-direction:column;
            font-family: Arial, sans-serif;
            background: #f0f0f0;
            margin:0;
        }
        #video {
            border: 1px solid #ccc;
            border-radius: 8px;
            max-width: 100%;
        }
        button {
            margin-top: 20px;
            padding: 10px 20px;
            border:none;
            border-radius: 4px;
            background-color: #007bff;
            color: white;
            font-size: 1em;
            cursor: pointer;
        }
        button:disabled {
            background-color: #aaa;
            cursor: default;
        }
        #loading {
            margin-top: 15px;
            font-style: italic;
            color: #555;
            display:none;
        }
        nav a {
            margin-top: 20px;
            font-weight: bold;
            text-decoration: none;
            color: #007bff;
        }
    </style>
</head>
<body>
    <h1>{{ title }}</h1>
    <video id="video" autoplay playsinline width="320" height="240"></video>
    <button id="captureBtn">Capture & Search</button>
    <div id="loading">Processing...</div>
    <nav>
        <a href="{{ url_for('gallery') }}">Gallery</a>
        {% if session.get('logged_in') %}
        | <a href="{{ url_for('admin') }}">Admin Panel</a> | <a href="{{ url_for('logout') }}">Logout</a>
        {% else %}
        | <a href="{{ url_for('login') }}">Admin Login</a>
        {% endif %}
    </nav>
<script>
    const video = document.getElementById('video');
    const captureBtn = document.getElementById('captureBtn');
    const loadingText = document.getElementById('loading');

    // Set up video stream
    navigator.mediaDevices.getUserMedia({video:true})
    .then(stream => {
        video.srcObject = stream;
    })
    .catch(err => {
        alert("Camera access denied or not available.");
    });

    function blobToFile(theBlob, fileName){
        theBlob.lastModifiedDate = new Date();
        theBlob.name = fileName;
        return theBlob;
    }

    captureBtn.onclick = function(){
        loadingText.style.display = 'block';
        captureBtn.disabled = true;

        // Capture current frame from video
        let canvas = document.createElement('canvas');
        canvas.width = video.videoWidth || 320;
        canvas.height = video.videoHeight || 240;
        let ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        canvas.toBlob(blob => {
            // Prepare form data
            const formData = new FormData();
            formData.append('image', blobToFile(blob, 'capture.png'));

            // Send to server for face search
            fetch('/api/search_face', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                loadingText.style.display = 'none';
                captureBtn.disabled = false;
                // alert(`Found ${data.results.length} possible matches! Check gallery.`);
                // You could redirect to gallery or show results
                window.location.href = '/gallery';
            })
            .catch(err => {
                loadingText.style.display = 'none';
                captureBtn.disabled = false;
                alert('Error during face search.');
            })
        }, 'image/png');
    };
</script>
</body>
</html>
"""

GALLERY_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }} - Gallery</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 2em auto;
            max-width: 960px;
            text-align:center;
        }
        .gallery {
            display: flex;
            flex-wrap: wrap;
            justify-content:center;
            gap: 10px;
        }
        .thumbnail {
            width: 80px;
            height: 80px;
            overflow: hidden;
            border-radius: 6px;
            box-shadow: 0 0 4px rgba(0,0,0,0.2);
            cursor: pointer;
            position: relative;
        }
        .thumbnail img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        /* Modal styles */
        #modal {
            display: none; 
            position: fixed; 
            z-index: 1000; 
            padding-top: 60px; 
            left: 0;
            top: 0;
            width: 100%; 
            height: 100%; 
            background-color: rgba(0,0,0,0.7);
        }
        #modal img {
            margin: auto;
            display: block;
            max-width: 90%;
            max-height: 80vh;
            border-radius: 8px;
        }
        #modal.close-btn {
            position: fixed;
            right: 25px;
            top: 25px;
            font-size: 2rem;
            color: white;
            cursor: pointer;
        }
        nav {
            margin-bottom: 1em;
        }
    </style>
</head>
<body>
    <nav>
        <a href="{{ url_for('index') }}">Home</a>
        {% if session.get('logged_in') %}
        | <a href="{{ url_for('admin') }}">Admin Panel</a> | <a href="{{ url_for('logout') }}">Logout</a>
        {% else %}
        | <a href="{{ url_for('login') }}">Admin Login</a>
        {% endif %}
    </nav>
    <h1>Gallery</h1>
    <div class="gallery">
        {% if images %}
            {% for img in images %}
            <div class="thumbnail" onclick="openModal('{{ url_for('photos', filename=img) }}')">
                <img src="{{ url_for('photos', filename=img) }}" alt="{{ img }}">
            </div>
            {% endfor %}
        {% else %}
            <p>No images found in the photo directory.</p>
        {% endif %}
    </div>

    <!-- Modal -->
    <div id="modal" onclick="closeModal()">
        <span id="closeBtn" class="close-btn">&times;</span>
        <img id="modalImg" src="" alt="Full size image">
    </div>

<script>
    const modal = document.getElementById('modal');
    const modalImg = document.getElementById('modalImg');
    const closeBtn = document.getElementById('closeBtn');

    function openModal(src) {
        modal.style.display = 'block';
        modalImg.src = src;
    }
    function closeModal() {
        modal.style.display = 'none';
        modalImg.src = '';
    }
    // Prevent modal close when clicking on image
    modalImg.onclick = function(event) {
        event.stopPropagation();
    }
    closeBtn.onclick = closeModal;
</script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int("5000"), debug=True)
