# Body in T-pose: torso, neck, arms, hands, legs, head base, ears.
import math, importlib, sys
from mathutils import Vector
import lib, palette; importlib.reload(lib); importlib.reload(palette)
from lib import *
P = palette.P

def M(key, **kw):
    b, s = P[key]; return toon("MAT_" + key, b, s, **kw)

def superellipse(rx, ry, a, p_front=2.0, p_back=2.0):
    c, s = math.cos(a), math.sin(a)
    p = p_front if s < 0 else p_back
    e = 2.0 / p
    return rx * math.copysign(abs(c) ** e, c), ry * math.copysign(abs(s) ** e, s)

TORSO = [  # z, cy, rx, ry, bust
    (0.700, 0.012, 0.100, 0.070, 0.0),
    (0.730, 0.012, 0.128, 0.084, 0.0),
    (0.800, 0.010, 0.143, 0.093, 0.0),
    (0.880, 0.006, 0.138, 0.088, 0.0),
    (0.950, 0.002, 0.117, 0.075, 0.0),
    (1.000, 0.000, 0.106, 0.069, 0.0),
    (1.060, -0.002, 0.116, 0.076, 0.006),
    (1.110, -0.004, 0.127, 0.082, 0.020),
    (1.160, -0.004, 0.133, 0.080, 0.014),
    (1.205, 0.000, 0.138, 0.070, 0.0),
    (1.240, 0.004, 0.118, 0.058, 0.0),
    (1.262, 0.006, 0.060, 0.046, 0.0),
]

LEG = [  # z, rx, ry, dy
    (0.83, 0.086, 0.086, 0.010), (0.72, 0.081, 0.080, 0.010), (0.62, 0.071, 0.071, 0.008),
    (0.52, 0.059, 0.060, 0.004), (0.44, 0.046, 0.048, 0.002), (0.36, 0.050, 0.054, 0.010),
    (0.28, 0.047, 0.051, 0.012), (0.18, 0.035, 0.038, 0.006), (0.10, 0.026, 0.030, 0.004),
    (0.05, 0.025, 0.030, 0.004)]


def _interp(table, z):
    """Linear interpolation of a table of tuples keyed by first element (ascending or descending)."""
    t = sorted(table, key=lambda r: r[0])
    if z <= t[0][0]: return t[0][1:]
    if z >= t[-1][0]: return t[-1][1:]
    for a, b in zip(t, t[1:]):
        if a[0] <= z <= b[0]:
            f = (z - a[0]) / (b[0] - a[0])
            return tuple(x + (y - x) * f for x, y in zip(a[1:], b[1:]))

def torso_point(z, a, off=0.0):
    cy, rx, ry, bust = _interp(TORSO, z)
    x, y = superellipse(rx + off, ry + off, a, 2.2, 2.0)
    if bust and math.sin(a) < 0:
        f = math.exp(-((abs(x) - 0.058) / 0.042) ** 2)
        y -= bust * f * (-math.sin(a)) ** 1.5
    return Vector((x, cy + y, z))

def torso_ring(z, n=32, off=0.0):
    return [torso_point(z, 2 * math.pi * j / n, off) for j in range(n)]

def leg_center(sx, z):
    rx, ry, dy = _interp(LEG, z)
    return Vector((sx * (0.085 - 0.012 * (1 - z / 0.83)), dy, z))

def leg_point(sx, z, a, off=0.0):
    rx, ry, dy = _interp(LEG, z)
    c = leg_center(sx, z)
    return c + Vector(((rx + off) * math.cos(a), (ry + off) * math.sin(a), 0))

def leg_ring(sx, z, n=16, off=0.0):
    return [leg_point(sx, z, 2 * math.pi * j / n, off) for j in range(n)]


def build():
    skin = M("skin")
    # ---------------- torso
    rings = [torso_ring(z, 32) for z, *_ in TORSO]
    o = loft("Body_Torso", rings, cap0=True, cap1=True, mats=[skin]); subsurf(o, 1)

    # ---------------- neck
    o = tube("Body_Neck", [(0, 0.008, 1.235), (0, 0.002, 1.29), (0, -0.004, 1.335)],
             [0.036, 0.032, 0.032], n=16, mats=[skin]); subsurf(o, 1)

    # ---------------- arms (T-pose, along +/-X), palms down
    zA = 1.205
    arm = [(0.09, 0.055, 0.055), (0.15, 0.047, 0.045), (0.22, 0.040, 0.039), (0.30, 0.035, 0.034),
           (0.36, 0.031, 0.031), (0.42, 0.033, 0.032), (0.49, 0.027, 0.028), (0.545, 0.019, 0.025)]
    for side, sx in (("L", 1), ("R", -1)):
        pts = [(sx * x, 0.004, zA) for x, _, _ in arm]
        rad = [(rz, ry) for _, rz, ry in arm]
        o = tube(f"Body_Arm.{side}", pts, rad, n=16, normals=[(0, 0, 1)] * len(pts), mats=[skin]); subsurf(o, 1)
        build_hand(side, sx, zA)

    # ---------------- legs
    for side, sx in (("L", 1), ("R", -1)):
        rings = [leg_ring(sx, z, 16) for z, *_ in LEG]
        o = loft(f"Body_Leg.{side}", rings, cap0=True, cap1=True, mats=[skin]); subsurf(o, 1)

    build_head()


def build_hand(side, sx, zA):
    skin = M("skin"); glove = M("glove")
    objs = []
    # palm: rounded box loft along X
    palm = []
    for x, hz, hy in ((0.535, 0.016, 0.026), (0.56, 0.013, 0.033), (0.60, 0.012, 0.036), (0.635, 0.010, 0.034)):
        r = []
        for j in range(16):
            a = 2 * math.pi * j / 16
            yy, zz = superellipse(hy, hz, a, 3.0, 3.0)
            r.append(Vector((sx * x, 0.004 + yy, zA + zz - 0.002)))
        palm.append(r)
    o = loft(f"Body_Palm.{side}", palm, cap0=True, cap1=True, mats=[glove]); subsurf(o, 1)
    # fingers (index at front -Y)
    fingers = [(-0.024, 0.062), (-0.008, 0.070), (0.008, 0.066), (0.023, 0.052)]
    for i, (fy, ln) in enumerate(fingers):
        x0 = 0.628
        pts = [(sx * (x0 + ln * t), 0.004 + fy * (1 + 0.15 * t), zA - 0.003 - 0.012 * t * t) for t in (0, 0.33, 0.66, 1.0)]
        o = tube(f"Body_Finger{i}.{side}", pts, [0.0085, 0.008, 0.0072, 0.006], n=8,
                 normals=[(0, 0, 1)] * 4, mats=[glove, skin],
                 )
        for p in o.data.polygons:
            p.material_index = 0 if abs(p.center.x) < x0 + ln * 0.42 else 1
        subsurf(o, 1)
    # thumb
    pts = [(sx * 0.565, -0.022, zA - 0.006), (sx * 0.59, -0.045, zA - 0.010), (sx * 0.615, -0.062, zA - 0.012),
           (sx * 0.635, -0.072, zA - 0.013)]
    o = tube(f"Body_Thumb.{side}", pts, [0.011, 0.0095, 0.0085, 0.007], n=8, normals=[(0, 0, 1)] * 4, mats=[glove, skin])
    for p in o.data.polygons:
        p.material_index = 0 if p.center.y > -0.055 else 1
    subsurf(o, 1)


def build_head():
    skin = M("skin")
    face = face_material()
    H = [  # z, cy, rx, ry
        (1.288, -0.066, 0.008, 0.008), (1.296, -0.060, 0.024, 0.024), (1.310, -0.048, 0.040, 0.044),
        (1.330, -0.034, 0.055, 0.064), (1.350, -0.022, 0.066, 0.080), (1.372, -0.014, 0.073, 0.090),
        (1.395, -0.010, 0.077, 0.096), (1.420, -0.007, 0.080, 0.099), (1.450, -0.005, 0.081, 0.099),
        (1.480, -0.004, 0.078, 0.095), (1.505, -0.002, 0.069, 0.085), (1.527, 0.000, 0.052, 0.065),
        (1.542, 0.002, 0.028, 0.036), (1.548, 0.002, 0.010, 0.012)]
    rings = []
    n = 40
    for z, cy, rx, ry in H:
        r = []
        for j in range(n):
            a = 2 * math.pi * j / n
            x, y = superellipse(rx, ry, a, 2.35, 2.0)
            p = Vector((x, cy + y, z))
            # nose bump
            p.y -= 0.0045 * math.exp(-(x / 0.007) ** 2) * math.exp(-((z - 1.350) / 0.012) ** 2) * max(0, -math.sin(a))
            r.append(p)
        rings.append(r)
    o = loft("Head", rings, cap0=True, cap1=True, mats=[face, skin])
    # front faces get the painted face texture, others plain skin; UVs: front projection
    me = o.data
    uv = me.uv_layers.new(name="FaceProj")
    for poly in me.polygons:
        poly.material_index = 0 if poly.center.y < -0.02 else 1
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = ((v.x + 0.09) / 0.18, (v.z - 1.27) / 0.18)
    subsurf(o, 1)
    # ears
    for side, sx in (("L", 1), ("R", -1)):
        e = ellipsoid(f"Ear.{side}", (0, 0, 0), (0.008, 0.014, 0.020), n=12, rings=8, mats=[skin])
        e.location = (sx * 0.071, 0.016, 1.372)
        e.rotation_euler = (0, sx * -0.25, 0)


def face_material():
    import os
    name = "MAT_face"
    sb, ss = P["skin"]
    def base_fn(nt):
        img_path = os.path.join(ROOT, "textures", "face.png")
        tex = nt.nodes.new('ShaderNodeTexImage')
        img = bpy.data.images.get("face.png")
        if img: img.reload()
        else: img = bpy.data.images.load(img_path)
        img.alpha_mode = 'STRAIGHT'
        tex.image = img; tex.interpolation = 'Cubic'; tex.extension = 'CLIP'
        uvn = nt.nodes.new('ShaderNodeUVMap'); uvn.uv_map = "FaceProj"
        nt.links.new(uvn.outputs[0], tex.inputs[0])
        rgb = nt.nodes.new('ShaderNodeRGB'); rgb.outputs[0].default_value = hexc(sb)
        return lib._mix(nt, tex.outputs['Alpha'], rgb.outputs[0], tex.outputs['Color'])
    m = toon(name, sb, None, base_fn=base_fn, thresh=-0.25)
    return m

if __name__ == "__main__" or True:
    pass
