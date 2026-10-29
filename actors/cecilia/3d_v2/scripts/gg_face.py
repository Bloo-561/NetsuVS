"""GG-style face material with view-dependent eyes (run in Blender).

Why: the sheet draws the eyes right out to the face's visible edge, where the
3D face (traced from the front and side views) turns back towards the ears.
A texture projected from the front stretches there, so at 3/4 and at the
idle sprite's angle the near eye smeared into a wide streak. Anime 3D models
(Guilty Gear included) solve this by cheating per view; this does it in the
shader:

  - base texture (skin, blush, nose, mouth): front-planar, as before;
  - the eye nearer the camera is laid out in SCREEN space: the front drawing
    of the eye at its front-view size, hung from its inner corner (a point
    on the face surface), so it keeps the drawn shape at any angle; towards
    profile (60..90 deg) it slides back and narrows to where and how wide
    the side view draws it;
  - the eye further from the camera stays front-planar (physical: it
    compresses and tucks behind the cheek like a real far eye).
At 0 deg both layouts equal the front-planar mapping, so the front view is
exactly the sheet's front view.

Camera direction comes from the shading point's incoming vector in the
face's object space, so it works for any camera and, once the face is
parented to the head bone, for any head turn.
Run: import runpy; runpy.run_path(r"<3d_v2>\\scripts\\gg_face.py")["material"]()
"""
import importlib
import json
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cfg  # noqa: E402
import face_texture as ft  # noqa: E402

importlib.reload(cfg)
importlib.reload(ft)

P = cfg.PX
FRONT = cfg.VIEWS["front"]
SIDE = cfg.VIEWS["side"]
EYE_ROW = 106.0                       # front row through the eyes' middle (98..114)
# side view's drawn eye (side-crop columns / rows, traced on the crop)
SIDE_EYE_FRONT_U = 157.0              # its front end (towards the nose)
SIDE_EYE_BACK_U = 140.3               # its back end
SIDE_EYE_ROW_SHIFT = -1.3             # drawn 1.3 rows higher than in the front view
PROFILE_T0, PROFILE_T1 = 60.0, 90.0   # degrees: the near eye moves to the side view's placement over this range
# hair shadow on the forehead (the GG/anime convention): the bangs' own front
# silhouette, dropped by BANG_SHADOW_DROP and nudged away from the key light
BANG_SHADOW_DROP = 1.6                # sheet px down
BANG_SHADOW_SHIFT = 0.4               # sheet px towards her left (+x, away from the light)
FACE_SHADOW_TINT = tuple(v ** 2.2 for v in (0.95, 0.80, 0.78))    # = toon.SHADOW["skin"]


def _img(name, path, alpha=False):
    im = bpy.data.images.get(name)
    if im is None or os.path.normcase(bpy.path.abspath(im.filepath)) != os.path.normcase(path):
        if im is not None:
            bpy.data.images.remove(im)
        im = bpy.data.images.load(path)
        im.name = name
    else:
        im.reload()
    im.alpha_mode = "STRAIGHT" if alpha else "NONE"
    im.colorspace_settings.name = "sRGB"
    return im


class Nodes:
    """tiny expression helper: math nodes from sockets or numbers"""

    def __init__(self, nt):
        self.nt = nt

    def _in(self, sock, val):
        if isinstance(val, (int, float)):
            sock.default_value = float(val)
        else:
            self.nt.links.new(val, sock)

    def op(self, operation, a, b=0.0, c=0.0, clamp=False):
        m = self.nt.nodes.new("ShaderNodeMath")
        m.operation = operation
        m.use_clamp = clamp
        self._in(m.inputs[0], a)
        if len(m.inputs) > 1:
            self._in(m.inputs[1], b)
        if len(m.inputs) > 2:
            self._in(m.inputs[2], c)
        return m.outputs[0]

    def add(self, a, b): return self.op("ADD", a, b)
    def sub(self, a, b): return self.op("SUBTRACT", a, b)
    def mul(self, a, b): return self.op("MULTIPLY", a, b)
    def div(self, a, b): return self.op("DIVIDE", a, b)
    def madd(self, a, b, c): return self.op("MULTIPLY_ADD", a, b, c)       # a * b + c

    def mix(self, a, b, t):
        """a + (b - a) * t"""
        return self.madd(self.sub(b, a), t, a)

    def smoothstep(self, x, e0, e1):
        m = self.nt.nodes.new("ShaderNodeMapRange")
        m.data_type = "FLOAT"
        m.interpolation_type = "SMOOTHSTEP"
        m.clamp = True
        self._in(m.inputs["Value"], x)
        m.inputs["From Min"].default_value = e0
        m.inputs["From Max"].default_value = e1
        m.inputs["To Min"].default_value = 0.0
        m.inputs["To Max"].default_value = 1.0
        return m.outputs["Result"]

    def sep(self, vec):
        s = self.nt.nodes.new("ShaderNodeSeparateXYZ")
        self.nt.links.new(vec, s.inputs[0])
        return s.outputs["X"], s.outputs["Y"], s.outputs["Z"]

    def comb(self, x, y, z=0.0):
        c = self.nt.nodes.new("ShaderNodeCombineXYZ")
        for i, v in enumerate((x, y, z)):
            self._in(c.inputs[i], v)
        return c.outputs[0]


def face_xc():
    with open(os.path.join(cfg.REFS, "profiles_head.json")) as fh:
        g = json.load(fh)["face_gg"]
    return float(g["xc"][0])


def surface_y(face_ob, x, z):
    """depth of the face surface at (x, z), by a ray from the front"""
    mw = face_ob.matrix_world
    inv = mw.inverted()
    o = inv @ Vector((x, -1.0, z))
    d = (inv.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
    ok, loc, nrm, idx = face_ob.ray_cast(o, d)
    if not ok:
        raise RuntimeError("no face surface at x=%.4f z=%.4f" % (x, z))
    return (mw @ loc).y


def anchors(face_ob):
    """per eye: inner-corner x (object space ~ world while unparented), its
    surface depth, the side view's depth for it, and the scale at profile"""
    ext = ft.eye_extents()
    z_eye = (FRONT["sole_v"] - EYE_ROW) * P
    y_side_front = -(SIDE_EYE_FRONT_U - SIDE["centre_u"]) * P
    out = {}
    for e in ("R", "L"):
        u_in, u_out = ext[e]["inner"], ext[e]["outer"]
        x_in = (u_in - FRONT["centre_u"]) * P
        width_front = abs(u_in - u_out)
        out[e] = dict(x=x_in, y=surface_y(face_ob, x_in, z_eye), y_side=y_side_front,
                      s_profile=(SIDE_EYE_FRONT_U - SIDE_EYE_BACK_U) / width_front, u_inner=u_in)
    return out


def bang_shadow(bangs_name="bangs"):
    """render the bangs alone from the front over the face texture's area
    (refs/face/bangs_front.png), then drop it into the forehead shadow mask
    refs/face/face_shadow.png (texture space of face_texture)"""
    import numpy as np
    import imgio
    importlib.reload(imgio)
    W = ft.U_RANGE[1] - ft.U_RANGE[0]
    H = ft.V_RANGE[1] - ft.V_RANGE[0]
    rx, ry = int(round(W * ft.TEX_SCALE)), int(round(H * ft.TEX_SCALE))
    sc = bpy.data.scenes.new("GG_TMP_bangs")
    bangs = bpy.data.objects[bangs_name]
    hull = bangs.modifiers.get("GG_outline")
    hull_on = hull.show_render if hull is not None else False
    if hull is not None:
        hull.show_render = False                            # the outline hull is not hair
    try:
        sc.collection.objects.link(bangs)
        cam = bpy.data.objects.new("GG_TMP_cam", bpy.data.cameras.new("GG_TMP_cam"))
        sc.collection.objects.link(cam)
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = max(W, H) * P
        cam.data.sensor_fit = "AUTO"
        uc, vc = 0.5 * sum(ft.U_RANGE), 0.5 * sum(ft.V_RANGE)
        cam.location = ((uc - FRONT["centre_u"]) * P, -6.0, (FRONT["sole_v"] - vc) * P)
        cam.rotation_euler = (math.radians(90.0), 0.0, 0.0)
        sc.camera = cam
        r = sc.render
        r.engine = "BLENDER_WORKBENCH"
        r.film_transparent = True
        r.resolution_x, r.resolution_y, r.resolution_percentage = rx, ry, 100
        r.image_settings.file_format = "PNG"
        r.image_settings.color_mode = "RGBA"
        sh = sc.display.shading
        sh.light, sh.color_type, sh.single_color = "FLAT", "SINGLE", (1.0, 1.0, 1.0)
        sc.display.render_aa = "16"
        p = ft.tex_path("bangs_front.png")
        r.filepath = p
        bpy.ops.render.render(write_still=True, scene=sc.name)
    finally:
        if hull is not None:
            hull.show_render = hull_on
        cam_data = bpy.data.cameras.get("GG_TMP_cam")
        ob = bpy.data.objects.get("GG_TMP_cam")
        if ob is not None:
            bpy.data.objects.remove(ob, do_unlink=True)
        if cam_data is not None:
            bpy.data.cameras.remove(cam_data)
        bpy.data.scenes.remove(sc)
    m = imgio.load(p)[..., 3].astype(np.float32) / 255.0
    dy = int(round(BANG_SHADOW_DROP * ft.TEX_SCALE))
    dx = int(round(BANG_SHADOW_SHIFT * ft.TEX_SCALE))
    sh = np.zeros_like(m)
    sh[dy:, dx:] = m[:-dy, :m.shape[1] - dx]
    shadow = np.clip(sh - m, 0.0, 1.0)
    # soften by one texture pixel
    pp = np.pad(shadow, 1, mode="edge")
    shadow = sum(pp[a:a + shadow.shape[0], b:b + shadow.shape[1]] for a in range(3) for b in range(3)) / 9.0
    g = np.clip(shadow * 255.0 + 0.5, 0, 255).astype(np.uint8)
    imgio.save(ft.tex_path("face_shadow.png"), np.repeat(g[..., None], 3, axis=-1))
    return dict(mask_px=int((m > 0.5).sum()), shadow_px=int((shadow > 0.5).sum()))


KEY_DIR = (-0.62, -0.60, 0.50)        # = toon.KEY_DIR (the key light the cast shadow comes from)
CAST_RATIO = (0.25, 0.6)              # lit-with-shadows / N.L below .. above: in / out of the bangs' shadow
# the cast shadow fades out between these front rows: the forehead and upper
# lids take the bangs' shadow, as on the sheet; the side locks' shadow would
# otherwise cross the cheeks in a diagonal band at 3/4 (M6 t1)
CAST_ROWS = (101.0, 109.0)


IRIS_LAYERS = ("face_eye_frame.png", "face_eye_iris.png", "face_eye_open.png")


def iris_node_name(axis, eye):
    """the material's Value nodes the eye bones drive (sheet px): iris_du.R, iris_dv.R, ..."""
    return "iris_%s.%s" % (axis, eye)


def material(name="PROJ_face", face_name="face", shadow=False, cast=True, iris=None):
    """iris: None = use the moving-iris layers when face_texture has written
    them (Milestone 7), False = the single eyes layer (Milestones 4-6)"""
    face_ob = bpy.data.objects[face_name]
    if iris is None:
        iris = all(os.path.exists(ft.tex_path(n)) for n in IRIS_LAYERS)
    A = anchors(face_ob)
    xc = face_xc()
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    G = Nodes(nt)
    N, L = nt.nodes.new, nt.links.new
    out = N("ShaderNodeOutputMaterial")
    tc = N("ShaderNodeTexCoord")
    px, py, pz = G.sep(tc.outputs["Object"])
    geo = N("ShaderNodeNewGeometry")
    vt = N("ShaderNodeVectorTransform")
    vt.vector_type = "VECTOR"
    vt.convert_from, vt.convert_to = "WORLD", "OBJECT"
    L(geo.outputs["Incoming"], vt.inputs[0])
    dx, dy, dz = G.sep(vt.outputs[0])
    # camera yaw around the head: theta > 0 = camera towards her right (-x)
    hx, hy = G.mul(dx, -1.0), G.mul(dy, -1.0)
    ln = G.op("SQRT", G.add(G.mul(hx, hx), G.add(G.mul(hy, hy), 1e-8)))
    cth, sth = G.div(hy, ln), G.div(hx, ln)
    theta = G.mul(G.op("ARCTAN2", sth, cth), 180.0 / math.pi)
    xs = G.sub(G.mul(px, cth), G.mul(py, sth))                # screen x of the shading point
    W = ft.U_RANGE[1] - ft.U_RANGE[0]
    H = ft.V_RANGE[1] - ft.V_RANGE[0]
    cu, sv = FRONT["centre_u"], FRONT["sole_v"]
    row = G.madd(pz, -1.0 / P, sv)                            # front-crop row of the shading point

    def uv(u_px, row_px):
        """front-crop (column, row) -> texture uv (v bottom-up)"""
        u = G.madd(u_px, 1.0 / W, -ft.U_RANGE[0] / W) if not isinstance(u_px, (int, float)) else (u_px - ft.U_RANGE[0]) / W
        v = G.madd(row_px, -1.0 / H, 1.0 + ft.V_RANGE[0] / H)
        return G.comb(u, v)

    u_planar = G.madd(px, 1.0 / P, cu)                        # front-planar column
    # base: skin, blush, nose, mouth
    tb = N("ShaderNodeTexImage")
    tb.image = _img("face_base", ft.tex_path("face_base.png"))
    tb.extension = "EXTEND"
    tb.interpolation = "Cubic"
    L(uv(u_planar, row), tb.inputs["Vector"])
    col = tb.outputs["Color"]
    for e, sgn in (("R", 1.0), ("L", -1.0)):
        a = A[e]
        th_e = G.mul(theta, sgn)                              # > 0: this eye is the near one
        near = G.op("GREATER_THAN", th_e, 0.0)
        w = G.smoothstep(th_e, PROFILE_T0, PROFILE_T1)       # 0 .. 1 towards profile
        s = G.madd(w, a["s_profile"] - 1.0, 1.0)              # 1 -> side view's width
        ay = G.madd(w, a["y_side"] - a["y"], a["y"])          # anchor depth: surface -> side view
        xs_a = G.sub(G.mul(cth, a["x"]), G.mul(ay, sth))     # screen x of the inner corner
        du = G.div(G.div(G.sub(xs, xs_a), s), P)              # columns from the inner corner, front scale
        u_aff = G.add(du, a["u_inner"])
        u_e = G.mix(u_planar, u_aff, near)
        row_e = G.madd(G.mul(w, near), -SIDE_EYE_ROW_SHIFT, row)
        te = N("ShaderNodeTexImage")
        if iris:
            te.image = _img("face_eye_frame", ft.tex_path("face_eye_frame.png"), alpha=True)
        else:
            te.image = _img("face_eyes", ft.tex_path("face_eyes.png"), alpha=True)
        te.extension = "CLIP"
        te.interpolation = "Cubic"
        L(uv(u_e, row_e), te.inputs["Vector"])
        # this eye only on its own half of the face, and only its own half of the texture
        own_side = G.op("LESS_THAN", G.mul(G.sub(px, xc), sgn), 0.0)
        own_tex = G.op("LESS_THAN", G.mul(G.sub(u_e, cu), sgn), 0.0)
        own = G.mul(own_side, own_tex)
        alpha = G.mul(te.outputs["Alpha"], own)
        mx = N("ShaderNodeMix")
        mx.data_type = "RGBA"
        L(alpha, mx.inputs["Factor"])
        L(col, mx.inputs[6])
        L(te.outputs["Color"], mx.inputs[7])
        col = mx.outputs[2]
        if iris:
            # the iris, moved by the eye bone (iris_du / iris_dv, sheet px,
            # driven by rig_eyes), clipped to the eye opening
            vu = N("ShaderNodeValue")
            vu.name = vu.label = iris_node_name("du", e)
            vv = N("ShaderNodeValue")
            vv.name = vv.label = iris_node_name("dv", e)
            vu.outputs[0].default_value = 0.0
            vv.outputs[0].default_value = 0.0
            ti = N("ShaderNodeTexImage")
            ti.image = _img("face_eye_iris", ft.tex_path("face_eye_iris.png"), alpha=True)
            ti.extension = "CLIP"
            ti.interpolation = "Cubic"
            L(uv(G.sub(u_e, vu.outputs[0]), G.sub(row_e, vv.outputs[0])), ti.inputs["Vector"])
            to = N("ShaderNodeTexImage")
            to.image = _img("face_eye_open", ft.tex_path("face_eye_open.png"))
            to.image.colorspace_settings.name = "Non-Color"
            to.extension = "CLIP"
            to.interpolation = "Linear"
            L(uv(u_e, row_e), to.inputs["Vector"])
            so = N("ShaderNodeSeparateColor")
            L(to.outputs["Color"], so.inputs[0])
            a_i = G.mul(G.mul(ti.outputs["Alpha"], so.outputs[0]), own)
            mi = N("ShaderNodeMix")
            mi.data_type = "RGBA"
            L(a_i, mi.inputs["Factor"])
            L(col, mi.inputs[6])
            L(ti.outputs["Color"], mi.inputs[7])
            col = mi.outputs[2]
    if shadow and os.path.exists(ft.tex_path("face_shadow.png")):
        ts = N("ShaderNodeTexImage")
        ts.image = _img("face_shadow", ft.tex_path("face_shadow.png"))
        ts.image.colorspace_settings.name = "Non-Color"
        ts.extension = "EXTEND"
        ts.interpolation = "Linear"
        L(uv(u_planar, row), ts.inputs["Vector"])
        sep_s = N("ShaderNodeSeparateColor")
        L(ts.outputs["Color"], sep_s.inputs[0])
        dark = N("ShaderNodeMix")
        dark.data_type = "RGBA"
        dark.blend_type = "MULTIPLY"
        dark.inputs["Factor"].default_value = 1.0
        L(col, dark.inputs[6])
        dark.inputs[7].default_value = FACE_SHADOW_TINT + (1.0,)
        msh = N("ShaderNodeMix")
        msh.data_type = "RGBA"
        L(sep_s.outputs[0], msh.inputs["Factor"])
        L(col, msh.inputs[6])
        L(dark.outputs[2], msh.inputs[7])
        col = msh.outputs[2]
    if cast:
        # the bangs' shadow on the forehead, cast by the key light (only the
        # bangs cast shadows, toon.CASTERS): EEVEE's lit diffuse with shadows
        # divided by the unshadowed N.L tells shadowed from lit
        dif = N("ShaderNodeBsdfDiffuse")
        dif.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
        s2r = N("ShaderNodeShaderToRGB")
        L(dif.outputs[0], s2r.inputs[0])
        bw = N("ShaderNodeRGBToBW")
        L(s2r.outputs["Color"], bw.inputs[0])
        g2 = N("ShaderNodeNewGeometry")
        kv = N("ShaderNodeCombineXYZ")
        kn = Vector(KEY_DIR).normalized()
        for i in range(3):
            kv.inputs[i].default_value = kn[i]
        dot = N("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        L(g2.outputs["Normal"], dot.inputs[0])
        L(kv.outputs[0], dot.inputs[1])
        ndl = G.op("MAXIMUM", dot.outputs["Value"], 0.05)
        ratio = G.div(bw.outputs[0], ndl)
        lit = G.smoothstep(ratio, CAST_RATIO[0], CAST_RATIO[1])
        in_light = G.op("GREATER_THAN", dot.outputs["Value"], 0.05)
        cast_f = G.mul(G.sub(1.0, lit), in_light)          # 1 = in the bangs' shadow
        cast_f = G.mul(cast_f, G.sub(1.0, G.smoothstep(row, CAST_ROWS[0], CAST_ROWS[1])))
        dark = N("ShaderNodeMix")
        dark.data_type = "RGBA"
        dark.blend_type = "MULTIPLY"
        dark.inputs["Factor"].default_value = 1.0
        L(col, dark.inputs[6])
        dark.inputs[7].default_value = FACE_SHADOW_TINT + (1.0,)
        mc = N("ShaderNodeMix")
        mc.data_type = "RGBA"
        L(cast_f, mc.inputs["Factor"])
        L(col, mc.inputs[6])
        L(dark.outputs[2], mc.inputs[7])
        col = mc.outputs[2]
    em = N("ShaderNodeEmission")
    L(col, em.inputs["Color"])
    L(em.outputs[0], out.inputs["Surface"])
    if face_ob.data.materials:
        face_ob.data.materials[0] = mat
    else:
        face_ob.data.materials.append(mat)
    return dict(material=mat.name, anchors={k: {kk: round(vv, 4) for kk, vv in v.items()} for k, v in A.items()}, xc=xc,
                iris=bool(iris))
