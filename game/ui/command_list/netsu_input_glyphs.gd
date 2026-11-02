class_name NetsuInputGlyphs
extends Control
## A move's input drawn as glyphs: numpad directions as arrows in a chip, buttons as white circles with a coloured
## ring (A blue, B gold, C red, S green), like the command list mockup (Nov 2 2026).
##
## text uses the command list notation (NetsuMoveCatalog.input_text):
##   "236 A|B"  -> ↓↘→  (A) / (B)        "214 B+C" -> ↓↙←  (B)+(C)        "j. 236 C" -> AIR ↓↘→ (C)
##   "[A]"      -> hold A                "> A"     -> › (A)  (a follow-up)  "236 B+C or 236236 A|B|C"
## Anything else is printed as it is.

const RING := {"A": Color(0.35, 0.71, 1.0), "B": Color(1.0, 0.79, 0.3), "C": Color(1.0, 0.35, 0.48), "S": Color(0.37, 0.88, 0.63)}
const ARROWS := {"1": Vector2(-1, 1), "2": Vector2(0, 1), "3": Vector2(1, 1), "4": Vector2(-1, 0), "6": Vector2(1, 0),
	"7": Vector2(-1, -1), "8": Vector2(0, -1), "9": Vector2(1, -1)}
const FONT_PATH := "res://assets/fonts/Rajdhani-Bold.ttf"

## Glyph height in pixels (the circles' diameter).
@export var glyph_height: float = 30.0
@export var text_color: Color = Color(0.73, 0.77, 0.9)
@export var arrow_color: Color = Color(0.9, 0.95, 1.0)

var text: String = "":
	set(value):
		text = value
		_parse()

var _tokens: Array = []   # [{"kind": "dirs" | "btn" | "txt", "v": String, "hold": bool}]
var _font: Font


func _init() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_font = load(FONT_PATH) if ResourceLoader.exists(FONT_PATH) else ThemeDB.fallback_font


func _parse() -> void:
	_tokens.clear()
	for raw in text.split(" ", false):
		var tok := raw.strip_edges()
		if tok == "":
			continue
		var hold := tok.begins_with("[") and tok.ends_with("]")
		var core := tok.trim_prefix("[").trim_suffix("]")
		if core == "*":
			_tokens.append({"kind": "dirs", "v": "*"})
		elif core.is_valid_int() and not core.contains("5") and not core.contains("0"):
			_tokens.append({"kind": "dirs", "v": core})
		elif _is_buttons(core):
			var i := 0
			var part := ""
			for ch in core:
				if ch == "+" or ch == "|":
					_tokens.append({"kind": "btn", "v": part, "hold": hold})
					_tokens.append({"kind": "txt", "v": "+" if ch == "+" else "/"})
					part = ""
				else:
					part += ch
				i += 1
			_tokens.append({"kind": "btn", "v": part, "hold": hold})
			if hold:
				_tokens.append({"kind": "txt", "v": "HOLD"})
		elif tok == "j.":
			_tokens.append({"kind": "txt", "v": "AIR"})
		elif tok == ">":
			_tokens.append({"kind": "txt", "v": "›"})
		else:
			_tokens.append({"kind": "txt", "v": tok})
	custom_minimum_size = Vector2(_width(), glyph_height)
	queue_redraw()


static func _is_buttons(s: String) -> bool:
	if s == "":
		return false
	var want_btn := true
	for ch in s:
		if want_btn:
			if not ch in ["A", "B", "C", "S"]:
				return false
		elif not ch in ["+", "|"]:
			return false
		want_btn = not want_btn
	return not want_btn


func _font_size() -> int:
	return int(round(glyph_height * 0.66))


func _token_width(t: Dictionary) -> float:
	var h := glyph_height
	match t["kind"]:
		"dirs":
			return h * 0.25 + t["v"].length() * h * 0.62
		"btn":
			return h
		_:
			return _font.get_string_size(t["v"], HORIZONTAL_ALIGNMENT_LEFT, -1, _font_size()).x


func _width() -> float:
	var w := 0.0
	for t in _tokens:
		w += _token_width(t) + glyph_height * 0.2
	return maxf(0.0, w - glyph_height * 0.2)


func _draw() -> void:
	var h := glyph_height
	var x := 0.0
	var cy := size.y / 2.0
	for t in _tokens:
		var w := _token_width(t)
		match t["kind"]:
			"dirs":
				var chip := Rect2(x, cy - h / 2.0, w, h)
				draw_style_box(_chip_style(), chip)
				var step := h * 0.62
				if t["v"] == "*":   # any direction: a small eight-way star
					var c0 := Vector2(x + w / 2.0, cy)
					for a in 8:
						var v := Vector2.RIGHT.rotated(a * PI / 4.0)
						draw_line(c0 + v * h * 0.08, c0 + v * h * 0.32, arrow_color, 2.0, true)
				else:
					for i in t["v"].length():
						var c := Vector2(x + h * 0.125 + step * (i + 0.5), cy)
						_draw_arrow(c, ARROWS.get(t["v"][i], Vector2.RIGHT), h * 0.3)
			"btn":
				var c := Vector2(x + h / 2.0, cy)
				var ring: Color = RING.get(t["v"], Color.WHITE)
				draw_circle(c, h / 2.0 + 2.0, Color(ring, 0.35))
				draw_circle(c, h / 2.0, ring)
				draw_circle(c, h / 2.0 - maxf(2.0, h * 0.09), Color(0.97, 0.97, 1.0))
				var fs := _font_size()
				var tw := _font.get_string_size(t["v"], HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
				draw_string(_font, Vector2(c.x - tw / 2.0, c.y + fs * 0.36), t["v"], HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color(0.16, 0.19, 0.42))
				if t.get("hold", false):
					draw_arc(c, h / 2.0 + 4.0, -PI * 0.85, -PI * 0.15, 12, Color(ring, 0.9), 2.0)
			_:
				var fs := _font_size()
				draw_string(_font, Vector2(x, cy + fs * 0.36), t["v"], HORIZONTAL_ALIGNMENT_LEFT, -1, fs, text_color)
		x += w + h * 0.2


func _chip_style() -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.62, 0.8, 1.0, 0.14)
	sb.border_color = Color(0.62, 0.8, 1.0, 0.35)
	sb.set_border_width_all(1)
	sb.set_corner_radius_all(int(glyph_height * 0.2))
	return sb


func _draw_arrow(c: Vector2, dir: Vector2, r: float) -> void:
	var d := dir.normalized()
	var n := Vector2(-d.y, d.x)
	var tip := c + d * r
	var tail := c - d * r
	var head := r * 0.75
	draw_line(tail, tip - d * head * 0.5, arrow_color, maxf(2.0, r * 0.28), true)
	draw_colored_polygon(PackedVector2Array([tip, tip - d * head + n * head * 0.65, tip - d * head - n * head * 0.65]), arrow_color)
