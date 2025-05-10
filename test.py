import sys
import os

print(f"Python Executable: {sys.executable}")
print(f"Python Path: {sys.path}")
print(f"Current Working Directory: {os.getcwd()}")

try:
    import face_recognition
    print("face_recognition imported successfully within the app.")
except ImportError as e:
    print(f"Error importing face_recognition within the app: {e}")

try:
    import face_recognition_models
    print("face_recognition_models imported successfully within the app.")
except ImportError as e:
    print(f"Error importing face_recognition_models within the app: {e}")