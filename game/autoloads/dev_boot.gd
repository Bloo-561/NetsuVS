extends Node
## DEV BOOT (Nov 11, autoload - reach it from anywhere as "DevBoot")
##
## Makes every scene runnable on its own. Open any screen (battle, VS screen, stage select, character
## select...) and press F6 ("Run Current Scene"): before that scene starts, this fills in the test match
## from data/dev_fixtures.tres, the same way the screens before it would have (MatchSetup.pending for the
## stage select, data/match_settings.tres for the VS screen and the battle, mode / assists / music for the rest).
##
## It does NOTHING when:
##   - the game is started normally (F5, or the exported game): the launched scene is the main scene;
##   - it's a release build;
##   - data/dev_fixtures.tres has "enabled" off.
## Godot starts every autoload before the scene, and this one is listed last in project.godot, so the
## other autoloads (MatchSetup, GameSettings...) are ready when it runs, and the scene isn't yet.
##
## The online lobby run on its own gets a fake room with bots instead: DevNet, game/systems/dev/fake_online.gd.

const FIXTURES := "res://data/dev_fixtures.tres"

## True when the current run started on a scene other than the main scene (F6) and the test match was filled in.
var launched_alone := false
## The scene that was launched ("" = the main scene / a normal start).
var launched_scene := ""


func _ready() -> void:
	if not OS.is_debug_build():
		return
	launched_scene = _scene_from_command_line()
	var main_scene := str(ProjectSettings.get_setting("application/run/main_scene", ""))
	if launched_scene == "" or _same_scene(launched_scene, main_scene):
		launched_scene = ""
		return
	if not ResourceLoader.exists(FIXTURES):
		push_warning("DevBoot: %s is missing, so %s runs without a test match." % [FIXTURES, launched_scene])
		return
	var fx = load(FIXTURES)
	if fx == null or not fx.enabled:
		return
	launched_alone = true
	_apply(fx)


## F6 and "godot --path . res://scenes/x.tscn" both pass the scene on the command line
## (newer editors as "--scene res://..."): the first argument that's a scene file.
func _scene_from_command_line() -> String:
	for arg in OS.get_cmdline_args():
		var a := str(arg)
		if a.ends_with(".tscn") or a.ends_with(".scn"):
			return a
	return ""


func _same_scene(a: String, b: String) -> bool:
	if a == b:
		return true
	# the main scene can be stored as a uid://...; compare real paths
	return _path(a) == _path(b)


func _path(p: String) -> String:
	if p.begins_with("uid://"):
		var id := ResourceUID.text_to_id(p)
		if ResourceUID.has_id(id):
			return ResourceUID.get_id_path(id)
	return p


func _apply(fx) -> void:
	var ms := get_node_or_null("/root/MatchSetup")
	if ms == null:
		push_warning("DevBoot: no MatchSetup autoload, nothing filled in.")
		return
	var count: int = ms.fighter_count()
	if count == 0:
		push_warning("DevBoot: no fighters loaded (build the C# project first), nothing filled in.")
		return
	var training: bool = fx.mode == "Training"
	var p1 := clampi(int(fx.p1_fighter), 0, count - 1)
	var p2 := clampi(int(fx.p2_fighter), 0, count - 1)
	var stage := clampi(int(fx.stage), 0, maxi(ms.stage_count() - 1, 0))
	var p2_device := 1 if (fx.p2_is_human and not training) else -1
	# what the main menu / side select / character select / stage select would have set
	ms.mode_name = fx.mode
	ms.humans = [] if training else [true, p2_device >= 0]
	ms.assist_picks = [int(fx.p1_assist), int(fx.p2_assist)]
	ms.music_choice = int(fx.music)
	ms.last_stage = stage
	ms.pending = {"p1": p1, "p2": p2, "d1": 0, "d2": p2_device, "c1": int(fx.p1_color), "c2": int(fx.p2_color),
		"a1": int(fx.p1_assist), "a2": int(fx.p2_assist)}
	# what start_match() writes for the VS screen and the battle (same code, no screen change)
	ms.fill_match_settings(p1, p2, 0, p2_device, stage, int(fx.p1_color), int(fx.p2_color),
		int(fx.p1_assist), int(fx.p2_assist))
	var stage_text: String = ms.stage_name(stage) if ms.stage_count() > 0 else "(no stage list)"
	print("[DevBoot] %s on its own: %s, %s vs %s, %s." % [launched_scene.get_file(), fx.mode,
		ms.fighter_profile(p1).ShortName, ms.fighter_profile(p2).ShortName, stage_text])
