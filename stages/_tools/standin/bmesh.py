import math
from mathutils import Vector, Matrix
from types import SimpleNamespace
class LoopUV:
    def __init__(self): self.uv = (0.0, 0.0)
class BMLoop:
    def __init__(self, v): self.vert = v; self.data = {}
    def __getitem__(self, k): return self.data.setdefault(k, LoopUV())
class BMVert:
    def __init__(self, co):
        self.co = Vector(co); self.link_faces = []; self.link_edges = []; self.is_valid = True; self.index = -1
class BMFace:
    def __init__(self, verts):
        self.verts = list(verts); self.loops = [BMLoop(v) for v in verts]; self.material_index = 0
        self.layers = {}; self.is_valid = True; self.index = -1
    def __getitem__(self, k): return self.layers.get(k, 0)
    def __setitem__(self, k, v): self.layers[k] = v
    @property
    def normal(self):
        n = [0.0, 0.0, 0.0]; vs = self.verts
        for i in range(len(vs)):
            a, b = vs[i].co, vs[(i + 1) % len(vs)].co
            n[0] += (a.y - b.y) * (a.z + b.z); n[1] += (a.z - b.z) * (a.x + b.x); n[2] += (a.x - b.x) * (a.y + b.y)
        return Vector(n).normalized()
    def normal_update(self): pass
    def normal_flip(self):
        self.verts.reverse(); self.loops.reverse()
    def calc_center_median(self):
        c = Vector((0, 0, 0))
        for v in self.verts: c = c + v.co
        return c / len(self.verts)
class Layers:
    def __init__(self): self.n = 0
    def new(self, name=""): self.n += 1; return ("layer", name, self.n)
class VertSeq(list):
    def __init__(self): super().__init__(); self.layers = SimpleNamespace(int=Layers())
    def new(self, co):
        v = BMVert(co); self.append(v); return v
    def ensure_lookup_table(self): pass
class FaceSeq(list):
    def __init__(self, bm): super().__init__(); self.bm = bm; self.layers = SimpleNamespace(int=Layers()); self.keys = set()
    def new(self, verts):
        verts = list(verts)
        if len(set(id(v) for v in verts)) != len(verts):
            raise ValueError("faces.new(): the same BMVert used multiple times")
        if len(verts) < 3:
            raise ValueError("faces.new(): need at least 3 verts")
        k = frozenset(id(v) for v in verts)
        if k in self.keys:
            raise ValueError("faces.new(): face already exists")
        self.keys.add(k)
        f = BMFace(verts); self.append(f)
        for v in verts: v.link_faces.append(f)
        return f
    def ensure_lookup_table(self): pass
class BMesh:
    def __init__(self):
        self.verts = VertSeq(); self.faces = FaceSeq(self); self.edges = []
        self.loops = SimpleNamespace(layers=SimpleNamespace(uv=Layers()))
    def normal_update(self): pass
    def to_mesh(self, me): pass
    def free(self): pass
    def from_mesh(self, me): pass
def new(): return BMesh()
class _Ops:
    def _apply(self, bm, pts, faces, matrix):
        M = matrix if matrix is not None else Matrix.Identity(4)
        vs = [bm.verts.new(M @ Vector(p)) for p in pts]
        for f in faces:
            bm.faces.new([vs[i] for i in f])
        return {"verts": vs}
    def create_cube(self, bm, size=1.0, matrix=None, **kw):
        h = size / 2
        pts = [(x * h, y * h, z * h) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
        faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        return self._apply(bm, pts, faces, matrix)
    def create_cone(self, bm, cap_ends=True, cap_tris=False, segments=8, radius1=1.0, radius2=1.0, depth=1.0, matrix=None, **kw):
        n = segments; pts = []
        for r, z in ((radius1, -depth / 2), (radius2, depth / 2)):
            for i in range(n):
                a = 2 * math.pi * i / n; pts.append((r * math.cos(a), r * math.sin(a), z))
        faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        if cap_ends:
            faces += [tuple(range(n))[::-1], tuple(range(n, 2 * n))]
        return self._apply(bm, pts, faces, matrix)
    def create_icosphere(self, bm, subdivisions=1, radius=1.0, matrix=None, **kw):
        t = (1 + 5 ** 0.5) / 2
        pts = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
        L = math.sqrt(1 + t * t); pts = [(a / L * radius, b / L * radius, c / L * radius) for a, b, c in pts]
        faces = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
                 (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
        return self._apply(bm, pts, faces, matrix)
    def create_uvsphere(self, bm, u_segments=8, v_segments=6, radius=1.0, matrix=None, **kw):
        pts = [(0, 0, -radius)]
        for j in range(1, v_segments):
            ph = -math.pi / 2 + math.pi * j / v_segments
            for i in range(u_segments):
                a = 2 * math.pi * i / u_segments
                pts.append((radius * math.cos(ph) * math.cos(a), radius * math.cos(ph) * math.sin(a), radius * math.sin(ph)))
        pts.append((0, 0, radius)); top = len(pts) - 1; U = u_segments
        faces = [(0, 1 + (i + 1) % U, 1 + i) for i in range(U)]
        for j in range(v_segments - 2):
            for i in range(U):
                a = 1 + j * U + i; b = 1 + j * U + (i + 1) % U
                faces.append((a, b, b + U, a + U))
        base = 1 + (v_segments - 2) * U
        faces += [(base + i, base + (i + 1) % U, top) for i in range(U)]
        return self._apply(bm, pts, faces, matrix)
    def bevel(self, bm, **kw): return {"faces": []}
    def recalc_face_normals(self, bm, faces=None, **kw): pass
    def delete(self, bm, geom=(), context='VERTS', **kw):
        gs = set(id(g) for g in geom)
        if context == 'FACES':
            bm.faces[:] = [f for f in bm.faces if id(f) not in gs]
        else:
            bm.faces[:] = [f for f in bm.faces if not any(id(v) in gs for v in f.verts)]
            bm.verts[:] = [v for v in bm.verts if id(v) not in gs]
    def bisect_plane(self, bm, **kw): return {}
ops = _Ops()
