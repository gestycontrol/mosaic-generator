import os
import hashlib

def calculate_md5(file_path):
    """
    Calcula el hash MD5 de un archivo.
    """
    hash_md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def remove_duplicate_images(directory):
    """
    Busca y elimina imágenes duplicadas en un directorio y sus subdirectorios.
    """
    md5_map = {}
    duplicates = []

    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)

            # Calcula el hash MD5 del archivo
            try:
                file_md5 = calculate_md5(file_path)

                if file_md5 in md5_map:
                    # Si ya existe el hash, añade el archivo a la lista de duplicados
                    duplicates.append(file_path)
                else:
                    # Almacena el hash y la ruta del archivo
                    md5_map[file_md5] = file_path

            except Exception as e:
                print(f"Error al procesar el archivo {file_path}: {e}")

    # Elimina los duplicados
    for duplicate in duplicates:
        try:
            os.remove(duplicate)
            print(f"Eliminado: {duplicate}")
        except Exception as e:
            print(f"Error al eliminar el archivo {duplicate}: {e}")

if __name__ == "__main__":
    # Cambia 'path_to_directory' por la ruta del directorio que deseas analizar
    path_to_directory = input("Introduce la ruta del directorio a analizar: ").strip()

    if os.path.isdir(path_to_directory):
        remove_duplicate_images(path_to_directory)
    else:
        print(f"La ruta proporcionada no es un directorio válido: {path_to_directory}")
