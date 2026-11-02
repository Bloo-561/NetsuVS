class_name NetsuCLIllustration
extends Control
## Drawn examples for command list topics that aren't a move (data/command_list/system.json "illustration"):
##   gauge      the Craft Gauge (bars from the fighter's MaxSuperGauge) and what each thing costs
##   scaling    damage of each hit of a combo (72% from hit 2, -14% a hit after that)
##   levels     blockstun of the four attack levels
##   overdrive  the low-health Overdrive state and what it gives
##   juggle     the combo counter's juggle meter running out
## Numbers here are for showing the idea; the fight's own rules live in the engine (docs/game_systems.md).

const BLUE := Color(0.16, 0.52, 1.0)
const CYAN := Color(0.3, 0.82, 1.0)
const LINE := Color(0.62, 0.8, 1.0)
const GOLD := Color(1.0, 0.79, 0.3)
const RED := Color(1.0, 0.16, 0.3)
const TEXT := Color(0.97, 0.97, 1.0)
const DIM := Color(0.73, 0.77, 0.9)

var kind := "":
	set(value):
		kind = value
		queue_redraw()
var bars := 4
var costs := {"EX MOVE": 1, "PUSHBLOCK": 1, "ASSIST CANCEL": 1, "SUPER": 3}

var _font: Font
var _bold: Font
var _t := 0.0


func _init() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	process_mode = Node.PROCESS_MODE_ALWAYS
	_font = load("res://assets/fonts/Rajdhani-Bold.ttf")
	_bold = NetsuUI.sans(2, true)


func _process(delta: float) -> void:
	if is_visible_in_tree() and kind != "":
		_t += delta
		queue_redraw()


func _text(pos: Vector2, s: String, fs: int, col: Color, font: Font = null) -> void:
	draw_string(font if font else _font, pos, s, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, col)


func _draw() -> void:
	var w := size.x
	var h := size.y
	match kind:
		"gauge":
			var x0 := 60.0
			var gw := w - 120.0
			var y := h * 0.42
			var fill := fmod(_t * 0.35, 1.0) * bars
			_text(Vector2(x0, y - 40), "%d%%" % int(round(fill * 100.0)), 60, GOLD, _bold)
			_text(Vector2(x0 + 190, y - 44), "CRAFT GAUGE", 24, DIM)
			var cell := (gw - (bars - 1) * 8.0) / bars
			for i in bars:
				var r := Rect2(x0 + i * (cell + 8.0), y, cell, 34)
				draw_rect(r, Color(LINE, 0.12))
				var part := clampf(fill - i, 0.0, 1.0)
				if part > 0.0:
					draw_rect(Rect2(r.position, Vector2(r.size.x * part, r.size.y)), Color(1.0, 0.7, 0.12) if part >= 1.0 else Color(1.0, 0.84, 0.4))
			var cx := x0
			for k in costs:
				var label := "%s · %d" % [k, costs[k]]
				_text(Vector2(cx, y + 80), label, 21, GOLD if costs[k] >= 3 else TEXT)
				cx += _font.get_string_size(label, HORIZONTAL_ALIGNMENT_LEFT, -1, 21).x + 34.0
		"scaling":
			var vals := [100.0]
			var p := 72.0
			for i in 7:
				vals.append(p)
				p *= 0.86
			var bw := (w - 120.0 - 7 * 14.0) / 8.0
			var base := h - 70.0
			for i in vals.size():
				var bh: float = (base - 70.0) * vals[i] / 100.0
				var r := Rect2(60.0 + i * (bw + 14.0), base - bh, bw, bh)
				draw_rect(r, (Color(0.62, 0.94, 1.0) if i == 0 else Color(0.45, 0.8, 1.0, 0.85)))
				_text(Vector2(r.position.x + 4, r.position.y - 10), "%d%%" % int(vals[i]), 20, TEXT, _bold)
				_text(Vector2(r.position.x + 4, base + 28), "HIT %d" % (i + 1), 17, DIM)
		"levels":
			var names := [["LIGHT", 11], ["MEDIUM", 14], ["HIGH MEDIUM", 15], ["HEAVY", 16]]
			for i in names.size():
				var y := 80.0 + i * 70.0
				_text(Vector2(70, y + 20), names[i][0], 24, DIM)
				var r := Rect2(260, y, w - 420, 26)
				draw_rect(r, Color(LINE, 0.1))
				draw_rect(Rect2(r.position, Vector2(r.size.x * names[i][1] / 16.0, r.size.y)), CYAN)
				_text(Vector2(w - 140, y + 22), "%df" % names[i][1], 24, TEXT, _bold)
		"overdrive":
			var y := 110.0
			var pulse := 0.6 + 0.4 * sin(_t * 5.0)
			draw_rect(Rect2(70, y, w - 140, 30), Color(1, 1, 1, 0.08))
			draw_rect(Rect2(70, y, (w - 140) * 0.28, 30), Color(0.85, 0.08, 0.2))
			_text(Vector2(70, y + 80), "OVERDRIVE", 40, Color(RED, pulse), _bold)
			var perks := ["+1 CRAFT BAR", "−10% DAMAGE TAKEN", "ASSIST LINK · ½ COOLDOWN"]
			var pw := (w - 140 - 2 * 12.0) / 3.0
			for i in perks.size():
				var r := Rect2(70 + i * (pw + 12.0), y + 120, pw, 56)
				draw_rect(r, Color(RED, 0.12))
				draw_rect(r, Color(1.0, 0.35, 0.45, 0.6), false, 1.0)
				_text(r.position + Vector2(14, 36), perks[i], 21, Color(1.0, 0.88, 0.9))
		"juggle":
			var left := 1.0 - fmod(_t * 0.3, 1.0)
			_text(Vector2(70, 120), str(int(lerpf(8, 23, 1.0 - left))), 62, TEXT, _bold)
			_text(Vector2(160, 118), "HITS", 26, CYAN, _bold)
			draw_rect(Rect2(70, 150, w - 140, 16), Color(LINE, 0.12))
			draw_rect(Rect2(70, 150, (w - 140) * 0.62, 16), BLUE)
			draw_rect(Rect2(70, 176, w - 140, 8), Color(LINE, 0.12))
			draw_rect(Rect2(70, 176, (w - 140) * left, 8), Color(1.0, 0.45 + 0.4 * left, 0.2))
			_text(Vector2(70, 220), "HITSTUN LEFT", 20, DIM)
			_text(Vector2(250, 220), "JUGGLE LEFT", 20, Color(1.0, 0.55, 0.36))
			if left < 0.2:
				_text(Vector2(420, 220), "TECH!", 22, TEXT, _bold)
