import os
import io
import base64
import pickle
import concurrent.futures
from flask import Flask, render_template, request, send_from_directory, jsonify
import face_recognition
from PIL import Image

app = Flask(__name__)
app.config.update({
    'current_directory': os.path.join(os.getcwd(), 'photos'),
    'encodings_cache': None,
    'processing': {
        'total': 0,
        'processed': 0,
        'matches': [],
        'running': False
    }
})

def validate_directory(path):
    return os.path.exists(path) and os.path.isdir(path)

def precompute_encodings(directory):
    cache_path = os.path.join(directory, 'face_encodings.pkl')
    encodings = {}
    
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'rb') as f:
                encodings = pickle.load(f)
            return encodings
        except:
            pass

    valid_extensions = ('.jpg', '.jpeg', '.png')
    files = [f for f in os.listdir(directory) if f.lower().endswith(valid_extensions)]
    
    for filename in files:
        path = os.path.join(directory, filename)
        try:
            image = face_recognition.load_image_file(path)
            encodings_list = face_recognition.face_encodings(image)
            if encodings_list:
                encodings[filename] = encodings_list
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    
    with open(cache_path, 'wb') as f:
        pickle.dump(encodings, f)
    
    return encodings

@app.route('/')
def index():
    return render_template('index2.html')

@app.route('/change_directory', methods=['POST'])
def change_directory():
    new_dir = request.form.get('directory')
    if not validate_directory(new_dir):
        return jsonify({'error': 'Invalid directory'}), 400
    
    app.config['current_directory'] = new_dir
    app.config['encodings_cache'] = precompute_encodings(new_dir)
    return jsonify({'message': f'Directory changed to {new_dir}', 'file_count': len(app.config['encodings_cache'])})

@app.route('/search', methods=['POST'])
def search():
    if 'image' not in request.json:
        return jsonify({'error': 'No image provided'}), 400
    
    try:
        # Reset processing state
        app.config['processing'] = {
            'total': len(app.config['encodings_cache']),
            'processed': 0,
            'matches': [],
            'running': True
        }
        
        # Process uploaded image
        image_data = base64.b64decode(request.json['image'].split(',')[1])
        image = face_recognition.load_image_file(io.BytesIO(image_data))
        input_encodings = face_recognition.face_encodings(image)
        
        if not input_encodings:
            return jsonify({'error': 'No faces detected'}), 400
        
        # Compare faces in parallel
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for filename, encodings in app.config['encodings_cache'].items():
                futures.append(executor.submit(
                    process_image,
                    filename,
                    encodings,
                    input_encodings[0]
                ))
            
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                app.config['processing']['processed'] += 1
                if result:
                    app.config['processing']['matches'].append(result)
        
        app.config['processing']['running'] = False
        return jsonify({
            'matches': app.config['processing']['matches'],
            'directory': app.config['current_directory']
        })
    
    except Exception as e:
        app.config['processing']['running'] = False
        return jsonify({'error': str(e)}), 500

def process_image(filename, db_encodings, input_encoding):
    try:
        for encoding in db_encodings:
            if face_recognition.compare_faces([input_encoding], encoding, tolerance=0.5)[0]:
                return filename
        return None
    except Exception as e:
        print(f"Error processing {filename}: {e}")
        return None

@app.route('/progress')
def get_progress():
    return jsonify(app.config['processing'])

@app.route('/photos/<path:filename>')
def serve_photo(filename):
    return send_from_directory(app.config['current_directory'], filename)

if __name__ == '__main__':
    app.config['encodings_cache'] = precompute_encodings(app.config['current_directory'])
    app.run(host='0.0.0.0', port=5000, debug=True)