"""Milestone 7: skinning (run in Blender, after rig_build.py).

Every weight is computed from the rest-pose geometry and the bones'
positions (nothing painted), so a rebuild reproduces it exactly:
  * chains (arms, legs, fingers, thumb, neckerchief tails, ahoge): each vertex
    is projected onto the chain's centre line; it belongs to the bone whose
    segment it falls on, blended linearly with the next bone within BLEND of a
    joint (smoothstep), and with the chain's parent bone before the first one;
  * torso garments: pelvis / spine / chest / neck by height, with the
    clavicle and the upper arm taking the shoulders;
  * skirt and petticoat: the two nearest skirt chains by angle round the
    waist, root / tip bone by height, the pelvis at the waistband;
  * hair: the head above the ears, the nearest hair chains below;
  * rigid parts follow one bone as children of it (no armature modifier):
    face, ears, skull filler, headband, clips (the face's material reads
    object coordinates, which must not slide), the sword's parts, belts and
    buckles, the hanger strap, the brooch.
The Armature modifier goes after the cloth thickness (built at rest, its
copies carry the weights) and before the normal blur, the hair-normal
transfer and the outline hull, which must follow the pose.
Run: import runpy; runpy.run_path(r"<3d_v2>\\scripts\\rig_weights.py")["run"]()
"""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RIG = "CEC_rig"
TORSO_C = (0.0, 0.030)
HAIR_C = (0.0, 0.020)
PRE_DEFORM = ("thickness", "solid")    # modifiers that stay before the Armature (built at rest)
PRESERVE_VOLUME = ("arm_R", "arm_L", "hand_R", "hand_L", "leg_R", "leg_L", "body", "jacket", "neck")

RIGID = {
    "face": "head", "ear_R": "head", "ear_L": "head", "skull": "head", "headband": "head", "clip_R": "head",
    "clip_L": "head", "GG_FaceNormalCentre": "head", "GG_HairNormalProxy": "head",
    "saya": "sheath", "saya_mouth": "sheath", "saya_tip": "sheath",
    "blade": "sword", "tsuka": "hilt", "tsuba": "hilt", "kashira": "hilt",
    "hanger_strap": "pelvis", "belt_A": "pelvis", "belt_B": "pelvis", "buckle_A": "pelvis", "buckle_B": "pelvis",
    "brooch": "chest", "bow_R": "foot.R", "bow_L": "foot.L",
}


def ramp(t, a, b):
    """0 at a, 1 at b (smoothstep), works both ways round"""
    x = np.clip((np.asarray(t, float) - a) / (b - a), 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def _bones(rig):
    """rest head / tail (armature space = world: the rig sits at the origin)"""
    return {b.name: (np.array(b.head_local), np.array(b.tail_local)) for b in rig.data.bones}


def chain(verts, pts, names, blend, parent=None, parent_blend=0.0, end_blend=None):
    """weights {bone: array} for vertices along a polyline chain
    pts[0..n] (bone k spans pts[k] -> pts[k+1])"""
    pts = np.asarray(pts, float)
    n = len(names)
    seg = pts[1:] - pts[:-1]
    L = np.linalg.norm(seg, axis=1)
    cum = np.r_[0.0, np.cumsum(L)]
    best_d = np.full(len(verts), np.inf)
    s = np.zeros(len(verts))
    for k in range(n):
        d = seg[k] / max(L[k], 1e-12)
        t = (verts - pts[k]) @ d
        tc = np.clip(t, 0.0, L[k])
        q = pts[k] + tc[:, None] * d[None, :]
        dist = np.linalg.norm(verts - q, axis=1)
        if k == 0:
            tc = np.where(t < 0, t, tc)                         # before the chain: negative s
        if k == n - 1:
            tc = np.where(t > L[k], t, tc)
        upd = dist < best_d - 1e-12
        best_d[upd] = dist[upd]
        s[upd] = cum[k] + tc[upd]
    W = {nm: np.zeros(len(verts)) for nm in names}
    # bone k owns [cum[k], cum[k+1]]; joints blend over +-blend
    own = np.zeros((n, len(verts)))
    for k in range(n):
        lo = 1.0 if k == 0 else ramp(s, cum[k] - blend, cum[k] + blend)
        hi = 1.0 if k == n - 1 else 1.0 - ramp(s, cum[k + 1] - blend, cum[k + 1] + blend)
        own[k] = lo * hi
    if parent is not None:
        wp = 1.0 - ramp(s, -parent_blend, parent_blend)
        own *= (1.0 - wp)[None, :]
        W[parent] = wp
    for k, nm in enumerate(names):
        W[nm] = W.get(nm, 0) + own[k]
    return W


def merge(*parts):
    out = {}
    for P_ in parts:
        for k, v in P_.items():
            out[k] = out.get(k, 0) + v
    return out


def scale(W, f):
    return {k: v * f for k, v in W.items()}


def torso(z, x, side_x=None, shoulders=True):
    """pelvis / spine / chest by height; clavicle + upper arm at the shoulders"""
    pel = 1.0 - ramp(z, 0.950, 1.010)
    chest = ramp(z, 1.070, 1.130)
    spine = np.clip(1.0 - pel - chest, 0.0, 1.0)
    W = dict(pelvis=pel, spine=spine, chest=chest)
    if shoulders:
        ax = np.abs(x)
        up = ramp(ax, 0.112, 0.138) * ramp(z, 1.150, 1.200)
        clav = ramp(ax, 0.060, 0.112) * ramp(z, 1.140, 1.210) * (1.0 - up)
        rest = 1.0 - up - clav
        W = scale(W, rest)
        for side, m in (("R", x < 0), ("L", x >= 0)):
            W["clavicle." + side] = np.where(m, clav, 0.0)
            W["upper_arm." + side] = np.where(m, up, 0.0)
    return W


def neck_top(z, W, start=1.262, end=1.292, head=None):
    """move part of the chest's weight to the neck (and the head) near the top"""
    nk = ramp(z, start, end)
    W = dict(W)
    c = W.get("chest", 0) * nk
    W["chest"] = W.get("chest", 0) - c
    W["neck"] = W.get("neck", 0) + c
    if head is not None:
        h = W["neck"] * ramp(z, head[0], head[1])
        W["neck"] = W["neck"] - h
        W["head"] = W.get("head", 0) + h
    return W


def around(verts, chains, centre, zcuts, z_blend, top=None):
    """skirt / hair style: chains = [(azimuth deg, [bone_01, bone_02]), ...]
    sorted by azimuth; angular linear blend between the two neighbours,
    bone_01 / bone_02 split at zcuts[0] (+-z_blend)"""
    ang = np.degrees(np.arctan2(verts[:, 0] - centre[0], -(verts[:, 1] - centre[1])))
    az = np.array([c[0] for c in chains], float)
    order = np.argsort(az)
    az = az[order]
    ch = [chains[i][1] for i in order]
    n = len(az)
    W = {}
    z = verts[:, 2]
    low = 1.0 - ramp(z, zcuts[0] - z_blend, zcuts[0] + z_blend)      # 1 below the split -> bone_02
    for i in range(n):
        j = (i + 1) % n
        a0, a1 = az[i], az[j] + (360.0 if j == 0 else 0.0)
        a = np.where(ang < a0, ang + 360.0, ang)
        inside = (a >= a0) & (a < a1)
        f = np.clip((a - a0) / (a1 - a0), 0.0, 1.0)
        for k, wk in ((i, 1.0 - f), (j, f)):
            w = np.where(inside, wk, 0.0)
            b1, b2 = ch[k]
            W[b1] = W.get(b1, 0) + w * (1.0 - low)
            W[b2] = W.get(b2, 0) + w * low
    if top is not None:
        bone, z0, z1 = top
        t = ramp(z, z0, z1)
        W = scale(W, 1.0 - t)
        W[bone] = W.get(bone, 0) + t
    return W


def world(ob):
    return np.array([ob.matrix_world @ v.co for v in ob.data.vertices])


# ----------------------------------------------------------------------------- per object
def weights_for(name, V, B):
    x, y, z = V[:, 0], V[:, 1], V[:, 2]
    if name in ("body", "jacket"):
        return torso(z, x)
    if name in ("collar", "shirt_collar", "tie"):
        return neck_top(z, torso(z, x, shoulders=False), 1.262, 1.300)
    if name == "neck":
        return neck_top(z, dict(chest=np.ones(len(V))), 1.258, 1.282, head=(1.296, 1.322))
    if name.startswith("arm_") or name.startswith("hand_"):
        sd = name[-1]
        pts = [B["clavicle." + sd][1], B["upper_arm." + sd][1], B["forearm." + sd][1], B["hand." + sd][1]]
        W = chain(V, pts, ["upper_arm." + sd, "forearm." + sd, "hand." + sd], 0.018,
                  parent="clavicle." + sd, parent_blend=0.012)
        if name.startswith("hand_"):
            W = hand_fingers(V, B, sd, W)
        return W
    if name.startswith("leg_"):
        sd = name[-1]
        pts = [B["thigh." + sd][0], B["shin." + sd][0], B["foot." + sd][0], B["foot." + sd][1]]
        return chain(V, pts, ["thigh." + sd, "shin." + sd, "foot." + sd], 0.030, parent="pelvis", parent_blend=0.035)
    if name.startswith("shoe_"):
        sd = name[-1]
        toe = ramp(-y, 0.030, 0.058)
        shin = 0.5 * ramp(z, 0.100, 0.125)
        foot = 1.0 - toe - shin
        return {"foot." + sd: np.clip(foot, 0, 1), "toe." + sd: toe, "shin." + sd: shin}
    if name in ("skirt", "lace"):
        chains = []
        for b in B:
            if b.startswith("skirt_") and "_01" in b:
                h, t = B[b]
                az = math.degrees(math.atan2(h[0] - TORSO_C[0], -(h[1] - TORSO_C[1])))
                chains.append((az, [b, b.replace("_01", "_02")]))
        zmid = float(np.mean([B[c[1][1]][0][2] for c in chains]))
        return around(V, chains, TORSO_C, (zmid,), 0.035, top=("pelvis", 0.950, 0.990))
    if name == "hair":
        chains = []
        for b in B:
            if b.startswith("hair_") and "_01" in b:
                h, t = B[b]
                az = math.degrees(math.atan2(h[0] - HAIR_C[0], -(h[1] - HAIR_C[1])))
                chains.append((az, [b, b.replace("_01", "_02")]))
        zmid = float(np.mean([B[c[1][1]][0][2] for c in chains]))
        return around(V, chains, HAIR_C, (zmid,), 0.025, top=("head", 1.400, 1.445))
    if name == "bangs":
        bw = (1.0 - ramp(z, 1.390, 1.440)) * (1.0 - ramp(np.abs(x), 0.030, 0.055))
        return {"bangs": bw, "head": 1.0 - bw}
    if name == "ahoge":
        pts = [B["ahoge_01"][0], B["ahoge_01"][1], B["ahoge_02"][1]]
        return chain(V, pts, ["ahoge_01", "ahoge_02"], 0.008, parent="head", parent_blend=0.004)
    if name == "neckerchief":
        knot = ramp(z, 1.178, 1.192)
        band = knot * ramp(np.abs(x), 0.030, 0.042)
        W = {"chest": band, "neckerchief": knot - band}
        for sd, m in (("R", x < 0), ("L", x >= 0)):
            pts = [B["scarf_tail_01." + sd][0], B["scarf_tail_01." + sd][1], B["scarf_tail_02." + sd][1]]
            T = chain(V, pts, ["scarf_tail_01." + sd, "scarf_tail_02." + sd], 0.020)
            for k, v in T.items():
                W[k] = W.get(k, 0) + np.where(m, v, 0.0) * (1.0 - knot)
        return W
    return None


def hand_fingers(V, B, sd, W):
    """fingers and thumb: their own chains, by connected component"""
    names = ("index", "middle", "ring", "pinky", "thumb")
    ob = bpy.data.objects["hand_" + sd]
    comp = _components(ob)
    out = {k: v.copy() for k, v in W.items()}
    counts = np.bincount(comp)
    palm = int(np.argmax(counts))
    for c in np.unique(comp):
        m = comp == c
        if c == palm:
            continue
        pv = V[m]
        cen = pv.mean(0)
        best, dbest = None, 1e9
        for nm in names:
            pts = [B["%s_01.%s" % (nm, sd)][0], B["%s_01.%s" % (nm, sd)][1], B["%s_02.%s" % (nm, sd)][1],
                   B["%s_03.%s" % (nm, sd)][1]]
            pts = np.array(pts)
            mid = pts[1:3].mean(0)
            d = np.linalg.norm(mid - cen)
            if d < dbest:
                best, dbest = (nm, pts), d
        nm, pts = best
        bones = ["%s_%02d.%s" % (nm, k, sd) for k in (1, 2, 3)]
        T = chain(pv, pts, bones, 0.0035, parent="hand." + sd, parent_blend=0.004)
        for k in out:
            out[k][m] = 0.0
        for k, v in T.items():
            if k not in out:
                out[k] = np.zeros(len(V))
            out[k][m] = v
    return out


def _components(ob):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    comp = np.full(len(bm.verts), -1)
    k = 0
    for v in bm.verts:
        if comp[v.index] >= 0:
            continue
        stack = [v]
        comp[v.index] = k
        while stack:
            a = stack.pop()
            for e in a.link_edges:
                o = e.other_vert(a)
                if comp[o.index] < 0:
                    comp[o.index] = k
                    stack.append(o)
        k += 1
    bm.free()
    return comp


# ----------------------------------------------------------------------------- apply
def _normalise(W, n):
    tot = np.zeros(n)
    for v in W.values():
        tot += np.clip(v, 0.0, None)
    tot = np.where(tot > 1e-9, tot, 1.0)
    return {k: np.clip(v, 0.0, None) / tot for k, v in W.items() if np.max(np.clip(v, 0.0, None)) > 1e-6}


def _write_groups(ob, W, bone_names):
    for g in list(ob.vertex_groups):
        if g.name in bone_names:
            ob.vertex_groups.remove(g)
    for k, w in W.items():
        g = ob.vertex_groups.new(name=k)
        q = np.round(w * 1000.0).astype(np.int64)
        for val in np.unique(q):
            if val <= 0:
                continue
            idx = np.nonzero(q == val)[0].tolist()
            g.add(idx, float(val) / 1000.0, "REPLACE")


def _armature_mod(ob, rig, preserve):
    mod = ob.modifiers.get("Armature") or ob.modifiers.new("Armature", "ARMATURE")
    mod.object = rig
    mod.use_vertex_groups = True
    mod.use_bone_envelopes = False
    mod.use_deform_preserve_volume = preserve
    # after the cloth thickness (a Solidify after the deform blew up where a
    # posed collar folded: its even-thickness offsets explode on folded
    # faces), before the normal blur, the hair-normal transfer and the
    # outline hull (those must see the posed shape)
    names = [m.name for m in ob.modifiers]
    pre = [i for i, n in enumerate(names) if n in PRE_DEFORM]
    want = (max(pre) + 1) if pre else 0
    cur = names.index("Armature")
    if cur != want:
        ob.modifiers.move(cur, want if cur > want else want - 1)
    return mod


def rest_world(ob):
    """ob's world matrix with its parent rig at rest, whatever the current pose.
    (matrix_world must not be read or set here: Blender resolves a bone parent
    through the pose, so a posed rig bakes its pose into the part.)"""
    p = ob.parent
    if p is None:
        return ob.matrix_basis.copy()
    if ob.parent_type == "BONE" and p.type == "ARMATURE" and ob.parent_bone in p.data.bones:
        b = p.data.bones[ob.parent_bone]
        P = p.matrix_world @ b.matrix_local @ Matrix.Translation((0.0, b.length, 0.0))
    else:
        P = p.matrix_world
    return P @ ob.matrix_parent_inverse @ ob.matrix_basis


def _parent_to_bone(ob, rig, bone):
    mw = rest_world(ob)
    ob.parent = rig
    ob.parent_type = "BONE"
    ob.parent_bone = bone
    b = rig.data.bones[bone]
    M = rig.matrix_world @ b.matrix_local @ Matrix.Translation((0.0, b.length, 0.0))
    ob.matrix_parent_inverse = M.inverted()
    ob.matrix_basis = mw            # at rest the parent inverse cancels the bone: world == basis
    for m in list(ob.modifiers):
        if m.type == "ARMATURE":
            ob.modifiers.remove(m)


def run(names=None):
    rig = bpy.data.objects[RIG]
    # rest pose while binding
    pos = rig.data.pose_position
    rig.data.pose_position = "REST"
    bpy.context.view_layer.update()
    B = _bones(rig)
    bone_names = set(B)
    report = {}
    model = bpy.data.collections["MODEL"].all_objects
    for ob in model:
        if names is not None and ob.name not in names:
            continue
        if ob.name in RIGID:
            _parent_to_bone(ob, rig, RIGID[ob.name])
            report[ob.name] = "child of " + RIGID[ob.name]
            continue
        if ob.type != "MESH":
            continue
        V = world(ob)
        W = weights_for(ob.name, V, B)
        if W is None:
            report[ob.name] = "skipped"
            continue
        W = _normalise(W, len(V))
        missing = [k for k in W if k not in bone_names]
        if missing:
            raise KeyError("%s: no bones %s" % (ob.name, missing))
        _write_groups(ob, W, bone_names)
        _armature_mod(ob, rig, ob.name in PRESERVE_VOLUME)
        report[ob.name] = len(W)
    rig.data.pose_position = pos
    bpy.context.view_layer.update()
    return report


if __name__ == "__main__":
    print(run())
