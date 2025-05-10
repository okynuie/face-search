import face_recognition

image = face_recognition.load_image_file("/home/unknown/Desktop/kulonuie/Pictures/Oky (4x6).jpg") #replace some_image.jpg with a valid image in your folder.
face_locations = face_recognition.face_locations(image)

print(face_locations)