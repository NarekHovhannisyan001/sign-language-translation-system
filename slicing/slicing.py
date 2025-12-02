import cv2
import os
from pathlib import Path


def detect_motion_segments(video_path: str, min_area: float = 500, min_duration_sec: float = 0.5):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    ret, prev = cap.read()
    if not ret:
        cap.release()
        return [], fps
    
    prev_gray = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY)
    prev_gray = cv2.GaussianBlur(prev_gray, (21, 21), 0)
    
    motion = False
    start_frame = 0
    segments = []
    frame_idx = 1

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        frame_delta = cv2.absdiff(prev_gray, gray)
        _, thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)

        cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        motion_found = any(cv2.contourArea(c) >= min_area for c in cnts)

        if motion_found:
            if not motion:
                motion = True
                start_frame = frame_idx
        else:
            if motion:
                end_frame = frame_idx
                duration = (end_frame - start_frame) / fps
                if duration >= min_duration_sec:
                    segments.append((start_frame, end_frame))
                motion = False

        prev_gray = gray
        frame_idx += 1

    if motion:
        end_frame = frame_idx
        duration = (end_frame - start_frame) / fps
        if duration >= min_duration_sec:
            segments.append((start_frame, end_frame))

    cap.release()
    return segments, fps


def slice_motion_into_single_file(video_path: str, segments, output_path: str):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    writer = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
    if not writer.isOpened():
        cap.release()
        raise RuntimeError(f"Could not open output file {output_path}")

    for (sf, ef) in segments:
        cap.set(cv2.CAP_PROP_POS_FRAMES, sf)
        for fno in range(int(sf), int(ef)):
            ret, frame = cap.read()
            if not ret:
                break
            writer.write(frame)

    writer.release()
    cap.release()


if __name__ == "__main__":
    # Project root directory
    project_root = Path(__file__).parent.parent
    
    # Input: raw videos from Java scraper
    input_dir = project_root / "videos"
    
    # Output: sliced videos with only motion
    output_dir = project_root / "sliced-videos"
    output_dir.mkdir(parents=True, exist_ok=True)

    min_area = 1000
    min_duration_sec = 0.5

    if not input_dir.exists():
        print(f"Error: Directory '{input_dir}' does not exist")
        print("Run Java scraper first to download videos")
        exit(1)

    video_files = [f for f in input_dir.iterdir() if f.is_file()]
    
    if not video_files:
        print(f"No videos found in '{input_dir}'")
        exit(1)

    print(f"Found {len(video_files)} video(s)\n")
    
    for video_file in video_files:
        out_path = output_dir / f"{video_file.stem}_sliced.mp4"
        
        if out_path.exists():
            print(f"⊘ Skip: {video_file.name} (already processed)")
            continue

        print(f"Processing: {video_file.name}")
        
        try:
            segments, fps = detect_motion_segments(str(video_file), min_area, min_duration_sec)
            
            if not segments:
                print(f"  ⚠ No motion detected\n")
                continue
                
            print(f"  ✓ Found {len(segments)} motion segment(s)")
            slice_motion_into_single_file(str(video_file), segments, str(out_path))
            print(f"  ✓ Saved: {out_path.name}\n")
            
        except Exception as e:
            print(f"  ✗ Error: {e}\n")