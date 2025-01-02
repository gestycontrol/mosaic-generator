<?php
import argparse
import numpy as np
from moviepy.video.VideoClip import VideoClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from PIL import Image

def configure_parameters(image_path, audio_path, grid_width=10):
    image = Image.open(image_path)
    audio = AudioFileClip(audio_path)

    image_width, image_height = image.size

    # We use 1080p as base for video height
    video_height = 1080
    video_width = int((video_height / image_height) * image_width)

    total_duration = audio.duration

    # Static phases (initial/final)
    static_duration = min(total_duration * 0.1, 5)
    final_static_duration = min(total_duration * 0.1, 5)

    remaining_time = total_duration - static_duration - final_static_duration
    zoom_out_duration = remaining_time * 0.1
    zoom_duration_per_sector = (remaining_time - zoom_out_duration) / (
        grid_width * (image_height // (image_width // grid_width))
    )

    fps = 24

    # ---------------------------------------------------------
    # Calculate final_scale for "static frame"
    # This final_scale is the scale factor at which we see the
    # entire image "best fit" inside the video dimension
    # without distorsions. We'll use it also in the zoom out.
    # ---------------------------------------------------------
    scale_w = video_width / image_width
    scale_h = video_height / image_height
    final_scale = min(scale_w, scale_h)  # so the whole image fits

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
        "final_scale": final_scale,  # factor de escala para la fase estática
    }

def static_frame(t, params):
    """
    Shows the image at 'final_scale' so that it fits inside the
    (video_width, video_height) area, then center-crops if needed.
    """
    image = params["image"]
    scale = params["final_scale"]

    # Compute new image size
    new_width = int(image.width * scale)
    new_height = int(image.height * scale)

    # Resize the original image
    resized_image = image.resize((new_width, new_height), Image.LANCZOS)

    # If it is larger than (video_width, video_height), crop the center
    x_offset = max(0, (new_width - params["video_width"]) // 2)
    y_offset = max(0, (new_height - params["video_height"]) // 2)
    right = x_offset + params["video_width"]
    lower = y_offset + params["video_height"]

    cropped = resized_image.crop((x_offset, y_offset, right, lower))

    return np.array(cropped)

def zoom_to_sector_frame(t, params, sector_index):
    """
    Zoom from normal (1:1) up to 1.5x for each sector, with a linear factor
    from 1.0 to 1.0 + zoom_ratio.
    """
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

    # For example, we do a 0.5 zoom ratio (1.0 => 1.5).
    zoom_ratio = 0.5
    progress = t / params["zoom_duration_per_sector"]
    zoom_level = 1.0 + zoom_ratio * progress  # from 1.0 to 1.5

    # Resize based on zoom_level but then center-crop to (video_width, video_height)
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
    """
    Smoothly go from a bigger zoom (e.g. 4x) down to final_scale,
    so it ends exactly matching the static_frame's scale.
    """
    start_zoom = 4.0  # you can tweak this if you want more or less initial "big zoom"
    end_zoom = params["final_scale"]  # it ends at the same scale as static_frame

    progress = t / params["zoom_out_duration"]
    # Linear interpolation between start_zoom and end_zoom
    current_zoom = start_zoom + (end_zoom - start_zoom) * progress

    # Now resize the original image with this current_zoom factor
    new_width = int(params["image_width"] * current_zoom)
    new_height = int(params["image_height"] * current_zoom)

    resized_image = params["image"].resize((new_width, new_height), Image.LANCZOS)

    # Center-crop to the video dimension
    x_offset = max(0, (new_width - params["video_width"]) // 2)
    y_offset = max(0, (new_height - params["video_height"]) // 2)
    right = x_offset + params["video_width"]
    lower = y_offset + params["video_height"]

    cropped_zoom = resized_image.crop((x_offset, y_offset, right, lower))

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

    # Final static phase
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
    video = video.with_fps(params["fps"])

    # The .resized() call at the end can be omitted, because we're already
    # generating frames at (video_width, video_height). But if you want to ensure
    # a final pass, you can keep it. It shouldn't cause a jump because all frames
    # are already (video_width, video_height).
    video = video.resized((params["video_width"], params["video_height"]))

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
