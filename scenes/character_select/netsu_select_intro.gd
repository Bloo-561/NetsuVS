extends CanvasLayer
## CHARACTER SELECT INTRO (Nov 2 2026), after Under Night In-Birth II's select intro: before the menu, the fighters'
## full art cuts in one after another, alternating left and right sides, and the menu opens on the 4th beat.
## Timed to the select theme ("Beyond the Crimson Horizon", 166 BPM, TamaDeez's edit): it reads the music's playback
## position, so every cut lands on the beat.
##   0 - 0.34 s        dark, a light burst builds from the centre
##   beat 1 (0.34 s)   the first fighter slams in on the left (blue panel), then a cut every half beat, swapping sides
##                     (blue panel on the left, crimson on the right), through the roster in order
##   beat 4 (1.42 s)   the last art flies off, a flash, the select screen is revealed (`revealed`)
## The fighters come from `fighters` (set by the select screen before adding this): [{tex, name, zoom, anchor}].
## Not played when the select theme is already running (back from the stage select).
## It's a CanvasLayer above the screen; it eats input until the reveal and frees itself after it.

signal revealed

@export var bpm: float = 166.0
@export var beat_offset: float = 0.339       ## seconds into the theme's file of its first beat
@export var reveal_beat: int = 3             ## 0-based: 3 = the 4th beat, 1.42 s
@export var cuts_per_beat: int = 2           ## 2 = a new fighter every half beat (6 cuts before the reveal)
@export var theme_file: String = "beyond_the_crimson_horizon_select"
@export var colors: Array[Color] = [Color(0.18, 0.55, 1.0), Color(1.0, 0.16, 0.3)]
## If the music hasn't started this long after the screen opened, the intro runs on its own clock.
@export var music_wait: float = 1.2
## Width of a render on the 1920 canvas (zoom 1), and where its top sits.
@export var render_width: float = 1000.0
@export var render_top: float = -10.0

const CANVAS := Vector2(1920, 1080)
const LEAN := 0.42          # the panels' seam leans "/" (x shift per pixel down)
const OUT_TIME := 0.3       # after the reveal

## [{"tex": Texture2D, "name": String, "zoom": float, "anchor": Vector2}]
var fighters: Array = []

var _draw_node: Control
var _font: Font
var _waited := 0.0
var _own_clock := -1.0
var _t := -1.0
var _done := false


func _ready() -> void:
	layer = 20
	_font = NetsuUI.sans(10, true)
	_draw_node = Control.new()
	_draw_node.size = CANVAS
	_draw_node.mouse_filter = Control.MOUSE_FILTER_STOP
	_draw_node.draw.connect(_draw_intro)
	add_child(_draw_node)
	get_viewport().size_changed.connect(_fit)
	_fit()


func _fit() -> void:
	var view := get_viewport().get_visible_rect().size
	var k := view.x / CANVAS.x
	_draw_node.scale = Vector2(k, k)
	_draw_node.position = Vector2(0, (view.y - CANVAS.y * k) / 2.0)


func _beat_time(i: float) -> float:
	return beat_offset + i * 60.0 / bpm


func _music_time() -> float:
	var audio := get_node_or_null("/root/AudioManager")
	if audio == null:
		return -1.0
	var player = audio.get("BGM")
	if player is AudioStreamPlayer and player.playing and player.stream != null \
			and str(player.stream.resource_path).get_file().begins_with(theme_file):
		return player.get_playback_position() + AudioServer.get_time_since_last_mix() - AudioServer.get_output_latency()
	return -1.0


func _process(delta: float) -> void:
	var m := _music_time()
	if m >= 0.0 and _own_clock < 0.0:
		_t = m
	else:
		_waited += delta
		if _own_clock >= 0.0:
			_own_clock += delta
			_t = _own_clock
		elif _waited >= music_wait:
			_own_clock = 0.0
			_t = 0.0
	var reveal := _beat_time(reveal_beat)
	if not _done and _t >= reveal:
		_done = true
		_draw_node.mouse_filter = Control.MOUSE_FILTER_IGNORE
		revealed.emit()
	if _t >= reveal + OUT_TIME + 0.05:
		queue_free()
		return
	_draw_node.queue_redraw()


func _input(event: InputEvent) -> void:
	if not _done and (event is InputEventKey or event is InputEventJoypadButton or event is InputEventJoypadMotion or event is InputEventMouseButton):
		get_viewport().set_input_as_handled()   # nothing can be picked while it's covered


static func _ease_out(x: float) -> float:
	x = clampf(x, 0.0, 1.0)
	return 1.0 - pow(1.0 - x, 3.0)


static func _ease_in(x: float) -> float:
	x = clampf(x, 0.0, 1.0)
	return x * x


## Everything on one side of the "/" seam through (cx, 540), moved by `shift`.
func _panel(side: int, cx: float, shift: Vector2) -> PackedVector2Array:
	var top := cx + LEAN * 540.0
	var bottom := cx - LEAN * 540.0
	var far := -400.0 if side == 0 else CANVAS.x + 400.0
	var pts := PackedVector2Array([Vector2(far, -20), Vector2(top, -20), Vector2(bottom, CANVAS.y + 20), Vector2(far, CANVAS.y + 20)])
	for i in pts.size():
		pts[i] += shift
	return pts


## The render's rect with its centre column at x = cx (zoom around its anchor, as the select screen does).
func _render_rect(f: Dictionary, cx: float, grow: float) -> Rect2:
	var tex: Texture2D = f["tex"]
	var sz := tex.get_size()
	var base := Vector2(render_width, render_width * sz.y / sz.x) * grow
	var tl := Vector2(cx - base.x / 2.0, render_top)
	var zoom := float(f.get("zoom", 1.0))
	if zoom != 1.0:
		var anchor: Vector2 = f.get("anchor", Vector2(0.5, 0.1))
		tl -= anchor * base * (zoom - 1.0)
	return Rect2(tl, base * zoom)


func _draw_intro() -> void:
	var c := _draw_node
	var t := _t
	var navy := Color(0.02, 0.03, 0.11)
	var reveal := _beat_time(reveal_beat)
	var away := _ease_out((t - reveal) / OUT_TIME) if t > reveal else 0.0
	# the dark backdrop, fading out after the reveal
	c.draw_rect(Rect2(Vector2.ZERO, CANVAS), Color(navy, 1.0 - away))
	if t < 0.0:
		return
	var b0 := _beat_time(0)
	var step := 60.0 / bpm / float(maxi(cuts_per_beat, 1))
	# before the first beat: a light burst building in the centre
	if t < b0:
		var k := clampf(t / b0, 0.0, 1.0)
		for i in 6:
			var r := (80.0 + 520.0 * k) * (1.0 - i * 0.14)
			c.draw_circle(CANVAS / 2.0, r, Color(0.75, 0.82, 1.0, 0.05 + 0.06 * k))
		c.draw_rect(Rect2(0, CANVAS.y / 2.0 - 3, CANVAS.x, 6), Color(1, 1, 1, 0.5 * k))
	var cut := int(floor((t - b0) / step)) if t >= b0 else -1
	var last_cut := int(round((reveal - b0) / step)) - 1
	cut = mini(cut, last_cut)
	if cut >= 0:
		var since := t - b0 - cut * step   # time into this cut
		var side := cut % 2
		var s := -1.0 if side == 0 else 1.0
		var col: Color = colors[side]
		var slam := _ease_out(since / 0.09)
		# the side's panel: sweeps in from its own edge, the seam just past the middle
		var seam := CANVAS.x / 2.0 - s * 60.0
		var panel_off := Vector2(s * 700.0 * (1.0 - slam) + s * 1600.0 * away, 0)
		var pts := _panel(side, seam, panel_off)
		var lit := navy.lerp(col, 0.55)
		var deep := navy.lerp(col, 0.2)
		c.draw_polygon(pts, PackedColorArray([navy, lit, deep, navy]))
		c.draw_line(pts[1], pts[2], Color(col.lightened(0.5), 0.9), 5.0, true)
		# the other side stays dark, with a thin line of its colour along the seam
		var other := _panel(1 - side, seam + s * 40.0, Vector2(-s * 1600.0 * away, 0))
		c.draw_line(other[1], other[2], Color(colors[1 - side], 0.5), 2.0, true)
		if not fighters.is_empty():
			var f: Dictionary = fighters[cut % fighters.size()]
			# the name, huge and faint, across the dark side
			var name_size := 190
			var label := String(f.get("name", "")).to_upper()
			var name_x := (CANVAS.x * 0.75 if side == 0 else CANVAS.x * 0.25) - _font.get_string_size(label, HORIZONTAL_ALIGNMENT_LEFT, -1, name_size).x / 2.0
			var name_drift := -s * 60.0 * since / step
			c.draw_string(_font, Vector2(name_x + name_drift, CANVAS.y / 2.0 + 70), label, HORIZONTAL_ALIGNMENT_LEFT, -1, name_size,
				Color(col.lightened(0.3), 0.16 * slam * (1.0 - away)))
			# the art: slams in from its edge, then drifts slowly toward the middle
			var cx := CANVAS.x * (0.3 if side == 0 else 0.7)
			cx += s * (420.0 * (1.0 - slam) - 40.0 * since / step) + s * 900.0 * away
			var rect := _render_rect(f, cx, 1.0)
			# a big faint ghost trailing it while it lands
			if slam < 1.0:
				var ghost := _render_rect(f, cx + s * 160.0, 1.12)
				c.draw_texture_rect(f["tex"], ghost, false, Color(col.lightened(0.4), 0.35 * (1.0 - slam)))
			c.draw_texture_rect(f["tex"], rect, false, Color(1, 1, 1, clampf(since / 0.03, 0.0, 1.0) * (1.0 - away)))
			# a white flash on the art as it lands
			var hit := clampf(1.0 - since / 0.1, 0.0, 1.0)
			if hit > 0.0:
				c.draw_texture_rect(f["tex"], rect, false, Color(1.6, 1.6, 1.8, 0.55 * hit))
		# a sharp light slash along the seam on each cut
		var sl := clampf(1.0 - since / 0.12, 0.0, 1.0)
		if sl > 0.0:
			c.draw_line(pts[1], pts[2], Color(1, 1, 1, 0.9 * sl), 14.0 * sl + 2.0, true)
	# flashes: each beat (small, bigger on the first), the reveal (big)
	var flash := 0.0
	for i in reveal_beat:
		var bt := _beat_time(i)
		if t >= bt:
			flash = maxf(flash, (0.35 if i == 0 else 0.14) * clampf(1.0 - (t - bt) / 0.12, 0.0, 1.0))
	if t >= reveal:
		flash = maxf(flash, 0.5 * clampf(1.0 - (t - reveal) / 0.25, 0.0, 1.0))
	if flash > 0.0:
		c.draw_rect(Rect2(Vector2.ZERO, CANVAS), Color(1, 1, 1, flash))
