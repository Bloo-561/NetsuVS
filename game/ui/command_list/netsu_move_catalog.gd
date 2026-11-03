class_name NetsuMoveCatalog
extends RefCounted
## COMMAND LIST DATA (Nov 2 2026)
##
## Builds the command list from the game's own data, so a new move, a renamed move, a changed input or new frame
## data shows up in the list by itself:
##   - a fighter's moves:  its DataContainer (actors/<fighter>/0_<TAG>_Data.tres) -> Stances[0].Moves (MoveSettings):
##     name, input (MotionInputs), cost, ground / air, follow-ups (SkipCheck + IsSequenceFromStates), the state it
##     plays (MoveState) -> FighterState.AnimationData: preview frames, startup / active / recovery, damage, guard.
##   - an assist's moves:  data/assist_list.tres (NetsuAssistElement.Moves) + the assist's own DataContainer.
##   - system topics:      data/command_list/system.json (written by hand; previews use the shown fighter's moves).
##
## Optional notes per fighter: actors/<fighter>/command_list.json, keyed by the ENGINE move name (MoveSettings.MoveName):
##   "moves": {"Teleport Slash": {"name": "Crescent Slash", "desc": "...", "input": "623 A|B", "tags": ["B: INVINCIBLE"],
##             "states": [82], "group": "Other Move Name", "hide": true, "section": "Specials", "data": {"ON BLOCK": "+3"}}}
##   "extra": [{"name": "...", "input": "...", "desc": "...", "section": "Specials", "after": "Command Dash", "states": [106]}]
## Every key is optional. A move with no notes still shows: its name, its input worked out from the data, its frame
## data and its animation; the description says it has none yet. Full guide: docs/command_list.md.

const BAR := 10000                 # StanceManager.NetsuBarSize (one bar of Craft Gauge since Oct 29)
const SUPER := 30000               # StanceManager.NetsuSuperCost
const SECTIONS := ["Normals", "Specials", "Supers", "Universal"]
const SYSTEM_FILE := "res://data/command_list/system.json"
const ASSIST_NOTES_FILE := "res://data/command_list/assists.json"
const NO_DESC := "No description yet. Add one in this fighter's command_list.json."

## DirectionalInputs bits -> numpad digit (facing right). ButtonInputs bits -> button letter.
const DIR := {1: "2", 2: "4", 4: "6", 8: "8", 3: "1", 5: "3", 10: "7", 12: "9"}
const BTN := [[1, "A"], [2, "B"], [4, "C"], [8, "S"]]

## HitboxType / HitType (engine/sakuga/Globals).
const HB_HURT := 0
const HB_HIT := 1
const HB_PROJECTILE := 3
const HB_THROW := 4
const HB_COUNTER := 5
const GUARD_NAMES := ["HIGH", "MID", "LOW", "UNBLOCKABLE"]

static var _data_cache := {}       # path -> DataContainer
static var _notes_cache := {}      # path -> Dictionary


# --- Finding things ------------------------------------------------------------------------

static func _g(o, key: String, fallback = null):
	if o == null:
		return fallback
	var v = o.get(key)
	return fallback if v == null else v


static func list_dir(dir: String) -> PackedStringArray:
	var out := PackedStringArray()
	if ResourceLoader.has_method("list_directory"):
		for f in ResourceLoader.call("list_directory", dir):
			out.append(str(f))
		return out
	var d := DirAccess.open(dir)
	if d == null:
		return out
	for f in d.get_files():
		out.append(f.trim_suffix(".remap"))
	return out


## The actor folder (res://actors/cecilia) of a roster slot, from its first colour's scene path.
static func fighter_dir(index: int) -> String:
	if index < 0 or index >= MatchSetup.fighter_count():
		return ""
	var path := MatchSetup.palette_scene_path(index, 0)
	return path.get_base_dir().get_base_dir() if path != "" else ""


## The 0_<TAG>_Data.tres in a folder (the shortest name when there are several, e.g. Mary and her note).
static func data_path_in(dir: String) -> String:
	var best := ""
	for f in list_dir(dir):
		if f.begins_with("0_") and f.ends_with("_Data.tres") and (best == "" or f.length() < best.length()):
			best = f
	return dir.path_join(best) if best != "" else ""


static func fighter_data_path(index: int) -> String:
	var dir := fighter_dir(index)
	return data_path_in(dir) if dir != "" else ""


static func assist_data_path(index: int) -> String:
	var list = MatchSetup.assists()
	if list == null or index < 0 or index >= MatchSetup.assist_count():
		return ""
	var inst = _g(list.Assists[index], "Instance")
	if inst == null or str(inst.resource_path) == "":
		return ""
	return data_path_in(str(inst.resource_path).get_base_dir().get_base_dir())


static func cached_data(path: String) -> Resource:
	if path == "":
		return null
	if not _data_cache.has(path):
		if not ResourceLoader.exists(path):
			return null
		_data_cache[path] = load(path)
	return _data_cache[path]


static func is_cached(path: String) -> bool:
	return _data_cache.has(path) or ResourceLoader.has_cached(path)


static func read_json(path: String) -> Dictionary:
	if _notes_cache.has(path):
		return _notes_cache[path]
	var out := {}
	if FileAccess.file_exists(path):
		var parsed = JSON.parse_string(FileAccess.get_file_as_string(path))
		if parsed is Dictionary:
			out = parsed
		else:
			push_warning("Command list: couldn't read %s (JSON error)" % path)
	_notes_cache[path] = out
	return out


## Training mode re-reads notes after you edit them (and the data after the frame data sheets change).
static func clear_cache() -> void:
	_notes_cache.clear()
	_data_cache.clear()


static func fighter_notes(index: int) -> Dictionary:
	var dir := fighter_dir(index)
	return read_json(dir.path_join("command_list.json")) if dir != "" else {}


# --- Inputs --------------------------------------------------------------------------------

## {"dirs": "236", "masks": [2], "hold": false} for one InputOption (the steps of one way to do the move).
static func _option_info(option) -> Dictionary:
	var dirs := ""
	var mask := 0
	var held := 0
	var last_mode := -1
	for step in _g(option, "Inputs", []):
		if step == null:
			continue
		var d := int(_g(step, "Directional", 0))
		var mode := int(_g(step, "DirectionalMode", 0))   # ButtonMode: 0 press, 1 hold, 2 release, 3 was pressed, 4 not pressed
		if d != 0 and DIR.has(d) and mode != 4 and mode != 2:
			var digit: String = DIR[d]
			# the same direction again counts when it's a second tap (22 = "was pressed", then pressed / held)
			if not dirs.ends_with(digit) or (last_mode == 3 and mode != 3):
				dirs += digit
			last_mode = mode
		var b := int(_g(step, "Buttons", 0))
		if b != 0:
			if int(_g(step, "ButtonMode", 0)) == 1:   # HOLD
				held |= b
			mask |= b
	return {"dirs": dirs, "mask": mask, "hold": mask != 0 and mask == held}


## Every way to do a move: [{"dirs", "mask", "hold"}], one per InputOption.
static func input_options(move) -> Array:
	var out: Array = []
	var inputs = _g(move, "Inputs")
	for option in _g(inputs, "ValidInputs", []):
		if option == null:
			continue
		var info := _option_info(option)
		if info["mask"] == 0 and info["dirs"] == "":
			continue
		out.append(info)
	return out


static func mask_text(mask: int) -> String:
	var parts: Array = []
	for b in BTN:
		if mask & b[0]:
			parts.append(b[1])
	return "+".join(parts)


## "236 A|B", "j. 214 C", "236 B+C or 236236 A|B|C": the notation the input glyphs draw (NetsuInputGlyphs).
static func input_text(options: Array, air_only: bool, drop_c_for: Dictionary = {}) -> String:
	var by_dirs := {}   # dirs -> [mask...], in first-seen order
	var order: Array = []
	var hold := false
	for o in options:
		var dirs: String = o["dirs"]
		if dirs == "5":
			dirs = ""
		if not by_dirs.has(dirs):
			by_dirs[dirs] = []
			order.append(dirs)
		if not int(o["mask"]) in by_dirs[dirs]:
			by_dirs[dirs].append(int(o["mask"]))
		hold = hold or o["hold"]
	# "B or C" specials: C is the EX (its own row), so the B move shows B only
	for dirs in order:
		var masks: Array = by_dirs[dirs]
		if drop_c_for.has(dirs) and masks.size() > 1 and 4 in masks:
			masks.erase(4)
	# four or more single directions with the same buttons (Flan's Star Rush): "* A|B" = any direction
	if order.size() >= 4:
		var same := true
		for dirs in order:
			if dirs.length() != 1 or by_dirs[dirs] != by_dirs[order[0]]:
				same = false
		if same:
			by_dirs = {"*": by_dirs[order[0]]}
			order = ["*"]
	# input leniency variants (623 / 6323 / 323 with the same buttons): show only the first, the standard motion
	for dirs in order:
		by_dirs[dirs].sort()
	var kept: Array = []
	for dirs in order:
		var dup := false
		for k in kept:
			if k != "" and dirs != "" and k.right(1) == dirs.right(1) and by_dirs[k] == by_dirs[dirs]:
				dup = true
		if not dup:
			kept.append(dirs)
	order = kept
	var alts: Array = []
	for dirs in order:
		var masks: Array = by_dirs[dirs]
		masks.sort()
		var btns: Array = []
		for mk in masks:
			btns.append(mask_text(mk))
		var b := "|".join(btns)
		if hold:
			b = "[" + b + "]"
		alts.append((dirs + " " + b).strip_edges() if dirs != "" else b)
	var unique: Array = []
	for a in alts:
		if not a in unique:
			unique.append(a)
	var text := " or ".join(unique)
	return ("j. " + text) if air_only and text != "" else text


# --- Frame data ---------------------------------------------------------------------------

static func _is_attack(el) -> bool:
	var t := int(_g(el, "HitboxType", 0))
	return t == HB_HIT or t == HB_PROJECTILE or t == HB_THROW or t == HB_COUNTER


static func _settings_attack(hs) -> bool:
	for el in _g(hs, "Hitboxes", []):
		if el != null and _is_attack(el):
			return true
	return false


static func _settings_hurt(hs) -> bool:
	for el in _g(hs, "Hitboxes", []):
		if el != null and int(_g(el, "HitboxType", 0)) == HB_HURT:
			return true
	return false


## Same rule as NetsuFrameData.TimingOf (engine/sakuga/Game/NetsuFrameData.cs): first / last frame with an attack box.
static func timing(ad) -> Dictionary:
	var t := {"has": false, "first": -1, "last": -1, "duration": int(_g(ad, "Duration", 0))}
	var keys: Array = _g(ad, "Hitboxes", [])
	for i in keys.size():
		var key = keys[i]
		if key == null or not _settings_attack(_g(key, "HitboxData")):
			continue
		var start := int(_g(key, "AtFrame", 0))
		var end: int = t["duration"] - 1
		for j in range(i + 1, keys.size()):
			if keys[j] != null:
				end = mini(end, int(_g(keys[j], "AtFrame", 0)) - 1)
				break
		if end < start or start >= t["duration"]:
			continue
		if not t["has"] or start < t["first"]:
			t["first"] = start
		if not t["has"] or end > t["last"]:
			t["last"] = end
		t["has"] = true
	return t


static func attack_boxes(ad) -> Array:
	var out: Array = []
	for key in _g(ad, "Hitboxes", []):
		for el in _g(_g(key, "HitboxData"), "Hitboxes", []):
			if el != null and _is_attack(el) and not el in out:
				out.append(el)
	return out


## No hurtbox from the first frame up to the attack: an invincible start.
static func invincible_start(ad, first: int) -> bool:
	if first < 2:
		return false
	var keys: Array = _g(ad, "Hitboxes", [])
	if keys.is_empty() or int(_g(keys[0], "AtFrame", 0)) > 0:
		return false
	for key in keys:
		if key == null:
			continue
		if int(_g(key, "AtFrame", 0)) >= first:
			break
		if _settings_hurt(_g(key, "HitboxData")):
			return false
	return true


## The fight's on-block rule (StanceManager.NetsuBlockAdvantage): ground normals A -4 / B -5 / C -8, ground
## specials A -4 / B or C -6 (not 623s, EX moves or supers). "" when the rule doesn't cover the move.
static func block_rule(move, options: Array) -> String:
	if move == null or int(_g(move, "SuperGaugeRequired", 0)) > 0 or (bool(_g(move, "UseOnAir", false)) and not bool(_g(move, "UseOnGround", false))):
		return ""
	var best := -1
	for o in options:
		var mk := int(o["mask"])
		var s := 0 if mk == 1 else (1 if mk == 2 else (2 if mk == 4 else -1))
		if s >= 0 and (best < 0 or s < best):
			best = s
	if best < 0:
		return ""
	var pri := int(_g(move, "Priority", 0))
	if pri == 6:
		return ["−4", "−5", "−8"][best]
	if pri == 7 or pri == 8:
		var inputs = _g(move, "Inputs")
		if inputs != null and str(inputs.resource_path).contains("623"):
			return ""
		return "−4" if best == 0 else "−6"
	return ""


## [[label, value], ...] for the data grid + auto tags, from the first state that attacks.
static func frame_data(data: Resource, states: Array, move, options: Array) -> Dictionary:
	var out := {"rows": [], "tags": []}
	var all_states: Array = _g(data, "States", [])
	var ad = null
	var t := {}
	for s in states:
		if s < 0 or s >= all_states.size() or all_states[s] == null:
			continue
		var cand = _g(all_states[s], "AnimationData")
		var ct := timing(cand)
		if ad == null:
			ad = cand
			t = ct
		if ct["has"]:
			ad = cand
			t = ct
			break
	if ad == null:
		return out
	var boxes := attack_boxes(ad)
	# the damage shown: the first striking (not grab) box among the listed states, and how many that state has
	# (a throw's grab box does no real damage; its throw state's hit does)
	var dmg_boxes: Array = []
	for s in states:
		if s < 0 or s >= all_states.size() or all_states[s] == null:
			continue
		for b in attack_boxes(_g(all_states[s], "AnimationData")):
			if int(_g(b, "HitboxType", 0)) != HB_THROW and int(_g(b, "BaseDamage", 0)) > 0:
				dmg_boxes.append(b)
		if not dmg_boxes.is_empty():
			break
	var rows: Array = out["rows"]
	if t.get("has", false):
		var recovery: int = maxi(0, t["duration"] - t["last"] - 1)
		var active: int = t["last"] - t["first"] + 1
		rows.append(["STARTUP", str(t["first"] + 1)])
		# hitting until the state ends after a long fall (dives): active until she lands
		rows.append(["ACTIVE", "to landing" if active > 60 and t["last"] >= t["duration"] - 1 else str(active)])
		if active > 60 and t["last"] >= t["duration"] - 1:
			recovery = 999
		# a state that runs on until she lands (dives, DPs) has a long made-up length: say so instead
		rows.append(["RECOVERY", str(recovery) if recovery <= 90 else "landing"])
		var blk := block_rule(move, options)
		rows.append(["ON BLOCK", blk if blk != "" else "—"])
	else:
		rows.append(["TOTAL", str(t.get("duration", 0)) + "f"])
	if not boxes.is_empty():
		var first = boxes[0]
		var dmg := int(_g(dmg_boxes[0], "BaseDamage", 0)) if not dmg_boxes.is_empty() else 0
		var hits := dmg_boxes.size()
		rows.append(["DAMAGE", (str(dmg) + (" ×%d" % hits if hits > 1 else "")) if dmg > 0 else "—"])
		var kind := int(_g(first, "HitboxType", 0))
		var guard: String = "THROW" if kind == HB_THROW else ("COUNTER" if kind == HB_COUNTER else GUARD_NAMES[clampi(int(_g(first, "HitType", 1)), 0, 3)])
		rows.append(["GUARD", guard])
		var air_only := move != null and bool(_g(move, "UseOnAir", false)) and not bool(_g(move, "UseOnGround", false))
		if guard == "HIGH" and not air_only:
			out["tags"].append("OVERHEAD")
		elif guard == "LOW" and int(_g(move, "Priority", 0)) != 6:
			out["tags"].append("LOW")
		if kind == HB_THROW and int(_g(move, "Priority", 0)) != 7:
			out["tags"].append("GRAB")
		if kind == HB_PROJECTILE:
			out["tags"].append("PROJECTILE")
	if t.get("has", false) and invincible_start(ad, t["first"]):
		out["tags"].append("INVINCIBLE")
	return out


# --- A fighter's list ----------------------------------------------------------------------

## Rows for one fighter, in list order. Each row:
##   {"name", "key", "section", "input", "desc", "tags": [], "cost": bars, "states": [int], "data": [[k, v]],
##    "follow": bool, "auto_desc": bool}
static func fighter_rows(data: Resource, notes: Dictionary) -> Array:
	var rows: Array = []
	if data == null:
		return rows
	var stances: Array = _g(data, "Stances", [])
	if stances.is_empty() or stances[0] == null:
		return rows
	var moves: Array = _g(stances[0], "Moves", [])
	var mnotes: Dictionary = notes.get("moves", {})
	# meter moves' directions with C (so the B version of the same motion shows B only)
	var ex_dirs := {}
	for m in moves:
		var cost := int(_g(m, "SuperGaugeRequired", 0))
		if m != null and cost >= BAR and cost < SUPER:
			for o in input_options(m):
				if int(o["mask"]) == 4:
					ex_dirs[o["dirs"]] = true
	# group the moves (same name, or a "group" note) in data order
	var groups := {}
	var order: Array = []
	for i in moves.size():
		var m = moves[i]
		if m == null:
			continue
		var name := str(_g(m, "MoveName", ""))
		var pri := int(_g(m, "Priority", 0))
		var cost := int(_g(m, "SuperGaugeRequired", 0))
		if pri < 6 or int(_g(m, "WillGaugeRequired", 0)) > 0 or name == "" or name == "Pushblock" or name.contains("Breakthrough"):
			continue
		var note: Dictionary = mnotes.get(name, {})
		if note.get("hide", false):
			continue
		var key := str(note.get("group", name))
		if not groups.has(key):
			var section := "Normals" if pri == 6 else "Specials"
			if cost >= SUPER:
				section = "Supers"
			elif name.contains("Throw"):
				section = "Universal"
			groups[key] = {"key": key, "section": section, "moves": [], "cost": 0, "air": false, "ground": false,
				"follow": true, "seq": []}
			order.append(key)
		var g: Dictionary = groups[key]
		g["moves"].append(m)
		g["cost"] = maxi(g["cost"], cost)
		g["air"] = g["air"] or bool(_g(m, "UseOnAir", false))
		g["ground"] = g["ground"] or bool(_g(m, "UseOnGround", false))
		var seq = _g(m, "IsSequenceFromStates", [])   # int[] in C#: a PackedInt32Array here
		if not (bool(_g(m, "SkipCheck", false)) and seq.size() > 0):
			g["follow"] = false
		for s in _g(m, "IsSequenceFromStates", []):
			g["seq"].append(int(s))
	# build the rows
	var built := {}
	for key in order:
		var g: Dictionary = groups[key]
		var note: Dictionary = mnotes.get(key, {})
		var first = g["moves"][0]
		var options: Array = []
		var states: Array = []
		for m in g["moves"]:
			options.append_array(input_options(m))
			var st := int(_g(m, "MoveState", -1))
			if st >= 0 and not st in states:
				states.append(st)
		if note.has("states"):
			states = []
			for s in note["states"]:
				states.append(int(s))
		var air_only: bool = g["air"] and not g["ground"]
		var input := str(note.get("input", input_text(options, air_only, ex_dirs if g["cost"] < BAR else {})))
		if g["follow"] and not input.begins_with(">"):
			input = "> " + input
		var fd := frame_data(data, states, first, options)
		var tags: Array = []
		for t in fd["tags"]:
			tags.append(t)
		if g["cost"] >= BAR and g["cost"] < SUPER:
			tags.push_front("EX")
		if g["air"] and g["ground"] and g["section"] != "Normals":
			tags.append("AIR OK")
		if note.has("tags"):
			tags = note["tags"].duplicate()
		var data_rows: Array = fd["rows"]
		for k in note.get("data", {}):
			var found := false
			for r in data_rows:
				if r[0] == k:
					r[1] = str(note["data"][k])
					found = true
			if not found:
				data_rows.append([k, str(note["data"][k])])
		var desc := str(note.get("desc", ""))
		var row := {"name": str(note.get("name", key)), "key": key, "section": str(note.get("section", g["section"])),
			"input": input, "desc": desc if desc != "" else NO_DESC, "auto_desc": desc == "", "tags": tags,
			"cost": int(g["cost"] / BAR), "states": states, "data": data_rows, "follow": g["follow"], "seq": g["seq"],
			"air": air_only}
		built[key] = row
	# follow-ups go right after the move they come out of
	var placed: Array = []
	for section in SECTIONS:
		for key in order:
			var row: Dictionary = built[key]
			if row["section"] != section or row["follow"] and _parent_of(row, built, order) != "":
				continue
			placed.append(row)
			_place_follow_ups(row, built, order, placed)
	for key in order:   # follow-ups whose parent wasn't found, and odd sections
		if not built[key] in placed:
			placed.append(built[key])
	# hand-written extra rows
	for extra in notes.get("extra", []):
		if not extra is Dictionary:
			continue
		var states: Array = []
		for s in extra.get("states", []):
			states.append(int(s))
		var fd := frame_data(data, states, null, [])
		var row := {"name": str(extra.get("name", "?")), "key": str(extra.get("name", "?")),
			"section": str(extra.get("section", "Specials")), "input": str(extra.get("input", "")),
			"desc": str(extra.get("desc", NO_DESC)), "auto_desc": false, "tags": extra.get("tags", fd["tags"]).duplicate(),
			"cost": int(extra.get("cost", 0)), "states": states, "data": fd["rows"], "follow": str(extra.get("input", "")).begins_with(">"), "seq": []}
		var at := placed.size()
		var after := str(extra.get("after", ""))
		for i in placed.size():
			if placed[i]["key"] == after:
				at = i + 1
				while at < placed.size() and placed[at]["follow"]:
					at += 1
		placed.insert(at, row)
	return placed


static func _parent_of(row: Dictionary, built: Dictionary, order: Array) -> String:
	for key in order:
		var other: Dictionary = built[key]
		if other == row:
			continue
		for s in row["seq"]:
			if s in other["states"]:
				return key
	return ""


static func _place_follow_ups(parent: Dictionary, built: Dictionary, order: Array, placed: Array) -> void:
	for key in order:
		var row: Dictionary = built[key]
		if row["follow"] and not row in placed and _parent_of(row, built, order) == parent["key"]:
			placed.append(row)
			_place_follow_ups(row, built, order, placed)


## A move's states by its engine name (system topics: "Throw", "Dash Forward"...). [] if the fighter has none.
static func states_of_move(data: Resource, move_name: String) -> Array:
	var stances: Array = _g(data, "Stances", [])
	if stances.is_empty() or stances[0] == null:
		return []
	for m in _g(stances[0], "Moves", []):
		if m != null and str(_g(m, "MoveName", "")) == move_name:
			return [int(_g(m, "MoveState", -1))]
	return []


## True when the move with this engine name only works in the air (the preview starts her in the air).
static func move_is_air(data: Resource, move_name: String) -> bool:
	var stances: Array = _g(data, "Stances", [])
	if stances.is_empty() or stances[0] == null:
		return false
	for m in _g(stances[0], "Moves", []):
		if m != null and str(_g(m, "MoveName", "")) == move_name:
			return bool(_g(m, "UseOnAir", false)) and not bool(_g(m, "UseOnGround", false))
	return false


## A state index by its StateName ("Assist Call", "Burst"...), -1 if none.
static func state_by_name(data: Resource, state_name: String) -> int:
	var all_states: Array = _g(data, "States", [])
	for i in all_states.size():
		if all_states[i] != null and str(_g(all_states[i], "StateName", "")).to_lower() == state_name.to_lower():
			return i
	return -1


static func anim_list(data: Resource, states: Array) -> Array:
	var out: Array = []
	var all_states: Array = _g(data, "States", [])
	for s in states:
		if s >= 0 and s < all_states.size() and all_states[s] != null:
			var ad = _g(all_states[s], "AnimationData")
			if ad != null:
				out.append(ad)
	return out


# --- Assists -------------------------------------------------------------------------------

static func assist_rows(index: int) -> Array:
	var rows: Array = []
	var list = MatchSetup.assists()
	if list == null or index < 0 or index >= MatchSetup.assist_count():
		return rows
	var el = list.Assists[index]
	var aname := str(_g(el, "AssistName", "Assist"))
	var data := cached_data(assist_data_path(index))
	var notes: Dictionary = read_json(ASSIST_NOTES_FILE).get(aname, {})
	var dir_inputs := {0: "S", 1: "6 S", 2: "4 S"}
	for mv in _g(el, "Moves", []):
		if mv == null:
			continue
		var mname := str(_g(mv, "MoveName", "5S"))
		var note: Dictionary = notes.get(mname, {})
		var states: Array = [int(_g(mv, "StateIndex", 1))]
		if note.has("states"):
			states = []
			for s in note["states"]:
				states.append(int(s))
		var data_rows: Array = [["COOLDOWN", "%d s" % roundi(float(_g(mv, "Cooldown", 600)) / 60.0)]]
		var dmg_total := 0
		var guard := ""
		for s in states:
			var all_states: Array = _g(data, "States", [])
			if s < 0 or s >= all_states.size() or all_states[s] == null:
				continue
			for b in attack_boxes(_g(all_states[s], "AnimationData")):
				dmg_total += int(_g(b, "BaseDamage", 0))
				if guard == "":
					guard = GUARD_NAMES[clampi(int(_g(b, "HitType", 1)), 0, 3)]
		if dmg_total > 0:
			data_rows.append(["DAMAGE", str(dmg_total)])
		if guard != "":
			data_rows.append(["GUARD", guard])
		for k in note.get("data", {}):
			data_rows.append([k, str(note["data"][k])])
		var display := str(_g(mv, "DisplayName", ""))
		rows.append({"name": str(note.get("name", display if display != "" else mname)), "key": mname, "section": aname,
			"input": str(note.get("input", dir_inputs.get(int(_g(mv, "Direction", 0)), "S"))),
			"desc": str(note.get("desc", _g(mv, "Description", ""))), "auto_desc": false,
			"tags": note.get("tags", []).duplicate(), "cost": 0, "states": states, "data": data_rows, "follow": false,
			"seq": [], "assist": index, "spawn": _g(mv, "SpawnOffset", Vector2i(-9000, 0))})
	var extras: Array = notes.get("extra", []).duplicate()
	extras.append_array(read_json(ASSIST_NOTES_FILE).get("*", {}).get("extra", []))   # rows every assist shows
	for extra in extras:
		if extra is Dictionary:
			rows.append({"name": str(extra.get("name", "")), "key": str(extra.get("name", "")), "section": str(extra.get("section", "Calling")),
				"input": str(extra.get("input", "")), "desc": str(extra.get("desc", "")), "auto_desc": false,
				"tags": extra.get("tags", []).duplicate(), "cost": int(extra.get("cost", 0)), "states": [], "data": _pairs(extra.get("data", [])),
				"follow": false, "seq": [], "preview": extra.get("preview", {})})
	return rows


static func _pairs(v) -> Array:
	var out: Array = []
	if v is Array:
		for p in v:
			if p is Array and p.size() >= 2:
				out.append([str(p[0]), str(p[1])])
	elif v is Dictionary:
		for k in v:
			out.append([str(k), str(v[k])])
	return out


# --- System topics -------------------------------------------------------------------------

## [{"id", "title", "rows": [...]}] from data/command_list/system.json. A row's "preview" says what the right side
## shows: {"move": "<engine move name>"} or {"state": "<state name>"} (played by the fighter being shown),
## {"illustration": "gauge" | "scaling" | "levels" | "overdrive" | "juggle"} or {"cutin": "ex" | "super"}.
static func system_pages() -> Array:
	var pages: Array = []
	for p in read_json(SYSTEM_FILE).get("pages", []):
		if not p is Dictionary:
			continue
		var rows: Array = []
		for t in p.get("topics", []):
			if not t is Dictionary:
				continue
			if t.has("heading"):
				rows.append({"heading": str(t["heading"])})
				continue
			rows.append({"name": str(t.get("name", "")), "key": str(t.get("name", "")), "section": str(p.get("title", "")),
				"input": str(t.get("input", "")), "desc": str(t.get("desc", "")), "auto_desc": false,
				"tags": t.get("tags", []).duplicate(), "cost": int(t.get("cost", 0)), "states": [],
				"data": _pairs(t.get("data", [])), "follow": false, "seq": [], "preview": t.get("preview", {})})
		pages.append({"id": str(p.get("id", "")), "title": str(p.get("title", "")), "rows": rows})
	return pages
