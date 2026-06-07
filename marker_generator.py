import cv2
import os

MARKER_DIR = "markers"
MARKER_SIZE = 400

aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)

os.makedirs(MARKER_DIR, exist_ok=True)

for marker_id in range(1, 5):
    marker = cv2.aruco.generateImageMarker(
        aruco_dict,
        marker_id,
        MARKER_SIZE
    )

    filename = os.path.join(
        MARKER_DIR,
        f"marker_{marker_id}.png"
    )

    cv2.imwrite(filename, marker)

    print(f"Saved: {filename}")

print("Done.")