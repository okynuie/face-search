import face_recognition

image_path = "/home/unknown/Desktop/kulonuie/Pictures/testing_me/_OKY8375.JPG"

try:
    image = face_recognition.load_image_file(image_path)
    face_encodings = face_recognition.face_encodings(image)
    if face_encodings:
        print(f"Found {len(face_encodings)} faces in {image_path}")
    else:
        print(f"No faces found in {image_path}")
except Exception as e:
    print(f"Error processing {image_path}: {e}")