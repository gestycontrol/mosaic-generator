import argparse
import numpy as np
from moviepy.video.VideoClip import VideoClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from PIL import Image

def configure_parameters(image_path, audio_path):
    image = Image.open(image_path)
    audio = AudioFileClip(audio_path)

    image_width, image_height = image.size

    # Dimensiones proporcionales al video (480p como referencia)
    video_height = 480
    video_width = int((video_height / image_height) * image_width)

    # Duración total del video según la longitud de la canción
    total_duration = audio.duration

    # Proporción de tiempo para cada fase del video
    zoom_duration = total_duration * 0.2  # 20% para zoom in y zoom out
    pan_duration = total_duration * 0.6   # 60% para el recorrido línea a línea

    fps = 24  # Cuadros por segundo

    return {
        "image": image,
        "image_width": image_width,
        "image_height": image_height,
        "video_width": video_width,
        "video_height": video_height,
        "zoom_duration": zoom_duration,
        "pan_duration": pan_duration,
        "fps": fps,
        "audio": audio,
    }

def zoom_frame(t, params, zoom_in=True):
    if zoom_in:
        scale = 1 - (t / params["zoom_duration"])
    else:
        scale = t / params["zoom_duration"]
    scale = max(scale, 0.1)  # Evitar un zoom excesivo
    resized_image = params["image"].resize(
        (int(params["image_width"] * scale), int(params["image_height"] * scale)), Image.LANCZOS
    )
    x_offset = max((resized_image.width - params["video_width"]) // 2, 0)
    y_offset = max((resized_image.height - params["video_height"]) // 2, 0)
    cropped_image = resized_image.crop(
        (x_offset, y_offset, x_offset + params["video_width"], y_offset + params["video_height"])
    )
    return np.array(cropped_image)

def pan_frame(t, params):
    pan_line = int((t / params["pan_duration"]) * (params["image_height"] - params["video_height"]))
    cropped_image = params["image"].crop(
        (0, pan_line, params["image_width"], pan_line + params["video_height"])
    )
    resized_image = cropped_image.resize(
        (params["video_width"], params["video_height"]), Image.LANCZOS
    )
    return np.array(resized_image)

def make_frame(t, params):
    if t < params["zoom_duration"]:
        return zoom_frame(t, params, zoom_in=True)
    elif t < params["zoom_duration"] + params["pan_duration"]:
        pan_t = t - params["zoom_duration"]
        return pan_frame(pan_t, params)
    else:
        zoom_t = t - (params["zoom_duration"] + params["pan_duration"])
        return zoom_frame(zoom_t, params, zoom_in=False)

def create_video(image_path, output_video, audio_path):
    params = configure_parameters(image_path, audio_path)

    total_duration = params["zoom_duration"] * 2 + params["pan_duration"]
    video = VideoClip(lambda t: make_frame(t, params), duration=total_duration)
    video = video.with_fps(params["fps"]).resized((params["video_width"], params["video_height"]))

    video = video.with_audio(params["audio"])

    video.write_videofile(output_video, codec="libx264", audio_codec="aac")
    print(f"¡Video generado exitosamente en {output_video}!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generar un video animado de una imagen con zoom, panning y música.")
    parser.add_argument("image_path", help="Ruta de la imagen de entrada")
    parser.add_argument("output_video", help="Ruta del video de salida")
    parser.add_argument("audio_path", help="Ruta del archivo de audio")
    args = parser.parse_args()

    create_video(args.image_path, args.output_video, args.audio_path)
