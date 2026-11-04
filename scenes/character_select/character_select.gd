extends Control
## CHARACTER SELECT  (Oct 19 2026 mockup)
##
## Player 1 picks on the left (blue), Player 2 on the right (crimson).
## The big renders are shown as drawn for both players (never mirrored).
##   Move:     left / right (up / down jumps between rows)
## Nov 2 evening: laid out and opened like Melty Blood Act Cadenza's select (see netsu_select_mb.gd and the intro below).
##   Pick:     A, S or Start   -> then pick a COLOR (left / right), A, then an ASSIST from the grid
##             of every assist (arrows; it grows with data/assist_list.tres), A again to lock
##   Undo:     B or C  (Escape also works for P1)
##   A+B macro (RB / U):  Button Settings      B+C macro (RT / O):  Keyboard Settings
##
## Versus: who is a person and who is the CPU comes from the side select
## (MatchSetup.humans). The person next to a CPU side picks the CPU's fighter
## after their own. Training: Player 2 JOINS by pressing a pick button; if
## nobody joins, Player 1 picks the training dummy.
## After both lock in -> stage select.
##
## While a player chooses a COLOR, the real in-game sprite (with that color's
## material) appears in front of their render, so you see exactly how it will
## look in battle.
##
## Fighters come from data/roster.tres (MatchSetup autoload). Empty "?" slots
## show where future Netsu no Kiseki characters will go.
## Layout numbers are mockup pixels (1671 x 941), converted with NetsuUI.m().
## Background: assets/ui/netsu/select_bg.png.

const MAIN_MENU := "res://scenes/main_menu/main_menu.tscn"
const OPTIONS_SCENE := "res://scenes/options/options_menu.tscn"
const SFX_MOVE := "res://assets/audio/menu/mahou/NavigationSound.wav"
const SFX_PICK := "res://assets/audio/menu/mahou/ConfirmSound.wav"
const SFX_BACK := "res://assets/audio/menu/mahou/CancelSound.wav"
const SFX_START := "res://assets/audio/menu/mahou/StrongConfirmSoundVers4.wav"
const RENDER_FADE := preload("res://game/ui/netsu/render_fade.gdshader")
## Nov 2: embers, beat streaks and edge pulses in time with the select theme (behind the renders)
const SELECT_FX := preload("res://scenes/character_select/netsu_select_fx.gd")
## Nov 2 (evening): Melty Blood Act Cadenza style dressing: heat emblem + lore (behind the renders), title plate, mode,
## scrolling bio lines and CHARACTER SELECT (over them). Also times the intro (song_time).
const SELECT_MB := preload("res://scenes/character_select/netsu_select_mb.gd")
## Nov 2 (late): THE IGNITION intro: the heat emblem lights up on the beat and bursts open on the big hit.
const SELECT_IGNITION := preload("res://scenes/character_select/netsu_select_ignition.gd")
## Which intro plays: "ignition" (Nov 2 late) or "tiles" (the Melty Blood style portraits flying in).
@export var intro_style: String = "ignition"

const ACCENT := [Color(0.18, 0.55, 1.0), Color(1.0, 0.16, 0.3)]          # P1 blue, P2 crimson
const ACCENT_LIGHT := [Color(0.3, 0.82, 1.0), Color(1.0, 0.62, 0.7)]     # status text

@export var roster_slots: int = 12
@export var roster_columns: int = 6
@export_group("Roster tiles (screen pixels)")
## Nov 2 (evening, after Melty Blood Act Cadenza): two rows of upright portrait tiles at the bottom centre, the top row
## a little to the left, the bottom row a little to the right.
@export var tile_size: Vector2 = Vector2(104, 118)
@export var tile_gap: float = 10.0
@export var tile_rows_y: Array = [700.0, 828.0]
@export var tile_rows_shift: Array = [-30.0, 30.0]
@export_group("Renders (mockup pixels)")
## [top-left x, top-left y, mockup px per render px (1024-wide render), tilt in degrees]
@export var render_p1: Array = [-17.1, 35.1, 0.724, 3.25]
@export var render_p2: Array = [961.6, 42.9, 0.7238, -1.09]
## Oct 29: per-fighter zoom of the big render (by ShortName), around render_anchor (fractions of the image: the top of
## their head), so a render whose figure is drawn smaller (Noah, Leticia) shows as big as the others. 1 = as drawn.
@export var render_zoom: Dictionary = {"Noah": 1.5, "Leticia": 1.25}
@export var render_anchor: Dictionary = {"Noah": Vector2(0.48, 0.065), "Leticia": Vector2(0.51, 0.10)}
@export_group("In-game sprite preview")
## Where the preview fighter's feet stand (Player 1; Player 2 is mirrored), screen pixels.
@export var preview_feet: Vector2 = Vector2(420, 712)
## Screen pixels per 0.0055 m (one sprite pixel of the original 1024-canvas sprites).
@export var preview_scale: float = 0.95
## Seconds per idle frame (only for fighters whose idle animation can't be read).
@export var preview_frame_time: float = 0.1
## Metres per sprite pixel the preview size is based on.
const PREVIEW_REF_PIXEL := 0.0055

const PREVIEW_SIZE := Vector2i(440, 480)
const PREVIEW_FEET_Y := 440.0   # where the feet sit inside the preview picture
## Part of a fighter's Portrait shown in a slot (fractions of the image). Oct 29: every Portrait is now framed the same
## way (head and shoulders), so the slot shows nearly all of it (the slot is about 1.13 times wider than tall).
const PORTRAIT_CROP := Rect2(0.0, 0.03, 1.0, 0.885)

var _count := 0
var _cursor: Array[int] = [0, 0]
var _locked: Array[bool] = [false, false]
var _coloring: Array[bool] = [false, false]   # choosing a color right now
var _color: Array[int] = [0, 0]
var _assisting: Array[bool] = [false, false]  # choosing an assist right now
var _assist: Array[int] = [0, 0]              # index in data/assist_list.tres (everyone has one)
var _assist_cards: Array[Dictionary] = []
var _assist_grids: Array[Dictionary] = []      # per side: the grid panel shown while choosing an assist
var _human: Array[bool] = [true, false]       # side is played by a person
var _join_allowed := true                     # Training: P2 can press A to join
var _leaving := false
var _panel: Control = null                    # open settings sheet, if any

var _renders: Array[TextureRect] = []
var _render_home: Array[Vector2] = []
var _names: Array[Label] = []
var _tags: Array[Label] = []
var _status: Array[Label] = []
var _tiles: Array[Dictionary] = []            # {"pos": top-left of the slot's box, "size": box size, "shape": points}
var _cursor_frames: Array[Node2D] = []
var _cursor_tags: Array[Node2D] = []
var _cursor_tag_labels: Array[Label] = []
var _ready_label: Label
var _footer: Dictionary
var _sfx: AudioStreamPlayer

## Character select theme (Nov 2: "Beyond the Crimson Horizon" by Manbou Nitouhei, TamaDeez's edit that starts 16.28 s
## into the song, played to the end then from the top). Loops; keeps playing into stage select.
## Was "Battle in the Moonlight" (still selectable in battle).
const THEME_PATH := "res://assets/audio/music/netsu/beyond_the_crimson_horizon_select.ogg"

# preview per side: {"viewport", "camera", "sprite", "rect", "ring", "frames", "material", "frame", "time"}
var _preview: Array[Dictionary] = [{}, {}]
var _look_cache := {}   # "fighter:color" -> {"props": Dictionary, "frames": Array}
## Fighter scenes loading in the background (see _prefetch_fighters).
var _prefetch: Array = []
## True once both sides are picked and the stage select is opening.
var _picked := false

## Nov 2 (evening): the Melty Blood style dressing (back: emblem + lore; front: plate, mode, bio lines, label), and the
## intro: the screen starts dark, CHARACTER SELECT flashes in on the first beat, the portraits fly in one pair per half
## beat (top row from the left, bottom row from the right), and on the 4th beat (the big hit) the dark lifts, the
## emblem flares, the fighters slide in and the cursors appear.
var _mb_back: Control
var _mb_front: Control
var _overlay: ColorRect
var _intro_on := false
var _ignition_on := false
var _intro_clock := -1.0
var _intro_wait := 0.0
const INTRO_REVEAL_BEAT := 3
const INTRO_FLY := 0.12


func _ready() -> void:
	_play_theme_when_shown()
	if MatchSetup.humans.size() == 2:
		_human = [bool(MatchSetup.humans[0]), bool(MatchSetup.humans[1])]
		_join_allowed = false
	_sfx = AudioStreamPlayer.new()
	add_child(_sfx)
	NetsuUI.picture(self, NetsuUI.SELECT_BG)
	var lights := NetsuLights.new()
	lights.beams = NetsuLights.preset("select")
	add_child(lights)
	add_child(SELECT_FX.new())
	_mb_back = SELECT_MB.new()
	_mb_back.kind = 0
	add_child(_mb_back)
	_build_renders()
	_build_header()
	_footer = NetsuUI.footer(self, false, 858.0, 93.0, 888.0, 1613.0, 890.0)
	_set_prompts()
	_count = MatchSetup.fighter_count()
	if _count == 0:
		_footer["text"].text = "No fighters loaded - build the C# project (Build button, top right) and reopen this screen."
		return
	_cursor[1] = mini(1, _count - 1)
	_prefetch_fighters()
	_build_plates()
	_overlay = ColorRect.new()
	_overlay.color = Color(0.01, 0.015, 0.05)
	_overlay.size = Vector2(1920, 1080)
	_overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_overlay.visible = false
	add_child(_overlay)
	_mb_front = SELECT_MB.new()
	_mb_front.kind = 1
	_mb_front.mode_text = MatchSetup.mode_name.to_upper()
	add_child(_mb_front)
	_build_roster()
	_build_cursors()
	_build_previews()
	_ready_label = NetsuUI.label("READY?", 110, Color.WHITE, NetsuUI.sans(10, true))
	NetsuUI.glow(_ready_label, Color(0.2, 0.45, 1.0, 0.8), 18)
	_ready_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_ready_label.position = Vector2(0, 330)
	_ready_label.size = Vector2(1920, 160)
	_ready_label.pivot_offset = _ready_label.size / 2.0
	add_child(_ready_label)
	_build_assist_cards()
	_build_assist_grids()
	for side in 2:
		_color[side] = _default_color(side)
		_assist[side] = clampi(int(MatchSetup.assist_picks[side]), 0, maxi(0, MatchSetup.assist_count() - 1))
		_show_fighter(side, false)
	# footer on top, so settings sheets opened under it cover everything else
	move_child(_footer["root"], get_child_count() - 1)
	_refresh()
	if _theme_playing():
		_show_bio(0)
		NetsuUI.cascade(self, 5)   # back from the stage select: just the entrance (skips sound, background, beams, motion)
	else:
		_start_intro()


# --- Intro (Nov 2 evening, after Melty Blood Act Cadenza) -------------------------------------------

func _start_intro() -> void:
	if intro_style == "ignition":
		_intro_on = true
		_ignition_on = true
		var ign := SELECT_IGNITION.new()
		ign.revealed.connect(_on_ignition_revealed)
		add_child(ign)   # a CanvasLayer over everything
		return
	_intro_on = true
	_overlay.visible = true
	_overlay.modulate.a = 1.0
	_mb_front.shown = 0.0
	_mb_front.label_shown = 0.0
	_mb_front.top_shown = 0.0
	_mb_front.top_target = 0.0
	for tile in _tiles:
		tile["node"].modulate.a = 0.0
	for n in _cursor_frames + _cursor_tags:
		n.modulate.a = 0.0
	_footer["root"].modulate.a = 0.0


## Time into the intro: the select theme's playback position, or (no music after 1.2 s) its own clock.
func _intro_time(delta: float) -> float:
	var m: float = _mb_front.song_time()
	if m >= 0.0 and _intro_clock < 0.0:
		return m
	_intro_wait += delta
	if _intro_clock >= 0.0:
		_intro_clock += delta
	elif _intro_wait >= 1.2:
		_intro_clock = 0.0
	return _intro_clock


func _update_intro(delta: float) -> void:
	var t := _intro_time(delta)
	var b0: float = _mb_front.beat_time(0)
	var half: float = 30.0 / _mb_front.bpm
	var reveal: float = _mb_front.beat_time(INTRO_REVEAL_BEAT)
	# the bright and faint lines come up before the first beat; CHARACTER SELECT flashes in on it
	_mb_front.shown = clampf(t / maxf(b0, 0.05), 0.0, 1.0) if t >= 0.0 else 0.0
	if t >= b0 and _mb_front.label_shown < 1.0:
		_mb_front.label_shown = 1.0
		_mb_front.label_flash = 1.0
	# the portraits: one pair per half beat, top row left to right from the left, bottom row right to left from the right
	for i in _tiles.size():
		var tile: Dictionary = _tiles[i]
		var cut := _intro_cut(i)
		var land := b0 + cut * half
		var p := clampf((t - (land - INTRO_FLY)) / INTRO_FLY, 0.0, 1.0) if t >= 0.0 else 0.0
		var e := 1.0 - pow(1.0 - p, 3.0)
		var from := -320.0 if tile["row"] % 2 == 0 else 320.0
		tile["node"].position = tile["pos"] + Vector2(from * (1.0 - e), 0.0)
		tile["node"].modulate.a = e
		var flash: Polygon2D = tile["flash"]
		flash.color.a = 0.85 * clampf(1.0 - (t - land) / 0.16, 0.0, 1.0) if t >= land else 0.0
	if t >= reveal:
		_end_intro()


## Which half beat a tile lands on: pairs of (top row from the left, bottom row from the right).
func _intro_cut(i: int) -> int:
	var row := i / roster_columns
	var col := i % roster_columns
	var n := mini(roster_columns, maxi(1, _tiles.size() - row * roster_columns))
	var k := col if row % 2 == 0 else n - 1 - col
	var cuts := maxi(1, roster_columns)
	return int(round(float(k) * 5.0 / float(maxi(1, cuts - 1)))) if cuts > 1 else 0


func _end_intro() -> void:
	_intro_on = false
	for tile in _tiles:
		tile["node"].position = tile["pos"]
		tile["node"].modulate.a = 1.0
		var flash: Polygon2D = tile["flash"]
		flash.color.a = 0.0
	_mb_front.shown = 1.0
	_mb_front.label_shown = 1.0
	_mb_front.top_target = 1.0
	_mb_back.pop()
	var t := create_tween().set_parallel(true)
	t.tween_property(_overlay, "modulate:a", 0.0, 0.28)
	t.tween_property(_footer["root"], "modulate:a", 1.0, 0.3)
	for n in _cursor_frames + _cursor_tags:
		t.tween_property(n, "modulate:a", 1.0, 0.2).set_delay(0.08)
	t.chain().tween_callback(func(): _overlay.visible = false)
	for side in 2:
		_show_fighter(side, true)
	_show_bio(0)
	_refresh()


## The ignition burst open (the big hit): the fighters slide in, everything else cascades in behind the shards.
func _on_ignition_revealed() -> void:
	_intro_on = false
	_ignition_on = false
	NetsuUI.cascade(self, 5, 0.0, 0.22, 36.0)
	for side in 2:
		_show_fighter(side, true)
	_mb_back.pop()
	_show_bio(0)


## The bright scrolling line shows this side's fighter and bio.
func _show_bio(side: int) -> void:
	if _mb_front == null or _count == 0:
		return
	var profile = MatchSetup.fighter_profile(_cursor[side])
	var bio = profile.get("Bio")
	_mb_front.show_bio(String(profile.FighterName), String(bio) if bio != null else "", ACCENT[side])


## The select theme is already playing (coming back from the stage select).
func _theme_playing() -> bool:
	var audio := get_node_or_null("/root/AudioManager")
	if audio == null:
		return false
	var player = audio.get("BGM")
	return player is AudioStreamPlayer and player.playing and player.stream != null and str(player.stream.resource_path) == THEME_PATH


## Oct 24: the roster only names each colour's fighter scene now (ScenePath) instead of loading every
## fighter as the game starts, so the first time the cursor reached a fighter its scene (all of its
## sprites) would load right then and the screen would stall. Every fighter starts loading in the
## background as the screen opens instead; the sprite preview (_look) picks each one up from there.
func _prefetch_fighters() -> void:
	for f in _count:
		var path: String = MatchSetup.palette_scene_path(f, 0)
		if path != "" and not path in _prefetch:
			MatchSetup.bg_load(path)
			_prefetch.append(path)


## Lets go of the fighters loaded in the background, except the two picked ones when the stage
## select is next (they stay loaded for the fight; MatchSetup lets go of them once it's built).
func _exit_tree() -> void:
	var keep: Array = []
	if _picked:
		for side in 2:
			var path: String = MatchSetup.palette_scene_path(_cursor[side], 0)
			if path in _prefetch and not path in keep:
				keep.append(path)
	MatchSetup.keep_warm(keep)
	MatchSetup.bg_release(_prefetch.filter(func(path): return not path in keep))


func _process(delta: float) -> void:
	if _intro_on and not _ignition_on:
		_update_intro(delta)
	for side in 2:
		var pv: Dictionary = _preview[side]
		if pv.is_empty() or pv["frames"].is_empty():
			continue
		pv["time"] += delta
		var hold: float = pv["frames"][pv["frame"]].get("time", preview_frame_time)
		if pv["time"] >= hold:
			pv["time"] -= hold
			pv["frame"] = (pv["frame"] + 1) % pv["frames"].size()
			_set_preview_frame(side)


func _unhandled_input(event: InputEvent) -> void:
	if _panel != null:
		return
	if _intro_on:
		return   # nothing can be picked until the intro has opened the menu
	if _leaving or SceneRouter.is_busy() or _count == 0:
		if _count == 0 and _is_back(event, 1):
			SceneRouter.go_to(MAIN_MENU)
		return
	for player in [1, 2]:
		var p := "p%d_" % player
		if event.is_action_pressed(p + "ab"):
			_open_settings("pad")
		elif event.is_action_pressed(p + "bc"):
			_open_settings("keyboard")
		elif event.is_action_pressed(p + "left", true):
			_move(player, -1)
		elif event.is_action_pressed(p + "right", true):
			_move(player, 1)
		elif event.is_action_pressed(p + "up", true):
			_move(player, -roster_columns)
		elif event.is_action_pressed(p + "down", true):
			_move(player, roster_columns)
		elif _is_pick(event, player):
			_pick(player)
		elif _is_back(event, player):
			_back(player)
		else:
			continue
		get_viewport().set_input_as_handled()
		return


func _is_pick(event: InputEvent, player: int) -> bool:
	var p := "p%d_" % player
	return event.is_action_pressed(p + "a") or event.is_action_pressed(p + "s") \
		or event.is_action_pressed(p + "start")


func _is_back(event: InputEvent, player: int) -> bool:
	var p := "p%d_" % player
	if event.is_action_pressed(p + "b") or event.is_action_pressed(p + "c"):
		return true
	if player == 1 and event is InputEventKey:
		var key := event as InputEventKey
		return key.pressed and not key.echo and key.physical_keycode == KEY_ESCAPE
	return false


# --- Who controls what ---------------------------------------------------------------

## Which side (0 = left, 1 = right) this player is choosing for right now, or -1.
## A person picks their own side first, then the CPU's side if it's next to them.
func _side_for(player: int) -> int:
	var own := player - 1
	var other := 1 - own
	if not _human[own]:
		return -1
	if not _locked[own]:
		return own
	if not _human[other] and not _locked[other]:
		return other
	return -1


func _move(player: int, step: int) -> void:
	var side := _side_for(player)
	if side < 0 or _locked[side]:
		return
	if _coloring[side]:
		if absi(step) == 1:
			_cycle_color(side, step)
		return
	if _assisting[side]:
		_assist_step(side, step if absi(step) == 1 else signi(step) * ASSIST_COLUMNS)
		return
	var next := _cursor[side] + step
	if absi(step) > 1 and (next < 0 or next >= _count):
		return   # up/down past the real fighters: stay put
	_cursor[side] = wrapi(next, 0, _count)
	_color[side] = _default_color(side)
	_play(SFX_MOVE)
	_show_fighter(side, true)
	_show_bio(side)
	_refresh()


func _pick(player: int) -> void:
	var own := player - 1
	if not _human[own]:
		if _join_allowed and own == 1:
			_human[1] = true   # Player 2 joins
			_locked[1] = false
			_coloring[1] = false
			_play(SFX_PICK)
			_refresh()
		return
	if _locked[0] and _locked[1]:
		_start()
		return
	var side := _side_for(player)
	if side < 0 or _locked[side]:
		return
	if not _coloring[side] and not _assisting[side] and MatchSetup.palette_count(_cursor[side]) > 1:
		_coloring[side] = true   # fighter chosen -> now the color
		_color[side] = _default_color(side)
		_update_preview(side)
		_play(SFX_PICK)
		_refresh()
		return
	if not _assisting[side] and _wants_assist(side):
		_coloring[side] = false
		_assisting[side] = true   # color chosen -> now the assist
		_play(SFX_PICK)
		_refresh()
		return
	_coloring[side] = false
	_assisting[side] = false
	_locked[side] = true
	_play(SFX_PICK)
	var pop := create_tween()
	pop.tween_property(_names[side], "scale", Vector2(1.08, 1.08), 0.06)
	pop.tween_property(_names[side], "scale", Vector2.ONE, 0.14)
	_refresh()


func _back(player: int) -> void:
	var own := player - 1
	var other := 1 - own
	if not _human[own]:
		return
	if not _human[other] and _locked[own] and (_locked[other] or _coloring[other] or _assisting[other]):
		_step_back(other)   # undo the CPU's pick first
	elif _step_back(own):
		pass
	elif _join_allowed and own == 1:
		_human[1] = false   # Player 2 leaves
	else:
		_leaving = true
		_play(SFX_BACK)
		SceneRouter.go_to(MAIN_MENU)
		return
	_play(SFX_BACK)
	_refresh()


## One step back on a side: locked -> assist -> color -> fighter. False if there was nothing to undo.
func _step_back(side: int) -> bool:
	if _locked[side]:
		_locked[side] = false
		if _wants_assist(side):
			_assisting[side] = true
		else:
			_coloring[side] = MatchSetup.palette_count(_cursor[side]) > 1
		return true
	if _assisting[side]:
		_assisting[side] = false
		_coloring[side] = MatchSetup.palette_count(_cursor[side]) > 1
		return true
	if _coloring[side]:
		_coloring[side] = false
		return true
	return false


func _start() -> void:
	_leaving = true
	_play(SFX_START)
	var flash := create_tween()
	flash.tween_property(_ready_label, "scale", Vector2(1.1, 1.1), 0.08)
	flash.tween_property(_ready_label, "scale", Vector2.ONE, 0.12)
	MatchSetup.assist_picks = [_assist[0], _assist[1]]
	var a1 := _assist[0]
	var a2 := _assist[1]
	await get_tree().create_timer(0.3).timeout
	_picked = true
	MatchSetup.choose_stage(_cursor[0], _cursor[1], 0 if _human[0] else -1, 1 if _human[1] else -1,
		_color[0], _color[1], a1, a2)


# --- Colors -----------------------------------------------------------------------------

## A color nobody else is wearing on the same fighter (mirror matches).
func _default_color(side: int) -> int:
	var count := MatchSetup.palette_count(_cursor[side])
	for c in count:
		if not _color_taken(side, c):
			return c
	return 0


func _color_taken(side: int, color: int) -> bool:
	var other := 1 - side
	return _cursor[other] == _cursor[side] and _color[other] == color and (_locked[other] or _coloring[other] or _assisting[other])


func _cycle_color(side: int, dir: int) -> void:
	var count := MatchSetup.palette_count(_cursor[side])
	var c := _color[side]
	for i in count:
		c = wrapi(c + dir, 0, count)
		if not _color_taken(side, c):
			break
	if c == _color[side]:
		return
	_color[side] = c
	_play(SFX_MOVE)
	_update_preview(side)
	var pv: Dictionary = _preview[side]
	if not pv.is_empty():
		var rect: TextureRect = pv["rect"]
		var pop := create_tween()
		pop.tween_property(rect, "scale", Vector2(1.06, 1.06), 0.06)
		pop.tween_property(rect, "scale", Vector2.ONE, 0.1)
	_refresh()


# --- Assists ------------------------------------------------------------------------------

## Everyone picks an assist (the training dummy too: whoever picks its fighter picks its assist).
func _wants_assist(_side: int) -> bool:
	return MatchSetup.assist_count() > 0

## Moves the assist cursor: +-1 along the grid (wrapping round), +-ASSIST_COLUMNS a row down / up.
func _assist_step(side: int, step: int) -> void:
	var n := MatchSetup.assist_count()
	if n == 0:
		return
	var cur := _assist[side]
	var next := cur
	if absi(step) == 1:
		next = posmod(cur + step, n)
	else:
		next = cur + step
		if next < 0 or next >= n:
			# past the top / bottom row: the same column in the last / first row (if there is one)
			var col := cur % ASSIST_COLUMNS
			var rows := ceili(float(n) / ASSIST_COLUMNS)
			var row := (rows - 1) if step < 0 else 0
			next = mini(row * ASSIST_COLUMNS + col, n - 1)
	if next == cur:
		return
	_assist[side] = next
	_play(SFX_MOVE)
	_update_assist_grid(side, true)
	_refresh()


# --- The assist grid ------------------------------------------------------------------------
# Every assist in data/assist_list.tres as a tile (picture + name), ASSIST_COLUMNS per row. More than
# ASSIST_ROWS_SHOWN rows scroll. One panel per side, over the lower part of that side's render, shown while
# that side chooses its assist. Adding an assist to the list adds a tile; nothing here needs changing.

const ASSIST_COLUMNS := 4
const ASSIST_ROWS_SHOWN := 2
const ASSIST_TILE := Vector2(112, 112)     # the picture
const ASSIST_TILE_GAP := Vector2(14, 44)   # between tiles (the name sits in the vertical gap)

## Panel's top-left (screen px) for each side.
@export var assist_grid_pos: Array[Vector2] = [Vector2(330, 300), Vector2(1052, 300)]


func _assist_grid_size(rows: int) -> Vector2:
	var w := ASSIST_COLUMNS * ASSIST_TILE.x + (ASSIST_COLUMNS - 1) * ASSIST_TILE_GAP.x + 56
	var h := 62 + rows * (ASSIST_TILE.y + ASSIST_TILE_GAP.y) + 78
	return Vector2(w, h)


func _build_assist_grids() -> void:
	var n := MatchSetup.assist_count()
	var rows := ceili(float(maxi(n, 1)) / ASSIST_COLUMNS)
	var shown := mini(rows, ASSIST_ROWS_SHOWN)
	var size := _assist_grid_size(shown)
	for side in 2:
		var accent: Color = ACCENT[side]
		var root := Control.new()
		root.mouse_filter = Control.MOUSE_FILTER_IGNORE
		root.position = assist_grid_pos[side]
		root.size = size
		root.pivot_offset = size / 2.0
		root.visible = false
		add_child(root)
		NetsuUI.frame_panel(root, Rect2(Vector2.ZERO, size), accent)
		var title := NetsuUI.label("CHOOSE AN ASSIST", 18, ACCENT_LIGHT[side], NetsuUI.sans(6))
		title.position = Vector2(46, 14)
		title.size = Vector2(size.x - 92, 26)
		root.add_child(title)
		root.add_child(NetsuUI.hairline(Vector2(24, 48), size.x - 48, Color(accent.lightened(0.3), 0.7), 1.5, "both"))
		# the tiles live in a clipped area so extra rows can scroll
		var view := Control.new()
		view.clip_contents = true
		view.mouse_filter = Control.MOUSE_FILTER_IGNORE
		view.position = Vector2(28, 58)
		view.size = Vector2(size.x - 56, shown * (ASSIST_TILE.y + ASSIST_TILE_GAP.y))
		root.add_child(view)
		var scroll := Control.new()
		scroll.mouse_filter = Control.MOUSE_FILTER_IGNORE
		view.add_child(scroll)
		var tiles: Array[Dictionary] = []
		for i in n:
			var col := i % ASSIST_COLUMNS
			var row := i / ASSIST_COLUMNS
			var tile := Control.new()
			tile.mouse_filter = Control.MOUSE_FILTER_IGNORE
			tile.position = Vector2(col * (ASSIST_TILE.x + ASSIST_TILE_GAP.x), 4 + row * (ASSIST_TILE.y + ASSIST_TILE_GAP.y))
			tile.size = ASSIST_TILE
			tile.pivot_offset = ASSIST_TILE / 2.0
			scroll.add_child(tile)
			var back := ColorRect.new()
			back.color = Color(0.03, 0.05, 0.16, 0.95)
			back.size = ASSIST_TILE
			back.mouse_filter = Control.MOUSE_FILTER_IGNORE
			tile.add_child(back)
			var pic := TextureRect.new()
			pic.texture = MatchSetup.assist_icon(i)
			pic.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
			pic.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
			pic.size = ASSIST_TILE
			pic.mouse_filter = Control.MOUSE_FILTER_IGNORE
			tile.add_child(pic)
			var pts := PackedVector2Array([Vector2.ZERO, Vector2(ASSIST_TILE.x, 0), ASSIST_TILE, Vector2(0, ASSIST_TILE.y), Vector2.ZERO])
			var rim := Line2D.new()
			rim.points = pts
			rim.width = 2.0
			rim.default_color = Color(0.55, 0.65, 0.9, 0.5)
			tile.add_child(rim)
			var nm := NetsuUI.label(MatchSetup.assist_name(i).to_upper(), 16, NetsuUI.DIM, NetsuUI.sans(3))
			nm.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			nm.position = Vector2(-10, ASSIST_TILE.y + 6)
			nm.size = Vector2(ASSIST_TILE.x + 20, 24)
			tile.add_child(nm)
			tiles.append({"root": tile, "pic": pic, "rim": rim, "name": nm})
		# scroll arrows (only drawn when there are more rows than fit)
		var up := NetsuUI.arrow(Vector2(size.x - 18, 70), 14, 1, Color(accent.lightened(0.4), 0.9), 2.5)
		up.rotation_degrees = -90
		root.add_child(up)
		var down := NetsuUI.arrow(Vector2(size.x - 18, 58 + view.size.y - 8), 14, 1, Color(accent.lightened(0.4), 0.9), 2.5)
		down.rotation_degrees = 90
		root.add_child(down)
		# the picked assist: its name and its two calls
		var y := 58 + view.size.y + 4
		root.add_child(NetsuUI.hairline(Vector2(24, y), size.x - 48, Color(accent.lightened(0.3), 0.5), 1.5, "both"))
		var big := NetsuUI.label("", 26, Color.WHITE, NetsuUI.sans(3))
		NetsuUI.glow(big, Color(accent.darkened(0.5), 0.7), 5)
		big.position = Vector2(46, y + 6)
		big.size = Vector2(size.x - 92, 32)
		root.add_child(big)
		var moves := NetsuUI.label("", 15, Color(0.86, 0.9, 1.0), NetsuUI.body())
		moves.position = Vector2(46, y + 38)
		moves.size = Vector2(size.x - 92, 22)
		moves.clip_text = true
		root.add_child(moves)
		_assist_grids.append({"root": root, "scroll": scroll, "tiles": tiles, "up": up, "down": down, "big": big,
			"moves": moves, "rows": rows, "shown": shown, "first_row": 0})


## Highlights the picked tile, scrolls it into view, fills in its name and calls.
func _update_assist_grid(side: int, pop: bool = false) -> void:
	if _assist_grids.size() <= side:
		return
	var g: Dictionary = _assist_grids[side]
	var show: bool = _assisting[side] and _wants_assist(side)
	if show and not g["root"].visible:
		g["root"].visible = true
		g["root"].modulate.a = 0.0
		g["root"].scale = Vector2(0.96, 0.96)
		var t := create_tween().set_parallel(true).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
		t.tween_property(g["root"], "modulate:a", 1.0, 0.16)
		t.tween_property(g["root"], "scale", Vector2.ONE, 0.2)
	elif not show:
		g["root"].visible = false
		return
	var accent: Color = ACCENT[side]
	var pick := _assist[side]
	var tiles: Array = g["tiles"]
	for i in tiles.size():
		var tile: Dictionary = tiles[i]
		var on := i == pick
		tile["rim"].default_color = accent.lightened(0.35) if on else Color(0.55, 0.65, 0.9, 0.45)
		tile["rim"].width = 4.0 if on else 2.0
		tile["pic"].modulate = Color.WHITE if on else Color(0.62, 0.64, 0.74)
		tile["name"].add_theme_color_override("font_color", Color.WHITE if on else NetsuUI.DIM)
		var target := Vector2(1.07, 1.07) if on else Vector2.ONE
		if on and pop:
			var t := create_tween()
			t.tween_property(tile["root"], "scale", Vector2(1.12, 1.12), 0.06)
			t.tween_property(tile["root"], "scale", target, 0.1)
		else:
			tile["root"].scale = target
	# scroll so the picked row is visible
	var row := pick / ASSIST_COLUMNS
	var first: int = g["first_row"]
	if row < first:
		first = row
	elif row >= first + int(g["shown"]):
		first = row - int(g["shown"]) + 1
	g["first_row"] = first
	create_tween().tween_property(g["scroll"], "position:y", -first * (ASSIST_TILE.y + ASSIST_TILE_GAP.y), 0.12)
	g["up"].visible = first > 0
	g["down"].visible = first + int(g["shown"]) < int(g["rows"])
	g["big"].text = MatchSetup.assist_name(pick).to_upper()
	var calls := ""
	for m in MatchSetup.assist_moves(pick):
		calls += ("%s  %s        " % [m["input"], m["display"]])
	g["moves"].text = calls.strip_edges()


## The small card above each name plate: the assist's face and name.
func _build_assist_cards() -> void:
	var k := NetsuUI.K
	for side in 2:
		var right := side == 1
		var accent: Color = ACCENT[side]
		var root := Control.new()
		root.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var box := Vector2(70, 70) * k
		var x := (1671 - 448) * k if right else 378 * k
		root.position = Vector2(x, 584 * k)
		root.size = box
		root.pivot_offset = box / 2.0
		add_child(root)
		var back := ColorRect.new()
		back.color = Color(0.03, 0.05, 0.16, 0.9)
		back.size = box
		back.mouse_filter = Control.MOUSE_FILTER_IGNORE
		root.add_child(back)
		var pic := TextureRect.new()
		pic.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		pic.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
		pic.size = box
		pic.mouse_filter = Control.MOUSE_FILTER_IGNORE
		root.add_child(pic)
		var rim := Line2D.new()
		rim.points = PackedVector2Array([Vector2.ZERO, Vector2(box.x, 0), box, Vector2(0, box.y), Vector2.ZERO])
		rim.width = 2.5
		rim.default_color = accent.lightened(0.25)
		root.add_child(rim)
		var cap := NetsuUI.label("ASSIST", 15, ACCENT_LIGHT[side], NetsuUI.sans(6))
		cap.size = Vector2(240, 24)
		cap.position = Vector2(-248, 4) if not right else Vector2(box.x + 8, 4)
		cap.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT if not right else HORIZONTAL_ALIGNMENT_LEFT
		root.add_child(cap)
		var nm := NetsuUI.label("", 30, Color.WHITE, NetsuUI.sans(3))
		NetsuUI.glow(nm, Color(accent.darkened(0.5), 0.6), 5)
		nm.size = Vector2(240, 44)
		nm.position = Vector2(-248, 24) if not right else Vector2(box.x + 8, 24)
		nm.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT if not right else HORIZONTAL_ALIGNMENT_LEFT
		root.add_child(nm)
		root.visible = false
		_assist_cards.append({"root": root, "pic": pic, "name": nm})


func _update_assist_card(side: int, pop: bool = false) -> void:
	if _assist_cards.size() <= side:
		return
	var card: Dictionary = _assist_cards[side]
	var a := _assist[side]
	card["pic"].texture = MatchSetup.assist_icon(a)
	card["name"].text = MatchSetup.assist_name(a).to_upper()
	card["root"].visible = _wants_assist(side) and _locked[side]
	if pop and card["root"].visible:
		var t := create_tween()
		t.tween_property(card["root"], "scale", Vector2(1.08, 1.08), 0.06)
		t.tween_property(card["root"], "scale", Vector2.ONE, 0.1)


# --- Settings shortcuts -------------------------------------------------------------------

## Opens Options' Button Settings ("pad") or Keyboard Settings ("keyboard") over this screen.
func _open_settings(page: String) -> void:
	_play(SFX_PICK)
	_panel = load(OPTIONS_SCENE).instantiate()
	_panel.set("embedded", true)
	_panel.set("start_page", page)
	_panel.set("footer_override", _footer)
	add_child(_panel)
	move_child(_panel, _footer["root"].get_index())
	_panel.connect("closed", _on_settings_closed)


func _on_settings_closed() -> void:
	_panel = null
	_set_prompts()
	_refresh()


## The mockup shows SELECT / CONFIRM / BACK / BUTTON SETTINGS. The pills are
## Player 1's A+B macro on the pad and on the keyboard. (B+C still opens
## Keyboard Settings, it's just not listed.)
func _set_prompts() -> void:
	var ab := "%s / %s" % [Controls.pad_name(Controls.pad_binding(1, "ab")), Controls.key_name(Controls.keyboard[1].get("ab"))]
	_footer["prompts"].text = "SELECT     A  CONFIRM     B  BACK     %s  BUTTON SETTINGS" % ab


# --- Updating the screen -------------------------------------------------------------

func _side_active(side: int) -> bool:
	return _human[side] or _locked[1 - side]


func _refresh() -> void:
	var cpu_name := "TRAINING DUMMY" if MatchSetup.mode_name == "Training" else "CPU"
	for side in 2:
		_tags[side].text = ("PLAYER %d" % (side + 1)) if _human[side] else cpu_name
		var active := _side_active(side)
		var status := "WAITING..."
		var lit := false
		if _locked[side]:
			status = "READY!"
			lit = true
		elif _coloring[side]:
			var count := MatchSetup.palette_count(_cursor[side])
			status = "‹  COLOR %d / %d  ·  %s  ›" % [_color[side] + 1, count,
				MatchSetup.palette_name(_cursor[side], _color[side]).to_upper()]
			lit = true
		elif _assisting[side]:
			status = "ASSIST  ·  %s" % MatchSetup.assist_name(_assist[side]).to_upper()
			lit = true
		elif active:
			status = "SELECTING..."
			lit = true
		_status[side].text = status
		_status[side].add_theme_color_override("font_color", ACCENT_LIGHT[side] if lit else Color(0.95, 0.95, 1.0, 0.92))
		_renders[side].modulate = Color.WHITE if active else Color(0.72, 0.72, 0.8)
		var pv: Dictionary = _preview[side]
		_update_assist_card(side)
		_update_assist_grid(side)
		if not pv.is_empty():
			var show_sprite: bool = _coloring[side] or _assisting[side] or _locked[side]
			pv["rect"].visible = show_sprite
			pv["ring"].visible = show_sprite
		_cursor_frames[side].visible = active
		_cursor_tags[side].visible = active
		_cursor_frames[side].modulate = Color(1.25, 1.25, 1.25) if _locked[side] else Color.WHITE
		_cursor_tag_labels[side].text = ("%dP" % (side + 1)) if _human[side] else "CPU"
		_move_cursor(side)
	var both: bool = _locked[0] and _locked[1]
	_ready_label.visible = both
	if both:
		_footer["text"].text = "Both fighters ready - press A to choose a stage."
		return
	for side in 2:
		if _coloring[side]:
			_footer["text"].text = "%s - choose a color with left / right, then A." % _who(side)
			return
		if _assisting[side]:
			_footer["text"].text = "%s - choose an assist with the arrows, then A.  (B: back to the colour)" % _who(side)
			return
	for side in 2:
		if _side_active(side) and not _locked[side]:
			if not _human[side]:
				_footer["text"].text = "Choose your opponent." + \
					("   (Player 2: press A to join)" if _join_allowed else "")
			else:
				_footer["text"].text = "Choose your fighter." if side == 0 else "Player 2 - choose your fighter."
			return


func _who(side: int) -> String:
	return ("Player %d" % (side + 1)) if _human[side] else "Opponent"


func _show_fighter(side: int, animate: bool) -> void:
	var profile = MatchSetup.fighter_profile(_cursor[side])
	var tex: Texture2D = profile.Render
	var r := _renders[side]
	r.texture = tex
	var place: Array = render_p1 if side == 0 else render_p2
	_render_home[side] = NetsuUI.m(place[0], place[1])
	if tex:
		var base_size: Vector2 = tex.get_size() * float(place[2]) * NetsuUI.K * (1024.0 / tex.get_size().x)
		var key := String(profile.ShortName)
		var zoom := float(render_zoom.get(key, 1.0))
		r.size = base_size * zoom
		if zoom != 1.0:
			# keep the anchor (top of the head) where it would be unzoomed
			var anchor: Vector2 = render_anchor.get(key, Vector2(0.5, 0.1))
			_render_home[side] -= (anchor * base_size * (zoom - 1.0)).rotated(deg_to_rad(float(place[3])))
	r.rotation_degrees = place[3]
	_names[side].text = String(profile.FighterName).to_upper()
	_update_preview(side)
	if not animate:
		r.position = _render_home[side]
		return
	r.position = _render_home[side] + Vector2(-160 if side == 0 else 160, 0)
	var slide := create_tween().set_parallel(true).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	slide.tween_property(r, "position", _render_home[side], 0.26)
	slide.tween_property(r, "self_modulate:a", 1.0, 0.2).from(0.0)


func _move_cursor(side: int) -> void:
	var tile: Dictionary = _tiles[_cursor[side]]
	var target: Vector2 = tile["pos"]
	var shared := _cursor[0] == _cursor[1] and _cursor_frames[0].visible and _cursor_frames[1].visible
	for line in _cursor_frames[side].get_children():
		if line is Line2D:
			line.points = tile["shape"]   # the two rows are slightly different sizes
	var nudge := Vector2.ZERO
	if shared:
		nudge = Vector2(-4, -4) if side == 0 else Vector2(4, 4)
	create_tween().tween_property(_cursor_frames[side], "position", target + nudge, 0.1)
	# tag sits on the slot's top edge; when both players share a slot, 2P moves right
	var top_mid: Vector2 = tile["pos"] + Vector2(tile["skew"] + tile["top_w"] / 2.0, 0)
	var tag_x := -9.0 * NetsuUI.K
	if shared:
		tag_x = (-30.0 if side == 0 else 22.0) * NetsuUI.K
	create_tween().tween_property(_cursor_tags[side], "position", top_mid + Vector2(tag_x, 0), 0.1)


func _play(path: String) -> void:
	var stream = load(path)
	if stream:
		_sfx.stream = stream
		_sfx.play()


# --- In-game sprite preview ---------------------------------------------------------------

## Reads how a color looks straight out of its fighter scene (the "Sprite"
## node under Graphics/Mesh: pixel size, color material...) without running the
## fighter, plus its idle animation (state 0 of the fighter data: each sprite with
## its own offset and how long it shows). Fighters whose data can't be read fall
## back to idle1.png, idle2.png ... next to the scene's sprite image.
func _look(fighter: int, color: int) -> Dictionary:
	var key := "%d:%d" % [fighter, color]
	if _look_cache.has(key):
		return _look_cache[key]
	var look := {"props": {}, "frames": []}   # frames: [{"tex", "offset", "time"}]
	var data = null
	var scene: PackedScene = MatchSetup.palette_scene(fighter, color)
	if scene:
		var state := scene.get_state()
		for i in state.get_node_count():
			var path := String(state.get_node_path(i))
			if path == ".":
				for j in state.get_node_property_count(i):
					if String(state.get_node_property_name(i, j)) == "Data":
						data = state.get_node_property_value(i, j)
			elif path.ends_with("Graphics/Mesh/Sprite"):
				for j in state.get_node_property_count(i):
					look["props"][String(state.get_node_property_name(i, j))] = state.get_node_property_value(i, j)
	look["frames"] = _idle_frames(data)
	if look["frames"].is_empty():
		var first = look["props"].get("texture")
		if first is Texture2D:
			var folder: String = first.resource_path.get_base_dir()
			var n := 1
			while ResourceLoader.exists("%s/idle%d.png" % [folder, n]):
				look["frames"].append({"tex": load("%s/idle%d.png" % [folder, n])})
				n += 1
			if look["frames"].is_empty():
				look["frames"].append({"tex": first})
	_look_cache[key] = look
	return look


## The idle animation of a fighter data resource: [{"tex", "offset", "time"}].
func _idle_frames(data) -> Array:
	var out: Array = []
	if data == null or not (data is Resource):
		return out
	var states = data.get("States")
	if not (states is Array) or states.is_empty() or states[0] == null:
		return out
	var anim = states[0].get("AnimationData")
	if anim == null:
		return out
	var keys = anim.get("Animations")
	if not (keys is Array):
		return out
	var dur := int(anim.get("Duration"))
	for k in keys.size():
		var mods = keys[k].get("Modifiers") if keys[k] else null
		if not (mods is Array) or mods.is_empty() or mods[0] == null or mods[0].get("Sprite") == null:
			continue
		var at := int(keys[k].get("AtFrame"))
		var nxt := int(keys[k + 1].get("AtFrame")) if k + 1 < keys.size() else dur
		out.append({"tex": mods[0].get("Sprite"), "offset": mods[0].get("Offset"), "time": maxf(1.0, float(nxt - at)) / 60.0})
	return out


func _update_preview(side: int) -> void:
	var pv: Dictionary = _preview[side]
	if pv.is_empty():
		return
	var look := _look(_cursor[side], _color[side])
	var sprite: Sprite3D = pv["sprite"]
	sprite.material_override = null
	for prop in look["props"]:
		if prop in ["texture", "layers", "material_override", "script"]:
			continue
		sprite.set(prop, look["props"][prop])
	sprite.flip_h = false   # Player 2's picture is mirrored by its TextureRect instead
	# each preview gets its own copy of the color material (the shader reads the current frame)
	var mat = look["props"].get("material_override")
	pv["material"] = mat.duplicate() if mat is Material else null
	sprite.material_override = pv["material"]
	pv["frames"] = look["frames"]
	pv["frame"] = 0
	_set_preview_frame(side)
	_frame_camera(side)


func _set_preview_frame(side: int) -> void:
	var pv: Dictionary = _preview[side]
	if pv["frames"].is_empty():
		return
	var f: Dictionary = pv["frames"][pv["frame"]]
	var tex: Texture2D = f["tex"]
	var sprite: Sprite3D = pv["sprite"]
	sprite.texture = tex
	if f.get("offset") is Vector2:
		sprite.offset = f["offset"]
	var mat = pv["material"]
	if mat is ShaderMaterial:
		mat.set_shader_parameter("albedo_texture", tex)


## Points the preview camera so the fighter's feet (its origin) sit at
## PREVIEW_FEET_Y, centred left-right, at `preview_scale` screen pixels per
## PREVIEW_REF_PIXEL metres, the same size for every fighter whatever its sprites.
func _frame_camera(side: int) -> void:
	var pv: Dictionary = _preview[side]
	var cam: Camera3D = pv["camera"]
	var m_per_px := PREVIEW_REF_PIXEL / preview_scale
	cam.size = PREVIEW_SIZE.y * m_per_px
	cam.position = Vector3(0.0, (PREVIEW_FEET_Y - PREVIEW_SIZE.y / 2.0) * m_per_px, 10.0)


func _build_previews() -> void:
	for side in 2:
		var vp := SubViewport.new()
		vp.size = PREVIEW_SIZE
		vp.transparent_bg = true
		vp.own_world_3d = true
		vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
		add_child(vp)
		var cam := Camera3D.new()
		cam.projection = Camera3D.PROJECTION_ORTHOGONAL
		cam.near = 0.1
		cam.far = 50.0
		vp.add_child(cam)
		var sprite := Sprite3D.new()
		vp.add_child(sprite)
		var accent: Color = ACCENT[side]
		var feet := Vector2(preview_feet.x if side == 0 else 1920.0 - preview_feet.x, preview_feet.y)
		# glowing ring the fighter stands on
		var ring := Node2D.new()
		ring.position = feet
		var glow := Polygon2D.new()
		glow.polygon = _ellipse(Vector2(86, 18), 40)
		glow.color = Color(accent, 0.22)
		ring.add_child(glow)
		for k in 2:
			var line := Line2D.new()
			line.points = _ellipse(Vector2(86 - k * 28, 18 - k * 6), 40)
			line.closed = true
			line.width = 3.0 - k
			line.default_color = Color(accent, 0.9 - k * 0.3)
			ring.add_child(line)
		add_child(ring)
		var rect := TextureRect.new()
		rect.texture = vp.get_texture()
		rect.size = Vector2(PREVIEW_SIZE)
		rect.position = feet - Vector2(PREVIEW_SIZE.x / 2.0, PREVIEW_FEET_Y)
		rect.pivot_offset = Vector2(PREVIEW_SIZE.x / 2.0, PREVIEW_FEET_Y)
		rect.flip_h = side == 1   # Player 2 faces left
		rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(rect)
		_preview[side] = {"viewport": vp, "camera": cam, "sprite": sprite, "rect": rect, "ring": ring,
			"frames": [], "material": null, "frame": 0, "time": 0.0}


func _ellipse(radius: Vector2, points: int) -> PackedVector2Array:
	var out := PackedVector2Array()
	for i in points:
		var a := TAU * i / points
		out.append(Vector2(cos(a) * radius.x, sin(a) * radius.y))
	return out


# --- Building --------------------------------------------------------------------------

func _build_renders() -> void:
	var fade := ShaderMaterial.new()
	fade.shader = RENDER_FADE
	for side in 2:
		var r := TextureRect.new()
		r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		r.stretch_mode = TextureRect.STRETCH_SCALE
		r.flip_h = false   # renders are never mirrored (mirroring swaps sword hands, logos...)
		r.material = fade
		r.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(r)
		_renders.append(r)
		_render_home.append(Vector2.ZERO)


func _build_header() -> void:
	# a dark band across the top, over the renders (a raised fist or a hat reaches up here): the plate and mode read on it.
	# Nov 2 evening: CHARACTER SELECT moved over the roster and the mode to the top centre (netsu_select_mb.gd).
	var shade := NetsuUI.gradient_rect(Color(0.02, 0.03, 0.12, 0.62), Color(0.02, 0.03, 0.12, 0.0), true)
	shade.size = Vector2(1920, 190)
	add_child(shade)


func _build_plates() -> void:
	var k := NetsuUI.K
	for side in 2:
		var accent: Color = ACCENT[side]
		var right := side == 1
		var root := Control.new()
		root.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(root)
		# main band behind the name, fading toward the middle of the screen
		var band := NetsuUI.gradient_rect(Color(accent.darkened(0.55), 0.0 if right else 0.85),
			Color(accent.darkened(0.55), 0.85 if right else 0.0), false)
		band.position = Vector2((1671 - 470) * k if right else 0.0, 658 * k)
		band.size = Vector2(470 * k + (2 if right else 0), 62 * k)
		root.add_child(band)
		# small tab behind PLAYER 1 / 2
		var tab: PackedVector2Array
		if right:
			tab = PackedVector2Array([Vector2(1467 * k, 626.7 * k), Vector2(1920, 626.7 * k), Vector2(1920, 657 * k), Vector2(1448 * k, 657 * k)])
		else:
			tab = PackedVector2Array([Vector2(0, 626.7 * k), Vector2(217 * k, 626.7 * k), Vector2(238 * k, 657 * k), Vector2(0, 657 * k)])
		var tab_fill := Polygon2D.new()
		tab_fill.polygon = tab
		var deep := Color(accent.darkened(0.6), 0.85)
		var mid := Color(accent.darkened(0.45), 0.7)
		tab_fill.vertex_colors = PackedColorArray([mid, deep, deep, mid] if right else [deep, mid, mid, deep])
		root.add_child(tab_fill)
		var tab_edge := Line2D.new()
		tab_edge.points = PackedVector2Array([tab[3], tab[0], tab[1]]) if right else PackedVector2Array([tab[0], tab[1], tab[2]])
		tab_edge.width = 2.0
		tab_edge.default_color = Color(accent.lightened(0.3), 0.95)
		root.add_child(tab_edge)
		# glowing lines above and below the name
		var x0 := (1671 - 470) * k if right else 0.0
		var fade := "left" if right else "right"
		root.add_child(NetsuUI.hairline(Vector2(x0, 658 * k), 470 * k + 2, Color(accent.lightened(0.25), 0.95), 2.0, fade))
		root.add_child(NetsuUI.hairline(Vector2(x0, 720 * k), 470 * k + 2, Color(accent.lightened(0.15), 0.35), 7.0, fade))
		root.add_child(NetsuUI.hairline(Vector2(x0, 720 * k), 470 * k + 2, Color(accent.lightened(0.45), 1.0), 2.5, fade))
		var align := HORIZONTAL_ALIGNMENT_RIGHT if right else HORIZONTAL_ALIGNMENT_LEFT
		var tag := NetsuUI.label("PLAYER 1", 18, Color(0.8, 0.9, 1.0) if not right else Color(1, 0.92, 0.94), NetsuUI.sans(6))
		_place(tag, 49, 1622, 642, right, 6)
		tag.horizontal_alignment = align
		root.add_child(tag)
		_tags.append(tag)
		var n := NetsuUI.label("", 50, Color.WHITE, NetsuUI.sans(3))
		NetsuUI.glow(n, Color(accent.darkened(0.5), 0.6), 6)
		_place(n, 46, 1626, 692, right, 3)
		n.horizontal_alignment = align
		n.pivot_offset = Vector2(n.size.x if right else 0.0, n.size.y / 2.0)
		root.add_child(n)
		_names.append(n)
		var st := NetsuUI.label("", 20, Color.WHITE, NetsuUI.sans(8))
		_place(st, 48, 1626, 742, right, 8)
		st.horizontal_alignment = align
		root.add_child(st)
		_status.append(st)


## Puts a plate label with its text starting at x_left (Player 1) or ending at
## x_right (Player 2), vertically centred on y (mockup pixels).
func _place(l: Label, x_left: float, x_right: float, y: float, right: bool, spacing: int) -> void:
	var k := NetsuUI.K
	l.size = Vector2(760, 70)
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	# letter spacing also adds room after the last letter: push right-aligned text over by it
	l.position = Vector2(x_right * k - 760 + spacing if right else x_left * k, y * k - 35)


func _build_roster() -> void:
	var total := maxi(roster_slots, _count)
	var empty_tex: Texture2D = load(NetsuUI.SLOT_EMPTY) if ResourceLoader.exists(NetsuUI.SLOT_EMPTY) else null
	var w := tile_size.x
	var h := tile_size.y
	var row_w := roster_columns * w + (roster_columns - 1) * tile_gap
	for i in total:
		var row := i / roster_columns
		var col := i % roster_columns
		var ry: float = float(tile_rows_y[mini(row, tile_rows_y.size() - 1)]) + maxi(0, row - (tile_rows_y.size() - 1)) * (h + 10.0)
		var shift: float = float(tile_rows_shift[row % tile_rows_shift.size()])
		var shape := NetsuUI.para(w, h, 0.0)
		var tile := Node2D.new()
		tile.position = Vector2(960.0 - row_w / 2.0 + shift + col * (w + tile_gap), ry)
		var box := Vector2(w, h)
		tile.add_child(NetsuUI.poly(shape, Color(0.04, 0.05, 0.12, 0.92)))
		var pic := Polygon2D.new()
		pic.polygon = shape
		var tex: Texture2D = null
		if i < _count:
			tex = MatchSetup.fighter_profile(i).Portrait
		else:
			tex = empty_tex
		if tex:
			pic.texture = tex
			var ts := tex.get_size()
			var crop := Rect2(0, 0, 1, 1)
			if i < _count:
				# upright tile: keep PORTRAIT_CROP's height, take a centred strip as wide as the tile's shape
				var cw := minf(1.0, (w / h) * PORTRAIT_CROP.size.y * ts.y / ts.x)
				crop = Rect2(0.5 - cw / 2.0, PORTRAIT_CROP.position.y, cw, PORTRAIT_CROP.size.y)
			var uv := PackedVector2Array()
			for p in shape:
				uv.append(Vector2((crop.position.x + p.x / box.x * crop.size.x) * ts.x,
					(crop.position.y + p.y / box.y * crop.size.y) * ts.y))
			pic.uv = uv
			if i >= _count:
				pic.color = Color(1, 1, 1, 0.55)
			tile.add_child(pic)
		# a soft shade along the bottom and the white frame (Melty Blood's tiles have a thin light border)
		var shade := Polygon2D.new()
		shade.polygon = PackedVector2Array([Vector2(0, h * 0.62), Vector2(w, h * 0.62), Vector2(w, h), Vector2(0, h)])
		shade.vertex_colors = PackedColorArray([Color(0.02, 0.03, 0.12, 0.0), Color(0.02, 0.03, 0.12, 0.0),
			Color(0.02, 0.03, 0.12, 0.45), Color(0.02, 0.03, 0.12, 0.45)])
		tile.add_child(shade)
		tile.add_child(NetsuUI.outline(shape, Color(0.92, 0.94, 1.0, 0.95 if i < _count else 0.55), 2.0))
		var flash := NetsuUI.poly(shape, Color(1, 1, 1, 0.0))   # the intro's white flash as it lands
		tile.add_child(flash)
		add_child(tile)
		_tiles.append({"pos": tile.position, "size": box, "shape": shape, "skew": 0.0, "top_w": w,
			"node": tile, "flash": flash, "row": row})


func _build_cursors() -> void:
	var k := NetsuUI.K
	for side in 2:
		var color: Color = ACCENT[side]
		var frame := Node2D.new()
		var shape: PackedVector2Array = _tiles[0]["shape"]
		frame.add_child(NetsuUI.outline(shape, Color(color, 0.35), 9.0))
		frame.add_child(NetsuUI.outline(shape, Color(color.lightened(0.15), 1.0), 3.5))
		frame.add_child(NetsuUI.outline(shape, Color(1, 1, 1, 0.5), 1.0))
		add_child(frame)
		_cursor_frames.append(frame)
		# the "1P" / "2P" tab sitting on the slot's top edge
		var tag := Node2D.new()
		var tw := 38.0 * k
		var th := 19.0 * k
		var tab := NetsuUI.para(tw, th, 4.0 * k)
		var tab_node := NetsuUI.poly(tab, color)
		tab_node.position = Vector2(-tw / 2.0, -th)
		tag.add_child(tab_node)
		var l := NetsuUI.label("1P", 21, Color.WHITE, NetsuUI.sans(0, true))
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		l.position = Vector2(-tw / 2.0, -th - 2)
		l.size = Vector2(tw + 4.0 * k, th + 2)
		tag.add_child(l)
		add_child(tag)
		_cursor_tags.append(tag)
		_cursor_tag_labels.append(l)
		frame.position = _tiles[_cursor[side]]["pos"]
		tag.position = _tiles[_cursor[side]]["pos"]
	# whoever is not moving sits under the other; keep 1P on top
	move_child(_cursor_frames[0], get_child_count() - 1)
	move_child(_cursor_tags[0], get_child_count() - 1)


## Oct 25 evening: the theme starts when the screen appears (not while the loading emblem still covers it).
func _play_theme_when_shown() -> void:
	var router := get_node_or_null("/root/SceneRouter")
	if router and router.has_method("wait_shown"):
		await router.wait_shown()
	if is_inside_tree():
		_play_theme()


## Starts the select theme on the BGM bus (Options > Sound > BGM volume).
## If it's already playing (back from stage select), it carries on instead of restarting.
func _play_theme() -> void:
	var audio := get_node_or_null("/root/AudioManager")
	if audio == null:
		return
	var theme = load(THEME_PATH) if ResourceLoader.exists(THEME_PATH) else null
	if theme == null:
		audio.call("StopBGM")
		return
	if "loop" in theme:
		theme.loop = true
	var player = audio.get("BGM")
	if player is AudioStreamPlayer and player.playing and player.stream == theme:
		return
	audio.call("PlayBGM", theme)
