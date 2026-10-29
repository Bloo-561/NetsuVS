# Celdic - 3D stage build script (Blender 5.x, runs in --background). Two variants of one town square:
#   VARIANT=day      sunny afternoon after the attack (collapsed timber frames, bunting still up)
#   VARIANT=burning  the town on fire at dusk: dark smoke, red sky, flames, lit lamps and windows
#
#   blender --background --factory-startup --python run_ce.py -- VARIANT=burning STEPS=build,bake,pv,export
#
# Layout is written in GODOT coordinates (x right, y up, +z toward the camera) and converted
# to Blender (Z-up) by G():  Godot (x, y, z) -> Blender (x, -z, y).  1 unit = 1 m.
# Baked groups (atlases): CE_Buildings, CE_Props, CE_Far, CE_Floor (light map only)
# Card groups (Godot shaders): CE_Sky, CE_Window (emit in the bake), CE_Bunting, CE_Fire, CE_Smoke (not baked)
import bpy, bmesh, math, random
from mathutils import Vector, Matrix

ROOT = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\stages\celdic"
TEXD = ROOT + r"\textures"
VARIANT = globals().get("VARIANT") or "day"

# ---------------- layout (Godot space, metres) ----------------
CENTER_Z = -10.0
FLOOR_X = 40.0                     # floor quad: x +-40, z -62..+22
FLOOR_BACK, FLOOR_FRONT = -62.0, 22.0
WELL = (0.0, -18.0)                # the well under the stone arch
RING_R = 9.5                       # curb ring of the round paved area
ARCH_HALF, ARCH_SPRING = 2.6, 4.6  # arch half-width and height where it starts to curve
SKY_R = 280.0
LANE_X, LANE_Z = 12.5, -9.0        # keep |x| < 12.5 and z > -9 clear (fight lane)

VARIANTS = {
    "day": dict(sun_dir=(0.45, -0.7, -0.55), sun_energy=4.5, sun_color="#fff0d6", world=("#a8c8f0", 1.1),
                fill=(6000, "#fff3e0"), top=(8000, "#bcd4ff"),
                sky=[(0.0, "#c8d8e0"), (0.12, "#eef4f8"), (0.2, "#a6cbef"), (1.0, "#3e7ad0")], sky_strength=1.0,
                haze="#a8c0d8", lamp_glow=0.6, lamp_w=0, window_color="#2a3036", window_glow=0.2, window_w=0, fire_w=0),
    "burning": dict(sun_dir=(0.45, -0.7, -0.55), sun_energy=0.0, sun_color="#ff8a5a", world=("#2a2038", 0.45),
                    fill=(1600, "#7a5a8a"), top=(2500, "#3a2a4a"),
                    sky=[(0.0, "#3a1a18"), (0.1, "#ff5a24"), (0.17, "#a8301c"), (0.32, "#3a2228"), (1.0, "#121018")],
                    sky_strength=1.2, haze="#7a2e22", lamp_glow=8.0, lamp_w=150, window_color="#ff8a3a", window_glow=6.0,
                    window_w=160, fire_w=380),
}
V = VARIANTS[VARIANT]

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

def stone_material(name, dark, light, moss=0.15, carved=False, rough=0.6):
    """Weathered blue-grey stone; teal grime in the crevices; carved = knotwork relief."""
    b = NB(name)
    n1 = b.noise(b.pos, 1.1, 6, 0.6)
    c = b.ramp(n1.outputs["Fac"], [(0.32, dark), (0.68, light)])
    grime = b.noise(b.pos, 0.35, 3, 0.5)
    gm = b.math('MULTIPLY', b.math('GREATER_THAN', grime.outputs["Fac"], 0.55), moss)
    c = b.mixc(c, "#3f6b66", gm)
    b.link(c, b.bsdf.inputs["Base Color"])
    b.bsdf.inputs["Roughness"].default_value = rough
    bump = b.n("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.25
    if carved:
        w = b.n("ShaderNodeTexWave"); w.wave_type = 'RINGS'
        w.inputs["Scale"].default_value = 4.0; w.inputs["Distortion"].default_value = 5.0
        w.inputs["Detail"].default_value = 2.0
        b.link(b.pos, w.inputs["Vector"])
        vor = b.n("ShaderNodeTexVoronoi"); vor.feature = 'DISTANCE_TO_EDGE'; vor.inputs["Scale"].default_value = 7.0
        b.link(b.pos, vor.inputs["Vector"])
        h = b.math('ADD', b.math('MULTIPLY', w.outputs["Fac"], 0.6), b.math('LESS_THAN', vor.outputs["Distance"], 0.03))
        bump.inputs["Strength"].default_value = 0.45
        b.link(h, bump.inputs["Height"])
        # carved grooves catch dirt: darken them
        c2 = b.mixc(c, "#2f3a40", b.math('MULTIPLY', b.math('LESS_THAN', vor.outputs["Distance"], 0.03), 0.35))
        b.link(c2, b.bsdf.inputs["Base Color"])
    else:
        b.link(n1.outputs["Fac"], bump.inputs["Height"])
    b.link(bump.outputs[0], b.bsdf.inputs["Normal"])
    return b

def emissive_card(name, fn, color, strength, floor=0.25):
    b = NB(name)
    im = b.image(fn, b.uv, 'EXTEND', True)
    k = b.math('ADD', b.math('MULTIPLY', im.outputs["Color"], 1.0 - floor), floor)
    em = b.n("ShaderNodeEmission"); em.inputs["Color"].default_value = (*srgb(color), 1)
    b.link(b.math('MULTIPLY', k, strength), em.inputs["Strength"])
    b.link(em.outputs[0], b.out.inputs[0])
    return b


def beam(g, p0, p1, w, h, m="Beam"):
    """Square timber from Godot point p0 to p1 (w across, h tall)."""
    g = grp(g) if isinstance(g, str) else g
    a, b = G(*p0), G(*p1); d = b - a; L = d.length
    q = d.normalized().to_track_quat('Z', 'Y')
    M = Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4() @ Matrix.Diagonal((w, h, L, 1.0))
    r = bmesh.ops.create_cube(g.bm, size=1.0, matrix=M)
    _tag(g, list({f for v in r["verts"] for f in v.link_faces}), m)

def gable_house(g, cx, cz, wx, wz, wall_h, rise, m_wall="Planks", m_roof="Roof", over=0.45, ridge_z=True, trim="Beam",
                broken=0.0, seed=0):
    """Box house with a gable roof. ridge_z: ridge runs front-back (gable end faces the camera).
    broken: fraction of the camera-facing roof slope that has collapsed (only charred rafters left)."""
    rnd = random.Random(seed)
    box(g, cx, -0.2, wall_h, cz, wx, wz, m_wall)
    for sx in (-1, 1):                                    # corner posts and a mid band
        for sz in (-1, 1):
            box(g, cx + sx * (wx / 2 - 0.1), -0.2, wall_h, cz + sz * (wz / 2 - 0.1), 0.28, 0.28, trim, 0.02)
    box(g, cx, wall_h * 0.48, wall_h * 0.48 + 0.18, cz, wx + 0.08, wz + 0.08, trim)
    box(g, cx, wall_h - 0.2, wall_h, cz, wx + 0.12, wz + 0.12, trim)
    # gable triangles + roof slabs
    gg = grp(g) if isinstance(g, str) else g
    span = wx if ridge_z else wz
    length = wz if ridge_z else wx
    for s in (-1, 1):
        # gable wall triangle at each end
        if ridge_z:
            zf = cz + s * wz / 2
            if broken > 0 and s > 0:            # front gable burnt away: only charred studs of uneven height remain
                for k in range(7):
                    xk = cx - wx / 2 + 0.4 + k * (wx - 0.8) / 6
                    hk = wall_h + (rise * (1 - abs(xk - cx) / (wx / 2))) * rnd.uniform(0.2, 0.9)
                    box(g, xk, wall_h, hk, zf, 0.14, 0.14, "Charred")
            else:
                quad(gg, [(cx - wx / 2, wall_h, zf), (cx + wx / 2, wall_h, zf), (cx, wall_h + rise, zf)][::(1 if s > 0 else -1)],
                     [(0, 0), (1, 0), (0.5, 1)][::(1 if s > 0 else -1)], m_wall)
        else:
            xf = cx + s * wx / 2
            quad(gg, [(xf, wall_h, cz + wz / 2), (xf, wall_h, cz - wz / 2), (xf, wall_h + rise, cz)][::(1 if s > 0 else -1)],
                 [(0, 0), (1, 0), (0.5, 1)][::(1 if s > 0 else -1)], m_wall)
        # roof slab from eave to ridge (with overhang)
        half = span / 2 + over
        ang = math.atan2(rise, span / 2)
        Ls = half / math.cos(ang)
        full = length + 2 * over
        gone = (broken if s > 0 else broken * 0.6) if ridge_z else (broken if s > 0 else 0.0)
        keep = full * (1 - gone)
        if ridge_z:
            e = (cx + s * half, wall_h - over * math.tan(ang), cz); r_ = (cx, wall_h + rise, cz)
            zc = cz - full * gone / 2                # the intact part stays at the back
            mid = ((e[0] + r_[0]) / 2, (e[1] + r_[1]) / 2 + 0.08, zc)
            M = Matrix.Translation(G(*mid)) @ Matrix.Rotation(s * ang, 4, 'Y') @ Matrix.Diagonal((Ls, keep, 0.16, 1.0))
            if gone > 0:
                zz = zc + keep / 2 + 0.35
                while zz < cz + full / 2:
                    t = rnd.uniform(0.35, 1.0) if rnd.random() < 0.6 else 1.0      # snapped rafters
                    p0 = (e[0], e[1], zz); p1 = (e[0] + (r_[0] - e[0]) * t, e[1] + (r_[1] - e[1]) * t, zz)
                    beam(g, p0, p1, 0.14, 0.2, "Charred")
                    zz += rnd.uniform(0.6, 0.9)
        else:
            e = (cx, wall_h - over * math.tan(ang), cz + s * half); r_ = (cx, wall_h + rise, cz)
            xc = cx + full * gone / 2
            mid = (xc, (e[1] + r_[1]) / 2 + 0.08, (e[2] + r_[2]) / 2)
            M = Matrix.Translation(G(*mid)) @ Matrix.Rotation(s * ang, 4, 'X') @ Matrix.Diagonal((keep, Ls, 0.16, 1.0))
            if gone > 0:
                xx = xc - keep / 2 - 0.35
                while xx > cx - full / 2:
                    t = rnd.uniform(0.35, 1.0) if rnd.random() < 0.6 else 1.0
                    p0 = (xx, e[1], e[2]); p1 = (xx, e[1] + (r_[1] - e[1]) * t, e[2] + (r_[2] - e[2]) * t)
                    beam(g, p0, p1, 0.14, 0.2, "Charred")
                    xx -= rnd.uniform(0.6, 0.9)
        r = bmesh.ops.create_cube(gg.bm, size=1.0, matrix=M)
        _tag(gg, list({f for v in r["verts"] for f in v.link_faces}), m_roof)
    # ridge beam
    if ridge_z:
        box(g, cx, wall_h + rise - 0.05, wall_h + rise + 0.2, cz, 0.3, length + 2 * over, trim)
    else:
        box(g, cx, wall_h + rise - 0.05, wall_h + rise + 0.2, cz, length + 2 * over, 0.3, trim)

def window(g, x, y, z, w, h, face_z=True, s=1):
    """Framed window on a +z (or +x) facing wall; the pane is a glowing card (Godot: CE_Window)."""
    if face_z:
        box(g, x, y - 0.08, y + h + 0.08, z + s * 0.05, w + 0.2, 0.12, "Beam")
        quad("CE_Window", [(x - w / 2, y, z + s * 0.12), (x + w / 2, y, z + s * 0.12), (x + w / 2, y + h, z + s * 0.12), (x - w / 2, y + h, z + s * 0.12)][::s],
             [(0, 0), (1, 0), (1, 1), (0, 1)][::s], "WindowCard")
        box(g, x, y + h / 2 - 0.04, y + h / 2 + 0.04, z + s * 0.14, w, 0.05, "Beam")
        box(g, x, y, y + h, z + s * 0.14, 0.06, 0.05, "Beam")
    else:
        box(g, x + s * 0.05, y - 0.08, y + h + 0.08, z, 0.12, w + 0.2, "Beam")
        quad("CE_Window", [(x + s * 0.12, y, z + w / 2), (x + s * 0.12, y, z - w / 2), (x + s * 0.12, y + h, z - w / 2), (x + s * 0.12, y + h, z + w / 2)][::s],
             [(0, 0), (1, 0), (1, 1), (0, 1)][::s], "WindowCard")
    WINDOWS.append((x, y + h / 2, z, w * h))

# ======================================================================
#  materials
# ======================================================================
def wood_material(name, dark, light, scale=2.5, vertical=True, rough=0.8, scorch=0.55):
    b = NB(name)
    w = b.n("ShaderNodeTexWave"); w.wave_type = 'BANDS'; w.bands_direction = 'X' if vertical else 'Y'
    w.inputs["Scale"].default_value = scale; w.inputs["Distortion"].default_value = 5.0; w.inputs["Detail"].default_value = 3.0
    b.link(b.pos, w.inputs["Vector"])
    n = b.noise(b.pos, 6.0, 4, 0.6)
    c = b.ramp(w.outputs["Fac"], [(0.2, dark), (0.8, light)])
    c = b.mixc(c, dark, b.math('MULTIPLY', n.outputs["Fac"], 0.35))
    # plank seams
    br = b.n("ShaderNodeTexBrick"); br.offset = 0.5
    for k, v in (("Scale", 1.0), ("Mortar Size", 0.012), ("Brick Width", 0.22 if vertical else 3.0), ("Row Height", 3.0 if vertical else 0.22)):
        br.inputs[k].default_value = v
    br.inputs["Color1"].default_value = (1, 1, 1, 1); br.inputs["Color2"].default_value = (0.92, 0.92, 0.92, 1)
    br.inputs["Mortar"].default_value = (0.25, 0.22, 0.2, 1)
    b.link(b.uv, br.inputs["Vector"])
    c = b.mixc(c, br.outputs["Color"], 1.0, 'MULTIPLY')
    # scorch / soot: big blotches of burnt wood (the town has been attacked)
    sn = b.noise(b.pos, 0.35, 4, 0.6)
    burn = b.math('MULTIPLY', b.math('GREATER_THAN', sn.outputs["Fac"], 1.0 - scorch * 0.6), 0.85)
    c = b.mixc(c, "#181210", burn)
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = rough
    return b

def plain(name, dark, light, scale=3.0, rough=0.7, metal=0.0):
    b = NB(name)
    n = b.noise(b.pos, scale, 4, 0.55)
    b.link(b.ramp(n.outputs["Fac"], [(0.3, dark), (0.7, light)]), b.bsdf.inputs["Base Color"])
    b.bsdf.inputs["Roughness"].default_value = rough; b.bsdf.inputs["Metallic"].default_value = metal
    return b

def brick_material(name, c1, c2, mortar, w=0.25, h=0.08):
    b = NB(name)
    br = b.n("ShaderNodeTexBrick"); br.offset = 0.5
    for k, v in (("Scale", 1.0), ("Mortar Size", 0.012), ("Brick Width", w), ("Row Height", h)):
        br.inputs[k].default_value = v
    br.inputs["Color1"].default_value = (*srgb(c1), 1); br.inputs["Color2"].default_value = (*srgb(c2), 1)
    br.inputs["Mortar"].default_value = (*srgb(mortar), 1)
    b.link(b.uv, br.inputs["Vector"])
    n = b.noise(b.pos, 2.0, 3, 0.5)
    c = b.mixc(br.outputs["Color"], b.ramp(n.outputs["Fac"], [(0.3, "#b8b0a8"), (0.7, "#ffffff")]), 1.0, 'MULTIPLY')
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = 0.85
    return b

def roof_material(name):
    """Terracotta tiles: rows of half-round tiles with dirt and colour variation."""
    b = NB(name)
    br = b.n("ShaderNodeTexBrick"); br.offset = 0.5
    for k, v in (("Scale", 1.0), ("Mortar Size", 0.01), ("Brick Width", 0.3), ("Row Height", 0.22)):
        br.inputs[k].default_value = v
    br.inputs["Color1"].default_value = (*srgb("#b5583a"), 1); br.inputs["Color2"].default_value = (*srgb("#9a4630"), 1)
    br.inputs["Mortar"].default_value = (*srgb("#4a2a20"), 1)
    b.link(b.uv, br.inputs["Vector"])
    n = b.noise(b.pos, 1.5, 4, 0.6)
    c = b.mixc(br.outputs["Color"], "#5a4a3a", b.math('MULTIPLY', b.math('GREATER_THAN', n.outputs["Fac"], 0.6), 0.5))
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = 0.75
    return b

def haze_material(name, dark, light, haze_col, near, far, hmin, hmax):
    b = plain(name, dark, light, 0.08, 0.9)
    sp = b.n("ShaderNodeSeparateXYZ"); b.link(b.pos, sp.inputs[0])
    mr = b.n("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = near; mr.inputs["From Max"].default_value = far
    mr.inputs["To Min"].default_value = hmin; mr.inputs["To Max"].default_value = hmax
    dist = b.math('ABSOLUTE', sp.outputs[1])            # Blender -y == Godot +z ... distance along the view
    b.link(dist, mr.inputs[0])
    em = b.n("ShaderNodeEmission"); em.inputs["Color"].default_value = (*srgb(haze_col), 1); em.inputs["Strength"].default_value = 1.0
    mix = b.n("ShaderNodeMixShader"); b.link(mr.outputs[0], mix.inputs[0])
    b.link(b.bsdf.outputs[0], mix.inputs[1]); b.link(em.outputs[0], mix.inputs[2]); b.link(mix.outputs[0], b.out.inputs[0])
    return b

def add_soot(mname, amount=0.45, scale=0.3):
    """Blotchy soot / burn marks layered over an existing material's base colour."""
    m = MATS[mname]; nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    sock = bsdf.inputs["Base Color"]
    if not sock.links:
        return
    src = sock.links[0].from_socket
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 4.0
    nt.links.new(geo.outputs["Position"], nz.inputs["Vector"])
    gt = nt.nodes.new("ShaderNodeMapRange"); gt.inputs["From Min"].default_value = 1.0 - amount * 0.6
    gt.inputs["From Max"].default_value = 1.0 - amount * 0.6 + 0.08
    nt.links.new(nz.outputs["Fac"], gt.inputs[0])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MIX'
    nt.links.new(gt.outputs[0], mix.inputs[0]); nt.links.new(src, mix.inputs[6])
    mix.inputs[7].default_value = (*srgb("#1a1614"), 1)
    nt.links.new(mix.outputs[2], sock)

def emit_solid(name, color, strength):
    b = NB(name)
    em = b.n("ShaderNodeEmission"); em.inputs["Color"].default_value = (*srgb(color), 1); em.inputs["Strength"].default_value = strength
    b.link(em.outputs[0], b.out.inputs[0])
    return b

def build_materials():
    wood_material("Planks", "#3d2c22", "#6a4e3a")
    wood_material("PlanksLight", "#5a4232", "#8a6a50")
    wood_material("Beam", "#4a3424", "#7a5a40", 4.0, vertical=False)
    wood_material("BeamDark", "#2a1e18", "#4a3628", 4.0, vertical=False)
    wood_material("Charred", "#141010", "#2e2420", 4.0, vertical=False, rough=0.9)
    roof_material("Roof")
    stone_material("StoneMoss", "#6a7260", "#8f957e", 0.35)
    stone_material("StoneLight", "#8a8478", "#b0a898", 0.1)
    brick_material("Brick", "#8a4a36", "#7a3e2e", "#5a4a40")
    brick_material("BrickWell", "#8c8478", "#a59c8c", "#4e463e", 0.22, 0.09)
    plain("RedStone", "#8a2a20", "#b0402c", 4.0, 0.6)
    plain("ArchMetal", "#5a3a26", "#8a5a38", 3.0, 0.55)
    plain("Iron", "#15161a", "#2a2c32", 6.0, 0.45, 0.4)
    plain("BenchRed", "#8a2a1e", "#b23a26", 8.0, 0.6)
    plain("Leaf", "#2e4a1e", "#4f7a2e", 9.0, 0.8)
    plain("FlowerRed", "#b0202a", "#e04048", 20.0, 0.7)
    plain("FlowerWhite", "#c8c4b8", "#f2efe6", 20.0, 0.7)
    plain("FlowerPink", "#b04a8a", "#e07ab8", 20.0, 0.7)
    plain("Dirt", "#4a3e30", "#6a5a46", 3.0, 0.95)
    plain("Water", "#0a0e12", "#1a2228", 2.0, 0.1)
    plain("Rubble", "#4e4640", "#7a7064", 5.0, 0.9)
    haze_material("Mountain", "#3e5a46", "#5e7a58", V["haze"], 120, 260, 0.45, 0.8)
    haze_material("FarRoof", "#8a4a32", "#a85a3a", V["haze"], 30, 80, 0.05, 0.35)
    haze_material("FarWall", "#5a4a3a", "#7a6450", V["haze"], 30, 80, 0.05, 0.35)
    haze_material("Tree", "#26401c", "#3e6028", V["haze"], 30, 90, 0.1, 0.4)
    for mname, amt in (("StoneMoss", 0.4), ("StoneLight", 0.35), ("Brick", 0.5), ("BrickWell", 0.35), ("FarWall", 0.55),
                       ("FarRoof", 0.5), ("Roof", 0.45), ("ArchMetal", 0.3), ("BenchRed", 0.4), ("Rubble", 0.3)):
        add_soot(mname, amt)
    plain("Soot", "#0c0a0a", "#1c1716", 3.0, 0.95)                       # burnt holes / blackened openings
    emit_solid("LampGlass", "#ffc27a", V["lamp_glow"])
    emit_solid("WindowCard", V["window_color"], V["window_glow"])
    emit_solid("FireCard", "#ff7a2a", 6.0)
    emit_solid("SmokeCard", "#202020", 0.0)
    emit_solid("BuntingCard", "#d04040", 0.0)
    b = NB("SkyCard")
    sep = b.n("ShaderNodeSeparateXYZ"); b.link(b.uv, sep.inputs[0])
    r = b.ramp(sep.outputs[1], V["sky"])
    em = b.n("ShaderNodeEmission"); em.inputs["Strength"].default_value = V["sky_strength"]
    b.link(r, em.inputs["Color"]); b.link(em.outputs[0], b.out.inputs[0])
    # the floor bakes a LIGHT MAP only; Godot draws the cobbles. A flat average stone colour here
    # (an image texture got stamped, inverted, into the light map)
    b = NB("FloorCobble")
    b.bsdf.inputs["Base Color"].default_value = (*srgb("#8f8476"), 1)
    b.bsdf.inputs["Roughness"].default_value = 0.8
    b = NB("Stand_P1"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#2d6cdf"), 1)
    b = NB("Stand_P2"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#e0463a"), 1)

# ======================================================================
#  the square
# ======================================================================
WINDOWS = []     # (x, y, z, area) - window lights (burning: fire inside)
LAMPS = [(11.6, -13.5, 4.4)]                       # standing lamp(s) - lit at night
FALLEN_LAMP = ((13.8, -19.6), (11.4, -21.9))       # knocked over: base -> lantern end

def build_floor():
    g = grp("CE_Floor")
    quad(g, [(-FLOOR_X, 0, FLOOR_FRONT), (FLOOR_X, 0, FLOOR_FRONT), (FLOOR_X, 0, FLOOR_BACK), (-FLOOR_X, 0, FLOOR_BACK)],
         [(-FLOOR_X, -FLOOR_FRONT), (FLOOR_X, -FLOOR_FRONT), (FLOOR_X, -FLOOR_BACK), (-FLOOR_X, -FLOOR_BACK)], "FloorCobble")

def build_well_and_arch():
    g = "CE_Props"; wx, wz = WELL
    # low ring curb around the paved circle + the step under the well
    n = 48
    for i in range(n):
        a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n; am = (a0 + a1) / 2
        r = RING_R; L = 2 * r * math.sin(math.pi / n) + 0.02
        obox(g, (wx + r * math.sin(am), 0.05, wz - r * math.cos(am)), (L, 0.16, 0.32), -math.degrees(am), "StoneLight", 0.03)
    octa_prism(g, wx, wz, 2.05, -0.2, 0.22, "StoneLight", 16, 0)
    octa_prism(g, wx, wz, 1.55, 0.2, 0.85, "BrickWell", 16, 0)
    octa_prism(g, wx, wz, 1.62, 0.85, 0.98, "RedStone", 16, 0)
    octa_prism(g, wx, wz, 1.2, 0.9, 0.93, "Water", 16, 0)
    # stone arch over the well
    for sx in (-1, 1):
        x = wx + sx * ARCH_HALF
        box(g, x, -0.2, 0.6, wz, 1.05, 1.05, "StoneLight", 0.04)
        box(g, x, 0.6, ARCH_SPRING, wz, 0.78, 0.78, "StoneMoss", 0.03)
        box(g, x, ARCH_SPRING - 0.35, ARCH_SPRING, wz, 0.95, 0.95, "StoneLight", 0.03)
    # one smooth curved band (inner / outer radius, front / back face) instead of stacked boxes
    gg = grp(g); bm = gg.bm; segs = 32; r_in, r_out, hz = ARCH_HALF - 0.32, ARCH_HALF + 0.32, 0.3
    rings = []
    for i in range(segs + 1):
        a = math.pi * i / segs
        c, s_ = -math.cos(a), math.sin(a)
        rings.append([bm.verts.new(G(wx + r * c, ARCH_SPRING + r * s_, wz + dz)) for (r, dz) in
                      ((r_out, hz), (r_out, -hz), (r_in, -hz), (r_in, hz))])
    new = []
    for i in range(segs):
        A, B = rings[i], rings[i + 1]
        for k in range(4):
            new.append(bm.faces.new((A[k], A[(k + 1) % 4], B[(k + 1) % 4], B[k])))
    new.append(bm.faces.new(rings[0])); new.append(bm.faces.new(rings[-1][::-1]))
    bmesh.ops.recalc_face_normals(bm, faces=new)
    _tag(gg, new, "ArchMetal")
    for i in range(1, 8):                                   # rivet bands across the arch
        a = math.pi * i / 8
        c, s_ = -math.cos(a), math.sin(a)
        p0 = (wx + (r_in - 0.02) * c, ARCH_SPRING + (r_in - 0.02) * s_, wz); p1 = (wx + (r_out + 0.02) * c, ARCH_SPRING + (r_out + 0.02) * s_, wz)
        beam(g, p0, p1, 0.66, 0.08, "Iron")
    top = ARCH_SPRING + ARCH_HALF + 0.3
    box(g, wx, top - 0.1, top + 0.35, wz, 0.7, 0.5, "StoneLight", 0.03)
    box(g, wx, top + 0.35, top + 1.3, wz, 0.14, 0.14, "Iron")
    box(g, wx, top + 0.95, top + 1.05, wz, 0.8, 0.08, "Iron")
    return (wx, top + 1.1, wz)

def bench(x, z, rot=0.0):
    g = "CE_Props"
    obox(g, (x, 0.45, z), (2.2, 0.08, 0.55), rot, "BenchRed", 0.01)
    obox(g, (x, 0.85, z - 0.25 * math.cos(math.radians(rot))), (2.2, 0.5, 0.06), rot, "BenchRed", 0.01)
    for sx in (-0.95, 0.95):
        dx, dz = sx * math.cos(math.radians(rot)), sx * math.sin(math.radians(rot))
        obox(g, (x + dx, 0.22, z + dz), (0.06, 0.44, 0.5), rot, "Iron")

def planter(x, z, w=2.0, d=0.8, h=0.6, seed=0):
    g = "CE_Props"; rnd = random.Random(seed)
    box(g, x, -0.1, h, z, w, d, "Brick", 0.02)
    box(g, x, h - 0.05, h + 0.06, z, w * 0.94, d * 0.86, "Dirt")
    for k in range(int(w * 9)):
        fx = x + rnd.uniform(-w / 2 + 0.15, w / 2 - 0.15); fz = z + rnd.uniform(-d / 2 + 0.12, d / 2 - 0.12)
        leaf_y = h + rnd.uniform(0.05, 0.25)
        rock(g, fx, leaf_y, fz, 0.16, 0.12, 0.16, rnd.randint(0, 9999), "Leaf")
        if rnd.random() < 0.6:
            rock(g, fx + rnd.uniform(-0.05, 0.05), leaf_y + 0.12, fz, 0.07, 0.05, 0.07, rnd.randint(0, 9999),
                 rnd.choice(("FlowerRed", "FlowerRed", "FlowerWhite", "FlowerPink")))

def barrel(x, z, s=1.0):
    g = "CE_Props"
    cyl(g, x, -0.05, z, 0.36 * s, 0.4 * s, 0.5 * s, "PlanksLight", 12)
    cyl(g, x, 0.45 * s, z, 0.4 * s, 0.36 * s, 0.5 * s, "PlanksLight", 12)
    for y in (0.15, 0.48, 0.82):
        cyl(g, x, y * s, z, 0.415 * s, 0.415 * s, 0.05 * s, "Iron", 12)

def lamp(x, z, h):
    g = "CE_Props"
    cyl(g, x, -0.05, z, 0.2, 0.16, 0.5, "Iron", 8)
    cyl(g, x, 0.45, z, 0.08, 0.06, h - 0.9, "Iron", 8)
    box(g, x, h - 0.5, h - 0.42, z, 0.5, 0.5, "Iron")
    box(g, x, h - 0.42, h + 0.15, z, 0.36, 0.36, "LampGlass")
    cyl(g, x, h + 0.15, z, 0.33, 0.05, 0.3, "Iron", 4, 45)
    cyl(g, x, h + 0.45, z, 0.05, 0.05, 0.15, "Iron", 6)

def rock(g, x, y, z, sx, sy, sz, seed, m="Rubble", sub=1, jag=0.25):
    gg = grp(g) if isinstance(g, str) else g
    rnd = random.Random(seed)
    M = Matrix.Translation(G(x, y, z)) @ Matrix.Rotation(rnd.uniform(0, 6.28), 4, 'Z') @ Matrix.Diagonal((sx, sz, sy, 1.0))
    r = bmesh.ops.create_icosphere(gg.bm, subdivisions=sub, radius=1.0, matrix=M)
    c = G(x, y, z)
    for v in r["verts"]:
        v.co = c + (v.co - c) * rnd.uniform(1 - jag, 1 + jag * 0.5)
    _tag(gg, list({f for v in r["verts"] for f in v.link_faces}), m)

def rubble_pile(x, z, r, n, seed, mats=("Rubble", "Rubble", "Brick", "Charred", "Roof")):
    """A heap of broken stone, brick, tiles and burnt timber, highest in the middle."""
    g = "CE_Props"; rnd = random.Random(seed)
    for k in range(n):
        a = rnd.uniform(0, 6.283); d = r * math.sqrt(rnd.random())
        px, pz = x + d * math.cos(a), z + d * math.sin(a)
        h = (1 - d / r) * r * 0.45
        m = rnd.choice(mats)
        if m == "Charred" or (m == "Roof" and rnd.random() < 0.5):
            beam(g, (px, h * 0.5, pz), (px + rnd.uniform(-1.2, 1.2), h * 0.5 + rnd.uniform(-0.1, 0.5), pz + rnd.uniform(-1.2, 1.2)),
                 rnd.uniform(0.12, 0.25), rnd.uniform(0.1, 0.2), m)
        else:
            s = rnd.uniform(0.18, 0.45)
            rock(g, px, h * 0.7, pz, s * rnd.uniform(0.8, 1.4), s * rnd.uniform(0.5, 0.9), s, rnd.randint(0, 99999), m)

def wrecked_cart(x, z):
    """A toppled hand cart: tilted bed, one wheel on its axle, one wheel fallen flat."""
    g = "CE_Props"
    obox(g, (x, 0.55, z), (2.4, 0.12, 1.3), 18, "PlanksLight", 0.02)
    obox(g, (x - 0.2, 0.95, z - 0.62), (2.3, 0.6, 0.08), 18, "Planks", 0.01)
    beam(g, (x + 1.2, 0.5, z + 0.3), (x + 2.8, 0.05, z + 0.9), 0.1, 0.1, "Beam")          # shafts on the ground
    beam(g, (x + 1.2, 0.5, z - 0.3), (x + 2.7, 0.05, z - 0.2), 0.1, 0.1, "Beam")
    gg = grp(g)
    M = Matrix.Translation(G(x - 0.6, 0.55, z + 0.75)) @ Matrix.Rotation(math.radians(90), 4, 'X')
    r = bmesh.ops.create_cone(gg.bm, cap_ends=True, cap_tris=False, segments=14, radius1=0.55, radius2=0.55, depth=0.1, matrix=M)
    _tag(gg, list({f for v in r["verts"] for f in v.link_faces}), "BeamDark")
    cyl(g, x + 0.8, 0.0, z - 1.4, 0.55, 0.55, 0.1, "BeamDark", 14)                         # the other wheel, lying flat
    for k in range(5):
        box(g, x - 1.6 + k * 0.5, -0.05, 0.45, z - 1.2 + (k % 2) * 0.3, 0.4, 0.4, "PlanksLight", 0.03, k * 17)   # spilled crates

def burnt_hole(g, x, y0, y1, z, w, seed, face=1):
    """A ragged burnt-through hole in a +z facing wall: black recess with charred plank ends around it."""
    rnd = random.Random(seed)
    box(g, x, y0, y1, z + face * 0.04, w, 0.06, "Soot")
    n = int(w / 0.22)
    for k in range(n):
        xk = x - w / 2 + (k + 0.5) * w / n
        top = y1 + rnd.uniform(-0.4, 0.5); bot = y0 + rnd.uniform(-0.4, 0.4)
        box(g, xk, top - rnd.uniform(0.1, 0.5), top, z + face * 0.08, w / n * 0.9, 0.07, "Charred")
        box(g, xk, bot, bot + rnd.uniform(0.1, 0.4), z + face * 0.08, w / n * 0.9, 0.07, "Charred")

def ruin(g, x, z, w, d, h, seed):
    """A burnt-out house: walls with jagged broken tops, no roof, charred beams leaning inside."""
    rnd = random.Random(seed)
    for side in range(4):
        horiz = side % 2 == 0
        L = w if horiz else d
        n = max(3, int(L / 0.8))
        for k in range(n):
            t0 = -L / 2 + L * k / n
            hh = h * rnd.uniform(0.35, 1.0) * (0.6 if rnd.random() < 0.3 else 1.0)
            if horiz:
                box(g, x + t0 + L / n / 2, -0.2, hh, z + (d / 2 if side == 0 else -d / 2), L / n + 0.02, 0.35, "FarWall")
            else:
                box(g, x + (w / 2 if side == 1 else -w / 2), -0.2, hh, z + t0 + L / n / 2, 0.35, L / n + 0.02, "FarWall")
    for k in range(rnd.randint(2, 4)):
        a = rnd.uniform(0, 6.283)
        beam(g, (x + rnd.uniform(-w / 3, w / 3), 0, z + rnd.uniform(-d / 3, d / 3)),
             (x + math.cos(a) * w * 0.4, h * rnd.uniform(0.6, 1.2), z + math.sin(a) * d * 0.4), 0.2, 0.25, "Charred")

def fence(x0, z0, x1, z1, h=1.0, posts=None, m="Beam"):
    g = "CE_Props"
    L = math.hypot(x1 - x0, z1 - z0); n = posts or max(2, int(L / 1.6) + 1)
    for k in range(n):
        t = k / (n - 1); x, z = x0 + (x1 - x0) * t, z0 + (z1 - z0) * t
        box(g, x, -0.1, h, z, 0.16, 0.16, m, 0.02)
    for y in (h * 0.4, h * 0.85):
        beam(g, (x0, y, z0), (x1, y, z1), 0.08, 0.12, m)

def build_left():
    g = "CE_Buildings"
    # the wooden house (gable end faces the camera, warm window)
    hx, hz = -11.0, -26.0
    gable_house(g, hx, hz, 7.4, 6.4, 4.6, 2.6, broken=0.65, seed=3)
    burnt_hole(g, hx + 1.0, 2.9, 4.2, hz + 3.2, 2.2, 41)
    # the collapsed part of the roof lies against the house: tiles, rafters, broken tiles
    obox(g, (hx + 4.6, 1.0, hz + 2.2), (3.2, 0.16, 2.6), 25, "Roof", 0.02)
    beam(g, (hx + 3.8, 0.0, hz + 4.6), (hx + 2.6, 3.4, hz + 2.2), 0.16, 0.22, "Charred")
    beam(g, (hx + 5.8, 0.0, hz + 3.9), (hx + 3.7, 2.6, hz + 0.8), 0.16, 0.22, "Charred")
    rubble_pile(hx + 4.4, hz + 3.4, 1.6, 22, 91, ("Roof", "Rubble", "Charred"))
    window(g, hx, 1.3, hz + 3.2, 1.5, 1.7)
    window(g, hx - 2.4, 1.3, hz + 3.2, 0.9, 1.4)
    box(g, hx + 2.3, -0.2, 2.4, hz + 3.25, 1.2, 0.12, "BeamDark")                  # door
    box(g, hx, 2.6, 2.75, hz + 3.6, 7.6, 0.9, "Beam")                             # porch roof ledge
    for k in range(9):                                                            # decorative band under the gable
        box(g, hx - 3.2 + k * 0.8, 4.3, 4.55, hz + 3.22, 0.35, 0.1, "PlanksLight")
    # lean-to scaffolding and fence between the house and the square
    for z in (-14.2, -19.5):
        box(g, -13.0, -0.2, 4.2, z, 0.3, 0.3, "Beam", 0.02)
    beam(g, (-13.0, 4.0, -14.2), (-13.0, 4.0, -19.5), 0.25, 0.3, "Beam")
    beam(g, (-16.5, 7.5, -12.5), (-9.5, 0.0, -13.2), 0.35, 0.35, "Beam")          # big diagonal brace
    beam(g, (-13.0, 0.3, -19.5), (-13.0, 3.9, -14.4), 0.2, 0.2, "Beam")
    beam(g, (-13.0, 0.3, -14.2), (-13.0, 3.9, -19.3), 0.2, 0.2, "Beam")
    fence(-15.5, -15.0, -8.8, -15.0, 1.0)
    # the tall building at the left screen edge (overhang at the top)
    bx0, bx1, bz0, bz1 = -21.0, -14.6, -12.0, 8.0
    box(g, (bx0 + bx1) / 2, -0.2, 9.0, (bz0 + bz1) / 2, bx1 - bx0, bz1 - bz0, "Planks")
    for z in range(int(bz0), int(bz1) + 1, 3):
        box(g, bx1 + 0.08, -0.2, 9.0, z, 0.3, 0.32, "Beam", 0.02)
    for y in (3.2, 6.2, 9.0):
        box(g, bx1 + 0.1, y - 0.18, y, (bz0 + bz1) / 2, 0.32, bz1 - bz0, "Beam")
    obox(g, (bx1 + 0.9, 9.25, (bz0 + bz1) / 2), (2.4, 0.18, bz1 - bz0 + 1), 0, "Roof")
    for z in range(int(bz0), int(bz1) + 1, 3):
        beam(g, (bx1, 7.2, z), (bx1 + 1.9, 9.1, z), 0.18, 0.22, "Beam")
    window(g, bx1 + 0.02, 4.0, -7.0, 1.2, 1.5, face_z=False)
    for (zz, y0, y1, w) in ((-1.5, 5.4, 7.6, 2.4), (4.5, 1.0, 2.6, 1.6)):   # burnt-through patches facing the square
        box(g, bx1 + 0.04, y0, y1, zz, 0.06, w, "Soot")
        rr = random.Random(int(zz * 10))
        for k in range(int(w / 0.22)):
            zk = zz - w / 2 + (k + 0.5) * w / int(w / 0.22)
            box(g, bx1 + 0.08, y1 - rr.uniform(0.1, 0.5), y1 + rr.uniform(0, 0.4), zk, 0.07, 0.2, "Charred")
            box(g, bx1 + 0.08, y0 - rr.uniform(0, 0.3), y0 + rr.uniform(0.1, 0.4), zk, 0.07, 0.2, "Charred")

def build_right():
    g = "CE_Buildings"; rnd = random.Random(12)
    # collapsed timber frames
    xs = (8.0, 11.2, 14.4, 17.6); zs = (-23.0, -28.0)
    tops = {}
    for i, x in enumerate(xs):
        for j, z in enumerate(zs):
            h = rnd.uniform(4.5, 7.2) if (i + j) % 3 else rnd.uniform(2.2, 3.4)    # some posts snapped off
            tops[(i, j)] = h
            box(g, x, -0.2, h, z, 0.32, 0.32, "BeamDark" if rnd.random() < 0.4 else "Beam", 0.02)
    for j, z in enumerate(zs):
        for i in range(3):
            y = min(tops[(i, j)], tops[(i + 1, j)]) - 0.3
            if y > 3.0:
                beam(g, (xs[i] - 0.2, y, z), (xs[i + 1] + 0.2, y + rnd.uniform(-0.4, 0.4), z), 0.24, 0.3, "Beam")
            beam(g, (xs[i], 2.8, z), (xs[i + 1], 2.8 + rnd.uniform(-0.2, 0.2), z), 0.22, 0.26, "Beam")
    for i, x in enumerate(xs):
        if min(tops[(i, 0)], tops[(i, 1)]) > 3.2:
            beam(g, (x, 3.0, zs[0] + 0.2), (x, 3.0, zs[1] - 0.2), 0.22, 0.26, "Beam")
    # partial deck boards on the first floor and broken wall panels
    for k in range(9):
        box(g, 9.0 + k * 0.85, 2.95, 3.08, -25.5 + rnd.uniform(-0.3, 0.3), 0.75, rnd.uniform(2.0, 4.6), "PlanksLight", 0.01)
    for k in range(5):
        box(g, 14.0 + k * 1.0, -0.2, rnd.uniform(1.2, 3.6), -28.4, 0.95, 0.12, "Planks")
    # fallen / leaning beams (the big diagonals in the painting)
    beam(g, (6.6, 0.0, -19.5), (9.8, 6.8, -24.5), 0.35, 0.4, "Beam")
    beam(g, (7.4, 0.0, -18.8), (10.2, 6.2, -24.0), 0.3, 0.35, "BeamDark")
    beam(g, (12.6, 0.0, -20.5), (16.2, 5.6, -26.0), 0.3, 0.35, "Beam")
    beam(g, (16.5, 0.2, -16.5), (21.5, 4.4, -26.5), 0.25, 0.9, "PlanksLight")    # long ramp plank (right edge)
    beam(g, (4.2, 0.0, -24.0), (8.0, 3.4, -23.2), 0.25, 0.3, "Charred")
    for k in range(14):                                                           # debris at the foot
        x = rnd.uniform(5.0, 18.0); z = rnd.uniform(-29.0, -20.5)
        beam(g, (x, 0.05, z), (x + rnd.uniform(-1.8, 1.8), rnd.uniform(0.1, 0.7), z + rnd.uniform(-1.5, 1.5)),
             rnd.uniform(0.15, 0.3), rnd.uniform(0.15, 0.3), rnd.choice(("Beam", "BeamDark", "Charred", "Planks")))
    for k in range(10):
        rock(g, rnd.uniform(4.0, 18.0), 0.0, rnd.uniform(-29.0, -21.0), rnd.uniform(0.3, 0.8), rnd.uniform(0.2, 0.5),
             rnd.uniform(0.3, 0.7), rnd.randint(0, 9999), "Rubble")
    # the building at the right screen edge (overhang top-right)
    bx0, bx1, bz0, bz1 = 15.6, 22.0, -8.0, 8.0
    box(g, (bx0 + bx1) / 2, -0.2, 8.4, (bz0 + bz1) / 2, bx1 - bx0, bz1 - bz0, "Planks")
    for z in range(int(bz0), int(bz1) + 1, 3):
        box(g, bx0 - 0.08, -0.2, 8.4, z, 0.3, 0.32, "Beam", 0.02)
    obox(g, (bx0 - 0.9, 8.6, (bz0 + bz1) / 2), (2.4, 0.18, bz1 - bz0 + 1), 0, "Roof")
    for z in range(int(bz0), int(bz1) + 1, 3):
        beam(g, (bx0, 6.6, z), (bx0 - 1.9, 8.5, z), 0.18, 0.22, "Beam")
    window(g, bx0 - 0.02, 3.6, -4.5, 1.2, 1.5, face_z=False, s=-1)
    for (zz, y0, y1, w) in ((1.5, 4.6, 7.2, 2.8), (-6.0, 0.8, 2.4, 1.4)):
        box(g, bx0 - 0.04, y0, y1, zz, 0.06, w, "Soot")
        rr = random.Random(int(zz * 10) + 7)
        for k in range(int(w / 0.22)):
            zk = zz - w / 2 + (k + 0.5) * w / int(w / 0.22)
            box(g, bx0 - 0.08, y1 - rr.uniform(0.1, 0.5), y1 + rr.uniform(0, 0.4), zk, 0.07, 0.2, "Charred")
            box(g, bx0 - 0.08, y0 - rr.uniform(0, 0.3), y0 + rr.uniform(0.1, 0.4), zk, 0.07, 0.2, "Charred")
    # a section of the overhang has crashed down onto the street
    obox(g, (bx0 - 1.6, 0.9, -1.0), (2.6, 0.18, 3.4), 0, "Roof", 0.02)
    beam(g, (bx0 - 0.2, 0.0, 0.8), (bx0 - 2.4, 1.9, -2.6), 0.18, 0.22, "Charred")
    # a brick house behind the frames (roof seen above them)
    gable_house(g, 19.0, -34.0, 8.0, 6.0, 5.5, 2.4, "Brick", ridge_z=False, broken=0.55, seed=5)
    window(g, 17.0, 2.2, -31.0, 1.1, 1.4); window(g, 21.0, 2.2, -31.0, 1.1, 1.4)

def build_props(arch_top):
    for (x, z, r) in ((-7.4, -16.6, 0), (-15.8, -9.0, 90)):
        bench(x, z, r)
    # the right bench is snapped in two
    obox("CE_Props", (8.6, 0.3, -16.9), (1.1, 0.08, 0.55), 12, "BenchRed", 0.01)
    obox("CE_Props", (9.9, 0.18, -16.6), (1.0, 0.08, 0.55), -25, "BenchRed", 0.01)
    beam("CE_Props", (8.2, 0.05, -17.3), (9.6, 0.75, -17.2), 0.06, 0.5, "BenchRed")
    # a collapsed house behind the well's left (big heap of beams and tiles)
    rubble_pile(-4.5, -33.0, 4.0, 60, 909)
    for k in range(8):
        rr = random.Random(950 + k); a = rr.uniform(0, 3.14)
        beam("CE_Props", (-4.5 + rr.uniform(-3, 3), 0.0, -33.0 + rr.uniform(-2, 2)),
             (-4.5 + math.cos(a) * 3.5, rr.uniform(1.5, 4.5), -33.0 + math.sin(a) * 2.5), 0.25, 0.3, rr.choice(("Charred", "BeamDark")))
    for k, (x, z, w) in enumerate(((-11.2, -15.3, 2.2), (-4.4, -17.4, 1.8), (11.4, -15.8, 2.2))):
        planter(x, z, w, 0.8, 0.6, 50 + k)
    # one planter smashed: broken brick sides, soil and flowers spilled across the paving
    rnd0 = random.Random(61)
    obox("CE_Props", (5.0, 0.3, -17.6), (1.8, 0.6, 0.16), 8, "Brick", 0.02)
    obox("CE_Props", (4.6, 0.15, -16.9), (0.9, 0.3, 0.16), 60, "Brick", 0.02)
    for k in range(14):
        rock("CE_Props", 5.0 + rnd0.uniform(-1.2, 1.4), 0.0, -16.8 + rnd0.uniform(-0.4, 0.9), rnd0.uniform(0.15, 0.35), 0.08,
             rnd0.uniform(0.15, 0.3), rnd0.randint(0, 9999), rnd0.choice(("Dirt", "Dirt", "Leaf", "FlowerRed", "Brick")))
    for k, (x, z) in enumerate(((-14.6, 2.6), (14.6, 2.6))):        # foreground corners
        planter(x, z, 2.6, 1.0, 0.75, 70 + k)
        fence(x - 1.5 * (1 if x < 0 else -1), 4.2, x + 1.6 * (1 if x < 0 else -1), 4.2, 1.2, 3, "BeamDark")
    for (x, z, s) in ((-15.0, -17.5, 1.0), (-13.8, -24.0, 1.1), (12.6, -25.2, 1.0), (17.0, -17.8, 1.1), (16.0, 5.4, 1.2), (-16.4, 5.0, 1.0)):
        barrel(x, z, s)
    for (x, z, h) in LAMPS:
        lamp(x, z, h)
    # the second lamp lies knocked over across the paving
    (bx, bz), (tx, tz) = FALLEN_LAMP
    cyl("CE_Props", bx, -0.05, bz, 0.2, 0.16, 0.5, "Iron", 8)
    beam("CE_Props", (bx, 0.35, bz), (tx, 0.25, tz), 0.12, 0.12, "Iron")
    obox("CE_Props", (tx - 0.2, 0.25, tz - 0.2), (0.45, 0.45, 0.45), 30, "Iron", 0.02)
    # rubble piles (stone, brick, roof tiles, burnt timber) around the square - never in the fight lane
    for k, (x, z, r, n) in enumerate(((-15.6, -12.8, 1.8, 26), (14.9, -12.4, 1.7, 24), (-7.8, -30.5, 2.2, 30),
                                      (6.2, -31.0, 2.0, 26), (-17.5, -28.5, 2.0, 24), (18.6, -21.0, 1.9, 24),
                                      (-3.6, -24.2, 1.3, 16), (-18.2, 0.5, 1.4, 16), (18.4, -3.0, 1.5, 18),
                                      (-21.0, -20.0, 2.2, 26), (22.5, -16.0, 2.0, 22))):
        rubble_pile(x, z, r, n, 200 + k)
    wrecked_cart(-16.4, -20.6)
    # displaced cobbles and dropped goods scattered at the plaza edges
    rnd = random.Random(77)
    for k in range(40):
        x = rnd.uniform(-22, 22); z = rnd.uniform(-34, 6)
        if abs(x) < 13.0 and z > -10.0:
            continue
        rock("CE_Props", x, 0.0, z, rnd.uniform(0.12, 0.3), rnd.uniform(0.06, 0.14), rnd.uniform(0.12, 0.3), rnd.randint(0, 9999), "Rubble")
    # crates and sacks behind the well (painting)
    rnd = random.Random(31)
    for k in range(6):
        x = rnd.uniform(-6, 5); z = rnd.uniform(-27, -22.5); s = rnd.uniform(0.6, 1.0)
        box("CE_Props", x, -0.1, s, z, s * 1.1, s, rnd.choice(("PlanksLight", "Beam")), 0.03, rnd.uniform(0, 40))

def build_far():
    g = "CE_Far"; rnd = random.Random(8)
    # mine headframe behind the arch
    hx, hz = 1.5, -40.0
    for sx in (-1, 1):
        for sz in (-1, 1):
            beam(g, (hx + sx * 2.2, 0, hz + sz * 2.2), (hx + sx * 1.0, 12.5, hz + sz * 1.0), 0.35, 0.35, "Beam")
    for y in (4.0, 8.0, 11.5):
        k = 2.2 - (2.2 - 1.0) * y / 12.5
        for sz in (-1, 1):
            beam(g, (hx - k, y, hz + sz * k), (hx + k, y, hz + sz * k), 0.22, 0.25, "Beam")
            beam(g, (hx + sz * k, y, hz - k), (hx + sz * k, y, hz + k), 0.22, 0.25, "Beam")
    box(g, hx, 9.2, 9.45, hz, 4.6, 3.2, "PlanksLight", 0.02)                       # platform
    for k in range(9):
        box(g, hx - 2.2 + k * 0.55, 9.45, 10.4, hz + 1.6, 0.06, 0.06, "Iron")        # railing
    box(g, hx, 10.3, 10.36, hz + 1.6, 4.4, 0.06, "Iron")
    beam(g, (hx - 4.5, 0, hz + 6), (hx - 0.5, 11.0, hz), 0.3, 0.3, "Beam")          # back-stay
    box(g, hx, 12.5, 13.1, hz, 2.6, 2.6, "Beam", 0.03)
    # masts / poles
    for (x, z, h) in ((-14.0, -38.0, 21.0), (17.0, -42.0, 17.0)):
        cyl(g, x, 0, z, 0.25, 0.14, h, "Beam", 8)
        box(g, x, h * 0.7, h * 0.7 + 0.18, z, 4.0, 0.16, "Beam")
        box(g, x, h * 0.85, h * 0.85 + 0.15, z, 2.6, 0.14, "Beam")
    # rows of houses behind the square
    for k in range(18):
        x = -38 + k * 4.6 + rnd.uniform(-1, 1); z = rnd.uniform(-58, -44)
        if abs(x - hx) < 4 and z > -46:
            continue
        w = rnd.uniform(4.0, 6.5); d = rnd.uniform(4.0, 6.0); h = rnd.uniform(3.5, 6.0)
        kind = rnd.random()
        if kind < 0.55:
            ruin(g, x, z, w, d, h, 500 + k)                                 # burnt-out shell
        else:
            gable_house(g, x, z, w, d, h, rnd.uniform(1.4, 2.4), "FarWall", "FarRoof", 0.3, rnd.random() < 0.4, "FarWall",
                        broken=rnd.choice((0.0, 0.0, 0.4, 0.6)), seed=600 + k)
    # trees
    for k in range(26):
        x = rnd.uniform(-60, 60); z = rnd.uniform(-75, -48)
        h = rnd.uniform(6, 11)
        cyl(g, x, 0, z, 0.35, 0.25, h * 0.4, "FarWall", 6)
        for j in range(3):
            rock(g, x + rnd.uniform(-1, 1), h * (0.5 + 0.17 * j), z + rnd.uniform(-1, 1), h * 0.28 * (1 - 0.2 * j),
                 h * 0.22, h * 0.28 * (1 - 0.2 * j), rnd.randint(0, 9999), "Tree", 2, 0.2)
    # mountains
    for (z, base, peaks, seed) in ((-170, -2, [(-160, 40, 90), (-60, 52, 80), (40, 46, 70), (130, 58, 90), (240, 40, 80)], 3),
                                   (-230, 0, [(-220, 60, 110), (-90, 70, 100), (60, 64, 120), (200, 72, 110)], 5)):
        ridge(g, z, -320, 320, base, peaks, seed, "Mountain")

def ridge(g, z, x0, x1, base, peaks, seed, m="Mountain", n=80):
    g = grp(g) if isinstance(g, str) else g
    rnd = random.Random(seed); bm = g.bm
    def prof(x):
        h = 3.0
        for (px, ph, pw) in peaks:
            d = abs(x - px) / pw
            if d < 1:
                h = max(h, ph * (1 - d * d) ** 1.2)
        return h
    cols = []
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        top = base + prof(x) * rnd.uniform(0.85, 1.1)
        mid = base + (top - base) * 0.55
        cols.append((bm.verts.new(G(x, base - 4, z + 6)), bm.verts.new(G(x, mid, z + rnd.uniform(-2, 3))), bm.verts.new(G(x, top, z - 4))))
    new = []
    for i in range(n):
        a, b = cols[i], cols[i + 1]
        for r in range(2):
            new.append(bm.faces.new((a[r], b[r], b[r + 1]))); new.append(bm.faces.new((a[r], b[r + 1], a[r + 1])))
    for f in new:
        f.normal_update()
        if f.normal.y > 0:
            f.normal_flip()
    _tag(g, new, m)

# ---------------- animated cards (drawn by Godot shaders) ----------------
def build_bunting(arch_top):
    """Lines of triangular pennants. UV.x = 0..1 across a flag, UV.y = flag id + v (v 0 = top edge)."""
    g = grp("CE_Bunting", "Cards"); fid = 0
    ends = ((-10.6, 5.6, -22.6, 0.9), (10.4, 5.9, -23.0, 0.9), (-6.5, 4.4, -13.4, 0.9),
            (4.4, 0.08, -15.6, 0.25))                     # this one snapped and hangs down to the paving
    for (ex, ey, ez, sag) in ends:
        A, B = Vector(arch_top), Vector((ex, ey, ez)); L = (B - A).length
        n = int(L / 0.62)
        for k in range(n):
            t0, t1 = (k + 0.15) / n, (k + 0.85) / n
            def pt(t):
                p = A.lerp(B, t); p.y -= sag * 4 * t * (1 - t)       # sag
                return p
            p0, p1 = pt(t0), pt(t1); tip = (p0 + p1) / 2; tip.y -= 0.5
            quad(g, [tuple(p0), tuple(tip), tuple(p1)], [(0, fid + 0.001), (0.5, fid + 0.999), (1, fid + 0.001)], "BuntingCard")
            fid += 1
        # the string
        for k in range(12):
            p0 = A.lerp(B, k / 12); p0.y -= sag * 4 * (k / 12) * (1 - k / 12)
            p1 = A.lerp(B, (k + 1) / 12); p1.y -= sag * 4 * ((k + 1) / 12) * (1 - (k + 1) / 12)
            beam("CE_Props", tuple(p0), tuple(p1), 0.02, 0.02, "BeamDark")

FIRES = [   # (x, y, z, size): flames (Burning variant); light power scales with size
    (-11.0, 7.0, -26.0, 2.2), (-11.0, 0.4, -22.9, 0.9), (-8.6, 4.5, -29.0, 1.6),
    (9.6, 3.2, -24.5, 2.0), (13.5, 0.2, -22.5, 1.4), (16.6, 3.2, -27.0, 2.4), (6.0, 0.2, -23.6, 1.2),
    (19.0, 8.0, -34.0, 2.6), (-2.5, 0.2, -25.0, 1.0), (3.5, 0.3, -26.5, 1.1),
    (-24.0, 6.0, -50.0, 3.0), (-12.0, 5.5, -48.0, 2.6), (10.0, 6.0, -52.0, 3.2), (26.0, 5.0, -47.0, 2.8),
    (-32.0, 5.0, -55.0, 3.0), (35.0, 6.0, -56.0, 3.0), (2.0, 7.0, -46.5, 2.0), (-17.5, 9.4, -2.0, 1.4),
    # burning rubble, the wrecked cart, the collapsed roof, the fallen lamp's oil
    (-15.6, 0.3, -12.8, 1.2), (14.9, 0.3, -12.4, 1.1), (-7.8, 0.5, -30.5, 1.6), (6.2, 0.4, -31.0, 1.5),
    (-16.4, 0.6, -20.6, 1.3), (-6.6, 0.4, -22.6, 1.0), (-7.2, 4.6, -24.0, 1.8), (11.4, 0.1, -21.9, 0.7),
    (-17.5, 0.4, -28.5, 1.4), (18.6, 0.3, -21.0, 1.3), (-21.0, 0.5, -20.0, 1.6), (22.5, 0.4, -16.0, 1.4),
    (19.0, 5.0, -31.5, 1.8), (-18.3, 6.5, -6.0, 1.2), (17.2, 5.5, -2.0, 1.2),
    (-40.0, 4.0, -46.0, 3.2), (-5.0, 5.0, -56.0, 3.4), (20.0, 4.5, -58.0, 3.0), (42.0, 4.0, -50.0, 3.0)]
SMOKES = [  # (x, y, z, width). The first SMOULDER ones also smoulder in the Day variant (thin grey smoke)
    (-11.0, 7.0, -27.0, 6.0), (13.5, 4.0, -26.0, 7.0), (-17.5, 1.0, -28.5, 4.5), (6.2, 1.0, -31.0, 4.5),
    (-22.0, 7.0, -52.0, 14.0), (12.0, 7.0, -54.0, 16.0), (32.0, 6.0, -55.0, 14.0), (-36.0, 6.0, -56.0, 12.0),
    (19.0, 7.0, -33.0, 8.0), (-7.8, 2.0, -30.5, 5.0), (-4.0, 6.0, -56.0, 15.0), (44.0, 5.0, -50.0, 13.0),
    (-44.0, 5.0, -47.0, 13.0), (2.0, 9.0, -46.0, 9.0), (-21.0, 1.0, -20.0, 4.5), (22.5, 1.0, -16.0, 4.5)]
SMOULDER = 4
HAZE = [  # (z, y top, x half-width) - layers of drifting smoke haze across the town (Burning)
    (-21.0, 4.0, 30.0), (-29.0, 7.0, 36.0), (-38.0, 10.0, 44.0), (-50.0, 16.0, 60.0), (-64.0, 24.0, 80.0)]

def build_fire_cards():
    """Crossed quads per flame / smoke column. UV.x across, UV.y = id + height (0 = base)."""
    for i, (x, y, z, s) in enumerate(FIRES):
        for a in (0.0, math.pi / 2):
            dx, dz = math.cos(a) * s * 0.6, math.sin(a) * s * 0.6
            quad("CE_Fire", [(x - dx, y, z - dz), (x + dx, y, z + dz), (x + dx, y + s * 1.9, z + dz), (x - dx, y + s * 1.9, z - dz)],
                 [(0, i + 0.001), (1, i + 0.001), (1, i + 0.999), (0, i + 0.999)], "FireCard")
    for i, (z, top, hw) in enumerate(HAZE):
        # facing the camera; UV.x runs in 20 m units across so the shader's noise keeps a steady scale
        quad("CE_Haze", [(-hw, -0.5, z), (hw, -0.5, z), (hw, top, z), (-hw, top, z)],
             [(0, i + 0.001), (2 * hw / 20.0, i + 0.001), (2 * hw / 20.0, i + 0.999), (0, i + 0.999)], "SmokeCard")
    for i, (x, y, z, s) in enumerate(SMOKES):
        for a in (0.3, 0.3 + math.pi / 2):
            dx, dz = math.cos(a) * s, math.sin(a) * s
            quad("CE_Smoke", [(x - dx, y, z - dz), (x + dx, y, z + dz), (x + dx * 1.8, y + s * 5.0, z + dz * 1.8), (x - dx * 1.8, y + s * 5.0, z - dz * 1.8)],
                 [(0, i + 0.001), (1, i + 0.001), (1, i + 0.999), (0, i + 0.999)], "SmokeCard")

def build_sky():
    g = grp("CE_Sky", "Cards")
    n = 96; y0, y1 = -40.0, 260.0
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        A0, A1 = 2 * math.pi * t0 - math.pi, 2 * math.pi * t1 - math.pi
        p0 = (SKY_R * math.sin(A0), 0, -10 - SKY_R * math.cos(A0)); p1 = (SKY_R * math.sin(A1), 0, -10 - SKY_R * math.cos(A1))
        quad(g, [(p0[0], y0, p0[2]), (p1[0], y0, p1[2]), (p1[0], y1, p1[2]), (p0[0], y1, p0[2])],
             [(t0, 0), (t1, 0), (t1, 1), (t0, 1)], "SkyCard")

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
    if V["sun_energy"] > 0:
        sd = bpy.data.lights.new("Sun", 'SUN'); sd.energy = V["sun_energy"]; sd.color = srgb(V["sun_color"]); sd.angle = math.radians(1.5)
        s = bpy.data.objects.new("Sun", sd); col("Lights").objects.link(s)
        d = Vector(V["sun_dir"]).normalized()
        s.rotation_mode = 'QUATERNION'; s.rotation_quaternion = Vector((d.x, -d.z, d.y)).to_track_quat('-Z', 'Y')
    for name, pos, aim, size, (power, colr) in (("Fill_Front", (0, 18, 30), (0, 2, -15), (70, 25), V["fill"]),
                                                ("Fill_Sky", (0, 60, -20), (0, 0, -20), (90, 90), V["top"])):
        ld = bpy.data.lights.new(name, 'AREA'); ld.shape = 'RECTANGLE'
        ld.size, ld.size_y = size; ld.energy = power; ld.color = srgb(colr)
        o = bpy.data.objects.new(name, ld); col("Lights").objects.link(o); o.location = G(*pos)
        o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = (G(*aim) - G(*pos)).normalized().to_track_quat('-Z', 'Y')
        o.visible_camera = False
    def point(name, p, wts, colr, rad=0.3):
        ld = bpy.data.lights.new(name, 'POINT'); ld.energy = wts; ld.color = srgb(colr); ld.shadow_soft_size = rad
        o = bpy.data.objects.new(name, ld); col("Lights").objects.link(o); o.location = G(*p); o.visible_camera = False
    if V["lamp_w"] > 0:
        for k, (x, z, h) in enumerate(LAMPS):
            point("Fill_Lamp%d" % k, (x, h - 0.15, z + 0.4), V["lamp_w"], "#ffbe78", 0.2)
    if V["window_w"] > 0:
        for k, (x, y, z, a) in enumerate(WINDOWS):
            point("Fill_Window%d" % k, (x, y, z + 0.6), V["window_w"] * a, V["window_color"], 0.5)
    if V["fire_w"] > 0:
        for k, (x, y, z, s) in enumerate(FIRES):
            point("Fill_Fire%d" % k, (x, y + s * 0.6, z + 0.3), V["fire_w"] * s * s, "#ff6a24", s * 0.5)

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
        cd.clip_start = 0.1; cd.clip_end = 900
        o = bpy.data.objects.new(name, cd); col("Cameras").objects.link(o)
        o.location = G(*pos); o.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.scene.camera = bpy.data.objects["CAM_mid"]

def build_all():
    reset(); COLS.clear(); MATS.clear(); GR.clear(); WINDOWS.clear()
    build_materials()
    build_floor()
    top = build_well_and_arch()
    build_left(); build_right(); build_props(top); build_far()
    build_bunting(top); build_fire_cards(); build_sky(); build_preview()
    objs = {name: g.finish() for name, g in list(GR.items())}
    for n in ("CE_Sky", "CE_Window", "CE_Bunting", "CE_Fire", "CE_Smoke", "CE_Haze"):
        objs[n].visible_shadow = False
    for n in ("CE_Bunting", "CE_Fire", "CE_Smoke", "CE_Haze"):
        objs[n].hide_render = True            # animated in Godot (fires light the bake through point lights)
    build_lights(); build_cameras(); setup_render()
    tris = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs.values()}
    return {"variant": VARIANT, "objects": list(objs), "tris": tris, "total_tris": sum(tris.values())}

if __name__ == "__main__":
    BUILD_INFO = build_all()
