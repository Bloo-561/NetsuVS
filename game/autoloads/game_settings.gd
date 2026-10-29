extends Node
## GAME SETTINGS (autoload - reach it from anywhere as "GameSettings")
##
## Everything the Options screen changes lives here, and is saved to
##   user://settings.cfg
## (on Windows: %APPDATA%\Godot\app_userdata\<project name>\settings.cfg).
## Delete that file to get every default back.
##
##   GameSettings.get_value("sound", "bgm")          # -> 70
##   GameSettings.set_value("sound", "bgm", 50)      # applies straight away
##
## Sound and display settings take effect the moment they change. Game settings
## (rounds, time, CPU difficulty, intros) are read by MatchSetup.start_match()
## when the next fight begins. Button layouts live in Controls; this script only
## saves and loads them.
##
## TO ADD A SETTING: add it to DEFAULTS, handle it in _apply() if it needs to do
## something right away, and add a row for it in scenes/options/options_menu.gd.

const PATH := "user://settings.cfg"

## Window sizes offered on the Display page (bigger than the monitor = hidden).
const RESOLUTIONS: Array[Vector2i] = [Vector2i(1280, 720), Vector2i(1600, 900), Vector2i(1920, 1080),
	Vector2i(2560, 1440), Vector2i(3840, 2160)]
const WINDOW_MODES := ["Window", "Borderless", "Fullscreen"]
## Same order as the engine's BotDifficulty (engine/sakuga/Globals/BotDifficulty.cs).
const DIFFICULTIES := ["Beginner", "Easy", "Normal", "Hard", "Very Hard", "Pro"]
## Seconds per round. -1 = no time limit.
const ROUND_TIMES := [30, 45, 60, 99, -1]
const LANGUAGES := ["English"]

const DEFAULTS := {
	"system": {"auto_save": true, "language": 0},
	"sound": {"master": 80, "bgm": 70, "sfx": 80, "voice": 80, "announcer": 80, "announcements": true},
	"display": {"resolution": 0, "window_mode": 0, "vsync": true, "keep_aspect": true},
	"game": {"difficulty": 2, "rounds_versus": 2, "time_versus": 99, "rounds_arcade": 2, "time_arcade": 99,
		"intros": true, "rounds_online": 2},   # rounds_online (Oct 26, TamaDeez): online is first to 2 by default
	# Training Menu (game/ui/training/netsu_training_menu.gd). The engine side is
	# engine/sakuga/Game/NetsuTraining.cs; the meaning of each number is listed there.
	"training": {"dummy": 0, "cpu_level": 2, "guard": 0, "counter_hit": false, "reset_mode": 0,
		"air_recovery": 0, "wakeup": 0, "wakeup_action": 0,
		"p1_health": 100, "p2_health": 100, "p1_craft": -1, "p2_craft": -1, "p1_burst": -1, "p2_burst": -1,
		"assist_instant": true, "playback_repeat": false,
		"show_info": true, "show_inputs": true, "show_hitboxes": false, "show_guide": true},
	# Online lobbies (scenes/online/online_lobby.gd): the name the other players see ("" = "Player N").
	"online": {"name": ""},
}

## Volume setting -> audio bus (data/audio_bus_layout.tres).
const BUSES := {"master": "Master", "bgm": "BGM", "sfx": "SFX", "voice": "Voice", "announcer": "Announcer"}

signal changed(section: String, key: String)

## True when something changed since the last save (only matters with Auto Save off).
var dirty := false

var _values := {}
var _base_db := {}   # each bus's volume from the bus layout = what "100%" sounds like


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	for key in BUSES:
		var bus := AudioServer.get_bus_index(BUSES[key])
		_base_db[key] = AudioServer.get_bus_volume_db(bus) if bus >= 0 else 0.0
	_values = DEFAULTS.duplicate(true)
	_load()
	for section in _values:
		for key in _values[section]:
			_apply(section, key)
	dirty = false


func get_value(section: String, key: String):
	return _values.get(section, {}).get(key, DEFAULTS[section][key])


func set_value(section: String, key: String, value) -> void:
	_values[section][key] = value
	_apply(section, key)
	changed.emit(section, key)
	_changed()


## Puts one page of the Options screen back to its defaults.
func restore_defaults(section: String) -> void:
	_values[section] = DEFAULTS[section].duplicate(true)
	for key in _values[section]:
		_apply(section, key)
		changed.emit(section, key)
	_changed()


## Puts just some settings of a section back to their defaults
## (the Versus "Game Settings" sheet only resets its own rows).
func restore_keys(section: String, keys: Array) -> void:
	for key in keys:
		_values[section][key] = DEFAULTS[section][key]
		_apply(section, key)
		changed.emit(section, key)
	_changed()


## Call after changing Controls' button layouts so they get saved.
func bindings_changed() -> void:
	_changed()


func save() -> bool:
	var cfg := ConfigFile.new()
	for section in _values:
		for key in _values[section]:
			cfg.set_value(section, key, _values[section][key])
	var b: Dictionary = Controls.export_bindings()
	for key in b:
		cfg.set_value("controls", key, b[key])
	var ok := cfg.save(PATH) == OK
	if ok:
		dirty = false
	else:
		push_warning("GameSettings: couldn't write %s" % PATH)
	return ok


func _changed() -> void:
	dirty = true
	if get_value("system", "auto_save"):
		save()


func _load() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(PATH) != OK:
		return  # first run: defaults
	for section in DEFAULTS:
		for key in DEFAULTS[section]:
			if cfg.has_section_key(section, key):
				var v = cfg.get_value(section, key)
				if typeof(v) == typeof(DEFAULTS[section][key]):
					_values[section][key] = v
	if cfg.has_section("controls"):
		var b := {}
		for key in cfg.get_section_keys("controls"):
			b[key] = cfg.get_value("controls", key)
		Controls.import_bindings(b)


# --- Applying -------------------------------------------------------------------

func _apply(section: String, key: String) -> void:
	match section:
		"sound":
			_apply_sound()
		"display":
			_apply_display()


func _apply_sound() -> void:
	for key in BUSES:
		var bus := AudioServer.get_bus_index(BUSES[key])
		if bus < 0:
			continue
		var volume: float = get_value("sound", key) / 100.0
		var mute := volume <= 0.0
		if key == "announcer" and not get_value("sound", "announcements"):
			mute = true
		AudioServer.set_bus_mute(bus, mute)
		if not mute:
			AudioServer.set_bus_volume_db(bus, _base_db[key] + linear_to_db(volume))


func _apply_display() -> void:
	var mode: int = get_value("display", "window_mode")
	match mode:
		1:
			DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)
		2:
			DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_EXCLUSIVE_FULLSCREEN)
		_:
			if DisplayServer.window_get_mode() != DisplayServer.WINDOW_MODE_WINDOWED:
				DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
			var size := RESOLUTIONS[clampi(get_value("display", "resolution"), 0, RESOLUTIONS.size() - 1)]
			if DisplayServer.window_get_size() != size:
				DisplayServer.window_set_size(size)
				var screen := DisplayServer.window_get_current_screen()
				var area := DisplayServer.screen_get_usable_rect(screen)
				DisplayServer.window_set_position(area.position + (area.size - size) / 2)
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_ENABLED if get_value("display", "vsync")
		else DisplayServer.VSYNC_DISABLED)
	# Keep 16:9 = black bars on other window shapes. Off = stretch to fill.
	get_window().content_scale_aspect = (Window.CONTENT_SCALE_ASPECT_KEEP if get_value("display", "keep_aspect")
		else Window.CONTENT_SCALE_ASPECT_IGNORE)


## Window sizes that fit on this monitor (indices into RESOLUTIONS).
func resolution_choices() -> Array:
	var screen := DisplayServer.screen_get_size(DisplayServer.window_get_current_screen())
	var list := []
	for i in RESOLUTIONS.size():
		if i == 0 or (RESOLUTIONS[i].x <= screen.x and RESOLUTIONS[i].y <= screen.y):
			list.append(i)
	return list


## F11 / Alt+Enter (see Controls) goes through here so the Options screen agrees.
func toggle_fullscreen() -> void:
	set_value("display", "window_mode", 1 if get_value("display", "window_mode") == 0 else 0)


# --- Match rules ------------------------------------------------------------------

## Called by MatchSetup.start_match() just before a fight. `cfg` is
## data/match_settings.tres (a C# MatchSettings resource).
func apply_match_rules(cfg, mode: String) -> void:
	match mode:
		"Versus":
			cfg.RoundsToWin = get_value("game", "rounds_versus")
			cfg.TimeLimit = get_value("game", "time_versus")
		"Online":
			# Netsu (Oct 26, TamaDeez): online has its own rounds setting (first to 2 by default), not Versus's
			cfg.RoundsToWin = get_value("game", "rounds_online")
			cfg.TimeLimit = get_value("game", "time_versus")
		"Arcade":
			cfg.RoundsToWin = get_value("game", "rounds_arcade")
			cfg.TimeLimit = get_value("game", "time_arcade")
		_:
			cfg.RoundsToWin = 1
			cfg.TimeLimit = -1   # training: no clock
	cfg.Difficulty = get_value("game", "difficulty")
	if mode in ["Versus", "Arcade", "Online"]:
		var mode_settings = cfg.GameModes[cfg.SelectedMode]
		mode_settings.ShowMatchIntro = get_value("game", "intros")
