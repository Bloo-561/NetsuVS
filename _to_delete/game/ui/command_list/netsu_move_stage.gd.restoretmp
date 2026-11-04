class_name NetsuMoveStage
extends Control
## The command list's preview (Nov 2 2026): the move played out against an opponent (NetsuMoveSim) in front of
## Thor's Hall, the real 3D stage, rendered in a SubViewport by a camera that follows the two fighters at the
## fight's angle (30° field of view, level, like FighterCamera). Sprites are drawn from the states' AnimationData
## at the fight's size: 1 sprite pixel = 0.00275 m (the fighters' Sprite3D pixel_size) x the fighter's NetsuScale.
##
##   show_sim(sim)        plays the recorded frames, looping
##   restart()            from the start
## Until the stage has loaded (on a thread) a plain gradient shows behind.

const STAGE_PATH := "res://stages/thors_hall_3d/thors_hall_3d.tscn"
const UNIT_PX := 27.5               # sprite pixels -> engine units (0.00275 m x 10000)
const FOV := 30.0
const FPS := 60.0
@export var ground_ratio: float = 0.84
## Metres shown top to bottom when they're close together on the ground.
@export var min_view_height: float = 3.3
@export var loop_hold: int = 30
@export var speed: float = 1.0

var playing := false
var _frames: Array = []
var _cams: Array = []               # per frame: Vector2(centre x in units, view height in metres)
var _t := 0.0
var _shown := -1
var _layer: Control
var _bg: TextureRect
var _vp: SubViewport
var _cam: Camera3D
var _stage_pending := false
static var _anim_cache := {}        # AnimationData -> {"stages": [{"start", "layers"}], "duration"}


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	clip_contents = true
	_vp = SubViewport.new()
	_vp.own_world_3d = true
	_vp.size = Vector2i(maxi(16, int(size.x)), maxi(16, int(size.y)))
	_vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	_vp.msaa_3d = Viewport.MSAA_2X
	add_child(_vp)
	_cam = Camera3D.new()
	_cam.fov = FOV
	_cam.current = true
	_vp.add_child(_cam)
	_bg = TextureRect.new()
	_bg.texture = _vp.get_texture()
	_bg.size = size
	_bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_bg.visible = false
	add_child(_bg)
	_layer = Control.new()
	_layer.size = size
	_layer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_layer.draw.connect(_draw_layer)
	add_child(_layer)
	resized.connect(_on_resized)
	_load_stage()


func _draw() -> void:
	# behind the stage (shown until it has loaded, or if it's missing): a dim hall-coloured gradient and a floor line
	var top := Color(0.16, 0.13, 0.13)
	var bottom := Color(0.32, 0.26, 0.24)
	var g := size.y * ground_ratio
	draw_polygon(PackedVector2Array([Vector2.ZERO, Vector2(size.x, 0), Vector2(size.x, g), Vector2(0, g)]),
		PackedColorArray([top, top, bottom, bottom]))
	draw_rect(Rect2(0, g, size.x, size.y - g), Color(0.22, 0.2, 0.22))
	draw_line(Vector2(0, g), Vector2(size.x, g), Color(1, 1, 1, 0.12), 1.0)


func _on_resized() -> void:
	if _vp:
		_vp.size = Vector2i(maxi(16, int(size.x)), maxi(16, int(size.y)))
		_bg.size = size
		_layer.size = size
		queue_redraw()


func _load_stage() -> void:
	if not ResourceLoader.exists(STAGE_PATH):
		return
	if ResourceLoader.has_cached(STAGE_PATH):
		_add_stage(load(STAGE_PATH))
	else:
		ResourceLoader.load_threaded_request(STAGE_PATH)
		_stage_pending = true


func _add_stage(scene: PackedScene) -> void:
	if scene == null:
		return
	_vp.add_child(scene.instantiate())
	_bg.visible = true
	_vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS if is_visible_in_tree() else SubViewport.UPDATE_DISABLED


func show_sim(sim: NetsuMoveSim) -> void:
	_frames = sim.frames if sim != null else []
	_build_cams()
	_t = 0.0
	_shown = -1
	playing = not _frames.is_empty()
	_place_camera(0)
	_layer.queue_redraw()


func clear() -> void:
	_frames = []
	playing = false
	_layer.queue_redraw()


func restart() -> void:
	_t = 0.0
	_shown = -1


## The camera for each frame: centred on both fighters, pulled back when they're far apart or high up, smoothed.
func _build_cams() -> void:
	_cams.clear()
	var aspect := size.x / maxf(size.y, 1.0)
	var cx := 0.0
	var vh := min_view_height
	for i in _frames.size():
		var lo := INF
		var hi := -INF
		var top := 0.0
		for a in _frames[i]["actors"]:
			if not a["fighter"]:
				continue
			var p: Vector2i = a["pos"]
			lo = minf(lo, p.x - 9000.0)
			hi = maxf(hi, p.x + 9000.0)
			top = maxf(top, p.y + 19000.0 * a["scale"])
		if lo == INF:
			lo = -10000.0
			hi = 10000.0
		var want_h := maxf(min_view_height, top / 10000.0 / (ground_ratio * 0.95))
		want_h = maxf(want_h, (hi - lo) / 10000.0 / (aspect * 0.92))
		var want_x := (lo + hi) / 2.0
		var pz: Dictionary = _frames[i].get("pause", {})
		if not pz.is_empty():
			# EX / super pause: the camera closes in on her (FighterCamera NetsuZoom...)
			var pp: Vector2i = pz["pos"]
			want_x = pp.x
			want_h = min_view_height * (0.72 if pz["super"] else 0.82)
		if i == 0:
			cx = want_x
			vh = want_h
		else:
			var fast: bool = not pz.is_empty() or _frames[i - 1].has("pause")
			cx = lerpf(cx, want_x, 0.25 if fast else 0.12)
			vh = lerpf(vh, want_h, 0.25 if fast else (0.08 if want_h < vh else 0.2))
		_cams.append(Vector2(cx, vh))


func _place_camera(i: int) -> void:
	if _cams.is_empty():
		return
	var c: Vector2 = _cams[clampi(i, 0, _cams.size() - 1)]
	var h := c.y
	var dist := h / (2.0 * tan(deg_to_rad(FOV / 2.0)))
	_cam.position = Vector3(c.x / 10000.0, (ground_ratio - 0.5) * h, dist)
	_cam.rotation = Vector3.ZERO


func _process(delta: float) -> void:
	if _stage_pending:
		var st := ResourceLoader.load_threaded_get_status(STAGE_PATH)
		if st == ResourceLoader.THREAD_LOAD_LOADED:
			_stage_pending = false
			_add_stage(ResourceLoader.load_threaded_get(STAGE_PATH))
		elif st == ResourceLoader.THREAD_LOAD_FAILED or st == ResourceLoader.THREAD_LOAD_INVALID_RESOURCE:
			_stage_pending = false
	if _vp and _bg.visible:
		_vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS if is_visible_in_tree() else SubViewport.UPDATE_DISABLED
	if not playing or _frames.is_empty() or not is_visible_in_tree():
		return
	_t += delta * FPS * speed
	var f := int(_t) % (_frames.size() + loop_hold)
	if f != _shown:
		_shown = f
		_place_camera(mini(f, _frames.size() - 1))
		_layer.queue_redraw()


## Where the engine draws a sprite layer (AnimationViewer.ViewAnimations: the Sprite3D gets the layer's Offset and
## Scale, then RotationDegrees.z, which turns it around the fighter's FEET; FlipX / FlipY flip the picture in place;
## facing left mirrors the whole thing). Maps the layer's own rect (l["rect"], sprite pixels, y down, feet at 0,0)
## to the screen: `origin` = the feet on screen, `px` = screen pixels per sprite pixel, side = 1 / -1.
## Nov 2: was turning each layer around its own middle, so tumbling hit reactions (drawn below the feet and turned
## 150 degrees) showed under the floor.
## Nov 2: the EX / super pause, as in a match: the stage goes dark (darker for a super), a glow behind her and the
## cut-in band (EX CRAFT / S-CRAFT and the move's name) behind the fighters...
func _draw_pause_back(L: Control, pz: Dictionary, ox: float, ground: float, k: float) -> void:
	var t: float = float(pz["t"])
	var n: float = maxf(1.0, float(pz["n"]))
	var fade := clampf(t / 6.0, 0.0, 1.0) * clampf((n - t) / 8.0, 0.0, 1.0)
	var is_super: bool = pz["super"]
	L.draw_rect(Rect2(Vector2.ZERO, size), Color(0.0, 0.01, 0.05, (0.72 if is_super else 0.55) * fade))
	var p: Vector2i = pz["pos"]
	var at := Vector2(ox + p.x * k, ground - (p.y + 8000) * k)
	var col := Color(1.0, 0.35, 0.45) if is_super else Color(0.4, 0.75, 1.0)
	for j in 5:
		L.draw_circle(at, (1.0 - j * 0.18) * 1.1 * size.y * 0.32, Color(col, 0.07 * fade))
	# the cut-in band behind the fighters (as in a match): slides in, holds, slides out
	var slide := clampf(t / 7.0, 0.0, 1.0)
	var out := clampf((n - t) / 7.0, 0.0, 1.0)
	var a := minf(slide, out)
	if a <= 0.0:
		return
	var h := size.y * 0.2
	var cy := size.y * 0.66
	var off := (1.0 - slide) * -size.x * 0.4 + (1.0 - out) * size.x * 0.4
	var sl := h * 0.5
	var band := PackedVector2Array([Vector2(off - sl, cy - h / 2 + sl * 0.2), Vector2(size.x + off + sl, cy - h / 2 - sl * 0.2),
		Vector2(size.x + off + sl, cy + h / 2 - sl * 0.2), Vector2(off - sl, cy + h / 2 + sl * 0.2)])
	L.draw_colored_polygon(band, Color(0.02, 0.03, 0.1, 0.82 * a))
	L.draw_line(band[0], band[1], Color(col, a), 3.0, true)
	L.draw_line(band[3], band[2], Color(col, 0.6 * a), 2.0, true)
	var font := NetsuUI.sans(1, true)
	var tag := "S-CRAFT" if is_super else "EX CRAFT"
	var ts := int(h * 0.22)
	var ns := int(h * 0.42)
	var move_title := str(pz.get("name", "")).to_upper()
	var x := size.x * 0.1 + off
	L.draw_string(font, Vector2(x, cy - h * 0.12), tag, HORIZONTAL_ALIGNMENT_LEFT, -1, ts, Color(col.lightened(0.3), a))
	if move_title != "":
		L.draw_string_outline(font, Vector2(x, cy + h * 0.3), move_title, HORIZONTAL_ALIGNMENT_LEFT, -1, ns, 6, Color(0, 0, 0.05, 0.8 * a))
		L.draw_string(font, Vector2(x, cy + h * 0.3), move_title, HORIZONTAL_ALIGNMENT_LEFT, -1, ns, Color(1, 1, 1, a))


## ...and in front of her, a flash of light as it starts.
func _draw_pause_front(L: Control, pz: Dictionary, ox: float, ground: float, k: float) -> void:
	var t: float = float(pz["t"])
	var p: Vector2i = pz["pos"]
	var at := Vector2(ox + p.x * k, ground - (p.y + 8000) * k)
	if t < 8.0:
		var f := 1.0 - t / 8.0
		L.draw_circle(at, size.y * (0.08 + 0.5 * (1.0 - f)), Color(1, 1, 1, 0.55 * f))


static func layer_xform(l: Dictionary, origin: Vector2, px: float, side: int) -> Transform2D:
	var th: float = l["rot"]   # radians, counter-clockwise (the engine's y is up)
	var c := cos(th)
	var sn := sin(th)
	var xf := Transform2D(Vector2(side * px * c, -px * sn), Vector2(side * px * sn, px * c), origin)
	if l["fx"] or l["fy"]:
		var r: Rect2 = l["rect"]
		var mid := r.position + r.size / 2.0
		var flip := Transform2D(0.0, Vector2(-1.0 if l["fx"] else 1.0, -1.0 if l["fy"] else 1.0), 0.0, Vector2.ZERO)
		xf = xf * Transform2D(0.0, Vector2.ONE, 0.0, mid) * flip * Transform2D(0.0, Vector2.ONE, 0.0, -mid)
	return xf


## A layer's drawn bounds around the feet, in sprite pixels (y down), facing right, rotation included.
static func layer_bounds(l: Dictionary) -> Rect2:
	var xf := layer_xform(l, Vector2.ZERO, 1.0, 1)
	var r: Rect2 = l["rect"]
	var out := Rect2(xf * r.position, Vector2.ZERO)
	for q in [Vector2(r.end.x, r.position.y), r.end, Vector2(r.position.x, r.end.y)]:
		out = out.expand(xf * q)
	return out


static func compiled(ad) -> Dictionary:
	if _anim_cache.has(ad):
		return _anim_cache[ad]
	var out := {"stages": [], "duration": maxi(1, int(ad.get("Duration") if ad.get("Duration") != null else 1))}
	var keys: Array = []
	for st in (ad.get("Animations") if ad.get("Animations") != null else []):
		if st != null:
			keys.append(st)
	keys.sort_custom(func(a, b): return int(a.get("AtFrame")) < int(b.get("AtFrame")))
	for st in keys:
		var layers: Array = []
		for m in (st.get("Modifiers") if st.get("Modifiers") != null else []):
			if m == null or m.get("Sprite") == null or bool(m.get("OnlyOnContact")):
				continue
			var tex: Texture2D = m.get("Sprite")
			var sc: Vector2 = m.get("Scale") if m.get("Scale") != null else Vector2.ONE
			var off: Vector2 = m.get("Offset") if m.get("Offset") != null else Vector2.ZERO
			var sz := tex.get_size() * Vector2(absf(sc.x), absf(sc.y))
			layers.append({"tex": tex, "rect": Rect2(Vector2(off.x * sc.x, -(off.y * sc.y) - sz.y), sz),
				"rot": deg_to_rad(float(m.get("Rotation"))), "fx": bool(m.get("FlipX")), "fy": bool(m.get("FlipY"))})
		out["stages"].append({"start": int(st.get("AtFrame")), "layers": layers})
	_anim_cache[ad] = out
	return out


func _draw_layer() -> void:
	var L := _layer
	if _frames.is_empty():
		return
	var i := mini(maxi(_shown, 0), _frames.size() - 1)
	var snap: Dictionary = _frames[i]
	var c: Vector2 = _cams[i] if i < _cams.size() else Vector2(0, min_view_height)
	var k := size.y / c.y / 10000.0          # screen px per engine unit
	var ground := size.y * ground_ratio
	var ox := size.x / 2.0 - c.x * k
	var pz: Dictionary = snap.get("pause", {})
	if not pz.is_empty():
		_draw_pause_back(L, pz, ox, ground, k)
	# shadows first
	for a in snap["actors"]:
		if not a["fighter"]:
			continue
		var p: Vector2i = a["pos"]
		var r: float = 4200.0 * a["scale"] * k
		L.draw_set_transform(Vector2(ox + p.x * k, ground), 0.0, Vector2(1.0, 0.18))
		L.draw_circle(Vector2.ZERO, r, Color(0, 0, 0, 0.32 * clampf(1.0 - p.y / 30000.0, 0.2, 1.0)))
	L.draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	for a in snap["actors"]:
		var ad = a["ad"]
		if ad == null:
			continue
		var comp := compiled(ad)
		var layers: Array = []
		for s in comp["stages"]:
			if s["start"] <= a["frame"]:
				layers = s["layers"]
			else:
				break
		var p: Vector2i = a["pos"]
		var side: int = a["side"]
		var unit: float = UNIT_PX * a["scale"]
		var shake := (2.0 if (i % 2 == 0) else -2.0) if a["shake"] else 0.0
		var tint := Color(1.0, 0.72, 0.72) if a["flash"] else Color.WHITE
		var feet := Vector2(ox + p.x * k + shake, ground - p.y * k)
		for l in layers:
			L.draw_set_transform_matrix(layer_xform(l, feet, unit * k, side))
			L.draw_texture_rect(l["tex"], l["rect"], false, tint)
	L.draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	if not pz.is_empty():
		_draw_pause_front(L, pz, ox, ground, k)
	# hit sparks
	for sp in snap["sparks"]:
		var sp_pos: Vector2i = sp["pos"]
		var at := Vector2(ox + sp_pos.x * k, ground - sp_pos.y * k)
		var age: int = sp["age"]
		var big: bool = sp["big"]
		var r: float = (10.0 + age * (5.0 if big else 3.5)) * (k * 10000.0 / 160.0)
		var alpha := clampf(1.0 - age / 14.0, 0.0, 1.0)
		L.draw_arc(at, r, 0.0, TAU, 32, Color(1.0, 0.95, 0.7, alpha), 3.0, true)
		for n in 8:
			var d := Vector2.RIGHT.rotated(n * TAU / 8.0 + 0.3)
			L.draw_line(at + d * r * 0.4, at + d * r * 1.25, Color(1.0, 1.0, 1.0, alpha), 2.0, true)
		if age < 3:
			L.draw_circle(at, r * 0.55, Color(1, 1, 1, 0.85))
