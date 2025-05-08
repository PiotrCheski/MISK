import cv2
import os
import numpy as np

# Ścieżka do katalogu bieżącego skryptu
current_dir = os.path.dirname(os.path.abspath(__file__))

# Ścieżka do tekstury (plik dirt.jpg znajduje się w folderze nadrzędnym względem folderu, w którym jest skrypt)
texture_path = os.path.join(current_dir, "..", "Textures", "dirt.jpg")

# Wczytaj teksturę
texture = cv2.imread(texture_path)

# Upewnij się, że tekstura jest poprawnie wczytana
if texture is None:
    print(f"Błąd wczytywania tekstury z {texture_path}")
    exit()

# Generowanie kodu ArUco


def generate_aruco_marker(marker_id, size=100):
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker_img = cv2.aruco.generateImageMarker(aruco_dict, marker_id, size)
    return marker_img

# Wygenerowanie markeru ArUco o ID 0
marker_img = generate_aruco_marker(0)
output_marker_path = os.path.join(current_dir, "..", "Textures", "aruco_marker_0.png")
cv2.imwrite(output_marker_path, marker_img)

print(f"Marker zapisany jako: {output_marker_path}")

# Zmniejsz rozmiar markeru, jeśli jest za duży, aby pasował do tekstury
marker_resized = cv2.resize(marker_img, (100, 100))

# Konwertuj marker na obraz kolorowy (dodaj 3 kanały RGB)
marker_colored = cv2.cvtColor(marker_resized, cv2.COLOR_GRAY2BGR)

# Oblicz lewy dolny róg tekstury
# Margines od krawędzi (np. 50 px od dołu i od lewej)
margin = 75

x_offset = margin
y_offset = texture.shape[0] - marker_colored.shape[0] - margin

# Upewnij się, że marker zmieści się w teksturze
if y_offset < 0 or x_offset + marker_colored.shape[1] > texture.shape[1]:
    raise ValueError("Marker nie mieści się w teksturze po przesunięciu.")

# Nałóż marker z przesunięciem od dolnego lewego rogu
texture[y_offset:y_offset + marker_colored.shape[0],
        x_offset:x_offset + marker_colored.shape[1]] = marker_colored


# Zapisz nową teksturę z markerem ArUco
output_texture_path = os.path.join(current_dir, "..", "Textures", "dirt_with_aruco.jpg")
cv2.imwrite(output_texture_path, texture)

# Pokaż wynik
cv2.imshow('Texture with ArUco', texture)
cv2.waitKey(0)
cv2.destroyAllWindows()

print(f"Nowa tekstura zapisana jako: {output_texture_path}")