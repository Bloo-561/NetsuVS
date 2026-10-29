"""Milestone 5: UV layout for the baked textures (run in Blender).

Every textured part gets a UV map "UVBake". Parts that share a texture are
unwrapped together (multi-object Smart UV Project), so their islands are
packed into one atlas at one texel density:
  body  - everything that takes the projected sheet colours (2048 px atlas)
  hair  - hair shell, bangs, skull filler, ahoge (the purple-tip mask)
The face keeps its drawn texture (face_texture.py), the neck and ears are
flat skin: no UVs needed.
Run: import runpy; runpy.run_path(r"<3d_v2>\\scripts\\uv_unwrap.py")["run"]()
"""
import math

import bpy

UV_NAME = "UVBake"
ATLAS = {
    "body": ("leg_R", "leg_L", "shoe_R", "shoe_L", "bow_R", "bow_L", "arm_R", "arm_L", "hand_R", "hand_L",
             "body", "jacket", "collar", "neckerchief", "brooch", "tie", "shirt_collar", "skirt", "lace",
             "belt_A", "belt_B", "buckle_A", "buckle_B", "kashira", "tsuka", "tsuba", "saya_mouth", "saya",
             "saya_tip", "hanger_strap", "blade", "headband", "clip_R", "clip_L"),
    "hair": ("hair", "bangs", "skull", "ahoge"),
}
ANGLE_LIMIT = math.radians(66.0)
ISLAND_MARGIN = 0.003          # UV units: 6 texels at 2048
# relative texel density of small parts seen in close-ups: their islands are
# scaled up before packing (M6: at 1.0-1.3 texels per mm the headband's
# emblem blurred into "TV"; the detail sheet draws "IV")
TEXEL_BOOST = {"headband": 3.0}


def atlas_of(name):
    for a, names in ATLAS.items():
        if name in names:
            return a
    return None


def unwrap(names):
    objs = [bpy.data.objects[n] for n in names if bpy.data.objects.get(n) is not None]
    vl = bpy.context.view_layer
    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for o in vl.objects:
        o.select_set(False)
    for o in objs:
        me = o.data
        uv = me.uv_layers.get(UV_NAME) or me.uv_layers.new(name=UV_NAME)
        me.uv_layers.active = uv
        uv.active_render = True
        o.select_set(True)
    vl.objects.active = objs[0]
    bpy.ops.object.mode_set(mode="EDIT")
    try:
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=ANGLE_LIMIT, island_margin=ISLAND_MARGIN, area_weight=0.0,
                                 correct_aspect=True, scale_to_bounds=False)
        boost = [o for o in objs if TEXEL_BOOST.get(o.name, 1.0) != 1.0]
        if boost:
            bpy.ops.object.mode_set(mode="OBJECT")
            for o in boost:
                k = TEXEL_BOOST[o.name]
                uvl = o.data.uv_layers[UV_NAME]
                a = [0.0] * (2 * len(uvl.data))
                uvl.data.foreach_get("uv", a)
                n = len(a) // 2
                cu, cv = sum(a[0::2]) / n, sum(a[1::2]) / n
                a[0::2] = [cu + (u - cu) * k for u in a[0::2]]
                a[1::2] = [cv + (v - cv) * k for v in a[1::2]]
                uvl.data.foreach_set("uv", a)
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
        # Smart UV's own packing fills ~40 % of the square; exact-shape packing
        # with rotation roughly doubles the texel density at the same size;
        # it scales all islands alike, so TEXEL_BOOST survives it
        bpy.ops.uv.select_all(action="SELECT")
        bpy.ops.uv.pack_islands(rotate=True, rotate_method="ANY", scale=True, merge_overlap=False,
                                margin_method="FRACTION", margin=ISLAND_MARGIN, shape_method="CONCAVE")
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")
    for o in objs:
        o.select_set(False)
    return [o.name for o in objs]


def run():
    return {a: unwrap(names) for a, names in ATLAS.items()}


if __name__ == "__main__":
    print(run())
