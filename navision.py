import cv2
import numpy as np
import os
from collections import deque

CALIBRATION_FILE = "calibration_result.npz"
MARKER_LENGTH = 0.05
SCREENSHOT_DIR = "screenshots"

selected_target = 4

PLACES = {
    1: "Entrance",
    2: "Hallway",
    3: "Library",
    4: "AI Laboratory"
}

GRAPH = {
    1: [2],
    2: [1, 3, 4],
    3: [2],
    4: [2]
}

# Simple indoor map coordinates
MARKER_WORLD_POSITIONS = {
    1: (0, 0),
    2: (2, 0),
    3: (2, -1),
    4: (4, 0)
}

MINIMAP_POS = {
    1: (900, 120),
    2: (1030, 120),
    3: (1030, 240),
    4: (1160, 120)
}


def load_calibration():
    data = np.load(CALIBRATION_FILE)
    return data["mtx"], data["dist"]


def find_path(start, goal):
    queue = deque([[start]])
    visited = set()

    while queue:
        path = queue.popleft()
        node = path[-1]

        if node == goal:
            return path

        if node not in visited:
            visited.add(node)

            for neighbor in GRAPH.get(node, []):
                new_path = list(path)
                new_path.append(neighbor)
                queue.append(new_path)

    return []


def get_marker_object_points(marker_length):
    half = marker_length / 2.0

    return np.array([
        [-half,  half, 0],
        [ half,  half, 0],
        [ half, -half, 0],
        [-half, -half, 0]
    ], dtype=np.float32)


def get_world_direction(current_id, next_id):
    if current_id == next_id:
        return "ARRIVED"

    x1, y1 = MARKER_WORLD_POSITIONS[current_id]
    x2, y2 = MARKER_WORLD_POSITIONS[next_id]

    dx = x2 - x1
    dy = y2 - y1

    if abs(dx) >= abs(dy):
        if dx > 0:
            return "MOVE EAST"
        elif dx < 0:
            return "MOVE WEST"
    else:
        if dy > 0:
            return "MOVE NORTH"
        elif dy < 0:
            return "MOVE SOUTH"

    return "GO FORWARD"


def get_screen_direction(center_x, frame_width):
    if center_x < frame_width * 0.4:
        return "TURN LEFT"
    elif center_x > frame_width * 0.6:
        return "TURN RIGHT"
    else:
        return "GO FORWARD"


def draw_big_navigation(frame, status):
    h, w = frame.shape[:2]

    if status == "TURN LEFT":
        arrow = "<"
        text = "TURN LEFT"
    elif status == "TURN RIGHT":
        arrow = ">"
        text = "TURN RIGHT"
    elif status == "DESTINATION REACHED":
        arrow = "OK"
        text = "DESTINATION REACHED"
    elif status == "MOVE EAST":
        arrow = ">"
        text = "MOVE EAST"
    elif status == "MOVE WEST":
        arrow = "<"
        text = "MOVE WEST"
    elif status == "MOVE NORTH":
        arrow = "^"
        text = "MOVE NORTH"
    elif status == "MOVE SOUTH":
        arrow = "v"
        text = "MOVE SOUTH"
    else:
        arrow = "^"
        text = "GO FORWARD"

    cv2.putText(frame, arrow, (w // 2 - 70, h // 2 + 10),
                cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 255, 0), 8)

    cv2.putText(frame, text, (w // 2 - 270, h // 2 + 90),
                cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 0), 3)


def draw_minimap(frame, current_id, target_id, path):
    cv2.putText(frame, "Indoor Map", (900, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    for node, neighbors in GRAPH.items():
        x1, y1 = MINIMAP_POS[node]

        for neighbor in neighbors:
            x2, y2 = MINIMAP_POS[neighbor]

            if node < neighbor:
                cv2.line(frame, (x1, y1), (x2, y2), (180, 180, 180), 2)

    if path and len(path) >= 2:
        for i in range(len(path) - 1):
            x1, y1 = MINIMAP_POS[path[i]]
            x2, y2 = MINIMAP_POS[path[i + 1]]
            cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 255), 5)

    for node, (x, y) in MINIMAP_POS.items():
        if node == current_id:
            color = (0, 255, 0)
        elif node == target_id:
            color = (0, 0, 255)
        else:
            color = (255, 255, 255)

        cv2.circle(frame, (x, y), 20, color, -1)
        cv2.circle(frame, (x, y), 20, (0, 0, 0), 2)

        cv2.putText(frame, str(node), (x - 8, y + 7),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

        cv2.putText(frame, PLACES[node], (x - 45, y + 45),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)


def draw_info_panel(frame, marker_id, target_id, path, distance, status, world_direction, screen_direction):
    current_place = PLACES.get(marker_id, "Unknown")
    target_place = PLACES.get(target_id, "Unknown")

    if path and len(path) > 1:
        next_id = path[1]
        next_place = PLACES[next_id]
    else:
        next_id = marker_id
        next_place = current_place

    route_names = " -> ".join(PLACES[p] for p in path) if path else "No route"

    x, y = 30, 40

    cv2.putText(frame, "Navision", (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

    cv2.putText(frame, f"Current Location: {current_place} (ID {marker_id})", (x, y + 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.putText(frame, f"Selected Destination: {target_place} (ID {target_id})", (x, y + 75),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.putText(frame, f"Next Checkpoint: {next_place} (ID {next_id})", (x, y + 110),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.putText(frame, f"Route: {route_names}", (x, y + 145),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    cv2.putText(frame, f"Map Direction: {world_direction}", (x, y + 180),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.putText(frame, f"Camera Guide: {screen_direction}", (x, y + 215),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.putText(frame, f"Distance to Marker: {distance:.2f} m", (x, y + 250),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.putText(frame, f"Status: {status}", (x, y + 285),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    cv2.putText(frame, "Keys: 1~4 Select Destination | S Save | Q Quit", (x, frame.shape[0] - 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)


def save_screenshot(frame):
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    existing = [f for f in os.listdir(SCREENSHOT_DIR) if f.endswith(".png")]
    filename = os.path.join(SCREENSHOT_DIR, f"navision_demo_{len(existing) + 1}.png")

    cv2.imwrite(filename, frame)
    print(f"Screenshot saved: {filename}")


def main():
    global selected_target

    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    camera_matrix, dist_coeffs = load_calibration()
    marker_object_points = get_marker_object_points(MARKER_LENGTH)

    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    parameters = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Camera open failed.")
        return

    print("Navision started.")
    print("Press 1~4 to select destination.")
    print("Press S to save screenshot.")
    print("Press Q to quit.")

    while True:
        ret, frame = cap.read()

        if not ret:
            print("Failed to read frame.")
            break

        frame = cv2.resize(frame, (1280, 720))
        frame_height, frame_width = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        corners, ids, rejected = detector.detectMarkers(gray)

        if ids is not None:
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)

            for i, marker_id in enumerate(ids.flatten()):
                marker_id = int(marker_id)

                image_points = corners[i][0].astype(np.float32)

                success, rvec, tvec = cv2.solvePnP(
                    marker_object_points,
                    image_points,
                    camera_matrix,
                    dist_coeffs
                )

                if not success:
                    continue

                cv2.drawFrameAxes(
                    frame,
                    camera_matrix,
                    dist_coeffs,
                    rvec,
                    tvec,
                    MARKER_LENGTH * 0.7
                )

                center_x = int(np.mean(image_points[:, 0]))
                center_y = int(np.mean(image_points[:, 1]))
                distance = np.linalg.norm(tvec)

                path = find_path(marker_id, selected_target)

                if path and len(path) > 1:
                    next_marker = path[1]
                else:
                    next_marker = marker_id

                world_direction = get_world_direction(marker_id, next_marker)
                screen_direction = get_screen_direction(center_x, frame_width)

                if marker_id == selected_target and distance < 0.8:
                    status = "DESTINATION REACHED"
                else:
                    status = world_direction

                draw_info_panel(
                    frame,
                    marker_id,
                    selected_target,
                    path,
                    distance,
                    status,
                    world_direction,
                    screen_direction
                )

                draw_big_navigation(frame, status)
                draw_minimap(frame, marker_id, selected_target, path)

                cv2.circle(frame, (center_x, center_y), 5, (0, 255, 0), -1)

                cv2.arrowedLine(
                    frame,
                    (frame_width // 2, frame_height - 80),
                    (center_x, center_y),
                    (0, 255, 0),
                    4,
                    tipLength=0.2
                )

                break

        else:
            cv2.putText(frame, "No marker detected", (30, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

            cv2.putText(frame, f"Selected Destination: {PLACES[selected_target]}",
                        (30, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            cv2.putText(frame, "Show an ArUco marker to start navigation.",
                        (30, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        cv2.imshow("Navision - Indoor AR Navigation System", frame)

        key = cv2.waitKey(1) & 0xFF

        if key in [ord("1"), ord("2"), ord("3"), ord("4")]:
            selected_target = int(chr(key))
            print(f"Selected destination: {PLACES[selected_target]}")

        elif key == ord("s"):
            save_screenshot(frame)

        elif key == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()