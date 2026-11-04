extends Control
## CHARACTER SELECT MOTION (Nov 2 2026), made for its theme, "Beyond the Crimson Horizon" (166 BPM, piano and
## violin, "flying over a sea of clouds at sunset"). Sits behind the renders, over the background and its light beams:
##   - embers: warm crimson / gold motes drifting up and swaying, like sparks against a sunset
##   - beat streaks: every couple of beats a quick light streak runs down one of the screen's "/" diagonals, P1 blue on
##     the left half, P2 crimson on the right, taking turns
##   - edge pulse: a soft glow on each side's outer edge on every beat, stronger at the start of each bar
## The beat follows the music itself (the BGM player's playback position) when the select theme is playing, so it
## stays in time; with no music it keeps its own clock at the same tempo.
## Everything is drawn here (no textures), on the 1920 x 1080 canvas. Settings below.

@export var bpm: float = 166.0
## Seconds into the select theme's file of its first beat (measured from the audio).
@export var beat_offset: float = 0.339
@export var theme_file: String = "beyond_the_crimson_horizon_select"
@export_range(0, 200) var ember_count: int = 48
@export var streak_every: int = 2                 ## beats between streaks
@export var pulse_strength: float = 1.0
@export var colors: Array[Color] = [Color(0.25, 0.62, 1.0), Color(1.0, 0.2, 0.36)]   ## P1 / P2
@export var ember_colors: Array[Color] = [Color(1.0, 0.42, 0.28), Color(1.0, 0.72, 0.36), Color(1.0, 0.3, 0.42)]

const CANVAS := Vector2(1920, 1080)
const DIAG := Vector2(-0.42, 1.0)   # the "/" lean of the background's lines (top right to bottom left)

var _embers: Array = []
var _streaks: Array = []
var _pulse := [0.0, 0.0]
var _beat := -1
var _clock := 0.0
var _next_side := 0
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	size = CANVAS
	_rng.randomize()
	for i in ember_count:
		_embers.append(_new_ember(true))


func _new_ember(anywhere: bool) -> Dictionary:
	var life := _rng.randf_range(5.0, 10.0)
	return {
		"pos": Vector2(_rng.randf_range(-40.0, CANVAS.x + 40.0), _rng.randf_range(0.0, CANVAS.y) if anywhere else CANVAS.y + 20.0),
		"rise": _rng.randf_range(28.0, 75.0),
		"sway": _rng.randf_range(10.0, 34.0),
		"phase": _rng.randf_range(0.0, TAU),
		"r": _rng.randf_range(1.4, 3.6),
		"age": _rng.randf_range(0.0, life) if anywhere else 0.0,
		"life": life,
		"col": ember_colors[_rng.randi() % ember_colors.size()] if not ember_colors.is_empty() else Color(1, 0.5, 0.3),
	}


## Seconds into the song: from the BGM player when the select theme is what's playing.
func _song_time(delta: float) -> float:
	_clock += delta
	var audio := get_node_or_null("/root/AudioManager")
	if audio != null:
		var player = audio.get("BGM")
		if player is AudioStreamPlayer and player.playing and player.stream != null \
				and str(player.stream.resource_path).get_file().begins_with(theme_file):
			return player.get_playback_position() + AudioServer.get_time_since_last_mix() - AudioServer.get_output_latency()
	return _clock


func _process(delta: float) -> void:
	if not is_visible_in_tree():
		return
	var per := 60.0 / maxf(bpm, 1.0)
	var t := _song_time(delta)
	var beat := int(floor((t - beat_offset) / per))
	if beat != _beat:
		if beat > _beat or beat < _beat - 4:   # (a loop of the song jumps back)
			_on_beat(beat)
		_beat = beat
	for side in 2:
		_pulse[side] = maxf(0.0, _pulse[side] - delta * 3.2)
	for e in _embers:
		e["age"] += delta
		e["pos"].y -= e["rise"] * delta
		if e["age"] >= e["life"] or e["pos"].y < -30.0:
			e.merge(_new_ember(false), true)
	for s in _streaks:
		s["t"] += delta / s["time"]
	_streaks = _streaks.filter(func(s): return s["t"] < 1.0)
	queue_redraw()


func _on_beat(beat: int) -> void:
	var bar_start := posmod(beat, 4) == 0
	for side in 2:
		_pulse[side] = maxf(_pulse[side], (1.0 if bar_start else 0.55) * pulse_strength)
	if streak_every > 0 and posmod(beat, streak_every) == 0:
		var side := _next_side
		_next_side = 1 - _next_side
		var x0 := _rng.randf_range(420.0, 980.0) if side == 0 else _rng.randf_range(1180.0, 1760.0)
		_streaks.append({"side": side, "x0": x0, "t": 0.0, "time": _rng.randf_range(0.45, 0.65),
			"len": _rng.randf_range(220.0, 360.0), "w": _rng.randf_range(1.6, 3.0)})


func _draw() -> void:
	# edge pulse: a soft glow on each side's outer edge
	for side in 2:
		var p: float = _pulse[side]
		if p <= 0.01:
			continue
		var col: Color = colors[side]
		var w := 300.0
		var x_out := 0.0 if side == 0 else CANVAS.x
		var x_in := w if side == 0 else CANVAS.x - w
		draw_polygon(PackedVector2Array([Vector2(x_out, 0), Vector2(x_in, 0), Vector2(x_in, CANVAS.y), Vector2(x_out, CANVAS.y)]),
			PackedColorArray([Color(col, 0.2 * p), Color(col, 0.0), Color(col, 0.0), Color(col, 0.2 * p)]))
	# embers
	for e in _embers:
		var life: float = e["life"]
		var age: float = e["age"]
		var a := clampf(age / 1.2, 0.0, 1.0) * clampf((life - age) / 1.5, 0.0, 1.0)
		if a <= 0.0:
			continue
		var pos: Vector2 = e["pos"] + Vector2(sin(age * 0.9 + e["phase"]) * e["sway"], 0.0)
		var col: Color = e["col"]
		var r: float = e["r"]
		draw_circle(pos, r * 3.2, Color(col, 0.08 * a))
		draw_circle(pos, r, Color(col.lightened(0.35), 0.75 * a))
	# beat streaks along the "/" diagonals
	var dir := DIAG.normalized()
	var travel := CANVAS.y / dir.y + 400.0
	for s in _streaks:
		var col: Color = colors[s["side"]]
		var t: float = s["t"]
		var ease_t := 1.0 - pow(1.0 - t, 2.2)
		var head := Vector2(s["x0"], -200.0) + dir * travel * ease_t
		var tail := head - dir * float(s["len"]) * (0.4 + 0.6 * (1.0 - t))
		var a := clampf(t / 0.12, 0.0, 1.0) * clampf((1.0 - t) / 0.35, 0.0, 1.0)
		var w: float = s["w"]
		draw_line(tail, head, Color(col, 0.22 * a), w * 5.0, true)
		draw_polyline_colors(PackedVector2Array([tail, head]), PackedColorArray([Color(col, 0.0), Color(col.lightened(0.6), 0.95 * a)]), w, true)
		draw_circle(head, w * 1.6, Color(1, 1, 1, 0.85 * a))
