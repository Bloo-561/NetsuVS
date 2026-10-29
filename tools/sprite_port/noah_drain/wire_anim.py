"""Swap the drain recoil frames of Noah's Void Grasp (81) and Void Devour (84) for the new pose + energy frames."""
import re, sys

SPR = "res://actors/noah/Sprites/v2/"
POSE_OFF = "Vector2(-236, -4)"
FX_OFF = "Vector2(-95, 245)"


def ext_lines(prefix, ids):
    out = [f'[ext_resource type="Texture2D" path="{SPR}noa_drain_end.png" id="t_drain_end"]']
    for i in ids:
        out.append(f'[ext_resource type="Texture2D" path="{SPR}{prefix}{i}.png" id="t_{prefix}{i}"]')
    return "\n".join(out) + "\n"


def blocks(frames, prefix, fx_ids):
    s = []
    for k, (at, fx) in enumerate(zip(frames, fx_ids)):
        s.append(f'[sub_resource type="Resource" id="MD{k}_0"]\nscript = ExtResource("sp")\nSprite = ExtResource("t_drain_end")\nOffset = {POSE_OFF}\n')
        s.append(f'[sub_resource type="Resource" id="MD{k}_1"]\nscript = ExtResource("sp")\nSprite = ExtResource("t_{prefix}{fx}")\nOffset = {FX_OFF}\n')
        at_line = f"AtFrame = {at}\n" if at else ""
        s.append(f'[sub_resource type="Resource" id="AD{k}"]\nscript = ExtResource("an")\n{at_line}Modifiers = [SubResource("MD{k}_0"), SubResource("MD{k}_1")]\n')
    return "\n".join(s)


def patch(path_in, path_out, old_tex_id, old_m, old_a, frames, prefix, fx_ids):
    t = open(path_in, newline="").read()
    assert "\r" not in t
    # 1. textures: drop the old recoil sprite, add the new ones after the last ext_resource
    old_ext = re.search(rf'^\[ext_resource [^\n]*id="{old_tex_id}"\]\n', t, re.M)
    assert old_ext
    t = t.replace(old_ext.group(0), "")
    last = list(re.finditer(r"^\[ext_resource [^\n]*\]\n", t, re.M))[-1]
    t = t[: last.end()] + ext_lines(prefix, sorted(set(fx_ids))) + t[last.end():]
    # 2. the old modifier + animation blocks -> the new ones
    blk = re.search(rf'\[sub_resource type="Resource" id="{old_m}"\]\n.*?\n\n\[sub_resource type="Resource" id="{old_a}"\]\n.*?\n\n', t, re.S)
    assert blk, "old blocks not found"
    assert f'ExtResource("{old_tex_id}")' in blk.group(0)
    t = t.replace(blk.group(0), blocks(frames, prefix, fx_ids) + "\n")
    # 3. animation list
    ref = f'SubResource("{old_a}")'
    assert t.count(ref) == 1
    t = t.replace(ref, ", ".join(f'SubResource("AD{k}")' for k in range(len(frames))))
    assert f'ExtResource("{old_tex_id}")' not in t
    open(path_out, "w", newline="").write(t)


src_dir, out_dir = sys.argv[1], sys.argv[2]
# Void Grasp (drain): frames 0-13, the opponent held 0.95 m in front
patch(f"{src_dir}/81_NOA_GRASP_AnimData.tres", f"{out_dir}/81_NOA_GRASP_AnimData.tres",
      "t_k_recoil", "M0_0", "A0", [0, 2, 4, 6, 8, 10, 12], "fx_drain_", [1, 2, 3, 4, 5, 6, 8])
# Void Devour (drain): frames 56-71, she was launched at 36, so the stream comes in from far away
patch(f"{src_dir}/84_NOA_DEVOUR_AnimData.tres", f"{out_dir}/84_NOA_DEVOUR_AnimData.tres",
      "t_x_recoil", "M9_0", "A9", [56, 58, 60, 62, 64, 66, 68, 70], "fx_drain_far_", [1, 2, 3, 4, 5, 6, 7, 8])
print("ok")
