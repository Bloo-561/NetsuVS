class_name NetsuAnimPreview
extends Control
## Plays a fighter's (or assist's) states the way the fight draws them, from their AnimationData: every
## AnimationSettings key (AtFrame) and its SpriteModifier layers (Sprite, Offset, Scale, Rotation, FlipX / FlipY).
## Nothing is pre-rendered, so a changed animation or a new move shows up in the command list by itself.
## Moves are drawn in place (the state's movement isn't simulated).
##
##   play(anims, ref_height)   anims = [AnimationData, ...] played one after another, looping
##   still(anims, frame)       one frame, cropped and fitted (list thumbnails)
## Offsets are the bottom-left corner of the picture in sprite pixels, y up (as Sprite3D draws them).

## Fight frames per second.
const FPS := 60.0
## The most frames taken from one state (long holds and supers are cut there).
@export var max_state_frames: int = 240
## Frames the last picture stays before the loop starts again.
@export var loop_hold: int = 24
## Where the floor is, from the top (0..1 of the height).
@export var ground_ratio: float = 0.88
## The standing pose's height as a share of the box (keeps every move of a fighter at the same size).
@export var fit_ratio: float = 0.7
@export var speed: float = 1.0
@export var shadow: bool = true

var playing := false
var _stages: Array = []      # [{"start": frame, "layers": [{"tex", "rect", "rot", "fx", "fy"}]}]
var _total := 0
var _bounds := Rect2()
var _ref_height := 0.0
var _still := -1
var _t := 0.0
var _shown := -1


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	process_mode = Node.PROCESS_MODE_ALWAYS   # keeps playing while the fight is paused


func play(anims: Array, ref_height: float = 0.0) -> void:
	_compile(anims)
	_ref_height = ref_height
	_still = -1
	_t = 0.0
	_shown = -1
	playing = _total > 0
	queue_redraw()


func still(anims: Array, frame: int = -1) -> void:
	_compile(anims)
	playing = false
	_still = clampi(frame if frame >= 0 else _total / 2, 0, maxi(0, _total - 1))
	queue_redraw()


func restart() -> void:
	_t = 0.0
	_shown = -1
	queue_redraw()


func clear() -> void:
	_stages.clear()
	_total = 0
	playing = false
	queue_redraw()


func has_frames() -> bool:
	return _total > 0


## The height (sprite px) of an animation's first picture: the standing pose, used as the size reference.
static func pose_height(ad) -> float:
	var p := NetsuAnimPreview.new()
	p._compile([ad])
	var h := 0.0
	if not p._stages.is_empty():
		var r := Rect2()
		var first := true
		for l in p._stages[0]["layers"]:
			r = l["rect"] if first else r.merge(l["rect"])
			first = false
		h = r.size.y
	p.free()
	return h


func _compile(anims: Array) -> void:
	_stages.clear()
	_total = 0
	var have := false
	for ad in anims:
		if ad == null:
			continue
		var dur := mini(int(ad.get("Duration") if ad.get("Duration") != null else 0), max_state_frames)
		if dur <= 0:
			continue
		var keys: Array = []
		for st in (ad.get("Animations") if ad.get("Animations") != null else []):
			if st != null:
				keys.append(st)
		keys.sort_custom(func(a, b): return int(a.get("AtFrame")) < int(b.get("AtFrame")))
		for st in keys:
			var at := int(st.get("AtFrame"))
			if at >= dur:
				continue
			var layers: Array = []
			for m in (st.get("Modifiers") if st.get("Modifiers") != null else []):
				if m == null or m.get("Sprite") == null or bool(m.get("OnlyOnContact")):
					continue
				var tex: Texture2D = m.get("Sprite")
				var sc: Vector2 = m.get("Scale") if m.get("Scale") != null else Vector2.ONE
				var off: Vector2 = m.get("Offset") if m.get("Offset") != null else Vector2.ZERO
				var size := tex.get_size() * Vector2(absf(sc.x), absf(sc.y))
				var rect := Rect2(Vector2(off.x * sc.x, -(off.y * sc.y) - size.y), size)
				layers.append({"tex": tex, "rect": rect, "rot": deg_to_rad(float(m.get("Rotation"))),
					"fx": bool(m.get("FlipX")), "fy": bool(m.get("FlipY"))})
				_bounds = rect if not have else _bounds.merge(rect)
				have = true
			_stages.append({"start": _total + at, "layers": layers})
		_total += dur


func _process(delta: float) -> void:
	if not playing or _total <= 0 or not is_visible_in_tree():
		return
	_t += delta * FPS * speed
	var f := int(_t) % (_total + loop_hold)
	if f != _shown:
		_shown = f
		queue_redraw()


func _layers_at(frame: int) -> Array:
	var out: Array = []
	for s in _stages:
		if s["start"] <= frame:
			out = s["layers"]
		else:
			break
	return out


func _draw() -> void:
	if _total <= 0:
		return
	var frame := _still if _still >= 0 else mini(maxi(_shown, 0), _total - 1)
	var layers := _layers_at(frame)
	if layers.is_empty():
		return
	var k := 1.0
	var origin := Vector2.ZERO
	if _still >= 0:
		# a thumbnail: this picture alone, cropped and fitted
		var r: Rect2 = layers[0]["rect"]
		for l in layers:
			r = r.merge(l["rect"])
		k = minf(size.x / maxf(r.size.x, 1.0), size.y / maxf(r.size.y, 1.0)) * 0.94
		origin = size / 2.0 - (r.position + r.size / 2.0) * k
	else:
		var ground := size.y * ground_ratio
		k = minf(size.x * 0.94 / maxf(_bounds.size.x, 1.0), ground * 0.96 / maxf(-_bounds.position.y, 1.0))
		if _bounds.end.y > 0.0:
			k = minf(k, (size.y - ground) / _bounds.end.y)
		if _ref_height > 0.0:
			k = minf(k, size.y * fit_ratio / _ref_height)
		origin = Vector2(size.x / 2.0 - (_bounds.position.x + _bounds.size.x / 2.0) * k, ground)
		if shadow:
			var radius := (0.2 * _ref_height if _ref_height > 0.0 else 0.25 * _bounds.size.x) * k
			draw_set_transform(Vector2(origin.x, ground), 0.0, Vector2(1.0, 0.2))
			draw_circle(Vector2.ZERO, radius, Color(0, 0, 0, 0.3))
	for l in layers:
		var rect: Rect2 = l["rect"]
		var center: Vector2 = origin + (rect.position + rect.size / 2.0) * k
		var flip := Vector2(-1.0 if l["fx"] else 1.0, -1.0 if l["fy"] else 1.0)
		draw_set_transform(center, l["rot"], flip)
		var s: Vector2 = rect.size * k
		draw_texture_rect(l["tex"], Rect2(-s / 2.0, s), false)
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
