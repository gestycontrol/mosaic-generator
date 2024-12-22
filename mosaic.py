from PIL import Image, ImageEnhance, ExifTags
import pyheif
import os
import numpy as np
import time
import gc
import hashlib
import random
import sys

# Configuración
base_image_path = sys.argv[1] if len(sys.argv) > 1 else 'path_to_base_image.png'  # Imagen principal
tiles_folder = 'path_to_tiles'              # Carpeta con las fotos
output_folder = 'output_mosaics'            # Carpeta para guardar mosaicos
processed_tiles_folder = 'processed_tiles'  # Carpeta para guardar las teselas procesadas
try:
    desired_width = int(sys.argv[2]) if len(sys.argv) > 2 else 1920  # Tamaño
except ValueError:
    print("El valor proporcionado para desired_width no es válido. Usando el valor por defecto: 1920.")
    desired_width = 1920
valid_image_extensions = ('.jpg', '.jpeg', '.png', '.heic')  # Extensiones válidas

# Opcional: Ajustar la opacidad de la imagen principal
try:
    overlay_opacity = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
    if overlay_opacity < 0 or overlay_opacity > 1:
        raise ValueError("La opacidad debe estar en el rango [0, 1].")
except ValueError:
    print("El valor proporcionado para overlay_opacity no es válido. Usando el valor por defecto: 0.3.")
    overlay_opacity = 0.3   

# Funciones auxiliares

def correct_image_orientation(image):
    """Corrige la orientación de una imagen usando datos EXIF."""
    try:
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation':
                break
        exif = image._getexif()
        if exif is not None:
            orientation = exif.get(orientation, None)
            if orientation == 3:
                image = image.rotate(180, expand=True)
            elif orientation == 6:
                image = image.rotate(270, expand=True)
            elif orientation == 8:
                image = image.rotate(90, expand=True)
    except Exception as e:
        print(f"No se pudo corregir la orientación de la imagen: {e}")
    return image

# Calcular el tamaño de las teselas
def calculate_tile_size(total_images, final_width, aspect_ratio):
    final_height = int(final_width / aspect_ratio)
    tile_width = tile_height = int(np.sqrt((final_width * final_height) / (0.9 * total_images)))
    if tile_width < 100 or tile_height < 100:
        tile_width = tile_height = max(100, int(np.sqrt((final_width * final_height) / (0.8 * total_images))))
    return tile_width, tile_height

# Crear carpetas de salida si no existen
os.makedirs(output_folder, exist_ok=True)
os.makedirs(processed_tiles_folder, exist_ok=True)

# Funciones para trabajar con colores

def average_color(image):
    img = np.array(image)
    w, h, d = img.shape
    return tuple(np.mean(img.reshape(w * h, d), axis=0))

def convert_heic_to_png(heic_path, output_path):
    heif_file = pyheif.read(heic_path)
    image = Image.frombytes(
        heif_file.mode, 
        heif_file.size, 
        heif_file.data,
        "raw",
        heif_file.mode,
        heif_file.stride,
    )
    image.save(output_path, format="PNG")

def generate_hashed_filename(filepath, resolution):
    md5_hash = hashlib.md5(filepath.encode()).hexdigest()
    return f"{md5_hash}_{resolution[0]}x{resolution[1]}.jpg"

def process_tiles(tile_size):
    total_files = sum([len(files) for _, _, files in os.walk(tiles_folder)])
    processed_count = 0
    for root, _, files in os.walk(tiles_folder):
        for file in files:
            img_path = os.path.join(root, file)
            if not file.lower().endswith(valid_image_extensions):
                print(f"Archivo no compatible ignorado: {img_path}")
                continue
            try:
                hashed_filename = generate_hashed_filename(img_path, tile_size)
                output_path = os.path.join(processed_tiles_folder, hashed_filename)

                if os.path.exists(output_path):
                    print(f"Tesela ya procesada: {output_path}")
                    processed_count += 1
                    print(f"Progreso: {processed_count}/{total_files} teselas procesadas ({(processed_count / total_files) * 100:.2f}%)")
                    continue

                if file.lower().endswith('.heic'):
                    convert_heic_to_png(img_path, output_path)
                else:
                    img = Image.open(img_path)
                    img = correct_image_orientation(img).convert('RGB')

                    img_width, img_height = img.size
                    target_ratio = tile_size[0] / tile_size[1]
                    img_ratio = img_width / img_height

                    if img_ratio > target_ratio:
                        new_width = int(target_ratio * img_height)
                        offset = (img_width - new_width) // 2
                        img = img.crop((offset, 0, offset + new_width, img_height))
                    else:
                        new_height = int(img_width / target_ratio)
                        offset = (img_height - new_height) // 2
                        img = img.crop((0, offset, img_width, offset + new_height))

                    img = img.resize(tile_size)
                    img.save(output_path, format="JPEG", quality=90)

                processed_count += 1
                print(f"Progreso: {processed_count}/{total_files} teselas procesadas ({(processed_count / total_files) * 100:.2f}%)")
            except Exception as e:
                print(f"Error al procesar {img_path}: {e}")


def load_tiles(tile_size):
    tiles = []
    tile_colors = []
    resolution_suffix = f"_{tile_size[0]}x{tile_size[1]}.jpg"
    for root, _, files in os.walk(processed_tiles_folder):
        for file in files:
            if not file.endswith(resolution_suffix):
                continue
            img_path = os.path.join(root, file)
            try:
                img = Image.open(img_path).convert('RGBA')
                tiles.append(img)
                tile_colors.append(average_color(img))
            except Exception as e:
                print(f"Error al cargar {img_path}: {e}")
    
    # Crear una lista de índices y mezclarla aleatoriamente
    indices = list(range(len(tiles)))
    random.shuffle(indices)
    
    # Reorganizar las listas de acuerdo con el orden aleatorio
    tiles = [tiles[i] for i in indices]
    tile_colors = [tile_colors[i] for i in indices]
    
    return tiles, tile_colors

base_image = Image.open(base_image_path)
base_image = correct_image_orientation(base_image)
base_width, base_height = base_image.size
aspect_ratio = base_width / base_height
final_width = desired_width
final_height = int(final_width / aspect_ratio)
total_images = sum([len(files) for _, _, files in os.walk(tiles_folder)])
tile_width, tile_height = calculate_tile_size(total_images, final_width, aspect_ratio)
grid_cols = final_width // tile_width
grid_rows = final_height // tile_height
tile_size = (tile_width, tile_height)

print(f"Tamaño de cada tesela: {tile_size}")
print(f"Grid: {grid_cols}x{grid_rows} ({grid_cols * grid_rows} teselas)")
print("Procesando teselas...")
process_tiles(tile_size)
tiles, tile_colors = load_tiles(tile_size)
total_tiles = len(tiles)
if total_tiles == 0:
    raise ValueError("No se encontraron imágenes válidas en la carpeta especificada.")

print(f"Fotos disponibles: {total_tiles}")
new_width = grid_cols * tile_width
new_height = grid_rows * tile_height
base_image = base_image.resize((new_width, new_height)).convert('RGBA')
base_pixels = np.array(base_image).reshape((grid_rows, tile_height, grid_cols, tile_width, 4)).mean(axis=(1, 3))
filtered_tiles = []
filtered_colors = []
for i, tile in enumerate(tiles):
    if tile.size == tile_size:
        filtered_tiles.append(tile)
        filtered_colors.append(tile_colors[i])
tiles = filtered_tiles
tile_colors = filtered_colors
if len(tiles) == 0:
    raise ValueError("No hay teselas que coincidan con la resolución esperada.")

mosaic = Image.new('RGBA', base_image.size)
used_tiles = set()

for y in range(grid_rows):
    row = Image.new('RGBA', (new_width, tile_height))
    for x in range(grid_cols):
        base_color = tuple(base_pixels[y, x][:3])
        closest_tile_idx = None
        min_distance = float('inf')
        for idx, tile_color in enumerate(tile_colors):
            if idx in used_tiles:
                continue
            distance = np.linalg.norm(np.array(tile_color[:3]) - np.array(base_color))
            if distance < min_distance:
                min_distance = distance
                closest_tile_idx = idx

        if closest_tile_idx is None or closest_tile_idx >= len(tiles):
            print(f"No se encontró una tesela adecuada para la posición ({y}, {x}). Usando una tesela aleatoria.")
            closest_tile = random.choice(tiles)
        else:
            closest_tile = tiles[closest_tile_idx]
            used_tiles.add(closest_tile_idx)

        row.paste(closest_tile, (x * tile_width, 0))
    mosaic.paste(row, (0, y * tile_height))

overlay = base_image.copy()
draw = Image.new('RGBA', mosaic.size, (0, 0, 0, 0))
opacity = overlay_opacity
for y in range(new_height):
    for x in range(new_width):
        r, g, b, a = overlay.getpixel((x, y))
        draw.putpixel((x, y), (r, g, b, int(a * opacity)))
mosaic = Image.alpha_composite(mosaic, draw)
output_path = os.path.join(output_folder, f"mosaic_{int(time.time())}.jpg")
mosaic.convert('RGB').save(output_path, format="JPEG", quality=90)

print(f"Mosaico generado en: {output_path} usando {used_tiles.__len__()} de {total_tiles} teselas.")

output_path_webp = output_path.replace(".jpg", ".webp")
mosaic.convert('RGB').save(output_path_webp, format="WEBP", quality=90)
print(f"Mosaico en formato WebP guardado en: {output_path_webp}")