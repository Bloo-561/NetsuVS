# Hair: bob clumps, bangs, side locks, lock between the eyes, inner volume, ahoge, headband with V mark.
import math, importlib
from mathutils import Vector
import lib, palette; importlib.reload(lib); importlib.reload(palette)
from lib import *
P = palette.P

HC = Vector((0, 0.008, 1.430))   # hair sphere center
SX, SY = 1.0, 1.12               # head is deeper than wide
D = math.radians

def hair_mat():
    hb, hs = P["hair"]; pb, ps = P["hair_purple"]
    def base_fn(nt):
        geo = nt.nodes.new('ShaderNodeNewGeometry')
        sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(geo.outputs['Position'], sep.inputs[0])
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.inputs['From Min'].default_value = 1.405; mr.inputs['From Max'].default_value = 1.292
        mr.inputs['To Min'].default_value = 0.0; mr.inputs['To Max'].default_value = 1.0
        mr.clamp = True
        nt.links.new(sep.outputs['Z'], mr.inputs['Value'])
        sm = nt.nodes.new('ShaderNodeMath'); sm.operation = 'POWER'; sm.inputs[1].default_value = 1.5
        nt.links.new(mr.outputs['Result'], sm.inputs[0])
        a = nt.nodes.new('ShaderNodeRGB'); a.outputs[0].default_value = hexc(hb)
        b = nt.nodes.new('ShaderNodeRGB'); b.outputs[0].default_value = hexc(pb)
        return lib._mix(nt, sm.outputs[0], a.outputs[0], b.outputs[0])
    m = toon("MAT_hair", hb, None, base_fn=base_fn, thresh=0.05)
    return m

def dirh(phi):  # horizontal unit-ish direction for azimuth phi (0 = front -Y, +90 = her left +X)
    front = max(0.0, math.cos(phi))
    sy = SY * (1 - 0.13 * front)
    return Vector((math.sin(phi) * SX, -math.cos(phi) * sy, 0))

def sphere_pt(phi, th, R):
    return HC + dirh(phi) * (R * math.sin(th)) + Vector((0, 0, R * math.cos(th)))

def clump(name, pts, wmax, tmax=0.012, cup=0.35, root_w=0.6, n=10, mats=None, twist=0.0):
    pts = [Vector(p) for p in pts]
    pts, T, _, _ = frames(pts)
    rings = []
    L = len(pts)
    for i, p in enumerate(pts):
        s = i / (L - 1)
        w = wmax * min(1.0, root_w + s * 2.2) * max(0.0, 1 - s ** 2.2) ** 0.9 + 0.0006
        t = tmax * (1 - 0.7 * s) + 0.0004
        Nn = (p - HC); Nn.z *= 0.6
        Nn = (Nn - Nn.dot(T[i]) * T[i]).normalized()
        B = T[i].cross(Nn)
        if twist:
            a = twist * s; B, Nn = B * math.cos(a) + Nn * math.sin(a), -B * math.sin(a) + Nn * math.cos(a)
        ring = []
        for j in range(n):
            a = 2 * math.pi * j / n
            c, si = math.cos(a), math.sin(a)
            ring.append(p + B * (w * c) + Nn * (t * si) - Nn * (cup * w * c * c))
        rings.append(ring)
    o = loft(name, rings, cap0=True, cap1=False, mats=mats)
    return o

def bob_path(phi, th0, tip_z, R0=0.118, flare=0.012, inset=0.0):
    pts = []
    for k in range(8):
        th = D(th0) + (D(96) - D(th0)) * k / 7
        R = R0 + 0.017 * math.sin(th) - inset
        pts.append(sphere_pt(phi, th, R))
    p95 = pts[-1]
    hdir = Vector((p95.x - HC.x, p95.y - HC.y, 0)); h0 = hdir.length; hdir.normalize()
    for k in range(1, 8):
        t = k / 7
        z = p95.z + (tip_z - p95.z) * t
        h = h0 * (1 - 0.05 * math.sin(math.pi * t)) + flare * t ** 3
        pts.append(Vector((HC.x, HC.y, 0)) + hdir * h + Vector((0, 0, z)))
    return bezier_pts(pts, 3)

def bang_path(phi, th0, tip_z, tip_y=-0.115, hook=0.004, spread=0.0):
    pts = []
    for k in range(6):
        th = D(th0) + (D(70) - D(th0)) * k / 5
        pts.append(sphere_pt(phi, th, 0.120 + 0.014 * math.sin(th)))
    a = pts[-1]
    end = Vector((a.x + spread, tip_y, tip_z))
    for k in range(1, 6):
        t = k / 5
        p = a.lerp(end, t)
        p.y = a.y + (end.y - a.y) * t - 0.006 * math.sin(math.pi * t)   # bulge forward a bit
        if k == 5: p.y += hook
        pts.append(p)
    return bezier_pts(pts, 3)

def lock_path(phi, th0, end, mid_out=0.006):
    pts = []
    for k in range(6):
        th = D(th0) + (D(84) - D(th0)) * k / 5
        pts.append(sphere_pt(phi, th, 0.120 + 0.016 * math.sin(th)))
    a = pts[-1]; end = Vector(end)
    for k in range(1, 7):
        t = k / 6
        p = a.lerp(end, t)
        out = Vector((p.x, p.y - HC.y, 0)).normalized()
        p += out * mid_out * math.sin(math.pi * t)
        pts.append(p)
    return bezier_pts(pts, 3)

def build():
    clear_collection("Hair")
    coll("Hair", coll())
    hm = hair_mat(); mats = [hm]
    C = "Hair"
    import random
    rnd = random.Random(7)
    # ---- bob: two layers around sides/back
    i = 0
    for layer, (step, off, R0, wm) in enumerate(((20, 0, 0.116, 0.078), (20, 10, 0.121, 0.070))):
        for a in range(78 + off, 283 + off - (10 if off else 0), step):
            phi = D(a)
            back = abs(math.cos(phi - math.pi))      # 1 at back
            tip = 1.274 + 0.012 * (1 - back) + (0.018 if layer else 0) + rnd.uniform(-0.008, 0.008)
            flare = 0.012 + 0.010 * (1 - back) + rnd.uniform(-0.004, 0.006)
            pts = bob_path(phi, 6 + rnd.uniform(0, 14), tip, R0=R0, flare=flare)
            o = clump(f"Hair_Bob{i:02d}", pts, wm * rnd.uniform(0.9, 1.1), tmax=0.013, mats=mats,
                      twist=rnd.uniform(-0.3, 0.3))
            move_to(o, C); i += 1
    # ---- side locks framing the face
    for k, (a, end, w) in enumerate(((56, (0.088, -0.046, 1.300), 0.038), (70, (0.108, -0.016, 1.286), 0.050),
                                     (-56, (-0.088, -0.046, 1.302), 0.038), (-70, (-0.108, -0.016, 1.290), 0.050))):
        o = clump(f"Hair_Side{k}", lock_path(D(a), 22, end), w, tmax=0.010, mats=mats); move_to(o, C)
    # ---- bangs (across the forehead, ending around the eyes)
    bangs = [(-44, 1.398, 0.040, -0.012), (-30, 1.386, 0.042, -0.006), (-16, 1.392, 0.040, 0.0),
             (2, 1.394, 0.040, 0.004), (16, 1.388, 0.042, 0.004), (30, 1.384, 0.042, 0.008), (44, 1.396, 0.040, 0.012)]
    for k, (a, tz, w, sp) in enumerate(bangs):
        ty = -0.110 if abs(a) < 35 else -0.098
        o = clump(f"Hair_Bang{k}", bang_path(D(a), 14, tz, tip_y=ty, spread=sp), w, tmax=0.010, mats=mats); move_to(o, C)
    # the lock falling between the eyes (slightly to her right)
    o = clump("Hair_BangCenter", bang_path(D(-6), 12, 1.352, tip_y=-0.116, spread=-0.004, hook=0.006), 0.022,
              tmax=0.008, mats=mats); move_to(o, C)
    # ---- crown cap + inner volume (fills gaps between clumps)
    rings = []
    for k in range(1, 10):
        th = D(100) * k / 9
        rings.append([sphere_pt(D(360 * j / 32), th, 0.114 + 0.012 * math.sin(th)) for j in range(32)])
    o = loft("Hair_Cap", rings, cap0=True, mats=mats); flip_if_inward(o); move_to(o, C)
    rings = []
    for k in range(7):
        z = 1.43 - (1.43 - 1.312) * k / 6
        r = []
        for j in range(25):
            phi = D(76 + 208 * j / 24)
            r.append(Vector((HC.x, HC.y, z)) + dirh(phi) * (0.124 - 0.006 * math.sin(math.pi * k / 6)))
        rings.append(r)
    o = loft("Hair_Inner", rings, closed=False, mats=mats); move_to(o, C)
    # ---- ahoge
    ctrl = [(0.0, 0.004, 1.548), (0.002, 0.010, 1.575), (0.010, 0.004, 1.600), (0.022, -0.012, 1.612),
            (0.034, -0.024, 1.604), (0.034, -0.026, 1.590), (0.026, -0.020, 1.584)]
    pts = bezier_pts(ctrl, 6)
    rings = []
    ptsv, T, N, B = frames(pts, Vector((0.6, 0.8, 0)))
    for i2, p in enumerate(ptsv):
        s = i2 / (len(ptsv) - 1)
        w = 0.010 * (1 - s ** 1.5) + 0.0006; t = 0.004 * (1 - 0.6 * s) + 0.0004
        rings.append([p + B[i2] * w * math.cos(2 * math.pi * j / 8) + N[i2] * t * math.sin(2 * math.pi * j / 8) for j in range(8)])
    o = loft("Hair_Ahoge", rings, cap0=True, mats=mats); move_to(o, C)
    build_headband()

def flip_if_inward(o):
    me = o.data
    c = sum((v.co for v in me.vertices), Vector()) / len(me.vertices)
    s = sum((p.normal.dot(p.center - HC)) for p in me.polygons)
    if s < 0: flip(o)

def move_to(o, cname):
    c = coll(cname, coll())
    for uc in list(o.users_collection): uc.objects.unlink(o)
    c.objects.link(o)

def build_headband():
    hb, hs = P["headband"]; gb, gs = P["gold"]
    band = toon("MAT_headband", hb, hs); gold = toon("MAT_gold", gb, gs)
    n = Vector((0, 0.433, 0.902)).normalized()
    e1 = Vector((1, 0, 0)); e2 = Vector((0, -0.902, 0.433)).normalized()
    pts, nrm, wid = [], [], []
    N = 48
    for k in range(N + 1):
        u = 2 * math.pi * k / N
        front = max(0.0, math.sin(u))
        R = 0.119 + 0.022 * front ** 0.35
        d = e1 * math.cos(u) + e2 * math.sin(u)
        d = Vector((d.x * SX, d.y * (SY * (1 - 0.13 * max(0, -d.y / max(1e-6, d.length)))), d.z))
        pts.append(HC + d * R)
        nrm.append((pts[-1] - HC))
        wid.append(0.021)
    o = strip("Hair_Headband", pts[:-1] + [pts[0]], wid[:-1] + [wid[0]], nrm[:-1] + [nrm[0]], thick=0.006, mats=[band])
    move_to(o, "Hair")
    # yellow "IV" mark on the front of the band
    d = e2.copy(); d.y *= SY * (1 - 0.13 * (-d.y / d.length))
    front = HC + d * 0.141
    out = (front - HC).normalized(); tx = Vector((1, 0, 0)); up = out.cross(tx).normalized()
    if up.z < 0: up = -up
    base = front + out * 0.0045
    def seg(nm, a, b, w=0.0028):
        A = base + tx * a[0] + up * a[1]; Bp = base + tx * b[0] + up * b[1]
        o = strip(nm, [A, (A + Bp) / 2, Bp], [w, w, w], [out, out, out], thick=0.0015, mats=[gold], smooth=False)
        move_to(o, "Hair")
    seg("Hair_BandMark_I", (-0.016, -0.0085), (-0.016, 0.0085))
    seg("Hair_BandMark_V1", (-0.009, 0.0085), (0.001, -0.0085))
    seg("Hair_BandMark_V2", (0.001, -0.0085), (0.012, 0.0085))
