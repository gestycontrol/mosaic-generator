"""
Usage (examples):
    python run_face_recognition.py /folder1 /folder2 output_faces.json faces_folder
    python run_face_recognition.py /folder1 /folder2 /folder3 output_faces.json faces_folder updated_faces.json

This script demonstrates how to:
1. Accept multiple image folders as input (recursively processed).
2. Detect faces in each image using the face_recognition library.
3. Save cropped faces in a separate folder (faces_folder).
4. Generate a single JSON file (output_faces.json) with data about all detected faces.
5. (Optional) Load an updated JSON file (updated_faces.json) to recategorize faces.

Important:
- If you want to process HEIC files, install pillow-heif (pip install pillow-heif) 
  and register the opener before using Image.open.
"""

import os
import json
import argparse
import face_recognition
from PIL import Image
import numpy as np

# If you need HEIC support, uncomment these lines (assuming pillow-heif is installed).
from pillow_heif import register_heif_opener
register_heif_opener()

def detect_faces_and_save_to_json(image_folders, output_json, faces_folder):
    """
    Recursively traverse multiple folders with images,
    detect faces, and save them in a JSON file.
    Each face is assigned a unique ID and placeholders for 'personName'.

    :param image_folders: List of folders to search for images (including subdirectories).
    :param output_json: Name of the JSON file to store face data.
    :param faces_folder: Folder where cropped face images will be saved.
    """
    os.makedirs(faces_folder, exist_ok=True)

    all_faces = []
    face_id_counter = 0

    # Allowed extensions: add .heic, .heif if you want
    allowed_extensions = (".jpg", ".jpeg", ".png", ".heic", ".heif")

    for folder in image_folders:
        print(f"Processing folder: {folder}")
        for root, dirs, files in os.walk(folder):
            print(f"  Visiting subfolder: {root}")
            for filename in files:
                if not filename.lower().endswith(allowed_extensions):
                    continue  # Skip non-image files

                image_path = os.path.join(root, filename)
                print(f"    Found image: {image_path}")
                try:
                    pil_image = Image.open(image_path)
                    image_array = np.array(pil_image.convert("RGB"))

                    # Detect faces
                    face_locations = face_recognition.face_locations(image_array)
                    face_encodings = face_recognition.face_encodings(image_array, face_locations)

                    if not face_locations:
                        print(f"      No faces detected in {filename}")
                    else:
                        print(f"      Detected {len(face_locations)} face(s) in {filename}")

                    for face_location, face_encoding in zip(face_locations, face_encodings):
                        top, right, bottom, left = face_location

                        # Create a unique ID for each face
                        face_id = f"face_{face_id_counter}"
                        face_id_counter += 1

                        # Extract the face and save it as a separate image
                        face_image = pil_image.crop((left, top, right, bottom))
                        face_filename = os.path.join(faces_folder, f"{face_id}.png")
                        face_image.save(face_filename)

                        # Convert face_encoding (numpy array) to list
                        face_encoding_list = face_encoding.tolist()

                        face_info = {
                            "faceId": face_id,
                            "originalImage": os.path.relpath(image_path, folder),
                            "faceImage": os.path.relpath(face_filename, faces_folder),
                            "encoding": face_encoding_list,
                            "personName": "",
                            "isConfirmed": False
                        }
                        all_faces.append(face_info)

                except Exception as e:
                    print(f"Error processing file {image_path}: {e}")

    # Save all detected faces into a single JSON
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(all_faces, f, indent=4)

    print(f"Faces have been analyzed and stored in {output_json}")


def recategorize_faces_with_updated_json(updated_json):
    """
    Load the updated JSON (where a user has corrected/merged names, etc.)
    and use it to refine categories or handle any custom logic you need.
    """
    if not os.path.exists(updated_json):
        print(f"Updated JSON file not found: {updated_json}")
        return

    with open(updated_json, 'r', encoding='utf-8') as f:
        updated_data = json.load(f)

    # Example logic (modify as you need)
    for face_entry in updated_data:
        face_id = face_entry["faceId"]
        person_name = face_entry["personName"]
        is_confirmed = face_entry["isConfirmed"]
        print(f"Face {face_id} labeled as '{person_name}' (confirmed={is_confirmed})")

    print("Recategorization based on updated JSON complete.")


def main():
    parser = argparse.ArgumentParser(
        description="Face recognition script with support for multiple input folders."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="One or more image folders, followed by output.json, faces_folder, and optionally updated.json."
    )

    args = parser.parse_args()
    paths = args.paths

    # We need at least 3 arguments total:
    #   1+ for the image folders,
    #   plus 1 for output.json,
    #   plus 1 for faces_folder.
    #
    # If there's a 5th argument, that's updated.json.
    # If there's more than 5, you have even more input folders, but the last 3 remain the same logic.
    #
    # E.g.:
    #  - 3 arguments => 1 folder, 1 output.json, 1 faces_folder
    #  - 4 arguments => 2+ folders, 1 output.json, 1 faces_folder
    #  - 5 arguments => 2+ folders, output.json, faces_folder, updated.json
    #
    if len(paths) < 3:
        parser.error("Usage: run_face_recognition.py /folder1 [folder2 ...] output.json faces_folder [updated.json]")

    # We'll parse from the end:
    # Last argument might be faces_folder (if 3 or 4 args total)
    # or updated_json (if 5 or more args total).
    updated_json = None

    if len(paths) == 3:
        # Exactly 3 args: [folder], output.json, faces_folder
        images_folders = [paths[0]]
        output_json = paths[1]
        faces_folder = paths[2]

    elif len(paths) == 4:
        # 4 args: [folders...], output.json, faces_folder
        images_folders = paths[:-2]    # all but last 2
        output_json = paths[-2]
        faces_folder = paths[-1]

    else:
        # 5 or more args: [folders...], output.json, faces_folder, updated.json
        updated_json = paths[-1]
        faces_folder = paths[-2]
        output_json = paths[-3]
        images_folders = paths[:-3]

    # 1) Detect faces
    detect_faces_and_save_to_json(images_folders, output_json, faces_folder)

    # 2) Optionally recategorize
    if updated_json:
        recategorize_faces_with_updated_json(updated_json)

if __name__ == "__main__":
    main()
