# North Ambria (v3) - 3D stage build script (Blender 5.x, runs in --background).
# An exposed North Ambria plateau in a raging snowstorm. A broad, wind-packed snowfield for the fight; two small
# weathered stone markers together on a low rise far back; snowbanks and half-buried rocks only at the side edges,
# a few dull ice outcrops at the far edges. Past the plateau edge the ground falls into a misty gulf, and layer upon
# layer of irregular cliffs and ridges march away into the storm, with a brighter break low on the horizon.
#
#   blender --background --factory-startup --python run_na.py -- STEPS=build,bake,preview,export,beauty
#   blender --background --factory-startup --python run_na.py -- STEPS=blockout       (grey blockout render only)
#
# Layout is written in GODOT coordinates (x right, y up, +z toward the camera) and converted
# to Blender (Z-up) by G():  Godot (x, y, z) -> Blender (x, -z, y).  1 unit = 1 m.
# Baked groups (atlases): NA_Rocks (rocks, markers, ice), NA_Cliffs (near cliff layers), NA_Far (far ridges)
# NA_Floor: the sculpted snowfield (light map only; Godot's floor shader draws the snow, exported as "Floor")
# Card groups (Godot shaders): NA_Sky (in the bake), NA_Mist, NA_Drift (blowing powder; Godot only)
# Materials: matte Principled (Roughness 0.94, Metallic 0, Coat 0, Transmission 0, Specular IOR Level 0.1).
import bpy, bmesh, math, random
from mathutils import Vector, Matrix

ROOT = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\stages\north_ambria"
TEXD = ROOT + r"\src\tex"
VARIANT = globals().get("VARIANT") or "storm"
BLOCKOUT = bool(globals().get("BLOCKOUT", False))

# ---------------- layout (Godot space, metres) ----------------
FLOOR_X = 90.0                     # the snowfield heightfield: x +-90, z -66..+24 (light map covers exactly this)
FLOOR_BACK, FLOOR_FRONT = -66.0, 24.0
FLOOR_STEP = 0.8
LANE_X, LANE_Z = 12.5, -9.0        # keep |x| < 12.5 and z > -9 clear and level (fight lane)
CENTER_Z = -6.0
RISE = (0.5, -42.0)                # the modest, distant rise with the two markers
RISE_H = 1.1
EDGE_Z = -55.0                     # the plateau edge (the ground falls away behind it)
WIND = (0.94, 0.34)                # wind direction over the ground (x, z): blowing to the right, a little toward us
SKY_R = 1300.0
SUN_DIR = (0.5, -0.38, 0.78)       # where the storm light travels TO: from behind-left, across the snow for relief

V = dict(world=("#9aa8be", 1.0), sun=(2.6, "#e6edf8", 9.0), fill=(1500, "#c4d0e4"), top=(2600, "#b8c4d8"),
         sky=[(0.0, "#c4ccd8"), (0.08, "#9aa6b8"), (0.25, "#6a7488"), (1.0, "#3a4252")], sky_strength=1.1)
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
#  shared shape helpers (lathe, prisms, cards, windows)
# ======================================================================
def lathe(g, x, y0, z, prof, seg=12, m="Steel", rot=0.0):
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

def prism(g, pts, axis, a0, a1, m):
    """A convex outline pushed along a world axis. axis 'z': pts are (x, y), from z = a0 to a1;
    axis 'x': pts are (z, y), from x = a0 to a1; axis 'y': pts are (x, z), from y = a0 to a1."""
    gg = grp(g) if isinstance(g, str) else g; bm = gg.bm
    def P(p, a):
        if axis == 'z':
            return G(p[0], p[1], a)
        if axis == 'x':
            return G(a, p[1], p[0])
        return G(p[0], a, p[1])
    F = [bm.verts.new(P(p, a1)) for p in pts]
    B = [bm.verts.new(P(p, a0)) for p in pts]
    faces = [bm.faces.new(F), bm.faces.new(B[::-1])]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((F[i], B[i], B[j], F[j])))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    _tag(gg, faces, m)
    return faces

def gable(g, x0, x1, z0, z1, y0, y_eave, y_ridge, m_wall, m_roof, ridge_axis='z', over=0.4, thick=0.25):
    """A building with a pitched roof: walls to y_eave, gable ends, two roof slabs (ridge along z or x)."""
    box(g, (x0 + x1) / 2, y0, y_eave, (z0 + z1) / 2, x1 - x0, z1 - z0, m_wall)
    if ridge_axis == 'z':
        xm = (x0 + x1) / 2
        prism(g, [(x0, y_eave), (x1, y_eave), (xm, y_ridge)][::-1], 'z', z0, z1, m_wall)
        for s in (-1, 1):
            xe = x0 - over if s < 0 else x1 + over
            ye = y_eave - over * (y_ridge - y_eave) / ((x1 - x0) / 2)
            p = [(xe, ye), (xm, y_ridge), (xm, y_ridge + thick), (xe, ye + thick)]
            prism(g, p if s > 0 else p[::-1], 'z', z0 - over, z1 + over, m_roof)
    else:
        zm = (z0 + z1) / 2
        prism(g, [(z0, y_eave), (z1, y_eave), (zm, y_ridge)][::-1], 'x', x0, x1, m_wall)
        for s in (-1, 1):
            ze = z0 - over if s < 0 else z1 + over
            ye = y_eave - over * (y_ridge - y_eave) / ((z1 - z0) / 2)
            p = [(ze, ye), (zm, y_ridge), (zm, y_ridge + thick), (ze, ye + thick)]
            prism(g, p if s > 0 else p[::-1], 'x', x0 - over, x1 + over, m_roof)

def card(gname, pts, fid, mat, u0=0.0, u1=1.0):
    """A shader card: Blender UV.x = u0..u1 across, UV.y = id + h (h 0 at pts[0..1], 1 at pts[2..3])."""
    return quad(grp(gname, "Cards"), pts, [(u0, fid + 0.001), (u1, fid + 0.001), (u1, fid + 0.999), (u0, fid + 0.999)], mat)

def card_uv(gg, faces, fid, h=0.5, u=0.5):
    for f in faces:
        f[gg.custom] = 1
        for l in f.loops:
            l[gg.uv].uv = (u, fid + h)

def glow_lathe(gname, x, y0, z, prof, fid, seg=10, mat="GlowWarm"):
    gg = grp(gname, "Cards")
    card_uv(gg, lathe(gg, x, y0, z, prof, seg, mat), fid)

def glow_box(gname, center, size, fid, mat="GlowWarm", rot_y=0.0):
    gg = grp(gname, "Cards")
    before = len(gg.bm.faces)
    obox(gg, center, size, rot_y, mat)
    card_uv(gg, list(gg.bm.faces)[before:], fid)

def letters(gname, text, x0, y0, z, h, fid, mat="GlowSign", face=1, depth=0.12):
    """Block capitals made of glowing boxes (a lit sign). Supported: A..Z subset used here."""
    S = {   # 5x7 grid strokes: (col0, row0, col1, row1) rectangles in grid units
        "R": [(0, 0, 1, 7), (1, 6, 4, 7), (3, 4, 4, 7), (1, 3, 4, 4), (2, 0, 3, 3), (3, 0, 4, 2)],
        "O": [(0, 1, 1, 6), (3, 1, 4, 6), (1, 0, 3, 1), (1, 6, 3, 7)],
        "E": [(0, 0, 1, 7), (0, 0, 4, 1), (0, 3, 3, 4), (0, 6, 4, 7)],
        "F": [(0, 0, 1, 7), (0, 3, 3, 4), (0, 6, 4, 7)],
        "C": [(0, 1, 1, 6), (1, 0, 4, 1), (1, 6, 4, 7)],
        "K": [(0, 0, 1, 7), (1, 3, 2, 4), (2, 4, 3, 5), (3, 5, 4, 7), (2, 2, 3, 3), (3, 0, 4, 2)],
    }
    u = h / 7.0; x = x0
    for ch in text:
        for (c0, r0, c1, r1) in S.get(ch, []):
            glow_box(gname, (x + (c0 + c1) / 2 * u, y0 + (r0 + r1) / 2 * u, z + face * depth / 2),
                     ((c1 - c0) * u, (r1 - r0) * u, depth), fid, mat)
        x += 5 * u

WIN = [0]          # running window id (each window card gets its own, the shader picks lit / dark from it)

def window_grid(gname, face, a0, a1, y0, y1, plane, col_w=2.6, row_h=3.4, ww=1.4, wh=1.8, shop=False, skip=None):
    """Window cards on a facade. face: '+z', '-z', '+x', '-x'; a0..a1 the span along the facade (x for z-faces,
    z for x-faces); plane = the facade's coordinate (+0.06 outward is added). shop=True: one big lit shop window
    per bay (UV.x 2..3 tells the shader)."""
    n = max(1, int((a1 - a0) / col_w)); cw = (a1 - a0) / n
    rows = 1 if shop else max(1, int((y1 - y0) / row_h))
    rh = (y1 - y0) / rows
    sgn = 1 if face[0] == '+' else -1
    for i in range(n):
        for j in range(rows):
            if skip and skip(i, j):
                continue
            ac = a0 + (i + 0.5) * cw; yc = y0 + (j + 0.5) * rh
            hw, hh = (cw * 0.42, rh * 0.38) if shop else (ww / 2, wh / 2)
            wid = WIN[0]; WIN[0] += 1
            if face[1] == 'z':
                zc = plane + sgn * 0.06
                pts = [(ac - hw * sgn, yc - hh, zc), (ac + hw * sgn, yc - hh, zc), (ac + hw * sgn, yc + hh, zc), (ac - hw * sgn, yc + hh, zc)]
            else:
                xc = plane + sgn * 0.06
                pts = [(xc, yc - hh, ac + hw * sgn), (xc, yc - hh, ac - hw * sgn), (xc, yc + hh, ac - hw * sgn), (xc, yc + hh, ac + hw * sgn)]
            card(gname, pts, wid, "WindowCard", 2.0 if shop else 0.0, 3.0 if shop else 1.0)


# ======================================================================
#  noise (pure python, deterministic)
# ======================================================================
def _hash(ix, iy, iz, seed):
    n = (ix * 374761393 + iy * 668265263 + iz * 2147483647 + seed * 1442695041) & 0xffffffff
    n = ((n ^ (n >> 13)) * 1274126177) & 0xffffffff
    return ((n ^ (n >> 16)) & 0xffffff) / 16777216.0

def _sm(t):
    return t * t * (3.0 - 2.0 * t)

def vnoise(x, y, seed=0):
    ix, iy = math.floor(x), math.floor(y); fx, fy = _sm(x - ix), _sm(y - iy)
    a = _hash(ix, iy, 0, seed); b = _hash(ix + 1, iy, 0, seed)
    c = _hash(ix, iy + 1, 0, seed); d = _hash(ix + 1, iy + 1, 0, seed)
    return a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy

def vnoise3(x, y, z, seed=0):
    ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
    fx, fy, fz = _sm(x - ix), _sm(y - iy), _sm(z - iz)
    def L(a, b, t):
        return a + (b - a) * t
    c = [[[_hash(ix + i, iy + j, iz + k, seed) for i in (0, 1)] for j in (0, 1)] for k in (0, 1)]
    return L(L(L(c[0][0][0], c[0][0][1], fx), L(c[0][1][0], c[0][1][1], fx), fy),
             L(L(c[1][0][0], c[1][0][1], fx), L(c[1][1][0], c[1][1][1], fx), fy), fz)

def fbm(x, y, seed=0, oct=5, gain=0.5):
    """About -1..1."""
    s, a, f, norm = 0.0, 1.0, 1.0, 0.0
    for i in range(oct):
        s += (vnoise(x * f, y * f, seed + i * 17) * 2.0 - 1.0) * a
        norm += a; a *= gain; f *= 2.03
    return s / norm

def fbm3(x, y, z, seed=0, oct=4, gain=0.5):
    s, a, f, norm = 0.0, 1.0, 1.0, 0.0
    for i in range(oct):
        s += (vnoise3(x * f, y * f, z * f, seed + i * 17) * 2.0 - 1.0) * a
        norm += a; a *= gain; f *= 2.03
    return s / norm

def ridged(x, y, seed=0, oct=4):
    """0..1, sharp crests."""
    s, a, f, norm = 0.0, 1.0, 1.0, 0.0
    for i in range(oct):
        s += (1.0 - abs(vnoise(x * f, y * f, seed + i * 31) * 2.0 - 1.0)) ** 2 * a
        norm += a; a *= 0.5; f *= 2.1
    return s / norm

def smoothstep(e0, e1, x):
    t = min(max((x - e0) / (e1 - e0), 0.0), 1.0)
    return t * t * (3 - 2 * t)

# ======================================================================
#  materials (matte everywhere)
# ======================================================================
def matte(b, rough=0.94):
    """The brief's matte snow/rock setup: no metal, coat, transmission, and almost no specular."""
    p = b.bsdf.inputs
    p["Roughness"].default_value = rough
    p["Metallic"].default_value = 0.0
    for k, v in (("Coat Weight", 0.0), ("Transmission Weight", 0.0), ("Specular IOR Level", 0.1), ("Sheen Weight", 0.0)):
        if k in p:
            p[k].default_value = v

def add_haze(b, colour, near, far, hmax):
    """Fade into the storm with distance from the arena (baked in as emission)."""
    dist = b.n("ShaderNodeVectorMath", operation='LENGTH'); b.link(b.pos, dist.inputs[0])
    mr = b.n("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = near; mr.inputs["From Max"].default_value = far
    mr.inputs["To Min"].default_value = 0.0; mr.inputs["To Max"].default_value = hmax
    b.link(dist.outputs["Value"], mr.inputs[0])
    em = b.n("ShaderNodeEmission"); em.inputs["Color"].default_value = (*srgb(colour), 1); em.inputs["Strength"].default_value = 1.0
    mix = b.n("ShaderNodeMixShader"); b.link(mr.outputs[0], mix.inputs[0])
    b.link(b.bsdf.outputs[0], mix.inputs[1]); b.link(em.outputs[0], mix.inputs[2]); b.link(mix.outputs[0], b.out.inputs[0])

def snowy(name, rock_dark, rock_light, snow, thresh=0.42, soft=0.22, scale=0.35, haze=None, rough=0.94, ao_dist=0.0):
    """Rock or ice with snow settled on every upward-facing surface (by the geometry normal, broken up by noise),
    and - with ao_dist - packed into the crevices and under the ledges where the rock is sheltered."""
    b = NB(name)
    n = b.noise(b.pos, scale, 5, 0.6)
    n2 = b.noise(b.pos, scale * 6.0, 3, 0.5)
    rock = b.ramp(n.outputs["Fac"], [(0.3, rock_dark), (0.7, rock_light)])
    rock = b.mixc(rock, b.ramp(n2.outputs["Fac"], [(0.35, "#b8b8b8"), (0.65, "#ffffff")]), 1.0, 'MULTIPLY')
    sep = b.n("ShaderNodeSeparateXYZ"); b.link(b.normal, sep.inputs[0])
    up = b.math('ADD', sep.outputs[2], b.math('MULTIPLY', b.math('SUBTRACT', n.outputs["Fac"], 0.5), 0.5))
    if ao_dist > 0:
        ao = b.n("ShaderNodeAmbientOcclusion"); ao.inputs["Distance"].default_value = ao_dist; ao.samples = 8
        crev = b.math('MULTIPLY', b.math('SUBTRACT', 1.0, ao.outputs["AO"]), b.math('ADD', sep.outputs[2], 0.6))
        up = b.math('ADD', up, b.math('MULTIPLY', crev, 0.45))
    mr = b.n("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = thresh; mr.inputs["From Max"].default_value = thresh + soft
    b.link(up, mr.inputs[0])
    c = b.mixc(rock, snow, mr.outputs[0])
    b.link(c, b.bsdf.inputs["Base Color"]); matte(b, rough)
    if haze:
        add_haze(b, *haze)
    return b

def snow_field(name):
    """Matte, wind-packed powder snow (Principled: Roughness 0.96, no metal, coat or transmission, Specular IOR
    Level 0.1). Irregular wind-shaped ripples and scoops as a soft bump, soft patches of smoother packed snow,
    restrained blue-grey in the hollows. Godot draws the same look with its own floor shader."""
    b = NB(name)
    # rotate world xy into the wind's frame so the ripples lie across it (Blender y = -Godot z)
    a = math.atan2(-WIND[1], WIND[0])
    mp = b.n("ShaderNodeMapping"); mp.inputs["Rotation"].default_value = (0.0, 0.0, -a)
    b.link(b.pos, mp.inputs[0])
    warp = b.noise(mp.outputs[0], 0.35, 3, 0.5)
    mix = b.n("ShaderNodeMix"); mix.data_type = 'VECTOR'; mix.inputs[0].default_value = 0.35
    b.link(mp.outputs[0], mix.inputs[4]); b.link(warp.outputs["Color"], mix.inputs[5])
    w = b.n("ShaderNodeTexNoise"); w.inputs["Scale"].default_value = 0.28; w.inputs["Detail"].default_value = 3.0
    w.inputs["Roughness"].default_value = 0.4; w.inputs["Distortion"].default_value = 0.25
    b.link(mix.outputs[1], w.inputs["Vector"])                 # soft pillows of powder, a metre or two across
    patches = b.noise(b.pos, 0.07, 4, 0.55)                      # where the snow is packed smooth
    packed = b.n("ShaderNodeMapRange"); packed.inputs["From Min"].default_value = 0.4; packed.inputs["From Max"].default_value = 0.72
    b.link(patches.outputs["Fac"], packed.inputs[0])
    grain = b.noise(b.pos, 6.0, 2, 0.45)
    hgt = b.math('ADD', b.math('MULTIPLY', w.outputs["Fac"], b.math('SUBTRACT', 1.0, b.math('MULTIPLY', packed.outputs[0], 0.8))),
                 b.math('MULTIPLY', grain.outputs["Fac"], 0.25))
    bump = b.n("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.5; bump.inputs["Distance"].default_value = 0.3
    b.link(hgt, bump.inputs["Height"]); b.link(bump.outputs[0], b.bsdf.inputs["Normal"])
    col = b.mixc("#d4dbe5", "#e9eef4", b.math('ADD', b.math('MULTIPLY', w.outputs["Fac"], 0.5), b.math('MULTIPLY', packed.outputs[0], 0.4)))
    b.link(col, b.bsdf.inputs["Base Color"]); matte(b, 0.96)
    return b

def emit_solid(name, color, strength):
    b = NB(name)
    em = b.n("ShaderNodeEmission"); em.inputs["Color"].default_value = (*srgb(color), 1); em.inputs["Strength"].default_value = strength
    b.link(em.outputs[0], b.out.inputs[0])
    return b

def flat(name, color, rough=0.94):
    b = NB(name); b.bsdf.inputs["Base Color"].default_value = (*srgb(color), 1); matte(b, rough)
    return b

HZ = "#aeb8c8"
SNOW = "#e8edf3"
def build_materials():
    if BLOCKOUT:     # the grey blockout: same material names, flat colours, no textures
        for nm, c in (("Rock", "#55595f"), ("RockNear", "#55595f"), ("Marker", "#6a6c70"), ("Ice", "#9fb4c8"), ("Cliff", "#6a6e76"),
                      ("CliffFar", "#868a92"), ("Ridge", "#9ea2aa"), ("SnowField", "#dcdfe4"), ("SkyCard", "#7a8090"),
                      ("MistCard", "#808080"), ("DriftCard", "#808080"), ("Stand_P1", "#2d6cdf"), ("Stand_P2", "#e0463a")):
            flat(nm, c)
        return
    snowy("RockNear", "#3c4048", "#5a5e66", SNOW, 0.45, 0.2, 0.6)
    snowy("Rock", "#40444c", "#5e626a", SNOW, 0.4, 0.22, 0.45, haze=(HZ, 40, 160, 0.5))
    snowy("Marker", "#5a5c60", "#77797c", SNOW, 0.62, 0.12, 2.4)
    snowy("Ice", "#8aa2b8", "#b4c6d4", SNOW, 0.55, 0.18, 1.2, haze=(HZ, 40, 160, 0.5), rough=0.85)
    snowy("Cliff", "#1f232b", "#383c45", SNOW, 0.74, 0.1, 0.08, haze=(HZ, 130, 900, 0.48), ao_dist=5.0)
    snowy("CliffFar", "#272b34", "#40444d", SNOW, 0.7, 0.12, 0.04, haze=(HZ, 220, 1100, 0.6), ao_dist=8.0)
    snowy("Ridge", "#343842", "#4c505a", SNOW, 0.62, 0.14, 0.015, haze=(HZ, 320, 1400, 0.72), ao_dist=16.0)
    snow_field("SnowField")
    b = NB("SkyCard")
    sep = b.n("ShaderNodeSeparateXYZ"); b.link(b.uv, sep.inputs[0])
    em = b.n("ShaderNodeEmission"); em.inputs["Strength"].default_value = V["sky_strength"]
    b.link(b.ramp(sep.outputs[1], V["sky"]), em.inputs["Color"]); b.link(em.outputs[0], b.out.inputs[0])
    emit_solid("MistCard", "#808080", 0.0)
    emit_solid("DriftCard", "#808080", 0.0)
    flat("Stand_P1", "#2d6cdf"); flat("Stand_P2", "#e0463a")

# ======================================================================
#  the snowfield
# ======================================================================
def ground_h(x, z):
    """Height of the snowfield. Exactly level in the fight lane; wind-sculpted drifts and banks outside it,
    the low rise far back, and the drop at the plateau edge."""
    ax = abs(x)
    side = smoothstep(13.0, 22.0, ax)
    back = smoothstep(-13.0, -26.0, z)
    open_ = max(side, back * 0.75)
    u = x * WIND[0] + z * WIND[1]; v = -x * WIND[1] + z * WIND[0]
    drifts = 0.5 * (fbm(u * 0.03, v * 0.1, 3, 4) * 0.5 + 0.5) + 0.45 * ridged(u * 0.05, v * 0.16, 7, 3)
    h = open_ * drifts * (0.8 + 1.8 * side)
    h += smoothstep(30.0, 80.0, ax) * (1.0 + 1.6 * (fbm(x * 0.02, z * 0.03, 11, 4) * 0.5 + 0.5))
    rx, rz = (x - RISE[0]) / 17.0, (z - RISE[1]) / 9.0
    r = math.sqrt(rx * rx + rz * rz)
    h += RISE_H * (1.0 - smoothstep(0.2, 1.0, r)) * (1.0 + 0.1 * fbm(x * 0.2, z * 0.2, 13, 3))
    h += back * 0.7 * (fbm(x * 0.03, z * 0.05, 17, 4) * 0.5 + 0.5)
    ze = EDGE_Z + 4.0 * fbm(x * 0.025, 1.7, 19, 4) + smoothstep(20.0, 80.0, ax) * 6.0
    drop = smoothstep(ze, ze - 9.0, z)
    return h * (1.0 - drop) - drop * (34.0 + 6.0 * fbm(x * 0.05, z * 0.05, 23, 3))

def build_floor():
    g = grp("NA_Floor"); bm = g.bm
    nx = int(2 * FLOOR_X / FLOOR_STEP); nz = int((FLOOR_FRONT - FLOOR_BACK) / FLOOR_STEP)
    xs = [-FLOOR_X + i * 2 * FLOOR_X / nx for i in range(nx + 1)]
    zs = [FLOOR_BACK + j * (FLOOR_FRONT - FLOOR_BACK) / nz for j in range(nz + 1)]
    VV = [[bm.verts.new(G(x, ground_h(x, z), z)) for x in xs] for z in zs]
    faces = []
    for j in range(nz):
        for i in range(nx):
            faces.append(bm.faces.new((VV[j][i], VV[j][i + 1], VV[j + 1][i + 1], VV[j + 1][i])))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    bm.normal_update()
    if sum(f.normal.z for f in faces[:50]) < 0:
        for f in faces:
            f.normal_flip()
    _tag(g, faces, "SnowField")

# ======================================================================
#  rocks, markers, ice
# ======================================================================
def rock(g, x, z, size, seed, m="Rock", sub=3, bury=0.32):
    """A weathered boulder half buried in snow: a noise-displaced ellipsoid (soft, not faceted)."""
    gg = grp(g) if isinstance(g, str) else g
    sx, sy, sz = size
    y0 = ground_h(x, z) - bury * sy
    c = G(x, y0 + sy * 0.5, z)
    res = bmesh.ops.create_icosphere(gg.bm, subdivisions=sub, radius=1.0, matrix=Matrix.Translation(c))
    rnd = random.Random(seed); ox, oy, oz = rnd.uniform(0, 50), rnd.uniform(0, 50), rnd.uniform(0, 50)
    ang = rnd.uniform(0, math.pi)
    ca, sa = math.cos(ang), math.sin(ang)
    for v in res["verts"]:
        d = v.co - c
        n = d.normalized()
        k = 1.0 + 0.24 * fbm3(n.x * 1.1 + ox, n.y * 1.1 + oy, n.z * 1.1 + oz, seed, 4) + 0.1 * (vnoise3(n.x * 4 + ox, n.y * 4, n.z * 4, seed + 5) - 0.5)
        k += 0.12 * max(0.0, n.z)            # a fuller, rounder top where the snow sits
        p = n * k
        px, py = p.x * ca - p.y * sa, p.x * sa + p.y * ca      # turn it about the vertical (Blender z)
        v.co = c + Vector((px * sx * 0.5, py * sz * 0.5, p.z * sy * 0.6))
    _tag(gg, list({f for v in res["verts"] for f in v.link_faces}), m)

def stone_marker(g, x, z, w, h, t, tilt, seed):
    """A small weathered stone marker: a slab with a rounded top built from stacked rounded-rect rings,
    roughened by noise, on a low base slab, leaning a few degrees."""
    gg = grp(g) if isinstance(g, str) else g; bm = gg.bm
    y0 = ground_h(x, z) - 0.15
    rnd = random.Random(seed)
    # base slab
    base_w, base_t, base_h = w * 1.45, t * 2.6, 0.24
    rock(gg, x, z + 0.02, (base_w * 1.2, base_h * 1.5, base_t * 1.2), seed + 3, "Marker", 2, 0.55)
    N, M = 22, 28
    rings = []
    rw = w / 2
    for j in range(N + 1):
        yy = j / N * h
        if yy < h - rw:
            hw = rw
        else:
            q = (yy - (h - rw)) / rw
            hw = rw * math.sqrt(max(0.0, 1.0 - q * q)) if j < N else 0.0
        ht = t / 2 * (1.0 - 0.06 * yy / h)
        ring = []
        for i in range(M):
            a = 2 * math.pi * i / M
            ca, sa = math.cos(a), math.sin(a)
            ex = math.copysign(abs(ca) ** (2 / 6.0), ca) * max(hw, 0.02)
            ez = math.copysign(abs(sa) ** (2 / 6.0), sa) * ht
            lx, ly, lz = ex, yy, ez
            # weathering: a rough skin, chipped edges, a worn top
            nn = fbm3(lx * 3.0 + seed, ly * 3.0, lz * 3.0, seed, 4)
            sc = 1.0 + 0.07 * nn - 0.05 * smoothstep(0.75, 1.0, yy / h) * (vnoise3(lx * 9, ly * 9, lz * 9, seed + 2) - 0.3)
            lx *= sc; lz *= sc
            # lean
            ly2 = ly * math.cos(tilt[0]) - lz * math.sin(tilt[0]); lz2 = ly * math.sin(tilt[0]) + lz * math.cos(tilt[0])
            lx3 = lx * math.cos(tilt[1]) - ly2 * math.sin(tilt[1]); ly3 = lx * math.sin(tilt[1]) + ly2 * math.cos(tilt[1])
            ring.append(bm.verts.new(G(x + lx3, y0 + base_h + ly3, z + lz2)))
        rings.append(ring)
    faces = []
    for A, B in zip(rings[:-1], rings[1:]):
        for i in range(M):
            faces.append(bm.faces.new((A[i], A[(i + 1) % M], B[(i + 1) % M], B[i])))
    faces.append(bm.faces.new(rings[0][::-1]))
    top = bm.verts.new(sum((v.co for v in rings[-1]), Vector()) / M)
    for i in range(M):
        faces.append(bm.faces.new((rings[-1][i], rings[-1][(i + 1) % M], top)))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    _tag(gg, faces, "Marker")
    # snow drifted against the foot of the stone, on the windward side
    for k in range(3):
        rock(gg, x - 0.25 + k * 0.25, z + rnd.uniform(-0.1, 0.25), (0.6, 0.22, 0.5), seed + 10 + k, "Marker", 2, 0.6)

def crystal(g, base, d, r, L, m="Ice"):
    """A six-sided ice crystal with a pointed tip, from a Godot base point along direction d."""
    gg = grp(g) if isinstance(g, str) else g
    dv = Vector((d[0], -d[2], d[1])).normalized()
    q = dv.to_track_quat('Z', 'Y')
    A = G(*base)
    body = L * 0.72
    M1 = Matrix.Translation(A + dv * body / 2) @ q.to_matrix().to_4x4()
    r1 = bmesh.ops.create_cone(gg.bm, cap_ends=True, cap_tris=False, segments=6, radius1=r, radius2=r * 0.9, depth=body, matrix=M1)
    M2 = Matrix.Translation(A + dv * (body + (L - body) / 2)) @ q.to_matrix().to_4x4()
    r2 = bmesh.ops.create_cone(gg.bm, cap_ends=True, cap_tris=False, segments=6, radius1=r * 0.9, radius2=0.0, depth=L - body, matrix=M2)
    _tag(gg, list({f for v in r1["verts"] + r2["verts"] for f in v.link_faces}), m)

def ice_cluster(x, z, s, seed):
    rnd = random.Random(seed); y = ground_h(x, z) - 0.3 * s
    for k in range(rnd.randint(3, 5)):
        a = rnd.uniform(0, 2 * math.pi); lean = rnd.uniform(0.15, 0.55)
        d = (math.cos(a) * lean, 1.0, math.sin(a) * lean)
        bx, bz = x + rnd.uniform(-0.6, 0.6) * s, z + rnd.uniform(-0.6, 0.6) * s
        crystal("NA_Rocks", (bx, y, bz), d, rnd.uniform(0.18, 0.34) * s, rnd.uniform(0.9, 2.2) * s)
    rock("NA_Rocks", x, z, (1.6 * s, 0.6 * s, 1.4 * s), seed + 7, "Rock", 2, 0.5)

ROCKS_NEAR = [(-16.5, 4.5, (3.4, 2.0, 2.6)), (-19.6, 0.6, (2.6, 1.7, 2.2)), (-14.6, 9.4, (1.7, 0.9, 1.4)),
              (-22.5, 7.5, (2.6, 1.4, 2.4)), (16.2, 3.0, (3.0, 1.8, 2.4)), (19.0, 6.8, (2.3, 1.4, 1.9)),
              (21.0, -0.4, (3.6, 2.4, 3.0)), (15.2, 10.5, (1.4, 0.7, 1.2)), (-25.0, -2.0, (3.4, 2.2, 2.8)),
              (24.5, -6.0, (3.0, 2.0, 2.6))]
ROCKS_MID = [(-15.8, -16.0, (2.6, 1.6, 2.2)), (-19.0, -23.0, (3.4, 2.2, 2.8)), (-14.5, -27.5, (1.8, 1.0, 1.5)),
             (16.5, -18.0, (2.8, 1.8, 2.4)), (20.0, -25.0, (3.6, 2.4, 3.0)), (15.2, -29.5, (1.6, 0.9, 1.3)),
             (-28.0, -12.0, (5.0, 3.4, 4.0)), (-33.0, -21.0, (6.5, 4.2, 5.2)), (28.0, -14.0, (4.6, 3.0, 4.0)),
             (34.0, -24.0, (7.0, 4.8, 6.0)), (-40.0, -31.0, (8.0, 5.6, 7.0)), (42.0, -34.0, (8.5, 5.2, 6.4)),
             (-11.0, -44.0, (1.6, 0.9, 1.4)), (12.5, -46.0, (2.0, 1.1, 1.6)), (-18.0, -48.5, (1.2, 0.7, 1.0)),
             (19.0, -50.0, (1.4, 0.8, 1.2)), (16.5, -40.0, (1.8, 1.1, 1.5)), (-17.5, -41.0, (2.4, 1.3, 2.0)),
             (-23.0, -52.0, (6.0, 3.6, 5.0)), (25.0, -53.5, (7.0, 4.4, 5.0)), (-46.0, -50.0, (9.0, 6.0, 7.0)),
             (49.0, -48.0, (10.0, 7.0, 8.0)), (-62.0, -43.0, (10.0, 8.0, 9.0)), (63.0, -40.0, (11.0, 8.5, 9.0)),
             (-55.0, -20.0, (9.0, 6.0, 8.0)), (57.0, -16.0, (9.5, 6.5, 8.0))]
ICE = [(-17.5, -20.5, 0.7), (18.5, -22.0, 0.75), (-27.0, -7.0, 1.0), (29.5, -10.0, 1.1), (-35.0, -27.0, 1.3), (37.0, -30.0, 1.3), (-21.0, -50.0, 1.0),
       (23.0, -51.0, 1.1), (-23.5, 9.0, 0.75), (24.0, 4.5, 0.8)]

def build_rocks():
    for k, (x, z, s) in enumerate(ROCKS_NEAR):
        rock("NA_Rocks", x, z, s, 100 + k, "RockNear", 4)
    for k, (x, z, s) in enumerate(ROCKS_MID):
        rock("NA_Rocks", x, z, s, 200 + k, "Rock", 3 if max(s) < 6 else 2)
    for k, (x, z, s) in enumerate(ICE):
        ice_cluster(x, z, s, 300 + k)
    # the two markers, together on the rise
    stone_marker("NA_Rocks", RISE[0] - 1.6, RISE[1] - 0.3, 1.05, 1.95, 0.38, (math.radians(-3), math.radians(2.5)), 11)
    stone_marker("NA_Rocks", RISE[0] + 1.7, RISE[1] + 0.1, 0.98, 1.82, 0.36, (math.radians(2), math.radians(-4)), 23)

# ======================================================================
#  cliffs and ridges
# ======================================================================
def cliff(g, x0, x1, step, zf, crest, base_y, depth, seed, m, rows=34, top_rows=6, amp=1.0):
    """A layered cliff face: a grid from its misty base up to the crest, leaning back, carved by noise into
    buttresses, strata and ledges (the material lays snow on the ledges), then a strip of the snowy top behind."""
    gg = grp(g); bm = gg.bm
    n = int((x1 - x0) / step)
    grid = []
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        cy, fz = crest(x), zf(x)
        col = []
        for j in range(rows + top_rows + 1):
            if j <= rows:
                v = j / rows
                y = base_y + (cy - base_y) * v
                z = fz - (v ** 1.7) * depth
            else:
                k = j - rows
                y = cy - (1.5 + 1.2 * k) * k * amp * 0.7                 # the back falls away: a sharp ridge, not a flat berm
                z = fz - depth - k * step * 1.4
            s = (cy - base_y) / 50.0 + 0.5
            bz = (fbm(x * 0.06, y * 0.016, seed, 5) * 7.0 + ridged(x * 0.12, y * 0.045, seed + 1, 3) * 3.5
                  + fbm(x * 0.025, y * 0.04, seed + 2, 4) * 4.0 + fbm(x * 0.2, y * 0.2, seed + 4, 3) * 0.9) * amp * min(1.6, s)
            terr = (y * 0.11 + fbm(x * 0.015, y * 0.02, seed + 3, 3) * 1.6)
            ledge = -1.1 * smoothstep(0.7, 0.97, terr - math.floor(terr)) * amp
            bx = fbm(x * 0.05 + 3.3, y * 0.05, seed + 5, 3) * 2.5 * amp
            if j > rows:
                bz *= 0.3; ledge = 0.0
            col.append(bm.verts.new(G(x + bx, y, z + bz + ledge)))
        grid.append(col)
    faces = []
    for i in range(n):
        for j in range(rows + top_rows):
            faces.append(bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1])))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    bm.normal_update()
    if sum(f.normal.y for f in faces[: rows * 3]) > 0:      # the face must look toward the arena (Blender -y = Godot +z)
        for f in faces:
            f.normal_flip()
    _tag(gg, faces, m)

def build_cliffs():
    """A dramatic North Ambria panorama seen from an exposed plateau: past the plateau edge a valley full of mist,
    and across it dark, rugged, steep cliff faces capped with snow, then ridge after ridge to the horizon with haze
    between. The side cliffs swing back into the distance (no bowl); every layer dips where the valley runs off.
    The faces are steep (dark rock; snow only on the ledges, crevices and crests) and the crests are sharp ridges."""
    def recede(z0, k):
        return lambda x, z0=z0, k=k: z0 - k * max(abs(x) - 30.0, 0.0)
    def peaks(x, seed, f, amp):                      # jagged crest line: sharp peaks and notches
        return amp * (ridged(x * f, 0.3, seed, 4) - 0.4) + 0.4 * amp * (ridged(x * f * 2.7, 0.8, seed + 7, 3) - 0.45)
    zl = recede(-150.0, 0.45)
    cliff("NA_Cliffs", -300.0, -24.0, 1.2,
          lambda x: zl(x) + 7.0 * fbm(x * 0.03, 0.5, 41, 3),
          lambda x: -6.0 + 34.0 * smoothstep(-24.0, -95.0, x) + peaks(x, 44, 0.05, 12.0) + 5.0 * fbm(x * 0.02, 0.2, 42, 3),
          -30.0, 7.0, 43, "Cliff", 40, 5, 1.2)
    zr = recede(-162.0, 0.42)
    cliff("NA_Cliffs", 22.0, 300.0, 1.2,
          lambda x: zr(x) + 7.0 * fbm(x * 0.03, 0.9, 51, 3),
          lambda x: -6.0 + 30.0 * smoothstep(22.0, 90.0, x) + peaks(x, 54, 0.05, 11.0) + 5.0 * fbm(x * 0.02, 0.6, 52, 3),
          -30.0, 7.0, 53, "Cliff", 40, 5, 1.2)
    z2 = recede(-260.0, 0.25)
    cliff("NA_Cliffs", -480.0, 480.0, 2.0,
          lambda x: z2(x) + 26.0 * fbm(x * 0.008, 0.3, 61, 3),
          lambda x: 2.0 + 56.0 * smoothstep(12.0, 240.0, abs(x)) + peaks(x, 63, 0.022, 16.0) + 6.0 * fbm(x * 0.014, 0.4, 62, 3),
          -32.0, 10.0, 64, "CliffFar", 38, 5, 1.6)
    cliff("NA_Far", -880.0, 880.0, 4.0,
          lambda x: -450.0 - 0.12 * max(abs(x) - 60.0, 0.0) + 40.0 * fbm(x * 0.004, 0.7, 71, 3),
          lambda x: 16.0 + 80.0 * smoothstep(20.0, 500.0, abs(x)) + peaks(x, 73, 0.01, 30.0) + 10.0 * fbm(x * 0.007, 0.2, 72, 3),
          -34.0, 18.0, 74, "Ridge", 30, 4, 2.4)
    cliff("NA_Far", -1000.0, 1000.0, 8.0,
          lambda x: -830.0 + 60.0 * fbm(x * 0.002, 0.1, 81, 3),
          lambda x: 48.0 + 80.0 * smoothstep(40.0, 700.0, abs(x)) + peaks(x, 82, 0.005, 46.0) + 12.0 * fbm(x * 0.004, 0.9, 83, 3),
          -34.0, 30.0, 84, "Ridge", 22, 4, 3.6)

# ======================================================================
#  cards: sky, mist, blowing powder
# ======================================================================
def build_cards():
    g = grp("NA_Sky", "Cards"); n = 128; y0, y1 = -160.0, 1000.0
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        A0, A1 = 2 * math.pi * t0 - math.pi, 2 * math.pi * t1 - math.pi
        p0 = (SKY_R * math.sin(A0), 0, -150 - SKY_R * math.cos(A0)); p1 = (SKY_R * math.sin(A1), 0, -150 - SKY_R * math.cos(A1))
        quad(g, [(p0[0], y0, p0[2]), (p1[0], y0, p1[2]), (p1[0], y1, p1[2]), (p0[0], y1, p0[2])], [(t0, 0), (t1, 0), (t1, 1), (t0, 1)], "SkyCard")
    # mist: (id, z, half width, bottom, top); UV.x = metres / 40 so the shader's noise has a world scale
    for fid, z, hw, yb, yt in ((0, -62.0, 240.0, -6.5, 3.0), (1, -140.0, 420.0, -6.5, 12.0), (2, -232.0, 560.0, -6.5, 24.0),
                               (3, -415.0, 950.0, -6.5, 46.0), (4, -780.0, 1080.0, -6.5, 80.0), (5, -50.0, 90.0, -1.0, 5.0)):
        card("NA_Mist", [(-hw, yb, z), (hw, yb, z), (hw, yt, z), (-hw, yt, z)], fid, "MistCard", 0.0, 2 * hw / 40.0)
    # the sea of storm mist filling the gulf below the plateau edge (horizontal; h runs from the edge outward)
    card("NA_Fog", [(-1300.0, -6.0, -57.0), (1300.0, -6.0, -57.0), (1300.0, -6.0, -980.0), (-1300.0, -6.0, -980.0)], 0, "MistCard", 0.0, 2600.0 / 40.0)

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
    sd = bpy.data.lights.new("Sun", 'SUN'); sd.energy = V["sun"][0]; sd.color = srgb(V["sun"][1]); sd.angle = math.radians(V["sun"][2])
    s = bpy.data.objects.new("Sun", sd); col("Lights").objects.link(s)
    d = Vector(SUN_DIR).normalized()
    s.rotation_mode = 'QUATERNION'; s.rotation_quaternion = Vector((d.x, -d.z, d.y)).to_track_quat('-Z', 'Y')
    def area(name, pos, aim, size, power, colr):
        ld = bpy.data.lights.new(name, 'AREA'); ld.shape = 'RECTANGLE'
        ld.size, ld.size_y = size; ld.energy = power; ld.color = srgb(colr)
        o = bpy.data.objects.new(name, ld); col("Lights").objects.link(o); o.location = G(*pos)
        o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = (G(*aim) - G(*pos)).normalized().to_track_quat('-Z', 'Y')
        o.visible_camera = False
    area("Fill_Front", (0, 12.0, 30.0), (0, 0.0, -14.0), (60, 16), V["fill"][0], V["fill"][1])
    area("Fill_Top", (0, 34.0, -16.0), (0, 0.0, -16.0), (70, 70), V["top"][0], V["top"][1])

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
        cd.clip_start = 0.1; cd.clip_end = 3000
        o = bpy.data.objects.new(name, cd); col("Cameras").objects.link(o)
        o.location = G(*pos); o.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.scene.camera = bpy.data.objects["CAM_mid"]

CARD_GROUPS = ("NA_Sky", "NA_Mist", "NA_Fog")
HIDDEN = ("NA_Mist", "NA_Fog")

def build_all():
    reset(); COLS.clear(); MATS.clear(); GR.clear()
    build_materials()
    build_floor(); build_rocks(); build_cliffs(); build_cards(); build_preview()
    objs = {name: g.finish() for name, g in list(GR.items())}
    for n in ("NA_Floor", "NA_Rocks", "NA_Cliffs", "NA_Far"):        # soft, natural forms: smooth shading everywhere
        if n in objs:
            for p in objs[n].data.polygons:
                p.use_smooth = True
    for n in CARD_GROUPS:
        if n in objs:
            objs[n].visible_shadow = False
    for n in HIDDEN:
        if n in objs:
            objs[n].hide_render = True
    build_lights(); build_cameras(); setup_render()
    tris = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs.values()}
    return {"variant": VARIANT, "blockout": BLOCKOUT, "objects": list(objs), "tris": tris, "total_tris": sum(tris.values())}

# ======================================================================
#  the final camera render (Cycles, the full lit scene + a real storm)
# ======================================================================
def _mat_flake():
    m = bpy.data.materials.new("Beauty_Flake"); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Location"].default_value = (-0.5, -0.5, 0); mp.inputs["Scale"].default_value = (2, 2, 1)
    nt.links.new(tc.outputs["UV"], mp.inputs[0])
    gr = nt.nodes.new("ShaderNodeTexGradient"); gr.gradient_type = 'SPHERICAL'
    nt.links.new(mp.outputs[0], gr.inputs[0])
    pw = nt.nodes.new("ShaderNodeMath"); pw.operation = 'POWER'; pw.inputs[1].default_value = 1.6
    nt.links.new(gr.outputs["Fac"], pw.inputs[0])
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_type = 'GEOMETRY'; at.attribute_name = "Alpha"
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'
    nt.links.new(pw.outputs[0], mul.inputs[0]); nt.links.new(at.outputs["Fac"], mul.inputs[1])
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*srgb("#eef2f8"), 1); em.inputs["Strength"].default_value = 1.1
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(mul.outputs[0], mix.inputs[0]); nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    return m

def _mat_veil(name, colour, strength, alpha, scale, vert=True):
    """Mist / drifting powder for the beauty render: emission + transparency through noise, densest low down."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1.0 / scale, 1.0 / scale, 2.4 / scale)
    nt.links.new(geo.outputs["Position"], mp.inputs[0])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.0; nz.inputs["Detail"].default_value = 6.0
    nz.inputs["Roughness"].default_value = 0.6; nz.inputs["Distortion"].default_value = 0.4
    nt.links.new(mp.outputs[0], nz.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeMapRange"); cr.inputs["From Min"].default_value = 0.35; cr.inputs["From Max"].default_value = 0.75
    nt.links.new(nz.outputs["Fac"], cr.inputs[0])
    uvn = nt.nodes.new("ShaderNodeUVMap"); uvn.uv_map = "Tex"
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(uvn.outputs[0], sep.inputs[0])
    fr = nt.nodes.new("ShaderNodeMath"); fr.operation = 'FRACT'; nt.links.new(sep.outputs[1], fr.inputs[0])
    inv = nt.nodes.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0; nt.links.new(fr.outputs[0], inv.inputs[1])
    pw = nt.nodes.new("ShaderNodeMath"); pw.operation = 'POWER'; pw.inputs[1].default_value = 1.4 if vert else 0.8
    nt.links.new(inv.outputs[0], pw.inputs[0])
    edge = nt.nodes.new("ShaderNodeMath"); edge.operation = 'MULTIPLY'; nt.links.new(pw.outputs[0], edge.inputs[0])
    sm = nt.nodes.new("ShaderNodeMapRange"); sm.inputs["From Min"].default_value = 0.0; sm.inputs["From Max"].default_value = 0.12
    nt.links.new(fr.outputs[0], sm.inputs[0]); nt.links.new(sm.outputs[0], edge.inputs[1])
    a = nt.nodes.new("ShaderNodeMath"); a.operation = 'MULTIPLY'; nt.links.new(edge.outputs[0], a.inputs[0]); nt.links.new(cr.outputs[0], a.inputs[1])
    a2 = nt.nodes.new("ShaderNodeMath"); a2.operation = 'MULTIPLY'; a2.inputs[1].default_value = alpha; nt.links.new(a.outputs[0], a2.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*srgb(colour), 1); em.inputs["Strength"].default_value = strength
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(a2.outputs[0], mix.inputs[0]); nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    return m

def _mat_fogsea():
    """The mist sea for the beauty render: nearly opaque, billowing, a little brighter far off toward the break."""
    m = bpy.data.materials.new("Beauty_FogSea"); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.012, 0.03, 0.012)
    nt.links.new(geo.outputs["Position"], mp.inputs[0])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.0; nz.inputs["Detail"].default_value = 7.0
    nz.inputs["Roughness"].default_value = 0.6
    nt.links.new(mp.outputs[0], nz.inputs["Vector"])
    a = nt.nodes.new("ShaderNodeMapRange"); a.inputs["From Min"].default_value = 0.3; a.inputs["From Max"].default_value = 0.7
    a.inputs["To Min"].default_value = 0.72; a.inputs["To Max"].default_value = 0.97
    nt.links.new(nz.outputs["Fac"], a.inputs[0])
    c = nt.nodes.new("ShaderNodeMapRange"); c.inputs["To Min"].default_value = 0.8; c.inputs["To Max"].default_value = 1.08
    nt.links.new(nz.outputs["Fac"], c.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*srgb("#aeb8c8"), 1)
    nt.links.new(c.outputs[0], em.inputs["Strength"])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(a.outputs[0], mix.inputs[0]); nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    return m

def _mat_sky():
    """Storm sky for the beauty render: dark churning cloud, paler at the horizon, a bright break behind the rise."""
    m = bpy.data.materials.new("Beauty_Sky"); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    cam = G(0, 1.9, 9.5)
    sub = nt.nodes.new("ShaderNodeVectorMath"); sub.operation = 'SUBTRACT'; sub.inputs[1].default_value = cam
    nt.links.new(geo.outputs["Position"], sub.inputs[0])
    nrm = nt.nodes.new("ShaderNodeVectorMath"); nrm.operation = 'NORMALIZE'; nt.links.new(sub.outputs[0], nrm.inputs[0])
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(nrm.outputs[0], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB"); cr = ramp.color_ramp
    stops = [(0.0, "#b4becc"), (0.05, "#8692a6"), (0.14, "#525c70"), (0.3, "#2a3242")]
    while len(cr.elements) < len(stops):
        cr.elements.new(0.5)
    for e, (p, c) in zip(cr.elements, stops):
        e.position = p; e.color = (*srgb(c), 1)
    nt.links.new(sep.outputs[2], ramp.inputs[0])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3.0; nz.inputs["Detail"].default_value = 8.0
    nz.inputs["Roughness"].default_value = 0.62; nz.inputs["Distortion"].default_value = 1.2
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (2.2, 1.0, 5.0)
    nt.links.new(nrm.outputs[0], mp.inputs[0]); nt.links.new(mp.outputs[0], nz.inputs["Vector"])
    cl = nt.nodes.new("ShaderNodeMapRange"); cl.inputs["From Min"].default_value = 0.38; cl.inputs["From Max"].default_value = 0.72
    cl.inputs["To Min"].default_value = 0.55; cl.inputs["To Max"].default_value = 1.25
    nt.links.new(nz.outputs["Fac"], cl.inputs[0])
    mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs[0].default_value = 1.0
    nt.links.new(ramp.outputs[0], mul.inputs[6]); nt.links.new(cl.outputs[0], mul.inputs[7])
    # the break: brightness around the direction behind the rise, just above the horizon
    bd = Vector((0.05, 0.995, 0.07)).normalized()            # Blender space: ahead (+y) and a little up
    dot = nt.nodes.new("ShaderNodeVectorMath"); dot.operation = 'DOT_PRODUCT'; dot.inputs[1].default_value = bd
    nt.links.new(nrm.outputs[0], dot.inputs[0])
    br = nt.nodes.new("ShaderNodeMapRange"); br.inputs["From Min"].default_value = 0.97; br.inputs["From Max"].default_value = 1.0
    br.interpolation_type = 'SMOOTHSTEP'
    br.inputs["To Min"].default_value = 0.0; br.inputs["To Max"].default_value = 1.0
    nt.links.new(dot.outputs["Value"], br.inputs[0])
    brk = nt.nodes.new("ShaderNodeMath"); brk.operation = 'MULTIPLY'; nt.links.new(br.outputs[0], brk.inputs[0]); nt.links.new(nz.outputs["Fac"], brk.inputs[1])
    add = nt.nodes.new("ShaderNodeMix"); add.data_type = 'RGBA'; add.blend_type = 'ADD'
    nt.links.new(brk.outputs[0], add.inputs[0]); nt.links.new(mul.outputs[2], add.inputs[6]); add.inputs[7].default_value = (0.32, 0.35, 0.4, 1)
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = 1.0
    nt.links.new(add.outputs[2], em.inputs[0]); nt.links.new(em.outputs[0], out.inputs[0])
    return m

def make_beauty(cam_name="CAM_mid", flakes=12000, seed=5):
    """Add the storm (flakes at every depth, streaked near the lens, mist veils, blowing powder) as real geometry,
    switch the cards to beauty materials, and set up a full-quality 16:9 render from the game camera."""
    sc = bpy.context.scene
    for o in bpy.data.objects:
        if o.name.startswith("PV_") or o.name.startswith("Preview"):
            o.hide_render = True
        elif o.name.startswith("NA_") or o.type == 'LIGHT':
            o.hide_render = False
    bg = sc.world.node_tree.nodes["Background"].inputs["Strength"]
    bg.default_value = sc.get("ce_world_strength", 1.0)
    bc = bpy.data.collections.get("Beauty") or bpy.data.collections.new("Beauty")
    if bc.name not in sc.collection.children:
        sc.collection.children.link(bc)
    for o in list(bc.objects):
        bpy.data.objects.remove(o)
    def override(objname, mat):
        o = bpy.data.objects.get(objname)
        if o is None:
            return
        for slot in o.material_slots:
            slot.link = 'OBJECT'; slot.material = mat
    override("NA_Sky", _mat_sky())
    override("NA_Mist", _mat_veil("Beauty_Mist", "#b0bacb", 1.0, 0.22, 30.0))
    override("NA_Fog", _mat_fogsea())
    sf = bpy.data.materials.get("SnowField")              # a clearer powder relief for the camera render
    if sf:
        for nd in sf.node_tree.nodes:
            if nd.type == 'BUMP':
                nd.inputs["Strength"].default_value = 0.6; nd.inputs["Distance"].default_value = 0.35
    # flakes: camera-facing quads through the whole view, smaller and fainter far away, streaked near the lens
    cam = bpy.data.objects[cam_name]
    cp = cam.location
    me = bpy.data.meshes.new("Beauty_Snow"); bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    cl = bm.loops.layers.float_color.new("Alpha")
    rnd = random.Random(seed)
    wdir = Vector((0.95, 0.0, -0.31)).normalized()            # streak direction on screen (right and down)
    up = Vector((0.0, 0.0, 1.0)); right = Vector((1.0, 0.0, 0.0))
    for k in range(flakes):
        if rnd.random() < 0.22:
            d = rnd.uniform(1.4, 12.0)                         # close flakes, streaked by the wind
        else:
            d = 4.0 + 86.0 * rnd.random() ** (1.0 / 2.2)         # the rest fill the depth of the storm
        x = rnd.uniform(-1.05, 1.05) * d * math.tan(math.radians(15.0)) * 1.778
        z = rnd.uniform(-1.05, 1.05) * d * math.tan(math.radians(15.0))
        c = cp + Vector((x, d, z))                            # the camera looks along Blender +y (Godot -z)
        s = (0.003 + 0.005 * rnd.random()) * (1.0 + d * 0.045)
        if d < 4.0:
            s *= 1.6                                            # bigger soft flakes by the lens
        streak = 1.0 + 0.7 * rnd.random()                       # only slightly drawn out by the wind, never lines
        alpha = (0.26 if d < 4 else 0.78) * rnd.uniform(0.6, 1.0) * (1.0 - 0.55 * min(d / 90.0, 1.0))
        a = wdir * (s * streak); b = Vector((-wdir.z, 0.0, wdir.x)) * s
        vs = [bm.verts.new(c - a - b), bm.verts.new(c + a - b), bm.verts.new(c + a + b), bm.verts.new(c - a + b)]
        f = bm.faces.new(vs)
        for l, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            l[uvl].uv = uv; l[cl] = (alpha, alpha, alpha, 1.0)
    # soft powder blowing low over the snow, from near to far
    for k in range(1600):
        d = 2.5 + 55.0 * rnd.random() ** 1.5
        x = rnd.uniform(-1.05, 1.05) * d * math.tan(math.radians(15.0)) * 1.778
        c = Vector((cp.x + x, cp.y + d, rnd.uniform(0.0, 0.5) ** 1.5 + 0.02))
        s = rnd.uniform(0.12, 0.45) * (1.0 + d * 0.02)
        a = wdir * (s * 1.8); a.z *= 0.2; b = Vector((0.0, 0.0, s * 0.45))
        vs = [bm.verts.new(c - a - b), bm.verts.new(c + a - b), bm.verts.new(c + a + b), bm.verts.new(c - a + b)]
        f = bm.faces.new(vs)
        al = rnd.uniform(0.03, 0.07)
        for l, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            l[uvl].uv = uv; l[cl] = (al, al, al, 1.0)
    bm.to_mesh(me); bm.free()
    me.materials.append(_mat_flake())
    so = bpy.data.objects.new("Beauty_Snow", me); bc.objects.link(so)
    so.visible_shadow = False
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.render.resolution_percentage = 100
    sc.cycles.samples = 160; sc.cycles.use_denoising = True
    sc.cycles.transparent_max_bounces = 96
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = 'AgX - Medium Low Contrast'
    except Exception:
        sc.view_settings.look = 'None'
    sc.view_settings.exposure = 0.35
    return {"flakes": flakes}

if __name__ == "__main__":
    BUILD_INFO = build_all()
