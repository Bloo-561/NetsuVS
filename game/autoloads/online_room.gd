extends Node
## ONLINE ROOM (autoload "OnlineRoom", Oct 25 2026): the rules of a group lobby.
##
## Up to 8 players in one lobby (the connections are the NetsuOnline autoload, engine/netcode/NetsuOnline.cs).
## KING OF THE HILL:
##   - everyone stands in one line (the queue). The first two fight: the KING (front of the line, player 1 side)
##     and the CHALLENGER (second, player 2 side).
##   - the winner stays on (the king's wins in a row are counted), the loser goes to the back of the line.
##   - everyone else watches the fight live: it opens on their screen by itself (B goes back to the lobby, A in the
##     lobby watches again), a moment behind the players. Someone who comes in during a fight watches it from the
##     start, fast-forwarded until it's live.
##   - the two players pick fighter / colour / assist in the lobby. They have pick_seconds (60) to do it once both
##     are there, then what they have is locked in. The host picks the stage (RANDOM = a new one each match); the
##     rules (rounds, round time, intros) are the host's Options.
##   - anyone can SIT OUT (leave the line, keep watching) and get back in line (at the back).
##   - leaving during your own fight loses it. The host leaving closes the lobby for everyone.
## The host's copy of this script decides everything (`room`, below) and sends it to everyone after every change
## ("room"); the others send what they do to the host: "hi" (name), "here" (lobby / fight / watch), "pick",
## "result", "queue" (sit out / back in line). Fights: MatchSetup.start_online_room(). The lobby screen
## (scenes/online/online_lobby.gd) shows `room` and calls the functions under "For the lobby screen".
## Docs: docs/online.md.

signal room_changed
signal notice(text: String)

const PROTOCOL := 2
const LOBBY := "res://scenes/online/online_lobby.tscn"
const BATTLE := "res://scenes/battle/battle.tscn"
const VS_SCREEN := "res://scenes/vs_screen/vs_screen.tscn"
const MAX_NAME := 16

## Seconds the two players get to pick (counted while both are in the lobby), then their choice is locked in.
@export var pick_seconds: float = 60.0
## Seconds on the results screen before everyone goes back to the lobby (any button goes straight away).
@export var results_seconds: float = 5.0
## Spectators: once the match is over, how long the stream may stay quiet before giving up on the rest.
@export var watch_give_up: float = 6.0

## The room, as the host decided it (everyone has a copy; ids are the connection ids: host 0):
##   "code": the lobby code   "members": {"<id>": {"name", "state": "lobby"|"fight"|"watch"|"", "out", "wins"}}
##   "order": ids in the order they came in   "queue": the line (ids), king first
##   "streak": wins in a row of "streak_id" (the last winner, -1 = nobody yet)
##   "stage": stage index or -1 (random)   "rules": {"rounds", "time", "intros"}
##   "match": {"id", "state": "none"|"picking"|"fighting"|"over", "p1", "p2", "picks": {"<id>": {"f","c","a","ready"}},
##             "p": the fight (MatchSetup.start_online_room), "pick_left": seconds, "winner", "loser", "forfeit"}
##   "last": the last result {"match", "winner", "loser", "w_name", "l_name", "streak", "forfeit"}
var room := {}
var my_id := -1
var playing := -1        # the match id this computer is fighting in (-1: none)
var watching := -1       # the match id this computer is watching (-1: none)

var _net: Node
var _in_lobby := false   # the lobby screen is open
var _declined := -1      # the match this computer stopped watching (not pulled back into it)
var _reported := -1      # the match whose result this computer sent
var _results_t := -1.0   # seconds the results screen has been up
var _over_t := 0.0       # watching: seconds since the match ended for the players with nothing new in the stream
var _want_lobby := false
var _last_pick := {}     # host: id -> the last {"f","c","a"} each player had (the next match starts from it)
var _next_match := 1
var _sent_state := ""
var _overlay: CanvasLayer
var _overlay_label: Label
var _pick_tick := 0.0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_connect.call_deferred()   # after every autoload is in the tree


func _connect() -> void:
	_net = get_node_or_null("/root/NetsuOnline")
	if _net == null:
		return
	_net.connect("Connected", _on_connected)
	_net.connect("Disconnected", _on_disconnected)
	_net.connect("MessageReceived", _on_message)
	_net.connect("MemberJoined", _on_member_joined)
	_net.connect("MemberLeft", _on_member_left)
	_net.connect("CodeReady", _on_code_ready)


# --- For the lobby screen -----------------------------------------------------------------------

## In a lobby (the host's is open, or this computer is in one).
func active() -> bool:
	return _net != null and bool(_net.InLobby) and not room.is_empty()


func is_host() -> bool:
	return _net != null and bool(_net.IsHost)


## The lobby screen opened / closed (this computer is in the lobby, not in a fight).
func lobby_opened() -> void:
	_in_lobby = true
	playing = -1
	watching = -1
	_want_lobby = false
	_results_t = -1.0
	_hide_overlay()
	if _net and bool(_net.IsHost) and room.is_empty() and bool(_net.IsActive):
		_host_open()
	_set_my_state("lobby")
	_apply_room()


func lobby_closed() -> void:
	_in_lobby = false


## The current match, or {} when there's none.
func current_match() -> Dictionary:
	return room.get("match", {})


func member(id: int) -> Dictionary:
	return room.get("members", {}).get(str(id), {})


func member_name(id: int) -> String:
	var m := member(id)
	return str(m.get("name", "")) if not m.is_empty() else "?"


## My side in the current match (picking or fighting): 0 = player 1 (king), 1 = player 2, -1 = not in it.
func my_side() -> int:
	var m := current_match()
	if m.is_empty() or not str(m.get("state", "none")) in ["picking", "fighting"]:
		return -1
	if int(m.get("p1", -1)) == my_id:
		return 0
	if int(m.get("p2", -1)) == my_id:
		return 1
	return -1


## Place in the line: 0 = king, 1 = challenger, 2 = next... -1 = sitting out.
func queue_position(id: int) -> int:
	return room.get("queue", []).find(id)


## The pick a player has in the current match ({} if none).
func pick_of(id: int) -> Dictionary:
	return current_match().get("picks", {}).get(str(id), {})


## Seconds left to pick (the host's count, carried on between its updates).
func pick_time_left() -> float:
	return float(current_match().get("pick_left", pick_seconds))


## The players of the current match are both in the lobby screen (the pick clock runs).
func pickers_here() -> bool:
	var m := current_match()
	return str(member(int(m.get("p1", -1))).get("state", "")) == "lobby" \
		and str(member(int(m.get("p2", -1))).get("state", "")) == "lobby"


func send_pick(f: int, c: int, a: int, ready: bool) -> void:
	_to_host({"t": "pick", "f": f, "c": c, "a": a, "ready": ready})


## Sit out (stay in the lobby, out of the line) or get back in line (at the back).
func set_sit_out(on: bool) -> void:
	_to_host({"t": "queue", "on": not on})


## Host: the stage for the next matches (-1 = random each match).
func set_stage(index: int) -> void:
	if not is_host() or room.is_empty():
		return
	room["stage"] = index
	MatchSetup.set_meta("online_stage", index)
	_broadcast()


## Watch the fight that's on (from the lobby).
func watch() -> void:
	var m := current_match()
	if str(m.get("state", "")) != "fighting" or my_side() >= 0:
		return
	_declined = -1
	_watch(m)


## Name shown in the lobby: the Options name, else "Player N" (the host fills that in).
func my_name() -> String:
	var gs := get_node_or_null("/root/GameSettings")
	return _clean_name(str(gs.get_value("online", "name")) if gs else "")


func set_my_name(text: String) -> void:
	var gs := get_node_or_null("/root/GameSettings")
	if gs:
		gs.set_value("online", "name", _clean_name(text))
	if active():
		_to_host({"t": "hi", "name": my_name(), "v": PROTOCOL})


# --- Connection events ------------------------------------------------------------------------------

func _on_code_ready(code: String, _lan: String, _note: String) -> void:
	if is_host():
		if room.is_empty():
			_host_open()
		room["code"] = code
		_broadcast()


func _on_connected(host: bool) -> void:
	if host:
		return   # the host: MemberJoined
	my_id = int(_net.MyId)
	_to_host({"t": "hi", "name": my_name(), "v": PROTOCOL})
	_sent_state = ""
	_set_my_state("lobby" if _in_lobby else "")


func _on_disconnected(_reason: String) -> void:
	_reset()


func _reset() -> void:
	room = {}
	my_id = -1
	playing = -1
	watching = -1
	_declined = -1
	_reported = -1
	_results_t = -1.0
	_want_lobby = false
	_last_pick = {}
	_sent_state = ""
	_hide_overlay()
	room_changed.emit()


func _on_message(m: Dictionary) -> void:
	if is_host():
		if m.has("from"):
			_host_handle(m, int(m["from"]))
		return
	match str(m.get("t", "")):
		"room":
			room = _normalized(m.get("room", {}))
			_apply_room()
			room_changed.emit()
		"notice":
			_notice(str(m.get("text", "")))


func _notice(text: String) -> void:
	if text == "":
		return
	if _in_lobby:
		notice.emit(text)
	else:
		MatchSetup.online_notice = text   # shown when the lobby opens


# --- Host: the room ---------------------------------------------------------------------------------

func _host_open() -> void:
	my_id = 0
	_next_match = 1
	var gs := get_node_or_null("/root/GameSettings")
	room = {
		"code": str(_net.Code),
		"members": {},
		"order": [],
		"queue": [],
		"streak": 0,
		"streak_id": -1,
		"stage": int(MatchSetup.get_meta("online_stage", -1)) if MatchSetup.has_meta("online_stage") else -1,
		"rules": {"rounds": int(gs.get_value("game", "rounds_online")) if gs else 2,
			"time": int(gs.get_value("game", "time_versus")) if gs else 99,
			"intros": bool(gs.get_value("game", "intros")) if gs else true},
		"match": {"id": 0, "state": "none", "p1": -1, "p2": -1, "picks": {}, "p": {}},
		"last": {},
	}
	_last_pick = {}
	_add_member(0, my_name())
	room["members"]["0"]["state"] = "lobby" if _in_lobby else ""


func _add_member(id: int, wanted: String) -> void:
	room["members"][str(id)] = {"name": _unique_name(id, wanted), "state": "", "out": false, "wins": 0}
	if not id in room["order"]:
		room["order"].append(id)
	if not id in room["queue"]:
		room["queue"].append(id)


func _on_member_joined(id: int) -> void:
	if room.is_empty():
		_host_open()
	_add_member(id, "")
	_maybe_next_match()
	_broadcast()
	if str(current_match().get("state", "")) == "fighting":
		_net.SendStreamTo(id)   # a fight is on: the newcomer can watch it from the start


func _on_member_left(id: int, why: String) -> void:
	if room.is_empty() or not room["members"].has(str(id)):
		return
	var who := member_name(id)
	var m: Dictionary = room["match"]
	var in_match := id == int(m.get("p1", -1)) or id == int(m.get("p2", -1))
	var fighting := in_match and str(m["state"]) == "fighting"
	room["members"][str(id)]["out"] = true   # (so the match below doesn't put them back in line)
	var text := "%s %s." % [who, why]
	if fighting:
		var other := int(m["p2"]) if id == int(m["p1"]) else int(m["p1"])
		_finish_match(other, id, true)
		text = "%s %s: %s wins the match." % [who, why, member_name(other)]
	room["members"].erase(str(id))
	room["order"].erase(id)
	room["queue"].erase(id)
	_last_pick.erase(id)
	if id == int(room.get("streak_id", -1)):
		room["streak"] = 0
		room["streak_id"] = -1
	if in_match and not fighting and str(m["state"]) == "picking":
		m["state"] = "none"
	_maybe_next_match()
	_send_notice(text)
	_broadcast()


## Something a player did (the host's own actions come here too, from = 0).
func _host_handle(m: Dictionary, from: int) -> void:
	if room.is_empty() or not room["members"].has(str(from)):
		return
	var me: Dictionary = room["members"][str(from)]
	match str(m.get("t", "")):
		"hi":
			if int(m.get("v", 0)) != PROTOCOL:
				_send_notice("%s has a different version of the game: fights with them would go wrong." % member_name(from))
			me["name"] = _unique_name(from, str(m.get("name", "")))
		"here":
			me["state"] = str(m.get("state", ""))
		"queue":
			var on := bool(m.get("on", true))
			me["out"] = not on
			if on and not from in room["queue"]:
				room["queue"].append(from)
			elif not on:
				room["queue"].erase(from)
				var cur: Dictionary = room["match"]
				if str(cur["state"]) == "picking" and from in [int(cur["p1"]), int(cur["p2"])]:
					cur["state"] = "none"
			_maybe_next_match()
		"pick":
			var cur: Dictionary = room["match"]
			if str(cur["state"]) != "picking" or not from in [int(cur["p1"]), int(cur["p2"])]:
				return
			var pk := {"f": clampi(int(m.get("f", 0)), 0, maxi(0, MatchSetup.fighter_count() - 1)),
				"c": maxi(int(m.get("c", 0)), 0), "a": maxi(int(m.get("a", 0)), 0), "ready": bool(m.get("ready", false))}
			cur["picks"][str(from)] = pk
			_last_pick[from] = {"f": pk["f"], "c": pk["c"], "a": pk["a"]}
			if _both_ready():
				_start_match()
		"result":
			var cur: Dictionary = room["match"]
			if str(cur["state"]) != "fighting" or int(m.get("match", -1)) != int(cur["id"]):
				return
			if not from in [int(cur["p1"]), int(cur["p2"])]:
				return
			var winner := int(cur["p1"]) if int(m.get("side", 0)) == 0 else int(cur["p2"])
			var loser := int(cur["p2"]) if winner == int(cur["p1"]) else int(cur["p1"])
			_finish_match(winner, loser, false)
		_:
			return
	_broadcast()


func _both_ready() -> bool:
	var m: Dictionary = room["match"]
	var a: Dictionary = m["picks"].get(str(m["p1"]), {})
	var b: Dictionary = m["picks"].get(str(m["p2"]), {})
	return bool(a.get("ready", false)) and bool(b.get("ready", false))


## The next two in line pick, when nothing is on.
func _maybe_next_match() -> void:
	var m: Dictionary = room["match"]
	if str(m["state"]) in ["picking", "fighting"]:
		return
	var line: Array = room["queue"]
	if line.size() < 2:
		if str(m["state"]) != "over":
			m["state"] = "none"
		return
	var p1 := int(line[0])
	var p2 := int(line[1])
	var picks := {}
	for side in 2:
		var id := p1 if side == 0 else p2
		var last: Dictionary = _last_pick.get(id, {})
		var f := int(last.get("f", side % maxi(1, MatchSetup.fighter_count())))
		picks[str(id)] = {"f": f, "c": int(last.get("c", 0)), "a": int(last.get("a", side % maxi(1, MatchSetup.assist_count()))),
			"ready": false}
	room["match"] = {"id": _next_match, "state": "picking", "p1": p1, "p2": p2, "picks": picks, "p": {},
		"pick_left": pick_seconds, "winner": -1, "loser": -1, "forfeit": false}
	_next_match += 1


func _start_match() -> void:
	var m: Dictionary = room["match"]
	var a: Dictionary = m["picks"][str(m["p1"])]
	var b: Dictionary = m["picks"][str(m["p2"])]
	var stage := int(room["stage"])
	if stage < 0 or stage >= MatchSetup.stage_count():
		stage = randi() % maxi(1, MatchSetup.stage_count())
	var c2 := int(b["c"])
	if int(b["f"]) == int(a["f"]) and c2 == int(a["c"]) and MatchSetup.palette_count(int(b["f"])) > 1:
		c2 = (c2 + 1) % MatchSetup.palette_count(int(b["f"]))   # mirror match: tell them apart
	m["p"] = {"f1": a["f"], "c1": a["c"], "a1": a["a"], "f2": b["f"], "c2": c2, "a2": b["a"], "stage": stage,
		"rules": room["rules"], "n1": member_name(int(m["p1"])), "n2": member_name(int(m["p2"])), "match": m["id"],
		"streak": int(room["streak"])}
	m["state"] = "fighting"


func _finish_match(winner: int, loser: int, forfeit: bool) -> void:
	var m: Dictionary = room["match"]
	room["streak"] = int(room["streak"]) + 1 if winner == int(room.get("streak_id", -1)) else 1
	room["streak_id"] = winner
	var line: Array = room["queue"]
	line.erase(loser)
	if room["members"].has(str(loser)) and not bool(room["members"][str(loser)].get("out", false)):
		line.append(loser)   # to the back of the line
	line.erase(winner)
	line.push_front(winner)   # stays on
	if room["members"].has(str(winner)):
		room["members"][str(winner)]["wins"] = int(room["members"][str(winner)].get("wins", 0)) + 1
	m["state"] = "over"
	m["winner"] = winner
	m["loser"] = loser
	m["forfeit"] = forfeit
	room["last"] = {"winner": winner, "loser": loser, "w_name": member_name(winner), "l_name": member_name(loser),
		"streak": int(room["streak"]), "forfeit": forfeit, "match": int(m["id"])}
	_maybe_next_match()


func _send_notice(text: String) -> void:
	if _net:
		_net.Send({"t": "notice", "text": text})
	_notice(text)


## The room to everyone (and to this computer's own screens).
func _broadcast() -> void:
	if room.is_empty():
		return
	if _net and int(_net.MemberCount) > 0:
		_net.Send({"t": "room", "room": room})
	_apply_room()
	room_changed.emit()


func _unique_name(id: int, wanted: String) -> String:
	var name := _clean_name(wanted)
	if name == "":
		name = "Player %d" % (id + 1)
	var taken := []
	for key in room.get("members", {}):
		if int(key) != id:
			taken.append(str(room["members"][key].get("name", "")).to_lower())
	var base := name
	var n := 2
	while name.to_lower() in taken:
		name = "%s (%d)" % [base, n]
		n += 1
	return name


func _clean_name(text: String) -> String:
	var out := ""
	for ch in text.strip_edges():
		if ch.unicode_at(0) >= 32:
			out += ch
	return out.strip_edges().substr(0, MAX_NAME)


# --- Everyone: following the room -------------------------------------------------------------------

## JSON turns numbers into floats: back to ints where the room has ids / counts.
func _normalized(r: Dictionary) -> Dictionary:
	if r.is_empty():
		return {}
	for key in ["order", "queue"]:
		var ints := []
		for v in r.get(key, []):
			ints.append(int(v))
		r[key] = ints
	r["streak"] = int(r.get("streak", 0))
	r["streak_id"] = int(r.get("streak_id", -1))
	r["stage"] = int(r.get("stage", -1))
	var m: Dictionary = r.get("match", {})
	for key in ["id", "p1", "p2", "winner", "loser"]:
		m[key] = int(m.get(key, -1))
	for key in ["winner", "loser", "streak", "match"]:
		if r.get("last", {}).has(key):
			r["last"][key] = int(r["last"][key])
	r["match"] = m
	return r


## Called whenever the room changes: start the fight this computer is in, or watch the one that's on.
func _apply_room() -> void:
	if room.is_empty() or _net == null:
		return
	var m := current_match()
	var state := str(m.get("state", "none"))
	if state == "fighting":
		_net.SetMatch(int(m["id"]), int(m["p1"]), int(m["p2"]))
		var id := int(m["id"])
		if id != playing and id != watching and _in_lobby and not SceneRouter.is_busy():
			if my_side() >= 0:
				_fight(m)
			elif id != _declined:
				_watch(m)
	# the fight this computer is in was decided without it (the other player left): back to the lobby
	var last: Dictionary = room.get("last", {})
	if playing >= 0 and int(last.get("match", -1)) == playing and bool(last.get("forfeit", false)) and _results_t < 0.0:
		_back_to_lobby()


func _fight(m: Dictionary) -> void:
	playing = int(m["id"])
	watching = -1
	_reported = -1
	_results_t = -1.0
	_set_my_state("fight")
	MatchSetup.start_online_room(m.get("p", {}), my_side())


func _watch(m: Dictionary) -> void:
	watching = int(m["id"])
	playing = -1
	_results_t = -1.0
	_over_t = 0.0
	_set_my_state("watch")
	MatchSetup.start_online_room(m.get("p", {}), -1)


func _set_my_state(state: String) -> void:
	if _net == null or not bool(_net.InLobby) or state == _sent_state:
		return
	_sent_state = state
	_to_host({"t": "here", "state": state})


func _to_host(m: Dictionary) -> void:
	if _net == null:
		return
	if bool(_net.IsHost):
		_host_handle(m, 0)
	elif bool(_net.IsConnected):
		_net.SendTo(0, m)


func _back_to_lobby() -> void:
	_want_lobby = true


func _process(delta: float) -> void:
	if _net == null:
		return
	if not room.is_empty() and not bool(_net.InLobby):
		_reset()
		return
	if room.is_empty():
		return
	if _in_lobby:
		_apply_room()   # (a fight that couldn't start while a screen change was running starts now)
	# host: the pick clock (only while both players are in the lobby screen)
	if is_host():
		var m := current_match()
		if str(m.get("state", "")) == "picking" and pickers_here():
			m["pick_left"] = maxf(0.0, float(m.get("pick_left", pick_seconds)) - delta)
			_pick_tick += delta
			if float(m["pick_left"]) <= 0.0:
				for key in m["picks"]:
					m["picks"][key]["ready"] = true
				_start_match()
				_broadcast()
			elif _pick_tick >= 5.0:
				_pick_tick = 0.0
				_broadcast()   # keeps everyone's clock in step
	elif str(current_match().get("state", "")) == "picking" and pickers_here():
		current_match()["pick_left"] = maxf(0.0, pick_time_left() - delta)
	_fight_tick(delta)
	if _want_lobby and not SceneRouter.is_busy():
		var scene := get_tree().current_scene
		var path: String = scene.scene_file_path if scene else ""
		if path != VS_SCREEN:   # (the VS screen goes on to the fight by itself: leave from there)
			_want_lobby = false
			playing = -1
			watching = -1
			_hide_overlay()
			if path != LOBBY:
				SceneRouter.go_to(LOBBY)


## In a fight (playing or watching): send the result, then back to the lobby a few seconds after the results screen.
func _fight_tick(delta: float) -> void:
	if playing < 0 and watching < 0:
		return
	var scene := get_tree().current_scene
	if scene == null or scene.scene_file_path != BATTLE:
		return
	var gm := scene.get_node_or_null("GameManager")
	if gm == null or not gm.has_method("NetsuMatchResult"):
		return
	_show_overlay()
	var r: Array = gm.NetsuMatchResult()
	if bool(r[0]):
		if playing >= 0 and _reported != playing and int(r[1]) >= 0:
			_reported = playing
			_to_host({"t": "result", "match": playing, "side": int(r[1])})
		_results_t = maxf(_results_t, 0.0) + delta
		if _results_t >= results_seconds:
			_back_to_lobby()
		return
	if watching >= 0:
		# the players are done (or gone) and the stream has stopped short of the end: don't wait forever
		var m := current_match()
		var over := not (str(m.get("state", "")) == "fighting" and int(m.get("id", -1)) == watching)
		var rb := scene.get_node_or_null("RollbackManager")
		var behind: int = rb.call("NetsuWatchBehind") if rb and rb.has_method("NetsuWatchBehind") else 0
		_over_t = _over_t + delta if over and behind <= 0 else 0.0
		if _over_t >= watch_give_up:
			_back_to_lobby()


func _input(event: InputEvent) -> void:
	if (playing < 0 and watching < 0) or _want_lobby:
		return
	var scene := get_tree().current_scene
	if scene == null or scene.scene_file_path != BATTLE:
		return
	var back := event.is_action_pressed("ui_cancel") or event.is_action_pressed("p1_b")
	if watching >= 0 and back and _results_t < 0.0:
		_declined = watching   # stopped watching: not pulled back into this one
		_back_to_lobby()
	elif _results_t >= 0.6 and _any_button(event):
		_back_to_lobby()   # (the results screen says PRESS ANY BUTTON)


func _any_button(event: InputEvent) -> bool:
	if event.is_echo() or not event.is_pressed():
		return false
	for action in ["ui_accept", "ui_cancel", "p1_a", "p1_b", "p1_c", "p1_s", "p1_start", "p2_a", "p2_b", "p2_c", "p2_s", "p2_start"]:
		if event.is_action_pressed(action):
			return true
	return false


# --- The banner over a fight -------------------------------------------------------------------------

func _show_overlay() -> void:
	if _overlay == null:
		_overlay = CanvasLayer.new()
		_overlay.layer = 60
		add_child(_overlay)
		_overlay_label = Label.new()
		_overlay_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		_overlay_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		_overlay_label.add_theme_font_size_override("font_size", 22)
		_overlay_label.add_theme_color_override("font_color", Color(0.85, 0.92, 1.0))
		_overlay_label.add_theme_color_override("font_outline_color", Color(0.02, 0.03, 0.12))
		_overlay_label.add_theme_constant_override("outline_size", 6)
		_overlay_label.add_theme_font_override("font", NetsuUI.sans(4))
		_overlay.add_child(_overlay_label)
	var view := get_viewport().get_visible_rect().size
	var k := view.y / 1080.0
	var text := ""
	if _results_t >= 0.0:
		# the results screen: at the bottom, between its own footer texts
		text = "BACK TO THE LOBBY IN %d" % ceili(maxf(results_seconds - _results_t, 0.0))
		_overlay_label.position = Vector2(0, view.y - 74.0 * k)
		_overlay_label.size = Vector2(view.x, 40.0 * k)
		_overlay_label.add_theme_font_size_override("font_size", int(22.0 * k))
	elif watching >= 0:
		# watching: under the round timer, between the players' name plates (the HUD's gauges are at the bottom)
		text = "WATCHING\nB  BACK TO THE LOBBY"
		_overlay_label.position = Vector2(view.x * 0.5 - 220.0 * k, 172.0 * k)
		_overlay_label.size = Vector2(440.0 * k, 64.0 * k)
		_overlay_label.add_theme_font_size_override("font_size", int(19.0 * k))
	_overlay_label.text = text
	_overlay.visible = text != ""


func _hide_overlay() -> void:
	if _overlay:
		_overlay.visible = false
