import cv2
import os
import numpy as np

def generate_aruco_textures(
    texture_path,
    output_dir,
    marker_ids,
    marker_size=100,
    margin=75
):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for marker_id in range(marker_ids):
        texture = cv2.imread(texture_path)
        if texture is None:
            print(f"[Błąd] Nie udało się wczytać tekstury z: {texture_path}")
            continue

        # Generuj marker
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        marker_img = cv2.aruco.generateImageMarker(aruco_dict, marker_id, marker_size)

        # Zapisz marker
        marker_path = os.path.join(output_dir, f"aruco_marker_{marker_id}.png")
        cv2.imwrite(marker_path, marker_img)

        # Dopasuj do tekstury
        marker_colored = cv2.cvtColor(
            cv2.resize(marker_img, (marker_size, marker_size)),
            cv2.COLOR_GRAY2BGR
        )

        x_offset = margin
        y_offset = texture.shape[0] - marker_size - margin

        if y_offset < 0 or x_offset + marker_size > texture.shape[1]:
            print(f"[Ostrzeżenie] Marker {marker_id} nie mieści się na teksturze. Pomijam.")
            continue

        texture[y_offset:y_offset + marker_size,
                x_offset:x_offset + marker_size] = marker_colored

        output_texture_path = os.path.join(output_dir, f"dirt_with_aruco_{marker_id}.jpg")
        cv2.imwrite(output_texture_path, texture)

        print(f"[OK] Zapisano: {output_texture_path}")
