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
## Bottom-left: percentage and Craft Point cells on one clean plate, "CRAFT POINTS".
## Oct 30 (TamaDeez, after the Climax-style reference): name above the bar by the 1P tab, BURST diamond under the bar
## by the portrait, the ASSIST card under the portrait (dimmed with a countdown when used), TIME shield.
## Assist data comes from the engine through MatchSetup.assist_hud.
## Nov 2 (TamaDeez, after the polished reference screenshot): thicker bright-outlined bar housing whose timer end runs
## parallel to the timer's side, red-pink bar for P2, wider flat-bottomed TIME panel (Burst diamond kept as it was),
## angular assist card with a bigger countdown diamond, and a new Craft Gauge plate (big
## percentage block, larger gold segments, CRAFT POINTS centred under them). Old version: _backup_stage_select/pre_hud_nov02/.

const K := 1920.0 / 1456.0
## Read by netsu_match_overlay.gd (it nudges the combo counter in training).
var layout_scale := K

@export_group("Colours")
@export var p1_accent: Color = Color(0.25, 0.6, 1.0)
@export var p2_accent: Color = Color(1.0, 0.22, 0.35)
@export var bar_dark: Color = Color(0.1, 0.39, 1.0)          ## P1 health fill near the portrait
@export var bar_light: Color = Color(0.4, 0.97, 1.0)         ## P1 health fill near the timer
@export var p2_bar_dark: Color = Color(0.9, 0.12, 0.36)      ## Nov 2: P2 health fill near the portrait
@export var p2_bar_light: Color = Color(1.0, 0.68, 0.8)      ## Nov 2: P2 health fill near the timer
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
@export var meter_color: Color = Color(1.0, 0.77, 0.22)
@export var meter_light: Color = Color(1.0, 0.92, 0.6)
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
@export var bar_x: Vector2 = Vector2(161, 653)     ## health fill: portrait end (bottom corner) / timer end (top corner)
@export var bar_y: float = 58.0
@export var bar_height: float = 28.0
@export var bar_slant: float = 7.0                 ## portrait end leans "/" by this much
@export var bar_end_slant: float = 10.5            ## Nov 2: timer end leans "\" by this much (parallel to the timer's side)
## Where the eyes (the middle of HUD_Portrait.png) sits in the corner frame, and how wide the whole picture is.
@export var portrait_center: Vector2 = Vector2(88, 70)
@export var portrait_span: float = 190.0
@export var name_position: Vector2 = Vector2(236, 45)   ## left end of the name's baseline (Oct 30: above the bar, beside the 1P tab)
@export var name_size: int = 24
## Oct 30: only places the STOCK / STAR badges now (under the bar, past the Burst diamond).
@export var burst_box: Rect2 = Rect2(150, 105, 150, 19)
@export var rounds_position: Vector2 = Vector2(612, 37)  ## first round marker (Nov 2: just outside the timer)
@export var rounds_step: float = 22.0
@export var rounds_to_win: int = 2   ## replaced by the match's real "rounds to win" when a fight starts
@export var timer_center_x: float = 728.0
@export var timer_size: int = 64
@export var timer_top: float = 16.0          ## Nov 2: the TIME panel's top edge / half widths (top, bottom) / bottom (mockup px)
@export var timer_half_width: Vector2 = Vector2(77, 43)
@export var timer_bottom: float = 113.0
@export var timer_warning: int = 10      ## Oct 30: at this many seconds or fewer the number turns red and pulses

@export_group("Burst Diamond")
@export var burst_center: Vector2 = Vector2(318, 103)    ## middle of the diamond (mockup px, P1); Nov 2: inside the Burst tab
@export var burst_size: float = 12.5                     ## centre to tip (mockup px)
## Nov 2: the Burst tab, part of the bar housing: hangs under it from the portrait to this x (top edge), down to the
## portrait's bottom (y 117); its end leans like the portrait's edge.
@export var burst_tab_end: float = 352.0
@export var burst_tab_bottom: float = 117.0
@export var burst_label: String = "BURST"

@export_group("Craft Gauge")
@export var meter_caption: String = "CRAFT GAUGE"
@export var meter_per_stock: int = 10000     ## 10000 = 100% (Oct 29: units x5; was 2000)
@export var meter_cells_x: Vector2 = Vector2(170, 474)    ## the cell row (left end / right end, bottom edge)
## Nov 2: Craft Gauge cap outside Overdrive (engine SakugaParameters.CraftCapNormal); bars above it are drawn locked.
@export var meter_normal_cap: float = 30000.0
@export var meter_y: float = 701.0                        ## top of the Craft Gauge plate (mockup px)

@export_group("Assist Gauge")
@export var assist_ready_color: Color = Color(1.0, 0.86, 0.45)
@export var stock_color: Color = Color(0.72, 0.35, 1.0)   ## Oct 26: the STOCK READY badge under the Burst gauge (Noah)
@export var assist_fill_color: Color = Color(0.55, 0.85, 1.0)
@export var assist_buff_color: Color = Color(0.45, 1.0, 0.8)
@export var assist_y: float = 128.0          ## Oct 30: top of the assist card under the portrait (mockup px)
@export var assist_card_x: Vector2 = Vector2(11, 139)  ## card's bottom edge: screen-edge end / inner end (mockup px)
@export var assist_card_height: float = 53.0
@export var assist_gray: Color = Color(0.72, 0.72, 0.76)   ## how the grey (used) picture is tinted

@export_group("Combo Counter")
@export var combo_position: Vector2 = Vector2(95, 300)   ## P1: left end of the number's baseline (Oct 30: lower, under the assist card)
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


## Oct 30: Burst diamond / assist card / timer animation state.
const BURST_FLASH_TIME := 0.45
const ASSIST_FLASH_TIME := 0.6
var _burst_was_ready := [true, true]
var _burst_used_flash := [0.0, 0.0]     # Burst just used: the diamond empties with a burst of light
var _burst_ready_flash := [0.0, 0.0]    # Burst just refilled: the diamond lights up
var _assist_prev_phase := [0, 0]
var _assist_flash := [0.0, 0.0]         # assist ready again: the card flashes in the side's colour
var _gray_icons := {}                   # assist icon -> grey copy (made once)
var _timer_text := ""
var _timer_pop := 0.0                   # the number just changed: it pops
var _timer_since := 0.0                 # seconds since it last changed (drives the sweep under the number)


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
		# Oct 30: Burst used / refilled
		var ready := _burst_ready(side)
		if _burst_was_ready[side] and not ready:
			_burst_used_flash[side] = BURST_FLASH_TIME
		elif ready and not _burst_was_ready[side]:
			_burst_ready_flash[side] = BURST_FLASH_TIME
		_burst_was_ready[side] = ready
		_burst_used_flash[side] = maxf(0.0, _burst_used_flash[side] - delta)
		_burst_ready_flash[side] = maxf(0.0, _burst_ready_flash[side] - delta)
		# Oct 30: assist ready again
		var info: Dictionary = MatchSetup.assist_hud[side] if MatchSetup.assist_hud.size() > side else {}
		if not info.is_empty():
			var phase := int(info.get("phase", 0))
			if phase == 0 and _assist_prev_phase[side] != 0:
				_assist_flash[side] = ASSIST_FLASH_TIME
			_assist_prev_phase[side] = phase
		_assist_flash[side] = maxf(0.0, _assist_flash[side] - delta)
	# Oct 30: the timer number pops when it changes
	var label = _src.get("timer")
	var t: String = str(label.text) if label else ""
	if t != _timer_text:
		if _timer_text != "":
			_timer_pop = 1.0
		_timer_text = t
		_timer_since = 0.0
	_timer_since += delta
	_timer_pop = move_toward(_timer_pop, 0.0, delta * 5.0)
	queue_redraw()


## Oct 30: Burst is full and not locked.
func _burst_ready(side: int) -> bool:
	if not _src.has(side):
		return true
	var lock = _src[side]["will_lock"]
	return _ratio(_src[side]["will"]) >= 0.999 and not (lock != null and lock.visible)


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
	# Nov 2: bigger, sitting on the bar housing's top line, with a thin outline-only slash after it
	var tab := _slanted(160, 207, 26, 23, 8, side)
	draw_colored_polygon(tab, accent)
	draw_polyline(_closed(tab), accent.lightened(0.4), 1.2, true)
	draw_polyline(_closed(_slanted(212, 222, 26, 23, 8, side)), Color(accent.lightened(0.3), 0.8), 1.2, true)
	var tag := "%dP" % (side + 1)
	var tw := _width(_serif, tag, 27)
	var tc := (tab[0] + tab[2]) / 2.0
	_text(_serif, Vector2(tc.x - tw / 2.0, tc.y + 10), tag, 27, Color.WHITE, 0)
	# Oct 28: Overdrive just started: the portrait flashes white then red, and its rim glows red while it lasts
	var flash: float = _od_flash[side] / OD_FLASH_TIME
	if flash > 0.0:
		var c := Color(1.0, 0.25, 0.2).lerp(Color.WHITE, flash)
		draw_colored_polygon(shape, Color(c, 0.75 * flash))
	if _overdrive(side):
		_glow_line(rim, Color(1.0, 0.3, 0.25, 0.55 + 0.25 * sin(_time * 4.0)), 2.0, 0.5)


## The frame the health bar sits in (Nov 2: a dark body with a bright outline a few px out from the bar; its timer end
## runs "\" parallel to the timer's side), and the faint strip behind the name.
func _draw_housing(side: int) -> void:
	var accent := _accent(side)
	var x1 := bar_x.y
	var top := bar_y - 5.0
	var bottom := bar_y + bar_height + 3.0
	var k := bar_end_slant / bar_height          # how far the timer end moves right per mockup px down
	var right_top := x1 + 5.0
	var right_bottom := right_top + k * (bottom - top)
	# Nov 2: the Burst tab is part of the housing: one body, the bar on top, the tab hanging under it by the portrait
	var tab_b := burst_tab_bottom
	var tab_end_b := burst_tab_end + (_portrait_edge_x(tab_b) - _portrait_edge_x(bottom))   # leans like the portrait edge
	var body := _pts([Vector2(150, top), Vector2(right_top, top), Vector2(right_bottom, bottom), Vector2(burst_tab_end, bottom),
		Vector2(tab_end_b, tab_b), Vector2(120, tab_b), Vector2(120, bottom)], side)
	draw_colored_polygon(body, Color(backing, 0.88))
	# the name sits above the bar, on a faint strip fading out toward the timer
	var strip := _slanted(205, 420, top - 24, 22, 5, side)
	draw_polygon(strip, PackedColorArray([Color(backing, 0.0), Color(backing, 0.0), Color(backing, 0.6), Color(backing, 0.6)]))
	# outline: bright along the top and the timer end, the side's colour along the bottom
	var light := accent.lerp(Color(0.75, 0.95, 1.0), 0.55)
	_glow_line(_pts([Vector2(157, top), Vector2(right_top, top), Vector2(right_bottom, bottom)], side), light, 2.2, 0.28)
	_glow_line(_pts([Vector2(right_bottom, bottom), Vector2(burst_tab_end, bottom), Vector2(tab_end_b, tab_b),
		Vector2(_portrait_edge_x(tab_b) - 2.0, tab_b)], side), accent.lightened(0.15), 2.0, 0.28)
	# a faint seam where the tab meets the bar's frame
	draw_line(_p(_portrait_edge_x(bottom), bottom, side), _p(burst_tab_end - 4.0, bottom, side), Color(light, 0.18), 1.0, true)


## The bar's shape between two points along it (mockup x of the bottom-left corner / top-right corner): the portrait end
## leans "/" (bar_slant) and the timer end "\" (bar_end_slant). Nov 2.
func _bar_poly(xa: float, xb: float, y: float, h: float, side: int, end_cut: bool) -> PackedVector2Array:
	var k := bar_end_slant / bar_height
	var br := xb + k * h if end_cut else xb - bar_slant * h / bar_height
	return _pts([Vector2(xa + bar_slant * h / bar_height, y), Vector2(xb, y), Vector2(br, y + h), Vector2(xa, y + h)], side)


func _draw_health(side: int) -> void:
	var src: Dictionary = _src[side]
	var hp := _ratio(src["health"])
	var lost := maxf(_ratio(src["lost"]), hp)
	var x0 := bar_x.x
	var x1 := bar_x.y
	var length := x1 - x0
	var y := bar_y
	var h := bar_height
	draw_colored_polygon(_bar_poly(x0, x1, y, h, side, true), Color(0.02, 0.04, 0.13, 0.96))
	# Oct 26 c15 (TamaDeez): the bar is anchored at the TIMER end and empties from the portrait side (BlazBlue style):
	# the health left sits next to the timer, the lost part opens up by the portrait.
	if lost > hp:
		draw_colored_polygon(_bar_poly(x1 - length * lost, x1 - length * hp, y, h, side, false), damage_color)
	if hp > 0.0:
		var x_start := x1 - length * hp
		var dark := bar_dark if side == 0 else p2_bar_dark
		var light := bar_light if side == 0 else p2_bar_light
		var near := dark.lerp(light, 1.0 - hp)   # colour by position: dark at the portrait end, light at the timer
		var far := light
		if _overdrive(side):
			# Oct 28 (TamaDeez): Overdrive = under 35% health: the bar turns red (a slow glow, no danger flashing)
			var glow := 0.5 + 0.5 * sin(_time * 3.0)
			near = overdrive_bar_dark.lerp(overdrive_bar_light, 0.15 * glow)
			far = overdrive_bar_light.lerp(Color(1.0, 0.45, 0.35), 0.25 * glow)
		elif hp <= danger_threshold:
			var pulse := 0.5 + 0.5 * sin(_time * 8.0)
			near = near.lerp(danger_color, 0.4 + 0.4 * pulse)
			far = far.lerp(danger_color, 0.5 + 0.4 * pulse)
		draw_polygon(_bar_poly(x_start, x1, y, h, side, true), PackedColorArray([near, far, far.darkened(0.18), near.darkened(0.18)]))
		# sheen along the top third, a thin bright edge on top
		draw_polygon(_bar_poly(x_start, x1, y, h * 0.38, side, true),
			PackedColorArray([Color(1, 1, 1, 0.12), Color(1, 1, 1, 0.38), Color(1, 1, 1, 0.1), Color(1, 1, 1, 0.02)]))
		draw_line(_p(x_start + bar_slant, y + 1.0, side), _p(x1, y + 1.0, side), Color(1, 1, 1, 0.45), 1.4, true)
	draw_polyline(_closed(_bar_poly(x0, x1, y, h, side, true)), Color(frame_color, 0.55), 1.2, true)
	# Overdrive (A+B+C): shown while it runs
	if _overdrive(side):
		var pulse := 0.6 + 0.4 * sin(_time * 5.0)
		_side_text(_serif, 480, 112, "OVERDRIVE", 26, Color(overdrive_color, pulse), side, 3)


## Oct 28: true while this fighter is in Overdrive (health under 35%). The engine reports it through
## MatchSetup.overdrive_hud (SakugaActor.NetsuOverdriveHud: 1 = on, 0 = off).
func _overdrive(side: int) -> bool:
	return MatchSetup.overdrive_hud.size() > side and int(MatchSetup.overdrive_hud[side]) > 0


func _draw_name_and_rounds(side: int) -> void:
	var label = _src[side]["name"]
	var text: String = str(label.text).to_upper() if label else ""
	if text != "":
		_spaced_name(name_position.x, name_position.y, text, name_size, side)
	# rounds: a glowing diamond for each round won, small hollow circles for the rest (just outside the timer)
	var won := _rounds_won(side)
	var accent := _accent(side)
	for i in maxi(2, rounds_to_win):   # Nov 2: always two small thin circles per player (more if the match needs more)
		var at := _p(rounds_position.x + i * rounds_step, rounds_position.y, side)
		if i < won:
			_diamond(at, 9.0, accent, true)
		else:
			draw_circle(at, 6.5, Color(backing, 0.55))
			draw_arc(at, 6.5, 0, TAU, 24, Color(accent.lerp(Color.WHITE, 0.6), 0.9), 1.3, true)


## Nov 2: the name in white caps with a little letter spacing; left end at mockup x (right end for P2).
func _spaced_name(x: float, y: float, text: String, size_px: int, side: int) -> void:
	var gap := size_px * 0.08
	var w := 0.0
	for ch in text:
		w += _width(_thin, ch, size_px) + gap
	w -= gap
	var px := _x(x, side) - (0.0 if side == 0 else w)
	for ch in text:
		_text(_thin, Vector2(px, y * K), ch, size_px, text_color, 5)
		px += _width(_thin, ch, size_px) + gap


## Oct 30 (TamaDeez, refined): the Burst emblem under the bar by the portrait, BURST on the portrait side. Same finish as
## the top frame: flat navy diamond, one crisp outline, no wide glows.
##   Ready  = solid diamond in the side's colour, bright white four-point star, a tight halo one step out.
##   Used   = a short white blink inside the diamond, then it's empty.
##   Refilling = one bright line traces the outline: from the top, round the tip AWAY from the portrait, down, round the
##            tip by the portrait and back to the top (P2 mirrored).
##   Locked (Burst not allowed) = the trace is grey.
## Settings: Burst Diamond group. Data: HealthBars/P1Will (0..max), P1WillLocked.
func _draw_burst(side: int) -> void:
	var src: Dictionary = _src[side]
	var accent := _accent(side)
	var cx := burst_center.x
	var cy := burst_center.y
	var s := burst_size
	# P1 order: top, away from the portrait, bottom, by the portrait (mirroring gives P2 the same path)
	var shape := _pts([Vector2(cx, cy - s), Vector2(cx + s, cy), Vector2(cx, cy + s), Vector2(cx - s, cy)], side)
	var c := _p(cx, cy, side)
	var r := s * K
	var ratio := _ratio(src["will"])
	var lock = src["will_lock"]
	var locked: bool = lock != null and lock.visible
	var ready := ratio >= 0.999 and not locked
	var line := accent.lightened(0.45)
	# Nov 2: BURST sits inside the tab (part of the bar housing), centred between the portrait's edge and the diamond
	var lw := _width(_thin, burst_label, 18) / K
	var left := _portrait_edge_x(cy)
	var lx: float = left + ((cx - s - 6.0) - left - lw) / 2.0
	_side_text(_thin, lx, cy + 6.5, burst_label, 18, text_color, side, 3)
	# a short divider between the label and the diamond, leaning like the tab's end
	var dx := cx - s - 7.0
	draw_line(_p(dx + 4.0, cy - 9.0, side), _p(dx - 2.0, cy + 9.0, side), Color(line, 0.35), 1.2, true)
	# flat navy diamond
	draw_colored_polygon(shape, Color(0.02, 0.04, 0.14, 0.94))
	if ready:
		# tight halo: one thin outline a step outside
		draw_polyline(_closed(_scaled(shape, c, 1.22)), Color(accent, 0.45), 1.2, true)
		draw_colored_polygon(_scaled(shape, c, 0.86), accent)
		var a := r * 0.66
		var b := r * 0.13
		draw_colored_polygon(PackedVector2Array([c + Vector2(0, -a), c + Vector2(b, -b), c + Vector2(a, 0), c + Vector2(b, b),
			c + Vector2(0, a), c + Vector2(-b, b), c + Vector2(-a, 0), c + Vector2(-b, -b)]), Color.WHITE)
		draw_polyline(_closed(shape), line, 2.0, true)
	else:
		draw_polyline(_closed(shape), Color(line, 0.3), 1.4, true)
		var col := Color(0.6, 0.62, 0.7) if locked else line
		var p := clampf(ratio, 0.0, 1.0) * 4.0
		if p > 0.0:
			var path := PackedVector2Array([shape[0]])
			var i := 0
			while i < 4 and p > 0.0:
				path.append((shape[i] as Vector2).lerp(shape[(i + 1) % 4], minf(p, 1.0)))
				p -= 1.0
				i += 1
			draw_polyline(path, col, 2.6, true)
			draw_circle(path[path.size() - 1], 2.6, Color.WHITE if not locked else col)
		# dim centre mark so the emblem still reads when empty
		var m := r * 0.3
		draw_line(c + Vector2(-m, 0), c + Vector2(m, 0), Color(line, 0.35), 1.4, true)
		draw_line(c + Vector2(0, -m), c + Vector2(0, m), Color(line, 0.35), 1.4, true)
	# just used: a short white blink inside the diamond
	var uf: float = _burst_used_flash[side] / BURST_FLASH_TIME
	if uf > 0.0:
		draw_colored_polygon(_scaled(shape, c, 0.86), Color(1, 1, 1, 0.6 * uf))
	# just refilled: the outline flashes white
	var rf: float = _burst_ready_flash[side] / BURST_FLASH_TIME
	if rf > 0.0:
		draw_polyline(_closed(shape), Color(1, 1, 1, rf), 2.4, true)


## Nov 2: x of the corner portrait's slanted inner edge at mockup height y (P1 coordinates).
func _portrait_edge_x(y: float) -> float:
	var pa: Vector2 = PORTRAIT[2]
	var pb: Vector2 = PORTRAIT[3]
	return pa.x + (pb.x - pa.x) * (y - pa.y) / (pb.y - pa.y)


func _scaled(points: PackedVector2Array, centre: Vector2, k: float) -> PackedVector2Array:
	var out := PackedVector2Array()
	for q in points:
		out.append(centre + (q - centre) * k)
	return out


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


## Nov 2 (after the polished reference): the TIME panel. A dark inverted trapezoid a little below the top of the screen,
## wide at the top with a flat bottom, its sides parallel to the ends of the health bars; TIME over the number.
## The number pops each time it changes and a thin arc under it sweeps round once per second. At timer_warning seconds
## or fewer the number turns red, pulses, and the panel's edge flashes red on every tick. No time limit (--): an
## infinity sign with a slow shimmer.
func _draw_timer() -> void:
	var cx := timer_center_x
	var label = _src["timer"]
	var t: String = str(label.text) if label else "99"
	var infinite := t == "--" or t == ""
	if infinite:
		t = "∞"
	var secs := int(t) if t.is_valid_int() else -1
	var warn := secs >= 0 and secs <= timer_warning
	var tick := clampf(1.0 - _timer_since / 0.35, 0.0, 1.0)   # fades out after each change
	var y0 := timer_top
	var y1 := timer_bottom
	var wt := timer_half_width.x
	var wb := timer_half_width.y
	# Nov 2: a downward-pointing shield (flat top, sides slanting in, a shallow point at the bottom)
	var outer := [Vector2(cx - wt, y0), Vector2(cx + wt, y0), Vector2(cx + wb, y1 - 9.0), Vector2(cx, y1 + 5.0), Vector2(cx - wb, y1 - 9.0)]
	var shape := _pts(outer, 0)
	draw_polygon(shape, PackedColorArray([Color(0.05, 0.08, 0.22, 0.96), Color(0.05, 0.08, 0.22, 0.96),
		Color(0.01, 0.02, 0.09, 0.96), Color(0.01, 0.02, 0.09, 0.96), Color(0.01, 0.02, 0.09, 0.96)]))
	var edge := Color(0.82, 0.92, 1.0, 0.95)
	if warn:
		edge = edge.lerp(Color(1.0, 0.3, 0.25), 0.4 + 0.6 * tick)
	_glow_line(_closed(shape), edge, 2.2, 0.25 + 0.4 * (tick if warn else 0.0))
	var mid := _p(cx, (y0 + y1) / 2.0, 0)
	draw_polyline(_closed(_scaled(shape, mid, 0.9)), Color(frame_color, 0.28), 1.0, true)
	# slim angular brackets just outside the panel, P1 blue on the left / P2 red on the right, each joined to its
	# health bar's frame by a short line along the frame's top
	var d := (wt - wb) / (y1 - 9.0 - y0)      # how far the panel's side moves in per mockup px down
	for side in 2:
		var col := _accent(side).lerp(Color.WHITE, 0.3)
		var y_a := y0 + 3.0
		var y_b := y1 - 22.0
		var x_a := cx - wt - 10.0 + d * (y_a - y0)
		var x_b := cx - wt - 10.0 + d * (y_b - y0)
		# a short tab out along the top toward the bar, down the side (meeting the bar frame's end), a hook in at the bottom
		var pts := _pts([Vector2(x_a - 22.0, y_a), Vector2(x_a, y_a), Vector2(x_b, y_b), Vector2(x_b + 10.0, y_b + 8.0)], side)
		_glow_line(pts, col, 2.0, 0.35)
	var c := cx * K
	_text(_thin, Vector2(c - _width(_thin, "TIME", 26) / 2.0, (y0 + 27.0) * K), "TIME", 26, Color(0.9, 0.94, 1.0), 0)
	# the number (or infinity), centred a little below the middle of the panel
	var mid_y := (y0 + 57.0) * K
	var size_px := int(timer_size * (1.0 + 0.22 * _timer_pop))
	var col := text_color
	if warn:
		col = Color(1.0, 0.45, 0.4).lerp(Color.WHITE, 0.35 * tick + 0.15 * sin(_time * 10.0))
	var base_y := mid_y + size_px * 0.36
	if infinite:
		size_px = int(timer_size * 1.45)
		col = text_color.lerp(Color(0.8, 0.93, 1.0), 0.4 + 0.4 * sin(_time * 2.0))
		base_y = mid_y + size_px * 0.27
	var nw := _width(_serif, t, size_px)
	if _timer_pop > 0.0:   # a quick glow behind the new number
		draw_string_outline(_serif, Vector2(c - nw / 2.0, base_y), t, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px, 14,
			Color(col if warn else frame_color, 0.3 * _timer_pop))
	_text(_serif, Vector2(c - nw / 2.0, base_y), t, size_px, col, 4)
	# per-second sweep under the number (a slow shimmer when there's no time limit)
	var arc_c := Vector2(c, mid_y + 2.0)
	var arc_r := 27.0 * K
	if infinite:
		var start := fmod(_time * 1.5, TAU)
		draw_arc(arc_c, arc_r, start, start + 0.8, 16, Color(0.75, 0.9, 1.0, 0.25), 2.0, true)
	elif secs >= 0:
		var frac := clampf(_timer_since, 0.0, 1.0)
		var a_from := PI * 0.2
		var a_to := PI * 0.8
		draw_arc(arc_c, arc_r, a_from, a_to, 24, Color(frame_color, 0.15), 2.0, true)
		draw_arc(arc_c, arc_r, a_to - (a_to - a_from) * (1.0 - frac), a_to, 24,
			Color(Color(1.0, 0.4, 0.35) if warn else frame_color.lightened(0.2), 0.75), 2.4, true)


## Nov 2 (after the polished reference): one angular plate in each bottom corner. On the outer end a raised block with
## the big percentage (pointed toward the screen edge), stepping down to the row of gold segments (one per bar), with
## CRAFT POINTS on a tab hanging under the segments. Navy fill, one bright outline in the side's colour, a few small
## light glints. A full segment is solid gold, the filling one is darker gold up to how full it is.
## Overdrive: the plate's top line turns warm.
## Shape points are mockup px for P1 measured from meter_y (701 in the reference).
const METER_PLATE := [Vector2(48, 0), Vector2(176, 0), Vector2(192, 16), Vector2(494, 16), Vector2(503, 35),
	Vector2(490, 61), Vector2(447, 61), Vector2(437, 76), Vector2(290, 76), Vector2(280, 61), Vector2(24, 61), Vector2(6, 48)]

func _draw_meter(side: int) -> void:
	var node = _src[side]["meter"]
	var value: float = node.value if node else 0.0
	var max_value: float = node.max_value if node and node.max_value > 0 else 40000.0
	var stocks := maxi(1, int(round(max_value / meter_per_stock)))
	var percent := int(value / meter_per_stock * 100.0)
	var accent := _accent(side)
	var y0 := meter_y
	var od := _overdrive(side)
	var pts: Array = []
	for q in METER_PLATE:
		pts.append(Vector2(q.x, q.y + y0))
	var plate := _pts(pts, side)
	draw_colored_polygon(plate, Color(0.01, 0.04, 0.15, 0.9))
	var line := accent.lerp(Color(0.6, 0.92, 1.0), 0.35)
	_glow_line(_closed(plate), line, 2.0, 0.28)
	if od:   # the top edge turns warm and glows
		_glow_line(_pts([pts[0], pts[1], pts[2], pts[3], pts[4]], side), Color(1.0, 0.85, 0.5, 0.75 + 0.25 * sin(_time * 5.0)), 2.2, 0.4)
	# inner line under the percentage block and small light glints on the corners
	draw_polyline(_pts([Vector2(40, y0 + 8), Vector2(168, y0 + 8), Vector2(178, y0 + 18)], side), Color(line, 0.35), 1.0, true)
	draw_colored_polygon(_pts([Vector2(16, y0 + 51), Vector2(42, y0 + 51), Vector2(46, y0 + 56), Vector2(20, y0 + 56)], side), Color(0.85, 0.97, 1.0, 0.9))
	draw_line(_p(150, y0 + 61, side), _p(170, y0 + 61, side), Color(0.85, 0.97, 1.0, 0.9), 2.4)
	draw_line(_p(160, y0 - 0.5, side), _p(176, y0 - 0.5, side), Color(0.85, 0.97, 1.0, 0.9), 2.4)
	# segments
	var c0 := meter_cells_x.x
	var c1 := meter_cells_x.y
	var gap := 5.0
	var cell := (c1 - c0 - gap * (stocks - 1)) / stocks
	var cy := y0 + 27.0
	var ch := 24.0
	var slant := 11.0
	var level := value / meter_per_stock
	for i in stocks:
		var x0 := c0 + i * (cell + gap)
		var shape := _slanted(x0, x0 + cell, cy, ch, slant, side)
		# Nov 2: the gauge holds 300% until Overdrive opens the 4th bar: locked bars are dark and hatched
		if not od and (i + 1) * meter_per_stock > meter_normal_cap + 1.0:
			draw_colored_polygon(shape, Color(0.015, 0.02, 0.07, 0.95))
			for h in range(1, 7):
				var hx := x0 + slant + (cell - slant) * h / 7.0
				draw_line(_p(hx, cy + 3.0, side), _p(hx - slant * 0.8, cy + ch - 3.0, side), Color(line, 0.14), 1.2, true)
			draw_polyline(_closed(shape), Color(line, 0.2), 1.0, true)
			continue
		draw_colored_polygon(shape, Color(0.05, 0.08, 0.22, 0.95))
		var fill := clampf(level - i, 0.0, 1.0)
		if fill > 0.0:
			var col := meter_color if fill >= 1.0 else meter_color.darkened(0.3)
			draw_colored_polygon(_slanted(x0, x0 + cell * fill, cy, ch, slant, side), col)
			draw_line(_p(x0 + slant, cy + 1.0, side), _p(x0 + slant + (cell - slant * 0.0) * fill, cy + 1.0, side), Color(meter_light, 0.8), 1.4)
		draw_polyline(_closed(shape), Color(0.0, 0.02, 0.1, 0.9) if fill >= 1.0 else Color(line, 0.35), 1.2, true)
	# CRAFT POINTS on the hanging tab
	_spaced_text(_thin, 306, y0 + 70.0, meter_caption, 18, 128.0 * K, Color(1, 1, 1, 0.95), side)
	# percentage: big italic number with a smaller %, a soft blue glow
	var num := str(percent)
	var nsize := 56
	var ssize := 34
	var nw := _width(_serif, num, nsize)
	var sw := _width(_serif, "%", ssize)
	var px := _x(112, side) - (nw + 2.0 + sw) / 2.0
	var base := (y0 + 45.0) * K
	draw_string_outline(_serif, Vector2(px, base), num, HORIZONTAL_ALIGNMENT_LEFT, -1, nsize, 14, Color(accent, 0.22))
	_text(_serif, Vector2(px, base), num, nsize, percent_color, 6)
	_text(_serif, Vector2(px + nw + 2.0, base), "%", ssize, percent_color, 5)


## Nov 2 (after the polished reference): the assist card under the portrait, its name centred under it. One angular card:
## the screen-edge side leans "/", the inner side comes to a point; flat navy backing, one crisp outline, a small
## team-colour corner at the bottom outer end.
##   Ready    = portrait in full colour, outline bright.
##   Cooldown = portrait dimmed (grey), with the countdown diamond (seconds left) over the outer part of the portrait.
##   Called (on screen) = dimmed, no number yet.
##   Ready again = a short white blink of the outline.
## Mary's buff: a thin teal bar under the card. Overdrive Link: a small diamond beside the card.
## Settings: Assist Gauge group. Data: MatchSetup.assist_hud (engine: NetsuAssist.Render; "frames_left" from the engine,
## or estimated here from how fast the gauge fills if the engine is an older build).
func _draw_assist(side: int) -> void:
	var info: Dictionary = MatchSetup.assist_hud[side] if MatchSetup.assist_hud.size() > side else {}
	if info.is_empty() or Time.get_ticks_msec() - int(info.get("msec", 0)) > 600:
		return
	var accent := _accent(side)
	var y := assist_y
	var h := assist_card_height
	var ratio: float = clampf(float(info.get("ratio", 0.0)), 0.0, 1.0)
	var phase: int = int(info.get("phase", 0))
	var ready := phase == 0
	var x0 := assist_card_x.x
	var x1 := assist_card_x.y
	var sl := 12.0
	var tip := 11.0
	var card := _pts([Vector2(x0 + sl, y), Vector2(x1, y), Vector2(x1 + tip, y + h * 0.42), Vector2(x1, y + h), Vector2(x0, y + h)], side)
	draw_colored_polygon(card, Color(0.02, 0.04, 0.14, 0.94))
	var tex = info.get("icon")
	if tex is Texture2D:
		var center := _p((x0 + x1 + sl) / 2.0 + 14.0, y + h * 0.5, side)
		var span := (x1 - x0) * K * 0.86   # how wide the whole icon is drawn: smaller = bigger face
		if ready:
			_icon_poly(card, tex, center, span, Color.WHITE)
		else:
			_icon_poly(card, _gray_icon(tex), center, span, assist_gray.darkened(0.4))
	var line := accent.lerp(Color(0.75, 0.95, 1.0), 0.4)
	if ready:
		draw_polyline(_closed(card), Color(accent, 0.25), 6.0, true)
	draw_polyline(_closed(card), line if ready else Color(line, 0.5), 2.0 if ready else 1.5, true)
	# team-colour corner at the bottom outer end
	draw_colored_polygon(_pts([Vector2(x0, y + h), Vector2(x0 + 14, y + h), Vector2(x0 + 4, y + h - 9)], side), accent if ready else Color(accent, 0.5))
	# ready again: one white blink of the outline
	var fl: float = _assist_flash[side] / ASSIST_FLASH_TIME
	if fl > 0.0:
		draw_polyline(_closed(card), Color(1, 1, 1, fl), 2.6, true)
	# countdown diamond (cooldown only), over the outer part of the portrait
	if phase == 2:
		var secs := _assist_seconds(side, info, ratio)
		var bc := _p(x0 + sl + 22.0, y, side)   # Nov 2: sits on the card's top edge, outer end
		var br := 18.0 * K
		var badge := PackedVector2Array([bc + Vector2(0, -br), bc + Vector2(br, 0), bc + Vector2(0, br), bc + Vector2(-br, 0)])
		draw_colored_polygon(badge, Color(0.01, 0.04, 0.13, 0.97))
		draw_polyline(_closed(badge), Color(accent, 0.3), 6.0, true)
		draw_polyline(_closed(badge), line, 2.0, true)
		if secs > 0:
			var t := str(secs)
			var ts := 26
			var tw := _width(_serif, t, ts)
			_text(_serif, Vector2(bc.x - tw / 2.0 - 1.0, bc.y + ts * 0.36), t, ts, text_color, 3)
	# Overdrive Link marker (the next assist call comes back faster)
	if _od_link(side):
		_diamond(_p(x1 + tip + 12, y + h * 0.42, side), 6.0, Color(1.0, 0.55, 0.3), true)
	# buff time left (Mary's 5S)
	var buff: float = clampf(float(info.get("buff", 0.0)), 0.0, 1.0)
	var name_y := y + h + 18.0
	if buff > 0.0:
		draw_line(_p(x0, y + h + 5.0, side), _p(x0 + (x1 - x0) * buff, y + h + 5.0, side), assist_buff_color, 3.0)
		name_y += 4.0
	# name, centred under the card
	var label := str(info.get("name", "")).to_upper()
	var nw := _width(_thin, label, 21)
	var ncx := _x((x0 + x1 + sl) / 2.0, side)
	_text(_thin, Vector2(ncx - nw / 2.0, name_y * K), label, 21, text_color if ready else Color(0.78, 0.8, 0.86), 4)


## Seconds until the assist is ready: from the engine (frames_left) when it sends it, otherwise estimated from how fast
## the gauge is filling.
var _cd_start := [{}, {}]
func _assist_seconds(side: int, info: Dictionary, ratio: float) -> int:
	if info.has("frames_left") and int(info["frames_left"]) >= 0:
		return int(ceil(int(info["frames_left"]) / 60.0))
	var now := Time.get_ticks_msec() / 1000.0
	var st: Dictionary = _cd_start[side]
	if st.is_empty() or ratio < float(st.get("r", 0.0)) - 0.001:
		_cd_start[side] = {"t": now, "r": ratio}
		return 0
	var dt := now - float(st["t"])
	var dr := ratio - float(st["r"])
	if dt < 0.25 or dr <= 0.0:
		return 0
	return int(ceil((1.0 - ratio) * dt / dr))


## The assist's picture drawn into a screen-space polygon: the picture's middle sits on `center`, `span` screen px wide.
func _icon_poly(poly: PackedVector2Array, tex: Texture2D, center: Vector2, span: float, tint: Color) -> void:
	var uvs := PackedVector2Array()
	for q in poly:
		uvs.append(Vector2(0.5 + (q.x - center.x) / span, 0.42 + (q.y - center.y) / span))
	draw_polygon(poly, PackedColorArray([tint]), uvs, tex)


## A grey copy of an assist icon (made the first time it's needed).
func _gray_icon(tex: Texture2D) -> Texture2D:
	if _gray_icons.has(tex):
		return _gray_icons[tex]
	var out: Texture2D = tex
	var img := tex.get_image()
	if img:
		img = img.duplicate()
		if img.is_compressed():
			img.decompress()
		img.clear_mipmaps()
		img.convert(Image.FORMAT_RGBA8)
		for yy in img.get_height():
			for xx in img.get_width():
				var c := img.get_pixel(xx, yy)
				var l := c.r * 0.3 + c.g * 0.59 + c.b * 0.11
				img.set_pixel(xx, yy, Color(l, l, l, c.a))
		out = ImageTexture.create_from_image(img)
	_gray_icons[tex] = out
	return out


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
