extends Control
## NETSU BATTLE HUD  (Oct 20 2026 mockup)
##
## HOW IT WORKS
## The engine (C#: engine/sakuga/UI/HealthHUD.cs and MetersHUD.cs) still fills
## in Mahou's original HUD every frame. This script hides Mahou's bars and READS
## their values, then draws everything in our own style:
##   - to change how something LOOKS  -> change it here (or in the Inspector)
##   - to change how something WORKS  -> that's the C# engine
## Everything is drawn on a 1920x1080 canvas and scaled to the screen.
## Positions are for Player 1 (blue); Player 2 (crimson) is the mirror image of the
## LAYOUT only - portraits are never flipped.
## Layout numbers are mockup pixels (1456 x 816 mockup), multiplied by K.
## Full map: docs/battle_hud.md
##
## Layout, Player 1 (top-left):  hexagon portrait in the corner, "1P" tab, long
## health bar in a framed housing, name under the bar, BURST box under the name,
## round markers above the timer end of the bar. Hexagon TIME badge in the middle.
## Bottom-left: percentage in a hexagon box, Craft Point cells, "CRAFT POINTS".
## Just above it: the ASSIST gauge (the assist's face, name and refill bar; READY when S
## can call it). Its data comes from the engine through MatchSetup.assist_hud.

const K := 1920.0 / 1456.0
## Read by netsu_match_overlay.gd (it nudges the combo counter in training).
var layout_scale := K

@export_group("Colours")
@export var p1_accent: Color = Color(0.25, 0.6, 1.0)
@export var p2_accent: Color = Color(1.0, 0.22, 0.35)
@export var bar_dark: Color = Color(0.18, 0.4, 0.9)          ## health fill near the portrait
@export var bar_light: Color = Color(0.68, 0.92, 1.0)        ## health fill near the timer
@export var damage_color: Color = Color(1.0, 0.88, 0.94)     ## chunk you just lost
@export var danger_color: Color = Color(1.0, 0.4, 0.35)      ## pulses toward this when low
@export_range(0.0, 1.0) var danger_threshold: float = 0.3    ## health bar pulses below this
@export var backing: Color = Color(0.02, 0.04, 0.14, 0.86)
@export var frame_color: Color = Color(0.82, 0.92, 1.0, 0.95)
@export var burst_ready_color: Color = Color(1.0, 0.86, 0.45)
@export var overdrive_color: Color = Color(1.0, 0.42, 0.3)
@export var overdrive_bar_dark: Color = Color(0.5, 0.0, 0.04)    ## Oct 28: health fill in Overdrive, portrait end
@export var overdrive_bar_light: Color = Color(1.0, 0.12, 0.1)   ## Oct 28: health fill in Overdrive, timer end
@export var will_locked_color: Color = Color(0.9, 0.2, 0.3)
@export var meter_color: Color = Color(0.98, 0.72, 0.2)
@export var meter_light: Color = Color(1.0, 0.86, 0.42)
@export var percent_color: Color = Color(1.0, 0.97, 0.88)
@export var text_color: Color = Color(1, 1, 1)
@export var outline_color: Color = Color(0.02, 0.03, 0.12, 0.9)

@export_group("Juggle Meter")
@export var juggle_caption: String = "JUGGLE"         ## small caption over the juggle meter
@export var juggle_offset_y: float = 56.0            ## mockup px below the combo counter's top line
@export var juggle_height: float = 9.0               ## bar thickness (mockup px)
@export var juggle_fresh: Color = Color(0.35, 1.0, 0.55)   ## combo young: full juggle
@export var juggle_mid: Color = Color(1.0, 0.85, 0.25)     ## juggle half spent
@export var juggle_spent: Color = Color(1.0, 0.25, 0.2)    ## combo about to drop
@export var juggle_locked: Color = Color(0.75, 0.3, 1.0)   ## air counter hit: no tech until landing
@export var juggle_otg: Color = Color(0.3, 0.85, 1.0)      ## Oct 26 c20: lying: OTG window left

@export_group("Layout (mockup pixels)")
@export var bar_x: Vector2 = Vector2(169, 636)     ## health fill: portrait end / timer end (bottom edge)
@export var bar_y: float = 51.0
@export var bar_height: float = 26.0
@export var bar_slant: float = 14.0
## Where the eyes (the middle of HUD_Portrait.png) sits in the corner frame, and how wide the whole picture is.
@export var portrait_center: Vector2 = Vector2(88, 70)
@export var portrait_span: float = 190.0
@export var name_position: Vector2 = Vector2(178, 100)   ## left end of the name's baseline
@export var name_size: int = 24
@export var burst_box: Rect2 = Rect2(140, 109, 193, 19)
@export var rounds_position: Vector2 = Vector2(592, 33)  ## first round marker
@export var rounds_step: float = 24.0
@export var rounds_to_win: int = 2   ## replaced by the match's real "rounds to win" when a fight starts
@export var timer_center_x: float = 728.0
@export var timer_size: int = 62

@export_group("Craft Gauge")
@export var meter_caption: String = "CRAFT POINTS"
@export var meter_per_stock: int = 10000     ## 10000 = 100% (Oct 29: units x5; was 2000)
@export var meter_cells_x: Vector2 = Vector2(161, 497)    ## the cell row (bottom-left / top-right)

@export_group("Assist Gauge")
@export var assist_ready_color: Color = Color(1.0, 0.86, 0.45)
@export var stock_color: Color = Color(0.72, 0.35, 1.0)   ## Oct 26: the STOCK READY badge under the Burst gauge (Noah)
@export var assist_fill_color: Color = Color(0.55, 0.85, 1.0)
@export var assist_buff_color: Color = Color(0.45, 1.0, 0.8)
@export var assist_y: float = 668.0          ## top of the assist row (mockup px)

@export_group("Combo Counter")
@export var combo_position: Vector2 = Vector2(95, 245)   ## P1: left end of the number's baseline
@export var combo_number_size: int = 120
@export var combo_label: String = "HIT"
@export var combo_label_size: int = 40
@export var combo_min_hits: int = 2
@export var combo_damage_label: String = "DAMAGE"

const CANVAS := Vector2(1920, 1080)

var _src := {}
var _thin: Font
var _serif: Font
var _time := 0.0
var _hud_portraits := {}
var _combo_alpha: Array[float] = [0.0, 0.0]
var _combo_pop: Array[float] = [0.0, 0.0]
var _combo_last: Array[int] = [0, 0]
var _combo_damage: Array[String] = ["", ""]


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	size = CANVAS
	_thin = NetsuUI.sans(3)              # Exo 2 SemiBold: names, captions
	_serif = NetsuUI.sans(1, true)       # Exo 2 Bold Italic: timer, percent, combo
	var cfg = MatchSetup.settings()
	if cfg and int(cfg.RoundsToWin) > 0:
		rounds_to_win = int(cfg.RoundsToWin)   # set by GameSettings (Options > Game Settings)
	var root := get_parent()
	for side in 2:
		var p := "P%d" % (side + 1)
		_src[side] = {
			"health": root.get_node_or_null("GameHUD_Background/HealthBars/%sHealth" % p),
			"lost": root.get_node_or_null("GameHUD_Background/HealthBars/%sLostHealth" % p),
			"will": root.get_node_or_null("GameHUD_Background/HealthBars/%sWill" % p),
			"will_lock": root.get_node_or_null("GameHUD_Background/HealthBars/%sWillLocked" % p),
			"name": root.get_node_or_null("GameHUD_Background/HealthBars/%sName" % p),
			"portrait": root.get_node_or_null("GameHUD_Background/HealthBars/%sPortrait" % p),
			"rounds": root.get_node_or_null("GameHUD_Background/HealthBars/%sRounds" % p),
			"meter": root.get_node_or_null("GameHUD_Foreground/Meters/%sMeter" % p),
			"combo": root.get_node_or_null("GameHUD_Background/ComboCounters/%sComboCounter" % p),
			"info": root.get_node_or_null("GameHUD_Foreground/TrainingInfo/%sInfo/Information" % p),
		}
	_src["timer"] = root.get_node_or_null("GameHUD_Background/HealthBars/Timer")
	for path in ["GameHUD_Background/HealthBars", "GameHUD_Foreground/Meters"]:
		var node := root.get_node_or_null(path)
		if node:
			node.visible = false
	var combos := root.get_node_or_null("GameHUD_Background/ComboCounters") as CanvasItem
	if combos:
		combos.modulate = Color(1, 1, 1, 0)
	var foreground := root.get_node_or_null("GameHUD_Foreground")
	if foreground:
		root.move_child.call_deferred(self, foreground.get_index() + 1)
	get_viewport().size_changed.connect(_fit)
	_fit()
	MatchSetup.assist_hud = [{}, {}]   # filled again by the engine every frame of this fight
	MatchSetup.stock_hud = [{}, {}]    # Oct 26: Noah's stocked energy (SakugaActor.NetsuStockHud)
	MatchSetup.star_hud = [{}, {}]     # Oct 29: Flan's star stacks (SakugaActor.NetsuStarHud)
	MatchSetup.overdrive_hud = [0, 0]  # Oct 26 evening: Overdrive time left (SakugaActor.NetsuOverdriveHud)
	MatchSetup.juggle_hud = [{}, {}]   # Oct 26 c15: juggle meter (SakugaActor.NetsuJuggleHud)
	# EX / super cut-ins draw on top of the HUD (netsu_cut_in.gd)
	var cut_in := Control.new()
	cut_in.name = "CutIn"
	cut_in.set_script(load("res://game/ui/battle_hud/netsu_cut_in.gd"))
	add_child(cut_in)
	# EX / super flash: dark stage + burst of light at the fighter (netsu_super_flash.gd). It goes
	# straight under the CanvasLayer, above the fighters' layer and under this HUD.
	var flash := Control.new()
	flash.name = "NetsuSuperFlash"
	flash.set_script(load("res://game/ui/battle_hud/netsu_super_flash.gd"))
	root.add_child.call_deferred(flash)


## Oct 28: Overdrive presentation state (see _process / _draw_portrait / _draw_meter / _draw_assist).
const OD_FLASH_TIME := 0.7
var _od_prev := [false, false]
var _od_flash := [0.0, 0.0]


## Oct 28: the Overdrive Link (one faster assist recovery) hasn't been used yet.
func _od_link(side: int) -> bool:
	return MatchSetup.overdrive_hud.size() > side and (int(MatchSetup.overdrive_hud[side]) & 2) != 0


func _fit() -> void:
	var view := get_viewport_rect().size
	scale = Vector2.ONE * (view.x / CANVAS.x)
	position = Vector2(0, (view.y - CANVAS.y * scale.y) / 2.0)


func _process(delta: float) -> void:
	_time += delta
	for side in 2:
		_update_combo(side, delta)
		# Oct 28: Overdrive just started: a short flash over the portrait
		var od := _overdrive(side)
		if od and not _od_prev[side]:
			_od_flash[side] = OD_FLASH_TIME
		_od_prev[side] = od
		_od_flash[side] = maxf(0.0, _od_flash[side] - delta)
	queue_redraw()


# --- Reading the engine -----------------------------------------------------------------

func _ratio(node) -> float:
	if node == null or node.max_value <= 0:
		return 0.0
	return clampf(node.value / node.max_value, 0.0, 1.0)


func _rounds_won(side: int) -> int:
	var rounds = _src[side]["rounds"]
	if rounds == null:
		return 0
	var won := 0
	for i in range(1, 6):
		var gem = rounds.get_node_or_null(("Odd/Round%d" if i % 2 == 1 else "Even/Round%d") % i)
		if gem and gem.visible:
			won += 1
	return won


## Tight head shot: actors/<fighter>/Artwork/HUD_Portrait.png if it exists.
func _hud_texture(portrait: Texture2D) -> Texture2D:
	if portrait == null:
		return null
	if not _hud_portraits.has(portrait):
		var path := portrait.resource_path.get_base_dir().path_join("HUD_Portrait.png")
		_hud_portraits[portrait] = load(path) if ResourceLoader.exists(path) else portrait
	return _hud_portraits[portrait]


# --- Drawing helpers -----------------------------------------------------------------------

## Mockup x -> screen x, mirrored for Player 2.
func _x(x: float, side: int) -> float:
	return x * K if side == 0 else CANVAS.x - x * K


func _p(x: float, y: float, side: int) -> Vector2:
	return Vector2(_x(x, side), y * K)


## A list of mockup points -> screen points.
func _pts(points: Array, side: int) -> PackedVector2Array:
	var out := PackedVector2Array()
	for q in points:
		out.append(_p(q.x, q.y, side))
	return out


func _accent(side: int) -> Color:
	return p1_accent if side == 0 else p2_accent


## A slanted band like "/" (mockup coordinates): x_a..x_b along the bottom edge.
func _slanted(x_a: float, x_b: float, y: float, h: float, slant: float, side: int) -> PackedVector2Array:
	return PackedVector2Array([_p(x_a + slant, y, side), _p(x_b + slant, y, side), _p(x_b, y + h, side), _p(x_a, y + h, side)])


func _closed(points: PackedVector2Array) -> PackedVector2Array:
	var out := points.duplicate()
	out.append(points[0])
	return out


## Glowing line: a wide soft stroke under a thin bright one.
func _glow_line(points: PackedVector2Array, color: Color, width: float = 2.0, glow: float = 0.35) -> void:
	draw_polyline(points, Color(color, color.a * glow), width + 6.0, true)
	draw_polyline(points, color, width, true)


func _text(font: Font, pos: Vector2, text: String, size_px: int, color: Color, outline: int = 6) -> void:
	if outline > 0:
		draw_string_outline(font, pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px, outline, Color(outline_color, outline_color.a * color.a))
	draw_string(font, pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px, color)


## Text whose left (P1) / right (P2) end sits at mockup x.
func _side_text(font: Font, x: float, y: float, text: String, size_px: int, color: Color, side: int, outline: int = 6) -> void:
	var w := _width(font, text, size_px)
	var px := _x(x, side) - (0.0 if side == 0 else w)
	_text(font, Vector2(px, y * K), text, size_px, color, outline)


func _width(font: Font, text: String, size_px: int) -> float:
	return font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px).x


func _diamond(at: Vector2, r: float, color: Color, filled: bool) -> void:
	var pts := PackedVector2Array([at + Vector2(0, -r), at + Vector2(r, 0), at + Vector2(0, r), at + Vector2(-r, 0)])
	if filled:
		draw_circle(at, r * 1.6, Color(color, 0.25))
		draw_colored_polygon(pts, color)
		var heart := PackedVector2Array([at + Vector2(0, -r * 0.45), at + Vector2(r * 0.45, 0), at + Vector2(0, r * 0.45), at + Vector2(-r * 0.45, 0)])
		draw_colored_polygon(heart, color.lightened(0.55))
	draw_polyline(_closed(pts), Color(1, 1, 1, 0.95) if filled else color, 1.6, true)


## Small four-point sparkle.
func _sparkle(at: Vector2, r: float, color: Color) -> void:
	draw_line(at + Vector2(-r, 0), at + Vector2(r, 0), color, 1.2, true)
	draw_line(at + Vector2(0, -r), at + Vector2(0, r), color, 1.2, true)


# --- Drawing ----------------------------------------------------------------------------------

func _draw() -> void:
	for side in 2:
		_draw_housing(side)
		_draw_health(side)
		_draw_portrait(side)
		_draw_name_and_rounds(side)
		_draw_burst(side)
		_draw_stock(side)
		_draw_stars(side)
		_draw_meter(side)
		_draw_assist(side)
		_draw_combo(side)
	_draw_timer()


## Hexagon in the corner (mockup points; P2 mirrored). The picture itself is never flipped.
const PORTRAIT := [Vector2(0, 0), Vector2(152, 0), Vector2(171, 45), Vector2(138, 117), Vector2(34, 117), Vector2(0, 72)]
const PORTRAIT_INNER := [Vector2(0, 5), Vector2(148, 5), Vector2(165, 45), Vector2(134, 112), Vector2(37, 112), Vector2(0, 66)]


func _draw_portrait(side: int) -> void:
	var shape := _pts(PORTRAIT, side)
	draw_colored_polygon(shape, backing)
	var node = _src[side]["portrait"]
	var tex: Texture2D = _hud_texture(node.texture if node else null)
	if tex:
		# HUD_Portrait.png is a square picture with the face in its middle; that middle sits on
		# the frame's centre (portrait_center) and the whole picture spans portrait_span mockup px.
		var uvs := PackedVector2Array()
		for q in PORTRAIT:
			var du: float = (q.x - portrait_center.x) / portrait_span
			if side == 1:
				du = -du   # the shape is mirrored, so this keeps the picture as drawn
			uvs.append(Vector2(0.5 + du, 0.5 + (q.y - portrait_center.y) / portrait_span))
		draw_polygon(shape, PackedColorArray([Color.WHITE]), uvs, tex)
	var accent := _accent(side)
	# soft colour wash at the bottom of the picture
	draw_polygon(_pts([Vector2(6, 80), Vector2(155, 80), Vector2(138, 117), Vector2(34, 117)], side),
		PackedColorArray([Color(accent, 0.0), Color(accent, 0.0), Color(accent, 0.35), Color(accent, 0.35)]))
	var rim := _pts(PORTRAIT.slice(1) , side)   # every edge except the screen-edge top
	_glow_line(rim, accent.lightened(0.25), 2.5)
	draw_polyline(_pts(PORTRAIT_INNER.slice(1), side), Color(frame_color, 0.45), 1.2, true)
	# "1P" / "2P" tab
	var tab := _slanted(157, 206, 17, 23, 7, side)
	draw_colored_polygon(tab, accent)
	draw_polyline(_closed(tab), accent.lightened(0.4), 1.2, true)
	var tag := "%dP" % (side + 1)
	var tw := _width(_serif, tag, 24)
	var tc := (tab[0] + tab[2]) / 2.0
	_text(_serif, Vector2(tc.x - tw / 2.0, tc.y + 9), tag, 24, Color.WHITE, 0)
	# Oct 28: Overdrive just started: the portrait flashes white then red, and its rim glows red while it lasts
	var flash: float = _od_flash[side] / OD_FLASH_TIME
	if flash > 0.0:
		var c := Color(1.0, 0.25, 0.2).lerp(Color.WHITE, flash)
		draw_colored_polygon(shape, Color(c, 0.75 * flash))
	if _overdrive(side):
		_glow_line(rim, Color(1.0, 0.3, 0.25, 0.55 + 0.25 * sin(_time * 4.0)), 2.0, 0.5)


## The frame the health bar sits in, the dark strip behind the name, and the line to the rounds.
func _draw_housing(side: int) -> void:
	var accent := _accent(side)
	var x1 := bar_x.y
	var top := bar_y - 11.0
	var body := _pts([Vector2(150, top), Vector2(445, top), Vector2(452, top + 6), Vector2(x1 + 22, top + 6),
		Vector2(x1 + 4, bar_y + bar_height + 7), Vector2(140, bar_y + bar_height + 7)], side)
	draw_colored_polygon(body, Color(backing, 0.6))
	# name strip under the bar, fading out toward the timer
	var strip := _slanted(136, 470, bar_y + bar_height + 7, 25, 6, side)
	draw_polygon(strip, PackedColorArray([Color(backing, 0.75), Color(backing, 0.0), Color(backing, 0.0), Color(backing, 0.75)]))
	# top edge: from the tab, stepping down halfway along
	_glow_line(_pts([Vector2(157, top), Vector2(445, top), Vector2(452, top + 6), Vector2(x1 + 22, top + 6)], side),
		accent.lightened(0.3), 2.0)
	# bottom edge and the slanted end by the timer
	_glow_line(_pts([Vector2(150, bar_y + bar_height + 7), Vector2(x1 + 4, bar_y + bar_height + 7), Vector2(x1 + 22, top + 6)], side),
		Color(accent.lightened(0.2), 0.85), 1.6)
	# fine line + sparkle running up to the round markers
	draw_line(_p(555, 0, side), _p(578, top + 6, side), Color(frame_color, 0.45), 1.2, true)
	_sparkle(_p(557, 35, side), 5.0, Color(frame_color, 0.6))


func _draw_health(side: int) -> void:
	var src: Dictionary = _src[side]
	var hp := _ratio(src["health"])
	var lost := maxf(_ratio(src["lost"]), hp)
	var x0 := bar_x.x
	var x1 := bar_x.y
	var length := x1 - x0
	var y := bar_y
	var h := bar_height
	draw_colored_polygon(_slanted(x0, x1, y, h, bar_slant, side), Color(0.03, 0.05, 0.16, 0.95))
	# Oct 26 c15 (TamaDeez): the bar is anchored at the TIMER end and empties from the portrait side (BlazBlue style):
	# the health left sits next to the timer, the lost part opens up by the portrait.
	if lost > hp:
		draw_colored_polygon(_slanted(x1 - length * lost, x1 - length * hp, y, h, bar_slant, side), damage_color)
	if hp > 0.0:
		var x_start := x1 - length * hp
		var near := bar_dark.lerp(bar_light, 1.0 - hp)   # colour by position: dark at the portrait end, light at the timer
		var far := bar_light
		if _overdrive(side):
			# Oct 28 (TamaDeez): Overdrive = under 35% health: the bar turns red (a slow glow, no danger flashing)
			var glow := 0.5 + 0.5 * sin(_time * 3.0)
			near = overdrive_bar_dark.lerp(overdrive_bar_light, 0.15 * glow)
			far = overdrive_bar_light.lerp(Color(1.0, 0.45, 0.35), 0.25 * glow)
		elif hp <= danger_threshold:
			var pulse := 0.5 + 0.5 * sin(_time * 8.0)
			near = near.lerp(danger_color, 0.4 + 0.4 * pulse)
			far = far.lerp(danger_color, 0.5 + 0.4 * pulse)
		draw_polygon(_slanted(x_start, x1, y, h, bar_slant, side), PackedColorArray([near, far, far.darkened(0.12), near.darkened(0.12)]))
		draw_polygon(_slanted(x_start, x1 - 3, y + 2, h * 0.35, bar_slant * 0.35, side),
			PackedColorArray([Color(1, 1, 1, 0.08), Color(1, 1, 1, 0.45), Color(1, 1, 1, 0.25), Color(1, 1, 1, 0.04)]))
	# tight white frame around the bar
	draw_polyline(_closed(_slanted(x0 - 3, x1 + 3, y - 2, h + 4, bar_slant + 1, side)), Color(frame_color, 0.9), 1.8, true)
	# Overdrive (A+B+C): shown while it runs
	if _overdrive(side):
		var pulse := 0.6 + 0.4 * sin(_time * 5.0)
		_side_text(_serif, 480, 103, "OVERDRIVE", 26, Color(overdrive_color, pulse), side, 3)


## Oct 28: true while this fighter is in Overdrive (health under 35%). The engine reports it through
## MatchSetup.overdrive_hud (SakugaActor.NetsuOverdriveHud: 1 = on, 0 = off).
func _overdrive(side: int) -> bool:
	return MatchSetup.overdrive_hud.size() > side and int(MatchSetup.overdrive_hud[side]) > 0


func _draw_name_and_rounds(side: int) -> void:
	var label = _src[side]["name"]
	var text: String = str(label.text).to_upper() if label else ""
	if text != "":
		_side_text(_thin, name_position.x, name_position.y, text, name_size, text_color, side, 5)
	# rounds: a glowing diamond for each round won, hollow circles for the rest
	var won := _rounds_won(side)
	var accent := _accent(side)
	for i in rounds_to_win:
		var at := _p(rounds_position.x + i * rounds_step, rounds_position.y, side)
		if i < won:
			_diamond(at, 9.0, accent, true)
		else:
			draw_arc(at, 8.0, 0, TAU, 24, Color(0.85, 0.9, 1.0, 0.85), 1.6, true)


func _draw_burst(side: int) -> void:
	var src: Dictionary = _src[side]
	var accent := _accent(side)
	var b := burst_box
	var shape := _slanted(b.position.x, b.end.x, b.position.y, b.size.y, 7, side)
	draw_colored_polygon(shape, Color(backing, 0.9))
	draw_polyline(_closed(shape), Color(accent.lightened(0.3), 0.9), 1.5, true)
	# bright accent line over the label part
	_glow_line(PackedVector2Array([_p(b.position.x + 8, b.position.y - 2, side), _p(b.position.x + 85, b.position.y - 2, side)]),
		accent.lightened(0.5), 2.0)
	var ratio := _ratio(src["will"])
	var lock = src["will_lock"]
	var color := accent
	if ratio >= 0.999:
		color = burst_ready_color.lerp(Color.WHITE, 0.3 + 0.3 * sin(_time * 6.0))
	elif lock and lock.visible:
		color = Color(0.3, 0.3, 0.38)
	var f0 := b.position.x + 87.0
	var f1 := b.end.x - 6.0
	var fy := b.position.y + 3.0
	var fh := b.size.y - 6.0
	draw_colored_polygon(_slanted(f0, f1, fy, fh, 5, side), Color(0.05, 0.07, 0.18))
	if ratio > 0.0:
		draw_polygon(_slanted(f0, f0 + (f1 - f0) * ratio, fy, fh, 5, side),
			PackedColorArray([color.darkened(0.15), color.lightened(0.35), color, color.darkened(0.3)]))
	draw_polyline(_closed(_slanted(f0, f1, fy, fh, 5, side)), Color(frame_color, 0.7), 1.2, true)
	_side_text(_thin, b.position.x + 26, b.position.y + 16, "BURST", 18, Color(1, 1, 1, 0.95), side, 0)
	# Oct 26 evening: the Overdrive timer, just past the end of the Burst gauge (seconds left)
	var od_frames: int = 0   # Oct 28: Overdrive has no timer any more (it lasts while health is under 35%)
	if od_frames > 0:
		var secs := "%.1f" % (float(od_frames) / 60.0)
		var pulse := 0.75 + 0.25 * sin(_time * 8.0)
		_side_text(_serif, b.end.x + 10, b.position.y + 18, secs, 22, Color(overdrive_color.lightened(0.2), pulse), side, 4)


## Oct 26 (TamaDeez): under the Burst gauge, a small badge while the fighter has a resource stocked (Noah: the energy
## Void Grasp / Void Devour stock for his Overflow Ray). Data: MatchSetup.stock_hud (SakugaActor.NetsuStockHud).
func _draw_stock(side: int) -> void:
	var info: Dictionary = MatchSetup.stock_hud[side] if MatchSetup.stock_hud.size() > side else {}
	if info.is_empty() or int(info.get("value", 0)) <= 0 or Time.get_ticks_msec() - int(info.get("msec", 0)) > 600:
		return
	var b := burst_box
	var y := b.end.y + 5.0
	var h := 17.0
	var x0 := b.position.x + 4.0
	var x1 := x0 + 132.0
	var pulse := 0.5 + 0.5 * sin(_time * 6.0)
	var shape := _slanted(x0, x1, y, h, 6, side)
	draw_colored_polygon(shape, Color(backing, 0.92))
	_glow_line(_closed(shape), stock_color.lerp(Color.WHITE, 0.25 * pulse), 1.6, 0.25 + 0.2 * pulse)
	var gem := _p(x0 + 15.0, y + h * 0.5, side)
	_diamond(gem, 6.5 + pulse, stock_color.lerp(Color.WHITE, 0.35 * pulse), true)
	_side_text(_thin, x0 + 28.0, y + 14.0, "STOCK", 15, Color(1, 1, 1, 0.95), side, 3)
	_side_text(_serif, x0 + 80.0, y + 14.5, "READY", 15, Color(stock_color.lightened(0.35), 0.7 + 0.3 * pulse), side, 3)


## Oct 29 (TamaDeez): under the Burst gauge, Flan's star stacks: one star per stack she can hold, lit for each one
## she has. Data: MatchSetup.star_hud (SakugaActor.NetsuStarHud).
func _draw_stars(side: int) -> void:
	var info: Dictionary = MatchSetup.star_hud[side] if MatchSetup.star_hud.size() > side else {}
	if info.is_empty() or Time.get_ticks_msec() - int(info.get("msec", 0)) > 600:
		return
	var value := int(info.get("value", 0))
	var max_value := int(info.get("max", 3))
	if max_value <= 0:
		return
	var b := burst_box
	var y := b.end.y + 5.0
	var h := 17.0
	var x0 := b.position.x + 4.0
	var x1 := x0 + 50.0 + 22.0 * max_value
	var pulse := 0.5 + 0.5 * sin(_time * 6.0)
	var gold := Color(1.0, 0.82, 0.25)
	var shape := _slanted(x0, x1, y, h, 6, side)
	draw_colored_polygon(shape, Color(backing, 0.92))
	_glow_line(_closed(shape), gold.lerp(Color.WHITE, 0.2 * pulse) if value > 0 else Color(gold, 0.35), 1.4, 0.2)
	_side_text(_thin, x0 + 8.0, y + 14.0, "STAR", 15, Color(1, 1, 1, 0.95), side, 3)
	for i in range(max_value):
		var c := _p(x0 + 58.0 + 22.0 * i, y + h * 0.5, side)
		if i < value:
			_sparkle(c, 7.0 + pulse, gold.lerp(Color.WHITE, 0.3 * pulse))
		else:
			_sparkle(c, 5.0, Color(gold, 0.25))


## Hexagon badge with TIME over the number (mockup points around the centre line).
func _draw_timer() -> void:
	var cx := timer_center_x
	var outer := [Vector2(cx - 38, 0), Vector2(cx + 38, 0), Vector2(cx + 66, 62), Vector2(cx + 29, 112),
		Vector2(cx, 124), Vector2(cx - 29, 112), Vector2(cx - 66, 62)]
	var inner := [Vector2(cx - 34, 5), Vector2(cx + 34, 5), Vector2(cx + 60, 62), Vector2(cx + 26, 107),
		Vector2(cx, 118), Vector2(cx - 26, 107), Vector2(cx - 60, 62)]
	var shape := _pts(outer, 0)
	draw_colored_polygon(shape, Color(0.02, 0.04, 0.14, 0.9))
	_glow_line(_closed(shape), Color(frame_color, 0.85), 1.8, 0.3)
	draw_polyline(_closed(_pts(inner, 0)), Color(frame_color, 0.35), 1.0, true)
	for s in [-1.0, 1.0]:   # little sparkles beside the badge
		_sparkle(Vector2((cx + s * 76) * K, 92 * K), 4.0, Color(frame_color, 0.5))
	var c := cx * K
	_text(_thin, Vector2(c - _width(_thin, "TIME", 19) / 2.0, 37 * K), "TIME", 19, Color(0.86, 0.9, 1.0), 0)
	var label = _src["timer"]
	var t: String = str(label.text) if label else "99"
	if t == "--":
		t = "∞"
	_text(_serif, Vector2(c - _width(_serif, t, timer_size) / 2.0, 83 * K), t, timer_size, text_color, 3)


func _draw_meter(side: int) -> void:
	var node = _src[side]["meter"]
	var value: float = node.value if node else 0.0
	var max_value: float = node.max_value if node and node.max_value > 0 else 40000.0
	var stocks := maxi(1, int(round(max_value / meter_per_stock)))
	var percent := int(value / meter_per_stock * 100.0)
	var accent := _accent(side)
	var bright := accent.lightened(0.45)
	var c0 := meter_cells_x.x
	var c1 := meter_cells_x.y
	# 1. coloured light panel spreading out of the corner, with diagonal streaks
	var panel := [Vector2(0, 733), Vector2(33, 740), Vector2(50, 766), Vector2(100, 769), Vector2(110, 779),
		Vector2(330, 779), Vector2(292, 816), Vector2(0, 816)]
	var cols := PackedColorArray()
	for q in panel:
		cols.append(Color(accent.darkened(0.15), 0.6 * clampf(1.0 - q.x / 340.0, 0.0, 1.0)))
	draw_polygon(_pts(panel, side), cols)
	draw_polygon(_pts([Vector2(0, 769), Vector2(100, 769), Vector2(110, 779), Vector2(60, 816), Vector2(0, 816)], side),
		PackedColorArray([Color(accent, 0.35), Color(accent, 0.25), Color(accent, 0.2), Color(accent, 0.1), Color(accent, 0.3)]))
	for streak in [[Vector2(190, 763), Vector2(142, 816), 0.9], [Vector2(312, 769), Vector2(268, 816), 0.55],
			[Vector2(122, 784), Vector2(97, 816), 0.4]]:
		_glow_line(PackedVector2Array([_p(streak[0].x, streak[0].y, side), _p(streak[1].x, streak[1].y, side)]),
			Color(bright, streak[2]), 1.6)
	_glow_line(_pts([Vector2(33, 740), Vector2(0, 770)], side), bright, 2.0)
	_glow_line(_pts([Vector2(0, 769), Vector2(100, 769), Vector2(110, 779), Vector2(320, 779)], side), Color(bright, 0.9), 1.6)
	# 2. track behind the cells and the dark strip for the caption
	draw_colored_polygon(_pts([Vector2(170, 733), Vector2(c1 + 3, 733), Vector2(c1 - 11, 762), Vector2(158, 762)], side),
		Color(0.02, 0.04, 0.16, 0.6))
	draw_polygon(_pts([Vector2(150, 762), Vector2(c1 - 11, 762), Vector2(c1 - 20, 783), Vector2(140, 783)], side),
		PackedColorArray([Color(0.02, 0.04, 0.16, 0.2), Color(0.02, 0.04, 0.16, 0.6), Color(0.02, 0.04, 0.16, 0.6), Color(0.02, 0.04, 0.16, 0.2)]))
	_glow_line(_pts([Vector2(176, 729), Vector2(300, 729), Vector2(305, 733), Vector2(c1 + 3, 733)], side), Color(frame_color, 0.75), 1.3, 0.25)
	_sparkle(_p(302, 727, side), 4.0, Color(bright, 0.9))
	_glow_line(_pts([Vector2(c1 + 18, 740), Vector2(c1 - 4, 765)], side), bright, 2.5)   # end stroke
	# 3. hexagon holding the percentage
	var hex := _pts([Vector2(33, 740), Vector2(50, 714), Vector2(163, 714), Vector2(176, 729), Vector2(165, 765), Vector2(50, 765)], side)
	draw_polygon(hex, PackedColorArray([Color(0.04, 0.07, 0.24, 0.94), Color(0.06, 0.1, 0.3, 0.94), Color(0.03, 0.05, 0.2, 0.94),
		Color(0.02, 0.04, 0.16, 0.94), Color(0.02, 0.04, 0.16, 0.94), Color(0.03, 0.05, 0.2, 0.94)]))
	_glow_line(_pts([Vector2(176, 729), Vector2(163, 714), Vector2(50, 714), Vector2(33, 740), Vector2(50, 765), Vector2(150, 765), Vector2(165, 779)], side),
		Color(bright, 0.95), 1.8)
	draw_polyline(_pts([Vector2(160, 719), Vector2(53, 719), Vector2(39, 740), Vector2(53, 760), Vector2(148, 760)], side), Color(frame_color, 0.3), 1.0, true)
	for corner in [Vector2(52, 715), Vector2(150, 715)]:   # little bright ticks on the top corners
		draw_line(_p(corner.x - 4, corner.y, side), _p(corner.x + 6, corner.y, side), Color(1, 1, 1, 0.9), 2.5, true)
	# 4. the cells: one per bar (10000 = 100%)
	var gap := 3.0
	var cell := (c1 - c0 - gap * (stocks - 1)) / stocks
	var cy := 739.0
	var ch := 20.0
	var slant := 8.0
	var level := value / meter_per_stock
	if level > 0.0:   # gold light leaking out under the first cell
		_glow_line(_pts([Vector2(c0 - 6, cy + ch + 3), Vector2(c0 + 14, cy + ch + 3)], side), Color(meter_color, 0.8), 2.0, 0.4)
	for i in stocks:
		var cx0 := c0 + i * (cell + gap)
		var shape := _slanted(cx0, cx0 + cell, cy, ch, slant, side)
		draw_colored_polygon(shape, Color(0.05, 0.07, 0.2, 0.95))
		var fill := clampf(level - i, 0.0, 1.0)
		if fill > 0.0:
			var top := meter_light
			var bottom := meter_color
			draw_polygon(_slanted(cx0, cx0 + cell * fill, cy, ch, slant, side),
				PackedColorArray([top, top, bottom, bottom]))
			draw_polygon(_slanted(cx0 + 2, cx0 + cell * fill, cy + 1, ch * 0.3, slant * 0.3, side),
				PackedColorArray([Color(1, 1, 1, 0.3), Color(1, 1, 1, 0.3), Color(1, 1, 1, 0.0), Color(1, 1, 1, 0.0)]))
			if fill < 1.0:   # the bar still filling: a bright flare at its tip
				var tip_x := cx0 + cell * fill
				draw_line(_p(tip_x + slant, cy, side), _p(tip_x, cy + ch, side), Color(1, 0.98, 0.85, 0.95), 2.5, true)
				draw_line(_p(tip_x + slant - 4, cy - 1, side), _p(tip_x + slant + 14, cy - 1, side), Color(1, 0.95, 0.7, 0.8), 2.0, true)
		draw_polyline(_closed(shape), Color(1, 1, 1, 0.85), 1.5, true)
	# Oct 28: Overdrive: a brighter frame around the Craft Gauge
	if _overdrive(side):
		var glow := 0.7 + 0.3 * sin(_time * 5.0)
		_glow_line(_closed(_slanted(c0 - 5, c1 + 5, cy - 4, ch + 8, slant, side)), Color(1.0, 0.92, 0.6, glow), 2.5, 0.7)
		_glow_line(_pts([Vector2(176, 729), Vector2(163, 714), Vector2(50, 714), Vector2(33, 740), Vector2(50, 765), Vector2(150, 765), Vector2(165, 779)], side),
			Color(1.0, 0.95, 0.75, glow), 2.6, 0.6)
	# 5. text
	var num := str(percent)
	var nsize := 50
	var ssize := 38
	var nw := _width(_serif, num, nsize)
	var sw := _width(_serif, "%", ssize)
	var px := _x(106, side) - (nw + 3.0 + sw) / 2.0
	var base := 751.0 * K
	for part in [[num, nsize, px], ["%", ssize, px + nw + 3.0]]:
		var at := Vector2(part[2], base)
		draw_string_outline(_serif, at, part[0], HORIZONTAL_ALIGNMENT_LEFT, -1, part[1], 12, Color(1.0, 0.75, 0.3, 0.25))
		draw_string_outline(_serif, at, part[0], HORIZONTAL_ALIGNMENT_LEFT, -1, part[1], 6, Color(0.25, 0.13, 0.04, 0.95))
		draw_string(_serif, at, part[0], HORIZONTAL_ALIGNMENT_LEFT, -1, part[1], percent_color)
	_spaced_text(_thin, 357, 775, meter_caption, 17, 149.0, Color(1, 1, 1, 0.92), side)


## The assist row: a small hexagon with the assist's face, its name and the refill bar.
## Ready: the bar glows gold and READY pulses. While the assist is on screen the bar is empty.
## A buff it gave (Mary's 5S) shows as a thin teal bar under it, running down.
func _draw_assist(side: int) -> void:
	var info: Dictionary = MatchSetup.assist_hud[side] if MatchSetup.assist_hud.size() > side else {}
	if info.is_empty() or Time.get_ticks_msec() - int(info.get("msec", 0)) > 600:
		return
	var accent := _accent(side)
	var y := assist_y
	var ratio: float = clampf(float(info.get("ratio", 0.0)), 0.0, 1.0)
	var phase: int = int(info.get("phase", 0))
	var ready := phase == 0
	# hexagon with the face
	var hexa := [Vector2(42, y), Vector2(94, y), Vector2(108, y + 19), Vector2(94, y + 38), Vector2(42, y + 38), Vector2(28, y + 19)]
	var shape := _pts(hexa, side)
	draw_colored_polygon(shape, backing)
	var tex = info.get("icon")
	if tex is Texture2D:
		var uvs := PackedVector2Array()
		for q in hexa:
			var du: float = (q.x - 68.0) / 80.0
			if side == 1:
				du = -du
			uvs.append(Vector2(0.5 + du, 0.5 + (q.y - (y + 19.0)) / 80.0))
		draw_polygon(shape, PackedColorArray([Color.WHITE if ready else Color(0.62, 0.64, 0.72)]), uvs, tex)
	var rim_color := assist_ready_color.lerp(Color.WHITE, 0.3 + 0.3 * sin(_time * 6.0)) if ready else accent.lightened(0.25)
	_glow_line(_closed(shape), rim_color, 2.0, 0.35 if ready else 0.2)
	# Oct 28: Overdrive Link marker (the next assist call comes back faster)
	if _od_link(side):
		var link_c := Color(1.0, 0.35, 0.25).lerp(Color(1.0, 0.85, 0.45), 0.5 + 0.5 * sin(_time * 5.0))
		_diamond(_p(14, y + 19, side), 7.0, link_c, true)
		_diamond(_p(14, y + 19, side), 10.0, Color(link_c, 0.6), false)
	# name and READY
	var label := str(info.get("name", "")).to_upper()
	_side_text(_thin, 116, y + 12, label, 17, Color(1, 1, 1, 0.95), side, 4)
	if ready:
		var pulse := 0.65 + 0.35 * sin(_time * 6.0)
		_side_text(_serif, 236, y + 13, "READY", 18, Color(assist_ready_color, pulse), side, 3)
	elif phase == 1:
		_side_text(_thin, 236, y + 12, "IN PLAY", 15, Color(accent.lightened(0.5), 0.9), side, 3)
	# the refill bar
	var x0 := 114.0
	var x1 := 300.0
	var by := y + 19.0
	var bh := 11.0
	draw_colored_polygon(_slanted(x0, x1, by, bh, 5, side), Color(0.03, 0.05, 0.16, 0.95))
	if ratio > 0.0:
		var c := assist_ready_color if ready else assist_fill_color
		if ready:
			c = c.lerp(Color.WHITE, 0.15 + 0.15 * sin(_time * 6.0))
		draw_polygon(_slanted(x0, x0 + (x1 - x0) * ratio, by, bh, 5, side),
			PackedColorArray([c.darkened(0.1), c.lightened(0.3), c, c.darkened(0.3)]))
	draw_polyline(_closed(_slanted(x0, x1, by, bh, 5, side)), Color(frame_color, 0.75), 1.3, true)
	# buff time left
	var buff: float = clampf(float(info.get("buff", 0.0)), 0.0, 1.0)
	if buff > 0.0:
		var bx1 := x0 + (x1 - x0) * buff
		draw_colored_polygon(_slanted(x0, bx1, by + bh + 3.0, 4.0, 2, side), Color(assist_buff_color, 0.9))
		_side_text(_thin, x1 + 10, by + bh + 7, "♪", 16, assist_buff_color, side, 3)


## Text stretched with letter spacing to a set width (screen px); left end at mockup x (right end for P2).
func _spaced_text(font: Font, x: float, y: float, text: String, size_px: int, width: float, color: Color, side: int) -> void:
	var raw := 0.0
	for ch in text:
		raw += _width(font, ch, size_px)
	var extra := (width - raw) / maxf(1.0, text.length() - 1)
	var px := _x(x, side) - (0.0 if side == 0 else width)
	for ch in text:
		draw_string_outline(font, Vector2(px, y * K), ch, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px, 4, Color(outline_color, 0.7))
		draw_string(font, Vector2(px, y * K), ch, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px, color)
		px += _width(font, ch, size_px) + extra


# --- Combo counter -------------------------------------------------------------------------------
# Data: Mahou's ComboCounter (ComboCount label, StunBar) + line 2 of the training info (combo damage).

func _combo_hits(side: int) -> int:
	var node = _src[side]["combo"]
	if node == null or not node.visible:
		return 0
	var label = node.get_node_or_null("ComboCount")
	return int(str(label.text)) if label else 0


func _update_combo(side: int, delta: float) -> void:
	var hits := _combo_hits(side)
	var showing := hits >= combo_min_hits
	if showing:
		if hits != _combo_last[side]:
			_combo_pop[side] = 1.0
		_combo_last[side] = hits
		var info = _src[side]["info"]
		if info:
			var lines := str(info.text).split("\n")
			if lines.size() > 1:
				_combo_damage[side] = lines[1]
	_combo_alpha[side] = move_toward(_combo_alpha[side], 1.0 if showing else 0.0, delta * (8.0 if showing else 2.5))
	_combo_pop[side] = move_toward(_combo_pop[side], 0.0, delta * 6.0)


## Oct 26 c15 (TamaDeez): the juggle meter under the combo counter (BlazBlue / Under Night style combos).
##   Top bar  = time before the victim can tech (their hitstun left, out of what the last hit gave).
##   Thin bar = juggle left: it shrinks as the combo goes on (MatchSetup.juggle_hud "decay"); the longer the combo,
##              the less hitstun every hit gives, until they tech out. Colour runs green -> yellow -> red with it.
##   Labels: TECH! (they can tech now: another hit is an invalid combo), AIR COUNTER (purple: no tech until they land),
##   INVALID, DOWN (hard knockdown).
##   Oct 26 c20: while they lie on the floor the top bar shows the OTG window instead (cyan, label OTG): how long they
##   can still be hit down there. It's shorter the more the combo is scaled. Empty = DOWN (they can't be hit, getting up).
## Settings: juggle_* exports. Data: MatchSetup.juggle_hud[victim] (engine: SakugaActor.NetsuJuggleHud).
func _draw_juggle(side: int, a: float, ly: float, x_near: float, x_far: float, accent: Color) -> void:
	var victim := 1 - side
	var d: Dictionary = MatchSetup.juggle_hud[victim] if MatchSetup.juggle_hud.size() > victim else {}
	if d.is_empty():
		return
	var y := ly + juggle_offset_y
	var x0 := x_near + 14.0
	var x1 := x_far - 40.0
	var w := x1 - x0
	var h := juggle_height
	var active: bool = d.get("active", false)
	var left := float(d.get("left", 0))
	var mx := maxf(1.0, float(d.get("max", 1)))
	var decay := clampf(float(d.get("decay", 0)) / 1000.0, 0.0, 1.0)
	var locked: bool = d.get("locked", false)
	var invalid: bool = d.get("invalid", false)
	var down: bool = d.get("down", false)
	var lying: bool = d.get("lying", false)
	var otg_left := float(d.get("otg_left", 0))
	var otg_max := float(d.get("otg_max", 0))
	var ratio := clampf(left / mx, 0.0, 1.0) if active else 0.0
	# track
	draw_colored_polygon(_slanted(x0, x1, y, h, 6.0, side), Color(0.02, 0.03, 0.1, 0.85 * a))
	var col := juggle_fresh.lerp(juggle_mid, clampf(decay * 2.0, 0.0, 1.0))
	if decay > 0.5:
		col = juggle_mid.lerp(juggle_spent, (decay - 0.5) * 2.0)
	var label := ""
	if locked:
		col = juggle_locked.lerp(Color.WHITE, 0.25 + 0.25 * sin(_time * 10.0))
		ratio = 1.0
		label = "AIR COUNTER"
	elif invalid:
		col = Color(0.55, 0.55, 0.62)
		label = "INVALID"
	elif lying:
		ratio = clampf(otg_left / otg_max, 0.0, 1.0) if otg_max > 0.0 else 0.0
		col = juggle_otg
		label = "OTG" if otg_left > 0.0 else "DOWN"
	elif down:
		ratio = 1.0
		col = col.darkened(0.25)
		label = "DOWN"
	elif active and left <= 0.0:
		label = "TECH!" if fmod(_time, 0.3) < 0.18 else ""
	if ratio > 0.0:
		draw_colored_polygon(_slanted(x0, x0 + w * ratio, y, h, 6.0, side), Color(col, a))
		draw_colored_polygon(_slanted(x0, x0 + w * ratio, y, h * 0.35, 2.0, side), Color(1, 1, 1, 0.25 * a))
	draw_polyline(_closed(_slanted(x0, x1, y, h, 6.0, side)), Color(accent.lightened(0.4), 0.7 * a), 1.2, true)
	# juggle left (thin line under it)
	var jy := y + h + 4.0
	draw_line(_p(x0, jy, side), _p(x1, jy, side), Color(0.02, 0.03, 0.1, 0.8 * a), 3.0)
	if 1.0 - decay > 0.0:
		draw_line(_p(x0, jy, side), _p(x0 + w * (1.0 - decay), jy, side), Color(col if not locked else juggle_fresh, 0.95 * a), 3.0)
	# caption + state text
	var cap_x := (x0 - 4.0) * K if side == 0 else CANVAS.x - (x0 - 4.0) * K
	var cap_size := 15
	var cw := _width(_thin, juggle_caption, cap_size)
	_text(_thin, Vector2(cap_x if side == 0 else cap_x - cw, (y - 4.0) * K), juggle_caption, cap_size, Color(0.85, 0.93, 1.0, 0.85 * a), 3)
	if label != "":
		var ls := 22
		var lw := _width(_serif, label, ls)
		var lx := (x1 + 10.0) * K if side == 0 else CANVAS.x - (x1 + 10.0) * K - lw
		var lc := juggle_locked if locked else (Color(1.0, 0.35, 0.3) if label == "TECH!" else (juggle_otg if label == "OTG" else Color(0.85, 0.88, 0.95)))
		_text(_serif, Vector2(lx, (y + h) * K + 2.0), label, ls, Color(lc, a), 4)


func _draw_combo(side: int) -> void:
	var a := _combo_alpha[side]
	if a <= 0.01:
		return
	var accent := _accent(side)
	var hits := str(_combo_last[side])
	var pop := _combo_pop[side]
	var num_size := int(combo_number_size * (1.0 + 0.16 * pop))
	var num_w := _width(_serif, hits, num_size)
	var lab_w := _width(_serif, combo_label, combo_label_size)
	var total := num_w + 8.0 + lab_w
	var x := combo_position.x * K if side == 0 else CANVAS.x - combo_position.x * K - total
	var y := combo_position.y * K
	draw_string_outline(_serif, Vector2(x, y), hits, HORIZONTAL_ALIGNMENT_LEFT, -1, num_size, 16, Color(accent, 0.3 * a))
	draw_string_outline(_serif, Vector2(x, y), hits, HORIZONTAL_ALIGNMENT_LEFT, -1, num_size, 7, Color(accent.darkened(0.2), a))
	draw_string(_serif, Vector2(x, y), hits, HORIZONTAL_ALIGNMENT_LEFT, -1, num_size, Color(1, 1, 1, a))
	draw_string_outline(_serif, Vector2(x + num_w + 8.0, y - 4), combo_label, HORIZONTAL_ALIGNMENT_LEFT, -1, combo_label_size, 5, Color(accent.darkened(0.2), a))
	draw_string(_serif, Vector2(x + num_w + 8.0, y - 4), combo_label, HORIZONTAL_ALIGNMENT_LEFT, -1, combo_label_size, Color(1, 1, 1, a))
	# damage panel: bright line under the number, dark band, thin line under the damage
	var line_y := y + 17.0
	var ly := line_y / K
	var x_near := 62.0     # slanted start of the panel
	var x_far := 360.0
	var band := PackedVector2Array([_p(x_near, ly, side), _p(x_far, ly, side), _p(x_far - 26, ly + 35, side),
		_p(x_near - 8, ly + 35, side), _p(x_near - 18, ly + 17, side)])
	draw_polygon(band, PackedColorArray([Color(backing, 0.75 * a), Color(backing, 0.0), Color(backing, 0.0),
		Color(backing, 0.75 * a), Color(backing, 0.75 * a)]))
	draw_polyline(PackedVector2Array([_p(x_near - 18, ly + 17, side), _p(x_near, ly, side), _p(x_far, ly, side)]),
		Color(accent, 0.35 * a), 7.0, true)
	draw_polyline(PackedVector2Array([_p(x_near - 18, ly + 17, side), _p(x_near, ly, side), _p(x_far, ly, side)]),
		Color(accent.lightened(0.45), 0.95 * a), 2.0, true)
	draw_line(_p(x_near - 18, ly + 17, side), _p(x_near - 8, ly + 35, side), Color(accent.lightened(0.3), 0.8 * a), 1.5, true)
	draw_line(_p(x_near - 8, ly + 35, side), _p(250, ly + 35, side), Color(accent.lightened(0.3), 0.6 * a), 1.5, true)
	_draw_juggle(side, a, ly, x_near, x_far, accent)
	var dmg := _combo_damage[side]
	if dmg != "" and dmg != "0":
		var dsize := 40
		var lsize := 22
		var dw := _width(_serif, dmg, dsize)
		var lw := _width(_serif, combo_damage_label, lsize)
		var dx := 90.0 * K if side == 0 else CANVAS.x - 90.0 * K - dw - 8.0 - lw
		_text(_serif, Vector2(dx, line_y + dsize + 2.0), dmg, dsize, Color(1, 1, 1, a), 4)
		_text(_serif, Vector2(dx + dw + 8.0, line_y + dsize), combo_damage_label, lsize, Color(0.85, 0.93, 1.0, a), 3)
