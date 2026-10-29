import math
class Vector:
    def __init__(self, v=(0.0, 0.0, 0.0)):
        self.v = [float(a) for a in v]
    def _g(i):
        return property(lambda s: s.v[i], lambda s, val: s.v.__setitem__(i, float(val)))
    x, y, z = _g(0), _g(1), _g(2)
    def __len__(self): return len(self.v)
    def __getitem__(self, i): return self.v[i]
    def __setitem__(self, i, val): self.v[i] = float(val)
    def __iter__(self): return iter(self.v)
    def __repr__(self): return "Vector(%s)" % self.v
    def _o(self, o): return o.v if isinstance(o, Vector) else list(o)
    def __add__(self, o): return Vector([a + b for a, b in zip(self.v, self._o(o))])
    __radd__ = __add__
    def __sub__(self, o): return Vector([a - b for a, b in zip(self.v, self._o(o))])
    def __rsub__(self, o): return Vector([b - a for a, b in zip(self.v, self._o(o))])
    def __mul__(self, o):
        if isinstance(o, (int, float)): return Vector([a * o for a in self.v])
        return Vector([a * b for a, b in zip(self.v, self._o(o))])
    __rmul__ = __mul__
    def __truediv__(self, o): return Vector([a / o for a in self.v])
    def __neg__(self): return Vector([-a for a in self.v])
    def dot(self, o): return sum(a * b for a, b in zip(self.v, self._o(o)))
    def cross(self, o):
        a, b = self.v, self._o(o)
        return Vector((a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]))
    @property
    def length(self): return math.sqrt(sum(a * a for a in self.v))
    def normalized(self):
        L = self.length
        return Vector([a / L for a in self.v]) if L > 1e-12 else Vector(self.v)
    def normalize(self):
        self.v = self.normalized().v
    def copy(self): return Vector(self.v)
    def lerp(self, o, t): return self + (Vector(self._o(o)) - self) * t
    def to_tuple(self): return tuple(self.v)
    def to_track_quat(self, track='Z', up='Y'):
        z = self.normalized()
        if track.startswith('-'): z = -z
        ref = Vector((0, 0, 1)) if abs(z.z) < 0.999 else Vector((0, 1, 0))
        x = ref.cross(z).normalized(); y = z.cross(x)
        return Quaternion(Matrix([[x.x, y.x, z.x], [x.y, y.y, z.y], [x.z, y.z, z.z]]))

class Quaternion:
    def __init__(self, m=None): self.m = m
    def to_matrix(self): return self.m

class Matrix:
    def __init__(self, rows): self.rows = [list(map(float, r)) for r in rows]
    @staticmethod
    def Identity(n): return Matrix([[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)])
    @staticmethod
    def Translation(v):
        m = Matrix.Identity(4)
        for i in range(3): m.rows[i][3] = v[i]
        return m
    @staticmethod
    def Diagonal(v):
        n = len(v); m = Matrix.Identity(n)
        for i in range(n): m.rows[i][i] = v[i]
        return m
    @staticmethod
    def Rotation(a, size, axis):
        c, s = math.cos(a), math.sin(a)
        if axis == 'X': r = [[1, 0, 0], [0, c, -s], [0, s, c]]
        elif axis == 'Y': r = [[c, 0, s], [0, 1, 0], [-s, 0, c]]
        elif axis == 'Z': r = [[c, -s, 0], [s, c, 0], [0, 0, 1]]
        else: raise ValueError(axis)
        m = Matrix(r)
        return m.to_4x4() if size == 4 else m
    def to_4x4(self):
        if len(self.rows) == 4: return Matrix(self.rows)
        m = Matrix.Identity(4)
        for i in range(3):
            for j in range(3): m.rows[i][j] = self.rows[i][j]
        return m
    def copy(self): return Matrix(self.rows)
    def __matmul__(self, o):
        n = len(self.rows)
        if isinstance(o, Matrix):
            assert len(o.rows) == n, "matrix size mismatch"
            return Matrix([[sum(self.rows[i][k] * o.rows[k][j] for k in range(n)) for j in range(n)] for i in range(n)])
        v = list(o)
        if n == 4 and len(v) == 3:
            w = v + [1.0]
            return Vector([sum(self.rows[i][k] * w[k] for k in range(4)) for i in range(3)])
        assert len(v) == n, "matrix/vector size mismatch"
        return Vector([sum(self.rows[i][k] * v[k] for k in range(n)) for i in range(n)])
