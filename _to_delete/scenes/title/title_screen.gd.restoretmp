extends Control
## TITLE SCREEN  (Oct 19 2026 mockup)
##
## The logo on the blue / crimson background and a pulsing PRESS START.
## Any button goes straight to the main menu (Story Mode and Exit Game were
## removed from this screen; RETURN on the main menu comes back here).
##
## The background (logo included) is assets/ui/netsu/title_bg.png, made from the
## mockup with PRESS START taken out so it can pulse.

@export var press_text: String = "PRESS START"
## Centre of PRESS START, in mockup pixels (1672 x 941).
@export var press_center: Vector2 = Vector2(837, 697)
@export var press_size: int = 45
@export var press_spacing: int = 22
@export var drifting_petals: int = 26

## Nov 2: title theme, "forget-me-not" (ワスレナグサ) by Manbou Nitouhei (OpenTracks #9562). Trimmed to the composer's
## loop end (4:45.473); plays from the start once, then loops back to theme_loop_start. Stops when the main menu opens.
const THEME_PATH := "res://assets/audio/music/netsu/forget_me_not.ogg"
@export var theme_loop_start: float = 40.421
## Nov 2: the sound when PRESS START is pressed (SFX bus). It plays on the scene tree's root, so the scene change
## doesn't cut it off.
@export_file("*.wav", "*.ogg") var start_sound: String = "res://assets/audio/menu/mahou/StrongConfirmSoundVers4.wav"
@export var start_sound_db: float = -3.0

var _press: Label
var _busy := false
var _time := 0.0


func _ready() -> void:
	_play_theme()
	var bg := NetsuUI.picture(self, NetsuUI.TITLE_BG)
	var lights := NetsuLights.new()
	lights.beams = NetsuLights.preset("title")
	lights.petals = drifting_petals
	add_child(lights)
	_press = NetsuUI.label(press_text, press_size, NetsuUI.TEXT, NetsuUI.serif(600, press_spacing))
	NetsuUI.glow(_press, Color(0.3, 0.55, 1.0, 0.35), 10)
	_press.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_press.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	var c := NetsuUI.m(press_center.x, press_center.y)
	# letter spacing adds room after the last letter too: nudge right by half of it to stay centred
	_press.position = Vector2(c.x - 600 + press_spacing / 2.0, c.y - 40)
	_press.size = Vector2(1200, 80)
	_press.pivot_offset = _press.size / 2.0
	add_child(_press)
	bg.modulate = Color(0, 0, 0)
	var t := create_tween().set_parallel(true)
	t.tween_property(bg, "modulate", Color.WHITE, 0.7)
	_press.modulate.a = 0.0


func _process(delta: float) -> void:
	_time += delta
	if not _busy and _time > 0.6:
		_press.modulate.a = 0.62 + 0.38 * sin((_time - 0.6) * 2.6 + PI / 2.0)


func _input(event: InputEvent) -> void:
	if _busy or SceneRouter.is_busy() or _time < 0.3:
		return
	if Controls.is_any_press(event):
		get_viewport().set_input_as_handled()
		Controls.menu_owner = Controls.player_from_event(event)
		_go()


func _go() -> void:
	_busy = true
	_play_start_sound()
	_press.modulate.a = 1.0
	var flash := create_tween()
	flash.tween_property(_press, "scale", Vector2(1.08, 1.08), 0.07)
	flash.tween_property(_press, "scale", Vector2.ONE, 0.12)
	await get_tree().create_timer(0.18).timeout
	SceneRouter.go_to(SceneRouter.MAIN_MENU, Color.WHITE)


## Starts the title theme on the BGM bus (Options > Sound > BGM volume). Carries on if it's already playing.
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
	if "loop_offset" in theme:
		theme.loop_offset = theme_loop_start
	var player = audio.get("BGM")
	if player is AudioStreamPlayer and player.playing and player.stream == theme:
		return
	audio.call("PlayBGM", theme)


func _play_start_sound() -> void:
	if start_sound == "" or not ResourceLoader.exists(start_sound):
		return
	var player := AudioStreamPlayer.new()
	player.bus = &"SFX"
	player.stream = load(start_sound)
	player.volume_db = start_sound_db
	player.finished.connect(player.queue_free)
	get_tree().root.add_child(player)
	player.play()
