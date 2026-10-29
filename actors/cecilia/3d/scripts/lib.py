# Cecilia 3D - shared helpers. Run inside Blender.
# Conventions: 1 unit = 1 m, Z up, she faces -Y, her LEFT is +X, feet at z=0.
import bpy, bmesh, math
from mathutils import Vector, Matrix

ROOT = r"E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs\actors\cecilia\3d"
COLL = "Cecilia"
LIGHT_DIR = Vector((-0.45, -0.65, 0.62)).normalized()   # fixed key light (world space): front, her right, above


# ---------------------------------------------------------------- collections / objects
def coll(name=COLL, parent=None):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


def remove(name):
    o = bpy.data.objects.get(name)
    if o:
        me = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if isinstance(me, bpy.types.Mesh) and me.users == 0:
            bpy.data.meshes.remove(me)
        elif isinstance(me, bpy.types.Curve) and me.users == 0:
            bpy.data.curves.remove(me)


def clear_collection(name):
    c = bpy.data.collections.get(name)
    if c:
        for o in list(c.objects):
            remove(o.name)


def mesh_obj(name, verts, faces, collection=COLL, smooth=True, mats=None, face_mats=None, recalc=True):
    remove(name)
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.validate()
    me.update()
    o = bpy.data.objects.new(name, me)
    coll(collection).objects.link(o)
    if recalc:
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me); bm.free()
    if smooth:
        me.shade_smooth()
    for m in (mats or []):
        me.materials.append(m)
    if face_mats:
        for p, i in zip(me.polygons, face_mats):
            p.material_index = i
    return o


def flip(o):
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(o.data); bm.free()


def subsurf(o, levels=1):
    m = o.modifiers.new("Subsurf", 'SUBSURF')
    m.levels = levels; m.render_levels = levels
    return m


# ---------------------------------------------------------------- lofting
def loft(name, rings, closed=True, cap0=False, cap1=False, **kw):
    """rings: list of lists of points (same count). Quads between rings, optional fan caps."""
    n = len(rings[0])
    verts, faces = [], []
    for r in rings:
        verts.extend([Vector(p) for p in r])
    m = n if closed else n - 1
    for i in range(len(rings) - 1):
        for j in range(m):
            j2 = (j + 1) % n
            faces.append((i * n + j, i * n + j2, (i + 1) * n + j2, (i + 1) * n + j))
    if cap0 and closed:
        verts.append(sum(verts[0:n], Vector()) / n); ci = len(verts) - 1
        for j in range(n):
            faces.append((ci, (j + 1) % n, j))
    if cap1 and closed:
        b = (len(rings) - 1) * n
        verts.append(sum(verts[b:b + n], Vector()) / n); ci = len(verts) - 1
        for j in range(n):
            faces.append((ci, b + j, b + (j + 1) % n))
    return mesh_obj(name, verts, faces, **kw)


def ring_z(cx, cy, z, rx, ry, n=24, fn=None):
    """Horizontal ellipse ring. Angle 0 = +X, 90 = +Y (back), -90 = -Y (front). fn(a, p)->p optional."""
    pts = []
    for j in range(n):
        a = 2 * math.pi * j / n
        p = Vector((cx + rx * math.cos(a), cy + ry * math.sin(a), z))
        if fn: p = fn(a, p)
        pts.append(p)
    return pts


def frames(points, up=Vector((0, 0, 1))):
    """Parallel-transport frames (T, N, B) along a polyline."""
    pts = [Vector(p) for p in points]
    T = []
    for i in range(len(pts)):
        a = pts[max(i - 1, 0)]; b = pts[min(i + 1, len(pts) - 1)]
        T.append((b - a).normalized())
    N0 = up - up.dot(T[0]) * T[0]
    if N0.length < 1e-5:
        N0 = Vector((1, 0, 0)) - Vector((1, 0, 0)).dot(T[0]) * T[0]
    N = [N0.normalized()]
    for i in range(1, len(pts)):
        n = N[-1] - N[-1].dot(T[i]) * T[i]
        N.append(n.normalized())
    B = [t.cross(n) for t, n in zip(T, N)]
    return pts, T, N, B


def tube(name, points, radii, n=16, up=Vector((0, 0, 1)), cap0=True, cap1=True, normals=None, **kw):
    """Tube along a path. radii: list of (r_n, r_b) per point (or float). normals: optional per-point N override."""
    pts, T, N, B = frames(points, up)
    if normals:
        N = []; B = []
        for t, nv in zip(T, normals):
            nv = Vector(nv); nv = (nv - nv.dot(t) * t).normalized(); N.append(nv); B.append(t.cross(nv))
    rings = []
    for i, p in enumerate(pts):
        r = radii[i]
        rn, rb = (r, r) if isinstance(r, (int, float)) else r
        rings.append([p + N[i] * rn * math.cos(2 * math.pi * j / n) + B[i] * rb * math.sin(2 * math.pi * j / n)
                      for j in range(n)])
    return loft(name, rings, cap0=cap0, cap1=cap1, **kw)


def strip(name, points, widths, normals, thick=0.0, n_across=2, **kw):
    """Flat ribbon along a path; width along B (= T x normal). thick>0 makes it a thin closed box tube."""
    pts, T, N, B = frames(points)
    rings = []
    for i, p in enumerate(pts):
        nv = Vector(normals[i]); nv = (nv - nv.dot(T[i]) * T[i]).normalized(); b = T[i].cross(nv)
        w = widths[i]
        if thick > 0:
            h = thick / 2
            rings.append([p + b * w / 2 + nv * h, p - b * w / 2 + nv * h, p - b * w / 2 - nv * h, p + b * w / 2 - nv * h])
        else:
            rings.append([p + b * w * (k / (n_across - 1) - 0.5) for k in range(n_across)])
    return loft(name, rings, closed=thick > 0, **kw)


def bezier_pts(ctrl, steps=16):
    """Catmull-Rom through control points -> smooth polyline."""
    c = [Vector(p) for p in ctrl]
    c = [c[0] + (c[0] - c[1])] + c + [c[-1] + (c[-1] - c[-2])]
    out = []
    for i in range(1, len(c) - 2):
        p0, p1, p2, p3 = c[i - 1], c[i], c[i + 1], c[i + 2]
        for s in range(steps):
            t = s / steps
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t))
    out.append(c[-2])
    return out


def ellipsoid(name, center, radii, n=16, rings=10, **kw):
    cx, cy, cz = center; rx, ry, rz = radii
    rs = []
    for i in range(1, rings):
        th = math.pi * i / rings
        rs.append([Vector((cx + rx * math.sin(th) * math.cos(2 * math.pi * j / n),
                           cy + ry * math.sin(th) * math.sin(2 * math.pi * j / n),
                           cz + rz * math.cos(th))) for j in range(n)])
    return loft(name, rs, cap0=True, cap1=True, **kw)


def box(name, center, size, rot=(0, 0, 0), **kw):
    sx, sy, sz = [s / 2 for s in size]
    v = [Vector((x, y, z)) for x in (-sx, sx) for y in (-sy, sy) for z in (-sz, sz)]
    R = Matrix.Rotation(rot[2], 3, 'Z') @ Matrix.Rotation(rot[1], 3, 'Y') @ Matrix.Rotation(rot[0], 3, 'X')
    v = [Vector(center) + R @ p for p in v]
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    kw.setdefault('smooth', False)
    return mesh_obj(name, v, f, **kw)


# ---------------------------------------------------------------- toon materials
def hexc(h, a=1.0):
    h = h.lstrip('#')
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    return (*lin, a)


def _sock(node, name, kind='inputs', typ=None):
    for s in getattr(node, kind):
        if s.name == name and (typ is None or s.type == typ):
            return s
    raise KeyError(name)


def _mix(nt, fac, a, b):
    m = nt.nodes.new('ShaderNodeMix'); m.data_type = 'RGBA'
    if isinstance(fac, float): m.inputs[0].default_value = fac
    else: nt.links.new(fac, m.inputs[0])
    for sock, val in ((_sock(m, 'A', typ='RGBA'), a), (_sock(m, 'B', typ='RGBA'), b)):
        if isinstance(val, tuple): sock.default_value = val
        else: nt.links.new(val, sock)
    return _sock(m, 'Result', 'outputs', 'RGBA')


def toon(name, base, shadow=None, thresh=0.12, base_fn=None, cull=False):
    """Flat 2-tone material: emission(base or shadow by N.L vs fixed light). base_fn(nt)->socket for custom base color.
    shadow: hex or None (auto = base * cool tint)."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(em.outputs[0], out.inputs['Surface'])
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    dot = nt.nodes.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'
    nt.links.new(geo.outputs['Normal'], dot.inputs[0]); dot.inputs[1].default_value = LIGHT_DIR
    gt = nt.nodes.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = thresh
    nt.links.new(_sock(dot, 'Value', 'outputs'), gt.inputs[0])
    if base_fn:
        b = base_fn(nt)
    else:
        rgb = nt.nodes.new('ShaderNodeRGB'); rgb.outputs[0].default_value = hexc(base); b = rgb.outputs[0]
    if shadow:
        srgb = nt.nodes.new('ShaderNodeRGB'); srgb.outputs[0].default_value = hexc(shadow)
        if base_fn:  # shadow = base * (shadow/base-ish tint)
            s = _mix(nt, 1.0, b, srgb.outputs[0]); s.node.blend_type = 'MULTIPLY'
        else:
            s = srgb.outputs[0]
    else:
        tint = nt.nodes.new('ShaderNodeRGB'); tint.outputs[0].default_value = hexc('#c2b0c8')
        s = _mix(nt, 1.0, b, tint.outputs[0]); s.node.blend_type = 'MULTIPLY'
    final = _mix(nt, gt.outputs[0], s, b)
    nt.links.new(final, em.inputs['Color'])
    m.use_backface_culling = cull
    m.diffuse_color = hexc(base) if base else (0.5, 0.5, 0.5, 1)
    return m


def outline_mat():
    name = "MAT_Outline"
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = hexc('#1e1418')
    nt.links.new(em.outputs[0], out.inputs['Surface'])
    m.use_backface_culling = True
    m.diffuse_color = hexc('#1e1418')
    return m


def add_outline(o, thick=0.0025):
    """Inverted-hull outline: solidify shell with flipped normals using the outline material (backface culled)."""
    if o.type != 'MESH': return
    for md in list(o.modifiers):
        if md.name == "Outline": o.modifiers.remove(md)
    ol = outline_mat()
    mats = o.data.materials
    # strip existing outline slots, then add one outline slot per base slot so index i -> i+k is always outline
    while len(mats) and mats[len(mats) - 1] and mats[len(mats) - 1].name == ol.name:
        mats.pop(index=len(mats) - 1)
    k = max(len(mats), 1)
    if len(mats) == 0: mats.append(None)
    for _ in range(k): mats.append(ol)
    idx = k
    md = o.modifiers.new("Outline", 'SOLIDIFY')
    md.thickness = thick; md.offset = 1.0
    md.use_flip_normals = True; md.use_rim = False
    md.material_offset = idx; md.material_offset_rim = idx
    # all original faces must use slots below idx; solidify offsets shell faces by idx
    return md


def set_mat(o, m, slot=0):
    me = o.data
    while len(me.materials) <= slot: me.materials.append(None)
    me.materials[slot] = m
