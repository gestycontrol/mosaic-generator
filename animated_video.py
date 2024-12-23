import argparse
import numpy as np
from moviepy.video.VideoClip import VideoClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from PIL import Image

def configure_parameters(image_path, audio_path, grid_width=10):
    image = Image.open(image_path)
    audio = AudioFileClip(audio_path)

    image_width, image_height = image.size

    # Dimensiones proporcionales al video (480p como referencia)
    video_height = 1080
    video_width = int((video_height / image_height) * image_width)

    # Duración total del video según la longitud de la canción
    total_duration = audio.duration

    # Configuración de tiempos
    static_duration = min(total_duration * 0.1, 5)  # Máximo de 5 segundos para la fase inicial
    final_static_duration = min(total_duration * 0.1, 5)  # Máximo de 5 segundos para la fase final

    # Tiempo restante para el zoom por sector y el zoom out
    remaining_time = total_duration - static_duration - final_static_duration
    zoom_out_duration = remaining_time * 0.1  # 20% del tiempo restante para el zoom out
    zoom_duration_per_sector = (remaining_time - zoom_out_duration) / (grid_width * (image_height // (image_width // grid_width)))

    fps = 24  # Cuadros por segundo

    return {
        "image": image,
        "image_width": image_width,
        "image_height": image_height,
        "video_width": video_width,
        "video_height": video_height,
        "static_duration": static_duration,
        "zoom_duration_per_sector": zoom_duration_per_sector,
        "zoom_out_duration": zoom_out_duration,
        "final_static_duration": final_static_duration,
        "fps": fps,
        "audio": audio,
        "grid_width": grid_width,
        "grid_height": image_height // (image_width // grid_width),
    }

def static_frame(t, params):
    resized_image = params["image"].resize(
        (params["video_width"], params["video_height"]), Image.LANCZOS
    )
    return np.array(resized_image)

def zoom_to_sector_frame(t, params, sector_index):
    grid_width, grid_height = params["grid_width"], params["grid_height"]
    sector_width = params["image_width"] // grid_width
    sector_height = params["image_height"] // grid_height

    col = sector_index % grid_width
    row = sector_index // grid_width

    left = col * sector_width
    upper = row * sector_height
    right = left + sector_width
    lower = upper + sector_height

    cropped_image = params["image"].crop((left, upper, right, lower))
    zoom_ratio = 0.5
    zoom_level = 1 + (t / params["zoom_duration_per_sector"]) * zoom_ratio  # Zoom dinámico

    resized_image = cropped_image.resize(
        (
            int(params["video_width"] * zoom_level),
            int(params["video_height"] * zoom_level),
        ),
        Image.LANCZOS,
    )

    x_offset = (resized_image.width - params["video_width"]) // 2
    y_offset = (resized_image.height - params["video_height"]) // 2

    cropped_zoom = resized_image.crop(
        (x_offset, y_offset, x_offset + params["video_width"], y_offset + params["video_height"])
    )

    return np.array(cropped_zoom)

def zoom_out_frame(t, params):
    zoom_level = 1 + (1 - t / params["zoom_out_duration"]) * 4
    resized_image = params["image"].resize(
        (
            int(params["image_width"] * zoom_level),
            int(params["image_height"] * zoom_level),
        ),
        Image.LANCZOS,
    )

    x_offset = (resized_image.width - params["video_width"]) // 2
    y_offset = (resized_image.height - params["video_height"]) // 2

    cropped_zoom = resized_image.crop(
        (x_offset, y_offset, x_offset + params["video_width"], y_offset + params["video_height"])
    )

    return np.array(cropped_zoom)

def make_frame(t, params):
    if t < params["static_duration"]:
        return static_frame(t, params)

    t -= params["static_duration"]

    num_sectors = params["grid_width"] * params["grid_height"]
    total_zoom_duration = num_sectors * params["zoom_duration_per_sector"]

    if t < total_zoom_duration:
        sector_index = int(t / params["zoom_duration_per_sector"])
        sector_t = t % params["zoom_duration_per_sector"]
        return zoom_to_sector_frame(sector_t, params, sector_index)

    t -= total_zoom_duration

    if t < params["zoom_out_duration"]:
        return zoom_out_frame(t, params)

    t -= params["zoom_out_duration"]

    return static_frame(t, params)

def create_video(image_path, output_video, audio_path):
    params = configure_parameters(image_path, audio_path)

    total_duration = (
        params["static_duration"]
        + params["grid_width"] * params["grid_height"] * params["zoom_duration_per_sector"]
        + params["zoom_out_duration"]
        + params["final_static_duration"]
    )

    video = VideoClip(lambda t: make_frame(t, params), duration=total_duration)
    video = video.with_fps(params["fps"]).resized((params["video_width"], params["video_height"]))

    video = video.with_audio(params["audio"])

    video.write_videofile(output_video, codec="libx264", audio_codec="aac")
    print(f"¡Video generado exitosamente en {output_video}!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generar un video animado de una imagen con zoom por sectores y música.")
    parser.add_argument("image_path", help="Ruta de la imagen de entrada")
    parser.add_argument("output_video", help="Ruta del video de salida")
    parser.add_argument("audio_path", help="Ruta del archivo de audio")
    args = parser.parse_args()

    create_video(args.image_path, args.output_video, args.audio_path)
