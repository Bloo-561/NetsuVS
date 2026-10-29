"""Character select: the small in-game preview now plays the fighter's real idle animation
(state 0 of its data: every sprite with its own offset and timing), and sizes it in metres, so
fighters with trimmed or high-resolution sprites (Cecilia since Oct 23) look right."""
import os, sys
PROJ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
f = os.path.join(PROJ, 'scenes', 'character_select', 'character_select.gd')
s = open(f, encoding='utf-8').read()
bk = os.path.join(PROJ, '_backup_stage_select', 'pre_sprite_port', 'character_select.gd.bak')
if not os.path.exists(bk):
    open(bk, 'w', encoding='utf-8').write(s)

def rep(old, new):
    global s
    if old not in s:
        sys.exit('patch target not found:\n' + old[:200])
    s = s.replace(old, new, 1)

rep('''## Screen pixels per sprite pixel.
@export var preview_scale: float = 0.95
## Seconds per idle frame.
@export var preview_frame_time: float = 0.1
''', '''## Screen pixels per 0.0055 m (one sprite pixel of the original 1024-canvas sprites).
@export var preview_scale: float = 0.95
## Seconds per idle frame (only for fighters whose idle animation can't be read).
@export var preview_frame_time: float = 0.1
## Metres per sprite pixel the preview size is based on.
const PREVIEW_REF_PIXEL := 0.0055
''')

rep('''		pv["time"] += delta
		if pv["time"] >= preview_frame_time:
			pv["time"] = 0.0
			pv["frame"] = (pv["frame"] + 1) % pv["frames"].size()
			_set_preview_frame(side)''', '''		pv["time"] += delta
		var hold: float = pv["frames"][pv["frame"]].get("time", preview_frame_time)
		if pv["time"] >= hold:
			pv["time"] -= hold
			pv["frame"] = (pv["frame"] + 1) % pv["frames"].size()
			_set_preview_frame(side)''')

old_look_start = s.index('## Reads how a color looks straight out of its fighter scene')
old_look_end = s.index('func _update_preview(side: int) -> void:')
s = s[:old_look_start] + '''## Reads how a color looks straight out of its fighter scene (the "Sprite"
## node under Graphics/Mesh: pixel size, color material...) without running the
## fighter, plus its idle animation (state 0 of the fighter data: each sprite with
## its own offset and how long it shows). Fighters whose data can't be read fall
## back to idle1.png, idle2.png ... next to the scene's sprite image.
func _look(fighter: int, color: int) -> Dictionary:
	var key := "%d:%d" % [fighter, color]
	if _look_cache.has(key):
		return _look_cache[key]
	var look := {"props": {}, "frames": []}   # frames: [{"tex", "offset", "time"}]
	var data = null
	var scene: PackedScene = MatchSetup.palette_scene(fighter, color)
	if scene:
		var state := scene.get_state()
		for i in state.get_node_count():
			var path := String(state.get_node_path(i))
			if path == ".":
				for j in state.get_node_property_count(i):
					if String(state.get_node_property_name(i, j)) == "Data":
						data = state.get_node_property_value(i, j)
			elif path.ends_with("Graphics/Mesh/Sprite"):
				for j in state.get_node_property_count(i):
					look["props"][String(state.get_node_property_name(i, j))] = state.get_node_property_value(i, j)
	look["frames"] = _idle_frames(data)
	if look["frames"].is_empty():
		var first = look["props"].get("texture")
		if first is Texture2D:
			var folder: String = first.resource_path.get_base_dir()
			var n := 1
			while ResourceLoader.exists("%s/idle%d.png" % [folder, n]):
				look["frames"].append({"tex": load("%s/idle%d.png" % [folder, n])})
				n += 1
			if look["frames"].is_empty():
				look["frames"].append({"tex": first})
	_look_cache[key] = look
	return look


## The idle animation of a fighter data resource: [{"tex", "offset", "time"}].
func _idle_frames(data) -> Array:
	var out: Array = []
	if data == null or not (data is Resource):
		return out
	var states = data.get("States")
	if not (states is Array) or states.is_empty() or states[0] == null:
		return out
	var anim = states[0].get("AnimationData")
	if anim == null:
		return out
	var keys = anim.get("Animations")
	if not (keys is Array):
		return out
	var dur := int(anim.get("Duration"))
	for k in keys.size():
		var mods = keys[k].get("Modifiers") if keys[k] else null
		if not (mods is Array) or mods.is_empty() or mods[0] == null or mods[0].get("Sprite") == null:
			continue
		var at := int(keys[k].get("AtFrame"))
		var nxt := int(keys[k + 1].get("AtFrame")) if k + 1 < keys.size() else dur
		out.append({"tex": mods[0].get("Sprite"), "offset": mods[0].get("Offset"), "time": maxf(1.0, float(nxt - at)) / 60.0})
	return out


''' + s[old_look_end:]

rep('''	var tex: Texture2D = pv["frames"][pv["frame"]]
	var sprite: Sprite3D = pv["sprite"]
	sprite.texture = tex''', '''	var f: Dictionary = pv["frames"][pv["frame"]]
	var tex: Texture2D = f["tex"]
	var sprite: Sprite3D = pv["sprite"]
	sprite.texture = tex
	if f.get("offset") is Vector2:
		sprite.offset = f["offset"]''')

old_cam_start = s.index('## Points the preview camera so the fighter\'s feet sit at PREVIEW_FEET_Y,')
old_cam_end = s.index('func _build_previews() -> void:')
s = s[:old_cam_start] + '''## Points the preview camera so the fighter's feet (its origin) sit at
## PREVIEW_FEET_Y, centred left-right, at `preview_scale` screen pixels per
## PREVIEW_REF_PIXEL metres, the same size for every fighter whatever its sprites.
func _frame_camera(side: int) -> void:
	var pv: Dictionary = _preview[side]
	var cam: Camera3D = pv["camera"]
	var m_per_px := PREVIEW_REF_PIXEL / preview_scale
	cam.size = PREVIEW_SIZE.y * m_per_px
	cam.position = Vector3(0.0, (PREVIEW_FEET_Y - PREVIEW_SIZE.y / 2.0) * m_per_px, 10.0)


''' + s[old_cam_end:]

open(f, 'w', encoding='utf-8').write(s)
print('patched', f)
