# Tachi + sheath. Sword and sheath are separate objects, each parented to its own empty:
#   Tachi_Sword  (empty at the grip, +Y points to the pommel)  -> hilt, guard, blade
#   Tachi_Sheath (empty at the sheath mouth)                    -> sheath
# Sheathed on her LEFT hip, hilt forward, sheath angled down and back.
import math, importlib
from mathutils import Vector, Matrix
import lib, palette; importlib.reload(lib); importlib.reload(palette)
from lib import *
P = palette.P
C = "Tachi"
TAU = 2 * math.pi

MOUTH = Vector((0.165, -0.090, 0.938))
TIP = Vector((0.262, 0.560, 0.600))
L_SHEATH = (TIP - MOUTH).length
U = (MOUTH - TIP).normalized()                  # points toward the hilt
CV = (Vector((0, 0, 1)) - Vector((0, 0, 1)).dot(U) * U).normalized()   # curvature direction (up)
BV = U.cross(CV)

def M(key, **kw):
    b, s = P[key]; return toon("MAT_" + key, b, s, **kw)

def put(o):
    c = coll(C, coll())
    for uc in list(o.users_collection): uc.objects.unlink(o)
    c.objects.link(o); return o

def axis(s, lo, hi, sori=0.016):
    t = (s - lo) / (hi - lo)
    return MOUTH + U * s + CV * (sori * math.sin(math.pi * t))

def section_rings(ss, rc, rb, lo, hi, n=24, sori=0.016, prof=None):
    rings = []
    for s in ss:
        c = axis(s, lo, hi, sori)
        k = prof(s) if prof else 1.0
        rings.append([c + CV * (rc * k * math.cos(TAU * j / n)) + BV * (rb * k * math.sin(TAU * j / n)) for j in range(n)])
    return rings

def build():
    clear_collection(C)
    coll(C, coll())
    white, red, gold, hred, blade = M("sheath"), M("hilt_red"), M("gold"), M("hilt_red"), M("blade")
    lo, hi = -L_SHEATH, 0.25
    # ---------------- sheath
    L = L_SHEATH
    marks = [-L, -L + 0.004, -L + 0.055, -L + 0.068, -0.30, -0.15, -0.088, -0.078, -0.070, -0.014, 0.0]
    ss = []
    for a, b in zip(marks, marks[1:]):
        steps = max(1, int((b - a) / 0.02))
        ss += [a + (b - a) * k / steps for k in range(steps)]
    ss.append(0.0)
    def prof(s):
        return 0.72 if s == -L else (0.92 if s < -L + 0.004 else 1.0)
    rings = section_rings(ss, 0.0175, 0.0115, lo, hi, prof=prof)
    sh = put(loft("Tachi_SheathMesh", rings, cap0=True, cap1=True, mats=[white, red, gold]))
    for p in sh.data.polygons:
        s = (p.center - MOUTH).dot(U)
        if s < -L + 0.055: p.material_index = 1
        elif s < -L + 0.068: p.material_index = 2
        elif -0.088 < s < -0.078: p.material_index = 2
        elif -0.078 <= s < -0.014: p.material_index = 1
        elif s >= -0.014: p.material_index = 2
        else: p.material_index = 0
    # ---------------- guard (ornate quatrefoil tsuba)
    n = 64
    def tsuba_ring(s, scale=1.0):
        c = axis(s, lo, hi)
        out = []
        for j in range(n):
            th = TAU * j / n
            r = (0.029 + 0.0065 * math.cos(4 * th) + 0.0015 * math.cos(12 * th)) * scale
            out.append(c + CV * (r * math.cos(th)) + BV * (r * 0.92 * math.sin(th)))
        return out
    put(loft("Tachi_Guard", [tsuba_ring(0.0015, 0.94), tsuba_ring(0.003), tsuba_ring(0.007), tsuba_ring(0.0085, 0.94)],
             cap0=True, cap1=True, mats=[gold]))
    # habaki / seppa
    put(loft("Tachi_Seppa", section_rings([0.0085, 0.013], 0.0175, 0.0135, lo, hi), cap0=True, cap1=True, mats=[gold]))
    # ---------------- hilt: red wrap with gold diamonds, gold fuchi + kashira
    ss = [0.013 + k * 0.0022 for k in range(int((0.232 - 0.013) / 0.0022) + 1)] + [0.236, 0.242, 0.247, 0.250]
    def hprof(s):
        if s > 0.236: return 1.08 - 0.9 * ((s - 0.236) / 0.014) ** 2.5
        return 1.0 - 0.06 * math.sin(math.pi * (s - 0.013) / 0.22)
    rings = section_rings(ss, 0.0140, 0.0112, lo, hi, n=28, prof=hprof)
    hl = put(loft("Tachi_Hilt", rings, cap0=True, cap1=True, mats=[hred, gold]))
    for p in hl.data.polygons:
        q = p.center
        s = (q - MOUTH).dot(U)
        c = axis(s, lo, hi)
        d = q - c
        th = math.atan2(d.dot(BV), d.dot(CV))
        if s < 0.022 or s > 0.226:
            p.material_index = 1; continue
        per = 0.024
        f = ((s - 0.022) / per) % 1.0
        dist = min(abs(th - math.pi / 2), abs(th + math.pi / 2))  # diamonds centered on both flat faces
        p.material_index = 1 if (abs(f - 0.5) * 2 + dist / 0.95) < 0.85 else 0
    # ---------------- blade (inside the sheath when sheathed)
    ss = [-0.70 + k * 0.025 for k in range(29)]
    def bprof(s):
        return max(0.04, min(1.0, (s + 0.70) / 0.05))
    rings = []
    for s in ss:
        c = axis(s, lo, hi); k = bprof(s)
        w = 0.0145 * k; t = 0.0028 * k
        rings.append([c + CV * (0.004 * k), c + BV * t, c - CV * w, c - BV * t])
    put(loft("Tachi_Blade", rings, cap0=True, cap1=True, mats=[blade], smooth=False))

    # ---------------- empties + parenting
    def empty(name, loc):
        lib.remove(name)
        e = bpy.data.objects.new(name, None); e.empty_display_type = 'ARROWS'; e.empty_display_size = 0.08
        coll(C, coll()).objects.link(e)
        R = U.to_track_quat('Y', 'Z').to_matrix().to_4x4()
        e.matrix_world = Matrix.Translation(loc) @ R
        return e
    grip = empty("Tachi_Sword", axis(0.12, lo, hi))
    sheath = empty("Tachi_Sheath", MOUTH)
    bpy.context.view_layer.update()
    for o in bpy.data.collections[C].objects:
        if o.type != 'MESH': continue
        par = sheath if o.name == "Tachi_SheathMesh" else grip
        o.parent = par
        o.matrix_parent_inverse = par.matrix_world.inverted()
