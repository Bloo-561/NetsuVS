extends Control
## NETSU WIN SCREEN  (Oct 19 2026: dark night-blue theme, like the menus)
##
##   [stage art, misty]                         [winner's victory render]
##   W I N N E R  (big, outlined)
##   ==== PLAYER 1 ===========
##   CECILIA            <- ShortName (big)
##   CECILIA RICHTER    <- FighterName (small)
##        "victory quote typed out here"
##
## Like the battle HUD, the engine still fills in Mahou's ResultsScreen
## (engine/sakuga/Components/GameMonitor.cs -> ShowResultScreen). This script
## makes that screen invisible, reads it, and shows this one instead.
##
## Where the pieces come from:
##   picture  -> fighter Profile -> VictoryRender   (actors/<fighter>/0_XXX_Profile.tres)
##   names    -> Profile -> ShortName / FighterName
##   quote    -> fighter Data -> Outros -> FinalMessage (actors/<fighter>/0_XXX_Data.tres)
##   backdrop -> the stage's Thumbnail in data/stage_list.tres
## Every size/colour/position below is an @export (click the root of
## netsu_win_screen.tscn). Full map: docs/win_screen.md

@export_group("Colours")
@export var p1_accent: Color = Color(0.25, 0.6, 1.0)     ## Player 1 blue
@export var p2_accent: Color = Color(1.0, 0.22, 0.35)    ## Player 2 crimson
@export_range(0.0, 1.0) var stage_dim: float = 0.55       ## how dark the stage gets behind the text

@export_group("Layout (1920x1080)")
@export var render_center_x: float = 1360.0
@export var render_top_y: float = 0.0
@export_range(0.2, 1.0) var render_show_fraction: float = 0.6  ## top part of the picture to show (torso and up, cut below the screen)
@export var render_height: float = 1180.0                    ## on-screen height of that part
@export var winner_position: Vector2 = Vector2(120, 150)
@export var winner_size: int = 200
@export var winner_spacing: int = 30                            ## gap between WINNER's letters
@export var bar_y: float = 382.0
@export var bar_length: float = 1050.0
@export var name_position: Vector2 = Vector2(120, 405)
@export var name_size: int = 112
@export var full_name_size: int = 26
@export var quote_box: Rect2 = Rect2(110, 700, 900, 150)
@export var quote_size: int = 34
@export var quote_seconds: float = 1.4                          ## typing time for the quote

const CANVAS := Vector2(1920, 1080)

var _results: Control
var _shown := false


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	visible = false
	size = CANVAS
	var root := get_parent()
	_results = root.get_node_or_null("ResultsScreen")
	if _results:
		_results.modulate = Color(1, 1, 1, 0)   # keep it "visible" for the engine, but unseen
		root.move_child.call_deferred(self, _results.get_index() + 1)
	get_viewport().size_changed.connect(_fit)
	_fit()


func _fit() -> void:
	var view := get_viewport_rect().size
	scale = Vector2.ONE * (view.x / CANVAS.x)
	position = Vector2(0, (view.y - CANVAS.y * scale.y) / 2.0)


func _process(_delta: float) -> void:
	if not _shown and _results and _results.visible:
		_shown = true
		_build()


# --- Reading what the engine decided ------------------------------------------

func _winner_side() -> int:
	var p2_banner := _results.get_node_or_null("WinBannerP2") as Control
	var p1_banner := _results.get_node_or_null("WinBannerP1") as Control
	if p1_banner and not p1_banner.visible:
		return 1
	if p2_banner and not p2_banner.visible:
		return 0
	return 0


func _winner_profile(side: int):
	var cfg = MatchSetup.settings()
	var index: int = cfg.P1SelectedCharacter if side == 0 else cfg.P2SelectedCharacter
	return MatchSetup.fighter_profile(index)


# --- Building the screen --------------------------------------------------------

func _build() -> void:
	var side := _winner_side()
	var accent := p1_accent if side == 0 else p2_accent
	var profile = _winner_profile(side)
	var short_name := str(profile.ShortName) if profile else "WINNER"
	var full_name := str(profile.FighterName) if profile else ""
	var render_tex: Texture2D = (_results.get_node("Character") as TextureRect).texture
	var quote := str((_results.get_node("VictoryMessage") as Label).text)

	# backdrop: the stage under a night-blue veil, darker on the text side
	var stage_tex: Texture2D = null
	var cfg = MatchSetup.settings()
	var stage_index: int = cfg.SelectedStage if cfg else -1
	if stage_index >= 0 and stage_index < MatchSetup.stage_count():
		stage_tex = MatchSetup.stage_thumbnail(stage_index)
	var bg := ColorRect.new()
	bg.color = Color(0.02, 0.03, 0.1)
	bg.size = CANVAS
	add_child(bg)
	if stage_tex:
		var stage := TextureRect.new()
		stage.texture = stage_tex
		stage.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		stage.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
		stage.size = CANVAS
		add_child(stage)
	var veil := ColorRect.new()
	veil.color = Color(0.02, 0.04, 0.16, stage_dim)
	veil.size = CANVAS
	add_child(veil)
	add_child(_gradient_rect(Vector2.ZERO, Vector2(1300, 1080), Color(0.02, 0.03, 0.12, 0.85), Color(0.02, 0.03, 0.12, 0.0), false))
	var lights := NetsuLights.new()
	lights.beams = NetsuLights.preset("menu") if side == 0 else NetsuLights.preset("select")
	add_child(lights)

	# the winner
	var render := TextureRect.new()
	if render_tex:
		var full := render_tex.get_size()
		var part := AtlasTexture.new()
		part.atlas = render_tex
		part.region = Rect2(0, 0, full.x, full.y * render_show_fraction)
		render.texture = part
		var ratio := part.region.size.x / maxf(part.region.size.y, 1.0)
		render.size = Vector2(render_height * ratio, render_height)
	render.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	render.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT
	var render_home := Vector2(render_center_x - render.size.x / 2.0, render_top_y)
	render.position = render_home + Vector2(260, 0)
	render.modulate.a = 0.0
	add_child(render)
	add_child(_gradient_rect(Vector2(0, 780), Vector2(1920, 300), Color(0.02, 0.03, 0.12, 0.0), Color(0.02, 0.03, 0.12, 0.9), true))

	# WINNER: big hollow letters with a coloured glow.
	# Exo 2's letters are built from overlapping pieces, so an outline alone also
	# traces the hidden lines inside E, R, N... Instead: a bright outlined copy,
	# then a dark filled copy on top that covers everything inside the letters.
	var winner := Control.new()
	winner.mouse_filter = Control.MOUSE_FILTER_IGNORE
	winner.position = winner_position
	add_child(winner)
	var edge := _label("WINNER", winner_size, accent.lightened(0.45), NetsuUI.sans(winner_spacing, true))
	edge.add_theme_color_override("font_outline_color", Color(accent.lightened(0.45), 0.95))
	edge.add_theme_constant_override("outline_size", 6)
	winner.add_child(edge)
	var inner := _label("WINNER", winner_size, Color(0.04, 0.06, 0.18, 0.93), NetsuUI.sans(winner_spacing, true))
	winner.add_child(inner)
	var glow := _label("WINNER", winner_size, Color(0, 0, 0, 0), NetsuUI.sans(winner_spacing, true))
	glow.add_theme_color_override("font_outline_color", Color(accent, 0.25))
	glow.add_theme_constant_override("outline_size", 22)
	glow.position = winner_position
	add_child(glow)
	move_child(glow, winner.get_index())

	# PLAYER bar: slanted accent band fading right, bright edge lines
	var bar := Control.new()
	bar.position = Vector2(0, bar_y)
	bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var band := Polygon2D.new()
	band.polygon = PackedVector2Array([Vector2(0, 0), Vector2(bar_length, 0), Vector2(bar_length - 14, 28), Vector2(0, 28)])
	band.vertex_colors = PackedColorArray([Color(accent, 0.95), Color(accent, 0.0), Color(accent.darkened(0.3), 0.0), Color(accent.darkened(0.3), 0.95)])
	bar.add_child(band)
	bar.add_child(NetsuUI.hairline(Vector2(0, -3), bar_length, Color(accent.lightened(0.5), 0.95), 2.0, "right"))
	bar.add_child(NetsuUI.hairline(Vector2(0, 31), bar_length * 0.7, Color(accent.lightened(0.3), 0.6), 1.5, "right"))
	# PLAYER 1 / PLAYER 2 / CPU (online: the lobby name), as the VS screen showed it
	var player := _label(MatchSetup.side_label(side), 26, Color.WHITE, NetsuUI.sans(10))
	player.position = Vector2(winner_position.x + 110, -6)
	bar.add_child(player)
	add_child(bar)

	# names
	var big := _label(short_name.to_upper(), name_size, Color.WHITE, NetsuUI.sans(4, true))
	big.add_theme_color_override("font_outline_color", Color(accent.darkened(0.4), 0.7))
	big.add_theme_constant_override("outline_size", 14)
	big.position = name_position
	add_child(big)
	var small := _label(full_name.to_upper(), full_name_size, Color(0.8, 0.88, 1.0), NetsuUI.sans(8))
	small.position = name_position + Vector2(10, name_size * 1.18)
	add_child(small)
	var rule := NetsuUI.hairline(name_position + Vector2(10, name_size * 1.18 + 44), 420, Color(accent.lightened(0.3), 0.8), 1.5, "right")
	add_child(rule)

	# quote in a slanted glass box
	var qb := Control.new()
	qb.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(qb)
	var r := quote_box
	var skew := 40.0
	var main := PackedVector2Array([r.position + Vector2(skew, 0), Vector2(r.end.x + skew, r.position.y), r.end,
		Vector2(r.position.x, r.end.y)])
	var fill := Polygon2D.new()
	fill.polygon = main
	fill.vertex_colors = PackedColorArray([Color(0.1, 0.12, 0.34, 0.85), Color(0.08, 0.1, 0.3, 0.6),
		Color(0.05, 0.07, 0.22, 0.6), Color(0.05, 0.06, 0.2, 0.88)])
	qb.add_child(fill)
	qb.add_child(NetsuUI.outline(main, Color(0.86, 0.88, 1.0, 0.75), 1.5))
	var strip := PackedVector2Array([r.position + Vector2(skew - 22, 0), r.position + Vector2(skew - 6, 0),
		Vector2(r.position.x - 6, r.end.y), Vector2(r.position.x - 22, r.end.y)])
	qb.add_child(NetsuUI.poly(strip, Color(accent.lightened(0.3), 0.6)))
	var line := _label(quote, quote_size, Color(0.96, 0.97, 1.0), NetsuUI.serif(500))
	line.add_theme_constant_override("line_spacing", 6)
	line.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	line.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	line.position = r.position + Vector2(skew + 40, 0)
	line.size = Vector2(r.size.x - 90, r.size.y)
	line.visible_ratio = 0.0
	qb.add_child(line)

	var footer := NetsuUI.footer(self, false, 849.0, 87.0, 885.0, 1600.0, 889.0)
	footer["text"].text = "%s wins the match." % short_name
	footer["prompts"].text = "PRESS ANY BUTTON"

	# --- animate in ---
	visible = true
	modulate.a = 0.0
	var t := create_tween().set_parallel(true)
	t.tween_property(self, "modulate:a", 1.0, 0.35)
	t.tween_property(render, "position", render_home, 0.6).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT).set_delay(0.1)
	t.tween_property(render, "modulate:a", 1.0, 0.45).set_delay(0.1)
	var d := 0.22
	for node in [glow, winner, bar, big, small, rule, qb]:
		var home: Vector2 = node.position
		node.position = home - Vector2(120, 0)
		node.modulate.a = 0.0
		t.tween_property(node, "position", home, 0.45).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT).set_delay(d)
		t.tween_property(node, "modulate:a", 1.0, 0.35).set_delay(d)
		d += 0.05
	t.tween_property(line, "visible_ratio", 1.0, quote_seconds).set_delay(0.9)
	var pulse := create_tween().set_loops()
	pulse.tween_property(footer["prompts"], "modulate:a", 0.45, 0.8)
	pulse.tween_property(footer["prompts"], "modulate:a", 1.0, 0.8)


func _label(text: String, font_size: int, color: Color, font: Font) -> Label:
	var label := Label.new()
	label.text = text
	if font:
		label.add_theme_font_override("font", font)
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", color)
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return label


func _gradient_rect(pos: Vector2, rect_size: Vector2, from: Color, to: Color, vertical: bool) -> TextureRect:
	var gradient := Gradient.new()
	gradient.set_color(0, from)
	gradient.set_color(1, to)
	var tex := GradientTexture2D.new()
	tex.gradient = gradient
	tex.fill_to = Vector2(0, 1) if vertical else Vector2(1, 0)
	var rect := TextureRect.new()
	rect.texture = tex
	rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	rect.position = pos
	rect.size = rect_size
	rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return rect


## A diagonal shaft of light (wider at the bottom, fading out).
func _beam(x: float, width: float, strength: float) -> Polygon2D:
	var beam := Polygon2D.new()
	beam.polygon = PackedVector2Array([Vector2(x + 260, 0), Vector2(x + 260 + width, 0),
		Vector2(x + width * 1.8, 1080), Vector2(x - width * 0.4, 1080)])
	beam.vertex_colors = PackedColorArray([Color(1, 1, 1, strength), Color(1, 1, 1, strength),
		Color(1, 1, 1, 0.0), Color(1, 1, 1, 0.0)])
	return beam
