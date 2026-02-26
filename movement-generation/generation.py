import json
import cv2
import numpy as np
import mediapipe as mp
import os
from functools import partial

# —————————————————————————————————————
# Gradient-Fill Helpers
# —————————————————————————————————————
def vertical_gradient_fill(canvas, poly, color):
    H_img, W_img = canvas.shape[:2]
    mask = np.zeros((H_img, W_img), np.uint8)
    cv2.fillConvexPoly(mask, poly, 255)
    x, y, w, h = cv2.boundingRect(poly)
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, W_img), min(y + h, H_img)
    if x1 <= x0 or y1 <= y0:
        return
    grad = np.linspace(1.2, 0.8, y1 - y0).reshape((y1 - y0, 1))
    for i, yy in enumerate(range(y0, y1)):
        scan = mask[yy, x0:x1].astype(bool)
        for c in range(3):
            canvas[yy, x0:x1, c][scan] = np.clip(color[c] * grad[i], 0, 255)


def radial_gradient_fill(canvas, ellipse, color):
    H_img, W_img = canvas.shape[:2]
    (cx, cy), (ax, ay), ang = ellipse
    cx, cy = int(cx), int(cy)
    ax, ay = int(ax / 2), int(ay / 2)
    mask = np.zeros((H_img, W_img), np.uint8)
    cv2.ellipse(mask, ellipse, 255, -1)
    ys, xs = np.where(mask > 0)
    dx = (xs - cx) / ax
    dy = (ys - cy) / ay
    dist = np.clip(np.sqrt(dx * dx + dy * dy), 0, 1)
    for c in range(3):
        vals = color[c] * (1.1 - 0.4 * dist)
        canvas[ys, xs, c] = np.clip(vals, 0, 255)

# —————————————————————————————————————
# Frame Drawing Function
# —————————————————————————————————————
def draw_frame_data(
    frame_data,
    canvas,
    width,
    height,
    BODY_COLOR,
    HEAD_COLOR,
    LIMB_COLOR,
    LEG_COLOR,
    FINGER_COLORS,
    WHITE,
    IDX,
    FINGERS,
    CONTOURS
):
    # Draw pose skeleton
    pose = frame_data.get('pose', [])
    if pose:
        pts = np.array([
            (int(p['x'] * width), int(p['y'] * height))
            for p in pose
        ], np.int32)
        # Torso fill
        torso = np.array([
            pts[IDX['LEFT_SHOULDER']],
            pts[IDX['RIGHT_SHOULDER']],
            pts[IDX['RIGHT_HIP']],
            pts[IDX['LEFT_HIP']]
        ], np.int32)
        vertical_gradient_fill(canvas, torso, BODY_COLOR)
        # Head fill
        face = frame_data.get('face', [])
        if face:
            fpts = np.array([
                (int(p['x'] * width), int(p['y'] * height))
                for p in face
            ], np.int32)
            mask = np.zeros(len(fpts), bool)
            for a, b in CONTOURS:
                mask[a] = mask[b] = True
            contour = fpts[mask]
            if len(contour) >= 5:
                hull = cv2.convexHull(contour)
                ellipse = cv2.fitEllipse(hull)
                radial_gradient_fill(canvas, ellipse, HEAD_COLOR)
        # Limbs
        limb_pairs = [
            (IDX['LEFT_SHOULDER'], IDX['LEFT_ELBOW']),
            (IDX['LEFT_ELBOW'], IDX['LEFT_WRIST']),
            (IDX['RIGHT_SHOULDER'], IDX['RIGHT_ELBOW']),
            (IDX['RIGHT_ELBOW'], IDX['RIGHT_WRIST'])
        ]
        for s, e in limb_pairs:
            color = tuple(LIMB_COLOR.astype(int).tolist())
            cv2.line(canvas, tuple(pts[s]), tuple(pts[e]), color, 12)
        leg_pairs = [
            ((IDX['LEFT_HIP'], IDX['LEFT_KNEE']), (IDX['LEFT_KNEE'], IDX['LEFT_ANKLE'])),
            ((IDX['RIGHT_HIP'], IDX['RIGHT_KNEE']), (IDX['RIGHT_KNEE'], IDX['RIGHT_ANKLE']))
        ]
        for (h, k), (k2, a) in leg_pairs:
            color = tuple(LEG_COLOR.astype(int).tolist())
            cv2.line(canvas, tuple(pts[h]), tuple(pts[k]), color, 12)
            cv2.line(canvas, tuple(pts[k2]), tuple(pts[a]), color, 12)
    # Draw hands/fingers
    for hand_key in ('left_hand', 'right_hand'):
        pts_h = frame_data.get(hand_key, [])
        if not pts_h:
            continue
        hand = np.array([
            (int(p['x'] * width), int(p['y'] * height))
            for p in pts_h
        ], np.int32)
        for fi, finger in enumerate(FINGERS):
            base = FINGER_COLORS[fi]
            segs = len(finger) - 1
            for i in range(segs):
                p1 = tuple(hand[finger[i]])
                p2 = tuple(hand[finger[i+1]])
                t = (i + 1) / segs
                col = (base + (WHITE - base) * t).astype(int).tolist()
                cv2.line(canvas, p1, p2, tuple(col), 4)

# —————————————————————————————————————
# Keypoint Interpolation Helper
# —————————————————————————————————————
def interpolate_keypoints(d1, d2, t):
    interp = {}
    for key in ('pose', 'face', 'left_hand', 'right_hand'):
        l1, l2 = d1.get(key, []), d2.get(key, [])
        if not l1 or not l2 or len(l1) != len(l2):
            interp[key] = []
            continue
        pts = []
        for p1, p2 in zip(l1, l2):
            pts.append({
                'id': p1['id'],
                'x': p1['x'] * (1 - t) + p2['x'] * t,
                'y': p1['y'] * (1 - t) + p2['y'] * t,
                'z': p1.get('z', 0) * (1 - t) + p2.get('z', 0) * t,
                'visibility': p1.get('visibility', 1) * (1 - t) + p2.get('visibility', 1) * t
            })
        interp[key] = pts
    return interp

# —————————————————————————————————————
# Generate Video from JSON Keypoints
# —————————————————————————————————————
def generate_skeleton_video(
    input_json,
    output_video="out.mp4",
    fps=30,
    width=640,
    height=480
):
    with open(input_json, 'r') as f:
        frames = json.load(f)
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    out = cv2.VideoWriter(output_video, fourcc, fps, (width, height))
    # precompute constants
    BODY_COLOR = np.array([200, 180, 50], np.float32)
    HEAD_COLOR = BODY_COLOR.copy()
    LIMB_COLOR = np.array([180, 180, 255], np.float32)
    LEG_COLOR = np.array([180, 255, 180], np.float32)
    FINGER_COLORS = [np.array(c, np.float32) for c in [(0,128,255),(0,255,0),(255,0,0),(255,255,0),(255,0,255)]]
    WHITE = np.array([255,255,255], np.float32)
    mp_pose = mp.solutions.pose; PL = mp_pose.PoseLandmark
    mp_face = mp.solutions.face_mesh; CONTOURS = mp_face.FACEMESH_TESSELATION
    IDX = {n:PL[n].value for n in PL.__members__}
    FINGERS = [[0,1,2,3,4],[0,5,6,7,8],[0,9,10,11,12],[0,13,14,15,16],[0,17,18,19,20]]
    draw = partial(
        draw_frame_data,
        width=width, height=height,
        BODY_COLOR=BODY_COLOR, HEAD_COLOR=HEAD_COLOR,
        LIMB_COLOR=LIMB_COLOR, LEG_COLOR=LEG_COLOR,
        FINGER_COLORS=FINGER_COLORS, WHITE=WHITE,
        IDX=IDX, FINGERS=FINGERS, CONTOURS=CONTOURS
    )
    for fd in frames:
        canvas = np.zeros((height, width, 3), np.uint8)
        draw(fd, canvas)
        out.write(canvas)
    out.release()
    print(f"✅ Saved video: {output_video} from {input_json}")

# —————————————————————————————————————
# Batch Generator with Trim & Interpolation
# —————————————————————————————————————
def generate_from_phrase(
    phrase,
    json_dir,
    output_video,
    fps=30,
    width=640,
    height=480,
    interp_frames=12,
    trim=20
):
    # collect JSON paths
    paths = []
    for token in phrase.split():
        wp = os.path.join(json_dir, f"{token}.json")
        if os.path.isfile(wp):
            paths.append(wp)
        else:
            for ch in token:
                lp = os.path.join(json_dir, f"{ch}.json")
                if os.path.isfile(lp):
                    paths.append(lp)
                else:
                    print(f"⚠️ Missing JSON for '{ch}'")
    # setup writer
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    out = cv2.VideoWriter(output_video, fourcc, fps, (width, height))
    # precompute constants & helper
    BODY_COLOR = np.array([200,180,50],np.float32)
    HEAD_COLOR = BODY_COLOR.copy()
    LIMB_COLOR = np.array([180,180,255],np.float32)
    LEG_COLOR  = np.array([180,255,180],np.float32)
    FINGER_COLORS = [np.array(c,np.float32) for c in [(0,128,255),(0,255,0),(255,0,0),(255,255,0),(255,0,255)]]
    WHITE = np.array([255,255,255],np.float32)
    mp_pose = mp.solutions.pose; PL = mp_pose.PoseLandmark
    mp_face = mp.solutions.face_mesh; CONTOURS = mp_face.FACEMESH_TESSELATION
    IDX = {n:PL[n].value for n in PL.__members__}
    FINGERS = [[0,1,2,3,4],[0,5,6,7,8],[0,9,10,11,12],[0,13,14,15,16],[0,17,18,19,20]]
    draw = partial(
        draw_frame_data,
        width=width, height=height,
        BODY_COLOR=BODY_COLOR, HEAD_COLOR=HEAD_COLOR,
        LIMB_COLOR=LIMB_COLOR, LEG_COLOR=LEG_COLOR,
        FINGER_COLORS=FINGER_COLORS, WHITE=WHITE,
        IDX=IDX, FINGERS=FINGERS, CONTOURS=CONTOURS
    )
    prev_last = None
    total = len(paths)
    for idx, p in enumerate(paths):
        with open(p) as f:
            frames = json.load(f)
        start = 0 if idx == 0 else trim
        end = len(frames) if idx == total-1 else max(start, len(frames)-trim)
        segment = frames[start:end]
        if prev_last and segment:
            first = segment[0]
            for j in range(1, interp_frames+1):
                t = j/(interp_frames+1)
                inter = interpolate_keypoints(prev_last, first, t)
                canvas = np.zeros((height, width, 3), np.uint8)
                draw(inter, canvas)
                out.write(canvas)
        for fd in segment:
            canvas = np.zeros((height, width, 3), np.uint8)
            draw(fd, canvas)
            out.write(canvas)
        if segment:
            prev_last = segment[-1]
    out.release()
    print(f"✅ Generated '{output_video}' with trim={trim} & interp_frames={interp_frames}")

# —————————————————————————————————————
# Example Usage
# —————————————————————————————————————
if __name__=='__main__':
    generate_from_phrase(
        "ես ապրել հայաստան շատ լավ ու հավեսով",
        "/Users/narek/Desktop/Khosogh-Dzerqer/assets/signlang_kp",
        "res18.mp4",
        fps=30,
        width=640,
        height=480,
        interp_frames=15,
        trim=15
    )