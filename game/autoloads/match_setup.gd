extends Node
## MATCH SETUP (autoload - reach it from anywhere as "MatchSetup")
##
## The bridge between our menus (GDScript) and the fight engine (C#).
## The engine reads everything about the next match from ONE resource:
## data/match_settings.tres. Menus fill it in through this script, then
## call start_match().
##
##   MatchSetup.mode_name = "Training"      # set by the main menu
##   MatchSetup.start_match(0, 1)           # P1 = fighter 0, P2 = fighter 1
##
## Fighters are listed in data/roster.tres, stages in data/stage_list.tres,
## assists (S / 6+S support characters) in data/assist_list.tres.
## (Resources are loaded on first use, so the menus still open even if the
## C# side hasn't been built yet.)

const BATTLE_SCENE := "res://scenes/battle/battle.tscn"
## The pre-fight screen (Oct 24): shows both fighters and the stage while the fight loads.
const VS_SCREEN := "res://scenes/vs_screen/vs_screen.tscn"
## Modes that get the VS screen before the fight (Training goes straight in).
const VS_SCREEN_MODES := ["Versus", "Arcade", "Online", "Training"]
const MATCH_SETTINGS := "res://data/match_settings.tres"
const ROSTER := "res://data/roster.tres"
const STAGES := "res://data/stage_list.tres"
const STAGE_SELECT_SCENE := "res://scenes/stage_select/stage_select.tscn"
const SOUNDTRACK := "res://data/soundtrack.tres"

## Battle music choice from the stage select: MUSIC_AUTO, MUSIC_RANDOM or a song index.
const MUSIC_AUTO := -2
const MUSIC_RANDOM := -1

## Stage used for each mode when nobody picks one (index into stage_list.tres).
const DEFAULT_STAGE := {"Training": 0, "Versus": 1}

## Which engine game mode the character select is picking for.
## Must match a ModeName in data/game_modes/ ("Training", "Versus", ...).
var mode_name := "Training"

# Untyped on purpose: these are C# resources, so GDScript can't check their fields.
var _settings
var _roster
var _stages

## Fighters picked on the character select, waiting for a stage (see choose_stage).
var pending := {}
## Last stage picked on the stage select (-1 = none yet), so the cursor starts there.
var last_stage := -1

## Versus side select result: [side 1 is a person, side 2 is a person].
## Empty = no side select happened (Training): player 2 joins by pressing A.
var humans: Array = []

## Battle music picked on the stage select (kept for the next match).
var music_choice := MUSIC_AUTO
var _soundtrack


func settings():
	if _settings == null:
		_settings = load(MATCH_SETTINGS)
	return _settings


func roster():
	if _roster == null:
		_roster = load(ROSTER)
	return _roster


func fighter_count() -> int:
	var list = roster()
	return list.elements.size() if list else 0


## The FighterProfile for a roster slot: FighterName, ShortName, Render,
## Portrait, VictoryRender, Bio...
func fighter_profile(index: int):
	return roster().elements[index].Profile


## The colour of a side's EX / super presentation in the current fight: the fighter's
## FighterProfile.NetsuAuraColor, or the side's colour (Player 1 blue, Player 2 red) when it has none.
## The engine's aura (SakugaActor.NetsuAuraColor) uses the same rule.
func side_color(side: int) -> Color:
	var fallback := Color(0.3, 0.62, 1.0) if side == 0 else Color(1.0, 0.25, 0.38)
	var cfg = settings()
	if cfg == null:
		return fallback
	var index := int(cfg.P1SelectedCharacter if side == 0 else cfg.P2SelectedCharacter)
	if index < 0 or index >= fighter_count():
		return fallback
	var c = fighter_profile(index).get("NetsuAuraColor")
	return c if c is Color and c.a > 0.01 else fallback


## Number of color palettes a fighter has.
func palette_count(index: int) -> int:
	return roster().elements[index].ColorPalettes.size()


func _find_mode(wanted: String) -> int:
	var modes = settings().GameModes
	for i in modes.size():
		if modes[i].ModeName == wanted:
			return i
	push_warning("MatchSetup: no game mode named '%s', using the first one." % wanted)
	return 0


## Fills in data/match_settings.tres and loads the battle.
##   p1_device / p2_device: 0 = player 1's controls, 1 = player 2's controls,
##                          -1 = CPU (or the training dummy).
##   p1_assist / p2_assist: index in data/assist_list.tres, -2 = the last one picked
##                          (assist_picks). Everyone has an assist: -1 becomes the first one.
func start_match(p1_fighter: int, p2_fighter: int, p1_device: int = 0, p2_device: int = -1,
		stage: int = -1, p1_color: int = -1, p2_color: int = -1, p1_assist: int = -2, p2_assist: int = -2) -> void:
	var cfg = settings()
	if "P1SelectedAssist" in cfg:   # (only after the C# project is built)
		cfg.P1SelectedAssist = _valid_assist(assist_picks[0] if p1_assist == -2 else p1_assist)
		cfg.P2SelectedAssist = _valid_assist(assist_picks[1] if p2_assist == -2 else p2_assist)
	cfg.SelectedMode = _find_mode(mode_name)
	cfg.P1SelectedCharacter = p1_fighter
	cfg.P1SelectedColor = maxi(p1_color, 0)
	cfg.P1SelectedDevice = p1_device
	cfg.P2SelectedCharacter = p2_fighter
	# Mirror match: give player 2 the alternate colors so you can tell them apart.
	if p2_color >= 0:
		cfg.P2SelectedColor = p2_color   # (the engine still bumps it if both picked the same look)
	else:
		cfg.P2SelectedColor = 1 if p2_fighter == p1_fighter and palette_count(p2_fighter) > 1 else 0
	cfg.P2SelectedDevice = p2_device
	cfg.SelectedStage = stage if stage >= 0 else DEFAULT_STAGE.get(mode_name, 0)
	cfg.SelectedBGM = resolve_music(music_choice, p1_fighter)
	prepare_music()
	# rounds, round time, CPU difficulty and intros from the Options screen
	var options := get_node_or_null("/root/GameSettings")
	if options:
		options.apply_match_rules(cfg, mode_name)
	if mode_name == "Online" and not online_rules.is_empty():
		# both computers must run the same fight: the host's rules win (start_online)
		cfg.RoundsToWin = int(online_rules.get("rounds", cfg.RoundsToWin))
		cfg.TimeLimit = int(online_rules.get("time", cfg.TimeLimit))
		cfg.GameModes[cfg.SelectedMode].ShowMatchIntro = bool(online_rules.get("intros", true))
	bg_release(_match_paths)
	_match_paths = []
	if mode_name in VS_SCREEN_MODES and ResourceLoader.exists(VS_SCREEN):
		SceneRouter.go_to(VS_SCREEN)   # it loads the fight while it plays, then calls enter_battle()
	else:
		await SceneRouter.go_to(BATTLE_SCENE)
		release_match_preload()   # the fight is built: let go of what was kept loaded for it


## Name of a fighter's colour ("Crimson", "Azure"...).
func palette_name(fighter: int, color: int) -> String:
	var pal = roster().elements[fighter].ColorPalettes[color]
	return str(pal.PaletteName)


## The fighter scene for one colour (actors/<fighter>/Instances/..._SkinXX.tscn). Loaded on demand from
## the colour's ScenePath (Oct 24: the roster no longer loads every fighter's scene up front).
func palette_scene(fighter: int, color: int) -> PackedScene:
	var pal = roster().elements[fighter].ColorPalettes[color]
	if pal.get("Instance") != null:
		return pal.Instance
	var path := palette_scene_path(fighter, color)
	return (load(path) as PackedScene) if path != "" and ResourceLoader.exists(path) else null


## Path of the fighter scene for one colour ("" if the roster entry has none).
func palette_scene_path(fighter: int, color: int) -> String:
	var pal = roster().elements[fighter].ColorPalettes[color]
	var inst = pal.get("Instance")
	if inst != null:
		return str(inst.resource_path)
	var path = pal.get("ScenePath")
	return "" if path == null else str(path)


## Path of a stage's scene ("" if none).
func stage_scene_path(index: int) -> String:
	if index < 0 or index >= stage_count():
		return ""
	var e = stages().elements[index]
	var inst = e.get("Instance")
	if inst != null:
		return str(inst.resource_path)
	var path = e.get("ScenePath")
	return "" if path == null else str(path)


## The colour a side really fights in: GameManager.CreateFighter gives player 2 the next colour when
## both players picked the same fighter in the same colour.
func engine_color(side: int) -> int:
	var cfg = settings()
	var c1 := int(cfg.P1SelectedColor)
	if side == 0:
		return c1
	var f2 := int(cfg.P2SelectedCharacter)
	var c2 := int(cfg.P2SelectedColor)
	if f2 == int(cfg.P1SelectedCharacter) and c2 == c1:
		c2 += 1
	if c2 >= palette_count(f2):
		c2 = 0
	return c2


# --- VS screen ------------------------------------------------------------------
# scenes/vs_screen/vs_screen.gd shows the match set up by start_match() and loads it meanwhile.

## Everything the VS screen shows about the fight that's been set up (data/match_settings.tres):
##   {"mode", "sides": [{"name", "full_name", "render", "player", "cpu", "assist", "assist_icon",
##    "color"} x2], "stage", "stage_thumb", "song", "artist", "rounds", "time"}
func versus_info() -> Dictionary:
	var cfg = settings()
	var sides: Array = []
	for side in 2:
		var f := int(cfg.P1SelectedCharacter if side == 0 else cfg.P2SelectedCharacter)
		var device := int(cfg.P1SelectedDevice if side == 0 else cfg.P2SelectedDevice)
		var p = fighter_profile(f)
		var a := assist_for_side(side)
		var color := engine_color(side)
		sides.append({"name": _text(p.ShortName), "full_name": _text(p.FighterName), "render": p.Render,
			"player": _side_label(side, device), "cpu": device < 0,
			"assist": assist_name(a) if a >= 0 else "", "assist_icon": assist_icon(a) if a >= 0 else null,
			"color": palette_name(f, color) if color < palette_count(f) else ""})
	var stage := int(cfg.SelectedStage)
	var has_stage := stage >= 0 and stage < stage_count()
	var song := song_info(int(cfg.SelectedBGM)) if int(cfg.SelectedBGM) < song_count() else {}
	return {"mode": mode_name, "sides": sides,
		"stage": stage_name(stage) if has_stage else "", "stage_thumb": stage_thumbnail(stage) if has_stage else null,
		"song": song.get("title", ""), "artist": song.get("artist", ""),
		"rounds": int(cfg.RoundsToWin) if "RoundsToWin" in cfg else 0, "time": int(cfg.TimeLimit) if "TimeLimit" in cfg else -1}


## The fight that's set up: "PLAYER 1", "PLAYER 2", "CPU"... for that side (the win screen; same as the VS screen).
func side_label(side: int) -> String:
	var cfg = settings()
	return _side_label(side, int(cfg.P1SelectedDevice if side == 0 else cfg.P2SelectedDevice))


## "PLAYER 1", "PLAYER 2", "CPU", or in Training "TRAINING DUMMY" for a side nobody plays. Online: the player's
## lobby name.
func _side_label(side: int, device: int) -> String:
	if mode_name == "Online":
		var online_name := online_player_name(side)
		if online_name != "":
			return online_name.to_upper()
	if device >= 0:
		return "PLAYER %d" % (side + 1)
	return "TRAINING DUMMY" if mode_name == "Training" else "CPU"


## Online: the lobby name of the player on that side ("" when not online).
func online_player_name(side: int) -> String:
	var cfg = settings()
	if mode_name != "Online" or not "OnlineP1Name" in cfg:
		return ""
	var n = cfg.OnlineP1Name if side == 0 else cfg.OnlineP2Name
	return "" if n == null else str(n)


## What the next fight needs loaded: the battle scene, the stage and both fighters' colour scenes.
func match_paths() -> Array:
	var cfg = settings()
	var out: Array = [BATTLE_SCENE]
	var stage_path := stage_scene_path(int(cfg.SelectedStage))
	if stage_path != "":
		out.append(stage_path)
	for side in 2:
		var f := int(cfg.P1SelectedCharacter if side == 0 else cfg.P2SelectedCharacter)
		var color := engine_color(side)
		if f < 0 or f >= fighter_count() or color >= palette_count(f):
			continue
		var path := palette_scene_path(f, color)
		if path != "" and not path in out:
			out.append(path)
	# Oct 25: the EX / super cut-in pictures and sounds too (game/ui/battle_hud/netsu_cut_in.gd): loaded at the
	# first EX move they stalled the fight for a moment
	for side in 2:
		var f2 := int(cfg.P1SelectedCharacter if side == 0 else cfg.P2SelectedCharacter)
		if f2 < 0 or f2 >= fighter_count():
			continue
		var folder := str(fighter_profile(f2).ShortName).to_lower()
		for pic in ["CutIn_EX.png", "CutIn_Super.png"]:
			var art := "res://actors/%s/Artwork/%s" % [folder, pic]
			if ResourceLoader.exists(art) and not art in out:
				out.append(art)
	for sfx in ["res://assets/audio/sfx/netsu_ex_flash.wav", "res://assets/audio/sfx/netsu_super_flash.wav"]:
		if ResourceLoader.exists(sfx) and not sfx in out:
			out.append(sfx)
	return out


var _match_paths: Array = []

## Starts loading the fight start_match() set up, on other threads (the VS screen calls this).
func preload_match() -> void:
	bg_release(_match_paths)
	_match_paths = match_paths()
	for path in _match_paths:
		bg_load(path)


## 0..1: how much of the fight is loaded (1 = ready to go).
func preload_progress() -> float:
	return bg_progress(_match_paths)


## Fades from the VS screen into the fight, using what preload_match() loaded (anything that isn't
## loaded yet loads the usual way). The loaded scenes are let go once the fight has been built.
func enter_battle(fade_out: float = 0.35, fade_in: float = 0.5) -> void:
	while SceneRouter.is_busy():
		await get_tree().process_frame
	var battle = bg_get(BATTLE_SCENE)
	await SceneRouter.fade_to(battle if battle is PackedScene else BATTLE_SCENE, Color.BLACK, fade_out, fade_in)
	release_match_preload()


## Lets go of the fight's scenes (and the fighters the character select kept warm) once it's built.
func release_match_preload() -> void:
	bg_release(_match_paths + _warm)
	_match_paths = []
	_warm = []


var _warm: Array = []

## Keeps these background loads (bg_load) until the next fight has been built: the character select
## keeps the two picked fighters loaded while the stage select is open.
func keep_warm(paths: Array) -> void:
	for path in paths:
		if not path in _warm:
			_warm.append(path)


# --- Background loading ----------------------------------------------------------
# Loads resources on other threads so screens keep animating (the VS screen loads the fight, the
# character select warms up every fighter). A finished load is kept here until bg_release().
# Oct 24 night: ONE load at a time (the others wait in _bg_queue). Several threaded loads at once that share
# files (both fighters use the shared inputs, sounds, effects, hitbox templates) sometimes failed in Godot 4.7
# with "Parse Error" in a random fighter file, and the fight then never started.

var _bg := {}   # path -> {"res": Resource or null, "done": bool, "keep": bool, "queued": bool}
var _bg_queue: Array = []   # paths waiting for their turn
var _bg_active := ""        # the path loading right now


func _ready() -> void:
	set_process(false)
	_connect_online.call_deferred()   # after every autoload is in the tree


func _connect_online() -> void:
	var online := get_node_or_null("/root/NetsuOnline")
	if online and online.has_signal("Disconnected") and not online.is_connected("Disconnected", _on_online_disconnected):
		online.connect("Disconnected", _on_online_disconnected)


# --- Online (Oct 24; group lobbies Oct 25) ----------------------------------------------
# The online lobby (scenes/online/online_lobby.gd; its rules: the OnlineRoom autoload, game/autoloads/online_room.gd;
# the connections: the NetsuOnline autoload, C#) starts fights with start_online_room(). The match's two players
# run the same fight with rollback, each reading its OWN player-1 controls for its side; everyone else in the
# lobby watches it (the inputs come from player 1's computer, through the host). The host's rules (rounds, round
# time, intros) are used everywhere. After the fight everyone goes back to the lobby (OnlineRoom does that).
const ONLINE_LOBBY := "res://scenes/online/online_lobby.tscn"
var online_rules := {}      # {"rounds", "time", "intros"} from the host
var online_notice := ""     # shown by the lobby when it opens (the opponent left during a fight...)


## p: {"f1", "c1", "a1", "f2", "c2", "a2", "stage", "rules": {...}, "n1", "n2"} (fighter, colour, assist for each
## side, the players' names). side: 0 / 1 = this computer plays that side, -1 = it watches.
func start_online_room(p: Dictionary, side: int) -> void:
	mode_name = "Online"
	humans = [true, true]
	online_rules = p.get("rules", {})
	var cfg = settings()
	if "PlayerID" in cfg:
		cfg.PlayerID = maxi(side, 0)
		cfg.IsSpectator = side < 0
		cfg.SpectatorCount = 0
	if "OnlineP1Name" in cfg:
		cfg.OnlineP1Name = str(p.get("n1", "Player 1"))
		cfg.OnlineP2Name = str(p.get("n2", "Player 2"))
	var controls := get_node_or_null("/root/Controls")
	if controls and controls.has_method("clear_sides"):
		controls.clear_sides()   # keyboard 1 and controller 1 both drive this computer's player
	assist_picks = [int(p.get("a1", 0)), int(p.get("a2", 0))]
	music_choice = MUSIC_AUTO
	start_match(int(p.get("f1", 0)), int(p.get("f2", 0)), 0, 1, int(p.get("stage", 0)),
		int(p.get("c1", 0)), int(p.get("c2", 0)), int(p.get("a1", 0)), int(p.get("a2", 0)))


## The 1-on-1 version (before group lobbies): the host plays player 1.
func start_online(host: bool, p: Dictionary) -> void:
	start_online_room(p, 0 if host else 1)


func _on_online_disconnected(reason: String) -> void:
	if mode_name != "Online":
		return
	var scene := get_tree().current_scene
	var path: String = scene.scene_file_path if scene else ""
	if path == ONLINE_LOBBY or path == "":
		return   # the lobby shows it itself
	online_notice = reason
	SceneRouter.go_to(ONLINE_LOBBY)


## Starts loading `path` in the background (does nothing if it's already loading or loaded here).
## urgent: ahead of everything else waiting (SceneRouter's next scene).
func bg_load(path: String, urgent: bool = false) -> void:
	if path == "" or not ResourceLoader.exists(path):
		return
	if _bg.has(path):
		_bg[path]["keep"] = true
		if urgent and _bg[path].get("queued", false):
			_bg_queue.erase(path)
			_bg_queue.push_front(path)
		return
	_bg[path] = {"res": null, "done": false, "keep": true, "queued": true}
	if urgent:
		_bg_queue.push_front(path)
	else:
		_bg_queue.append(path)
	_bg_pump()
	set_process(true)


## Starts the next queued background load when none is running.
func _bg_pump() -> void:
	while _bg_active == "" and not _bg_queue.is_empty():
		var p: String = _bg_queue.pop_front()
		if not _bg.has(p):
			continue
		_bg[p]["queued"] = false
		if ResourceLoader.load_threaded_request(p) != OK:
			_bg[p]["done"] = true   # couldn't start: it loads the normal way when it's needed
			if not _bg[p]["keep"]:
				_bg.erase(p)
			continue
		_bg_active = p


## 0..1 for these paths together (1 = all loaded). Paths that aren't loading here count as loaded.
func bg_progress(paths: Array) -> float:
	if paths.is_empty():
		return 1.0
	var total := 0.0
	for path in paths:
		total += _bg_collect(path)
	return total / paths.size()


## The loaded resource, or null while it's still loading (or if it failed / was never asked for).
func bg_get(path: String) -> Resource:
	if not _bg.has(path) or _bg_collect(path) < 1.0 or not _bg.has(path):
		return null
	return _bg[path]["res"]


## Stops holding these. Loads still running are picked up and dropped when they finish.
func bg_release(paths: Array) -> void:
	for path in paths:
		if not _bg.has(path):
			continue
		if _bg[path]["done"] or _bg[path].get("queued", false):
			_bg.erase(path)   # finished, or never started (the queue skips it)
			_bg_queue.erase(path)
		else:
			_bg[path]["keep"] = false
			set_process(true)


## Progress of one background load (0..1); picks the resource up as soon as it's in.
func _bg_collect(path: String) -> float:
	if not _bg.has(path):
		return 1.0
	var e: Dictionary = _bg[path]
	if e["done"]:
		return 1.0
	if e.get("queued", false):
		_bg_pump()
		if e.get("queued", false):
			return 0.0   # still waiting for its turn
	var progress: Array = []
	var status := ResourceLoader.load_threaded_get_status(path, progress)
	if status == ResourceLoader.THREAD_LOAD_IN_PROGRESS:
		return float(progress[0]) if progress.size() > 0 else 0.0
	if status == ResourceLoader.THREAD_LOAD_LOADED:
		e["res"] = ResourceLoader.load_threaded_get(path)
	else:
		push_warning("MatchSetup: background load of %s failed; it will load the normal way." % path)
	e["done"] = true
	if not e["keep"]:
		_bg.erase(path)
	if _bg_active == path:
		_bg_active = ""
		_bg_pump()
	return 1.0


func _process(_delta: float) -> void:
	if _bg_active != "":
		_bg_collect(_bg_active)   # moves the queue on even when nobody is asking for progress
	_bg_pump()
	var waiting := _bg_active != "" or not _bg_queue.is_empty()
	for path in _bg.keys():
		if not _bg[path]["keep"] and not _bg[path]["done"]:
			_bg_collect(path)
			waiting = waiting or _bg.has(path)
	if not waiting:
		set_process(false)


# --- Training ----------------------------------------------------------------
# The Training Menu (game/ui/training/netsu_training_menu.gd) stores its settings in GameSettings'
# "training" section; the fight's training controller (netsu_training_hud.gd) sends them to the
# engine (GameManager.NetsuSetTraining -> engine/sakuga/Game/NetsuTraining.cs).

## The Training Menu's settings as one Dictionary for the engine.
func training_options() -> Dictionary:
	var out := {}
	var gs := get_node_or_null("/root/GameSettings")
	if gs:
		for key in gs.DEFAULTS["training"]:
			out[key] = gs.get_value("training", key)
	return out


# --- Stages ------------------------------------------------------------------

func stages():
	if _stages == null:
		_stages = load(STAGES)
	return _stages


func stage_count() -> int:
	var list = stages()
	return list.elements.size() if list else 0


func stage_name(index: int) -> String:
	return str(stages().elements[index].Name)


func stage_thumbnail(index: int) -> Texture2D:
	return stages().elements[index].Thumbnail


## Stage the current mode uses when nobody picks one.
func default_stage() -> int:
	return DEFAULT_STAGE.get(mode_name, 0)


## Called by the character select: remember the picks and open the stage select.
func choose_stage(p1_fighter: int, p2_fighter: int, p1_device: int = 0, p2_device: int = -1,
		p1_color: int = -1, p2_color: int = -1, p1_assist: int = -2, p2_assist: int = -2) -> void:
	pending = {"p1": p1_fighter, "p2": p2_fighter, "d1": p1_device, "d2": p2_device, "c1": p1_color, "c2": p2_color,
		"a1": p1_assist, "a2": p2_assist}
	SceneRouter.go_to(STAGE_SELECT_SCENE)


## Called by the stage select: start the fight with the remembered picks.
func start_pending(stage: int) -> void:
	start_match(pending.get("p1", 0), pending.get("p2", 0), pending.get("d1", 0), pending.get("d2", -1), stage,
		pending.get("c1", -1), pending.get("c2", -1), pending.get("a1", -2), pending.get("a2", -2))


## "CECILIA  VS  SILVERWING" for the stage select header.
func pending_matchup_text() -> String:
	if pending.is_empty():
		return ""
	var a = fighter_profile(pending.get("p1", 0))
	var b = fighter_profile(pending.get("p2", 0))
	return "%s  VS  %s" % [str(a.ShortName).to_upper(), str(b.ShortName).to_upper()]


# --- Music -------------------------------------------------------------------
# Songs live in data/soundtrack.tres (SongName, Artist, Source, Character, LoopStart).
# A fighter's own theme is the song at their Profile.AutoBGM index.

func soundtrack():
	if _soundtrack == null and ResourceLoader.exists(SOUNDTRACK):
		_soundtrack = load(SOUNDTRACK)
	return _soundtrack


func song_count() -> int:
	var list = soundtrack()
	return list.elements.size() if list and list.elements else 0


## {"title", "artist", "source", "fighter" (roster index or -1), "clip"} for one song.
func song_info(index: int) -> Dictionary:
	var e = soundtrack().elements[index]
	var fighter := -1
	var who := _text(e.get("Character"))
	for i in fighter_count():
		var p = fighter_profile(i)
		if who != "" and (who == str(p.ShortName) or who == str(p.FighterName)):
			fighter = i
			break
		if who == "" and int(p.AutoBGM) == index:
			fighter = i
	return {"title": _text(e.get("SongName")), "artist": _text(e.get("Artist")),
		"source": _text(e.get("Source")), "fighter": fighter, "clip": e.get("clip")}


## A fighter's own theme (their Profile.AutoBGM), clamped to the soundtrack.
func theme_for(fighter: int) -> int:
	var n := song_count()
	if n == 0:
		return 0
	var i := int(fighter_profile(fighter).AutoBGM) if fighter >= 0 and fighter < fighter_count() else 0
	return clampi(i, 0, n - 1)


## Turns a stage select choice (MUSIC_AUTO / MUSIC_RANDOM / index) into a song index.
func resolve_music(choice: int, p1_fighter: int) -> int:
	var n := song_count()
	if n == 0:
		return 0
	if choice == MUSIC_RANDOM:
		return randi() % n
	if choice >= 0 and choice < n:
		return choice
	return theme_for(p1_fighter)


## OGG / MP3 songs don't loop unless told to: switch looping on (jumping back to
## LoopStart) for every song. Kept loaded here so the battle gets the same copies.
func prepare_music() -> void:
	var list = soundtrack()
	if list == null or list.elements == null:
		return
	for e in list.elements:
		var clip = e.get("clip")
		if clip is AudioStreamOggVorbis or clip is AudioStreamMP3:
			clip.loop = true
			var start = e.get("LoopStart")
			clip.loop_offset = float(start) if start != null else 0.0


func _text(v) -> String:
	return "" if v == null else str(v)


## EX moves (1 bar) and supers (3 bars) call this from the engine
## (StanceManager.ExecuteMove) as they start; the battle HUD's cut-in
## (game/ui/battle_hud/netsu_cut_in.gd) listens to the signal.
signal cut_in(side: int, fighter: String, move_name: String, is_super: bool, from_left: bool)

func netsu_cut_in(side: int, fighter: String, move_name: String, is_super: bool, from_left: bool) -> void:
	cut_in.emit(side, fighter, move_name, is_super, from_left)


## The engine calls this as an EX move (cost 10000) or super (30000) freezes the opponent
## (SakugaActor.NetsuSuperFlashLook), and for an Assist Cancel (cost -1). pos = the fighter's chest
## in the 3D world, frames = how long the freeze lasts. game/ui/battle_hud/netsu_super_flash.gd
## listens: it dims the stage and draws the burst of light.
signal super_flash(side: int, pos: Vector3, cost: int, frames: int)

func netsu_super_flash(side: int, pos: Vector3, cost: int, frames: int) -> void:
	super_flash.emit(side, pos, cost, frames)


## The engine calls this when a fighter's super starts (on = true: from its flash) and when she is out of the
## attack again (on = false). netsu_cut_in.gd keeps the super's dark backdrop up in between.
signal super_hold(side: int, on: bool)

func netsu_super_hold(side: int, on: bool) -> void:
	super_hold.emit(side, on)


# --- Assists -----------------------------------------------------------------
# Support characters called in a fight with S (5S) and forward + S (6S), in the
# style of Dengeki Bunko Fighting Climax. The engine side is
# engine/sakuga/Components/NetsuAssist.cs; the list (names, moves, cooldowns,
# where they appear) is data/assist_list.tres, made by tools/sprite_port/assists.py.

const ASSISTS := "res://data/assist_list.tres"
## Craft Gauge bars an Assist Cancel costs (NetsuAssist.AssistCancelCost = 10000 = 1 of 4 bars; 2 before Oct 26).
const ASSIST_CANCEL_BARS := 1
var _assists

## The assist each player picked last (index in data/assist_list.tres). There is no "none":
## every fighter has an assist (the engine also turns -1 into the first one).
## The character select changes it; start_match() uses it when it isn't told otherwise.
var assist_picks: Array = [0, 2]


func assists():
	if _assists == null and ResourceLoader.exists(ASSISTS):
		_assists = load(ASSISTS)
	return _assists


func assist_count() -> int:
	var list = assists()
	if list == null or list.get("Assists") == null:
		return 0
	return list.Assists.size()


## index if it's a real assist, else 0 (the first one).
func _valid_assist(index: int) -> int:
	return index if index >= 0 and index < assist_count() else 0


func assist_name(index: int) -> String:
	if index < 0 or index >= assist_count():
		return "None"
	return str(assists().Assists[index].AssistName)


func assist_icon(index: int) -> Texture2D:
	if index < 0 or index >= assist_count():
		return null
	return assists().Assists[index].Icon


## [{"name": "5S", "display": "Encore", "input": "S", "text": "..."}] for one assist.
func assist_moves(index: int) -> Array:
	var out: Array = []
	if index < 0 or index >= assist_count():
		return out
	var inputs := {0: "S", 1: "6 + S", 2: "4 + S"}
	for mv in assists().Assists[index].Moves:
		if mv == null:
			continue
		out.append({"name": str(mv.MoveName), "display": str(mv.DisplayName), "input": inputs.get(int(mv.Direction), "S"),
			"text": str(mv.Description), "cooldown": int(mv.Cooldown)})
	return out


## Which assist a side has in the match being set up / played (-1 = settings not built yet).
func assist_for_side(side: int) -> int:
	var cfg = settings()
	if cfg == null or not ("P1SelectedAssist" in cfg):
		return -1
	return int(cfg.P1SelectedAssist if side == 0 else cfg.P2SelectedAssist)


## A command list section for an assist (the pause menu adds it to the fighter's own list).
func assist_command_section(index: int) -> Dictionary:
	var moves := assist_moves(index)
	if moves.is_empty():
		return {}
	var rows: Array = []
	for m in moves:
		var secs := float(m["cooldown"]) / 60.0
		rows.append([m["display"] if m["display"] != "" else m["name"], m["input"],
			"%s (gauge refills in %.0f s)" % [m["text"], secs]])
	# how calling works (engine/sakuga/Components/NetsuAssist.cs)
	rows.append(["Calling from neutral", "S on the ground", "your fighter poses while the assist comes in (can't act or block); free in the air"])
	rows.append(["Assist Cancel", "S during your attack", "calls the assist at once, no pose; costs %d bar%s" % [ASSIST_CANCEL_BARS, "" if ASSIST_CANCEL_BARS == 1 else "s"]])
	return {"title": "Assist: " + assist_name(index), "moves": rows}


## The battle HUD's assist gauges. The engine (NetsuAssist.cs) reports both every
## frame; game/ui/battle_hud/netsu_hud.gd draws them.
##   phase: 0 ready, 1 on screen, 2 refilling.  ratio: gauge 0..1.  buff: buff time left 0..1.
var assist_hud: Array = [{}, {}]


## Oct 26 (TamaDeez): a fighter's stocked resource (Noah's energy from 214, his custom variable "Stock"). The engine
## (SakugaActor.NetsuStockHud) reports it when it changes; netsu_hud.gd draws a READY icon under the Burst gauge.
var stock_hud: Array = [{}, {}]
var star_hud: Array = [{}, {}]   # Oct 29: Flan's star stacks (netsu_star_hud)


## Oct 28: 1 while that side is in Overdrive (health under 35%), else 0. Was: Overdrive frames left.
## Oct 26 evening (TamaDeez): Overdrive frames left per side (0 = not in Overdrive). The engine
## (SakugaActor.NetsuOverdriveHud) reports it as it changes; netsu_hud.gd shows the timer next to the Burst
## gauge and netsu_super_flash.gd tints the stage a little darker while anyone's Overdrive runs.
var overdrive_hud: Array = [0, 0]


func netsu_overdrive_hud(side: int, frames: int) -> void:
	if side < 0 or side > 1:
		return
	overdrive_hud[side] = frames


func overdrive_running() -> bool:
	return int(overdrive_hud[0]) > 0 or int(overdrive_hud[1]) > 0


## Oct 26 c15 (TamaDeez): the juggle meter. The engine (SakugaActor.NetsuJuggleHud) reports, for the fighter being
## comboed (`side` = the VICTIM), whether a combo is running, hitstun frames left / given by the last hit, the juggle
## decay (0..1000), the air counter lock (no tech until landing), invalid combo and hard knockdown. netsu_hud.gd draws it
## under the attacker's combo counter.
var juggle_hud: Array = [{}, {}]


## Oct 26 c20: while they lie on the floor it also sends the OTG window: frames left to hit them there / the whole window.
func netsu_juggle_hud(side: int, active: bool, left: int, max_left: int, decay: int, locked: bool, invalid: bool, down: bool,
		lying: bool = false, otg_left: int = 0, otg_max: int = 0) -> void:
	if side < 0 or side > 1:
		return
	juggle_hud[side] = {"active": active, "left": left, "max": max_left, "decay": decay, "locked": locked,
		"invalid": invalid, "down": down, "lying": lying, "otg_left": otg_left, "otg_max": otg_max}


## Oct 29 (TamaDeez): Flan's star stacks (SakugaActor.NetsuStarHud): how many she holds and the most she can hold.
func netsu_star_hud(side: int, value: int, max_value: int) -> void:
	if side < 0 or side > 1:
		return
	star_hud[side] = {"value": value, "max": max_value, "msec": Time.get_ticks_msec()}


func netsu_stock_hud(side: int, value: int) -> void:
	if side < 0 or side > 1:
		return
	stock_hud[side] = {"value": value, "msec": Time.get_ticks_msec()}


func netsu_assist_hud(side: int, assist_name_text: String, ratio: float, phase: int, buff: float, icon, frames_left: int = -1) -> void:
	if side < 0 or side > 1:
		return
	# Oct 30: frames_left = frames until the assist is ready (countdown badge); -1 = not cooling down / older engine build
	assist_hud[side] = {"name": assist_name_text, "ratio": ratio, "phase": phase, "buff": buff, "icon": icon,
		"frames_left": frames_left, "msec": Time.get_ticks_msec()}
