"""GG-style cel shading (run in Blender).

Milestone 6: the Arc System Works (Guilty Gear Xrd) character shader, after
GDC 2015 "GuiltyGearXrd's Art Style" (J. Motomura) as implemented by
galloscript/GGXrdShading and Aerthas' ASW shaders (GG_Shade below):
  light   = ((N.L + 1) * occlusion) / 2 + (2 * threshold - 1) + bias
  shadow 1 where light < 0.5            colour: the sheet's shadow tone
  shadow 2 where occlusion or threshold < 0.1   colour: shadow^2 / base
  specular where N.H > 1 - size, inside the specular mask, on lit areas
with occlusion / threshold / specular mask baked per texel (shade_bake.py)
instead of painted, one fixed key light (KEY_DIR) and inverted-hull outlines
whose width is the sheet's line width (LINE_SHEET_PX, never under
LINE_MIN_PX render pixels; set_line_width) and whose colour is the sheet's
contour colour for each part (bake.outline_colours -> body_lineclr.png).

The M3 preview notes, still true:
  - one fixed key light direction; every part's colour goes through a hard
    two-tone step on N.L computed in the shader (lit = the colour, shadow =
    colour x a shadow tint). No shadow maps: the result is clean and the
    same in every render, the way GG's shading is (their shadows come from
    the normals and per-part thresholds, not from cast shadows);
  - the face's shading normals point away from a point inside the head
    (Normal Edit, radial): one clean shadow shape across the face instead of
    the noise of every bump;
  - the face uses gg_face (view-dependent eyes);
  - the hair is flat colour: the sheet's purple tips become a projected
    purple mask (layers.hair_purple) cut into 3 flat bands;
  - inverted-hull outlines (Solidify, flipped, back-face culled) in a dark
    tint of each part.
Run: import runpy; runpy.run_path(r"<3d_v2>\\scripts\\toon.py")["apply"]()
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cfg  # noqa: E402

KEY_DIR = Vector((-0.62, -0.60, 0.50))        # towards the light: her right-front (46 deg), 30 deg above
TEX_DIR = os.path.join(cfg.ROOT, "textures")
P = cfg.PX
# outlines: the sheet's outer contour is 1.74 / 1.73 px wide (FWHM, front / back
# median); the hull is that wide in sheet px, and at least LINE_MIN_PX render px
LINE_SHEET_PX = 1.75
LINE_MIN_PX = 1.0
OUTLINE_SCALE = {}                            # per-object width factors
STEP_W = 0.008                                # half-width of the light / shadow steps (anti-aliasing)
SPEC_METAL = dict(size=0.05, color=(255, 248, 228))    # gold / silver fittings (mask: shade_bake.SPEC_FAMILIES)
SPEC_HAIR = dict(size=0.10, color=(100, 100, 106))     # the sheet's grey sheen on the black hair (98-99, 98, 103-105)
# per-object specular: the jacket's sheen (shade_bake.SHEEN_MODE), a wide N.H
# lobe: from the front it takes the upper chest and the front panels, as the
# sheet draws it, and leaves the sides and under the bust black; its colour is
# the sheet's (light grey, 110-130 cluster)
SPEC_OBJ = {"jacket": dict(size=0.06, color=(121, 121, 125)),
            # the neckerchief's satin: the sheet's lightest yellow (99.5th percentile), not the metal's white
            "neckerchief": dict(size=0.05, color=(255, 232, 146))}
SKIN_SHADE = (240, 199, 185)                  # bake.FAMILY["skin"] shadow tone
FACE_OUTLINE = (147, 96, 100)                 # the jaw line on the sheet (darkest third)
HAIR_OUTLINE = [(0.0, (39, 39, 46)), (0.30, (79, 33, 75))]   # bake.outline_colours: hairblack, purple
RAMP_POS = 0.0                                # light/shadow threshold on N.L (before the per-part bias)
RAMP_SOFT = 0.02                              # half-width of the step (AA does the rest)


def srgb(c):
    """sRGB 0-255 -> linear 0-1"""
    out = []
    for v in c:
        v = v / 255.0
        out.append(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def srgb_mult(m):
    """an sRGB-space multiplier (0-1) -> the linear multiplier with the same look"""
    return tuple(v ** 2.2 for v in m)


# shadow = colour x tint (given as sRGB multipliers); bias shifts the step
SHADOW = {"skin": srgb_mult((0.95, 0.80, 0.78)), "hair": srgb_mult((0.60, 0.58, 0.72)),
          "default": srgb_mult((0.66, 0.64, 0.76))}
BIAS = {"skin": 0.0, "hair": 0.0, "default": 0.0}
BIAS_OBJ = {"neck": -0.6}                     # the neck sits in the chin's shadow (anime convention; light units)
NECK_SHADE = (246, 172, 152)                  # the sheet's neck under the chin (median; a warmer tone than the body's)
EAR_RGB, EAR_SHADE = (245, 211, 183), (223, 177, 154)   # the sheet's ear (side view: median, darkest fifth)
NO_OUTLINE = ("skull",)                       # inner filler: its edges against the hair are not lines
# the hair shell is pushed in round each ear (M3: the hair tucked behind the
# ear, so the ear shows as on the sheet's side view): a box-shaped pit ~3 x
# 7 cm, 6 cm deep. Its walls are hair, not a drawn edge: no outline there and
# no occlusion shadow (shade_bake), or the pit reads as a dark frame (M6 t2)
EAR_PIT = dict(y=(0.033, 0.068), z=(1.332, 1.403), absx=(0.05, 0.128))


def in_ear_pit(co):
    """co: (N, 3) world positions (rest pose) -> bool mask of the ear pits'
    walls and floor (both sides)"""
    import numpy as np
    co = np.asarray(co)
    ax = np.abs(co[:, 0])
    return ((co[:, 1] > EAR_PIT["y"][0]) & (co[:, 1] < EAR_PIT["y"][1]) & (co[:, 2] > EAR_PIT["z"][0]) &
            (co[:, 2] < EAR_PIT["z"][1]) & (ax > EAR_PIT["absx"][0]) & (ax < EAR_PIT["absx"][1]))


def ear_pit_outline(ob, name="outline_w"):
    """zero the hair's outline weight on the ear pits' vertices (the group
    itself comes from build_head.outline_weights)"""
    import numpy as np
    vg = ob.vertex_groups.get(name)
    if vg is None:
        return 0
    co = np.array([ob.matrix_world @ v.co for v in ob.data.vertices])
    idx = np.nonzero(in_ear_pit(co))[0].tolist()
    if idx:
        vg.add(idx, 0.0, "REPLACE")
    return len(idx)
SKIN_RGB = (254, 238, 226)                    # face_texture.skin_colour of the eyes panel
BAND_RGB = {"red": (205, 62, 64), "gold": (236, 178, 84)}
BAND_GOLD_RATIO = 0.2                         # linear g / r above this: the emblem
SKIN_PARTS = ("face", "neck", "ear_R", "ear_L")
HAIR_PARTS = ("hair", "bangs", "skull", "ahoge")
OUTLINE_W = 0.0016                            # m
OUTLINE = {"skin": srgb((120, 70, 64)), "hair": srgb((22, 18, 30)), "default": srgb((24, 20, 28))}
FACE_NORMAL_CENTRE = (0.0, 0.035, 1.395)      # inside the head, behind the face
# flat hair colours (sRGB) from the sheet's hair pixels (M6: luminance
# clusters of the hair class in all three views): dark base, a mid purple and
# the tips' purple; cut points on the baked purple mask. HAIR_SHADE: each
# band's shadow tone, the next cluster down (black hair: 77-79 lit / 66-67
# shadow / 46 darkest; purple: 152-156 / 119-121 / 97-100 / 62-74)
HAIR_BANDS = [(0.0, (78, 79, 84)), (0.30, (118, 56, 106)), (0.62, (154, 81, 137))]
HAIR_SHADE = [(0.0, (66, 67, 72)), (0.30, (84, 36, 80)), (0.62, (100, 44, 94))]


def kind(name):
    if name in SKIN_PARTS:
        return "skin"
    if name in HAIR_PARTS:
        return "hair"
    return "default"


CASTERS = ("bangs",)                         # the only shadow casters: the bangs onto the forehead


def key_light(scene):
    """a sun along KEY_DIR. The toon step does not read it (GG_Toon holds
    the same direction); it only casts the bangs' shadow onto the face
    (gg_face, CASTERS)"""
    ob = bpy.data.objects.get("GG_Key")
    if ob is None:
        ob = bpy.data.objects.new("GG_Key", bpy.data.lights.new("GG_Key", "SUN"))
    if scene.collection.objects.get(ob.name) is None:
        scene.collection.objects.link(ob)
    ob.data.energy = math.pi                      # white diffuse then reads N.L (x shadow)
    ob.data.angle = math.radians(0.5)
    ob.data.use_shadow = True
    for attr, val in (("shadow_maximum_resolution", 0.0002), ("shadow_filter_radius", 0.5),
                      ("use_shadow_jitter", False)):
        if hasattr(ob.data, attr):
            setattr(ob.data, attr, val)
    ee = scene.eevee
    for attr, val in (("use_shadows", True), ("shadow_ray_count", 1), ("shadow_step_count", 6)):
        if hasattr(ee, attr):
            setattr(ee, attr, val)
    ob.rotation_euler = KEY_DIR.normalized().to_track_quat("Z", "Y").to_euler()
    return ob


def toon_group():
    """node group: Color, Shadow (tint), Bias -> toon colour (lit / shadow by
    a hard step on N.L + Bias)"""
    g = bpy.data.node_groups.get("GG_Toon")
    if g is not None:
        bpy.data.node_groups.remove(g)
    g = bpy.data.node_groups.new("GG_Toon", "ShaderNodeTree")
    g.interface.new_socket("Color", in_out="INPUT", socket_type="NodeSocketColor")
    g.interface.new_socket("Shadow", in_out="INPUT", socket_type="NodeSocketColor")
    g.interface.new_socket("Bias", in_out="INPUT", socket_type="NodeSocketFloat")
    g.interface.new_socket("Color", in_out="OUTPUT", socket_type="NodeSocketColor")
    N, L = g.nodes.new, g.links.new
    gin, gout = N("NodeGroupInput"), N("NodeGroupOutput")
    geo = N("ShaderNodeNewGeometry")
    key = N("ShaderNodeCombineXYZ")
    k = KEY_DIR.normalized()
    for i in range(3):
        key.inputs[i].default_value = k[i]
    dot = N("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    L(geo.outputs["Normal"], dot.inputs[0])
    L(key.outputs[0], dot.inputs[1])
    add = N("ShaderNodeMath")
    add.operation = "ADD"
    L(dot.outputs["Value"], add.inputs[0])
    L(gin.outputs["Bias"], add.inputs[1])
    step = N("ShaderNodeMapRange")
    step.data_type = "FLOAT"
    step.clamp = True
    L(add.outputs[0], step.inputs["Value"])
    step.inputs["From Min"].default_value = RAMP_POS - RAMP_SOFT
    step.inputs["From Max"].default_value = RAMP_POS + RAMP_SOFT
    shade = N("ShaderNodeMix")
    shade.data_type = "RGBA"
    shade.blend_type = "MULTIPLY"
    shade.inputs["Factor"].default_value = 1.0
    L(gin.outputs[0], shade.inputs[6])
    L(gin.outputs[1], shade.inputs[7])
    mix = N("ShaderNodeMix")
    mix.data_type = "RGBA"
    L(step.outputs["Result"], mix.inputs["Factor"])
    L(shade.outputs[2], mix.inputs[6])
    L(gin.outputs[0], mix.inputs[7])
    L(mix.outputs[2], gout.inputs[0])
    return g


def toonify(mat, k, bias=None):
    """insert GG_Toon between a material's colour and its emission"""
    nt = mat.node_tree
    em = next((n for n in nt.nodes if n.type == "EMISSION"), None)
    if em is None or not em.inputs["Color"].links:
        return False
    old = next((n for n in nt.nodes if n.type == "GROUP" and n.node_tree and n.node_tree.name == "GG_Toon"), None)
    src = em.inputs["Color"].links[0].from_socket
    if old is not None:                                   # already toonified: re-link to its input
        src = old.inputs[0].links[0].from_socket
        nt.nodes.remove(old)
    grp = nt.nodes.new("ShaderNodeGroup")
    grp.node_tree = bpy.data.node_groups["GG_Toon"]
    nt.links.new(src, grp.inputs[0])
    grp.inputs[1].default_value = SHADOW[k] + (1.0,)
    grp.inputs[2].default_value = BIAS[k] if bias is None else bias
    nt.links.new(grp.outputs[0], em.inputs["Color"])
    return True


HAIR_MASK = os.path.join(cfg.ROOT, "textures", "hair_mask.png")     # bake.py (M5)


def hair_mask_material(ob, name):
    """the purple mask baked into the hair atlas (bake.py), read through UVs,
    so it stays on the hair when the hair is posed"""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVBake"
    t = nt.nodes.new("ShaderNodeTexImage")
    im = bpy.data.images.get("hair_mask.png")
    if im is None:
        im = bpy.data.images.load(HAIR_MASK, check_existing=True)
        im.name = "hair_mask.png"
    else:
        im.filepath = HAIR_MASK
        im.reload()
    im.colorspace_settings.name = "Non-Color"
    t.image = im
    t.interpolation = "Linear"
    t.extension = "EXTEND"
    nt.links.new(uv.outputs["UV"], t.inputs["Vector"])
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(t.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return mat


SHADE_TEX = os.path.join(cfg.ROOT, "textures", "body_shade.png")   # bake.py (M5): the families' shadow tones


def toon_tex_group():
    """node group: Color (lit), Shadow (the sheet's own shadow colour), Bias ->
    the same hard step on N.L as GG_Toon, but picking between two colours"""
    g = bpy.data.node_groups.get("GG_ToonTex")
    if g is not None:
        bpy.data.node_groups.remove(g)
    g = bpy.data.node_groups.new("GG_ToonTex", "ShaderNodeTree")
    g.interface.new_socket("Color", in_out="INPUT", socket_type="NodeSocketColor")
    g.interface.new_socket("Shadow", in_out="INPUT", socket_type="NodeSocketColor")
    g.interface.new_socket("Bias", in_out="INPUT", socket_type="NodeSocketFloat")
    g.interface.new_socket("Color", in_out="OUTPUT", socket_type="NodeSocketColor")
    N, L = g.nodes.new, g.links.new
    gin, gout = N("NodeGroupInput"), N("NodeGroupOutput")
    geo = N("ShaderNodeNewGeometry")
    key = N("ShaderNodeCombineXYZ")
    k = KEY_DIR.normalized()
    for i in range(3):
        key.inputs[i].default_value = k[i]
    dot = N("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    L(geo.outputs["Normal"], dot.inputs[0])
    L(key.outputs[0], dot.inputs[1])
    add = N("ShaderNodeMath")
    add.operation = "ADD"
    L(dot.outputs["Value"], add.inputs[0])
    L(gin.outputs["Bias"], add.inputs[1])
    step = N("ShaderNodeMapRange")
    step.data_type = "FLOAT"
    step.clamp = True
    L(add.outputs[0], step.inputs["Value"])
    step.inputs["From Min"].default_value = RAMP_POS - RAMP_SOFT
    step.inputs["From Max"].default_value = RAMP_POS + RAMP_SOFT
    mix = N("ShaderNodeMix")
    mix.data_type = "RGBA"
    L(step.outputs["Result"], mix.inputs["Factor"])
    L(gin.outputs[1], mix.inputs[6])
    L(gin.outputs[0], mix.inputs[7])
    L(mix.outputs[2], gout.inputs[0])
    return g


def toonify_tex(mat, bias=None):
    """baked-texture material: lit colour from its base texture, shadow colour
    from the shade texture at the same UV"""
    nt = mat.node_tree
    em = next((n for n in nt.nodes if n.type == "EMISSION"), None)
    if em is None or not em.inputs["Color"].links:
        return False
    old = next((n for n in nt.nodes if n.type == "GROUP" and n.node_tree and n.node_tree.name == "GG_ToonTex"), None)
    src = em.inputs["Color"].links[0].from_socket
    if old is not None:
        src = old.inputs[0].links[0].from_socket
        nt.nodes.remove(old)
    base = src.node
    sh = next((n for n in nt.nodes if n.type == "TEX_IMAGE" and n.get("gg_shade")), None)
    if sh is None:
        sh = nt.nodes.new("ShaderNodeTexImage")
        sh["gg_shade"] = True
    im = bpy.data.images.get("body_shade.png")
    if im is None:
        im = bpy.data.images.load(SHADE_TEX, check_existing=True)
        im.name = "body_shade.png"
    else:
        im.filepath = SHADE_TEX
        im.reload()                                       # a fresh bake replaced the file
    sh.image = im
    sh.interpolation = "Linear"
    sh.extension = "EXTEND"
    if base.type == "TEX_IMAGE" and base.inputs["Vector"].links:
        nt.links.new(base.inputs["Vector"].links[0].from_socket, sh.inputs["Vector"])
    grp = nt.nodes.new("ShaderNodeGroup")
    grp.node_tree = bpy.data.node_groups.get("GG_ToonTex") or toon_tex_group()
    nt.links.new(src, grp.inputs[0])
    nt.links.new(sh.outputs["Color"], grp.inputs[1])
    grp.inputs[2].default_value = BIAS["default"] if bias is None else bias
    nt.links.new(grp.outputs[0], em.inputs["Color"])
    return True


def hair_material(ob):
    """flat hair colour: the purple mask (baked, or else projected like the
    sheet colours) cut into HAIR_BANDS"""
    name = "GG_hair_" + ob.name
    if ob.data.uv_layers.get("UVBake") is not None and os.path.exists(HAIR_MASK):
        mat = hair_mask_material(ob, name)
    else:
        import projection as pj
        importlib.reload(pj)
        _, views, k, use_vis = pj.LAYERED[ob.name]
        mat = pj.material(name=name, layer="hairp", views=views, k=k, use_vis=use_vis)
        for n in mat.node_tree.nodes:                     # the mask is data, not colour
            if n.type == "TEX_IMAGE" and n.image is not None and n.image.name.startswith("layer_hairp"):
                n.image.colorspace_settings.name = "Non-Color"
    nt = mat.node_tree
    em = next(n for n in nt.nodes if n.type == "EMISSION")
    src = em.inputs["Color"].links[0].from_socket
    bw = nt.nodes.new("ShaderNodeRGBToBW")
    nt.links.new(src, bw.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    els = ramp.color_ramp.elements
    while len(els) < len(HAIR_BANDS):
        els.new(0.5)
    for el, (pos, c) in zip(els, HAIR_BANDS):
        el.position = pos
        el.color = srgb(c) + (1.0,)
    nt.links.new(bw.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    me = ob.data
    if me.materials:
        me.materials[0] = mat
    else:
        me.materials.append(mat)
    return mat


def flat_material(ob, rgb, name=None):
    """one flat colour (emission), for parts whose drawn colours are just shading"""
    name = name or "GG_flat_" + ob.name
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    rgbn = nt.nodes.new("ShaderNodeRGB")
    rgbn.outputs[0].default_value = srgb(rgb) + (1.0,)
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(rgbn.outputs[0], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    me = ob.data
    if me.materials:
        me.materials[0] = mat
    else:
        me.materials.append(mat)
    return mat


def band_material(ob):
    """headband: the projected drawing cut into flat red and gold (emblem)"""
    mat = next((m for m in ob.data.materials if m and m.name.startswith("PROJ_")), None)
    if mat is None:
        return None
    nt = mat.node_tree
    em = next(n for n in nt.nodes if n.type == "EMISSION")
    src = em.inputs["Color"].links[0].from_socket
    if src.node.type == "MIX" and src.node.get("gg_band"):
        return mat
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(src, sep.inputs[0])
    ratio = nt.nodes.new("ShaderNodeMath")
    ratio.operation = "DIVIDE"
    nt.links.new(sep.outputs[1], ratio.inputs[0])
    nt.links.new(sep.outputs[0], ratio.inputs[1])
    gold = nt.nodes.new("ShaderNodeMath")
    gold.operation = "GREATER_THAN"
    nt.links.new(ratio.outputs[0], gold.inputs[0])
    gold.inputs[1].default_value = BAND_GOLD_RATIO
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix["gg_band"] = True
    nt.links.new(gold.outputs[0], mix.inputs["Factor"])
    mix.inputs[6].default_value = srgb(BAND_RGB["red"]) + (1.0,)
    mix.inputs[7].default_value = srgb(BAND_RGB["gold"]) + (1.0,)
    nt.links.new(mix.outputs[2], em.inputs["Color"])
    return mat


def outline_material(k):
    name = "GG_Outline_" + k
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = OUTLINE[k] + (1.0,)
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    mat.use_backface_culling = True
    return mat


def add_outline(ob, k):
    me = ob.data
    mat = outline_material(k)
    if mat.name not in [m.name for m in me.materials if m]:
        me.materials.append(mat)
    idx = [m.name for m in me.materials].index(mat.name)
    mod = ob.modifiers.get("GG_outline") or ob.modifiers.new("GG_outline", "SOLIDIFY")
    mod.thickness = OUTLINE_W
    mod.offset = 1.0
    mod.use_flip_normals = True
    mod.use_rim = False
    mod.material_offset = idx
    mod.use_quality_normals = True
    if ob.vertex_groups.get("outline_w") is not None:     # no outline along seams (build_head.outline_weights)
        mod.vertex_group = "outline_w"
        mod.thickness_vertex_group = 0.0
    else:
        mod.vertex_group = ""
    return mod


def face_normals(ob):
    e = bpy.data.objects.get("GG_FaceNormalCentre")
    if e is None:
        e = bpy.data.objects.new("GG_FaceNormalCentre", None)
        bpy.data.collections["MODEL"].objects.link(e)
    e.location = FACE_NORMAL_CENTRE
    e.hide_render = e.hide_viewport = True
    mod = ob.modifiers.get("GG_face_normals") or ob.modifiers.new("GG_face_normals", "NORMAL_EDIT")
    mod.mode = "RADIAL"
    mod.target = e
    mod.mix_mode = "COPY"
    # keep the outline modifier last (it must thicken the final shape)
    names = [m.name for m in ob.modifiers]
    if "GG_outline" in names and names.index("GG_outline") != len(names) - 1:
        ob.modifiers.move(names.index("GG_outline"), len(names) - 1)
    return mod


HAIR_PROXY = dict(centre=(0.0, 0.01, 1.42), radius=0.12, bottom=1.12, segments=48, rings=12)


def hair_normal_proxy():
    """a capsule around the head (hemisphere on a cylinder): the hair takes
    its normals (Data Transfer), the usual anime/GG trick, so the light/shadow
    edge on the hair is one clean curve instead of following every lock's
    facet; the drawn locks keep their outlines"""
    name = "GG_HairNormalProxy"
    ob = bpy.data.objects.get(name)
    if ob is not None:
        me = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        if me.users == 0:
            bpy.data.meshes.remove(me)
    cx, cy, cz = HAIR_PROXY["centre"]
    R, S, K = HAIR_PROXY["radius"], HAIR_PROXY["segments"], HAIR_PROXY["rings"]
    prof = [(R * math.sin(math.pi / 2 * k / K), cz + R * math.cos(math.pi / 2 * k / K)) for k in range(K + 1)]
    prof += [(R, cz - (cz - HAIR_PROXY["bottom"]) * t / 4.0) for t in range(1, 5)]
    verts, faces = [(cx, cy, prof[0][1])], []
    for r, z in prof[1:]:
        for s in range(S):
            a = 2 * math.pi * s / S
            verts.append((cx + r * math.cos(a), cy + r * math.sin(a), z))
    for s in range(S):
        faces.append((0, 1 + s, 1 + (s + 1) % S))
    for i in range(len(prof) - 2):
        b0, b1 = 1 + i * S, 1 + (i + 1) * S
        for s in range(S):
            faces.append((b0 + s, b1 + s, b1 + (s + 1) % S, b0 + (s + 1) % S))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.data.collections["MODEL"].objects.link(ob)
    ob.hide_render = True
    ob.display_type = "WIRE"
    return ob


def hair_normals(ob, proxy):
    mod = ob.modifiers.get("GG_hair_normals") or ob.modifiers.new("GG_hair_normals", "DATA_TRANSFER")
    mod.object = proxy
    mod.use_loop_data = True
    mod.data_types_loops = {"CUSTOM_NORMAL"}
    mod.loop_mapping = "POLYINTERP_NEAREST"
    mod.mix_mode = "REPLACE"
    mod.mix_factor = 1.0
    names = [m.name for m in ob.modifiers]                 # outline stays last
    if "GG_outline" in names and names.index("GG_outline") != len(names) - 1:
        ob.modifiers.move(names.index("GG_outline"), len(names) - 1)
    return mod


# Lofted parts follow the traced outline row by row (rings 1 sheet px apart);
# what is left of the binary masks' 1-px staircase (after profiles.py's
# smoothing) tilts the normals ring to ring, and the hard toon step turns that
# into a saw-toothed light/shadow edge. Blurring the normals over a few rings
# (custom normals, geometry and silhouettes untouched) gives a clean edge.
NORMAL_BLUR = {"leg_R": 8, "leg_L": 8, "arm_R": 6, "arm_L": 6, "body": 6, "shoe_R": 4, "shoe_L": 4,
               # the jacket's sheen (SPEC_OBJ) and its light/shadow edge broke up on its facets (M6 t2)
               "jacket": 6,
               # decals ray-cast cell by cell onto the body: their facets flicker in the toon step
               "neckerchief": 10, "shirt_collar": 6, "brooch": 4, "tie": 4,
               # the skirt's rings kink slightly at the blend rows: a dashed shadow line across the front
               "skirt": 8}


def normal_blur_group(iterations):
    """one node group per iteration count (Blender 5's modifier inputs live
    in mod.properties; a constant inside the group sidesteps that)"""
    name = "GG_NormalBlur_%d" % iterations
    ng = bpy.data.node_groups.get(name)
    if ng is not None:
        return ng
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    nodes, links = ng.nodes, ng.links
    gi, go = nodes.new("NodeGroupInput"), nodes.new("NodeGroupOutput")
    nrm = nodes.new("GeometryNodeInputNormal")
    blur = nodes.new("GeometryNodeBlurAttribute")
    blur.data_type = "FLOAT_VECTOR"
    blur.inputs["Iterations"].default_value = int(iterations)
    setn = nodes.new("GeometryNodeSetMeshNormal")
    setn.mode = "FREE"
    setn.domain = "POINT"
    links.new(gi.outputs["Geometry"], setn.inputs["Mesh"])
    links.new(nrm.outputs["Normal"], [s for s in blur.inputs if s.name == "Value" and s.enabled][0])
    vin = [s for s in setn.inputs if s.type == "VECTOR" and s.enabled][0]
    links.new([s for s in blur.outputs if s.name == "Value" and s.enabled][0], vin)
    links.new(setn.outputs["Mesh"], go.inputs["Geometry"])
    return ng


def blur_normals(ob, iterations):
    mod = ob.modifiers.get("GG_normal_blur") or ob.modifiers.new("GG_normal_blur", "NODES")
    mod.node_group = normal_blur_group(iterations)
    names = [m.name for m in ob.modifiers]                 # outline stays last
    if "GG_outline" in names and names.index("GG_outline") != len(names) - 1:
        ob.modifiers.move(names.index("GG_outline"), len(names) - 1)
    return mod


# ----------------------------------------------------------------------------- M6: GG_Shade
def shade_group():
    """Base, Shade, Ctrl (R occlusion, G threshold, B specular mask), Bias,
    SpecColor, SpecSize -> Color"""
    name = "GG_Shade"
    g = bpy.data.node_groups.get(name)
    if g is not None:
        bpy.data.node_groups.remove(g)
    g = bpy.data.node_groups.new(name, "ShaderNodeTree")
    for nm, st in (("Base", "NodeSocketColor"), ("Shade", "NodeSocketColor"), ("Ctrl", "NodeSocketColor"),
                   ("Bias", "NodeSocketFloat"), ("SpecColor", "NodeSocketColor"), ("SpecSize", "NodeSocketFloat")):
        g.interface.new_socket(nm, in_out="INPUT", socket_type=st)
    g.interface.new_socket("Color", in_out="OUTPUT", socket_type="NodeSocketColor")
    N, L = g.nodes.new, g.links.new
    gi, go = N("NodeGroupInput"), N("NodeGroupOutput")
    geo = N("ShaderNodeNewGeometry")
    key = N("ShaderNodeCombineXYZ")
    k = KEY_DIR.normalized()
    for i in range(3):
        key.inputs[i].default_value = k[i]

    def sock(x):
        return x

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

    def vmath(op, a, b=None):
        m = N("ShaderNodeVectorMath")
        m.operation = op
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (tuple, list)):
                m.inputs[i].default_value = v
            else:
                L(v, m.inputs[i])
        return m.outputs["Value"] if op == "DOT_PRODUCT" else m.outputs["Vector"]

    def ramp01(x, lo, hi):
        """0 below lo .. 1 above hi (linear, clamped)"""
        r = N("ShaderNodeMapRange")
        r.data_type = "FLOAT"
        r.clamp = True
        L(x, r.inputs["Value"])
        r.inputs["From Min"].default_value = lo
        r.inputs["From Max"].default_value = hi
        return r.outputs["Result"]

    def mix(fac, a, b):
        m = N("ShaderNodeMix")
        m.data_type = "RGBA"
        L(fac, m.inputs["Factor"])
        L(a, m.inputs[6])
        L(b, m.inputs[7])
        return m.outputs[2]

    sep = N("ShaderNodeSeparateColor")
    L(gi.outputs["Ctrl"], sep.inputs[0])
    occ, thr, spm = sep.outputs[0], sep.outputs[1], sep.outputs[2]
    nl = vmath("DOT_PRODUCT", geo.outputs["Normal"], key.outputs[0])
    light = math_("ADD", math_("ADD", math_("MULTIPLY", math_("MULTIPLY", math_("ADD", nl, 1.0), occ), 0.5),
                                       math_("SUBTRACT", math_("MULTIPLY", thr, 2.0), 1.0)), gi.outputs["Bias"])
    s1 = math_("SUBTRACT", 1.0, ramp01(light, 0.5 - STEP_W, 0.5 + STEP_W))
    s2 = math_("MAXIMUM", math_("SUBTRACT", 1.0, ramp01(occ, 0.1 - STEP_W, 0.1 + STEP_W)),
               math_("SUBTRACT", 1.0, ramp01(thr, 0.1 - STEP_W, 0.1 + STEP_W)))
    base, shade = gi.outputs["Base"], gi.outputs["Shade"]
    deep = vmath("MINIMUM", vmath("DIVIDE", vmath("MULTIPLY", shade, shade), vmath("MAXIMUM", base, (0.02, 0.02, 0.02))),
                 shade)
    c1 = mix(s1, base, shade)
    c2 = mix(s2, c1, deep)
    h = vmath("NORMALIZE", vmath("ADD", key.outputs[0], geo.outputs["Incoming"]))
    nh = vmath("DOT_PRODUCT", geo.outputs["Normal"], h)
    edge = math_("SUBTRACT", 1.0, gi.outputs["SpecSize"])
    sp = math_("MULTIPLY", math_("MULTIPLY", math_("GREATER_THAN", nh, edge), spm), math_("SUBTRACT", 1.0, s1))
    out = mix(sp, c2, gi.outputs["SpecColor"])
    L(out, go.inputs["Color"])
    return g


def _image(fname, colorspace="sRGB"):
    path = os.path.join(TEX_DIR, fname)
    im = bpy.data.images.get(fname)
    if im is None:
        im = bpy.data.images.load(path, check_existing=True)
        im.name = fname
    else:
        im.filepath = path
        im.reload()
    im.colorspace_settings.name = colorspace
    return im


def _new_material(name):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    return mat


def _assign(ob, mat):
    me = ob.data
    keep = [m for m in me.materials if m and m.name.startswith("GG_Outline")]
    me.materials.clear()
    me.materials.append(mat)
    for m in keep:
        me.materials.append(m)


def _tex(nt, uv, fname, colorspace="sRGB"):
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = _image(fname, colorspace)
    t.interpolation = "Linear"
    t.extension = "EXTEND"
    nt.links.new(uv, t.inputs["Vector"])
    return t


def _shade_node(nt, bias=0.0, spec=None):
    grp = nt.nodes.new("ShaderNodeGroup")
    grp.node_tree = bpy.data.node_groups.get("GG_Shade") or shade_group()
    grp.inputs["Bias"].default_value = bias
    spec = spec or SPEC_METAL
    grp.inputs["SpecColor"].default_value = srgb(spec["color"]) + (1.0,)
    grp.inputs["SpecSize"].default_value = spec["size"]
    return grp


def _emit(nt, color_socket):
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(color_socket, em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return em


def gg_tex_material(ob, bias=0.0, spec=None):
    """baked atlas part: base / shadow tone / control textures through UVBake"""
    mat = _new_material("TEX_" + ob.name)
    nt = mat.node_tree
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVBake"
    grp = _shade_node(nt, bias, spec)
    nt.links.new(_tex(nt, uv.outputs["UV"], "body_base.png").outputs["Color"], grp.inputs["Base"])
    nt.links.new(_tex(nt, uv.outputs["UV"], "body_shade.png").outputs["Color"], grp.inputs["Shade"])
    nt.links.new(_tex(nt, uv.outputs["UV"], "body_ctrl.png", "Non-Color").outputs["Color"], grp.inputs["Ctrl"])
    _emit(nt, grp.outputs["Color"])
    _assign(ob, mat)
    return mat


# ----------------------------------------------------------------------------- M8: the skirt's live shadow on the legs
# shade_bake bakes the legs' occlusion without the skirt and lace (raw sky
# share in R). A Geometry Nodes modifier on each leg ray-casts the POSED skirt
# and lace from every vertex over its hemisphere (SKIRT_OCC dirs, cosine
# weighted) and stores the share they leave open as "skirt_vis"; the leg
# material multiplies the two and remaps them like shade_bake does
# (AO_DEEP / AO_SHADOW / AO_OPEN). In the rest pose this reproduces the narrow
# band under the lace; when a leg lifts the skirt the shadow goes with it.
SKIRT_RECEIVERS = ("leg_R", "leg_L")            # = shade_bake.SKIRT_RECEIVERS
SKIRT_OCC = dict(objects=("skirt", "lace"), dirs=32, length=0.6, lift=0.003)
AO_REMAP = (0.18, 0.34, 0.55)                   # = shade_bake.AO_DEEP, AO_SHADOW, AO_OPEN


def _fib(n):
    out = []
    for i in range(n):
        z = 1.0 - 2.0 * (i + 0.5) / n
        r = math.sqrt(max(0.0, 1.0 - z * z))
        th = math.pi * (1.0 + 5.0 ** 0.5) * (i + 0.5)
        out.append((r * math.cos(th), r * math.sin(th), z))
    return out


def skirt_occ_group():
    name = "GG_SkirtOcclusion"
    g = bpy.data.node_groups.get(name)
    if g is not None:
        bpy.data.node_groups.remove(g)
    g = bpy.data.node_groups.new(name, "GeometryNodeTree")
    g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    g.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, L = g.nodes.new, g.links.new
    gi, go = N("NodeGroupInput"), N("NodeGroupOutput")
    join = N("GeometryNodeJoinGeometry")
    for nm in SKIRT_OCC["objects"]:
        oi = N("GeometryNodeObjectInfo")
        oi.transform_space = "RELATIVE"
        oi.inputs["Object"].default_value = bpy.data.objects[nm]
        L(oi.outputs["Geometry"], join.inputs[0])
    pos, nrm = N("GeometryNodeInputPosition"), N("GeometryNodeInputNormal")

    def vm(op, a, b, c=None):
        m = N("ShaderNodeVectorMath")
        m.operation = op
        for i, v in enumerate((a, b, c)):
            if v is None:
                continue
            if isinstance(v, (tuple, list, float, int)):
                m.inputs[i].default_value = v if not isinstance(v, (float, int)) else (v, v, v)
            else:
                L(v, m.inputs[i])
        return m.outputs["Value"] if op == "DOT_PRODUCT" else m.outputs["Vector"]

    def fm(op, a, b=None):
        m = N("ShaderNodeMath")
        m.operation = op
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (float, int)):
                m.inputs[i].default_value = float(v)
            else:
                L(v, m.inputs[i])
        return m.outputs[0]

    src = vm("MULTIPLY_ADD", nrm.outputs["Normal"], SKIRT_OCC["lift"], pos.outputs["Position"])
    wsum, bsum = None, None
    for d in _fib(SKIRT_OCC["dirs"]):
        c = vm("DOT_PRODUCT", nrm.outputs["Normal"], d)
        w = fm("MULTIPLY", c, fm("GREATER_THAN", c, 0.05))
        rc = N("GeometryNodeRaycast")
        L(join.outputs[0], rc.inputs["Target Geometry"])
        L(src, rc.inputs["Source Position"])
        rc.inputs["Ray Direction"].default_value = d
        rc.inputs["Ray Length"].default_value = SKIRT_OCC["length"]
        b = fm("MULTIPLY", w, rc.outputs["Is Hit"])
        wsum = w if wsum is None else fm("ADD", wsum, w)
        bsum = b if bsum is None else fm("ADD", bsum, b)
    vis = fm("SUBTRACT", 1.0, fm("DIVIDE", bsum, fm("MAXIMUM", wsum, 1e-4)))
    st = N("GeometryNodeStoreNamedAttribute")
    st.data_type = "FLOAT"
    st.domain = "POINT"
    L(gi.outputs[0], st.inputs["Geometry"])
    st.inputs["Name"].default_value = "skirt_vis"
    L(vis, st.inputs["Value"])
    L(st.outputs[0], go.inputs[0])
    return g


def skirt_occlusion(ob):
    """the live skirt-shadow modifier on a leg: after the pose (Armature) and
    the normal blur, before the outline hull"""
    grp = bpy.data.node_groups.get("GG_SkirtOcclusion") or skirt_occ_group()
    mod = ob.modifiers.get("GG_skirt_occ") or ob.modifiers.new("GG_skirt_occ", "NODES")
    mod.node_group = grp
    names = [m.name for m in ob.modifiers]
    want = len(names) - 1
    if "GG_outline" in names:
        want = names.index("GG_outline") - (1 if names.index("GG_outline") > names.index("GG_skirt_occ") else 0)
    if names.index("GG_skirt_occ") != want:
        ob.modifiers.move(names.index("GG_skirt_occ"), want)
    return mod


def gg_leg_material(ob, bias=0.0, spec=None):
    """gg_tex_material for a leg: control R is the raw sky share without the
    skirt; times the live skirt_vis, remapped to the shader's occlusion"""
    mat = _new_material("TEX_" + ob.name)
    nt = mat.node_tree
    N, L = nt.nodes.new, nt.links.new
    uv = N("ShaderNodeUVMap")
    uv.uv_map = "UVBake"
    grp = _shade_node(nt, bias, spec)
    L(_tex(nt, uv.outputs["UV"], "body_base.png").outputs["Color"], grp.inputs["Base"])
    L(_tex(nt, uv.outputs["UV"], "body_shade.png").outputs["Color"], grp.inputs["Shade"])
    ctrl = _tex(nt, uv.outputs["UV"], "body_ctrl.png", "Non-Color")
    sep = N("ShaderNodeSeparateColor")
    L(ctrl.outputs["Color"], sep.inputs[0])
    att = N("ShaderNodeAttribute")
    att.attribute_type = "GEOMETRY"
    att.attribute_name = "skirt_vis"
    a = N("ShaderNodeMath")
    a.operation = "MULTIPLY"
    L(sep.outputs[0], a.inputs[0])
    L(att.outputs["Fac"], a.inputs[1])
    total = None
    lo = 0.0
    for hi, step in zip(AO_REMAP, (0.1, 0.4, 0.5)):
        r = N("ShaderNodeMapRange")
        r.data_type = "FLOAT"
        r.clamp = True
        L(a.outputs[0], r.inputs["Value"])
        r.inputs["From Min"].default_value = lo
        r.inputs["From Max"].default_value = hi
        r.inputs["To Min"].default_value = 0.0
        r.inputs["To Max"].default_value = step
        total = r.outputs["Result"] if total is None else _add(nt, total, r.outputs["Result"])
        lo = hi
    comb = N("ShaderNodeCombineColor")
    L(total, comb.inputs[0])
    L(sep.outputs[1], comb.inputs[1])
    L(sep.outputs[2], comb.inputs[2])
    L(comb.outputs[0], grp.inputs["Ctrl"])
    _emit(nt, grp.outputs["Color"])
    _assign(ob, mat)
    return mat


def _add(nt, a, b):
    m = nt.nodes.new("ShaderNodeMath")
    m.operation = "ADD"
    nt.links.new(a, m.inputs[0])
    nt.links.new(b, m.inputs[1])
    return m.outputs[0]


def _ramp(nt, src, stops):
    r = nt.nodes.new("ShaderNodeValToRGB")
    r.color_ramp.interpolation = "CONSTANT"
    els = r.color_ramp.elements
    while len(els) < len(stops):
        els.new(0.5)
    for el, (pos, c) in zip(els, stops):
        el.position = pos
        el.color = srgb(c) + (1.0,)
    nt.links.new(src, r.inputs[0])
    return r.outputs["Color"]


def gg_hair_material(ob, bias=0.0):
    """the hair's three flat bands from the baked purple mask, their shadow
    tones, the hair control texture (occlusion + sheen strands)"""
    mat = _new_material("GG_hair_" + ob.name)
    nt = mat.node_tree
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVBake"
    mask = _tex(nt, uv.outputs["UV"], "hair_mask.png", "Non-Color")
    bw = nt.nodes.new("ShaderNodeRGBToBW")
    nt.links.new(mask.outputs["Color"], bw.inputs[0])
    lit = _ramp(nt, bw.outputs[0], HAIR_BANDS)
    dark = _ramp(nt, bw.outputs[0], HAIR_SHADE)
    grp = _shade_node(nt, bias, SPEC_HAIR)
    nt.links.new(lit, grp.inputs["Base"])
    nt.links.new(dark, grp.inputs["Shade"])
    nt.links.new(_tex(nt, uv.outputs["UV"], "hair_ctrl.png", "Non-Color").outputs["Color"], grp.inputs["Ctrl"])
    _emit(nt, grp.outputs["Color"])
    _assign(ob, mat)
    return mat


def gg_flat_material(ob, lit, shade, bias=0.0):
    """one flat colour with its shadow tone (neck, ears)"""
    mat = _new_material("GG_flat_" + ob.name)
    nt = mat.node_tree
    a, b, c = nt.nodes.new("ShaderNodeRGB"), nt.nodes.new("ShaderNodeRGB"), nt.nodes.new("ShaderNodeRGB")
    a.outputs[0].default_value = srgb(lit) + (1.0,)
    b.outputs[0].default_value = srgb(shade) + (1.0,)
    c.outputs[0].default_value = (1.0, 0.5, 0.0, 1.0)          # open, neutral threshold, no specular
    grp = _shade_node(nt, bias)
    nt.links.new(a.outputs[0], grp.inputs["Base"])
    nt.links.new(b.outputs[0], grp.inputs["Shade"])
    nt.links.new(c.outputs[0], grp.inputs["Ctrl"])
    _emit(nt, grp.outputs["Color"])
    _assign(ob, mat)
    return mat


def gg_outline_material(kind_):
    """outline hull colour: the sheet's contour colour of the part under it
    (texture through UVBake), or a constant"""
    name = "GG_Outline_" + kind_
    mat = _new_material(name)
    nt = mat.node_tree
    if kind_ == "tex":
        uv = nt.nodes.new("ShaderNodeUVMap")
        uv.uv_map = "UVBake"
        col = _tex(nt, uv.outputs["UV"], "body_lineclr.png").outputs["Color"]
    elif kind_ == "hair":
        uv = nt.nodes.new("ShaderNodeUVMap")
        uv.uv_map = "UVBake"
        mask = _tex(nt, uv.outputs["UV"], "hair_mask.png", "Non-Color")
        bw = nt.nodes.new("ShaderNodeRGBToBW")
        nt.links.new(mask.outputs["Color"], bw.inputs[0])
        col = _ramp(nt, bw.outputs[0], HAIR_OUTLINE)
    else:
        rgbn = nt.nodes.new("ShaderNodeRGB")
        rgbn.outputs[0].default_value = srgb(FACE_OUTLINE if kind_ == "skin" else (24, 20, 28)) + (1.0,)
        col = rgbn.outputs[0]
    _emit(nt, col)
    mat.use_backface_culling = True
    return mat


def gg_add_outline(ob, kind_):
    me = ob.data
    mat = gg_outline_material(kind_) if bpy.data.materials.get("GG_Outline_" + kind_) is None else \
        bpy.data.materials["GG_Outline_" + kind_]
    old = [i for i, m in enumerate(me.materials) if m and m.name.startswith("GG_Outline") and m.name != mat.name]
    for i in reversed(old):
        me.materials.pop(index=i)
    if mat.name not in [m.name for m in me.materials if m]:
        me.materials.append(mat)
    idx = [m.name for m in me.materials].index(mat.name)
    mod = ob.modifiers.get("GG_outline") or ob.modifiers.new("GG_outline", "SOLIDIFY")
    mod.thickness = LINE_SHEET_PX * P * OUTLINE_SCALE.get(ob.name, 1.0)
    mod.offset = 1.0
    mod.use_flip_normals = True
    mod.use_rim = False
    mod.material_offset = idx
    mod.use_quality_normals = True
    if ob.vertex_groups.get("outline_w") is not None:     # no outline along seams (build_head.outline_weights)
        mod.vertex_group = "outline_w"
        mod.thickness_vertex_group = 0.0
    else:
        mod.vertex_group = ""
    names = [m.name for m in ob.modifiers]                 # the hull goes last
    if names.index("GG_outline") != len(names) - 1:
        ob.modifiers.move(names.index("GG_outline"), len(names) - 1)
    return mod


def set_line_width(mpp=None):
    """outline hull width for a render at mpp metres per render pixel: the
    sheet's line width, but never thinner than LINE_MIN_PX render pixels"""
    t = LINE_SHEET_PX * P
    if mpp:
        t = max(t, LINE_MIN_PX * mpp)
    n = 0
    for ob in bpy.data.collections["MODEL"].all_objects:
        mod = ob.modifiers.get("GG_outline") if ob.type == "MESH" else None
        if mod is not None:
            mod.thickness = t * OUTLINE_SCALE.get(ob.name, 1.0)
            n += 1
    return dict(thickness_mm=round(t * 1000, 2), hulls=n)


def apply(scene_name="HEADREVIEW", head_only=False):
    """all materials, outlines and normal modifiers; run in the rest pose
    (the face material measures the face in world space)"""
    rig = bpy.data.objects.get("CEC_rig")
    old = rig.data.pose_position if rig is not None else None
    if rig is not None:
        rig.data.pose_position = "REST"
        bpy.context.view_layer.update()
    try:
        return _apply(scene_name, head_only)
    finally:
        if rig is not None:
            rig.data.pose_position = old
            bpy.context.view_layer.update()


def _apply(scene_name="HEADREVIEW", head_only=False):
    import gg_face
    importlib.reload(gg_face)
    toon_group()
    toon_tex_group()
    proxy = hair_normal_proxy()
    for ob in bpy.data.collections["MODEL"].all_objects:
        if ob.type == "MESH":
            ob.visible_shadow = ob.name in CASTERS
    done = []
    for ob in list(bpy.data.collections["MODEL"].all_objects):
        if ob.type != "MESH" or ob.name == proxy.name:
            continue
        k = kind(ob.name)
        has_uv = ob.data.uv_layers.get("UVBake") is not None
        bias = BIAS_OBJ.get(ob.name, 0.0)
        line = "default"
        if ob.name == "face":
            gg_face.material()
            face_normals(ob)
            line = "skin"
        elif k == "hair" and has_uv and os.path.exists(os.path.join(TEX_DIR, "hair_ctrl.png")):
            gg_hair_material(ob, bias)
            hair_normals(ob, proxy)
            line = "hair"
            if ob.name == "hair":
                ear_pit_outline(ob)
        elif k == "hair":
            hair_material(ob)
            hair_normals(ob, proxy)
            line = "hair" if has_uv else "default"
        elif ob.name == "neck":
            gg_flat_material(ob, SKIN_RGB, NECK_SHADE, bias)
            line = "skin"
        elif ob.name in ("ear_R", "ear_L"):
            gg_flat_material(ob, EAR_RGB, EAR_SHADE, bias)
            line = "skin"
        elif ob.name in SKIRT_RECEIVERS and has_uv and os.path.exists(os.path.join(TEX_DIR, "body_ctrl.png")):
            gg_leg_material(ob, bias, SPEC_OBJ.get(ob.name))
            line = "tex"
        elif has_uv and os.path.exists(os.path.join(TEX_DIR, "body_ctrl.png")):
            gg_tex_material(ob, bias, SPEC_OBJ.get(ob.name))
            line = "tex"
        elif ob.name == "headband":
            band_material(ob)
        elif head_only and k == "default" and ob.name not in ("clip_R", "clip_L"):
            continue
        mats = [m for m in ob.data.materials if m and m.name.startswith(("PROJ_",))]
        for m in mats:
            toonify(m, k, BIAS_OBJ.get(ob.name))
        if ob.name in NO_OUTLINE:
            mod = ob.modifiers.get("GG_outline")
            if mod is not None:
                ob.modifiers.remove(mod)
        else:
            gg_add_outline(ob, line)
        if ob.name in NORMAL_BLUR:
            blur_normals(ob, NORMAL_BLUR[ob.name])
        if ob.name in SKIRT_RECEIVERS:
            skirt_occlusion(ob)
        done.append(ob.name)
    for sc in bpy.data.scenes:
        if sc.name in (scene_name, "Scene", "REVIEW"):
            key_light(sc)
    # the eye bones drive the rebuilt face material (Milestone 7)
    if bpy.data.objects.get("CEC_rig") is not None and "face" in done:
        import rig_eyes
        importlib.reload(rig_eyes)
        rig_eyes.drivers()
    return done
