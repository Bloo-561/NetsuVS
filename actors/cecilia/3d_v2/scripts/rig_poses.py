"""Milestone 7: test poses for the rig (run in Blender, after rig_build.py and
rig_weights.py).

  idle        her idle stance from actors/cecilia/Sprites/idle1.png (a 3/4
              view facing right): deep front-back stance, left foot forward,
              the sheathed tachi held level across the hips (right hand on
              the sheath, left hand on the hilt), chest turned to the camera,
              head turned to screen-right
  draw_slash  two-handed rising slash after the draw: right-foot lunge, the
              sword in both hands up and to her right, the sheath left on the
              hip
  right_hand  the sword drawn in the right hand alone, held out level (the
              right-hand socket)
  rest        the bind pose (sword at the hip)
Poses are set with the rig's controls only (IK targets, poles, the torso
control, FK spine / neck / head / fingers / chains, the sword switches), the
way an animator would. render() writes the review renders.
Run: import runpy; P = runpy.run_path(r"<3d_v2>\\scripts\\rig_poses.py"); P["pose"]("idle")
"""
import math
import os
import sys

import bpy
from mathutils import Euler, Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RIG = "CEC_rig"
LAST = {}                            # diagnostics from the last pose (leg reach, ...)
IDLE_AZ = -40.0                      # camera azimuth for the idle stance (her right-front; she faces screen-right):
                                     # idle1.png shows her chest ~40 deg from the viewer


def rig_obj():
    return bpy.data.objects[RIG]


def update():
    bpy.context.view_layer.update()


def reset(rig=None):
    rig = rig or rig_obj()
    for pb in rig.pose.bones:
        pb.location = (0.0, 0.0, 0.0)
        pb.rotation_euler = (0.0, 0.0, 0.0)
        pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)
    for k in ("sword", "sheath", "hand_L", "hand_R"):
        rig[k] = 0
    rig.data.pose_position = "POSE"
    update()
    return rig


def rot(rig, bone, x=0.0, y=0.0, z=0.0):
    rig.pose.bones[bone].rotation_euler = (math.radians(x), math.radians(y), math.radians(z))


def world(rig, bone):
    return rig.matrix_world @ rig.pose.bones[bone].matrix


def rest(rig, bone):
    return rig.matrix_world @ rig.data.bones[bone].matrix_local


def set_world(rig, bone, M):
    rig.pose.bones[bone].matrix = rig.matrix_world.inverted() @ M
    update()


def frame(y_dir, z_hint, origin):
    """4x4 with Y along y_dir, Z as close to z_hint as possible"""
    Y = Vector(y_dir).normalized()
    Z = Vector(z_hint) - Vector(z_hint).dot(Y) * Y
    Z.normalize()
    X = Y.cross(Z)
    M = Matrix((X, Y, Z)).transposed().to_4x4()
    M.translation = Vector(origin)
    return M


def place(rig, bone, pos):
    """move a control's head to a world position (its rest orientation kept)"""
    R0 = rest(rig, bone)
    M = R0.copy()
    M.translation = Vector(pos)
    set_world(rig, bone, M)


def move_ctrl(rig, bone, offset=(0, 0, 0), yaw=0.0, pivot=None):
    """an IK / root control: its rest frame moved by `offset` (world) and
    turned `yaw` degrees about world Z round its head"""
    R0 = rest(rig, bone)
    head = R0.translation.copy()
    Rz = Matrix.Rotation(math.radians(yaw), 4, "Z")
    M = Matrix.Translation(head + Vector(offset)) @ Rz @ Matrix.Translation(-head) @ R0
    set_world(rig, bone, M)


def fist(rig, side, amount=1.0, thumb=1.0):
    """curl the fingers round a grip (negative local X = towards the palm)"""
    curl = (62.0, 88.0, 52.0)
    for f in ("index", "middle", "ring", "pinky"):
        for k in range(3):
            rot(rig, "%s_%02d.%s" % (f, k + 1, side), x=-curl[k] * amount)
    s = 1.0 if side == "R" else -1.0
    rot(rig, "thumb_01." + side, x=-10.0 * thumb, z=s * 18.0 * thumb)
    rot(rig, "thumb_02." + side, x=-25.0 * thumb)
    rot(rig, "thumb_03." + side, x=-35.0 * thumb)


def leg_reach(rig):
    """{side: distance hip -> ankle target / (thigh + shin)}"""
    out = {}
    for side in ("L", "R"):
        hip = world(rig, "thigh." + side).translation
        ank = world(rig, "foot_ik." + side).translation
        L = rig.data.bones["thigh." + side].length + rig.data.bones["shin." + side].length
        out[side] = (hip - ank).length / L
    return out


def place_foot(rig, side, horiz, yaw=0.0, max_reach=0.98):
    """put a foot's IK control on the floor at the hip's floor point plus
    `horiz` (world x, y), turned `yaw` degrees; pulled in towards the hip if
    the leg could not reach it (the IK would leave the foot short)"""
    hip = world(rig, "thigh." + side).translation
    ank0 = rest(rig, "foot_ik." + side).translation
    L = rig.data.bones["thigh." + side].length + rig.data.bones["shin." + side].length
    h = Vector((horiz[0], horiz[1], 0.0))
    dz = hip.z - ank0.z
    hmax = math.sqrt(max((max_reach * L) ** 2 - dz * dz, 0.0))
    if h.length > hmax:
        h *= hmax / h.length
    target = Vector((hip.x + h.x, hip.y + h.y, ank0.z))
    move_ctrl(rig, "foot_ik." + side, target - ank0, yaw)
    return h.length


def socket_relation(rig):
    """hand.R -> socket_hand.R at rest: sword_world = hand_world @ T"""
    return rig.data.bones["hand.R"].matrix_local.inverted() @ rig.data.bones["socket_hand.R"].matrix_local


def place_sword_in_right_hand(rig, blade_dir, concave_hint, guard_pos, reach=0.94):
    """put hand_ik.R where the right fist must be for the sword (in the
    right-hand socket) to lie along blade_dir with its guard at guard_pos;
    if the wrist would be out of the arm's reach, the sword slides back
    towards the shoulder until it is within `reach` of the arm's length"""
    T = socket_relation(rig)
    S = frame(blade_dir, concave_hint, guard_pos)
    H = S @ T.inverted()
    sh = world(rig, "upper_arm.R").translation
    arm = rig.data.bones["upper_arm.R"].length + rig.data.bones["forearm.R"].length
    d = H.translation - sh
    if d.length > reach * arm:
        shift = d * (reach * arm / d.length - 1.0)
        S.translation = S.translation + shift
        H = S @ T.inverted()
    set_world(rig, "hand_ik.R", rig.matrix_world @ H)
    return S


# ----------------------------------------------------------------------------- poses
def pose_rest(rig):
    reset(rig)
    return rig


IDLE_M7 = dict(
    az=IDLE_AZ,                                   # the camera azimuth the stance is laid out for
    torso_fwd=-0.05, drop=0.215, hips_yaw=0.0,    # hips: along screen-right, down, turned
    front=0.30, front_cam=0.03, front_yaw=30.0,   # left foot: forward (screen-right), towards the camera, turned
    rear=0.50, rear_cam=0.05, rear_yaw=-55.0,     # right foot: back
    pelvis=(0.0, -8.0, 0.0), spine=(6.0, -6.0, 0.0), chest=(4.0, -8.0, 2.0),
    neck=(-2.0, 16.0, 0.0), head=(8.0, 20.0, -4.0),
    clav_x=-4.0, clav_z=6.0,
    sheath_up=0.085, sheath_cam=0.215, sheath_fwd=0.07,   # the held sheath's mouth from the pelvis
    sheath_tilt=0.0,                              # deg: hilt end up (+) / down
    elbow_out=0.45, elbow_down=0.10,
    lean=None, chest_yaw=None, head_yaw=None,     # scalar overrides of spine x, chest y, head y (fitting)
)
# Milestone 8: the idle stance fitted to idle1.png's silhouette through the
# sprite camera (sprite.fit, renders/checks/sprite_fit_v2/v3.json): the
# camera 80 deg round to her right and level (a fighting-game side view), the
# legs nearly side-on, the chest twisted back 3/4 to the viewer, the face
# turned so it shows (fixed by hand: the silhouette can't see a face), the
# sheathed tachi held in front at the belt (fixed by hand: the fit tucked the
# short sword into the body to dodge idle1's long one). IoU against idle1:
# 0.29 with the M7 stance -> 0.68 (silhouette), 0.70 on the final sprite.
IDLE = dict(IDLE_M7, az=-80.0, front=0.27, rear=0.44, drop=0.275, torso_fwd=-0.11, hips_yaw=12.5,
            lean=4.5, chest_yaw=-48.0, head_yaw=-12.0, sheath_up=0.13, sheath_cam=0.14, sheath_fwd=-0.095)


def pose_idle(rig, base=None, **kw):
    """her idle stance (Sprites/idle1.png); keyword arguments override IDLE
    (base=IDLE_M7 gives the Milestone 7 version)"""
    p = dict(base or IDLE, **kw)
    reset(rig)
    a = math.radians(p["az"])
    fwd = Vector((math.cos(a), math.sin(a), 0.0))          # screen-right on the floor
    cam = Vector((math.sin(a), -math.cos(a), 0.0))         # towards the camera
    # stance: left foot forward, right foot back, hips down between them
    move_ctrl(rig, "torso", fwd * p["torso_fwd"] + Vector((0.0, 0.0, -p["drop"])), yaw=p["hips_yaw"])
    move_ctrl(rig, "foot_ik.L", fwd * p["front"] + cam * p["front_cam"], yaw=p["front_yaw"])
    move_ctrl(rig, "foot_ik.R", fwd * -p["rear"] + cam * p["rear_cam"], yaw=p["rear_yaw"])
    aL, aR = world(rig, "foot_ik.L").translation, world(rig, "foot_ik.R").translation
    rear = Vector((math.sin(math.radians(-62.0)), -math.cos(math.radians(-62.0)), 0.0))
    place(rig, "knee_pole.L", aL + Vector((0, 0, 0.40)) + fwd * 0.60 + cam * 0.15)
    place(rig, "knee_pole.R", aR + Vector((0, 0, 0.40)) + rear * 0.50)
    # body: lean a little forward, chest and hips turned towards the camera
    rots = {b: list(p[b]) for b in ("pelvis", "spine", "chest", "neck", "head")}
    for key, (bone, ax) in (("lean", ("spine", 0)), ("chest_yaw", ("chest", 1)), ("head_yaw", ("head", 1))):
        if p.get(key) is not None:
            rots[bone][ax] = p[key]
    for b, r in rots.items():
        rot(rig, b, *r)
    for side, z_ in (("L", -p["clav_z"]), ("R", p["clav_z"])):
        rot(rig, "clavicle." + side, x=p["clav_x"], z=z_)
    # the sheathed tachi held level across the hips, hilt towards screen-right
    update()
    hips = world(rig, "pelvis").translation
    mouth = hips + Vector((0.0, 0.0, p["sheath_up"])) + cam * p["sheath_cam"] + fwd * p["sheath_fwd"]
    t = math.radians(p["sheath_tilt"])
    set_world(rig, "sheath_hold", frame(-fwd * math.cos(t) - Vector((0, 0, 1)) * math.sin(t), (0, 0, 1), mouth))
    rig["sword"], rig["sheath"], rig["hand_L"], rig["hand_R"] = 0, 1, 1, 1
    update()
    sR, sL = world(rig, "upper_arm.R").translation, world(rig, "upper_arm.L").translation
    place(rig, "elbow_pole.R", sR - fwd * p["elbow_out"] + Vector((0.0, 0.0, -p["elbow_down"])))
    place(rig, "elbow_pole.L", sL + fwd * p["elbow_out"] + Vector((0.0, 0.15, -p["elbow_down"])))
    fist(rig, "R")
    fist(rig, "L")
    # hair and tails settle with the turn
    rot(rig, "hair_back_01", x=4.0)
    rot(rig, "scarf_tail_01.L", x=-6.0)
    rot(rig, "scarf_tail_01.R", x=-4.0)
    update()
    return rig


SLASH = dict(front=0.46, rear=0.60, drop=0.30, hips_yaw=30.0, reach=0.60,
             az=IDLE_AZ, front_yaw=45.0, rear_yaw=-65.0, anchor=None, spine_y=8.0, chest_y=10.0, head_y=4.0)
# Milestone 8: the same cut laid out for the sprite camera (sprite.CAM, 80 deg
# round to her right) with the rear foot planted where the idle's rear foot
# stands (anchor = idle's foot_ik.R, set by sprite.frame_test): the game's
# sprites keep the rear foot on x 403 (idle1 and 5m4 both)
SLASH_SPRITE = dict(SLASH, az=-80.0, hips_yaw=-10.0, front_yaw=30.0, rear_yaw=-55.0, front=0.55, drop=0.34,
                    spine_y=-4.0, chest_y=-20.0, head_y=-14.0)


def root_to(rig, bone, xy):
    """slide the whole rig (root) so that `bone`'s head stands on world xy"""
    h = world(rig, bone).translation
    pb = rig.pose.bones["root"]
    pb.location = (pb.location[0] + xy[0] - h.x, pb.location[1] + xy[1] - h.y, pb.location[2])
    update()


def pose_draw_slash(rig, **kw):
    """the cut of her two-handed draw (5C, Sprites/5m4.png): long lunge, left
    foot forward as in every one of her sprites, rear leg straight, both arms
    out in front at chest height, the blade level and pointing ahead, the
    sheath left on the hip. Keywords override SLASH."""
    SL = dict(SLASH, **kw)
    reset(rig)
    a = math.radians(SL["az"])
    fwd = Vector((math.cos(a), math.sin(a), 0.0))          # screen-right on the floor
    cam = Vector((math.sin(a), -math.cos(a), 0.0))         # towards the camera
    up = Vector((0.0, 0.0, 1.0))
    # hips first (low, a little forward, turned towards the target), then the
    # feet from the hips: the front one ahead, the rear one as far back as the
    # straight rear leg reaches
    move_ctrl(rig, "torso", fwd * 0.03 + Vector((0.0, 0.0, -SL["drop"])), yaw=SL["hips_yaw"])
    rL = place_foot(rig, "L", fwd * SL["front"] + cam * 0.03, yaw=SL["front_yaw"])
    rR = place_foot(rig, "R", fwd * -SL["rear"] + cam * 0.02, yaw=SL["rear_yaw"])
    aL, aR = world(rig, "foot_ik.L").translation, world(rig, "foot_ik.R").translation
    place(rig, "knee_pole.L", aL + up * 0.45 + fwd * 0.70)
    place(rig, "knee_pole.R", aR + up * 0.40 + cam * 0.35 - fwd * 0.10)
    # body leans into the cut, chest square to the target
    rot(rig, "pelvis", x=8.0)
    rot(rig, "spine", x=14.0, y=SL["spine_y"])
    rot(rig, "chest", x=12.0, y=SL["chest_y"], z=-3.0)
    rot(rig, "neck", x=-10.0, y=2.0)
    rot(rig, "head", x=-16.0, y=SL["head_y"])
    rot(rig, "clavicle.R", x=4.0, z=14.0)               # shoulders reach forward
    rot(rig, "clavicle.L", x=4.0, z=-12.0)
    update()
    rig["sword"], rig["sheath"] = 2, 0
    sR, sL = world(rig, "upper_arm.R").translation, world(rig, "upper_arm.L").translation
    mid = 0.5 * (sR + sL)
    blade = fwd + up * 0.10
    guard = mid + fwd * SL["reach"] - up * 0.04 + cam * 0.02     # arms straight (the reach clamp stops it)
    place_sword_in_right_hand(rig, blade, up, guard)
    update()
    place(rig, "elbow_pole.R", sR + cam * 0.30 - up * 0.45)
    place(rig, "elbow_pole.L", sL - cam * 0.30 - up * 0.45)
    fist(rig, "R")
    fist(rig, "L")
    # motion: hair and the neckerchief tails stream back
    for nm in ("hair_back_01", "hair_back_side_01.L", "hair_back_side_01.R", "hair_side_01.L", "hair_side_01.R"):
        rot(rig, nm, x=10.0)
    rot(rig, "scarf_tail_01.L", x=18.0, z=-6.0)
    rot(rig, "scarf_tail_01.R", x=22.0, z=-4.0)
    rot(rig, "scarf_tail_02.L", x=10.0)
    rot(rig, "scarf_tail_02.R", x=12.0)
    update()
    if SL["anchor"] is not None:
        root_to(rig, "foot_ik.R", SL["anchor"])
    LAST["fit"] = dict(front=round(rL, 3), rear=round(rR, 3))
    return rig


def pose_right_hand(rig):
    """the right-hand socket, held out level (5B-style one-handed draw)"""
    reset(rig)
    rig["sword"] = 1
    update()
    sR = world(rig, "upper_arm.R").translation
    rot(rig, "chest", y=-10.0)
    update()
    place_sword_in_right_hand(rig, (0.05, -1.0, 0.05), (0, 0, 1), sR + Vector((-0.10, -0.38, -0.12)))
    place(rig, "elbow_pole.R", sR + Vector((-0.20, 0.10, -0.40)))
    # left arm down by her side, hand relaxed
    sL = world(rig, "upper_arm.L").translation
    set_world(rig, "hand_ik.L", frame((0.15, 0.0, -1.0), (1.0, 0.0, 0.1), sL + Vector((0.06, 0.02, -0.32))))
    place(rig, "elbow_pole.L", sL + Vector((0.10, 0.35, -0.15)))
    fist(rig, "R")
    fist(rig, "L", 0.35, 0.3)
    update()
    return rig


def pose_overhead(rig):
    """shoulder test: the sword raised high in the right hand (her Raijin /
    Fujin wind-up), the left hand on the sheath at the hip, a short stance"""
    reset(rig)
    move_ctrl(rig, "torso", (0.0, 0.0, -0.04))
    move_ctrl(rig, "foot_ik.L", (0.04, -0.16, 0.0), yaw=20.0)
    move_ctrl(rig, "foot_ik.R", (-0.04, 0.14, 0.0), yaw=-25.0)
    aL, aR = world(rig, "foot_ik.L").translation, world(rig, "foot_ik.R").translation
    place(rig, "knee_pole.L", aL + Vector((0.05, -0.60, 0.40)))
    place(rig, "knee_pole.R", aR + Vector((-0.05, -0.60, 0.40)))
    rot(rig, "spine", x=-4.0)
    rot(rig, "chest", x=-6.0, y=-6.0)
    rot(rig, "head", x=-10.0)
    rot(rig, "clavicle.R", x=14.0)                     # the shoulder lifts with the arm
    update()
    rig["sword"], rig["sheath"], rig["hand_R"] = 1, 0, 0
    sR = world(rig, "upper_arm.R").translation
    place_sword_in_right_hand(rig, (0.05, 0.30, 0.95), (0.0, 1.0, 0.0), sR + Vector((-0.10, -0.03, 0.45)))
    place(rig, "elbow_pole.R", sR + Vector((-0.45, 0.10, 0.10)))
    # left hand on the sheath's mouth at the hip (thumb on the guard)
    update()
    sL = world(rig, "upper_arm.L").translation
    mouth = world(rig, "sheath").translation
    set_world(rig, "hand_ik.L", frame((-0.30, -0.35, -0.88), (0.85, 0.0, 0.3), mouth + Vector((0.035, -0.02, 0.07))))
    place(rig, "elbow_pole.L", sL + Vector((0.30, 0.30, -0.20)))
    fist(rig, "R")
    fist(rig, "L", 0.8, 0.6)
    update()
    return rig


POSES = dict(rest=pose_rest, idle=pose_idle, draw_slash=pose_draw_slash, right_hand=pose_right_hand,
             overhead=pose_overhead, idle_m7=lambda rig, **kw: pose_idle(rig, base=IDLE_M7, **kw),
             draw_slash_sprite=lambda rig, **kw: pose_draw_slash(rig, **dict(SLASH_SPRITE, **kw)))


def pose(name, **kw):
    rig = rig_obj()
    return POSES[name](rig, **kw)


# ----------------------------------------------------------------------------- renders
def bone_point(bone, at="head"):
    rig = rig_obj()
    pb = rig.pose.bones[bone]
    return tuple(rig.matrix_world @ (pb.head if at == "head" else pb.tail))


def render(tag, views, size=1.9, res=(900, 900), target=(0.0, 0.0, 0.74)):
    """views: [(suffix, azimuth, elevation)]"""
    import runpy
    rb = runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "review_body.py"))
    out = []
    for nm, az, el in views:
        out.append(rb["angle"](tag, nm, az, el, target=target, size=size, res=res))
    return out
