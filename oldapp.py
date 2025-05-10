from flask import Flask, render_template, request, jsonify, send_from_directory
from concurrent.futures import ProcessPoolExecutor  # Or ThreadPoolExecutor
import multiprocessing
import face_recognition
import os

import concurrent.futures
import pickle
from functools import lru_cache

import base64
import io
import time
from PIL import Image
import numpy as np

app = Flask(__name__)
# PHOTO_FOLDER = "/home/unknown/Pictures/testing/"  # Replace with your actual photo folder
# PHOTO_FOLDER = "/home/unknown/Pictures/compressed1"  # Replace with your actual photo folder
PHOTO_FOLDER = "/home/unknown/Pictures/trial_compressed"  # Replace with your actual photo folder
# PHOTO_FOLDER = "/home/unknown/Desktop/kulonuie/Pictures/testing_me"  # Replace with your actual photo folder
# PHOTO_FOLDER = "/home/unknown/Desktop/kulonuie/Pictures/testing"  # Replace with your actual photo folder
# encoded_faces = {}  # Make sure this global is populated at startup

# deepseek approach
# Configuration
CACHE_FILE = "face_encodings.pkl"
PHOTO_EXTENSIONS = ('.png', '.jpg', '.jpeg')
FACE_DETECTION_MODEL = 'hog'  # Use 'cnn' for better accuracy but slower

def precompute_encodings():
    """Precompute and cache face encodings for all images"""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'rb') as f:
            return pickle.load(f)
    
    encodings_cache = {}
    
    for filename in os.listdir(PHOTO_FOLDER):
        if filename.lower().endswith(PHOTO_EXTENSIONS):
            photo_path = os.path.join(PHOTO_FOLDER, filename)
            try:
                image = face_recognition.load_image_file(photo_path)
                face_locations = face_recognition.face_locations(
                    image, 
                    model=FACE_DETECTION_MODEL,
                    number_of_times_to_upsample=1  # Reduce for faster processing
                )
                face_encodings = face_recognition.face_encodings(
                    image, 
                    known_face_locations=face_locations
                )
                
                if face_encodings:
                    encodings_cache[filename] = face_encodings
            except Exception as e:
                print(f"Error processing {filename}: {e}")
    
    with open(CACHE_FILE, 'wb') as f:
        pickle.dump(encodings_cache, f)
    
    return encodings_cache

@lru_cache(maxsize=1)
def get_cached_encodings():
    """Get cached encodings with LRU caching"""
    return precompute_encodings()

def process_image(filename, input_encoding, tolerance=0.6):
    """Process a single image for parallel execution"""
    encodings = get_cached_encodings().get(filename, [])
    for db_encoding in encodings:
        if face_recognition.compare_faces(
            [input_encoding], 
            db_encoding,
            tolerance=tolerance
        )[0]:
            return filename
    return None

def find_matching_photos_optimized(input_image_data):
    """Optimized version of face matching function"""
    try:
        # Decode input image
        image = face_recognition.load_image_file(io.BytesIO(base64.b64decode(input_image_data)))
        input_encodings = face_recognition.face_encodings(image)
        
        if not input_encodings:
            return []
        
        input_encoding = input_encodings[0]
        encodings_cache = get_cached_encodings()
        total_files = len(encodings_cache)
        
        print(f"Starting comparison of {total_files} photos...")
        
        matches = []
        processed = 0
        
        # Use parallel processing for comparison
        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = {
                executor.submit(
                    process_image, 
                    filename, 
                    input_encoding
                ): filename for filename in encodings_cache
            }
            
            for future in concurrent.futures.as_completed(futures):
                processed += 1
                result = future.result()
                if result:
                    matches.append(os.path.join(PHOTO_FOLDER, result))
                
                # Update progress every 5% or at least once
                if processed % max(1, total_files//20) == 0 or processed == total_files:
                    print(f"Progress: {processed}/{total_files} ({processed/total_files:.0%})", 
                          end='\r' if processed != total_files else '\n')
        
        return matches

    except Exception as e:
        print(f"Error: {e}")
        return []
    
# 






# # paralel process (work)
# def encode_single_image(filename, shared_encoded_faces):
#     if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
#         photo_path = os.path.join(PHOTO_FOLDER, filename)
#         try:
#             image = face_recognition.load_image_file(photo_path)
#             face_encodings = face_recognition.face_encodings(image)
#             if face_encodings:
#                 shared_encoded_faces[filename] = face_encodings
#         except Exception as e:
#             print(f"Error processing: {photo_path} {e}")
#     return None

# def pre_encode_faces_parallel(manager):
#     print(f"PHOTO_FOLDER during pre-encoding: {PHOTO_FOLDER}")
#     filenames = [f for f in os.listdir(PHOTO_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
#     total_files = len(filenames)
#     num_processes = multiprocessing.cpu_count()
#     shared_encoded_faces = manager.dict()
#     processed_count = 0

#     with multiprocessing.Pool(processes=num_processes) as pool:
#         results = []
#         for filename in filenames:
#             result = pool.apply_async(encode_single_image, args=(filename, shared_encoded_faces))
#             results.append(result)

#         for result in results:
#             result.get()  # Wait for the result of each task
#             processed_count += 1
#             print(f"Processed: {processed_count}/{total_files}", end='\r')

#         pool.close()
#         pool.join()

#         global encoded_faces
#         encoded_faces.update(shared_encoded_faces)

#     print("\nEncoding complete.")
#     return encoded_faces
# # 


# # error parallel attemp
# def compare_faces(filename, input_face_encoding):
#     """Compares faces in a single pre-encoded image."""
#     print(f"Comparing against filename: {filename}")
#     print(f"PHOTO_FOLDER in compare_faces: {PHOTO_FOLDER}")
#     full_path = os.path.join(PHOTO_FOLDER, filename)
#     print(f"Attempting to open: {full_path}")
#     if filename in encoded_faces:
#         for database_face_encoding in encoded_faces[filename]:
#             results = face_recognition.compare_faces([input_face_encoding], database_face_encoding)
#             if results[0]:
#                 return os.path.join(PHOTO_FOLDER, filename)
#     return None

# def find_matching_photos(input_image_data):
#     """Finds photos with matching faces using pre-encoded data and parallel processing."""
#     print("masuk find matching function")
#     try:
#         print("try function")
#         image_bytes = base64.b64decode(input_image_data)
#         image = Image.open(io.BytesIO(image_bytes))
#         input_image = np.array(image)

#         input_face_encodings = face_recognition.face_encodings(input_image)

#         if input_face_encodings:
#             print(f"Found {len(input_face_encodings)} face(s) in the input image.")
#         else:
#             print("No faces found in the input image.")
#             return []

#         input_face_encoding = input_face_encodings[0]  # Assuming you want to compare against the first detected face

#         matching_photos = []
#         print(f"PHOTO_FOLDER at search time: {PHOTO_FOLDER}")
#         print(f"Number of pre-encoded images to compare against: {len(encoded_faces)}")

#         with ProcessPoolExecutor() as executor:
#             futures = [executor.submit(compare_faces, filename, input_face_encoding)
#                        for filename in encoded_faces.keys()]
#             for future in futures:
#                 match = future.result()
#                 if match:
#                     matching_photos.append(match)
#                     # If you only need the first match, you can return here:
#                     # return [match]

#         return matching_photos

#     except Exception as e:
#         print(f"An unexpected error occurred in find_matching_photos_optimized: {e}")
#         return []
# # 


# # working single process (work)
# def find_matching_photos(input_image_data):
#     """Finds photos with matching faces in the folder."""
#     print("masuk find matching function")
#     try:
#         print("try function")
#         image_bytes = base64.b64decode(input_image_data)
#         image = Image.open(io.BytesIO(image_bytes))
#         input_image = np.array(image)

#         input_face_encodings = face_recognition.face_encodings(input_image)

#         if input_face_encodings:
#             print(f"Found {len(input_face_encodings)} ")
#         else:
#             print(f"No faces found in {input_image}")

#         if not input_face_encodings:
#             print("masuk not input")
#             return []

#         input_face_encoding = input_face_encodings[0]
#         # print("input :", input_face_encoding)

#         matching_photos = []

#         # print("Keys in encoded_faces:", encoded_faces.keys())

#         print(f"PHOTO_FOLDER at search time: {PHOTO_FOLDER}")  

#         # with ProcessPoolExecutor() as executor:  # or ThreadPoolExecutor()
#         #     results = list(executor.map(compare_faces_in_image, encoded_faces.keys(), [input_face_encoding] * len(encoded_faces)))
#         #     for result in results:
#         #         matching_photos.extend(result)
#         # return matching_photos


#         for filename in os.listdir(PHOTO_FOLDER):
#             if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
#                 photo_path = os.path.join(PHOTO_FOLDER, filename)

#                 try:
#                     database_image = face_recognition.load_image_file(photo_path)
#                     database_face_encodings = face_recognition.face_encodings(database_image)

#                     if database_face_encodings:
#                         for database_face_encoding in database_face_encodings:
#                             results = face_recognition.compare_faces([input_face_encoding], database_face_encoding)
#                             if results[0]:
#                                 matching_photos.append(photo_path)
#                                 break

#     # except Exception as e:
#     #     print(f"Error processing {photo_path}: {e}")
#     #     return []

#                 except Exception as e:
#                     print(f"Error processing {photo_path}: {e}")

#         return matching_photos

#     except Exception as e:
#         print(f"An unexpected error occurred: {e}")
#         return []
# # 

@app.route('/images/<filename>')
def get_image(filename):
    return send_from_directory(PHOTO_FOLDER, filename)

@app.route('/search', methods=['POST'])
def search_faces():
    """Handles the face search request."""

    data = request.get_json()
    image_data = data.get('image')

    if not image_data:
        return jsonify({"error": "No image data provided"}), 400

    matches = find_matching_photos_optimized(image_data)
    # matches = find_matching_photos(image_data)
    # return jsonify({"matches": matches})
    image_urls = [f'/images/{os.path.basename(match)}' for match in matches]
    return jsonify({"matches": image_urls})

@app.route('/')
def index():
    return render_template('index1.html')

if __name__ == '__main__':
    # multiprocessing.set_start_method('spawn', force=True)
    # manager = multiprocessing.Manager()
    # global encoded_faces  # Declare encoded_faces as global before assignment
    # encoded_faces = manager.dict()

    # start_time = time.time()  # Record the start time
    # final_encoded_faces = pre_encode_faces_parallel(manager)
    # end_time = time.time()    # Record the end time

    # manager.shutdown() # Explicitly shutdown the manager
    # print("Pre-encoding complete.")
    # print("Keys in encoded_faces after pre-encoding:", encoded_faces.keys())

    # total_time = end_time - start_time
    # print(f"Total processing time : {total_time:.2f} seconds")

    app.run(debug=True)
    # app.run(debug=True, use_reloader=False)