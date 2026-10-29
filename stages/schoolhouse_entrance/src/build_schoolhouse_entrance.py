# Old Schoolhouse -Entrance- - 3D stage build script (Blender 5.x, runs in --background).
# The old schoolhouse's entrance hall at night: a raised stair between stone balustrades with a dark marble
# block at its foot, a gallery with small windows and two lanterns above it, big arches and timber beams,
# carved stone pillars, brick side bays with tall windows, heavy wooden doors, and moonlight falling through
# the windows onto a polished slate floor.
#
#   blender --background --factory-startup --python run_se.py -- STEPS=build,bake,preview,export CAMS=CAM_mid
#
# Layout is written in GODOT coordinates (x right, y up, +z toward the camera) and converted
# to Blender (Z-up) by G():  Godot (x, y, z) -> Blender (x, -z, y).  1 unit = 1 m.
# Baked groups (atlases): SE_Walls, SE_Detail, SE_Ceiling, SE_Floor (light map only)
# Card groups (Godot shaders): SE_Window, SE_Glow (emit in the bake), SE_Beam (moonbeams, not baked)
import bpy, bmesh, math, random
from mathutils import Vector, Matrix

ROOT = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\stages\schoolhouse_entrance"
TEXD = ROOT + r"\src\tex"
VARIANT = globals().get("VARIANT") or "night"

# ---------------- layout (Godot space, metres) ----------------
FLOOR_X = 18.0                     # floor quad: x +-18, z -24.5..+16
FLOOR_BACK, FLOOR_FRONT = -24.5, 16.0
LANE_X, LANE_Z = 12.5, -9.0        # keep |x| < 12.5 and z > -9 clear (fight lane)
CENTER_Z = -6.0
WALL_T = 0.7
H_GAL, H_TOP, H_CEIL = 4.6, 10.2, 13.2     # gallery line (string course), top cornice, ceiling
BX, BZ = 9.0, -24.0                # back wall: x +-9 at z -24
CX, CZ = 17.0, -18.0               # outer corners (angled bays run from here to the back wall)
FRONT_Z = 9.0                      # the side walls run from the outer corners to here
STAIR_HW, STAIR_Z0, STAIR_Y0 = 1.9, -19.6, 2.3     # stair half-width, front of the first step, its height
MOON = (0.62, -0.68, 0.34)         # moonlight through the LEFT windows (Godot direction); the right side mirrors x

V = dict(world=("#16243e", 0.9), moon=(7.0, "#a8c0ff"), fill=(4200, "#5a72a8"), top=(2600, "#43567e"),
         window_color="#b8d0ff", window_emit=3.2, lantern_w=170, lantern_color="#ffb060")

def srgb(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c)

def G(x, y, z):
    return Vector((x, -z, y))

def reset():
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.cameras,
                 bpy.data.lights, bpy.data.collections, bpy.data.node_groups, bpy.data.worlds):
        for d in list(coll):
            coll.remove(d)
    for im in list(bpy.data.images):
        if im.name not in ("Render Result", "Viewer Node"):
            bpy.data.images.remove(im)

COLS = {}
def col(name):
    if name not in COLS:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
        COLS[name] = c
    return COLS[name]

# ======================================================================
#  mesh builder: one bmesh per group
# ======================================================================
class Group:
    def __init__(self, name, coll="Stage"):
        self.name, self.coll = name, coll
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("Tex")
        self.custom = self.bm.faces.layers.int.new("custom_uv")
        self.mats = []

    def mi(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def finish(self):
        bm = self.bm
        bm.normal_update()
        for f in bm.faces:
            if f[self.custom]:
                continue
            n = f.normal; ax = max(range(3), key=lambda i: abs(n[i]))
            for l in f.loops:
                p = l.vert.co
                if ax == 0:   l[self.uv].uv = (p.y * (1 if n.x > 0 else -1), p.z)
                elif ax == 1: l[self.uv].uv = (p.x * (-1 if n.y > 0 else 1), p.z)
                else:         l[self.uv].uv = (p.x, p.y)
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me); bm.free()
        for m in self.mats:
            me.materials.append(MATS[m])
        o = bpy.data.objects.new(self.name, me)
        col(self.coll).objects.link(o)
        return o

GR = {}
def grp(name, coll="Stage"):
    if name not in GR:
        GR[name] = Group(name, coll)
    return GR[name]

def _tag(g, faces, m):
    idx = g.mi(m)
    for f in faces:
        f.material_index = idx
    return faces

def obox(g, center, size, rot_y=0.0, m="Stone", bevel=0.0):
    """Box at Godot `center` with Godot `size` (x, y, z), turned rot_y degrees about the vertical."""
    g = grp(g) if isinstance(g, str) else g
    M = Matrix.Translation(G(*center)) @ Matrix.Rotation(math.radians(rot_y), 4, 'Z') @ \
        Matrix.Diagonal((size[0], size[2], size[1], 1.0))
    r = bmesh.ops.create_cube(g.bm, size=1.0, matrix=M)
    verts = r["verts"]
    _tag(g, list({f for v in verts for f in v.link_faces}), m)
    if bevel > 0:
        edges = list({e for v in verts for e in v.link_edges})
        b = min(bevel, 0.45 * min(size))
        res = bmesh.ops.bevel(g.bm, geom=verts + edges, offset=b, segments=1, affect='EDGES',
                              profile=0.5, clamp_overlap=True)
        _tag(g, res["faces"], m)

def box(g, x, y0, y1, z, wx, wz, m="Stone", bevel=0.0, rot_y=0.0):
    """Box standing from y0 to y1, centred on (x, z), wx by wz wide."""
    obox(g, (x, (y0 + y1) / 2, z), (wx, y1 - y0, wz), rot_y, m, bevel)

def cyl(g, x, y0, z, r1, r2, h, m="Stone", seg=8, rot=0.0):
    """Vertical cone / cylinder from y0 up by h (seg = 4 -> pyramid)."""
    g = grp(g) if isinstance(g, str) else g
    M = Matrix.Translation(G(x, y0 + h / 2, z)) @ Matrix.Rotation(math.radians(rot), 4, 'Z')
    r = bmesh.ops.create_cone(g.bm, cap_ends=True, cap_tris=False, segments=seg,
                              radius1=r1, radius2=r2, depth=h, matrix=M)
    _tag(g, list({f for v in r["verts"] for f in v.link_faces}), m)

def cone_dir(g, base, d, r, L, m="Metal", seg=6):
    """Cone from Godot point `base` pointing along Godot direction d (spike)."""
    g = grp(g) if isinstance(g, str) else g
    dv = Vector((d[0], -d[2], d[1])).normalized()
    q = dv.to_track_quat('Z', 'Y')
    M = Matrix.Translation(G(*base) + dv * (L / 2)) @ q.to_matrix().to_4x4()
    r = bmesh.ops.create_cone(g.bm, cap_ends=True, cap_tris=False, segments=seg,
                              radius1=r, radius2=0.0, depth=L, matrix=M)
    _tag(g, list({f for v in r["verts"] for f in v.link_faces}), m)

def quad(g, pts, uvs, m):
    g = grp(g) if isinstance(g, str) else g
    vs = [g.bm.verts.new(G(*p)) for p in pts]
    f = g.bm.faces.new(vs)
    f.material_index = g.mi(m); f[g.custom] = 1
    for l, uv in zip(f.loops, uvs):
        l[g.uv].uv = uv
    return f

def octa_prism(g, cx, cz, r, y0, y1, m="Stone", seg=8, rot=22.5):
    cyl(g, cx, y0, cz, r / math.cos(math.pi / seg), r / math.cos(math.pi / seg), y1 - y0, m, seg, rot)

def polar(r, th, y=0.0):
    """Godot point at radius r / angle th (0 = straight ahead of the camera) around the platform centre."""
    return (r * math.sin(th), y, CENTER_Z - r * math.cos(th))

# ======================================================================
#  materials
# ======================================================================
MATS = {}

class NB:
    def __init__(self, name):
        self.m = bpy.data.materials.new(name); self.m.use_nodes = True
        self.nt = self.m.node_tree; self.nt.nodes.clear()
        self.out = self.n("ShaderNodeOutputMaterial", (1100, 0))
        self.bsdf = self.n("ShaderNodeBsdfPrincipled", (700, 0))
        self.nt.links.new(self.bsdf.outputs[0], self.out.inputs[0])
        uvn = self.n("ShaderNodeUVMap", (-1400, 0)); uvn.uv_map = "Tex"
        self.uv = uvn.outputs[0]
        geo = self.n("ShaderNodeNewGeometry", (-1400, -300))
        self.pos = geo.outputs["Position"]; self.normal = geo.outputs["Normal"]
        MATS[name] = self.m

    def n(self, t, loc=(0, 0), **kw):
        nd = self.nt.nodes.new(t); nd.location = loc
        for k, v in kw.items():
            setattr(nd, k, v)
        return nd

    def link(self, a, b):
        self.nt.links.new(a, b)

    def math(self, op, a, b=None):
        nd = self.n("ShaderNodeMath", operation=op)
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                nd.inputs[i].default_value = v
            else:
                self.link(v, nd.inputs[i])
        return nd.outputs[0]

    def noise(self, vec, scale, detail=4, rough=0.55):
        nd = self.n("ShaderNodeTexNoise"); nd.inputs["Scale"].default_value = scale
        nd.inputs["Detail"].default_value = detail; nd.inputs["Roughness"].default_value = rough
        self.link(vec, nd.inputs["Vector"])
        return nd

    def ramp(self, fac, stops):
        nd = self.n("ShaderNodeValToRGB"); cr = nd.color_ramp
        while len(cr.elements) < len(stops):
            cr.elements.new(0.5)
        for e, (p, c) in zip(cr.elements, stops):
            e.position = p; e.color = (*srgb(c), 1)
        self.link(fac, nd.inputs[0])
        return nd.outputs[0]

    def mixc(self, a, b, fac, blend='MIX'):
        nd = self.n("ShaderNodeMix"); nd.data_type = 'RGBA'; nd.blend_type = blend
        for sock, v in ((0, fac), (6, a), (7, b)):
            if isinstance(v, (int, float)):
                nd.inputs[sock].default_value = v
            elif isinstance(v, str):
                nd.inputs[sock].default_value = (*srgb(v), 1)
            else:
                self.link(v, nd.inputs[sock])
        return nd.outputs[2]

    def image(self, fn, vec, extension='REPEAT', non_color=False):
        im = self.n("ShaderNodeTexImage"); im.image = bpy.data.images.load(TEXD + "\\" + fn, check_existing=True)
        im.extension = extension
        if non_color:
            im.image.colorspace_settings.name = 'Non-Color'
        self.link(vec, im.inputs[0])
        return im

def beam(g, p0, p1, w, h, m="Metal"):
    """Square bar from Godot point p0 to p1 (w across, h tall)."""
    g = grp(g) if isinstance(g, str) else g
    a, b = G(*p0), G(*p1); d = b - a; L = d.length
    q = d.normalized().to_track_quat('Z', 'Y')
    M = Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4() @ Matrix.Diagonal((w, h, L, 1.0))
    r = bmesh.ops.create_cube(g.bm, size=1.0, matrix=M)
    _tag(g, list({f for v in r["verts"] for f in v.link_faces}), m)

def tube(g, pts, r, m="Pipe", seg=10):
    """Round pipe along a polyline of Godot points (smooth joints from overlapping segments + ball joints)."""
    g = grp(g) if isinstance(g, str) else g
    for a, b in zip(pts[:-1], pts[1:]):
        A, B = G(*a), G(*b); d = B - A
        q = d.normalized().to_track_quat('Z', 'Y')
        M = Matrix.Translation((A + B) / 2) @ q.to_matrix().to_4x4()
        rr = bmesh.ops.create_cone(g.bm, cap_ends=False, cap_tris=False, segments=seg, radius1=r, radius2=r, depth=d.length, matrix=M)
        _tag(g, list({f for v in rr["verts"] for f in v.link_faces}), m)
    for p in pts[1:-1]:
        rr = bmesh.ops.create_uvsphere(g.bm, u_segments=seg, v_segments=6, radius=r * 1.0, matrix=Matrix.Translation(G(*p)))
        _tag(g, list({f for v in rr["verts"] for f in v.link_faces}), m)

def arc_pts(c, r, a0, a1, n, plane="xy"):
    """Points on a circular arc around Godot point c (plane xy: bends up/over in x-y)."""
    out = []
    for k in range(n + 1):
        a = a0 + (a1 - a0) * k / n
        if plane == "xy":
            out.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a), c[2]))
        else:
            out.append((c[0], c[1] + r * math.sin(a), c[2] + r * math.cos(a)))
    return out


# ======================================================================
#  shape helpers
# ======================================================================
def lathe(g, x, y0, z, prof, seg=12, m="Iron", rot=0.0):
    """Surface of revolution around the vertical through (x, z). prof = [(radius, height), ...] bottom -> top,
    starting and ending at radius 0 so it is closed."""
    gg = grp(g) if isinstance(g, str) else g; bm = gg.bm
    rings = []
    for (r, y) in prof:
        if r < 1e-4:
            rings.append([bm.verts.new(G(x, y0 + y, z))])
        else:
            rings.append([bm.verts.new(G(x + r * math.cos(2 * math.pi * i / seg + rot), y0 + y, z + r * math.sin(2 * math.pi * i / seg + rot)))
                          for i in range(seg)])
    faces = []
    for A, B in zip(rings[:-1], rings[1:]):
        if len(A) == 1 and len(B) == 1:
            continue
        if len(A) == 1:
            faces += [bm.faces.new((A[0], B[(i + 1) % seg], B[i])) for i in range(seg)]
        elif len(B) == 1:
            faces += [bm.faces.new((A[i], A[(i + 1) % seg], B[0])) for i in range(seg)]
        else:
            faces += [bm.faces.new((A[i], A[(i + 1) % seg], B[(i + 1) % seg], B[i])) for i in range(seg)]
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    _tag(gg, faces, m)
    return faces

def torus(g, center, R, r, rot=None, nR=16, nr=5, m="Iron"):
    gg = grp(g) if isinstance(g, str) else g; bm = gg.bm
    M = Matrix.Translation(G(*center)) @ (rot if rot is not None else Matrix.Identity(4))
    rings = []
    for i in range(nR):
        a = 2 * math.pi * i / nR
        rings.append([bm.verts.new(M @ Vector(((R + r * math.cos(2 * math.pi * j / nr)) * math.cos(a),
                                                (R + r * math.cos(2 * math.pi * j / nr)) * math.sin(a),
                                                r * math.sin(2 * math.pi * j / nr)))) for j in range(nr)])
    faces = []
    for i in range(nR):
        A, B = rings[i], rings[(i + 1) % nR]
        for j in range(nr):
            k = (j + 1) % nr
            faces.append(bm.faces.new((A[j], B[j], B[k], A[k])))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    _tag(gg, faces, m)

def hexa(g, pts, m):
    """A closed six-sided solid from 8 Godot points: bottom ring (4) then the matching top ring (4)."""
    gg = grp(g) if isinstance(g, str) else g; bm = gg.bm
    v = [bm.verts.new(G(*p)) for p in pts]
    b, t = v[:4], v[4:]
    faces = [bm.faces.new((b[3], b[2], b[1], b[0])), bm.faces.new((t[0], t[1], t[2], t[3]))]
    for i in range(4):
        j = (i + 1) % 4
        faces.append(bm.faces.new((b[i], b[j], t[j], t[i])))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    _tag(gg, faces, m)
    return faces

def _card_uv(gg, faces, fid, h=0.5):
    """Mark faces as custom-UV (kept by Group.finish) with Blender v = id + h (shaders read the id)."""
    for f in faces:
        f[gg.custom] = 1
        for l in f.loops:
            l[gg.uv].uv = (0.5, fid + h)

class Seg:
    """One straight wall. t runs along it from A to B, `off` is the distance in front of its inner face."""
    def __init__(self, A, B):
        self.A, self.B = A, B
        dx, dz = B[0] - A[0], B[1] - A[1]
        self.L = math.hypot(dx, dz); self.d = (dx / self.L, dz / self.L)
        n1 = (self.d[1], -self.d[0])
        mx, mz = (A[0] + B[0]) / 2, (A[1] + B[1]) / 2
        self.n = n1 if n1[0] * (0 - mx) + n1[1] * (CENTER_Z - mz) > 0 else (-n1[0], -n1[1])
        self.rot = math.degrees(math.atan2(-self.d[1], self.d[0]))

    def P(self, t, y, off=0.0):
        return (self.A[0] + self.d[0] * t + self.n[0] * off, y, self.A[1] + self.d[1] * t + self.n[1] * off)

    def box(self, g, t0, t1, y0, y1, off0, off1, m, bevel=0.0):
        obox(g, self.P((t0 + t1) / 2, (y0 + y1) / 2, (off0 + off1) / 2), (t1 - t0, y1 - y0, off1 - off0), self.rot, m, bevel)

    def quad(self, g, t0, t1, y0, y1, off, uvs, m):
        return quad(g, [self.P(t0, y0, off), self.P(t1, y0, off), self.P(t1, y1, off), self.P(t0, y1, off)], uvs, m)

def wall_prism(g, s, pts, off0, off1, m):
    """A convex outline drawn on the wall (pts = [(t, y), ...]) pushed out from off0 to off1."""
    gg = grp(g) if isinstance(g, str) else g; bm = gg.bm
    F = [bm.verts.new(G(*s.P(t, y, off1))) for t, y in pts]
    B = [bm.verts.new(G(*s.P(t, y, off0))) for t, y in pts]
    faces = [bm.faces.new(F), bm.faces.new(B[::-1])]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((F[i], B[i], B[j], F[j])))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    _tag(gg, faces, m)
    return faces

def wall_band(g, s, inner, outer, off0, off1, m):
    """An open strip on the wall between two matching polylines (a door frame, an arch), from off0 to off1."""
    for i in range(len(inner) - 1):
        wall_prism(g, s, [inner[i], inner[i + 1], outer[i + 1], outer[i]], off0, off1, m)

def arch(s, t0, t1, y_spring, y_crown, thick, off0, off1, m="Timber", n=16, g="SE_Detail"):
    """A segmental arch band on the wall, springing at t0 / t1."""
    a = (t1 - t0) / 2; sag = y_crown - y_spring
    R = (a * a + sag * sag) / (2 * sag); cy = y_crown - R; tc = (t0 + t1) / 2
    ph = math.asin(min(1.0, a / R))
    inner = [(tc + R * math.sin(-ph + 2 * ph * k / n), cy + R * math.cos(-ph + 2 * ph * k / n)) for k in range(n + 1)]
    outer = [(tc + (R + thick) * math.sin(-ph + 2 * ph * k / n), cy + (R + thick) * math.cos(-ph + 2 * ph * k / n)) for k in range(n + 1)]
    wall_band(g, s, inner, outer, off0, off1, m)
    return R, cy, tc

# ======================================================================
#  materials
# ======================================================================
def plain(name, dark, light, scale=3.0, rough=0.6, emit=0.0):
    b = NB(name)
    n = b.noise(b.pos, scale, 4, 0.55)
    c = b.ramp(n.outputs["Fac"], [(0.3, dark), (0.7, light)])
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = rough
    if emit > 0:
        b.link(c, b.bsdf.inputs["Emission Color"]); b.bsdf.inputs["Emission Strength"].default_value = emit
    return b

def blocks(name, c1, c2, mortar, bw, bh, ms=0.012, scale_noise=1.5, rough=0.7, vary=0.35):
    """Bricks / stone blocks from the Tex UV (metres)."""
    b = NB(name)
    br = b.n("ShaderNodeTexBrick"); br.offset = 0.5
    for k, v in (("Scale", 1.0), ("Mortar Size", ms), ("Brick Width", bw), ("Row Height", bh), ("Mortar Smooth", 0.15)):
        br.inputs[k].default_value = v
    br.inputs["Bias"].default_value = 0.0
    br.inputs["Color1"].default_value = (*srgb(c1), 1); br.inputs["Color2"].default_value = (*srgb(c2), 1)
    br.inputs["Mortar"].default_value = (*srgb(mortar), 1)
    b.link(b.uv, br.inputs["Vector"])
    n = b.noise(b.pos, scale_noise, 5, 0.6)
    c = b.mixc(br.outputs["Color"], b.ramp(n.outputs["Fac"], [(0.3, "#b8b8b8"), (0.7, "#ffffff")]), vary, 'MULTIPLY')
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = rough
    return b

def wood(name, dark, light, plank=0.28, rough=0.6):
    b = NB(name)
    n = b.noise(b.pos, 6.0, 4, 0.6)
    c = b.ramp(n.outputs["Fac"], [(0.3, dark), (0.7, light)])
    w = b.n("ShaderNodeTexWave"); w.wave_type = 'BANDS'; w.bands_direction = 'X'
    w.inputs["Scale"].default_value = 1.0 / plank * 0.5; w.inputs["Distortion"].default_value = 0.5
    b.link(b.uv, w.inputs["Vector"])
    seam = b.math('LESS_THAN', w.outputs["Fac"], 0.06)
    c = b.mixc(c, "#120c08", b.math('MULTIPLY', seam, 0.8))
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = rough
    return b

def marble(name, dark, light, vein):
    b = NB(name)
    n = b.noise(b.pos, 0.9, 5, 0.6)
    c = b.ramp(n.outputs["Fac"], [(0.25, dark), (0.75, light)])
    vn = b.noise(b.pos, 0.6, 6, 0.65); vn.inputs["Distortion"].default_value = 3.5
    d = b.math('ABSOLUTE', b.math('SUBTRACT', vn.outputs["Fac"], 0.5))
    mr = b.n("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 0.0; mr.inputs["From Max"].default_value = 0.03
    mr.inputs["To Min"].default_value = 0.8; mr.inputs["To Max"].default_value = 0.0; b.link(d, mr.inputs[0])
    c = b.mixc(c, vein, mr.outputs[0])
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = 0.25
    return b

def emit_solid(name, color, strength):
    b = NB(name)
    em = b.n("ShaderNodeEmission"); em.inputs["Color"].default_value = (*srgb(color), 1); em.inputs["Strength"].default_value = strength
    b.link(em.outputs[0], b.out.inputs[0])
    return b

def build_materials():
    blocks("Brick", "#4a3226", "#5c3e2c", "#1e1814", 0.26, 0.085, 0.012, 2.0)
    blocks("StoneBlock", "#2a3038", "#343b45", "#14171c", 0.9, 0.45, 0.01, 1.2)
    plain("Stone", "#3e444e", "#555c68", 2.0, 0.6)
    plain("StoneLight", "#5a616c", "#747b86", 2.5, 0.55)
    plain("StoneDark", "#262a32", "#343a44", 2.0, 0.65)
    marble("Marble", "#1c2026", "#2e343c", "#5c646e")
    plain("Timber", "#221a14", "#33281e", 5.0, 0.7)
    wood("DoorWood", "#3a2416", "#5a3a22", 0.26)
    wood("Planks", "#1e1610", "#2e2218", 0.3)
    plain("Iron", "#16181c", "#262a30", 8.0, 0.45)
    plain("Brass", "#5a4424", "#806238", 8.0, 0.4)
    b = NB("FloorSlate"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#5a606c"), 1); b.bsdf.inputs["Roughness"].default_value = 0.4
    emit_solid("WindowCard", V["window_color"], V["window_emit"])
    emit_solid("GlowLantern", "#ffb868", 4.5)
    emit_solid("BeamCard", "#a8c0ff", 0.0)
    b = NB("Stand_P1"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#2d6cdf"), 1)
    b = NB("Stand_P2"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#e0463a"), 1)

# ======================================================================
#  the hall
# ======================================================================
WINDOWS = []       # window card ids
BEAMS = []         # moonbeam card ids
LANTERNS = []      # (x, y, z) lantern glass centres (bake lights, Godot flicker)

def build_wall(s, openings, low="StoneBlock", mid="Brick", up="Brick"):
    """Wall from y -0.2 up to the ceiling with rectangular holes. openings = [(t0, t1, y0, y1), ...]."""
    g = "SE_Walls"
    ys = sorted(set([-0.2, 1.0, H_GAL, H_CEIL + 0.2] + [y for o in openings for y in (o[2], o[3])]))
    for ya, yb in zip(ys[:-1], ys[1:]):
        holes = sorted((o[0], o[1]) for o in openings if o[2] <= ya + 1e-6 and o[3] >= yb - 1e-6)
        m = low if yb <= 1.0 + 1e-6 else (mid if yb <= H_GAL + 1e-6 else up)
        t = 0.0
        for (h0, h1) in holes + [(s.L, s.L)]:
            if h0 - t > 0.005:
                s.box(g, t, h0, ya, yb, -WALL_T, 0.0, m)
            t = max(t, h1)

def plinth(s, skip=()):
    """The stepped stone ledge along the foot of the wall."""
    g = "SE_Walls"
    t = 0.0
    for (a, b) in sorted(skip) + [(s.L, s.L)]:
        if a - t > 0.05:
            s.box(g, t, a, 0.0, 0.42, 0.0, 1.0, "Stone")
            s.box(g, t, a, 0.36, 0.44, 0.96, 1.06, "StoneLight")
            s.box(g, t, a, 0.42, 0.7, 0.0, 0.55, "Stone")
            s.box(g, t, a, 0.64, 0.72, 0.5, 0.6, "StoneLight")
        t = max(t, b)

def courses(s, gallery=False):
    """String course at the gallery line and the top cornice."""
    g = "SE_Walls"
    if gallery:                                                               # the back gallery: a deep ledge
        s.box(g, 0.0, s.L, H_GAL - 0.4, H_GAL, 0.0, 1.4, "Stone")
        s.box(g, 0.0, s.L, H_GAL - 0.52, H_GAL - 0.36, 1.3, 1.52, "StoneLight")
        s.box(g, 0.0, s.L, H_GAL - 0.04, H_GAL + 0.04, 1.36, 1.5, "StoneLight")
    else:
        s.box(g, 0.0, s.L, H_GAL - 0.14, H_GAL + 0.26, 0.0, 0.34, "StoneLight")
        s.box(g, 0.0, s.L, H_GAL - 0.3, H_GAL - 0.14, 0.0, 0.2, "Stone")
    s.box(g, 0.0, s.L, H_TOP, H_TOP + 0.34, 0.0, 0.46, "StoneLight")
    s.box(g, 0.0, s.L, H_TOP + 0.34, H_TOP + 0.62, 0.0, 0.66, "Stone")
    s.box(g, 0.0, s.L, H_TOP - 0.16, H_TOP, 0.0, 0.26, "Stone")

def window(s, tc, w, y0, y1, moon=None):
    """A stone-framed window with an iron grid (2 x 3 panes), its glass card and, if moon is given, a moonbeam."""
    g = "SE_Detail"; hw = w / 2
    wid = len(WINDOWS); WINDOWS.append(s.P(tc, (y0 + y1) / 2, 0))
    s.quad("SE_Window", tc - hw, tc + hw, y0, y1, -WALL_T + 0.08, [(0, wid + 0.001), (1, wid + 0.001), (1, wid + 0.999), (0, wid + 0.999)], "WindowCard")
    s.box(g, tc - hw - 0.2, tc - hw, y0 - 0.12, y1 + 0.12, -0.05, 0.14, "StoneLight")
    s.box(g, tc + hw, tc + hw + 0.2, y0 - 0.12, y1 + 0.12, -0.05, 0.14, "StoneLight")
    s.box(g, tc - hw - 0.22, tc + hw + 0.22, y1, y1 + 0.24, -0.05, 0.17, "StoneLight")
    s.box(g, tc - 0.16, tc + 0.16, y1 + 0.02, y1 + 0.34, 0.0, 0.22, "Stone")                       # keystone
    s.box(g, tc - hw - 0.26, tc + hw + 0.26, y0 - 0.18, y0, -0.1, 0.26, "StoneLight")              # sill
    fo0, fo1 = -0.4, -0.34
    for x in (tc - hw + 0.03, tc, tc + hw - 0.03):
        s.box(g, x - 0.03, x + 0.03, y0, y1, fo0, fo1, "Iron")
    for k in range(4):
        y = y0 + 0.03 + (y1 - y0 - 0.06) * k / 3
        s.box(g, tc - hw, tc + hw, y - 0.03, y + 0.03, fo0, fo1, "Iron")
    if moon is not None:
        moonbeam(s, tc - hw, tc + hw, y0, y1, moon)

def moonbeam(s, t0, t1, y0, y1, D):
    """The light shaft from a window: the window rectangle swept along the moonlight down to the floor (4 sheets)."""
    bid = len(BEAMS); BEAMS.append((s.P((t0 + t1) / 2, y1, 0), D))
    def proj(p):
        k = p[1] / -D[1]
        return (p[0] + D[0] * k, 0.02, p[2] + D[2] * k)
    c = [s.P(t0, y1, -0.45), s.P(t1, y1, -0.45), s.P(t1, y0, -0.45), s.P(t0, y0, -0.45)]   # tl, tr, br, bl
    uv = [(0, bid + 0.001), (1, bid + 0.001), (1, bid + 0.999), (0, bid + 0.999)]
    for a, b in ((0, 1), (3, 2), (0, 3), (1, 2)):
        quad("SE_Beam", [c[a], c[b], proj(c[b]), proj(c[a])], uv, "BeamCard")

def lantern(p, n, arm=0.75, g="SE_Detail", k=1.5):
    """An iron wall lantern with a warm glass (SE_Glow id 0) hanging from a bracket. p = mount point on the wall.
    k scales the lantern."""
    x, y, z = p; nx, nz = n
    hx, hz = x + nx * arm, z + nz * arm
    def S(prof):
        return [(r * k, h * k) for r, h in prof]
    top = y + 0.55 * k
    obox(g, (x + nx * 0.03, y + 0.4 * k, z + nz * 0.03), (0.24 * k, 0.5 * k, 0.06), math.degrees(math.atan2(nx, nz)), "Iron")
    beam(g, (x + nx * 0.05, top, z + nz * 0.05), (hx, top, hz), 0.05 * k, 0.05 * k, "Iron")
    beam(g, (x + nx * 0.05, y + 0.2 * k, z + nz * 0.05), (hx - nx * 0.2 * k, top - 0.03, hz - nz * 0.2 * k), 0.035 * k, 0.035 * k, "Iron")
    beam(g, (hx, top, hz), (hx, y + 0.42 * k, hz), 0.03 * k, 0.03 * k, "Iron")
    lathe(g, hx, y - 0.36 * k, hz, S([(0, 0), (0.04, 0.0), (0.15, 0.09), (0.16, 0.13), (0, 0.13)]), 6, "Iron", math.pi / 6)
    gg = grp("SE_Glow", "Cards")
    _card_uv(gg, lathe(gg, hx, y - 0.23 * k, hz, S([(0, 0), (0.14, 0.0), (0.165, 0.36), (0, 0.36)]), 6, "GlowLantern", math.pi / 6), 0)
    for j in range(6):                                                         # the cage bars
        a = 2 * math.pi * j / 6 + math.pi / 6
        bx, bz = hx + 0.168 * k * math.cos(a), hz + 0.168 * k * math.sin(a)
        beam(g, (bx, y - 0.24 * k, bz), (bx, y + 0.14 * k, bz), 0.025 * k, 0.025 * k, "Iron")
    lathe(g, hx, y + 0.12 * k, hz, S([(0, 0), (0.21, 0.0), (0.2, 0.04), (0.11, 0.15), (0.05, 0.22), (0.07, 0.27), (0, 0.32)]), 6, "Iron", math.pi / 6)
    LANTERNS.append((hx, y, hz))

def carved_face(fs, w, y0, y1, depth=0.06):
    """Relief on a pillar face: a raised frame with a chain of diamonds and little side leaves."""
    g = "SE_Detail"
    a, b = 0.16, w - 0.16
    for (t0, t1, ya, yb) in ((a, a + 0.08, y0, y1), (b - 0.08, b, y0, y1), (a, b, y0, y0 + 0.08), (a, b, y1 - 0.08, y1)):
        fs.box(g, t0, t1, ya, yb, 0.0, depth, "StoneLight")
    tc = w / 2; y = y0 + 0.4
    while y < y1 - 0.4:
        wall_prism(g, fs, [(tc, y - 0.24), (tc + 0.2, y), (tc, y + 0.24), (tc - 0.2, y)], 0.0, depth + 0.02, "StoneLight")
        for sx in (-1, 1):
            wall_prism(g, fs, [(tc + sx * 0.26, y + 0.2), (tc + sx * 0.42, y + 0.3), (tc + sx * 0.3, y + 0.4)][::sx], 0.0, depth, "Stone")
        y += 0.62

def corner_pillar(p, a_seg, b_seg, w=1.6, lantern_y=None):
    """A massive square stone pillar in the corner where two walls meet: chamfered base, carved shaft, capital."""
    g = "SE_Detail"
    nx, nz = a_seg.n[0] + b_seg.n[0], a_seg.n[1] + b_seg.n[1]; L = math.hypot(nx, nz); nx, nz = nx / L, nz / L
    cx, cz = p[0] + nx * 0.75, p[1] + nz * 0.75
    rot = math.degrees(math.atan2(nx, nz))
    r2 = math.sqrt(2.0)
    obox(g, (cx, 0.55, cz), (w + 0.9, 1.1, w + 0.9), rot, "Stone", 0.03)
    cyl(g, cx, 1.1, cz, (w + 0.9) / 2 * r2, (w + 0.2) / 2 * r2, 0.5, "StoneLight", 4, rot + 45)
    obox(g, (cx, 5.6, cz), (w, 8.0, w), rot, "Stone")
    cyl(g, cx, 9.6, cz, (w + 0.1) / 2 * r2, (w + 0.6) / 2 * r2, 0.4, "StoneLight", 4, rot + 45)
    obox(g, (cx, 10.2, cz), (w + 0.6, 0.4, w + 0.6), rot, "StoneLight", 0.02)
    obox(g, (cx, (10.4 + H_CEIL) / 2, cz), (w + 0.2, H_CEIL - 10.4, w + 0.2), rot, "Stone")
    dx, dz = nz, -nx
    fx, fz = cx + nx * w / 2, cz + nz * w / 2
    fs = Seg((fx - dx * w / 2, fz - dz * w / 2), (fx + dx * w / 2, fz + dz * w / 2))
    carved_face(fs, w, 1.9, 9.3)
    if lantern_y is not None:
        lantern(fs.P(w / 2, lantern_y, 0.06), fs.n)
    return (cx, cz, nx, nz)

def wall_pillar(s, t, w=1.3, lantern_y=None):
    g = "SE_Detail"
    s.box(g, t - w / 2 - 0.3, t + w / 2 + 0.3, 0.0, 1.05, 0.0, 1.05, "Stone", 0.03)
    s.box(g, t - w / 2 - 0.12, t + w / 2 + 0.12, 1.05, 1.4, 0.0, 0.85, "StoneLight")
    s.box(g, t - w / 2, t + w / 2, 1.4, 9.6, 0.0, 0.72, "Stone")
    s.box(g, t - w / 2 - 0.15, t + w / 2 + 0.15, 9.6, 10.2, 0.0, 0.95, "StoneLight", 0.02)
    fs = Seg(s.P(t - w / 2, 0, 0.72)[0::2], s.P(t + w / 2, 0, 0.72)[0::2])
    carved_face(fs, w, 1.9, 9.2)
    if lantern_y is not None:
        lantern(fs.P(w / 2, lantern_y, 0.06), fs.n)

def door(s, tc):
    """Heavy wooden double door in a stone frame with a chamfered top, iron straps and ring handles."""
    g = "SE_Detail"
    outer = [(tc - 1.65, 0.0), (tc - 1.65, 3.9), (tc - 0.75, 4.95), (tc + 0.75, 4.95), (tc + 1.65, 3.9), (tc + 1.65, 0.0)]
    inner = [(tc - 1.3, 0.0), (tc - 1.3, 3.75), (tc - 0.6, 4.6), (tc + 0.6, 4.6), (tc + 1.3, 3.75), (tc + 1.3, 0.0)]
    wall_band(g, s, inner, outer, -WALL_T + 0.1, 0.22, "StoneLight")
    for sx in (-1, 1):                                                         # wall filling the corners above the frame
        wall_prism("SE_Walls", s, [(tc + sx * 1.65, 3.9), (tc + sx * 0.75, 4.95), (tc + sx * 1.65, 4.95)][::sx], -WALL_T, 0.0, "Brick")
    for sx in (-1, 1):                                                         # the two leaves
        pts = [(tc + sx * 1.3, 0.0), (tc, 0.0), (tc, 4.6), (tc + sx * 0.6, 4.6), (tc + sx * 1.3, 3.75)]
        wall_prism(g, s, pts if sx < 0 else pts[::-1], -0.36, -0.26, "DoorWood")
        for y in (0.7, 2.1, 3.4):
            a, b = sorted((tc + sx * 1.28, tc + sx * 0.04))
            s.box(g, a, b, y - 0.07, y + 0.07, -0.26, -0.22, "Iron")
            for k in range(5):
                tt = a + 0.1 + k * (b - a - 0.2) / 4
                s.box(g, tt - 0.03, tt + 0.03, y - 0.03, y + 0.03, -0.22, -0.19, "Iron")
        hx = tc + sx * 0.28
        torus(g, s.P(hx, 1.95, -0.2), 0.12, 0.018, Matrix.Rotation(math.radians(s.rot), 4, 'Z') @ Matrix.Rotation(math.radians(90), 4, 'X'), 14, 4)
        s.box(g, hx - 0.06, hx + 0.06, 2.0, 2.14, -0.26, -0.21, "Iron")
    s.box(g, tc - 1.7, tc + 1.7, 0.0, 0.12, -0.5, 0.7, "StoneLight")            # threshold
    s.box(g, tc - 0.18, tc + 0.18, 4.95, 5.35, 0.0, 0.26, "Stone")             # carved boss above

def build_stair():
    """The raised stair: a dark marble block at its foot, steps rising to the gallery, stone balustrades and newels."""
    g = "SE_Detail"; hw = STAIR_HW
    box(g, 0.0, 0.0, STAIR_Y0, (STAIR_Z0 + STAIR_Z0 + 2.0) / 2, 2 * hw, 2.0, "Marble")
    for (x, y0, y1, z, wx, wz) in ((0.0, 0.0, 0.1, STAIR_Z0 + 2.02, 2 * hw, 0.06), (0.0, STAIR_Y0 - 0.1, STAIR_Y0, STAIR_Z0 + 2.02, 2 * hw, 0.06),
                                   (-hw + 0.05, 0.0, STAIR_Y0, STAIR_Z0 + 2.02, 0.1, 0.06), (hw - 0.05, 0.0, STAIR_Y0, STAIR_Z0 + 2.02, 0.1, 0.06)):
        box(g, x, y0, y1, z, wx, wz, "StoneLight")
    n = 9; run = (STAIR_Z0 - BZ) / n; rise = (H_GAL - STAIR_Y0) / n
    for k in range(n):
        zf = STAIR_Z0 - run * k; yt = STAIR_Y0 + rise * (k + 1)
        box(g, 0.0, STAIR_Y0 - 0.3, yt, (zf + BZ) / 2, 2 * hw, zf - BZ, "Stone")
        box(g, 0.0, yt - 0.05, yt + 0.01, zf - 0.03, 2 * hw, 0.08, "StoneLight")
    zf, zb = STAIR_Z0 + 2.2, BZ
    for sx in (-1, 1):
        xi, xo = sx * hw, sx * (hw + 0.55)
        a, b = sorted((xi, xo))
        hexa(g, [(a, 0.0, zf), (b, 0.0, zf), (b, 0.0, zb), (a, 0.0, zb), (a, 2.95, zf), (b, 2.95, zf), (b, H_GAL + 0.95, zb), (a, H_GAL + 0.95, zb)], "Stone")
        a2, b2 = a - 0.08, b + 0.08
        hexa(g, [(a2, 2.9, zf), (b2, 2.9, zf), (b2, H_GAL + 0.9, zb), (a2, H_GAL + 0.9, zb),
                 (a2, 3.08, zf), (b2, 3.08, zf), (b2, H_GAL + 1.08, zb), (a2, H_GAL + 1.08, zb)], "StoneLight")
        xc = sx * (hw + 0.28)
        box(g, xc, 0.0, 3.05, zf + 0.35, 1.0, 1.0, "Stone", 0.02)
        box(g, xc, 3.05, 3.3, zf + 0.35, 1.18, 1.18, "StoneLight", 0.02)
        box(g, xc, 3.3, 3.5, zf + 0.35, 0.8, 0.8, "Stone")
        box(g, xc, 0.0, 0.5, zf + 0.35, 1.2, 1.2, "StoneLight", 0.02)

def build_room():
    S = {}
    for side, sx in (("L", -1), ("R", 1)):
        S["side" + side] = Seg((sx * CX, FRONT_Z), (sx * CX, CZ))
        S["bay" + side] = Seg((sx * CX, CZ), (sx * BX, BZ))
    S["back"] = Seg((-BX, BZ), (BX, BZ))
    back = S["back"]
    wins = [(2.25, 1.1), (5.45, 1.1), (9.0, 1.1), (12.55, 1.1), (15.75, 1.1)]
    build_wall(back, [(t - w / 2, t + w / 2, 6.1, 7.9) for t, w in wins], low="StoneBlock", mid="StoneBlock", up="Brick")
    for t, w in wins:
        window(back, t, w, 6.1, 7.9)
    plinth(back, [(6.4, 11.6)])
    courses(back, gallery=True)
    for t in (9 - 1.95, 9 + 1.95, 9 - 5.15, 9 + 5.15):                         # pilasters on the upper back wall
        back.box("SE_Walls", t - 0.26, t + 0.26, H_GAL, H_TOP, 0.0, 0.36, "Stone")
        back.box("SE_Walls", t - 0.34, t + 0.34, H_TOP - 0.5, H_TOP, 0.0, 0.44, "StoneLight")
    for t in (9 - 1.95, 9 + 1.95):
        lantern(back.P(t, 7.3, 0.36), back.n)
    arch(back, 0.6, back.L - 0.6, 8.3, 10.0, 0.75, 0.0, 0.9, "Timber")
    arch(back, 1.4, back.L - 1.4, 8.2, 9.55, 0.16, 0.0, 0.3, "StoneLight")
    for side, sx in (("L", -1), ("R", 1)):
        bay, sd = S["bay" + side], S["side" + side]
        moon = (MOON[0] if sx < 0 else -MOON[0], MOON[1], MOON[2])
        build_wall(bay, [(5.0 - 0.65, 5.0 + 0.65, 1.9, 4.0), (5.0 - 0.75, 5.0 + 0.75, 6.0, 8.6)])
        window(bay, 5.0, 1.3, 1.9, 4.0, moon)
        window(bay, 5.0, 1.5, 6.0, 8.6, moon)
        plinth(bay)
        courses(bay)
        arch(bay, 0.9, bay.L - 0.9, 8.95, 10.45, 0.6, 0.0, 0.7, "Timber", 12)
        # the side wall: lower windows, upper windows, a door, two wall pillars with lanterns
        lows, ups, door_t = (24.0, 11.5), (24.0, 19.5, 11.5, 4.5), 19.5
        ops = [(t - 0.65, t + 0.65, 1.9, 4.0) for t in lows] + [(t - 0.75, t + 0.75, 6.0, 8.6) for t in ups] + \
              [(door_t - 1.65, door_t + 1.65, 0.0, 4.95)]
        build_wall(sd, ops)
        for t in lows:
            window(sd, t, 1.3, 1.9, 4.0, moon if t > 10 else None)
        for t in ups:
            window(sd, t, 1.5, 6.0, 8.6, moon if t > 10 else None)
        door(sd, door_t)
        plinth(sd, [(door_t - 1.8, door_t + 1.8)])
        courses(sd)
        for t in (8.0, 15.5):
            wall_pillar(sd, t, 1.3, 3.5)
        for (a, b) in ((0.4, 7.3), (8.7, 14.8), (16.2, 26.0)):
            arch(sd, a, b, 8.9, 10.5, 0.6, 0.0, 0.7, "Timber", 12)
    P = {}
    for side, sx in (("L", -1), ("R", 1)):
        P["in" + side] = corner_pillar((sx * BX, BZ), S["bay" + side], back)
        P["out" + side] = corner_pillar((sx * CX, CZ), S["side" + side], S["bay" + side], 1.6, 3.5)
    return S, P

def build_ceiling():
    """Timber ceiling: planks and joists (SE_Ceiling) and the big beams with hanging carved bosses (SE_Detail)."""
    g = "SE_Ceiling"
    zc, zl = (BZ + FRONT_Z) / 2, FRONT_Z - BZ + 1.0
    box(g, 0.0, H_CEIL, H_CEIL + 0.3, zc, 2 * CX + 2, zl, "Planks")
    k = 0
    while BZ + 0.6 + k * 1.4 < FRONT_Z:
        box(g, 0.0, H_CEIL - 0.28, H_CEIL, BZ + 0.6 + k * 1.4, 2 * CX, 0.22, "Timber")
        k += 1
    d = "SE_Detail"
    for x in (-3.6, 3.6):
        box(d, x, 11.4, H_CEIL - 0.28, zc, 0.8, FRONT_Z - BZ, "Timber")
        box(d, x, 10.6, 11.4, BZ + 0.55, 0.9, 1.1, "Stone", 0.02)                 # corbel on the back wall
        box(d, x, 10.2, 10.6, BZ + 0.35, 0.6, 0.7, "StoneLight", 0.02)
    for z in (-14.0, -3.0):
        box(d, 0.0, 11.6, H_CEIL - 0.28, z, 2 * CX, 0.7, "Timber")
        for x in (-3.6, 3.6):                                                    # carved bosses hanging at the crossings
            box(d, x, 10.9, 11.6, z, 1.0, 1.0, "Stone", 0.03)
            box(d, x, 10.55, 10.9, z, 0.62, 0.62, "StoneLight", 0.02)
            cyl(d, x, 10.15, z, 0.03, 0.3, 0.4, "Stone", 4, 45)
        for sx in (-1, 1):                                                       # corbels on the side walls
            box(d, sx * (CX - 0.5), 10.8, 11.6, z, 1.0, 0.9, "Stone", 0.02)

def build_floor():
    g = grp("SE_Floor")
    quad(g, [(-FLOOR_X, 0, FLOOR_FRONT), (FLOOR_X, 0, FLOOR_FRONT), (FLOOR_X, 0, FLOOR_BACK), (-FLOOR_X, 0, FLOOR_BACK)],
         [(-FLOOR_X, -FLOOR_FRONT), (FLOOR_X, -FLOOR_FRONT), (FLOOR_X, -FLOOR_BACK), (-FLOOR_X, -FLOOR_BACK)], "FloorSlate")

def build_preview():
    g = grp("Preview_Standins", "Preview")
    for x, m in ((-1.8, "Stand_P1"), (1.8, "Stand_P2")):
        obox(g, (x, 0.875, 0), (0.6, 1.75, 0.3), 0, m)

# ======================================================================
#  lights, render, cameras
# ======================================================================
def build_lights():
    w = bpy.data.worlds.new("World"); bpy.context.scene.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*srgb(V["world"][0]), 1); bg.inputs["Strength"].default_value = V["world"][1]
    bpy.context.scene["ce_variant"] = VARIANT
    bpy.context.scene["ce_world_strength"] = V["world"][1]
    for k, sx in enumerate((-1, 1)):                                            # the moon, through each side's windows
        sd = bpy.data.lights.new("Moon_%d" % k, 'SUN'); sd.energy = V["moon"][0]; sd.color = srgb(V["moon"][1]); sd.angle = math.radians(2.0)
        o = bpy.data.objects.new("Moon_%d" % k, sd); col("Lights").objects.link(o)
        dx, dy, dz = (MOON[0] if sx < 0 else -MOON[0]), MOON[1], MOON[2]
        o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = Vector((dx, -dz, dy)).normalized().to_track_quat('-Z', 'Y')
    def area(name, pos, aim, size, power, colr):
        ld = bpy.data.lights.new(name, 'AREA'); ld.shape = 'RECTANGLE'
        ld.size, ld.size_y = size; ld.energy = power; ld.color = srgb(colr)
        o = bpy.data.objects.new(name, ld); col("Lights").objects.link(o); o.location = G(*pos)
        o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = (G(*aim) - G(*pos)).normalized().to_track_quat('-Z', 'Y')
        o.visible_camera = False
    area("Fill_Front", (0, 6.0, 14.0), (0, 2.5, -14.0), (26, 8), V["fill"][0], V["fill"][1])
    area("Fill_Top", (0, 12.5, -8.0), (0, 0.0, -8.0), (20, 20), V["top"][0], V["top"][1])
    for k, (x, y, z) in enumerate(LANTERNS):
        ld = bpy.data.lights.new("Lantern_%d" % k, 'POINT'); ld.energy = V["lantern_w"]; ld.color = srgb(V["lantern_color"])
        ld.shadow_soft_size = 0.12
        o = bpy.data.objects.new("Lantern_%d" % k, ld); col("Lights").objects.link(o); o.location = G(x, y, z); o.visible_camera = False

def setup_render():
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons["cycles"].preferences
    try:
        prefs.compute_device_type = 'HIP'; prefs.get_devices()
        for dv in prefs.devices:
            dv.use = (dv.type == 'HIP' and "9070" in dv.name)
        sc.cycles.device = 'GPU'
    except Exception:
        sc.cycles.device = 'CPU'
    sc.cycles.samples = 64; sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6; sc.cycles.diffuse_bounces = 3; sc.cycles.transparent_max_bounces = 16
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.render.resolution_percentage = 50
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'

CAMS = (("CAM_near", (0, 1.4, 6.5)), ("CAM_mid", (0, 1.9, 9.5)), ("CAM_far", (0, 3.35, 16.0)),
        ("CAM_near_right", (9.3, 1.4, 6.5)), ("CAM_near_left", (-9.3, 1.4, 6.5)),
        ("CAM_far_right", (4.75, 3.35, 16.0)), ("CAM_far_left", (-4.75, 3.35, 16.0)),
        ("CAM_jump_far", (0, 7.5, 16.0)))

def build_cameras():
    for name, pos in CAMS:
        cd = bpy.data.cameras.new(name); cd.sensor_fit = 'VERTICAL'; cd.angle_y = math.radians(30)
        cd.clip_start = 0.1; cd.clip_end = 400
        o = bpy.data.objects.new(name, cd); col("Cameras").objects.link(o)
        o.location = G(*pos); o.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.scene.camera = bpy.data.objects["CAM_mid"]

def build_all():
    reset(); COLS.clear(); MATS.clear(); GR.clear()
    for L in (WINDOWS, BEAMS, LANTERNS):
        L.clear()
    build_materials()
    build_floor()
    build_room(); build_stair(); build_ceiling()
    build_preview()
    objs = {name: g.finish() for name, g in list(GR.items())}
    for n in ("SE_Window", "SE_Glow", "SE_Beam"):
        if n in objs:
            objs[n].visible_shadow = False        # the moon shines through the glass; glows don't block it
    objs["SE_Beam"].hide_render = True            # moonbeams are drawn in Godot only
    build_lights(); build_cameras(); setup_render()
    tris = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs.values()}
    return {"variant": VARIANT, "objects": list(objs), "tris": tris, "total_tris": sum(tris.values()),
            "windows": len(WINDOWS), "beams": len(BEAMS), "lanterns": len(LANTERNS)}

if __name__ == "__main__":
    BUILD_INFO = build_all()
