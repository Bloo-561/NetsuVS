# Outfit: pinafore dress (bodice, pleated skirt, hem stripes), petticoat, cropped jacket + sleeves + cuffs + collar,
# shirt + frill collar, tie, sailor collar, brooch, neckerchief, crossed belts + buckles, socks (asymmetric) + ribbons,
# loafers + bows, glove cuffs, arm band (her RIGHT arm).
import math, importlib
from mathutils import Vector
import lib, palette, body
for m_ in (lib, palette, body): importlib.reload(m_)
from lib import *
from body import torso_point, torso_ring, leg_center, leg_point, leg_ring, superellipse
P = palette.P
C = "Outfit"
TAU = 2 * math.pi

def M(key, **kw):
    b, s = P[key]; return toon("MAT_" + key, b, s, **kw)

def put(o):
    c = coll(C, coll())
    for uc in list(o.users_collection): uc.objects.unlink(o)
    c.objects.link(o); return o

def lerp(a, b, t): return a + (b - a) * t

def front_y(x, z, off=0.0):
    """y of the torso surface (front) at a given x, z."""
    best = None
    for k in range(200):
        a = -math.pi + math.pi * k / 199
        p = torso_point(z, a, off)
        if best is None or abs(p.x - x) < abs(best.x - x): best = p
    return best.y

# ------------------------------------------------------------------ dress
Z_TOP, Z_HEM = 0.955, 0.775

def skirt_point(z, a, off=0.0, pleats=True):
    t = (Z_TOP - z) / (Z_TOP - Z_HEM); t = max(0.0, t)
    top = torso_point(Z_TOP, a, 0.010)
    s = math.sin(a)
    ry = 0.150 if s < 0 else 0.178
    hem = Vector((0.222 * math.cos(a), 0.012 + ry * s, z))
    tt = t ** 0.85
    p = Vector((lerp(top.x, hem.x, tt), lerp(top.y, hem.y, tt), z))
    rad = Vector((p.x, p.y - 0.012, 0)).normalized()
    if pleats:
        frac = (a * 24 / TAU) % 1.0
        tri = 1 - 4 * abs(frac - 0.5)
        p += rad * (0.010 * t * tri)
    return p + rad * off

def build_dress():
    dress, stripe = M("dress"), M("stripe")
    # bodice
    rings = [torso_ring(z, 32, 0.008) for z in (0.935, 0.98, 1.03, 1.08, 1.12, 1.16, 1.20)]
    put(loft("Outfit_Bodice", rings, mats=[dress]))
    # skirt
    rows = [0.955, 0.925, 0.895, 0.865, 0.840, 0.8135, 0.8085, 0.7995, 0.7945, 0.785, 0.775]
    n = 96
    rings = [[skirt_point(z, TAU * j / n) for j in range(n)] for z in rows]
    o = put(loft("Outfit_Skirt", rings, mats=[dress, stripe], smooth=False))
    for p in o.data.polygons:
        z = p.center.z
        p.material_index = 1 if (0.8085 < z < 0.8135 or 0.7945 < z < 0.7995) else 0
    # petticoat with scalloped hem
    n = 240
    pet = M("petticoat")
    def pp(z, a, off):
        q = skirt_point(max(z, Z_HEM), a, off, pleats=False)
        q.z = z
        return q
    rings = [[pp(z, TAU * j / n, -0.016) for j in range(n)] for z in (0.86, 0.80)]
    rings.append([pp(0.776, TAU * j / n, -0.013) for j in range(n)])
    hem = []
    for j in range(n):
        a = TAU * j / n
        f = (a * 30 / TAU) % 1.0
        dz = 0.012 * math.sqrt(max(0.0, 1 - ((f - 0.5) * 2) ** 2))
        hem.append(pp(0.758 - dz, a, -0.010 + 0.004 * dz / 0.012))
    rings.append(hem)
    put(loft("Outfit_Petticoat", rings, mats=[pet]))

# ------------------------------------------------------------------ jacket
def open_ring(z, off, gap, n=40, fn=torso_point):
    # angles from the front-right edge, round the back, to the front-left edge
    lo = None
    for k in range(400):
        a = -math.pi / 2 + (math.pi / 2) * k / 399
        if fn(z, a, off).x >= gap: lo = a; break
    d = lo + math.pi / 2
    return [fn(z, -math.pi / 2 + d + (TAU - 2 * d) * j / (n - 1), off) for j in range(n)]

def build_jacket():
    jk, sl, li = M("jacket"), M("sleeve"), M("lining")
    rows = [1.022, 1.05, 1.09, 1.13, 1.17, 1.205, 1.232, 1.250]
    rings = []
    for z in rows:
        t = (z - rows[0]) / (rows[-1] - rows[0])
        rings.append(open_ring(z, 0.017 + 0.004 * (1 - t), lerp(0.092, 0.052, t)))
    o = put(loft("Outfit_Jacket", rings, closed=False, mats=[jk, sl]))
    for p in o.data.polygons:  # grey yoke on the upper front, like the sheet
        p.material_index = 1 if (p.center.z > 1.168 and p.center.y < -0.01) else 0
    subsurf(o, 1)
    # sleeves (rolled to just below the elbow) + white cuffs
    zA = 1.205
    S = [(0.110, 0.056, 0.060), (0.15, 0.060, 0.060), (0.22, 0.054, 0.053), (0.30, 0.050, 0.049),
         (0.37, 0.047, 0.046), (0.400, 0.046, 0.045)]
    for side, sx in (("L", 1), ("R", -1)):
        pts = [(sx * x, 0.004, zA + 0.004 * (1 - x / 0.4)) for x, _, _ in S]
        put(tube(f"Outfit_Sleeve.{side}", pts, [(rz, ry) for _, rz, ry in S], n=20, normals=[(0, 0, 1)] * len(S),
                 cap0=True, cap1=False, mats=[sl])); subsurf(bpy.data.objects[f"Outfit_Sleeve.{side}"], 1)
        cpts = [(sx * x, 0.004, zA) for x in (0.365, 0.39, 0.418)]
        put(tube(f"Outfit_Cuff.{side}", cpts, [(0.051, 0.050), (0.053, 0.052), (0.051, 0.050)], n=20,
                 normals=[(0, 0, 1)] * 3, cap0=False, cap1=False, mats=[li]))
    # arm band on her RIGHT upper arm (-X)
    put(tube("Outfit_ArmBand.R", [(-0.262, 0.004, zA + 0.0015), (-0.27, 0.004, zA + 0.0012), (-0.278, 0.004, zA + 0.001)],
             [(0.0545, 0.0535)] * 3, n=20, normals=[(0, 0, 1)] * 3, cap0=False, cap1=False, mats=[M("armband")]))
    # turned-down collar (open at the front)
    def neck_pt(z, a, r):
        return Vector((r * math.cos(a), 0.004 + r * 1.05 * math.sin(a), z))
    rows = []
    d = math.radians(24)
    angs = [-math.pi / 2 + d + (TAU - 2 * d) * j / 39 for j in range(40)]
    rows.append([neck_pt(1.282, a, 0.050) for a in angs])
    rows.append([neck_pt(1.284, a, 0.060) for a in angs])
    outer = []
    for a in angs:
        f = max(0.0, -math.sin(a)) ** 3      # front: lapel points drop lower
        q = neck_pt(1.236 - 0.030 * f, a, 0.086 - 0.016 * f)
        outer.append(q)
    rows.append(outer)
    put(loft("Outfit_JacketCollar", rows, closed=False, mats=[jk]))

# ------------------------------------------------------------------ shirt, tie, collars, brooch, neckerchief
def build_neck():
    sh, tie, sail, br, ke = M("shirt"), M("tie"), M("sailor"), M("brooch"), M("kerchief")
    put(loft("Outfit_Shirt", [torso_ring(z, 32, 0.004) for z in (1.17, 1.20, 1.232, 1.255)], mats=[sh]))
    # frilled stand collar
    rows = []
    n = 60
    for z, r in ((1.250, 0.044), (1.272, 0.041), (1.290, 0.042)):
        rows.append([Vector((r * math.cos(TAU * j / n), 0.004 + r * math.sin(TAU * j / n),
                             z + (0.0045 * abs(math.sin(TAU * j / n * 7)) if z > 1.28 else 0))) for j in range(n)])
    put(loft("Outfit_FrillCollar", rows, mats=[sh]))
    # tie (short, black)
    pts = [Vector((0, front_y(0, z, 0.012), z)) for z in (1.262, 1.240, 1.216)]
    put(strip("Outfit_Tie", pts, [0.016, 0.019, 0.016], [(0, -1, 0.15)] * 3, thick=0.004, mats=[tie]))
    # sailor collar: two dark-grey bands from the neck sides down to the brooch
    for side, sx in (("L", 1), ("R", -1)):
        pts = []
        for t in (0, 0.33, 0.66, 1.0):
            x = sx * lerp(0.050, 0.004, t); z = lerp(1.262, 1.196, t)
            pts.append(Vector((x, front_y(x, z, 0.016) if t > 0 else -0.030, z)))
        put(strip(f"Outfit_Sailor.{side}", pts, [0.034, 0.030, 0.024, 0.014],
                  [(sx * 0.3, -1, 0.5)] * 4, thick=0.004, mats=[sail]))
    # brooch (white flower)
    bc = Vector((0, front_y(0, 1.196, 0.030), 1.196))
    for k in range(5):
        a = TAU * k / 5 + math.pi / 2
        o = ellipsoid(f"Outfit_BroochPetal{k}", (0, 0, 0), (0.0062, 0.0035, 0.0062), n=10, rings=6, mats=[br])
        o.location = bc + Vector((0.0068 * math.cos(a), 0, 0.0068 * math.sin(a))); put(o)
    o = ellipsoid("Outfit_BroochCenter", (0, 0, 0), (0.0042, 0.004, 0.0042), n=10, rings=6, mats=[M("gold")])
    o.location = bc + Vector((0, -0.003, 0)); put(o)
    # neckerchief: side loops + two tails hanging down the chest
    for side, sx in (("L", 1), ("R", -1)):
        pts = [bc + Vector((sx * 0.004, 0.006, 0)), bc + Vector((sx * 0.022, 0.008, -0.004)),
               Vector((sx * 0.040, front_y(sx * 0.040, 1.188, 0.020), 1.188))]
        put(strip(f"Outfit_KerchiefWing.{side}", pts, [0.016, 0.020, 0.014], [(0, -1, 0.2)] * 3, thick=0.004, mats=[ke]))
        ends = (0.030, 1.108) if sx > 0 else (-0.022, 1.100)
        pts = []
        for t in (0, 0.25, 0.5, 0.75, 1.0):
            x = lerp(sx * 0.004, ends[0], t); z = lerp(1.192, ends[1], t)
            pts.append(Vector((x, front_y(x, z, 0.019), z)))
        widths = [0.016, 0.019, 0.020, 0.019, 0.002]
        put(strip(f"Outfit_KerchiefTail.{side}", pts, widths, [(0, -1, 0.05)] * 5, thick=0.003, mats=[ke]))
    o = ellipsoid("Outfit_KerchiefKnot", (0, 0, 0), (0.010, 0.006, 0.008), n=10, rings=6, mats=[ke])
    o.location = bc + Vector((0, 0.005, -0.002)); put(o)

# ------------------------------------------------------------------ belts
def build_belts():
    bt, bk = M("belt"), M("buckle")
    for name, z0, slope, buckle_a in (("A", 0.944, 0.045, -1.05), ("B", 0.912, -0.040, -2.20)):
        n = 64
        pts, nr = [], []
        for j in range(n + 1):
            a = TAU * j / n
            z = z0 + slope * math.cos(a)
            p = torso_point(z, a, 0.020)
            pts.append(p); nr.append(Vector((p.x, p.y, 0)))
        put(strip(f"Outfit_Belt{name}", pts, [0.017] * (n + 1), nr, thick=0.004, mats=[bt]))
        z = z0 + slope * math.cos(buckle_a)
        p = torso_point(z, buckle_a, 0.025)
        nn = Vector((p.x, p.y, 0)).normalized()
        th = math.atan2(-nn.x, nn.y)
        # buckle frame = 4 thin bars
        for k, (cx, cz, sx_, sz_) in enumerate(((-0.010, 0, 0.003, 0.024), (0.010, 0, 0.003, 0.024),
                                               (0, 0.0105, 0.023, 0.003), (0, -0.0105, 0.023, 0.003))):
            off = Vector((math.cos(th) * cx, math.sin(th) * cx, cz))
            put(box(f"Outfit_Buckle{name}{k}", p + off, (sx_, 0.004, sz_), rot=(0, 0, th), mats=[bk]))
    # sword hanger loops on her left hip
    for k, z in enumerate((0.935, 0.905)):
        p = torso_point(z, -0.35, 0.024)
        put(box(f"Outfit_Hanger{k}", p, (0.014, 0.006, 0.030), rot=(0, 0.35, -0.35 + math.pi / 2), mats=[bt]))

# ------------------------------------------------------------------ legs
def build_legs():
    st, rb = M("stocking"), M("ribbon")
    # her RIGHT leg (-X): thigh-high stocking; LEFT (+X): knee-high sock
    for side, sx, top in (("R", -1, 0.625), ("L", 1, 0.425)):
        zs = [0.045, 0.08, 0.12, 0.18, 0.24, 0.30, 0.36, 0.42] + ([0.48, 0.54, 0.60] if top > 0.5 else []) + [top]
        o = put(loft(f"Outfit_Sock.{side}", [leg_ring(sx, z, 20, 0.004) for z in zs], mats=[st]))
        subsurf(o, 1)
        put(loft(f"Outfit_SockTop.{side}", [leg_ring(sx, z, 20, 0.0065) for z in (top - 0.016, top - 0.008, top)], mats=[st]))
    # criss-cross ribbons on the right stocking
    p = 0.16
    for k, sgn in enumerate((1, -1)):
        pts, nr = [], []
        z = 0.605
        while z >= 0.075:
            th = -math.pi / 2 + sgn * TAU * (z - 0.605) / p
            q = leg_point(-1, z, th, 0.0085)
            pts.append(q); nr.append(q - leg_center(-1, z)); z -= 0.006
        put(strip(f"Outfit_Ribbon{k}", pts, [0.013] * len(pts), nr, thick=0.002, mats=[rb]))
    # loafers + bows
    sh, bw = M("shoe"), M("bow")
    S = [(0.050, 0.068, 0.033), (0.034, 0.088, 0.039), (0.0, 0.094, 0.043), (-0.04, 0.082, 0.046),
         (-0.08, 0.064, 0.047), (-0.118, 0.050, 0.044), (-0.145, 0.038, 0.035), (-0.162, 0.025, 0.022)]
    for side, sx in (("L", 1), ("R", -1)):
        cx = leg_center(sx, 0.05).x
        rings = []
        for y, h, w in S:
            r = []
            for j in range(20):
                a = TAU * j / 20
                xx, zz = superellipse(w, h / 2, a, 3.0, 3.0)
                r.append(Vector((cx + xx, y, h / 2 + zz)))
            rings.append(r)
        o = put(loft(f"Outfit_Shoe.{side}", rings, cap0=True, cap1=True, mats=[sh])); subsurf(o, 1)
        # sole
        put(box(f"Outfit_Sole.{side}", (cx, -0.056, 0.005), (0.090, 0.218, 0.010), mats=[M("tie")]))
        # bow on the instep
        base = Vector((cx, -0.056, 0.090))
        for k, s2 in enumerate((-1, 1)):
            o = ellipsoid(f"Outfit_BowLobe{k}.{side}", (0, 0, 0), (0.019, 0.007, 0.013), n=12, rings=6, mats=[bw])
            o.location = base + Vector((s2 * 0.018, 0, 0.003)); o.rotation_euler = (0, s2 * -0.35, 0); put(o)
            put(strip(f"Outfit_BowTail{k}.{side}", [base, base + Vector((s2 * 0.008, -0.003, -0.012)),
                                                     base + Vector((s2 * 0.013, -0.006, -0.022))],
                      [0.007, 0.008, 0.006], [(0, -1, 0.3)] * 3, thick=0.0025, mats=[bw]))
        o = ellipsoid(f"Outfit_BowKnot.{side}", (0, 0, 0), (0.0075, 0.0085, 0.0085), n=10, rings=6, mats=[bw])
        o.location = base + Vector((0, -0.002, 0.002)); put(o)

# ------------------------------------------------------------------ glove cuffs
def build_gloves():
    gl = M("glove")
    for side, sx in (("L", 1), ("R", -1)):
        pts = [(sx * x, 0.004, 1.203) for x in (0.522, 0.538, 0.556)]
        put(tube(f"Outfit_GloveCuff.{side}", pts, [(0.022, 0.028), (0.0225, 0.0285), (0.021, 0.027)], n=16,
                 normals=[(0, 0, 1)] * 3, cap0=False, cap1=False, mats=[gl]))

def build():
    clear_collection(C)
    coll(C, coll())
    build_dress(); build_jacket(); build_neck(); build_belts(); build_legs(); build_gloves()
