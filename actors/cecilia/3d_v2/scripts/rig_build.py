"""Milestone 7: the armature (run in Blender).

Builds CEC_rig: deform bones placed from the model's own measurements, IK
arms and legs, finger and thumb chains, head and eyes, hair, neckerchief and
skirt chains, and the tachi's sockets (hip, right hand, both hands).

Conventions (cfg.py): 1 unit = 1 m, Z up, she faces -Y, her LEFT is +X.
Bone names end in .L / .R for her left / right (Blender's mirror tools read
them). Limb bones are rolled "Z up / Z forward", so on both sides a positive
local-X rotation lifts a finger / the hand / the forearm, and a negative one
curls it towards the palm.

Where the joints are (sheet px -> m with cfg.PX = 2.32 mm):
  shoulder  x 0.110 (2-3 cm inside the jacket's shoulder edge, x 0.133),
            arm axis z 1.222, y = profiles arm_axis_y (0.027)
  elbow     x 0.280: just above the rolled cuff (sheet cols 121-149 from the
            centre); set 1 cm back so the IK knows which way it bends
  wrist     x 0.445: where the glove starts (build_clothes.WRIST_U)
  knuckles  x 0.527: 8 mm inside the palm's end (KNUCKLE_U), finger joints
            at 45 / 75 % of each finger
  hip       x 0.085, y 0.035, z 0.800: leg centre line at the top of the leg
  knee      z 0.490 (sheet knee 0.476 / 0.488 / 0.502 front / back / side);
            2 cm forward of the hip-ankle line (bend direction)
  ankle     z 0.095, the leg centre line where it enters the shoe
  spine     y 0.03 (behind the torso's mid-depth): pelvis 0.86, spine 0.97,
            chest 1.09, neck 1.245, head 1.31 (chin 1.287)
  eyes      x +-0.046, z 1.369 (face_texture.eye_extents), pivot 5 cm in
Hair, skirt and neckerchief chains follow the meshes (measured here at run
time); the tachi's bones follow its traced centre lines (profiles_m2.json).

Sword system (custom properties on the rig object, drivers do the rest):
  sword  0 = in the sheath, 1 = right hand (socket_hand.R), 2 = both hands
           (right hand socket + left hand on the hilt below it)
  sheath 0 = on the left hip (socket_hip), 1 = held: follows the free
           control sheath_hold (her idle stance holds the sheathed tachi
           across her hips)
  hand_L 0 = its own IK control, 1 = on the hilt (grip.L)
  hand_R 0 = its own IK control, 1 = on the sheath (grip_sheath.R)
The hilt follows the sheet's bent angle while the sheathed tachi hangs at the
hip and swings straight in line with the blade when drawn or held (hilt ->
hilt_straight; idle1 draws the held tachi straight).
Run: import runpy; runpy.run_path(r"<3d_v2>\\scripts\\rig_build.py")["build"]()
"""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cfg  # noqa: E402

RIG = "CEC_rig"
P = cfg.PX
COLL = "RIG"

# ----------------------------------------------------------------------------- joints (her right; left = mirror)
SHOULDER_X, ELBOW_X, WRIST_X, KNUCKLE_X = 0.110, 0.280, 0.445, 0.527
ARM_Z = 1.222
ELBOW_BACK = 0.010                    # elbow joint behind the arm line: IK bend direction
CLAVICLE_IN = (0.020, 0.030, 1.240)   # clavicle root (her right: x negated)
HIP = (0.085, 0.035, 0.800)
KNEE_Z, ANKLE_Z = 0.490, 0.095
KNEE_FORWARD = 0.020                  # knee joint in front of the hip-ankle line
BALL = (0.163, -0.045, 0.030)         # ball of the foot (shoe: toe at y -0.100, heel +0.137)
TOE_TIP = (0.165, -0.098, 0.030)
SPINE_Y = 0.030
SPINE_Z = dict(pelvis=0.860, spine=0.970, chest=1.090, neck=1.245, head=1.310, head_top=1.500)
FINGER_SPLIT = (0.45, 0.75)           # finger joints at these fractions from the knuckle
EYE_DEPTH = 0.050                     # eye pivot behind the eye surface
HAIR_CHAINS = {"front": 50.0, "side": 95.0, "back_side": 140.0}   # azimuth (deg from the front), mirrored; + back
SKIRT_AZ = [0, 45, 90, 135, 180]      # deg from the front, 45..135 mirrored
SKIRT_Z = (0.990, 0.870, 0.750)       # chain root (waistband), mid, hem
TORSO_C = (0.0, 0.030)                # skirt / torso axis (x, y)
HAIR_C = (0.0, 0.020)


def _mirror(p):
    return (-p[0], p[1], p[2])


def _r(p):
    """her right-side point from a +x description"""
    return (-abs(p[0]), p[1], p[2])


def _load_profiles():
    with open(os.path.join(cfg.REFS, "profiles_m2.json")) as fh:
        return json.load(fh)


def _world_verts(name):
    ob = bpy.data.objects[name]
    return np.array([ob.matrix_world @ v.co for v in ob.data.vertices])


def _leg_line(d2):
    """leg centre line (x, y) at height z, her right leg, from the M2 rings"""
    L = np.array(d2["legs"]["R"])
    L = L[np.argsort(L[:, 0])]

    def at(z):
        return (float(np.interp(z, L[:, 0], 0.5 * (L[:, 1] + L[:, 2]))),
                float(np.interp(z, L[:, 0], 0.5 * (L[:, 3] + L[:, 4]))))
    return at


def _radius(verts, z, az_deg, centre, dz=0.006, half=10.0, outer=True):
    m = np.abs(verts[:, 2] - z) < dz
    p = verts[m]
    if len(p) == 0:
        return None
    ang = np.degrees(np.arctan2(p[:, 0] - centre[0], -(p[:, 1] - centre[1])))
    rad = np.hypot(p[:, 0] - centre[0], p[:, 1] - centre[1])
    mm = np.abs(((ang - az_deg + 180.0) % 360.0) - 180.0) < half
    if not mm.any():
        return None
    return float(rad[mm].max() if outer else rad[mm].min())


def _polar(az_deg, r, z, centre):
    a = math.radians(az_deg)
    return (centre[0] + r * math.sin(a), centre[1] - r * math.cos(a), z)


# ----------------------------------------------------------------------------- bone table
def bone_table():
    """-> list of dicts: name, head, tail, parent, connect, roll (vector the
    local Z axis is aligned to), deform, coll"""
    import build_clothes as bc
    d2 = _load_profiles()
    leg = _leg_line(d2)
    B = []

    def add(name, head, tail, parent=None, connect=False, roll=(0, 0, 1), deform=True, coll="Body"):
        B.append(dict(name=name, head=tuple(map(float, head)), tail=tuple(map(float, tail)), parent=parent,
                      connect=connect, roll=tuple(map(float, roll)), deform=deform, coll=coll))

    add("root", (0, 0, 0), (0, 0.25, 0), roll=(0, 0, 1), deform=False, coll="Controls")
    add("torso", (0, SPINE_Y, SPINE_Z["pelvis"]), (0, SPINE_Y + 0.18, SPINE_Z["pelvis"]), "root", deform=False,
        coll="Controls")
    add("pelvis", (0, SPINE_Y, SPINE_Z["pelvis"]), (0, SPINE_Y, SPINE_Z["spine"]), "torso", roll=(0, -1, 0))
    add("spine", (0, SPINE_Y, SPINE_Z["spine"]), (0, SPINE_Y, SPINE_Z["chest"]), "pelvis", True, roll=(0, -1, 0))
    add("chest", (0, SPINE_Y, SPINE_Z["chest"]), (0, SPINE_Y + 0.005, SPINE_Z["neck"]), "spine", True, roll=(0, -1, 0))
    add("neck", (0, SPINE_Y + 0.005, SPINE_Z["neck"]), (0, 0.025, SPINE_Z["head"]), "chest", True, roll=(0, -1, 0))
    add("head", (0, 0.025, SPINE_Z["head"]), (0, 0.025, SPINE_Z["head_top"]), "neck", True, roll=(0, -1, 0))

    # ---- arms, hands, fingers
    ay = float(d2["arm_axis_y"])
    fing_tip_x = float(np.abs(np.array(d2["arms"]["R"]["x"])).max())
    names = ("index", "middle", "ring", "pinky")
    for side, sg in (("R", -1.0), ("L", 1.0)):
        def X(p):
            return (sg * abs(p[0]), p[1], p[2])
        sh = X((SHOULDER_X, ay, ARM_Z))
        el = X((ELBOW_X, ay + ELBOW_BACK, ARM_Z))
        wr = X((WRIST_X, ay, ARM_Z + 0.006))
        kn = X((KNUCKLE_X, bc.HAND_YC, ARM_Z + 0.004))
        add("clavicle." + side, X(CLAVICLE_IN), sh, "chest", roll=(0, 0, 1))
        add("upper_arm." + side, sh, el, "clavicle." + side, True, roll=(0, 0, 1))
        add("forearm." + side, el, wr, "upper_arm." + side, True, roll=(0, 0, 1))
        add("hand." + side, wr, kn, "forearm." + side, True, roll=(0, 0, 1))
        zrow = (cfg.VIEWS["front"]["sole_v"] - (bc.FINGER_ROW + 0.5)) * P
        for j, (dy, short, r) in enumerate(bc.FINGERS):
            y = bc.HAND_YC + dy
            z = zrow - dy * bc.FINGER_ROLL - 0.001
            x0, x3 = KNUCKLE_X, fing_tip_x - short
            xs = [x0, x0 + (x3 - x0) * FINGER_SPLIT[0], x0 + (x3 - x0) * FINGER_SPLIT[1], x3]
            par = "hand." + side
            for k in range(3):
                nm = "%s_%02d.%s" % (names[j], k + 1, side)
                add(nm, X((xs[k], y, z)), X((xs[k + 1], y, z - 0.0005 * k)), par, k > 0, roll=(0, 0, 1),
                    coll="Fingers")
                par = nm
        b, t_ = bc.THUMB["base"], bc.THUMB["tip"]
        fx = lambda u: (u - cfg.VIEWS["front"]["centre_u"]) * P          # noqa: E731
        zed = lambda v: (cfg.VIEWS["front"]["sole_v"] - v) * P             # noqa: E731
        p0 = (abs(fx(b[0])), bc.HAND_YC + b[1], zed(b[2] + 0.5))
        p1 = (abs(fx(t_[0])), bc.HAND_YC + t_[1], zed(t_[2] + 0.5))
        pm = tuple(0.5 * (a + c) for a, c in zip(p0, p1))
        pc = (WRIST_X + 0.030, bc.HAND_YC - 0.010, ARM_Z - 0.004)      # thumb root inside the palm
        add("thumb_01." + side, X(pc), X(p0), "hand." + side, roll=(0, -1, 0), coll="Fingers")
        add("thumb_02." + side, X(p0), X(pm), "thumb_01." + side, True, roll=(0, -1, 0), coll="Fingers")
        add("thumb_03." + side, X(pm), X(p1), "thumb_02." + side, True, roll=(0, -1, 0), coll="Fingers")
        # IK controls: copies of the hand's rest frame; poles behind the elbows
        add("hand_ik." + side, wr, kn, "root", roll=(0, 0, 1), deform=False, coll="Controls")
        add("elbow_pole." + side, X((ELBOW_X, ay + 0.40, ARM_Z)), X((ELBOW_X, ay + 0.45, ARM_Z)), "root",
            deform=False, coll="Controls")

    # ---- legs
    for side, sg in (("R", -1.0), ("L", 1.0)):
        def X(p):
            return (sg * abs(p[0]), p[1], p[2])
        hip = X(HIP)
        ax_, ay_ = leg(ANKLE_Z)
        ankle = X((abs(ax_), ay_, ANKLE_Z))
        kx, ky = leg(KNEE_Z)
        # knee: on the leg's own centre line in x, KNEE_FORWARD in front of the hip-ankle line in y
        t = (HIP[2] - KNEE_Z) / (HIP[2] - ANKLE_Z)
        y_line = HIP[1] + (ay_ - HIP[1]) * t
        knee = X((abs(kx), y_line - KNEE_FORWARD, KNEE_Z))
        add("thigh." + side, hip, knee, "pelvis", roll=(0, -1, 0))
        add("shin." + side, knee, ankle, "thigh." + side, True, roll=(0, -1, 0))
        add("foot." + side, ankle, X(BALL), "shin." + side, True, roll=(0, 0, 1))
        add("toe." + side, X(BALL), X(TOE_TIP), "foot." + side, True, roll=(0, 0, 1))
        add("foot_ik." + side, ankle, X(BALL), "root", roll=(0, 0, 1), deform=False, coll="Controls")
        add("knee_pole." + side, X((abs(kx), -0.45, KNEE_Z)), X((abs(kx), -0.50, KNEE_Z)), "root", deform=False,
            coll="Controls")

    # ---- head: eyes, hair, bangs, ahoge
    import face_texture as ft
    ext = ft.eye_extents()
    face = _world_verts("face")
    for side, key in (("R", "R"), ("L", "L")):
        e = ext[key]
        u = 0.5 * (e["inner"] + e["outer"])
        x = (u - cfg.VIEWS["front"]["centre_u"]) * P
        z = (cfg.VIEWS["front"]["sole_v"] - 0.5 * (e["top"] + e["bottom"])) * P
        near = face[(np.abs(face[:, 0] - x) < 0.004) & (np.abs(face[:, 2] - z) < 0.004)]
        ys = float(near[:, 1].min()) if len(near) else -0.075
        add("eye." + side, (x, ys + EYE_DEPTH, z), (x, ys + EYE_DEPTH - 0.025, z), "head", roll=(0, 0, 1),
            deform=False, coll="Face")
    eye_z = B[-1]["head"][2]
    add("eyes_target", (0, -0.45, eye_z), (0, -0.48, eye_z), "head", roll=(0, 0, 1), deform=False, coll="Face")
    hair = _world_verts("hair")
    chains = [("hair_back", 180.0)]
    for nm, az in HAIR_CHAINS.items():
        chains += [("hair_%s.L" % nm, az), ("hair_%s.R" % nm, -az)]
    for nm, az in chains:
        r0 = (_radius(hair, 1.43, az, HAIR_C, outer=False) or 0.11) - 0.010
        r1 = (_radius(hair, 1.36, az, HAIR_C, outer=False) or 0.13) - 0.008
        r2 = (_radius(hair, 1.295, az, HAIR_C, outer=False) or 0.12) - 0.004
        p0, p1, p2 = _polar(az, r0, 1.43, HAIR_C), _polar(az, r1, 1.36, HAIR_C), _polar(az, r2, 1.295, HAIR_C)
        base, side = (nm.split(".") + [""])[:2]
        n1 = base + "_01" + ("." + side if side else "")
        n2 = base + "_02" + ("." + side if side else "")
        out = _polar(az, 1.0, 0.0, (0, 0))
        add(n1, p0, p1, "head", roll=(out[0], out[1], 0), coll="Hair")
        add(n2, p1, p2, n1, True, roll=(out[0], out[1], 0), coll="Hair")
    bangs = _world_verts("bangs")
    yb = float(bangs[:, 1].min())
    add("bangs", (0, yb + 0.030, 1.455), (0, yb + 0.008, 1.385), "head", roll=(0, -1, 0), coll="Hair")
    ah = _world_verts("ahoge")
    a0 = ah[np.argmin(ah[:, 2])]
    a2 = ah[np.argmax(np.hypot(ah[:, 0] - a0[0], ah[:, 1] - a0[1]) + (ah[:, 2] - a0[2]))]
    a1 = ah[np.argmax(ah[:, 2])]
    add("ahoge_01", a0, a1, "head", roll=(0, -1, 0), coll="Hair")
    add("ahoge_02", a1, a2 if np.linalg.norm(a2 - a1) > 0.008 else a1 + np.array([0.01, -0.005, -0.004]), "ahoge_01",
        True, roll=(0, -1, 0), coll="Hair")

    # ---- neckerchief: knot + two tails
    nk = _world_verts("neckerchief")
    add("neckerchief", (0, -0.050, 1.205), (0, -0.068, 1.180), "chest", roll=(0, -1, 0), coll="Cloth")
    for side, sg in (("R", -1.0), ("L", 1.0)):
        pts = []
        for z in (1.180, 1.125, 1.068):
            m = (np.abs(nk[:, 2] - z) < 0.006) & (nk[:, 0] * sg > 0.002)
            p = nk[m]
            pts.append((float(p[:, 0].mean()), float(p[:, 1].mean()) + 0.004, z))
        add("scarf_tail_01." + side, pts[0], pts[1], "neckerchief", roll=(0, -1, 0), coll="Cloth")
        add("scarf_tail_02." + side, pts[1], pts[2], "scarf_tail_01." + side, True, roll=(0, -1, 0), coll="Cloth")

    # ---- skirt: chains round the waist, roots at the waistband, tips at the hem
    sk = _world_verts("skirt")
    for az0 in SKIRT_AZ:
        for az in ((az0,) if az0 in (0, 180) else (az0, -az0)):
            nm = {0: "front", 45: "front", 90: "side", 135: "back", 180: "back"}[abs(az)]
            suffix = "" if az in (0, 180) else (".L" if az > 0 else ".R")
            pts = []
            for k, z in enumerate(SKIRT_Z):
                r = _radius(sk, z, az, TORSO_C) or 0.12
                pts.append(_polar(az, r - (0.012, 0.008, 0.004)[k], z, TORSO_C))
            n1, n2 = "skirt_%s_01%s" % (nm, suffix), "skirt_%s_02%s" % (nm, suffix)
            if az0 == 45:
                n1, n2 = "skirt_frontside_01%s" % suffix, "skirt_frontside_02%s" % suffix
            if az0 == 135:
                n1, n2 = "skirt_backside_01%s" % suffix, "skirt_backside_02%s" % suffix
            if az0 == 90:
                n1, n2 = "skirt_side_01%s" % suffix, "skirt_side_02%s" % suffix
            fwd = (0, -1, 0)
            add(n1, pts[0], pts[1], "pelvis", roll=fwd, coll="Skirt")
            add(n2, pts[1], pts[2], n1, True, roll=fwd, coll="Skirt")
            B[-2]["az"] = B[-1]["az"] = az

    # ---- tachi
    H = np.array([p[:3] for p in d2["sword"]["hilt"]])       # cap end -> guard
    S_ = np.array([p[:3] for p in d2["sword"]["sheath"]])    # mouth -> tip
    mouth, tip = S_[0], S_[-1]
    # curvature normal of the sheath (the side it bends towards): the bone's Z axis
    mid = S_[len(S_) // 2]
    chord = (tip - mouth) / np.linalg.norm(tip - mouth)
    bow = (mid - mouth) - chord * ((mid - mouth) @ chord)
    bow = -bow / max(np.linalg.norm(bow), 1e-9)               # concave side
    blade_dir = S_[3] - S_[0]
    blade_dir /= np.linalg.norm(blade_dir)
    sheath_len = float(np.linalg.norm(tip - mouth))
    add("sheath", mouth, mouth + chord * sheath_len, "root", roll=bow, deform=False, coll="Sword")
    add("socket_hip", mouth, mouth + chord * sheath_len, "pelvis", roll=bow, deform=False, coll="Mechanism")
    add("sheath_hold", mouth, mouth + chord * sheath_len, "root", roll=bow, deform=False, coll="Controls")
    blade_len = 0.29
    add("sword", mouth, mouth + blade_dir * blade_len, "root", roll=bow, deform=False, coll="Sword")
    add("sword_slot", mouth, mouth + blade_dir * blade_len, "sheath", roll=bow, deform=False, coll="Mechanism")
    hilt_len = float(np.linalg.norm(H[0] - H[-1]))
    hilt_dir = (H[0] - H[-1]) / hilt_len
    n_bend = np.cross(hilt_dir, -blade_dir)
    n_bend = n_bend / max(np.linalg.norm(n_bend), 1e-9)
    add("hilt", H[-1], H[-1] + hilt_dir * hilt_len, "sword", roll=n_bend, deform=False, coll="Sword")
    add("hilt_straight", H[-1], H[-1] - blade_dir * hilt_len, "sword", roll=n_bend, deform=False, coll="Mechanism")
    return B, dict(blade_dir=blade_dir, hilt_dir=hilt_dir, mouth=mouth, bow=bow, hilt_len=hilt_len,
                   bend_deg=float(np.degrees(np.arccos(np.clip(hilt_dir @ -blade_dir, -1, 1)))))


# ----------------------------------------------------------------------------- sockets computed from the hand
GRIP = dict(x=0.541, z_below=0.034, guard_gap=0.016, spacing=0.066)
# the right fist: the hilt runs through the curled fingers (front-back in the
# T-pose hand), GRIP x along the hand from the centre line, z_below under the
# knuckle line; the guard sits guard_gap in front of the index finger, the
# blade points forward (out of the thumb side), its concave side up. The left
# hand on the hilt is that grip mirrored through the blade's plane and moved
# `spacing` towards the pommel (a hand's width less a little: the sheet's
# hilt is 9.6 cm, so two fists only just fit, the left one over the cap).


def socket_frames(eb, info):
    """rest matrices (armature space) for socket_hand.R, grip.L and
    grip_sheath.R, from the right hand's rest frame"""
    import build_clothes as bc
    hand = eb["hand.R"]
    y_index = bc.HAND_YC + bc.FINGERS[0][0] - bc.FINGERS[0][2]
    head = Vector((-GRIP["x"], y_index - GRIP["guard_gap"], hand.head.z - GRIP["z_below"]))
    Ys = Vector((0, -1, 0))                                   # blade forward
    Zs = Vector((0, 0, 1))                                    # concave side up
    Xs = Ys.cross(Zs)
    sock = Matrix((Xs, Ys, Zs)).transposed().to_4x4()
    sock.translation = head
    # sword bone rest frame
    sw = eb["sword"].matrix.copy()
    H_R = hand.matrix.copy()
    # hand -> sword relation while gripping: sword_world = hand_world @ T
    T = H_R.inverted() @ sock
    # left hand on the hilt: mirror the gripping right hand through the
    # sword's blade plane (normal = sword X), then slide towards the pommel
    S_ = sock
    n = S_.col[0].to_3d().normalized()
    p0 = S_.translation.copy()
    Hgrip = S_ @ T.inverted()                                 # right hand frame while gripping (world)
    Xr, Yr, Zr = (Hgrip.col[i].to_3d() for i in range(3))
    def refl(v):
        return v - 2.0 * v.dot(n) * n
    pos = Hgrip.translation.copy()
    pos_m = pos - 2.0 * (pos - p0).dot(n) * n
    XL, YL, ZL = -refl(Xr), refl(Yr), refl(Zr)
    pos_m = pos_m + (-S_.col[1].to_3d().normalized()) * GRIP["spacing"]
    gL = Matrix((XL, YL, ZL)).transposed().to_4x4()
    gL.translation = pos_m
    # in the sword's frame (so the bone can live under the hilt / sword)
    grip_L_rel = sock.inverted() @ gL
    return dict(socket=sock, T=T, grip_L_world_from_socket=grip_L_rel, sword_rest=sw)


# ----------------------------------------------------------------------------- build
def _set_bone_from_matrix(b, M, length):
    b.head = M.translation
    b.tail = M.translation + M.col[1].to_3d().normalized() * length
    b.align_roll(M.col[2].to_3d())


def _widgets():
    wc = bpy.data.collections.get("WGT")
    if wc is None:
        wc = bpy.data.collections.new("WGT")
        bpy.context.scene.collection.children.link(wc)
    wc.hide_render = True
    wc.hide_viewport = True
    out = {}

    def mk(name, verts, edges):
        ob = bpy.data.objects.get(name)
        if ob is None:
            me = bpy.data.meshes.new(name)
            me.from_pydata(verts, edges, [])
            ob = bpy.data.objects.new(name, me)
            wc.objects.link(ob)
        out[name] = ob
    n = 24
    circ = [(math.cos(2 * math.pi * k / n), 0.0, math.sin(2 * math.pi * k / n)) for k in range(n)]
    mk("WGT_circle", circ, [(k, (k + 1) % n) for k in range(n)])
    cube = [(x, y, z) for x in (-1, 1) for y in (0, 2) for z in (-1, 1)]
    ce = [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]
    mk("WGT_box", [(0.5 * a, 0.5 * b, 0.5 * c) for a, b, c in cube], ce)
    sph = []
    edges = []
    for ax in range(3):
        base = len(sph)
        for k in range(n):
            a = 2 * math.pi * k / n
            v = [0.0, 0.0, 0.0]
            v[(ax + 1) % 3], v[(ax + 2) % 3] = math.cos(a), math.sin(a)
            sph.append(tuple(v))
            edges.append((base + k, base + (k + 1) % n))
    mk("WGT_sphere", [(0.5 * a, 0.5 * b + 0.5, 0.5 * c) for a, b, c in sph], edges)
    return out


def _pole_angle(base_bone, ik_bone, pole_loc):
    def signed(u, v, normal):
        a = u.angle(v)
        return -a if u.cross(v).dot(normal) < 0 else a
    pole_normal = (ik_bone.tail - base_bone.head).cross(pole_loc - base_bone.head)
    proj = pole_normal.cross(base_bone.tail - base_bone.head)
    return signed(base_bone.x_axis, proj, base_bone.tail - base_bone.head)


def _rest_error(rig, base, tip):
    """how far the IK chain moves away from its rest pose, mm + deg of twist"""
    e = 0.0
    for n in (base, tip):
        pb, b = rig.pose.bones[n], rig.data.bones[n]
        d = b.matrix_local.inverted() @ pb.matrix
        e += (pb.tail - b.tail_local).length * 1000.0 + abs(math.degrees(d.to_euler()[1]))
    return e


def fit_poles(rig, poles):
    """the textbook pole-angle formula gets the sign wrong for the legs (a
    180 deg twist at rest); try the four candidates and keep the one that
    leaves the chain at rest, then refine in 0.1 deg steps"""
    out = {}
    chains = [("upper_arm", "forearm", "arm"), ("thigh", "shin", "leg")]
    for side in ("R", "L"):
        for base, tip, key in chains:
            c = rig.pose.bones["%s.%s" % (tip, side)].constraints["IK"]
            a = poles["%s.%s" % (key, side)]
            best = None
            for cand in (a, -a, a + math.pi, -a + math.pi):
                c.pole_angle = cand
                bpy.context.view_layer.update()
                e = _rest_error(rig, base + "." + side, tip + "." + side)
                if best is None or e < best[0]:
                    best = (e, cand)
            a0 = best[1]
            for d in range(-30, 31):
                cand = a0 + math.radians(d * 0.1)
                c.pole_angle = cand
                bpy.context.view_layer.update()
                e = _rest_error(rig, base + "." + side, tip + "." + side)
                if e < best[0]:
                    best = (e, cand)
            c.pole_angle = best[1]
            bpy.context.view_layer.update()
            out["%s.%s" % (key, side)] = best[1]
            out["%s.%s err" % (key, side)] = best[0]
    return out


def _driver(rig, owner, path, expr, props, index=-1):
    fc = owner.driver_add(path, index) if index >= 0 else owner.driver_add(path)
    d = fc.driver
    d.type = "SCRIPTED"
    for k in list(d.variables):
        d.variables.remove(k)
    for p in props:
        v = d.variables.new()
        v.name = p
        v.type = "SINGLE_PROP"
        v.targets[0].id_type = "OBJECT"
        v.targets[0].id = rig
        v.targets[0].data_path = '["%s"]' % p
    d.expression = expr
    return fc


def rest_world(o):
    """o's world matrix with its parent rig at the rest pose, whatever the
    current pose (never read matrix_world here: a posed rig would bake its
    pose into the part's rest transform)"""
    p = o.parent
    if p is None:
        return o.matrix_basis.copy()
    if o.parent_type == "BONE" and p.type == "ARMATURE" and o.parent_bone in p.data.bones:
        b = p.data.bones[o.parent_bone]
        P = p.matrix_world @ b.matrix_local @ Matrix.Translation((0.0, b.length, 0.0))
    else:
        P = p.matrix_world
    return P @ o.matrix_parent_inverse @ o.matrix_basis


def _remove_old():
    ob = bpy.data.objects.get(RIG)
    if ob is not None:
        for o in bpy.data.objects:
            if o.parent == ob:
                mw = rest_world(o)
                o.parent = None
                o.matrix_parent_inverse = Matrix.Identity(4)
                o.matrix_basis = mw
            for m in list(getattr(o, "modifiers", [])):
                if m.type == "ARMATURE" and m.object == ob:
                    o.modifiers.remove(m)
        arm = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        if arm is not None and arm.users == 0:
            bpy.data.armatures.remove(arm)


def build():
    _remove_old()
    coll = bpy.data.collections.get(COLL)
    if coll is None:
        coll = bpy.data.collections.new(COLL)
        bpy.context.scene.collection.children.link(coll)
    for sc in bpy.data.scenes:                                # every scene evaluates the rig
        if sc.collection.children.get(COLL) is None:
            try:
                sc.collection.children.link(coll)
            except RuntimeError:
                pass
    arm = bpy.data.armatures.new(RIG)
    rig = bpy.data.objects.new(RIG, arm)
    coll.objects.link(rig)
    arm.display_type = "OCTAHEDRAL"
    rig.show_in_front = True
    table, info = bone_table()
    vl = bpy.context.view_layer
    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for o in vl.objects:
        o.select_set(False)
    vl.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.edit_bones
    for b in table:
        e = eb.new(b["name"])
        e.head, e.tail = Vector(b["head"]), Vector(b["tail"])
        e.align_roll(Vector(b["roll"]))
        e.use_deform = b["deform"]
    for b in table:
        if b["parent"]:
            e = eb[b["name"]]
            e.parent = eb[b["parent"]]
            e.use_connect = b["connect"]
    # sockets from the hand frame
    sf = socket_frames(eb, info)
    e = eb.new("socket_hand.R")
    _set_bone_from_matrix(e, sf["socket"], eb["sword"].length)
    e.parent = eb["hand.R"]
    e.use_deform = False
    g = eb.new("grip.L")
    # grip.L hangs under the hilt, which is bent at rest and straight when
    # drawn: its rest is chosen so that it lands on the straight hilt
    M = (eb["hilt"].matrix @ eb["hilt_straight"].matrix.inverted() @ eb["sword"].matrix
         @ sf["grip_L_world_from_socket"])
    _set_bone_from_matrix(g, M, eb["hand.L"].length)
    g.parent = eb["hilt"]
    g.use_deform = False
    # the right hand on the sheath, 30 % down from the mouth: the same fist
    # relation as on the hilt
    sh = eb["sheath"]
    frame = sh.matrix.copy()
    frame.translation = sh.head + (sh.tail - sh.head) * 0.30
    gs = eb.new("grip_sheath.R")
    _set_bone_from_matrix(gs, frame @ sf["T"].inverted(), eb["hand.R"].length)
    gs.parent = sh
    gs.use_deform = False
    # pole angles (rest pose preserved)
    poles = {}
    for side in ("R", "L"):
        poles["arm." + side] = _pole_angle(eb["upper_arm." + side], eb["forearm." + side],
                                           eb["elbow_pole." + side].head)
        poles["leg." + side] = _pole_angle(eb["thigh." + side], eb["shin." + side], eb["knee_pole." + side].head)
    bpy.ops.object.mode_set(mode="POSE")
    # ---- bone collections + colours
    colls = {}
    for b in table + [dict(name=n, coll="Mechanism") for n in ("socket_hand.R", "grip.L", "grip_sheath.R")]:
        cn = b["coll"]
        if cn not in colls:
            colls[cn] = arm.collections.new(cn)
        colls[cn].assign(arm.bones[b["name"]])
    if "Mechanism" in colls:
        colls["Mechanism"].is_visible = False
    palette = {"Controls": "THEME09", "Fingers": "THEME03", "Hair": "THEME07", "Skirt": "THEME05",
               "Cloth": "THEME06", "Sword": "THEME11", "Face": "THEME02"}
    for b in table:
        pb = rig.pose.bones[b["name"]]
        pb.rotation_mode = "XYZ"
        th = palette.get(b["coll"])
        if th:
            pb.color.palette = th
    # ---- widgets
    W = _widgets()
    shapes = {"root": ("WGT_circle", 1.0), "torso": ("WGT_circle", 1.2), "sheath_hold": ("WGT_circle", 0.6),
              "eyes_target": ("WGT_box", 0.6)}
    for side in ("R", "L"):
        shapes["hand_ik." + side] = ("WGT_box", 0.9)
        shapes["foot_ik." + side] = ("WGT_box", 0.9)
        shapes["elbow_pole." + side] = ("WGT_sphere", 0.8)
        shapes["knee_pole." + side] = ("WGT_sphere", 0.8)
    for nm, (w, s) in shapes.items():
        pb = rig.pose.bones[nm]
        pb.custom_shape = W[w]
        pb.custom_shape_scale_xyz = (s, s, s)
    # ---- IK
    for side in ("R", "L"):
        c = rig.pose.bones["forearm." + side].constraints.new("IK")
        c.name = "IK"
        c.target, c.subtarget = rig, "hand_ik." + side
        c.pole_target, c.pole_subtarget = rig, "elbow_pole." + side
        c.pole_angle = poles["arm." + side]
        c.chain_count = 2
        c = rig.pose.bones["hand." + side].constraints.new("COPY_ROTATION")
        c.name = "IK rotation"
        c.target, c.subtarget = rig, "hand_ik." + side
        c = rig.pose.bones["shin." + side].constraints.new("IK")
        c.name = "IK"
        c.target, c.subtarget = rig, "foot_ik." + side
        c.pole_target, c.pole_subtarget = rig, "knee_pole." + side
        c.pole_angle = poles["leg." + side]
        c.chain_count = 2
        c = rig.pose.bones["foot." + side].constraints.new("COPY_ROTATION")
        c.name = "IK rotation"
        c.target, c.subtarget = rig, "foot_ik." + side
    # ---- eyes
    for side in ("R", "L"):
        c = rig.pose.bones["eye." + side].constraints.new("DAMPED_TRACK")
        c.target, c.subtarget = rig, "eyes_target"
        c.track_axis = "TRACK_Y"
    # ---- skirt follows the thighs (part of each thigh's swing, by azimuth)
    for b in table:
        if not b["name"].startswith("skirt_") or "_01" not in b["name"]:
            continue
        az = b.get("az", 0.0)
        pb = rig.pose.bones[b["name"]]
        for side, a_leg in (("R", -90.0), ("L", 90.0)):
            w = 0.5 * (0.5 * (1.0 + math.cos(math.radians(az - a_leg)))) ** 1.5
            if w < 0.02:
                continue
            c = pb.constraints.new("COPY_ROTATION")
            c.name = "follow thigh." + side
            c.target, c.subtarget = rig, "thigh." + side
            c.use_y = False
            c.mix_mode = "ADD"
            c.target_space = "LOCAL_OWNER_ORIENT"
            c.owner_space = "LOCAL"
            c.influence = w
    # ---- tachi switches
    for k, v, lo, hi, desc in (("sword", 0, 0, 2, "0 in the sheath, 1 right hand, 2 both hands"),
                               ("sheath", 0, 0, 1, "0 on the left hip, 1 held (follows sheath_hold)"),
                               ("hand_L", 0, 0, 1, "left hand: 0 own IK control, 1 on the hilt"),
                               ("hand_R", 0, 0, 1, "right hand: 0 own IK control, 1 on the sheath")):
        rig[k] = v
        ui = rig.id_properties_ui(k)
        ui.update(min=lo, max=hi, soft_min=lo, soft_max=hi, description=desc)
    pb = rig.pose.bones["sheath"]
    c = pb.constraints.new("COPY_TRANSFORMS")
    c.name = "on hip"
    c.target, c.subtarget = rig, "socket_hip"
    c = pb.constraints.new("COPY_TRANSFORMS")
    c.name = "held"
    c.target, c.subtarget = rig, "sheath_hold"
    _driver(rig, c, "influence", "sheath", ["sheath"])
    pb = rig.pose.bones["sword"]
    c = pb.constraints.new("COPY_TRANSFORMS")
    c.name = "sheathed"
    c.target, c.subtarget = rig, "sword_slot"
    c = pb.constraints.new("COPY_TRANSFORMS")
    c.name = "in hand"
    c.target, c.subtarget = rig, "socket_hand.R"
    _driver(rig, c, "influence", "1.0 if sword >= 1 else 0.0", ["sword"])
    pb = rig.pose.bones["hilt"]
    c = pb.constraints.new("COPY_TRANSFORMS")
    c.name = "straight"
    c.target, c.subtarget = rig, "hilt_straight"
    # bent only while the sheathed tachi hangs at the hip (the sheet's
    # drawing); straight when drawn or when the sheathed tachi is held (idle1)
    _driver(rig, c, "influence", "1.0 if (sword >= 1 or sheath == 1) else 0.0", ["sword", "sheath"])
    # the blade renders only when drawn (sheathed it would poke through the
    # sheath's curve: M4 hid it)
    blade = bpy.data.objects.get("blade")
    if blade is not None:
        blade.driver_remove("hide_render")
        _driver(rig, blade, "hide_render", "1.0 if sword == 0 else 0.0", ["sword"])
    pb = rig.pose.bones["hand_ik.L"]
    c = pb.constraints.new("COPY_TRANSFORMS")
    c.name = "on hilt"
    c.target, c.subtarget = rig, "grip.L"
    _driver(rig, c, "influence", "1.0 if (hand_L == 1 or sword == 2) else 0.0", ["hand_L", "sword"])
    pb = rig.pose.bones["hand_ik.R"]
    c = pb.constraints.new("COPY_TRANSFORMS")
    c.name = "on sheath"
    c.target, c.subtarget = rig, "grip_sheath.R"
    _driver(rig, c, "influence", "1.0 if hand_R == 1 else 0.0", ["hand_R"])
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.select_set(False)
    poles = fit_poles(rig, poles)
    out = dict(bones=len(arm.bones), deform=sum(1 for b in arm.bones if b.use_deform),
               poles={k: round(math.degrees(v), 2) if not k.endswith("err") else round(v, 3) for k, v in poles.items()},
               hilt_bend_deg=round(info["bend_deg"], 1))
    return out


if __name__ == "__main__":
    print(build())
