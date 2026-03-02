import json
import cv2
import numpy as np
import mediapipe as mp
import os
from functools import partial

# ─────────────────────────────────────────────
# Color Palette (BGR for OpenCV)
# ─────────────────────────────────────────────
SKIN_LIGHT  = np.array([160, 190, 225], np.float32)   # highlight
SKIN_MID    = np.array([130, 165, 210], np.float32)   # base skin
SKIN_DARK   = np.array([100, 135, 180], np.float32)   # shadow

SHIRT_TOP   = np.array([140, 100,  70], np.float32)   # warm rust top
SHIRT_BOT   = np.array([100,  70,  50], np.float32)   # darker bottom

PANTS_TOP   = np.array([ 80,  65,  50], np.float32)
PANTS_BOT   = np.array([ 55,  45,  35], np.float32)

NECK_COLOR  = SKIN_MID.copy()

# ─────────────────────────────────────────────
# Face Landmark Index Groups
# ─────────────────────────────────────────────
LEFT_EYE    = [33,7,163,144,145,153,154,155,133,173,157,158,159,160,161,246]
RIGHT_EYE   = [362,382,381,380,374,373,390,249,263,466,388,387,386,385,384,398]
LEFT_IRIS   = [474,475,476,477]
RIGHT_IRIS  = [469,470,471,472]
LEFT_BROW   = [70,63,105,66,107,55,65,52,53,46]
RIGHT_BROW  = [300,293,334,296,336,285,295,282,283,276]
LIPS_OUTER  = [61,185,40,39,37,0,267,269,270,409,291,375,321,405,314,17,84,181,91,146]
LIPS_INNER  = [78,191,80,81,82,13,312,311,310,415,308,324,318,402,317,14,87,178,88,95]
NOSE_BRIDGE = [168,6,197,195,5]
NOSE_TIP    = [4,1,19,94,2]



# ─────────────────────────────────────────────
# Drawing Helpers
# ─────────────────────────────────────────────

def draw_capsule(canvas, p1, p2, color, radius, shadow_offset=2):
    """Rounded filled cylinder between two joints with drop shadow."""
    x1, y1 = int(p1[0]), int(p1[1])
    x2, y2 = int(p2[0]), int(p2[1])
    c      = tuple(np.clip(color,        0, 255).astype(int).tolist())
    shadow = tuple(np.clip(color * 0.5,  0, 255).astype(int).tolist())
    so = shadow_offset
    # Shadow pass
    cv2.line(  canvas, (x1+so, y1+so), (x2+so, y2+so), shadow, radius*2+2, cv2.LINE_AA)
    cv2.circle(canvas, (x1+so, y1+so), radius, shadow, -1, cv2.LINE_AA)
    cv2.circle(canvas, (x2+so, y2+so), radius, shadow, -1, cv2.LINE_AA)
    # Main pass
    cv2.line(  canvas, (x1, y1), (x2, y2), c, radius*2, cv2.LINE_AA)
    cv2.circle(canvas, (x1, y1), radius, c, -1, cv2.LINE_AA)
    cv2.circle(canvas, (x2, y2), radius, c, -1, cv2.LINE_AA)


def draw_joint(canvas, pt, radius, color):
    """Joint circle with shadow and highlight shine."""
    x, y   = int(pt[0]), int(pt[1])
    c      = tuple(np.clip(color,       0, 255).astype(int).tolist())
    dark   = tuple(np.clip(color*0.55,  0, 255).astype(int).tolist())
    bright = tuple(np.clip(color*1.35,  0, 255).astype(int).tolist())
    cv2.circle(canvas, (x+2, y+2), radius,          dark,   -1, cv2.LINE_AA)
    cv2.circle(canvas, (x,   y  ), radius,          c,      -1, cv2.LINE_AA)
    cv2.circle(canvas, (x-1, y-1), max(1,radius//3), bright, -1, cv2.LINE_AA)


def vertical_gradient_fill(canvas, poly, color_top, color_bot):
    """Fill convex polygon with vertical gradient."""
    H, W = canvas.shape[:2]
    mask = np.zeros((H, W), np.uint8)
    cv2.fillConvexPoly(mask, poly, 255)
    x, y, w, h = cv2.boundingRect(poly)
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x+w, W), min(y+h, H)
    if x1 <= x0 or y1 <= y0:
        return
    rows = max(y1 - y0 - 1, 1)
    for i, yy in enumerate(range(y0, y1)):
        t = i / rows
        blend = color_top * (1-t) + color_bot * t
        scan = mask[yy, x0:x1].astype(bool)
        for c in range(3):
            canvas[yy, x0:x1, c][scan] = np.clip(blend[c], 0, 255)


def radial_gradient_fill(canvas, ellipse, color_center, color_edge):
    """Fill ellipse with radial gradient."""
    H, W = canvas.shape[:2]
    (cx, cy), (ax, ay), _ = ellipse
    cx, cy = int(cx), int(cy)
    ax, ay = max(1, int(ax/2)), max(1, int(ay/2))
    mask = np.zeros((H, W), np.uint8)
    cv2.ellipse(mask, ellipse, 255, -1)
    ys, xs = np.where(mask > 0)
    if len(ys) == 0:
        return
    dist = np.clip(np.sqrt(((xs-cx)/ax)**2 + ((ys-cy)/ay)**2), 0, 1)
    for c in range(3):
        canvas[ys, xs, c] = np.clip(
            color_center[c]*(1-dist) + color_edge[c]*dist, 0, 255)



def draw_face_features(canvas, fpts):
    """Draw eyes (with iris), eyebrows, lips and nose on face."""

    def pts_of(indices):
        return np.array([fpts[i] for i in indices if i < len(fpts)], np.int32)

    # ── Eyes: white sclera ────────────────────────────────────
    sclera = (245, 245, 240)
    for eye_idx in [LEFT_EYE, RIGHT_EYE]:
        eye = pts_of(eye_idx)
        if len(eye) >= 5:
            hull = cv2.convexHull(eye)
            cv2.fillConvexPoly(canvas, hull, sclera)
            c_eye = tuple(np.clip(SKIN_DARK * 0.6, 0, 255).astype(int).tolist())
            cv2.polylines(canvas, [hull], True, c_eye, 1, cv2.LINE_AA)

    # ── Iris ──────────────────────────────────────────────────
    iris_color  = (90, 65, 45)
    pupil_color = (15, 10, 10)
    for iris_idx in [LEFT_IRIS, RIGHT_IRIS]:
        iris = pts_of(iris_idx)
        if len(iris) >= 4:
            cx = int(np.mean(iris[:, 0]))
            cy = int(np.mean(iris[:, 1]))
            r  = max(2, int(np.mean(np.sqrt(
                (iris[:, 0] - cx)**2 + (iris[:, 1] - cy)**2))))
            cv2.circle(canvas, (cx, cy),          r,           iris_color,  -1, cv2.LINE_AA)
            cv2.circle(canvas, (cx, cy),           max(1,r//2), pupil_color, -1, cv2.LINE_AA)
            cv2.circle(canvas, (cx-1, cy-1),       max(1,r//4),(220,215,210),-1, cv2.LINE_AA)

    # ── Lips ──────────────────────────────────────────────────
    lip_outer_color = (115, 145, 180)  # neutral skin tone outer lip
    lip_inner_color = (95,  120, 155)   # slightly darker inner
    outer = pts_of(LIPS_OUTER)
    inner = pts_of(LIPS_INNER)
    if len(outer) >= 5:
        cv2.fillConvexPoly(canvas, cv2.convexHull(outer), lip_outer_color)
    if len(inner) >= 5:
        cv2.fillConvexPoly(canvas, cv2.convexHull(inner), lip_inner_color)
    if len(outer) >= 2:
        c_lip = tuple(np.clip(np.array(lip_outer_color, np.float32)*0.75, 0, 255).astype(int).tolist())
        cv2.polylines(canvas, [cv2.convexHull(outer)], True, c_lip, 1, cv2.LINE_AA)



# ─────────────────────────────────────────────
# Main Frame Drawing
# ─────────────────────────────────────────────

def draw_frame_data(frame_data, canvas, width, height, IDX, FINGERS, CONTOURS):
    pose = frame_data.get('pose', [])
    if not pose:
        return

    pts = np.array([
        (int(p['x'] * width), int(p['y'] * height))
        for p in pose
    ], np.int32)

    def pt(name):
        return pts[IDX[name]]

    # ── 1. LEGS (behind everything) ───────────────────────────────
    for hip, knee, ankle in [
        ('LEFT_HIP',  'LEFT_KNEE',  'LEFT_ANKLE'),
        ('RIGHT_HIP', 'RIGHT_KNEE', 'RIGHT_ANKLE'),
    ]:
        draw_capsule(canvas, pt(hip),  pt(knee),  PANTS_TOP, 9)
        draw_capsule(canvas, pt(knee), pt(ankle), PANTS_BOT, 8)
        draw_joint(canvas, pt(knee),  7, PANTS_TOP)
        draw_joint(canvas, pt(ankle), 6, PANTS_BOT)

    # ── 2. TORSO ──────────────────────────────────────────────────
    torso = np.array([
        pt('LEFT_SHOULDER'), pt('RIGHT_SHOULDER'),
        pt('RIGHT_HIP'),     pt('LEFT_HIP')
    ], np.int32)
    vertical_gradient_fill(canvas, torso, SHIRT_TOP, SHIRT_BOT)
    outline = tuple(np.clip(SHIRT_TOP * 0.65, 0, 255).astype(int).tolist())
    cv2.polylines(canvas, [torso], True, outline, 1, cv2.LINE_AA)

    # ── 3. ARMS (over torso) ──────────────────────────────────────
    for shoulder, elbow, wrist in [
        ('LEFT_SHOULDER',  'LEFT_ELBOW',  'LEFT_WRIST'),
        ('RIGHT_SHOULDER', 'RIGHT_ELBOW', 'RIGHT_WRIST'),
    ]:
        draw_capsule(canvas, pt(shoulder), pt(elbow), SKIN_MID,  8)
        draw_capsule(canvas, pt(elbow),    pt(wrist), SKIN_DARK, 7)
        draw_joint(canvas, pt(elbow), 7, SKIN_MID)
        draw_joint(canvas, pt(wrist), 6, SKIN_DARK)

    # Shoulder & hip joints
    draw_joint(canvas, pt('LEFT_SHOULDER'),  10, SHIRT_TOP)
    draw_joint(canvas, pt('RIGHT_SHOULDER'), 10, SHIRT_TOP)
    draw_joint(canvas, pt('LEFT_HIP'),        9, SHIRT_BOT)
    draw_joint(canvas, pt('RIGHT_HIP'),       9, SHIRT_BOT)

    # ── 4. NECK ───────────────────────────────────────────────────
    neck_base = (
        (pt('LEFT_SHOULDER')[0] + pt('RIGHT_SHOULDER')[0]) // 2,
        (pt('LEFT_SHOULDER')[1] + pt('RIGHT_SHOULDER')[1]) // 2,
    )
    draw_capsule(canvas, neck_base, neck_base, NECK_COLOR, 6)

    # ── 5. HEAD ───────────────────────────────────────────────────
    face = frame_data.get('face', [])
    if face:
        fpts = np.array([
            (int(p['x'] * width), int(p['y'] * height))
            for p in face
        ], np.int32)
        face_mask = np.zeros(len(fpts), bool)
        for a, b in CONTOURS:
            face_mask[a] = face_mask[b] = True
        contour = fpts[face_mask]
        if len(contour) >= 5:
            hull = cv2.convexHull(contour)
            ellipse = cv2.fitEllipse(hull)
            radial_gradient_fill(canvas, ellipse, SKIN_LIGHT, SKIN_DARK)
            c_out = tuple(np.clip(SKIN_DARK * 0.7, 0, 255).astype(int).tolist())
            cv2.ellipse(canvas, ellipse, c_out, 1, cv2.LINE_AA)
            # Draw facial features on top of head
            draw_face_features(canvas, fpts)

    # ── 6. HANDS / FINGERS ────────────────────────────────────────
    for hand_key in ('left_hand', 'right_hand'):
        pts_h = frame_data.get(hand_key, [])
        if not pts_h:
            continue
        hand = np.array([
            (int(p['x'] * width), int(p['y'] * height))
            for p in pts_h
        ], np.int32)

        # Palm
        palm_ids = [0, 1, 5, 9, 13, 17]
        hull = cv2.convexHull(hand[palm_ids])
        c_palm = tuple(np.clip(SKIN_MID, 0, 255).astype(int).tolist())
        cv2.fillConvexPoly(canvas, hull, c_palm)

        # Fingers with tapering thickness
        for finger in FINGERS:
            segs = len(finger) - 1
            for i in range(segs):
                t = (i + 1) / segs
                seg_color = SKIN_DARK * (1 - t*0.3) + SKIN_LIGHT * (t*0.3)
                c = tuple(np.clip(seg_color, 0, 255).astype(int).tolist())
                thickness = max(2, 5 - i)
                cv2.line(canvas,
                         tuple(hand[finger[i]]),
                         tuple(hand[finger[i+1]]),
                         c, thickness, cv2.LINE_AA)
            # Fingertip
            tip = tuple(hand[finger[-1]])
            cv2.circle(canvas, tip, 3,
                       tuple(np.clip(SKIN_LIGHT, 0, 255).astype(int).tolist()),
                       -1, cv2.LINE_AA)


# ─────────────────────────────────────────────
# MediaPipe Constants
# ─────────────────────────────────────────────

def _build_constants():
    mp_pose = mp.solutions.pose
    PL      = mp_pose.PoseLandmark
    mp_face = mp.solutions.face_mesh
    IDX     = {n: PL[n].value for n in PL.__members__}
    CONTOURS = mp_face.FACEMESH_TESSELATION
    FINGERS  = [[0,1,2,3,4],[0,5,6,7,8],[0,9,10,11,12],[0,13,14,15,16],[0,17,18,19,20]]
    return IDX, FINGERS, CONTOURS


# ─────────────────────────────────────────────
# Keypoint Interpolation
# ─────────────────────────────────────────────

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
                'id':         p1['id'],
                'x':          p1['x']*(1-t) + p2['x']*t,
                'y':          p1['y']*(1-t) + p2['y']*t,
                'z':          p1.get('z',0)*(1-t) + p2.get('z',0)*t,
                'visibility': p1.get('visibility',1)*(1-t) + p2.get('visibility',1)*t
            })
        interp[key] = pts
    return interp


# ─────────────────────────────────────────────
# Generate from Single JSON
# ─────────────────────────────────────────────

def generate_skeleton_video(input_json, output_video="out.mp4",
                             fps=30, width=640, height=480):
    with open(input_json, 'r') as f:
        frames = json.load(f)
    IDX, FINGERS, CONTOURS = _build_constants()
    out = cv2.VideoWriter(output_video, cv2.VideoWriter_fourcc(*'MJPG'),
                          fps, (width, height))
    draw = partial(draw_frame_data, width=width, height=height,
                   IDX=IDX, FINGERS=FINGERS, CONTOURS=CONTOURS)
    for fd in frames:
        canvas = np.zeros((height, width, 3), np.uint8)
        draw(fd, canvas)
        out.write(canvas)
    out.release()
    print(f"✅ Saved: {output_video}")


# ─────────────────────────────────────────────
# Batch Generator with Trim & Interpolation
# ─────────────────────────────────────────────

def generate_from_phrase(phrase, json_dir, output_video,
                          fps=30, width=640, height=480,
                          interp_frames=12, trim=20):
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

    IDX, FINGERS, CONTOURS = _build_constants()
    out = cv2.VideoWriter(output_video, cv2.VideoWriter_fourcc(*'MJPG'),
                          fps, (width, height))
    draw = partial(draw_frame_data, width=width, height=height,
                   IDX=IDX, FINGERS=FINGERS, CONTOURS=CONTOURS)

    prev_last = None
    total = len(paths)

    for idx, p in enumerate(paths):
        with open(p) as f:
            frames = json.load(f)
        start   = 0 if idx == 0 else trim
        end     = len(frames) if idx == total-1 else max(start, len(frames)-trim)
        segment = frames[start:end]

        if prev_last and segment:
            for j in range(1, interp_frames+1):
                t = j / (interp_frames+1)
                inter  = interpolate_keypoints(prev_last, segment[0], t)
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
    print(f"✅ Generated '{output_video}' trim={trim} interp={interp_frames}")


if __name__ == '__main__':
    generate_skeleton_video(
        input_json=r"C:\Users\comp\Downloads\idle2.json",
        output_video=r"C:\Users\comp\Videos\dp\sign-language-translation-system\ui\idle.mp4",
        fps=30,
        width=640,
        height=480
    )