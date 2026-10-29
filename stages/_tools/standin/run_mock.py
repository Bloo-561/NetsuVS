# usage: python3 run_mock.py BUILD_SCRIPT VARIANT OUT.glb NAMES_JSON PREVIEW_JSON
import sys, os, json, math, struct, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from unittest.mock import MagicMock
from types import SimpleNamespace
import bpy, bmesh
build, variant, out = sys.argv[1], sys.argv[2], sys.argv[3]
NAMES = json.loads(open(sys.argv[4]).read()); PREV = json.loads(open(sys.argv[5]).read())
ns = {"__name__": "lib", "VARIANT": variant}
t0 = time.time()
exec(compile(open(build, encoding="utf-8").read(), build, "exec"), ns)
ns["NB"].ramp = lambda self, fac, stops: MagicMock()
CAP = {}
def finish(self):
    for m in self.mats:
        assert m in ns["MATS"], "material not defined: " + m
    CAP[self.name] = (self.bm, list(self.mats), self.uv, self.custom)
    o = MagicMock(); o.data.polygons = [SimpleNamespace(vertices=[0] * len(f.verts)) for f in self.bm.faces]
    return o
ns["Group"].finish = finish
info = ns["build_all"]()
print({k: v for k, v in info.items() if k not in ("objects", "tris")}, "%.1fs" % (time.time() - t0))
print({g: sum(len(f.verts) - 2 for f in c[0].faces) for g, c in CAP.items()})
missing = sorted({m for (_, mats, _, _) in CAP.values() for m in mats if m not in PREV})
if missing: print("no preview colour for:", missing)

def srgb2lin(c): return [((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c]
def hexc(h): h = h.lstrip('#'); return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
L = [0.35, 0.85, 0.4]; ln = math.sqrt(sum(a * a for a in L)); L = [a / ln for a in L]
gl = {"asset": {"version": "2.0"}, "scenes": [{"nodes": []}], "scene": 0, "nodes": [], "meshes": [], "materials": [],
      "accessors": [], "bufferViews": [], "buffers": [], "extensionsUsed": ["KHR_materials_unlit"]}
blob = bytearray()
def add(data, comp, typ, cnt, mn=None, mx=None):
    off = len(blob); blob.extend(data)
    while len(blob) % 4: blob.append(0)
    gl["bufferViews"].append({"buffer": 0, "byteOffset": off, "byteLength": len(data)})
    a = {"bufferView": len(gl["bufferViews"]) - 1, "componentType": comp, "count": cnt, "type": typ}
    if mn is not None: a["min"] = mn; a["max"] = mx
    gl["accessors"].append(a); return len(gl["accessors"]) - 1
MATIDX = {}
def material(key, col):
    if key not in MATIDX:
        gl["materials"].append({"name": key, "doubleSided": True, "extensions": {"KHR_materials_unlit": {}},
                                "pbrMetallicRoughness": {"baseColorFactor": col + [1.0], "metallicFactor": 0, "roughnessFactor": 1}})
        MATIDX[key] = len(gl["materials"]) - 1
    return MATIDX[key]
for g, (bm, mats, uvk, cust) in CAP.items():
    if g not in NAMES: continue
    prims = {}
    for f in bm.faces:
        vs = [v.co for v in f.verts]
        n = f.normal; ng = [n.x, n.z, -n.y]
        mname = mats[f.material_index]
        base = srgb2lin(hexc(PREV.get(mname, "#ff00ff")))
        sh = round((0.5 + 0.5 * abs(sum(a * b for a, b in zip(ng, L)))) * 4) / 4
        key = "%s_%.2f" % (mname, sh)
        P, N, T, col = prims.setdefault(key, ([], [], [], [c * sh for c in base]))
        uvs = [l[uvk].uv if f[cust] else (0.0, 0.0) for l in f.loops]
        for i in range(1, len(vs) - 1):
            for k in (0, i, i + 1):
                v = vs[k]; P += [v.x, v.z, -v.y]; N += ng; T += [uvs[k][0], 1.0 - uvs[k][1]]
    plist = []
    for key, (P, N, T, col) in prims.items():
        cnt = len(P) // 3
        xs, ys, zs = P[0::3], P[1::3], P[2::3]
        pa = add(struct.pack("<%df" % len(P), *P), 5126, "VEC3", cnt, [min(xs), min(ys), min(zs)], [max(xs), max(ys), max(zs)])
        na = add(struct.pack("<%df" % len(N), *N), 5126, "VEC3", cnt)
        ta = add(struct.pack("<%df" % len(T), *T), 5126, "VEC2", cnt)
        plist.append({"attributes": {"POSITION": pa, "NORMAL": na, "TEXCOORD_0": ta}, "material": material(key, col)})
    gl["meshes"].append({"name": NAMES[g], "primitives": plist})
    gl["nodes"].append({"name": NAMES[g], "mesh": len(gl["meshes"]) - 1}); gl["scenes"][0]["nodes"].append(len(gl["nodes"]) - 1)
gl["buffers"].append({"byteLength": len(blob)})
js = json.dumps(gl).encode(); js += b" " * ((4 - len(js) % 4) % 4)
glb = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(blob)) + struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(blob), 0x004E4942) + bytes(blob)
open(out, "wb").write(glb)
print("wrote", out, len(glb) // 1024, "KB")
