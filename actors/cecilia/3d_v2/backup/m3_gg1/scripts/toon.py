"""GG-style cel-shading preview (run in Blender, after projection.apply()).

A first look at the Guilty Gear style ahead of Milestone 6 (which tunes it):
  - every PROJ_ material's colour goes through a 2-tone ramp from one sun
    (the key light): lit = the colour, shadow = colour x a shadow tint
    (warm for skin); hard edge, cast shadows on (the bangs shade the face);
  - the face's shading normals point away from a point inside the head
    (Normal Edit, radial), the usual anime trick: one clean shadow shape
    across the face instead of the noise of every bump;
  - inverted-hull outlines (Solidify, flipped, back-face culled) in a dark
    tint of each part.
Run: import runpy; runpy.run_path(r"<3d_v2>\\scripts\\toon.py")["apply"]()
"""
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

KEY_DIR = Vector((-0.45, -0.75, 0.55))        # towards the light: her right-front, above
KEY_ANGLE = math.radians(1.0)                 # sun disc: near-hard shadows
RAMP_POS = 0.15                               # light/shadow threshold on the diffuse term (~ cos of the angle to the light)
SHADOW = {"skin": (0.86, 0.68, 0.66), "hair": (0.55, 0.50, 0.66), "default": (0.62, 0.60, 0.70)}
SKIN_PARTS = ("face", "neck", "ear_R", "ear_L")
HAIR_PARTS = ("hair", "bangs", "skull", "ahoge")
OUTLINE_W = 0.0016                            # m
OUTLINE = {"skin": (0.32, 0.16, 0.14), "hair": (0.05, 0.04, 0.07), "default": (0.06, 0.05, 0.07)}
FACE_NORMAL_CENTRE = (0.0, 0.035, 1.395)      # inside the head, behind the face


def kind(name):
    if name in SKIN_PARTS:
        return "skin"
    if name in HAIR_PARTS:
        return "hair"
    return "default"


def key_light(scene):
    ob = bpy.data.objects.get("GG_Key")
    if ob is None:
        ob = bpy.data.objects.new("GG_Key", bpy.data.lights.new("GG_Key", "SUN"))
    if scene.collection.objects.get(ob.name) is None:
        scene.collection.objects.link(ob)
    ob.data.energy = math.pi                      # white diffuse then reads cos(angle) through Shader to RGB
    ob.data.angle = KEY_ANGLE
    ob.data.use_shadow = True
    ob.rotation_euler = KEY_DIR.normalized().to_track_quat("Z", "Y").to_euler()
    return ob


def toon_group():
    """node group: Color in -> toon colour out (lit / shadow by a hard ramp)"""
    g = bpy.data.node_groups.get("GG_Toon")
    if g is not None:
        bpy.data.node_groups.remove(g)
    g = bpy.data.node_groups.new("GG_Toon", "ShaderNodeTree")
    g.interface.new_socket("Color", in_out="INPUT", socket_type="NodeSocketColor")
    g.interface.new_socket("Shadow", in_out="INPUT", socket_type="NodeSocketColor")
    g.interface.new_socket("Color", in_out="OUTPUT", socket_type="NodeSocketColor")
    N, L = g.nodes.new, g.links.new
    gin, gout = N("NodeGroupInput"), N("NodeGroupOutput")
    dif = N("ShaderNodeBsdfDiffuse")
    dif.inputs["Color"].default_value = (1, 1, 1, 1)
    s2r = N("ShaderNodeShaderToRGB")
    L(dif.outputs[0], s2r.inputs[0])
    bw = N("ShaderNodeRGBToBW")
    L(s2r.outputs["Color"], bw.inputs[0])
    ramp = N("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].position = RAMP_POS
    ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    L(bw.outputs[0], ramp.inputs[0])
    shade = N("ShaderNodeMix")
    shade.data_type = "RGBA"
    shade.blend_type = "MULTIPLY"
    shade.inputs["Factor"].default_value = 1.0
    L(gin.outputs[0], shade.inputs[6])
    L(gin.outputs[1], shade.inputs[7])
    mix = N("ShaderNodeMix")
    mix.data_type = "RGBA"
    L(ramp.outputs["Color"], mix.inputs["Factor"])
    L(shade.outputs[2], mix.inputs[6])
    L(gin.outputs[0], mix.inputs[7])
    L(mix.outputs[2], gout.inputs[0])
    return g


def toonify(mat, k):
    """insert GG_Toon between a PROJ material's colour and its emission"""
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
    nt.links.new(grp.outputs[0], em.inputs["Color"])
    return True


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
    return mod


def apply(scene_name="HEADREVIEW"):
    toon_group()
    done = []
    for ob in bpy.data.collections["MODEL"].all_objects:
        if ob.type != "MESH":
            continue
        k = kind(ob.name)
        mats = [m for m in ob.data.materials if m and m.name.startswith("PROJ_")]
        for m in mats:
            toonify(m, k)
        if ob.name == "face":
            face_normals(ob)
        add_outline(ob, k)
        done.append(ob.name)
    for sc in bpy.data.scenes:
        if sc.name in (scene_name, "Scene", "REVIEW"):
            key_light(sc)
            ee = sc.eevee
            if hasattr(ee, "use_shadows"):
                ee.use_shadows = True
            if hasattr(ee, "shadow_ray_count"):
                ee.shadow_ray_count = 1
            if hasattr(ee, "shadow_step_count"):
                ee.shadow_step_count = 6
    return done
