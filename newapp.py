import os
import io
import base64
import concurrent.futures
import pickle
from functools import lru_cache
from flask import Flask, render_template, request, jsonify, send_from_directory
import face_recognition
import numpy as np
from PIL import Image

# Initialize Flask app
app = Flask(__name__)
app.config.update({
    'PHOTO_FOLDER': os.path.join(os.getcwd(), 'photos'),
    'CACHE_FILE': os.path.join(os.getcwd(), 'face_encodings.pkl'),
    'PROCESSING_STATUS': {
        'total': 0,
        'processed': 0,
        'matches': [],
        'complete': False,
        'error': None
    }
})

# Configuration
FACE_DETECTION_MODEL = 'hog'  # 'hog' (faster) or 'cnn' (more accurate)
PHOTO_EXTENSIONS = ('.png', '.jpg', '.jpeg')

def precompute_encodings():
    """Rebuild encodings cache from scratch"""
    encodings_cache = {}
    cache_path = app.config['CACHE_FILE']
    
    try:
        # Try loading existing cache first
        if os.path.exists(cache_path):
            with open(cache_path, 'rb') as f:
                encodings_cache = pickle.load(f)
                return encodings_cache
    except Exception as e:
        print(f"Cache loading failed, rebuilding: {e}")

    # Rebuild cache
    for filename in os.listdir(app.config['PHOTO_FOLDER']):
        if filename.lower().endswith(PHOTO_EXTENSIONS):
            photo_path = os.path.join(app.config['PHOTO_FOLDER'], filename)
            try:
                image = face_recognition.load_image_file(photo_path)
                face_locations = face_recognition.face_locations(
                    image, 
                    model=FACE_DETECTION_MODEL,
                    number_of_times_to_upsample=1
                )
                face_encodings = face_recognition.face_encodings(
                    image, 
                    known_face_locations=face_locations
                )
                
                if face_encodings:
                    encodings_cache[filename] = face_encodings
            except Exception as e:
                print(f"Error processing {filename}: {e}")

    # Save new cache
    with open(cache_path, 'wb') as f:
        pickle.dump(encodings_cache, f)
    
    return encodings_cache

@lru_cache(maxsize=1)
def get_cached_encodings():
    """Get cached encodings with app-context awareness"""
    if 'face_encodings_cache' not in app.config or app.config['face_encodings_cache'] is None:
        app.config['face_encodings_cache'] = precompute_encodings()
    return app.config['face_encodings_cache']

def process_image(filename, input_encoding):
    """Process single image for face matching"""
    try:
        encodings = get_cached_encodings().get(filename, [])
        for db_encoding in encodings:
            if face_recognition.compare_faces(
                [input_encoding], 
                db_encoding,
                tolerance=0.6
            )[0]:
                return filename
        return None
    except Exception as e:
        print(f"Error processing {filename}: {e}")
        return None

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and initiate processing"""
    # Reset processing status
    app.config['PROCESSING_STATUS'] = {
        'total': 0,
        'processed': 0,
        'matches': [],
        'complete': False,
        'error': None
    }
    
    if 'file' not in request.files:
        app.config['PROCESSING_STATUS']['error'] = "No file uploaded"
        app.config['PROCESSING_STATUS']['complete'] = True
        return jsonify(app.config['PROCESSING_STATUS'])
    
    file = request.files['file']
    if file.filename == '':
        app.config['PROCESSING_STATUS']['error'] = "Empty filename"
        app.config['PROCESSING_STATUS']['complete'] = True
        return jsonify(app.config['PROCESSING_STATUS'])
    
    try:
        # Process input image
        image_data = file.read()
        image = face_recognition.load_image_file(io.BytesIO(image_data))
        input_encodings = face_recognition.face_encodings(image)
        
        if not input_encodings:
            app.config['PROCESSING_STATUS']['error'] = "No faces detected in uploaded image"
            app.config['PROCESSING_STATUS']['complete'] = True
            return jsonify(app.config['PROCESSING_STATUS'])
        
        input_encoding = input_encodings[0]
        encodings_cache = get_cached_encodings()
        app.config['PROCESSING_STATUS']['total'] = len(encodings_cache)
        
        # Start async processing
        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = {
                executor.submit(process_image, filename, input_encoding): filename
                for filename in encodings_cache
            }
            
            for future in concurrent.futures.as_completed(futures):
                app.config['PROCESSING_STATUS']['processed'] += 1
                result = future.result()
                if result:
                    app.config['PROCESSING_STATUS']['matches'].append(
                        os.path.join(app.config['PHOTO_FOLDER'], result)
                    )
        
        app.config['PROCESSING_STATUS']['complete'] = True
        return jsonify(app.config['PROCESSING_STATUS'])
    
    except Exception as e:
        app.config['PROCESSING_STATUS']['error'] = str(e)
        app.config['PROCESSING_STATUS']['complete'] = True
        return jsonify(app.config['PROCESSING_STATUS'])

@app.route('/progress')
def get_progress():
    return jsonify(app.config['PROCESSING_STATUS'])

@app.route('/reset-cache')
def reset_cache():
    """Clear and rebuild face encodings cache"""
    try:
        if os.path.exists(app.config['CACHE_FILE']):
            os.remove(app.config['CACHE_FILE'])
        get_cached_encodings.cache_clear()
        app.config['face_encodings_cache'] = None
        precompute_encodings()
        return jsonify({"status": "Cache reset successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/photos/<filename>')
def serve_photo(filename):
    return send_from_directory(app.config['PHOTO_FOLDER'], filename)

if __name__ == '__main__':
    # Clear existing caches on startup
    get_cached_encodings.cache_clear()
    app.config['face_encodings_cache'] = None
    app.run(debug=True)