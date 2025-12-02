import json
from pathlib import Path
import cv2
import mediapipe as mp


def extract_keypoints(video_path: str, output_path: str):
    mp_holistic = mp.solutions.holistic
    holistic = mp_holistic.Holistic(
        static_image_mode=False,
        model_complexity=1,
        refine_face_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    all_frames = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = holistic.process(image_rgb)

        data = {
            'frame': frame_idx,
            'pose': [],
            'face': [],
            'left_hand': [],
            'right_hand': []
        }

        if results.pose_landmarks:
            for id, lm in enumerate(results.pose_landmarks.landmark):
                data['pose'].append({
                    'id': id,
                    'x': lm.x,
                    'y': lm.y,
                    'z': lm.z,
                    'visibility': lm.visibility
                })

        if results.face_landmarks:
            for id, lm in enumerate(results.face_landmarks.landmark):
                data['face'].append({
                    'id': id,
                    'x': lm.x,
                    'y': lm.y,
                    'z': lm.z
                })

        if results.left_hand_landmarks:
            for id, lm in enumerate(results.left_hand_landmarks.landmark):
                data['left_hand'].append({
                    'id': id,
                    'x': lm.x,
                    'y': lm.y,
                    'z': lm.z
                })

        if results.right_hand_landmarks:
            for id, lm in enumerate(results.right_hand_landmarks.landmark):
                data['right_hand'].append({
                    'id': id,
                    'x': lm.x,
                    'y': lm.y,
                    'z': lm.z
                })

        all_frames.append(data)
        
        if frame_idx % 100 == 0 and frame_idx > 0:
            print(f"  Processed {frame_idx} frames...")
        
        frame_idx += 1

    cap.release()
    holistic.close()

    with open(output_path, 'w') as f:
        json.dump(all_frames, f, indent=2)

    return len(all_frames)


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    
    input_dir = project_root / "sliced-videos"
    output_dir = project_root / "keypoints"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists():
        print(f"Error: Directory '{input_dir}' does not exist")
        print("Run slicing.py first to create sliced videos")
        exit(1)

    video_files = [f for f in input_dir.iterdir() if f.is_file() and f.suffix in ['.mp4', '.webm']]
    
    if not video_files:
        print(f"No videos found in '{input_dir}'")
        exit(1)

    print(f"Found {len(video_files)} video(s)\n")
    
    for video_file in video_files:
        output_json = output_dir / f"{video_file.stem}_keypoints.json"
        
        if output_json.exists():
            print(f"⊘ Skip: {video_file.name} (already processed)")
            continue

        print(f"Processing: {video_file.name}")
        
        try:
            num_frames = extract_keypoints(str(video_file), str(output_json))
            print(f"  ✓ Extracted {num_frames} frames → {output_json.name}\n")
            
        except Exception as e:
            print(f"  ✗ Error: {e}\n")
