# Depths of the Old Schoolhouse - 3D stage build script (Blender 5.x, runs in --background)
#
#   blender --background --factory-startup --python run_sd.py -- STEPS=build,bake,pv,export
#
# A floating stone platform above a sea of clouds under a starry, ringed sky: ornate tiled floor,
# a stepped dais with a spiked gazebo (teleport circle), four green-glowing lantern pillars,
# a spiked balustrade with little lantern obelisks, and floating ruins all around.
#
# Layout is written in GODOT coordinates (x right, y up, +z toward the camera) and converted
# to Blender (Z-up) by G():  Godot (x, y, z) -> Blender (x, -z, y).  1 unit = 1 m.
# Baked groups (atlases): SD_Platform, SD_Pillars, SD_Islands, SD_Floor (light map only)
# Card groups (Godot shaders, not baked): SD_Sky, SD_Glow, SD_Circle - they still EMIT in the bake,
# so the green lanterns, the circle and the sky light the stone.
import bpy, bmesh, math, random
from mathutils import Vector, Matrix

ROOT = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\stages\schoolhouse_depths"
TEXD = ROOT + r"\textures"

# ---------------- layout (Godot space, metres) ----------------
CENTER_Z = -8.0                    # platform centre (x = 0)
PLAT_R = 34.0                      # floor radius (the void starts here)
BAL_R = 33.0                       # balustrade ring radius
FLOOR_X = 36.0                     # floor quad: x +-36, z -44..+28
FLOOR_BACK, FLOOR_FRONT = CENTER_Z - 36.0, CENTER_Z + 36.0
CARPET = (-12.0, 12.0, -17.0, -3.0)          # x0, x1, z0, z1 of the ornate inlay (24 x 14 m)
DAIS_Z = -28.0                     # gazebo / teleport circle centre
DAIS_STEPS = [(10.0, 0.22), (9.3, 0.44), (8.6, 0.66), (7.9, 0.88), (7.2, 1.10)]   # (octagon radius, top y)
DAIS_TOP = 1.10
GAZ_R, GAZ_N, GAZ_H = 3.6, 8, 12.0
PILLARS = [(-12.5, -13.0, 20.0, 1.6), (12.5, -13.0, 20.0, 1.6),     # outer pair (frame the screen edges)
           (-7.5, -21.0, 16.0, 1.3), (7.5, -21.0, 16.0, 1.3)]      # inner pair (flank the dais)
LANE_X, LANE_Z = 12.5, -9.0
SKY_R = 200.0
GLOW_COLOR, GLOW_STRENGTH = "#3dff94", 7.0
GLOW_LIGHT_W = 140.0               # point light in front of each lantern face
CIRCLE_COLOR = "#5ff0ff"
# lighting
WORLD_COLOR, WORLD_STRENGTH = "#0e2650", 0.9
KEY_COLOR, KEY_W = "#86e2ff", 42000          # starlight / ring glow from behind
FILL_COLOR, FILL_W = "#a9c6ff", 11000        # soft front fill
TOP_COLOR, TOP_W = "#6aa6ff", 14000

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

def build_materials():
    stone_material("Stone", "#747a7e", "#a3a8aa", 0.07)          # weathered grey stone (less teal grime)
    stone_material("StoneLight", "#959a9c", "#c0c4c4", 0.04)
    stone_material("StoneDark", "#40474d", "#5f666b", 0.12)
    stone_material("StoneCarved", "#7d8488", "#aab0b2", 0.05, carved=True)
    stone_material("Rock", "#4a5262", "#6f7888", 0.05, rough=0.8)
    b = NB("Metal")       # dark verdigris bronze (gazebo, spikes) - baked without metalness, stylised sheen via roughness
    n = b.noise(b.pos, 2.5, 4, 0.5)
    b.link(b.ramp(n.outputs["Fac"], [(0.3, "#46565a"), (0.7, "#6f8584")]), b.bsdf.inputs["Base Color"])
    b.bsdf.inputs["Roughness"].default_value = 0.35
    # floor: tiles everywhere + the ornate inlay rectangle (Tex UV = metres (x, -z))
    b = NB("FloorStone")
    mp = b.n("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.25, 0.25, 1); b.link(b.uv, mp.inputs[0])
    tiles = b.image("floor_tiles.png", mp.outputs[0])
    x0, x1, z0, z1 = CARPET
    mp2 = b.n("ShaderNodeMapping")
    mp2.inputs["Location"].default_value = (-x0 / (x1 - x0), 1 + z0 / (z1 - z0) + 0.0, 0)
    mp2.inputs["Scale"].default_value = (1 / (x1 - x0), 1 / (z1 - z0), 1)
    # Tex UV.y = -z; carpet v (Blender, 0 = bottom) = 1 - (z - z0) / (z1 - z0) = 1 + (UV.y + z0) / (z1 - z0)
    mp2.inputs["Location"].default_value = (-x0 / (x1 - x0), 1 + z0 / (z1 - z0), 0)
    b.link(b.uv, mp2.inputs[0])
    carpet = b.image("floor_carpet.png", mp2.outputs[0], 'CLIP')
    c = b.mixc(tiles.outputs["Color"], carpet.outputs["Color"], carpet.outputs["Alpha"])
    b.link(c, b.bsdf.inputs["Base Color"]); b.bsdf.inputs["Roughness"].default_value = 0.25
    # cards
    emissive_card("GlowCard", "glyph.png", GLOW_COLOR, GLOW_STRENGTH, 0.3)
    emissive_card("CircleCard", "circle.png", CIRCLE_COLOR, 4.0, 0.05)
    b = NB("SkyCard")     # gradient stand-in for the Godot sky (lights the platform in the bake)
    sep = b.n("ShaderNodeSeparateXYZ"); b.link(b.uv, sep.inputs[0])
    r = b.ramp(sep.outputs[1], [(0.0, "#7fc8e8"), (0.38, "#bdeeff"), (0.43, "#4aa8dc"), (0.55, "#1a4f92"), (1.0, "#0a1a40")])
    em = b.n("ShaderNodeEmission"); em.inputs["Strength"].default_value = 1.1
    b.link(r, em.inputs["Color"]); b.link(em.outputs[0], b.out.inputs[0])
    b = NB("Stand_P1"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#2d6cdf"), 1)
    b = NB("Stand_P2"); b.bsdf.inputs["Base Color"].default_value = (*srgb("#e0463a"), 1)

# ======================================================================
#  geometry
# ======================================================================
GLOW_LIGHTS = []     # (godot position, watts) of the green spill lights

def build_floor():
    g = grp("SD_Floor")
    quad(g, [(-FLOOR_X, 0, FLOOR_FRONT), (FLOOR_X, 0, FLOOR_FRONT), (FLOOR_X, 0, FLOOR_BACK), (-FLOOR_X, 0, FLOOR_BACK)],
         [(-FLOOR_X, -FLOOR_FRONT), (FLOOR_X, -FLOOR_FRONT), (FLOOR_X, -FLOOR_BACK), (-FLOOR_X, -FLOOR_BACK)], "FloorStone")

def glow_panel(cx, y0, y1, cz, face, half_w, out):
    """Glowing glyph panel on one face of a square column. face: 0 +z, 1 +x, 2 -z, 3 -x."""
    nx, nz = ((0, 1), (1, 0), (0, -1), (-1, 0))[face]
    tx, tz = nz, -nx                                  # tangent (left -> right seen from outside)
    px, pz = cx + nx * out, cz + nz * out
    a = (px - tx * half_w, y0, pz - tz * half_w); b = (px + tx * half_w, y0, pz + tz * half_w)
    c = (px + tx * half_w, y1, pz + tz * half_w); d = (px - tx * half_w, y1, pz - tz * half_w)
    quad("SD_Glow", [a, b, c, d], [(0, 0), (1, 0), (1, 1), (0, 1)], "GlowCard")
    return (px + nx * 0.45, (y0 + y1) / 2, pz + nz * 0.45)

def lantern(g, x, z, y0, y1, w, light_w):
    """A lantern section: dark core, corner posts and four glowing panels."""
    box(g, x, y0, y1, z, w * 0.92, w * 0.92, "StoneDark")
    for sx in (-1, 1):
        for sz in (-1, 1):
            box(g, x + sx * w * 0.46, y0, y1, z + sz * w * 0.46, w * 0.18, w * 0.18, "StoneCarved", 0.02)
    for f in range(4):
        p = glow_panel(x, y0 + 0.08 * (y1 - y0), y1 - 0.08 * (y1 - y0), z, f, w * 0.36, w * 0.472)
        GLOW_LIGHTS.append((p, light_w))

def moulding(g, x, z, y, h, w, m="StoneLight", points=False):
    box(g, x, y, y + h, z, w, w, m, 0.04)
    if points:      # little pyramids on the corners (painting)
        for sx in (-1, 1):
            for sz in (-1, 1):
                cyl(g, x + sx * w * 0.42, y + h, z + sz * w * 0.42, w * 0.12, 0.0, w * 0.35, "StoneLight", 4, 45)

def lantern_pillar(x, z, H, w):
    g = "SD_Pillars"
    f = lambda t: H * t
    box(g, x, -0.3, f(0.05), z, w * 1.7, w * 1.7, "Stone", 0.05)                 # plinth
    moulding(g, x, z, f(0.05), f(0.025), w * 1.45)
    box(g, x, f(0.075), f(0.30), z, w * 1.18, w * 1.18, "StoneCarved", 0.03)     # carved lower block
    moulding(g, x, z, f(0.30), f(0.025), w * 1.32)
    lantern(g, x, z, f(0.325), f(0.52), w * 1.02, GLOW_LIGHT_W)                  # lower lantern
    moulding(g, x, z, f(0.52), f(0.03), w * 1.38, points=True)
    box(g, x, f(0.55), f(0.66), z, w * 0.82, w * 0.82, "StoneCarved", 0.03)      # shaft
    moulding(g, x, z, f(0.66), f(0.025), w * 1.18)
    lantern(g, x, z, f(0.685), f(0.83), w * 0.98, GLOW_LIGHT_W)                  # upper lantern
    moulding(g, x, z, f(0.83), f(0.03), w * 1.36, points=True)
    # pagoda top: shrinking tiers with flared caps, then a spire
    y = f(0.86)
    for k, (s, h) in enumerate(((0.95, 0.035), (0.75, 0.03), (0.55, 0.025))):
        box(g, x, y, y + f(h), z, w * s, w * s, "Stone", 0.02)
        cyl(g, x, y + f(h), z, w * s * 0.85, w * s * 0.35, f(0.012), "StoneLight", 4, 45)
        y += f(h) + f(0.012)
    cyl(g, x, y, z, w * 0.22, 0.0, f(0.12), "Metal", 4, 45)

def obelisk(x, z, s, base_y=0.0, light_w=60.0):
    g = "SD_Pillars"
    box(g, x, base_y - 0.2, base_y + 0.35 * s, z, 0.9 * s, 0.9 * s, "Stone", 0.03)
    box(g, x, base_y + 0.35 * s, base_y + 1.3 * s, z, 0.55 * s, 0.55 * s, "StoneCarved", 0.02)
    y0 = base_y + 1.3 * s
    box(g, x, y0, y0 + 0.65 * s, z, 0.5 * s, 0.5 * s, "StoneDark")
    for f in range(4):
        p = glow_panel(x, y0 + 0.05 * s, y0 + 0.6 * s, z, f, 0.2 * s, 0.262 * s)
    GLOW_LIGHTS.append(((x, y0 + 0.33 * s, z), light_w))
    box(g, x, y0 + 0.65 * s, y0 + 0.75 * s, z, 0.7 * s, 0.7 * s, "StoneLight", 0.02)
    cyl(g, x, y0 + 0.75 * s, z, 0.38 * s, 0.0, 0.7 * s, "StoneLight", 4, 45)

def build_dais():
    g = "SD_Platform"
    y_prev = -0.3
    for r, top in DAIS_STEPS:
        octa_prism(g, 0, DAIS_Z, r, y_prev if y_prev < 0 else -0.3, top, "StoneLight" if r < 8 else "Stone")
    # a low border of small spiked posts around the top (painting)
    for k in range(16):
        th = 2 * math.pi * k / 16
        x, z = 6.6 * math.sin(th), DAIS_Z - 6.6 * math.cos(th)
        box(g, x, DAIS_TOP, DAIS_TOP + 0.45, z, 0.4, 0.4, "Stone", 0.02)
        cyl(g, x, DAIS_TOP + 0.45, z, 0.22, 0.0, 0.7 + 0.4 * (k % 2), "Metal", 4, 45 + math.degrees(th))
    # gazebo base ring
    octa_prism(g, 0, DAIS_Z, 4.4, DAIS_TOP - 0.05, DAIS_TOP + 0.25, "StoneCarved")
    # teleport circle (Godot draws the rotating runes)
    n = 64; r0, r1 = 1.5, 3.1; y = DAIS_TOP + 0.255
    for i in range(n):
        a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
        p = lambda a, r: (r * math.sin(a), y, DAIS_Z - r * math.cos(a))
        quad("SD_Circle", [p(a0, r1), p(a1, r1), p(a1, r0), p(a0, r0)],
             [(i / n * 4, 1), ((i + 1) / n * 4, 1), ((i + 1) / n * 4, 0), (i / n * 4, 0)], "CircleCard")

def build_gazebo():
    g = "SD_Pillars"; y0 = DAIS_TOP + 0.25
    rings = (6.0, 10.2)
    for k in range(GAZ_N):
        th = 2 * math.pi * (k + 0.5) / GAZ_N
        x, z = GAZ_R * math.sin(th), DAIS_Z - GAZ_R * math.cos(th)
        box(g, x, y0, y0 + 0.9, z, 0.75, 0.75, "StoneCarved", 0.03)
        cyl(g, x, y0 + 0.9, z, 0.36, 0.2, 0.5, "Stone", 8)
        # slender stacked shaft with bulbs
        y = y0 + 1.4
        for seg, (h, rb) in enumerate(((2.2, 0.28), (1.9, 0.26), (1.9, 0.25), (1.8, 0.24), (1.6, 0.22), (1.3, 0.2))):
            octa_prism(g, x, z, 0.2, y, y + h, "Metal")
            cyl(g, x, y + h - 0.1, z, rb * 1.05, rb * 1.05, 0.25, "Metal", 8)
            cyl(g, x, y + h + 0.15, z, rb * 1.05, rb * 0.5, 0.25, "Metal", 8)
            y += h + 0.4
        cyl(g, x, y, z, 0.3, 0.0, 2.4, "Metal", 6)                              # spike finial
        for ry in rings:                                                        # outward spikes at the rings
            cone_dir(g, (x + 0.1 * math.sin(th), y0 + ry, z - 0.1 * math.cos(th)), (math.sin(th), 0, -math.cos(th)),
                     0.18, 1.5 if k % 2 == 0 else 1.0, "Metal", 6)
    for ry in rings:       # the two horizontal rings: octagonal bands (two stacked thin boxes per side)
        for k in range(GAZ_N):
            a0, a1 = 2 * math.pi * (k + 0.5) / GAZ_N, 2 * math.pi * (k + 1.5) / GAZ_N
            am = (a0 + a1) / 2
            L = 2 * (GAZ_R + 0.2) * math.sin(math.pi / GAZ_N)
            x, z = (GAZ_R + 0.2) * math.cos(math.pi / GAZ_N) * math.sin(am), DAIS_Z - (GAZ_R + 0.2) * math.cos(math.pi / GAZ_N) * math.cos(am)
            for dy, hh, th_ in ((-0.12, 0.12, 0.28), (0.12, 0.12, 0.22)):
                obox(g, (x, y0 + ry + dy, z), (L + 0.1, hh, th_), -math.degrees(am), "Metal", 0.02)
    # small pyramids around the gazebo foot (painting)
    for k in range(8):
        th = 2 * math.pi * k / 8
        x, z = 5.2 * math.sin(th), DAIS_Z - 5.2 * math.cos(th)
        cyl(g, x, DAIS_TOP, z, 0.45, 0.0, 1.3, "Stone", 4, 45)

def build_balustrade():
    g = "SD_Platform"; rnd = random.Random(4)
    n = int(2 * math.pi * BAL_R / 3.2)
    for k in range(n):
        th = 2 * math.pi * k / n - math.pi
        x, _, z = polar(BAL_R, th)
        rot = -math.degrees(th)
        # rail section to the next post (low wall + rounded cap)
        thm = th + math.pi / n
        xm, _, zm = polar(BAL_R, thm); L = 2 * BAL_R * math.sin(math.pi / n)
        obox(g, (xm, 0.35, zm), (L, 0.7, 0.55), rot, "Stone", 0.04)
        obox(g, (xm, 0.82, zm), (L, 0.24, 0.42), rot, "StoneLight", 0.08)
        # post with a spike finial; every third one taller
        big = k % 3 == 0
        box(g, x, 0.0, 1.15 if big else 1.0, z, 0.75, 0.75, "Stone", 0.04, rot)
        box(g, x, 1.15 if big else 1.0, 1.3 if big else 1.12, z, 0.9, 0.9, "StoneLight", 0.03, rot)
        cyl(g, x, 1.3 if big else 1.12, z, 0.38, 0.0, 1.4 if big else 0.8, "StoneLight", 4, 45 + rot)
    # the ledge outside the balustrade (so the platform has a visible edge)
    m = 96
    for k in range(m):
        a0, a1 = 2 * math.pi * k / m - math.pi, 2 * math.pi * (k + 1) / m - math.pi
        P = lambda r, a, y: polar(r, a, y)
        quad(g, [P(BAL_R + 0.3, a0, 0.02), P(PLAT_R, a0, 0.02), P(PLAT_R, a1, 0.02), P(BAL_R + 0.3, a1, 0.02)],
             [(0, 0), (1, 0), (1, 1), (0, 1)], "StoneDark")
    # lantern obelisks standing on the balustrade around the back half, and two beside the dais steps
    for k in range(-5, 6):
        th = math.radians(k * 18.0)
        if abs(k) == 0:
            continue
        x, _, z = polar(BAL_R - 0.2, th)
        obelisk(x, z, 1.25, 0.0, 70.0)
    for sx in (-1, 1):
        obelisk(sx * 4.6, -16.4, 1.45, 0.0, 90.0)

ISLANDS = [  # (angle deg, radius, height, size) - floating ruins around the platform
    (-62, 88, 22, 6.0), (-40, 120, 34, 8.0), (-24, 95, 17, 4.5), (-12, 150, 40, 10.0), (8, 135, 21, 5.5),
    (20, 100, 30, 7.0), (36, 125, 18, 5.0), (52, 92, 26, 6.5), (70, 115, 38, 9.0), (-82, 120, 30, 7.5),
    (95, 110, 23, 6.0), (-100, 105, 24, 6.0)]     # every rock tip stays above y = 0 (the mirror cut)

def island(cx, cy, cz, s, seed):
    g = "SD_Islands"; rnd = random.Random(seed); bm = grp(g).bm
    # top slab (octagon) and an upside-down jagged rock cone under it
    octa_prism(g, cx, cz, s, cy - 0.35 * s, cy, "Stone")
    segs = 7; rings = 5; ring_v = []
    for k in range(rings):
        t = k / rings
        y = cy - 0.35 * s - t * 2.4 * s
        rad = s * 1.02 * (1 - t) ** 0.9 * rnd.uniform(0.85, 1.1)
        a0 = rnd.random() * 6.28; ring = []
        for i in range(segs):
            a = a0 + 6.283 * i / segs + rnd.uniform(-0.25, 0.25); rr = rad * rnd.uniform(0.75, 1.12)
            ring.append(bm.verts.new(G(cx + rr * math.cos(a), y + rnd.uniform(-0.1, 0.1) * s, cz + rr * math.sin(a))))
        ring_v.append(ring)
    tip = bm.verts.new(G(cx + rnd.uniform(-0.3, 0.3) * s, cy - 0.35 * s - 2.9 * s, cz))
    new = []
    for k in range(rings - 1):
        A, B = ring_v[k], ring_v[k + 1]
        for i in range(segs):
            j = (i + 1) % segs
            new.append(bm.faces.new((A[i], A[j], B[j]))); new.append(bm.faces.new((A[i], B[j], B[i])))
    T = ring_v[-1]
    for i in range(segs):
        new.append(bm.faces.new((T[i], T[(i + 1) % segs], tip)))
    bmesh.ops.recalc_face_normals(bm, faces=new)
    _tag(grp(g), new, "Rock")
    # ruined towers and walls on top
    for t in range(rnd.randint(1, 3)):
        tx = cx + rnd.uniform(-0.45, 0.45) * s; tz = cz + rnd.uniform(-0.45, 0.45) * s
        tw = s * rnd.uniform(0.22, 0.34); th = s * rnd.uniform(0.7, 1.8)
        box(g, tx, cy, cy + th, tz, tw, tw, "Stone", 0.02, rnd.uniform(0, 90))
        box(g, tx, cy + th, cy + th + tw * 0.3, tz, tw * 1.3, tw * 1.3, "StoneLight", 0.02)
        cyl(g, tx, cy + th + tw * 0.3, tz, tw * 0.6, 0.0, tw * rnd.uniform(1.5, 2.6), "StoneLight", 4, 45)
    if rnd.random() < 0.7:
        a = rnd.uniform(0, 180)
        box(g, cx, cy, cy + s * 0.4, cz + rnd.uniform(-0.3, 0.3) * s, s * 1.2, s * 0.15, "Stone", 0.02, a)

def build_islands():
    for k, (ang, r, h, s) in enumerate(ISLANDS):
        x, _, z = polar(r, math.radians(ang))
        island(x, h, z, s, 300 + k)
    bpy.context.scene["sd_islands"] = [list(polar(r, math.radians(a), h)) for (a, r, h, s) in ISLANDS]

def build_sky():
    """Sky cylinder around the platform. Godot draws a view-direction sky on it (stars, rings, cloud sea);
    in the bake it emits a gradient so the stone picks up the cool sky light from below and above."""
    g = grp("SD_Sky", "Cards")
    n = 96; y0, y1 = -150.0, 220.0
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        A0, A1 = 2 * math.pi * t0 - math.pi, 2 * math.pi * t1 - math.pi
        p0 = polar(SKY_R, A0); p1 = polar(SKY_R, A1)
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
    bg.inputs["Color"].default_value = (*srgb(WORLD_COLOR), 1); bg.inputs["Strength"].default_value = WORLD_STRENGTH
    for name, pos, aim, size, power, colr in (
            ("Key_Back", (0, 70, -110), (0, 0, -20), (160, 60), KEY_W, KEY_COLOR),
            ("Fill_Front", (0, 24, 38), (0, 2, -14), (80, 30), FILL_W, FILL_COLOR),
            ("Top", (10, 90, -10), (0, 0, -15), (80, 80), TOP_W, TOP_COLOR)):
        ld = bpy.data.lights.new(name, 'AREA'); ld.shape = 'RECTANGLE'
        ld.size, ld.size_y = size; ld.energy = power; ld.color = srgb(colr)
        o = bpy.data.objects.new(name, ld); col("Lights").objects.link(o)
        o.location = G(*pos)
        d = (G(*aim) - G(*pos)).normalized()
        o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d.to_track_quat('-Z', 'Y')
        o.visible_camera = False
    for k, (p, wts) in enumerate(GLOW_LIGHTS):
        ld = bpy.data.lights.new("Glow_%d" % k, 'POINT'); ld.energy = wts; ld.color = srgb(GLOW_COLOR)
        ld.shadow_soft_size = 0.3
        o = bpy.data.objects.new("Glow_%d" % k, ld); col("Lights").objects.link(o); o.location = G(*p)
        o.visible_camera = False
    ld = bpy.data.lights.new("Circle_Light", 'POINT'); ld.energy = 900; ld.color = srgb(CIRCLE_COLOR)
    ld.shadow_soft_size = 1.5
    o = bpy.data.objects.new("Circle_Light", ld); col("Lights").objects.link(o); o.location = G(0, DAIS_TOP + 1.2, DAIS_Z)
    o.visible_camera = False

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
        cd.clip_start = 0.1; cd.clip_end = 800
        o = bpy.data.objects.new(name, cd); col("Cameras").objects.link(o)
        o.location = G(*pos); o.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.scene.camera = bpy.data.objects["CAM_mid"]

def build_all():
    reset(); COLS.clear(); MATS.clear(); GR.clear(); GLOW_LIGHTS.clear()
    build_materials()
    build_floor(); build_dais(); build_gazebo(); build_balustrade()
    for (x, z, H, w) in PILLARS:
        lantern_pillar(x, z, H, w)
    build_islands(); build_sky(); build_preview()
    objs = {name: g.finish() for name, g in list(GR.items())}
    for n in ("SD_Sky", "SD_Glow", "SD_Circle"):
        objs[n].visible_shadow = False
    build_lights(); build_cameras(); setup_render()
    tris = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs.values()}
    return {"objects": list(objs), "tris": tris, "total_tris": sum(tris.values()), "glow_lights": len(GLOW_LIGHTS)}

if __name__ == "__main__":
    BUILD_INFO = build_all()
