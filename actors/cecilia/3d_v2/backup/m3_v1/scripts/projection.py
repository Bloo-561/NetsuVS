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
Run: import runpy; ns = runpy.run_path(r"<3d_v2>\\scripts\\projection.py"); ns["apply"]()
"""
import importlib
import math
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


def model_objects(coll="MODEL"):
    return [o for o in bpy.data.collections[coll].all_objects if o.type == "MESH"]


def build_bvh(objs):
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
        for i, v in enumerate(me.vertices):
            p = mw @ v.co
            n = (nm @ v.normal).normalized()
            for k, d in DIRS.items():
                if n.dot(d) <= -0.05:
                    continue                       # faces away from this view
                origin = p + d * EPS + n * EPS
                hit = bvh.ray_cast(origin, d, 10.0)
                vis[k][i] = 0.0 if hit[0] is not None else 1.0
        for k, arr in vis.items():
            att = me.attributes.get(k) or me.attributes.new(k, "FLOAT", "POINT")
            att.data.foreach_set("value", arr)
    return len(objs)


def _img(name, path):
    im = bpy.data.images.get(name)
    if im is None:
        im = bpy.data.images.load(path, check_existing=True)
        im.name = name
    return im


def material(fallback=(0.5, 0.5, 0.5, 1.0), name="PROJ"):
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
    L(geo.outputs["Normal"], nsep.inputs[0])

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
        t = N("ShaderNodeTexImage")
        t.image = _img("ref_" + view, cfg.ref_path(view))
        t.extension = "CLIP"
        t.interpolation = "Linear"
        L(uv, t.inputs["Vector"])
        return t.outputs["Color"]

    col_f = tex("front", uv_for("front", sep.outputs["X"], 1.0))
    col_b = tex("back", uv_for("back", sep.outputs["X"], -1.0))
    col_s = tex("side", uv_for("side", sep.outputs["Y"], -1.0))

    def attr(name):
        a = N("ShaderNodeAttribute")
        a.attribute_name = name
        a.attribute_type = "GEOMETRY"
        return a.outputs["Fac"]

    def weight(n_socket, sign, vis_name):
        f = math_("POWER", math_("MAXIMUM", math_("MULTIPLY", n_socket, sign), 0.0), K)
        return math_("MULTIPLY", f, attr(vis_name))
    w_f = weight(nsep.outputs["Y"], -1.0, "vis_f")
    w_b = weight(nsep.outputs["Y"], 1.0, "vis_b")
    w_r = weight(nsep.outputs["X"], -1.0, "vis_r")
    w_l = weight(nsep.outputs["X"], 1.0, "vis_l")
    w_s = math_("ADD", w_r, w_l)
    tot = math_("ADD", math_("ADD", w_f, w_b), w_s)

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
    acc = vadd(vadd(scale(col_f, w_f), scale(col_b, w_b)), scale(col_s, w_s))
    norm = scale(acc, math_("DIVIDE", 1.0, math_("MAXIMUM", tot, 1e-4)))
    # fallback where no view sees the surface
    fb = N("ShaderNodeRGB")
    fb.outputs[0].default_value = fallback
    has = math_("GREATER_THAN", tot, 1e-3)
    mix = N("ShaderNodeMix")
    mix.data_type = "RGBA"
    L(has, mix.inputs["Factor"])
    L(fb.outputs[0], mix.inputs[6])
    L(norm, mix.inputs[7])
    em = N("ShaderNodeEmission")
    L(mix.outputs[2], em.inputs["Color"])
    L(em.outputs[0], out.inputs["Surface"])
    return mat


FALLBACK = {"hair": (0.12, 0.10, 0.14, 1), "face": (0.99, 0.9, 0.86, 1), "skull": (0.12, 0.10, 0.14, 1),
            "nose": (0.99, 0.9, 0.86, 1), "neck": (0.95, 0.75, 0.7, 1), "ear_R": (0.99, 0.9, 0.86, 1),
            "ear_L": (0.99, 0.9, 0.86, 1)}


def apply(objs=None, with_visibility=True):
    objs = objs or model_objects()
    if with_visibility:
        add_visibility(objs)
    for o in objs:
        fb = FALLBACK.get(o.name, (0.5, 0.5, 0.5, 1))
        mat = material(fb, "PROJ_" + o.name)
        o.data.materials.clear()
        o.data.materials.append(mat)
    return [o.name for o in objs]
