"""Colour by projection (preview, run in Blender): the sheet's front/back/side
images projected onto the model from their orthographic cameras.

For every vertex: visibility from each view direction (BVH ray cast against
the whole MODEL, so the front image doesn't paint through onto hidden
surfaces), stored as point attributes vis_f, vis_b, vis_r, vis_l. The
material evaluates per pixel:
    colour = sum_v w_v * vis_v * image_v(projected uv) / sum_v w_v * vis_v
with w_v = max(0, facing)^K from the shading normal. Left side uses the side
image mirrored (the side view shows her right side). Surfaces no view sees
get the object's fallback colour. Emission only: this shows the sheet's own
colours/shading; the toon shader replaces it in M6, and M5 bakes + cleans it.

Head parts (LAYERED) project per-class layers (refs/layers, see layers.py)
instead of the raw crops, so each part only takes its own colours, and use
only the views that suit them. The face is not projected from the
turnaround at all: it carries the drawn face texture of face_texture.py
(eyes from the high-resolution eyes panel), mapped front-planar. The ears
take the side view alone.
Run: import runpy; ns = runpy.run_path(r"<3d_v2>\\scripts\\projection.py"); ns["apply"]()
"""
import importlib
import os
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cfg  # noqa: E402

importlib.reload(cfg)

K = 4.0                  # facing exponent (sharper = less blending between views)
DIRS = {"vis_f": Vector((0, -1, 0)), "vis_b": Vector((0, 1, 0)), "vis_r": Vector((-1, 0, 0)), "vis_l": Vector((1, 0, 0))}
EPS = 0.0015
W_EPS = 1e-5             # floor added to every view weight (see material())
FACE_K = 8.0             # face: front drawing vs plain skin blend sharpness (by normal)
LAYER_DIR = os.path.join(cfg.REFS, "layers")
ALL = ("front", "back", "side")
# object: (layer, views, K, use visibility)
LAYERED = {
    "hair": ("hair", ALL, 8.0, True),
    "bangs": ("hair", ALL, 8.0, False),
    "skull": ("hair", ALL, 4.0, False),       # seen only through gaps: take the drawing as is
    "ahoge": ("hair", ALL, 4.0, False),
    "face": ("facetex", ("front",), K, False),            # face_texture.py: drawn face, front-planar
    "neck": ("skin", ALL, K, False),
    "ear_R": ("skin", ("side",), K, False),
    "ear_L": ("skin", ("side",), K, False),
    "headband": ("band", ("front", "side"), K, False),
    "clip_R": ("clip", ("front", "side"), K, False),
    "clip_L": ("clip", ("front", "side"), K, False),
}


def model_objects(coll="MODEL"):
    """the model's meshes; helpers that don't render (toon's hair normal
    proxy) are neither painted nor occluders"""
    return [o for o in bpy.data.collections[coll].all_objects if o.type == "MESH" and not o.hide_render]


def build_bvh(objs):
    # the toon outline hulls (toon.add_outline) are not occluders: a vertex's
    # own hull, 1.6 mm out, would hide it from every view
    hulls = [m for o in objs for m in o.modifiers if m.name == "GG_outline" and m.show_viewport]
    for m in hulls:
        m.show_viewport = False
    try:
        return _build_bvh(objs)
    finally:
        for m in hulls:
            m.show_viewport = True


def _build_bvh(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    verts, polys = [], []
    for o in objs:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        mw = o.matrix_world
        base = len(verts)
        verts += [mw @ v.co for v in me.vertices]
        polys += [[base + i for i in p.vertices] for p in me.polygons]
        ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys, epsilon=0.0)


def add_visibility(objs, occluders=None):
    bvh = build_bvh(occluders or model_objects())
    for o in objs:
        me = o.data
        mw = o.matrix_world
        nm = mw.to_3x3().inverted_safe().transposed()
        vis = {k: np.zeros(len(me.vertices), np.float32) for k in DIRS}
        pn = np.zeros((len(me.vertices), 3), np.float32)
        for i, v in enumerate(me.vertices):
            p = mw @ v.co
            n = (nm @ v.normal).normalized()
            pn[i] = n
            for k, d in DIRS.items():
                if n.dot(d) <= -0.05:
                    continue                       # faces away from this view
                origin = p + d * EPS + n * EPS
                hit = bvh.ray_cast(origin, d, 10.0)
                vis[k][i] = 0.0 if hit[0] is not None else 1.0
        for k, arr in vis.items():
            att = me.attributes.get(k) or me.attributes.new(k, "FLOAT", "POINT")
            att.data.foreach_set("value", arr)
        att = me.attributes.get("proj_n") or me.attributes.new("proj_n", "FLOAT_VECTOR", "POINT")
        att.data.foreach_set("vector", pn.ravel())
    return len(objs)


def _img(name, path):
    im = bpy.data.images.get(name)
    if im is None:
        im = bpy.data.images.load(path, check_existing=True)
        im.name = name
    else:
        im.reload()
    return im


def image_for(view, layer=None):
    """(datablock name, path) of the image projected for a view, None if missing"""
    if layer is None:
        return "ref_" + view, cfg.ref_path(view)
    p = os.path.join(LAYER_DIR, "%s_%s.png" % (layer, view))
    return ("layer_%s_%s" % (layer, view), p) if os.path.exists(p) else None


def face_material(name="PROJ_face"):
    """the drawn face texture (face_texture.py), mapped front-planar: texture
    pixel = (front-crop column - U0, row - V0) * TEX_SCALE"""
    import face_texture as ft
    importlib.reload(ft)
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    out = N("ShaderNodeOutputMaterial")
    geo = N("ShaderNodeNewGeometry")
    sep = N("ShaderNodeSeparateXYZ")
    L(geo.outputs["Position"], sep.inputs[0])
    c = cfg.VIEWS["front"]
    W = (ft.U_RANGE[1] - ft.U_RANGE[0])
    H = (ft.V_RANGE[1] - ft.V_RANGE[0])

    def lin(sock, a, b):                                       # a * sock + b
        m1 = N("ShaderNodeMath"); m1.operation = "MULTIPLY_ADD"
        L(sock, m1.inputs[0]); m1.inputs[1].default_value = a; m1.inputs[2].default_value = b
        return m1.outputs[0]
    # u = (x / P + cu - U0) / W ; v(image, bottom-up) = 1 - (sole_v - z / P - V0) / H
    u = lin(sep.outputs["X"], 1.0 / (cfg.PX * W), (c["centre_u"] - ft.U_RANGE[0]) / W)
    v = lin(sep.outputs["Z"], 1.0 / (cfg.PX * H), 1.0 - (c["sole_v"] - ft.V_RANGE[0]) / H)
    comb = N("ShaderNodeCombineXYZ")
    L(u, comb.inputs[0]); L(v, comb.inputs[1])
    t = N("ShaderNodeTexImage")
    t.image = _img("face_tex", ft.tex_path())
    t.extension = "EXTEND"
    t.interpolation = "Cubic"
    L(comb.outputs[0], t.inputs["Vector"])
    # the drawing belongs on the face's front; where the face turns away
    # (cheek sides) a front-planar texture would stretch, so blend to plain
    # skin by the normal (FACE_K): the forehead corner of the texture is skin
    sk = N("ShaderNodeTexImage")
    sk.image = t.image
    sk.extension = "EXTEND"
    skuv = N("ShaderNodeCombineXYZ")
    skuv.inputs[0].default_value, skuv.inputs[1].default_value = 0.02, 0.98
    L(skuv.outputs[0], sk.inputs["Vector"])
    geo2 = N("ShaderNodeNewGeometry")
    nsep = N("ShaderNodeSeparateXYZ")
    L(geo2.outputs["Normal"], nsep.inputs[0])
    negy = N("ShaderNodeMath"); negy.operation = "MULTIPLY"
    L(nsep.outputs["Y"], negy.inputs[0]); negy.inputs[1].default_value = -1.0
    clampy = N("ShaderNodeMath"); clampy.operation = "MAXIMUM"
    L(negy.outputs[0], clampy.inputs[0]); clampy.inputs[1].default_value = 0.0
    # front share = ny'^K / (ny'^K + (1 - ny'^2)^(K/2)) with ny' = max(0, -ny)
    pw = N("ShaderNodeMath"); pw.operation = "POWER"
    L(clampy.outputs[0], pw.inputs[0]); pw.inputs[1].default_value = FACE_K
    sq = N("ShaderNodeMath"); sq.operation = "MULTIPLY"
    L(clampy.outputs[0], sq.inputs[0]); L(clampy.outputs[0], sq.inputs[1])
    om = N("ShaderNodeMath"); om.operation = "SUBTRACT"; om.use_clamp = True
    om.inputs[0].default_value = 1.0; L(sq.outputs[0], om.inputs[1])
    pw2 = N("ShaderNodeMath"); pw2.operation = "POWER"
    L(om.outputs[0], pw2.inputs[0]); pw2.inputs[1].default_value = FACE_K / 2.0
    den = N("ShaderNodeMath"); den.operation = "ADD"
    L(pw.outputs[0], den.inputs[0]); L(pw2.outputs[0], den.inputs[1])
    den2 = N("ShaderNodeMath"); den2.operation = "MAXIMUM"
    L(den.outputs[0], den2.inputs[0]); den2.inputs[1].default_value = 1e-6
    fr = N("ShaderNodeMath"); fr.operation = "DIVIDE"
    L(pw.outputs[0], fr.inputs[0]); L(den2.outputs[0], fr.inputs[1])
    mix = N("ShaderNodeMix"); mix.data_type = "RGBA"
    L(fr.outputs[0], mix.inputs["Factor"])
    L(sk.outputs["Color"], mix.inputs[6])
    L(t.outputs["Color"], mix.inputs[7])
    em = N("ShaderNodeEmission")
    L(mix.outputs[2], em.inputs["Color"])
    L(em.outputs[0], out.inputs["Surface"])
    return mat


def material(fallback=(0.5, 0.5, 0.5, 1.0), name="PROJ", layer=None, views=ALL, k=K, use_vis=True):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    N = nt.nodes.new
    L = nt.links.new
    out = N("ShaderNodeOutputMaterial")
    geo = N("ShaderNodeNewGeometry")
    sep = N("ShaderNodeSeparateXYZ")
    L(geo.outputs["Position"], sep.inputs[0])
    nsep = N("ShaderNodeSeparateXYZ")
    # view weights from the geometry's own normals, stored by add_visibility
    # ("proj_n"): the toon shading later replaces the shading normals (face
    # radial, hair from a capsule), which must not change what projects where
    pn = N("ShaderNodeAttribute")
    pn.attribute_name = "proj_n"
    pn.attribute_type = "GEOMETRY"
    pnn = N("ShaderNodeVectorMath")
    pnn.operation = "NORMALIZE"
    L(pn.outputs["Vector"], pnn.inputs[0])
    L(pnn.outputs[0], nsep.inputs[0])

    def math_(op, a, b=None, clamp=False):
        m = N("ShaderNodeMath")
        m.operation = op
        m.use_clamp = clamp
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[i].default_value = float(v)
            else:
                L(v, m.inputs[i])
        return m.outputs[0]

    def uv_for(view, coord_socket, sign):
        c = cfg.VIEWS[view]
        # u = (centre_u + sign * coord / P) / W ; v = (z / P - sole_v + H) / H
        u = math_("DIVIDE", math_("ADD", math_("MULTIPLY", coord_socket, sign / cfg.PX), c["centre_u"]), c["W"])
        v = math_("DIVIDE", math_("ADD", math_("DIVIDE", sep.outputs["Z"], cfg.PX), c["H"] - c["sole_v"]), c["H"])
        comb = N("ShaderNodeCombineXYZ")
        L(u, comb.inputs[0])
        L(v, comb.inputs[1])
        return comb.outputs[0]

    def tex(view, uv):
        src = image_for(view, layer.get(view) if isinstance(layer, dict) else layer)
        if src is None:
            return None
        t = N("ShaderNodeTexImage")
        t.image = _img(*src)
        t.extension = "EXTEND" if layer else "CLIP"
        t.interpolation = "Linear"
        L(uv, t.inputs["Vector"])
        return t.outputs["Color"]

    cols = {}
    if "front" in views:
        cols["front"] = tex("front", uv_for("front", sep.outputs["X"], 1.0))
    if "back" in views:
        cols["back"] = tex("back", uv_for("back", sep.outputs["X"], -1.0))
    if "side" in views:
        cols["side"] = tex("side", uv_for("side", sep.outputs["Y"], -1.0))
    cols = {v: c for v, c in cols.items() if c is not None}
    em = N("ShaderNodeEmission")
    L(em.outputs[0], out.inputs["Surface"])
    if len(cols) == 1 and not use_vis:
        # a single clean layer: take it as is, whatever the facing
        L(list(cols.values())[0], em.inputs["Color"])
        return mat

    def attr(name):
        a = N("ShaderNodeAttribute")
        a.attribute_name = name
        a.attribute_type = "GEOMETRY"
        return a.outputs["Fac"]

    def weight(n_socket, sign, vis_name):
        # + W_EPS: surfaces facing no camera (undersides, rims) still take the
        # visible views' colours instead of dropping to the flat fallback
        f = math_("ADD", math_("POWER", math_("MAXIMUM", math_("MULTIPLY", n_socket, sign), 0.0), k), W_EPS)
        return math_("MULTIPLY", f, attr(vis_name)) if use_vis else f

    def scale(col, w):
        m = N("ShaderNodeVectorMath")
        m.operation = "SCALE"
        L(col, m.inputs[0])
        L(w, m.inputs["Scale"])
        return m.outputs[0]

    def vadd(a, b):
        m = N("ShaderNodeVectorMath")
        m.operation = "ADD"
        L(a, m.inputs[0])
        L(b, m.inputs[1])
        return m.outputs[0]

    terms, ws = [], []
    if "front" in cols:
        w = weight(nsep.outputs["Y"], -1.0, "vis_f")
        terms.append(scale(cols["front"], w)); ws.append(w)
    if "back" in cols:
        w = weight(nsep.outputs["Y"], 1.0, "vis_b")
        terms.append(scale(cols["back"], w)); ws.append(w)
    if "side" in cols:
        w = math_("ADD", weight(nsep.outputs["X"], -1.0, "vis_r"), weight(nsep.outputs["X"], 1.0, "vis_l"))
        terms.append(scale(cols["side"], w)); ws.append(w)
    acc, tot = terms[0], ws[0]
    for t_, w_ in zip(terms[1:], ws[1:]):
        acc, tot = vadd(acc, t_), math_("ADD", tot, w_)
    norm = scale(acc, math_("DIVIDE", 1.0, math_("MAXIMUM", tot, 1e-4)))
    # fallback where no view sees the surface
    fb = N("ShaderNodeRGB")
    fb.outputs[0].default_value = fallback
    has = math_("GREATER_THAN", tot, 0.5 * W_EPS)
    mix = N("ShaderNodeMix")
    mix.data_type = "RGBA"
    L(has, mix.inputs["Factor"])
    L(fb.outputs[0], mix.inputs[6])
    L(norm, mix.inputs[7])
    L(mix.outputs[2], em.inputs["Color"])
    return mat


FALLBACK = {"hair": (0.12, 0.10, 0.14, 1), "bangs": (0.12, 0.10, 0.14, 1), "face": (0.99, 0.9, 0.86, 1), "skull": (0.12, 0.10, 0.14, 1),
            "ahoge": (0.12, 0.10, 0.14, 1), "nose": (0.99, 0.9, 0.86, 1), "neck": (0.95, 0.75, 0.7, 1),
            "ear_R": (0.99, 0.9, 0.86, 1), "ear_L": (0.99, 0.9, 0.86, 1)}


def apply(objs=None, with_visibility=True):
    objs = objs or model_objects()
    if with_visibility:
        add_visibility(objs)
    for o in objs:
        fb = FALLBACK.get(o.name, (0.5, 0.5, 0.5, 1))
        if o.name in LAYERED and LAYERED[o.name][0] == "facetex":
            mat = face_material("PROJ_" + o.name)
        elif o.name in LAYERED:
            layer, views, k, use_vis = LAYERED[o.name]
            mat = material(fb, "PROJ_" + o.name, layer=layer, views=views, k=k, use_vis=use_vis)
        else:
            mat = material(fb, "PROJ_" + o.name)
        o.data.materials.clear()
        o.data.materials.append(mat)
    return [o.name for o in objs]
