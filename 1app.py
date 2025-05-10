import os
import json
import base64
import threading
from flask import Flask, render_template, request, jsonify, send_from_directory
import face_recognition
from PIL import Image
import io

app = Flask(__name__)

# Load or initialize configuration
CONFIG_FILE = 'config.json'
DEFAULT_CONFIG = {
    'title': 'Face Search Gallery',
    'photo_dir': os.path.join(os.getcwd(), 'photos'),
    'encodings_cache': {}
}

try:
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
except:
    config = DEFAULT_CONFIG.copy()
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

# Create photo directory if not exists
os.makedirs(config['photo_dir'], exist_ok=True)

def precompute_encodings():
    """Precompute face encodings in background"""
    encodings = {}
    photo_dir = config['photo_dir']
    valid_extensions = ('.jpg', '.jpeg', '.png')
    
    for filename in os.listdir(photo_dir):
        if filename.lower().endswith(valid_extensions):
            path = os.path.join(photo_dir, filename)
            try:
                image = face_recognition.load_image_file(path)
                face_encodings = face_recognition.face_encodings(image)
                if face_encodings:
                    encodings[filename] = [enc.tolist() for enc in face_encodings]
            except Exception as e:
                print(f"Error processing {filename}: {e}")
    
    config['encodings_cache'] = encodings
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

# Initial precomputation
threading.Thread(target=precompute_encodings).start()

@app.route('/')
def index():
    return render_template('index.html', 
                         title=config['title'],
                         photo_dir=config['photo_dir'])

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        config['title'] = request.form.get('title', config['title'])
        new_dir = request.form.get('photo_dir')
        
        if new_dir and os.path.isdir(new_dir):
            config['photo_dir'] = os.path.abspath(new_dir)
            threading.Thread(target=precompute_encodings).start()
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
    
    return render_template('admin.html', 
                         current_title=config['title'],
                         current_dir=config['photo_dir'])

@app.route('/search', methods=['POST'])
def search():
    if 'image' not in request.json:
        return jsonify({'error': 'No image provided'}), 400
    
    try:
        image_data = base64.b64decode(request.json['image'].split(',')[1])
        image = face_recognition.load_image_file(io.BytesIO(image_data))
        input_encodings = face_recognition.face_encodings(image)
        
        if not input_encodings:
            return jsonify({'error': 'No faces detected'}), 400
        
        matches = []
        input_encoding = input_encodings[0]
        
        for filename, encodings in config['encodings_cache'].items():
            for enc in encodings:
                if face_recognition.compare_faces(
                    [input_encoding], 
                    [enc],
                    tolerance=0.5
                )[0]:
                    matches.append(filename)
                    break
        
        return jsonify({'matches': matches})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/photos/<filename>')
def serve_photo(filename):
    return send_from_directory(config['photo_dir'], filename)

if __name__ == '__main__':
    app.run(debug=True)