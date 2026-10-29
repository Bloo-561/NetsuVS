extends CanvasLayer
## SCENE ROUTER (autoload - reach it from anywhere as "SceneRouter")
##
## Moves between screens. Oct 25: the screen fades to black and the Netsu emblem lights up in the middle
## (game/ui/netsu/netsu_emblem.gd: a steel medallion whose ring locks, six stones light one after another and
## the heat sigil in the centre ignites) while the next scene loads in the background (MatchSetup's loader),
## then it fades into the new scene. The title -> main menu keeps its white flash; the VS screen -> fight is a
## plain fade (the VS screen is that loading screen). use_emblem = false brings back the old slanted wipe.
##   SceneRouter.go_to(SceneRouter.MAIN_MENU)
##   SceneRouter.go_to(SceneRouter.TITLE, Color.WHITE)   # white flash instead (title -> main menu)
##
## When you add a new screen, add its path to the list below.

const TITLE := "res://scenes/title/title_screen.tscn"
const MAIN_MENU := "res://scenes/main_menu/main_menu.tscn"
const CHARACTER_SELECT := "res://scenes/character_select/character_select.tscn"
const STAGE_SELECT := "res://scenes/stage_select/stage_select.tscn"
const OPTIONS := "res://scenes/options/options_menu.tscn"
const BATTLE := "res://scenes/battle/battle.tscn"
const VS_SCREEN := "res://scenes/vs_screen/vs_screen.tscn"
const ONLINE_LOBBY := "res://scenes/online/online_lobby.tscn"
const EMBLEM := preload("res://game/ui/netsu/netsu_emblem.gd")

## Seconds for each half of the transition (cover, then reveal).
@export var fade_time: float = 0.3
## Oct 25: fade to black + the Netsu emblem while loading (false = the old slanted wipe).
@export var use_emblem: bool = true
@export var black_in: float = 0.22         ## seconds to fade to black
@export var black_out: float = 0.32        ## seconds from black into the new scene
@export var emblem_speed: float = 1.5      ## the emblem's light-up: 1 = about a second, 2 = twice as fast

var _fade: ColorRect      # used for the white flash
var _wipe: Wipe
var _emblem: Control      # game/ui/netsu/netsu_emblem.gd
var _busy := false
## Oct 25 evening: true while the screen is covered (black / wipe) during a change; `shown` is emitted the moment
## the new screen starts to appear (character select starts its music then: `await SceneRouter.wait_shown()`).
var _covered := false
signal shown


func _ready() -> void:
	layer = 100  # draw above everything
	process_mode = Node.PROCESS_MODE_ALWAYS
	_fade = ColorRect.new()
	_fade.color = Color.BLACK
	_fade.set_anchors_preset(Control.PRESET_FULL_RECT)
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fade.modulate.a = 0.0
	add_child(_fade)
	_wipe = Wipe.new()
	_wipe.set_anchors_preset(Control.PRESET_FULL_RECT)
	_wipe.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_wipe)
	_emblem = EMBLEM.new()
	_emblem.name = "NetsuEmblem"
	add_child(_emblem)


## Waits until the new screen starts to appear (returns at once when nothing covers it).
func wait_shown() -> void:
	if _covered:
		await shown


func _reveal() -> void:
	if _covered:
		_covered = false
		shown.emit()


## True while a transition is happening. Screens should ignore input while busy.
func is_busy() -> bool:
	return _busy


func go_to(scene_path: String, fade_color: Color = Color.BLACK) -> void:
	if _busy:
		return
	_busy = true
	var flash := fade_color != Color.BLACK
	if not flash and use_emblem:
		await _emblem_go(scene_path)
		_busy = false
		return
	if flash:
		_fade.color = fade_color
		_fade.mouse_filter = Control.MOUSE_FILTER_STOP
		var fade_out := create_tween()
		fade_out.tween_property(_fade, "modulate:a", 1.0, fade_time * 0.8)
		await fade_out.finished
	else:
		_wipe.mouse_filter = Control.MOUSE_FILTER_STOP
		_wipe.phase = 0
		var cover := create_tween()
		cover.tween_property(_wipe, "progress", 1.0, fade_time).from(0.0).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN_OUT)
		await cover.finished

	_covered = true
	var error := get_tree().change_scene_to_file(scene_path)
	if error != OK:
		push_error("SceneRouter: couldn't open %s (error %d)" % [scene_path, error])
	await get_tree().process_frame
	await get_tree().process_frame
	_reveal()

	if flash:
		var fade_in := create_tween()
		fade_in.tween_property(_fade, "modulate:a", 0.0, fade_time)
		await fade_in.finished
		_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	else:
		_wipe.phase = 1
		var reveal := create_tween()
		reveal.tween_property(_wipe, "progress", 1.0, fade_time * 1.1).from(0.0).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
		await reveal.finished
		_wipe.progress = 0.0
		_wipe.phase = 0
		_wipe.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_busy = false


## Black, the emblem lighting up while `scene_path` loads in the background, then into the new scene.
func _emblem_go(scene_path: String) -> void:
	var loader := get_node_or_null("/root/MatchSetup")
	var bg := loader != null and loader.has_method("bg_load") and ResourceLoader.exists(scene_path)
	if bg:
		loader.bg_load(scene_path, true)
	_fade.color = Color.BLACK
	_fade.mouse_filter = Control.MOUSE_FILTER_STOP
	var cover := create_tween()
	cover.tween_property(_fade, "modulate:a", 1.0, black_in).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN)
	await cover.finished
	_emblem.speed = emblem_speed
	_emblem.play()
	var packed = null
	var waited := 0.0
	while true:
		await get_tree().process_frame
		waited += get_process_delta_time()
		var can_go := true
		if bg:
			packed = loader.bg_get(scene_path)
			can_go = packed != null or loader.bg_progress([scene_path]) >= 1.0 or waited > 20.0
		if can_go and _emblem.finished_lighting():
			break
	var error: int
	_covered = true
	if packed is PackedScene:
		error = get_tree().change_scene_to_packed(packed)
	else:
		error = get_tree().change_scene_to_file(scene_path)   # the background load failed: the usual way
	if error != OK:
		push_error("SceneRouter: couldn't open %s (error %d)" % [scene_path, error])
	if bg:
		loader.bg_release([scene_path])
	await get_tree().process_frame
	await get_tree().process_frame
	_reveal()
	_emblem.fade_out(0.16)
	var reveal := create_tween()
	reveal.tween_interval(0.12)
	reveal.tween_property(_fade, "modulate:a", 0.0, black_out).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	await reveal.finished
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE


## Fades to `color`, switches to `scene` and fades back in. `scene` is a PackedScene that's already
## loaded (the VS screen loads the fight in the background and hands it over) or a path.
func fade_to(scene, color: Color = Color.BLACK, out_time: float = 0.35, in_time: float = 0.5) -> void:
	if _busy:
		return
	_busy = true
	_fade.color = color
	_fade.mouse_filter = Control.MOUSE_FILTER_STOP
	var fade_out := create_tween()
	fade_out.tween_property(_fade, "modulate:a", 1.0, out_time).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN)
	await fade_out.finished
	var error: int
	_covered = true
	if scene is PackedScene:
		error = get_tree().change_scene_to_packed(scene)
	else:
		error = get_tree().change_scene_to_file(str(scene))
	if error != OK:
		push_error("SceneRouter: couldn't open %s (error %d)" % [scene, error])
	# the first frames of a fight are the heaviest: let them pass before fading in
	for i in 3:
		await get_tree().process_frame
	_reveal()
	var fade_in := create_tween()
	fade_in.tween_property(_fade, "modulate:a", 0.0, in_time).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	await fade_in.finished
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_busy = false


## The slanted panel. phase 0: sweeps in from the left until it covers the
## screen (progress 0 -> 1). phase 1: carries on off to the right.
class Wipe extends Control:
	var phase := 0
	var progress := 0.0:
		set(v):
			progress = v
			queue_redraw()
	const SLANT := 0.35   # sideways shift per px of height

	func _draw() -> void:
		var w := size.x
		var h := size.y
		var lean := h * SLANT
		var span := w + lean
		var lead: float   # x of the panel's leading (right) edge at the top
		var tail: float   # x of its trailing (left) edge at the top
		if phase == 0:
			if progress <= 0.0:
				return
			lead = -lean + progress * (span + lean)
			tail = -lean * 2.0 - 200.0
		else:
			if progress >= 1.0:
				return
			lead = w + lean + 200.0
			tail = -lean + progress * (span + lean)
		var top_l := Vector2(tail + lean, 0)
		var top_r := Vector2(lead + lean, 0)
		var bot_r := Vector2(lead, h)
		var bot_l := Vector2(tail, h)
		draw_polygon(PackedVector2Array([top_l, top_r, bot_r, bot_l]),
			PackedColorArray([Color(0.03, 0.05, 0.17), Color(0.05, 0.09, 0.26), Color(0.04, 0.07, 0.22), Color(0.02, 0.03, 0.12)]))
		# a crimson band just behind the leading edge, a glowing blue edge in front
		var edge_r := [top_r, bot_r]
		if phase == 0:
			draw_polygon(PackedVector2Array([top_r + Vector2(-90, 0), top_r + Vector2(-60, 0), bot_r + Vector2(-60, 0), bot_r + Vector2(-90, 0)]),
				PackedColorArray([Color(1.0, 0.2, 0.32, 0.55)]))
			for i in 3:
				draw_line(edge_r[0], edge_r[1], Color(0.35, 0.7, 1.0, 0.18), 26.0 - i * 8.0, true)
			draw_line(edge_r[0], edge_r[1], Color(0.8, 0.92, 1.0), 3.0, true)
		else:
			draw_polygon(PackedVector2Array([top_l + Vector2(60, 0), top_l + Vector2(90, 0), bot_l + Vector2(90, 0), bot_l + Vector2(60, 0)]),
				PackedColorArray([Color(1.0, 0.2, 0.32, 0.55)]))
			for i in 3:
				draw_line(top_l, bot_l, Color(0.35, 0.7, 1.0, 0.18), 26.0 - i * 8.0, true)
			draw_line(top_l, bot_l, Color(0.8, 0.92, 1.0), 3.0, true)
		# a diamond riding in the middle of the covered part
		var cx := clampf((top_l.x + bot_r.x) / 2.0, 0.0, w)
		var c := Vector2(cx, h / 2.0)
		if (phase == 0 and progress > 0.6) or (phase == 1 and progress < 0.4):
			var a := clampf((progress - 0.6) / 0.4, 0.0, 1.0) if phase == 0 else clampf(1.0 - progress / 0.4, 0.0, 1.0)
			var r := 18.0
			var pts := PackedVector2Array([c + Vector2(0, -r), c + Vector2(r, 0), c + Vector2(0, r), c + Vector2(-r, 0), c + Vector2(0, -r)])
			draw_polyline(pts, Color(0.75, 0.9, 1.0, a), 2.0, true)
			draw_line(c + Vector2(-140, 0), c + Vector2(-r - 8, 0), Color(0.6, 0.8, 1.0, a * 0.7), 1.5, true)
			draw_line(c + Vector2(r + 8, 0), c + Vector2(140, 0), Color(0.6, 0.8, 1.0, a * 0.7), 1.5, true)
