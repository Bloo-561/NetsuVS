extends Control
## NETSU MATCH OVERLAY - replaces the rest of Mahou's battle UI with our look
## (Oct 19 2026 mockups, same dark night-blue style as the menus):
##   1. Round cards   (catchphrase banner / ROUND 1 / FIGHT! / K.O. / PLAYER 1 WINS)
##   2. Hit notifications ("FIRST STRIKE", "COUNTER", "PUNISH", ...)
##   3. Training data panels + input history (Training mode)
##   (the pause menu is game/ui/pause/netsu_pause_menu.gd)
##
## Same trick as netsu_hud.gd: the engine keeps driving Mahou's nodes in
## engine/ui/instances/Sakuga_UI.tscn (made invisible here) and this script
## reads them every frame and draws our version. Timing stays frame-exact for
## rollback because the engine still owns the animation.
## Text lists, colours and positions are @exports. Full map: docs/battle_hud.md

@export_group("Colours")
@export var p1_accent: Color = Color(0.25, 0.6, 1.0)     ## Player 1 blue
@export var p2_accent: Color = Color(1.0, 0.22, 0.35)    ## Player 2 crimson
@export var line_color: Color = Color(0.7, 0.86, 1.0)    ## glowing hairlines and diamonds
@export var panel_color: Color = Color(0.03, 0.05, 0.17, 0.86)

@export_group("Round Cards")
## Pre-round banner lines. If you add more, one is picked at random each match.
## Two lines each, split with "\n"; the FIRST word of line 1 is drawn blue,
## the first word of line 2 crimson.
@export var catchphrases: PackedStringArray = [
	"Rank Means Nothing.\nSkill Means Everything.",
]
## What the other Mahou cards show. Leave a value empty to use the engine's text
## (ROUND 1 / FINAL ROUND and the K.O. / PERFECT! / TIME UP! names).
@export var card_text := {
	"FIGHT!": "Fight!",
	"Draw": "Draw",
	"P1Win": "Player 1 Wins",
	"P2Win": "Player 2 Wins",
	"RoundCard": "",
	"KO": "",
}
@export var banner_center_y: float = 500.0
@export var phrase_size: int = 54
@export var card_size: int = 120

@export_group("Hit Notifications")
@export var notif_position: Vector2 = Vector2(40, 470)   ## P1 top-left; P2 is mirrored
@export var notif_size: Vector2 = Vector2(330, 36)
@export var notif_gap: float = 8.0
@export var notif_text_size: int = 21

@export_group("Training")
@export var training_panel_position: Vector2 = Vector2(28, 652)   ## P1; P2 is mirrored
@export var training_panel_size: Vector2 = Vector2(370, 268)
@export var training_labels: PackedStringArray = ["Last hit", "Combo dmg", "Best combo", "Hit type", "Scaling", "Frame data"]
@export var history_position: Vector2 = Vector2(20, 174)   ## P1 column; P2 mirrored
@export var history_size: Vector2 = Vector2(166, 29)
@export var training_shift: float = 175.0   ## how far combo/notifs move right when input history is on

const CANVAS := Vector2(1920, 1080)
const CARDS := ["CatchPhrase", "RoundCard", "FIGHT!", "KO", "Draw", "P1Win", "P2Win"]
const ARROWS := ["↙", "↓", "↘", "←", "•", "→", "↖", "↑", "↗"]

var _root: Node
var _font: Font
var _bold: Font
var _serif: Font
var _phrase := ""
var _time := 0.0
var _cards := {}
var _notifs := [[], []]
var _info := [null, null]
var _info_box := [null, null]
var _history := [[], []]
var _history_base := {}
var _hud: Control
var _hud_combo_x := 0.0


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	size = CANVAS
	_font = NetsuUI.sans(2)                 # Exo 2 SemiBold: labels, notifications, training
	_bold = NetsuUI.sans(6, true)           # Exo 2 Bold Italic: ROUND / FIGHT! / K.O.
	_serif = _italic_serif()                # Cormorant Garamond Italic: the catchphrase
	if not catchphrases.is_empty():
		_phrase = catchphrases[randi() % catchphrases.size()]
	_root = get_parent()
	# 1. round cards
	var cards := _root.get_node_or_null("MatchCards") as CanvasItem
	if cards:
		cards.modulate = Color(1, 1, 1, 0)
		for n in CARDS:
			_cards[n] = cards.get_node_or_null(NodePath(n))
	# 2. notifications
	for side in 2:
		var box := _root.get_node_or_null("GameHUD_Background/Notifs%s" % ("P1" if side == 0 else "P2")) as CanvasItem
		if box:
			box.modulate = Color(1, 1, 1, 0)
			_notifs[side] = box.get_children()
	# 3. training
	var training := _root.get_node_or_null("GameHUD_Foreground/TrainingInfo") as CanvasItem
	if training:
		training.modulate = Color(1, 1, 1, 0)
		for side in 2:
			_info_box[side] = training.get_node_or_null("P%dInfo" % (side + 1))
			_info[side] = training.get_node_or_null("P%dInfo/Information" % (side + 1))
	var history := _root.get_node_or_null("GameHUD_Foreground/InputHistory") as CanvasItem
	if history:
		history.modulate = Color(1, 1, 1, 0)
		for side in 2:
			var column := history.get_node_or_null("P%dInputHistory" % (side + 1))
			if column:
				_history[side] = column.get_children()
	# leftovers (the pause menu is game/ui/pause/netsu_pause_menu.gd)
	var seed_label := _root.get_node_or_null("Seed") as CanvasItem
	if seed_label:
		seed_label.visible = false
	_hud = _root.get_node_or_null("NetsuHUD")
	if _hud:
		_hud_combo_x = _hud.get("combo_position").x
	var foreground := _root.get_node_or_null("GameHUD_Foreground")
	if foreground:
		_root.move_child.call_deferred(self, foreground.get_index() + 2)
	get_viewport().size_changed.connect(_fit)
	_fit()


func _fit() -> void:
	var view := get_viewport_rect().size
	scale = Vector2.ONE * (view.x / CANVAS.x)
	position = Vector2(0, (view.y - CANVAS.y * scale.y) / 2.0)


func _process(delta: float) -> void:
	_time += delta
	queue_redraw()


func _italic_serif() -> Font:
	var path := "res://assets/fonts/CormorantGaramond-Italic.ttf"
	var f := FontVariation.new()
	f.base_font = load(path) if ResourceLoader.exists(path) else NetsuUI.SERIF_FILE
	f.variation_opentype = {TextServerManager.get_primary_interface().name_to_tag("wght"): 600}
	# lining numbers ("ROUND 1", not an old-style 1 that looks like an I)
	f.opentype_features = {TextServerManager.get_primary_interface().name_to_tag("lnum"): 1}
	f.fallbacks = [NetsuUI.BODY_FILE]
	return f


func _x(x: float, side: int) -> float:
	return x if side == 0 else CANVAS.x - x


func _history_on() -> bool:
	for side in 2:
		for e in _history[side]:
			if e is CanvasItem and e.is_visible_in_tree():
				var f = e.get_node_or_null("Frames")
				if f and str(f.text) != "":
					return true
	return false


func _draw() -> void:
	var shift := training_shift if _history_on() else 0.0
	if _hud:
		var pos: Vector2 = _hud.get("combo_position")
		var hud_k = _hud.get("layout_scale")   # the HUD's mockup scale (its layout numbers are mockup pixels)
		_hud.set("combo_position", Vector2(_hud_combo_x + shift / (float(hud_k) if hud_k != null else NetsuUI.K), pos.y))
	for side in 2:
		_draw_notifs(side, shift)
		_draw_training(side)
		_draw_history(side)
	_draw_cards()


func _accent(side: int) -> Color:
	return p1_accent if side == 0 else p2_accent


func _diamond(at: Vector2, r: float, edge: Color, fill: Color) -> void:
	var pts := PackedVector2Array([at + Vector2(0, -r), at + Vector2(r, 0), at + Vector2(0, r), at + Vector2(-r, 0)])
	draw_colored_polygon(pts, fill)
	pts.append(pts[0])
	draw_polyline(pts, edge, 2.0, true)


func _hair(a: Vector2, b: Vector2, color: Color, width: float = 1.5) -> void:
	draw_line(a, b, color, width, true)


func _text_w(font: Font, text: String, size: int) -> float:
	return font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x


# --- 1. Round cards -------------------------------------------------------------

## The banner: a dark slanted band across the middle with a blue end on the left,
## a crimson end on the right, glowing hairlines and diamonds.
## open: 0..1 (the band grows out from the centre), a: alpha.
func _draw_banner(cy: float, h: float, open: float, a: float) -> void:
	var half := 610.0 * open
	var cx := CANVAS.x / 2.0
	var top := cy - h / 2.0
	var bot := cy + h / 2.0
	var lean := h * 0.42
	var x0 := cx - half
	var x1 := cx + half
	# main band (slanted ends)
	var band := PackedVector2Array([Vector2(x0 + lean, top), Vector2(x1, top), Vector2(x1 - lean, bot), Vector2(x0, bot)])
	draw_polygon(band, PackedColorArray([Color(panel_color, 0.88 * a), Color(panel_color, 0.88 * a),
		Color(panel_color.darkened(0.2), 0.92 * a), Color(panel_color.darkened(0.2), 0.92 * a)]))
	# outer hairlines running past the band
	var c := Color(line_color, 0.85 * a)
	_hair(Vector2(x0 - 40 * open, top - 8), Vector2(x1 + 40 * open, top - 8), Color(line_color, 0.45 * a))
	_hair(Vector2(x0 - 60 * open, bot + 8), Vector2(x1 + 60 * open, bot + 8), Color(line_color, 0.45 * a))
	_hair(Vector2(x0 + lean, top), Vector2(x1, top), c)
	_hair(Vector2(x0, bot), Vector2(x1 - lean, bot), c)
	# coloured slanted ends
	for s in [0, 1]:
		var col := _accent(s)
		var w := 34.0
		var gap := 26.0
		var base_x := x0 - 70.0 * open if s == 0 else x1 + 70.0 * open
		for k in 2:
			var off := (gap + w) * k * (1.0 if s == 0 else -1.0)
			var strip: PackedVector2Array
			if s == 0:
				strip = PackedVector2Array([Vector2(base_x + lean + off + 20, top - 4), Vector2(base_x + lean + off + 20 + w * (1.0 - 0.6 * k), top - 4),
					Vector2(base_x + off + 20 + w * (1.0 - 0.6 * k), bot + 4), Vector2(base_x + off + 20, bot + 4)])
			else:
				strip = PackedVector2Array([Vector2(base_x - off - 20 - w * (1.0 - 0.6 * k), top - 4), Vector2(base_x - off - 20, top - 4),
					Vector2(base_x - lean - off - 20, bot + 4), Vector2(base_x - lean - off - 20 - w * (1.0 - 0.6 * k), bot + 4)])
			draw_colored_polygon(strip, Color(col, (0.95 if k == 0 else 0.55) * a))
	# diamonds: top and bottom centre, and at both inner ends of a thin centre line
	var dfill := Color(panel_color, a)
	_diamond(Vector2(cx, top), 11.0, c, dfill)
	_diamond(Vector2(cx, bot), 11.0, c, dfill)
	if open > 0.6:
		var inner := 545.0 * open
		_diamond(Vector2(cx - inner, cy), 11.0, c, dfill)
		_diamond(Vector2(cx + inner, cy), 11.0, c, dfill)
		_hair(Vector2(cx - inner + 20, cy), Vector2(cx - 300, cy), Color(line_color, 0.3 * a), 1.0)
		_hair(Vector2(cx + 300, cy), Vector2(cx + inner - 20, cy), Color(line_color, 0.3 * a), 1.0)


## One line of the catchphrase: first word in `accent`, the rest white.
func _draw_phrase_line(line: String, cy: float, size: int, accent: Color, a: float) -> void:
	var parts := line.split(" ", false, 1)
	var first := parts[0]
	var rest := (" " + parts[1]) if parts.size() > 1 else ""
	var w1 := _text_w(_serif, first, size)
	var w2 := _text_w(_serif, rest, size)
	var x := CANVAS.x / 2.0 - (w1 + w2) / 2.0
	var base := cy + size * 0.32
	var shadow := Color(0.0, 0.02, 0.1, 0.8 * a)
	draw_string_outline(_serif, Vector2(x, base), first + rest, HORIZONTAL_ALIGNMENT_LEFT, -1, size, 8, shadow)
	draw_string(_serif, Vector2(x, base), first, HORIZONTAL_ALIGNMENT_LEFT, -1, size, Color(accent.lightened(0.15), a))
	draw_string(_serif, Vector2(x + w1, base), rest, HORIZONTAL_ALIGNMENT_LEFT, -1, size, Color(1, 1, 1, a))


func _draw_cards() -> void:
	for n in CARDS:
		var label = _cards.get(n)
		if label == null or not label.visible:
			continue
		var a: float = label.modulate.a * label.self_modulate.a
		if a <= 0.01:
			continue
		var grow: float = clampf(label.scale.y, 0.5, 2.0)
		var open := clampf(a * 1.4, 0.0, 1.0)
		var cy := banner_center_y
		if n == "CatchPhrase":
			var lines := _phrase.split("\n")
			_draw_banner(cy, 140.0, open, a)
			if lines.size() >= 2:
				_draw_phrase_line(lines[0], cy - 30, phrase_size, p1_accent, a)
				_draw_phrase_line(lines[1], cy + 30, phrase_size, p2_accent, a)
			elif lines.size() == 1:
				_draw_phrase_line(lines[0], cy, phrase_size, p1_accent, a)
			continue
		var text: String = card_text.get(n, "")
		if text == "":
			text = str(label.text)
		text = text.replace("\n", " ")
		var accent := line_color
		if n == "P1Win":
			accent = p1_accent
		elif n == "P2Win":
			accent = p2_accent
		elif n == "KO":
			accent = p2_accent
		_draw_banner(cy, 130.0 * minf(grow, 1.25), open, a)
		# same italic serif as the catchphrase: white letters with a coloured glow
		var size_px := int(card_size * grow * (1.0 if n in ["FIGHT!", "KO"] else 0.85))
		var w := _text_w(_serif, text, size_px)
		var pos := Vector2(CANVAS.x / 2.0 - w / 2.0, cy + size_px * 0.3)
		draw_string_outline(_serif, pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px, 24, Color(accent, 0.3 * a))
		draw_string_outline(_serif, pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px, 8, Color(0.0, 0.03, 0.14, 0.85 * a))
		draw_string(_serif, pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px, Color(1, 1, 1, a))


# --- 2. Hit notifications -------------------------------------------------------

func _draw_notifs(side: int, shift: float) -> void:
	var y := notif_position.y
	var accent := _accent(side)
	for widget in _notifs[side]:
		if not (widget is CanvasItem) or not widget.visible:
			continue
		var labels: Array = widget.find_children("*", "Label", true, false)
		if labels.is_empty():
			continue
		var text := str(labels[0].text).to_upper()
		if text == "":
			continue
		var x0 := notif_position.x + shift
		var x1 := x0 + notif_size.x
		var h := notif_size.y
		var slant := 12.0
		var band := PackedVector2Array([Vector2(_x(x0 + slant, side), y), Vector2(_x(x1 + slant, side), y),
			Vector2(_x(x1, side), y + h), Vector2(_x(x0, side), y + h)])
		draw_polygon(band, PackedColorArray([panel_color, Color(panel_color, 0.35), Color(panel_color, 0.35), panel_color]))
		_hair(Vector2(_x(x0 + slant, side), y), Vector2(_x(x1 - 40, side), y), Color(line_color, 0.6))
		var strip := PackedVector2Array([Vector2(_x(x0 + slant, side), y), Vector2(_x(x0 + slant + 7, side), y),
			Vector2(_x(x0 + 7, side), y + h), Vector2(_x(x0, side), y + h)])
		draw_colored_polygon(strip, accent)
		_diamond(Vector2(_x(x0 + 30, side), y + h / 2.0), 6.0, Color(line_color, 0.95), Color(accent, 0.9))
		if _font:
			var w := _text_w(_font, text, notif_text_size)
			var tx := _x(x0 + 46, side) - (0.0 if side == 0 else w)
			draw_string(_font, Vector2(tx, y + h * 0.7), text, HORIZONTAL_ALIGNMENT_LEFT, -1, notif_text_size, Color.WHITE)
		y += h + notif_gap


# --- 3. Training panels + input history -------------------------------------------

func _draw_training(side: int) -> void:
	var box = _info_box[side]
	var info = _info[side]
	if box == null or info == null or not box.is_visible_in_tree() or _font == null:
		return
	var values := str(info.text).split("\n")
	var accent := _accent(side)
	var w := training_panel_size.x
	var h := training_panel_size.y
	var x := training_panel_position.x if side == 0 else CANVAS.x - training_panel_position.x - w
	var y := training_panel_position.y
	var r := Rect2(x, y, w, h)
	draw_rect(r, panel_color)
	# glowing frame with bright corner triangles
	var pts := PackedVector2Array([r.position, Vector2(r.end.x, r.position.y), r.end, Vector2(r.position.x, r.end.y), r.position])
	draw_polyline(pts, Color(accent, 0.25), 8.0, true)
	draw_polyline(pts, Color(accent.lightened(0.3), 0.95), 2.0, true)
	for corner in [0, 1, 2, 3]:
		var p: Vector2 = pts[corner]
		var dx := 1.0 if corner in [0, 3] else -1.0
		var dy := 1.0 if corner in [0, 1] else -1.0
		draw_colored_polygon(PackedVector2Array([p, p + Vector2(dx * 18, 0), p + Vector2(0, dy * 18)]), accent.lightened(0.35))
	# header tab
	var head_h := 36.0
	draw_polygon(PackedVector2Array([Vector2(x + 2, y + 2), Vector2(x + w - 2, y + 2), Vector2(x + w - 2, y + head_h), Vector2(x + 2, y + head_h)]),
		PackedColorArray([Color(accent, 0.55), Color(accent, 0.08), Color(accent, 0.08), Color(accent, 0.55)]))
	_hair(Vector2(x, y + head_h), Vector2(x + w, y + head_h), Color(accent.lightened(0.3), 0.8))
	var title := "TRAINING DATA   P%d" % (side + 1)
	draw_string(_font, Vector2(x + 40, y + 26), title, HORIZONTAL_ALIGNMENT_LEFT, -1, 20, Color.WHITE)
	var row := (h - head_h - 14.0) / maxf(training_labels.size(), 1)
	for i in mini(training_labels.size(), values.size()):
		var ry := y + head_h + 8 + row * i
		draw_string(_font, Vector2(x + 24, ry + row * 0.66), training_labels[i].to_upper(), HORIZONTAL_ALIGNMENT_LEFT, -1, 18, Color(0.85, 0.9, 1.0))
		draw_string(_font, Vector2(x + w - 24 - 160, ry + row * 0.66), values[i].strip_edges().to_upper(), HORIZONTAL_ALIGNMENT_RIGHT, 160, 19, Color.WHITE)
		if i < training_labels.size() - 1:
			_hair(Vector2(x + 18, ry + row), Vector2(x + w - 18, ry + row), Color(line_color, 0.14), 1.0)


## Arrow (dir 0..8 as numpad - 1: 0 = down-left ... 4 = neutral ... 8 = up-right) as a small drawn icon.
func _draw_dir(c: Vector2, dir: int, color: Color) -> void:
	if dir == 4:
		draw_circle(c, 3.5, color)
		return
	var v := Vector2(dir % 3 - 1, 1 - dir / 3)   # numpad -> screen direction
	v = v.normalized()
	var ang := v.angle()
	var r := 9.0
	var tip := c + Vector2.RIGHT.rotated(ang) * r
	var tail := c - Vector2.RIGHT.rotated(ang) * r
	draw_line(tail, tip - Vector2.RIGHT.rotated(ang) * 3.0, color, 2.6, true)
	draw_colored_polygon(PackedVector2Array([tip, tip + Vector2(-7, -5.5).rotated(ang), tip + Vector2(-7, 5.5).rotated(ang)]), color)


func _draw_history(side: int) -> void:
	if _font == null:
		return
	var y := history_position.y
	var w := history_size.x
	var rh := history_size.y
	var accent := _accent(side)
	for e in _history[side]:
		if not (e is CanvasItem) or not e.is_visible_in_tree():
			continue
		var frames = e.get_node_or_null("Frames")
		if frames == null or str(frames.text) == "":
			continue
		var x := history_position.x if side == 0 else CANVAS.x - history_position.x - w
		draw_rect(Rect2(x, y, w, rh - 2), Color(panel_color, 0.82))
		_hair(Vector2(x, y + rh - 2), Vector2(x + w, y + rh - 2), Color(line_color, 0.18), 1.0)
		draw_rect(Rect2(x if side == 0 else x + w - 3, y, 3, rh - 2), Color(accent, 0.8))
		var dir = e.get_node_or_null("Dir")
		_draw_dir(Vector2(x + 26, y + rh / 2.0 - 1), clampi(dir.frame, 0, 8) if dir else 4, Color.WHITE)
		var bx := x + 50
		for b in [["A", "A"], ["B", "B"], ["C", "C"], ["D", "S"]]:
			var sprite = e.get_node_or_null(b[0])
			if sprite and _is_pressed(sprite):
				draw_circle(Vector2(bx + 8, y + rh / 2.0 - 1), 9.0, Color(accent.lightened(0.2), 0.95))
				var lw := _text_w(_font, b[1], 14)
				draw_string(_font, Vector2(bx + 8 - lw / 2.0, y + rh / 2.0 + 4), b[1], HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color.WHITE)
			bx += 21
		draw_string(_font, Vector2(x + w - 62, y + rh * 0.7), str(frames.text), HORIZONTAL_ALIGNMENT_RIGHT, 52, 18, Color(0.9, 0.93, 1.0))
		y += rh


## The engine shows a pressed button by moving its sprite 2 frames forward.
func _is_pressed(sprite) -> bool:
	var id: int = sprite.get_instance_id()
	if not _history_base.has(id):
		_history_base[id] = sprite.frame
	_history_base[id] = mini(_history_base[id], sprite.frame)
	return sprite.frame >= _history_base[id] + 2
