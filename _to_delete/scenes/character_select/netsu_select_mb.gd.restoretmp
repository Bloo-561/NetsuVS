extends Control
## CHARACTER SELECT DRESSING (Nov 2 2026), after Melty Blood Act Cadenza's select screen, in Netsu's colours.
## Two copies of this node sit in the screen:
##   kind 0 (BACK, behind the renders):  the heat emblem at the top centre (twelve-ray sun, seven element stones,
##                                       a slowly turning crimson ring that pulses on the beat) and a block of faint
##                                       lore text in the middle of the screen
##   kind 1 (FRONT, over the renders):   the top plate (a light line across the screen, NETSU VS in a plate), the
##                                       mode over the emblem, two scrolling lines across the screen (the bright one:
##                                       the fighter under the cursor and their bio, right to left; a faint one under
##                                       it, left to right) and CHARACTER SELECT over the roster
## The beat follows the select theme's playback position (same as netsu_select_fx.gd).
## Everything is drawn here, on the 1920 x 1080 canvas.

@export var kind: int = 0
@export var bpm: float = 166.0
@export var beat_offset: float = 0.339
@export var theme_file: String = "beyond_the_crimson_horizon_select"
@export var colors: Array[Color] = [Color(0.25, 0.62, 1.0), Color(1.0, 0.2, 0.36)]
@export var emblem_center: Vector2 = Vector2(960, 150)
@export var emblem_radius: float = 112.0
@export var marquee_y: float = 612.0          ## baseline of the bright line
@export var marquee_speed: float = 170.0      ## px per second
@export var label_y: float = 676.0            ## centre of CHARACTER SELECT
@export var title_text: String = "NETSU VS"
## The faint line under the bright one.
@export var theme_line: String = "Beyond the crimson horizon the old miracle wakes once more, and every flame answers its call."
## The lore block behind everything (kind 0).
@export var lore: PackedStringArray = PackedStringArray([
	"Seven stones, one heart of heat.",
	"Where the elements meet, a miracle is written in fire,",
	"and those who carry it are drawn to one another",
	"like sparks to the wind, blade to blade, fist to fist.",
	"Choose the one who will burn brightest."])

var mode_text := ""
## FRONT: how much of the dressing shows (the intro brings it up); label_flash = CHARACTER SELECT flashing in.
var shown := 1.0
var label_shown := 1.0
var top_target := 1.0
var top_shown := 1.0      ## the title plate and the mode (they come in when the menu opens)
var label_flash := 0.0

const CANVAS := Vector2(1920, 1080)
const ELEMENT_COLORS := [Color(0.85, 0.52, 0.25), Color(0.35, 0.6, 1.0), Color(1.0, 0.3, 0.22), Color(0.35, 1.0, 0.5),
	Color(0.55, 0.38, 0.85), Color(1.0, 0.85, 0.3), Color(0.9, 0.93, 1.0)]

var _clock := 0.0
var _beat_pulse := 0.0
var _beat := -1
var _pop := 0.0
var _bright := ""
var _bright_color := Color(0.25, 0.62, 1.0)
var _bright_x := 0.0
var _bright_alpha := 1.0
var _faint_x := 0.0
var _sans: Font
var _bold: Font
var _serif: Font


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	size = CANVAS
	_sans = NetsuUI.sans(6)
	_bold = NetsuUI.sans(2, true)
	_serif = NetsuUI.serif(500, 1)
	_bright = theme_line
	_bright_x = 0.0


## Seconds into the select theme (its playback position), or this node's own clock when it isn't playing.
func song_time() -> float:
	var audio := get_node_or_null("/root/AudioManager")
	if audio != null:
		var player = audio.get("BGM")
		if player is AudioStreamPlayer and player.playing and player.stream != null \
				and str(player.stream.resource_path).get_file().begins_with(theme_file):
			return player.get_playback_position() + AudioServer.get_time_since_last_mix() - AudioServer.get_output_latency()
	return -1.0


func beat_time(i: float) -> float:
	return beat_offset + i * 60.0 / bpm


## FRONT: the bright line now shows this fighter (starts in from the right edge).
func show_bio(fighter_name: String, bio: String, color: Color) -> void:
	var text := fighter_name.to_upper() + "  -  " + bio
	if text == _bright:
		return
	_bright = text
	_bright_color = color
	_bright_x = CANVAS.x * 0.55
	_bright_alpha = 0.0


## BACK: the emblem flares (the menu opening).
func pop() -> void:
	_pop = 1.0


func _process(delta: float) -> void:
	_clock += delta
	var t := song_time()
	if t < 0.0:
		t = _clock
	var beat := int(floor((t - beat_offset) / (60.0 / bpm)))
	if beat != _beat:
		if beat > _beat or beat < _beat - 4:
			_beat_pulse = 1.0 if posmod(beat, 4) == 0 else 0.6
		_beat = beat
	_beat_pulse = maxf(0.0, _beat_pulse - delta * 3.0)
	_pop = maxf(0.0, _pop - delta * 1.8)
	if top_shown < 1.0 and top_target > top_shown:
		top_shown = minf(top_target, top_shown + delta * 4.0)
	_bright_x -= marquee_speed * delta
	_bright_alpha = minf(1.0, _bright_alpha + delta * 4.0)
	_faint_x += marquee_speed * 0.45 * delta
	label_flash = maxf(0.0, label_flash - delta * 4.0)
	queue_redraw()


func _draw() -> void:
	if kind == 0:
		_draw_emblem()
		_draw_lore()
	else:
		_draw_top()
		_draw_marquee()
		_draw_label()


# --- BACK ------------------------------------------------------------------------------------------

func _draw_emblem() -> void:
	var c := emblem_center
	var r := emblem_radius * (1.0 + 0.08 * _pop)
	var crimson := colors[1]
	var blue := colors[0]
	var pulse := _beat_pulse
	# soft glow
	for i in 6:
		draw_circle(c, r * (1.25 - i * 0.12), Color(crimson, 0.035 + 0.02 * pulse + 0.05 * _pop))
	# the big crimson ring: a thick arc, broken at two points, turning slowly
	var spin := _clock * 0.25
	for half in 2:
		var a0 := spin + half * PI + 0.35
		draw_arc(c, r, a0, a0 + PI - 0.7, 48, Color(crimson, 0.75 + 0.25 * pulse), 9.0, true)
		draw_arc(c, r + 9.0, a0 + 0.2, a0 + PI - 0.9, 40, Color(crimson.lightened(0.3), 0.35), 2.0, true)
	# the inner blue ring and its tick marks (turning the other way)
	draw_arc(c, r * 0.78, 0.0, TAU, 72, Color(blue, 0.45), 2.0, true)
	for i in 36:
		var a := -spin * 1.6 + TAU * i / 36.0
		var l := 7.0 if i % 3 == 0 else 3.5
		var d := Vector2(cos(a), sin(a))
		draw_line(c + d * (r * 0.78 - l), c + d * (r * 0.78), Color(blue.lightened(0.3), 0.55), 1.4, true)
	# the twelve-ray sun (heat) in the middle
	for i in 12:
		var a := TAU * i / 12.0 - PI / 2.0
		var d := Vector2(cos(a), sin(a))
		var side := Vector2(-d.y, d.x)
		var inner := r * 0.2
		var outer := r * (0.5 if i % 2 == 0 else 0.4) * (1.0 + 0.06 * pulse)
		draw_colored_polygon(PackedVector2Array([c + d * inner + side * 6.0, c + d * outer, c + d * inner - side * 6.0]),
			Color(1.0, 0.55, 0.35, 0.45 + 0.3 * pulse + 0.3 * _pop))
	draw_circle(c, r * 0.19, Color(0.04, 0.03, 0.1, 0.85))
	draw_arc(c, r * 0.19, 0.0, TAU, 40, Color(1.0, 0.7, 0.45, 0.8), 2.0, true)
	draw_circle(c, r * 0.08, Color(1.0, 0.8, 0.5, 0.55 + 0.4 * pulse))
	# seven element stones on the ring between the sun and the blue ring
	for i in 7:
		var a := TAU * i / 7.0 - PI / 2.0
		var p := c + Vector2(cos(a), sin(a)) * r * 0.64
		var col: Color = ELEMENT_COLORS[i]
		draw_circle(p, 9.0, Color(col, 0.18 + 0.2 * pulse))
		draw_circle(p, 4.5, Color(col, 0.9))
	if _pop > 0.0:
		draw_arc(c, r * (1.0 + 0.9 * (1.0 - _pop)), 0.0, TAU, 64, Color(1, 0.85, 0.8, 0.6 * _pop), 3.0, true)


func _draw_lore() -> void:
	var y := 300.0
	for line in lore:
		var w := _serif.get_string_size(line, HORIZONTAL_ALIGNMENT_LEFT, -1, 26).x
		draw_string(_serif, Vector2(960.0 - w / 2.0, y), line, HORIZONTAL_ALIGNMENT_LEFT, -1, 26, Color(0.7, 0.82, 1.0, 0.17))
		y += 40.0


# --- FRONT -----------------------------------------------------------------------------------------

func _draw_top() -> void:
	var a := top_shown
	if a <= 0.0:
		return
	var line := Color(0.62, 0.86, 1.0, 0.85 * a)
	# a light line across the top, the title plate hanging from it in the middle
	draw_line(Vector2(0, 22), Vector2(770, 22), line, 2.0, true)
	draw_line(Vector2(1150, 22), Vector2(1920, 22), line, 2.0, true)
	var plate := PackedVector2Array([Vector2(760, 6), Vector2(1160, 6), Vector2(1138, 40), Vector2(782, 40)])
	draw_colored_polygon(plate, Color(0.02, 0.04, 0.14, 0.88 * a))
	draw_polyline(PackedVector2Array([plate[0], plate[1], plate[2], plate[3], plate[0]]), line, 2.0, true)
	var w := _sans.get_string_size(title_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 24).x
	draw_string_outline(_sans, Vector2(960 - w / 2.0, 33), title_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 24, 6, Color(0.02, 0.04, 0.2, 0.6 * a))
	draw_string(_sans, Vector2(960 - w / 2.0, 33), title_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 24, Color(0.85, 0.94, 1.0, a))
	# the mode over the emblem, like the time limit in the reference
	if mode_text != "":
		var cap := "MODE"
		var cw := _sans.get_string_size(cap, HORIZONTAL_ALIGNMENT_LEFT, -1, 20).x
		draw_string_outline(_sans, Vector2(960 - cw / 2.0, 110), cap, HORIZONTAL_ALIGNMENT_LEFT, -1, 20, 6, Color(0.02, 0.03, 0.12, 0.7 * a))
		draw_string(_sans, Vector2(960 - cw / 2.0, 110), cap, HORIZONTAL_ALIGNMENT_LEFT, -1, 20, Color(1, 1, 1, 0.9 * a))
		var mw := _bold.get_string_size(mode_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 50).x
		draw_string_outline(_bold, Vector2(960 - mw / 2.0, 165), mode_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 50, 10, Color(0.02, 0.03, 0.12, 0.8 * a))
		draw_string(_bold, Vector2(960 - mw / 2.0, 165), mode_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 50, Color(1, 1, 1, a))


func _draw_marquee() -> void:
	var a := shown
	if a <= 0.0:
		return
	# bright line, right to left, repeating
	var size_px := 38
	var gap := 260.0
	var w := _bold.get_string_size(_bright, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px).x + gap
	var x := fposmod(_bright_x, w) - w
	var ba := a * _bright_alpha
	var glow := _bright_color.darkened(0.35)
	while x < CANVAS.x:
		draw_string_outline(_bold, Vector2(x, marquee_y), _bright, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px, 12, Color(glow, 0.45 * ba))
		draw_string_outline(_bold, Vector2(x, marquee_y), _bright, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px, 5, Color(0.02, 0.03, 0.15, 0.9 * ba))
		draw_string(_bold, Vector2(x, marquee_y), _bright, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px, Color(1, 1, 1, ba))
		x += w
	# faint line under it, left to right
	var fs := 22
	var fw := _serif.get_string_size(theme_line, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x + 180.0
	var fx := fposmod(_faint_x, fw) - fw
	while fx < CANVAS.x:
		draw_string(_serif, Vector2(fx, marquee_y + 32.0), theme_line, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color(0.55, 0.75, 1.0, 0.4 * a))
		fx += fw


func _draw_label() -> void:
	var a := label_shown
	if a <= 0.0:
		return
	var text := "CHARACTER SELECT"
	var size_px := 26
	var w := _sans.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px).x
	var y := label_y + 9.0
	var col := Color(1, 1, 1, a).lerp(Color(1, 1, 1, 1), label_flash)
	draw_string_outline(_sans, Vector2(960 - w / 2.0, y), text, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px, 7, Color(0.02, 0.03, 0.15, 0.85 * a))
	draw_string(_sans, Vector2(960 - w / 2.0, y), text, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px, col)
	# hairlines out to each side, blue on the left, crimson on the right
	var l0 := 960 - w / 2.0 - 18.0
	var r0 := 960 + w / 2.0 + 18.0
	draw_polyline_colors(PackedVector2Array([Vector2(l0 - 300, label_y), Vector2(l0, label_y)]),
		PackedColorArray([Color(colors[0], 0.0), Color(colors[0].lightened(0.3), 0.9 * a)]), 2.0, true)
	draw_polyline_colors(PackedVector2Array([Vector2(r0, label_y), Vector2(r0 + 300, label_y)]),
		PackedColorArray([Color(colors[1].lightened(0.3), 0.9 * a), Color(colors[1], 0.0)]), 2.0, true)
	if label_flash > 0.0:
		draw_rect(Rect2(l0 - 300, label_y - 22, (r0 + 300) - (l0 - 300), 44), Color(1, 1, 1, 0.25 * label_flash))
