extends Node
## FAKE ONLINE ROOM (Nov 11, dev only; autoload "DevNet", listed right after NetsuOnline)
##
## Lets scenes/online/online_lobby.tscn run on its own (F6) with no second computer. When it's on, this node takes
## the name /root/NetsuOnline (the real C# node is renamed /root/NetsuOnlineReal and left idle), so the lobby
## screen, OnlineRoom (the room rules) and MatchSetup talk to it exactly as they talk to the real connection: same
## signals, same properties, same calls. All the room rules run for real (OnlineRoom's host code): king of the hill,
## picks, the pick clock, PASS, SPECTATE ONLY, the room log.
##
## What it fakes:
##   - CREATE LOBBY: you're the host (code 00000); `fake_players` bots join one by one, say hello and stand in line.
##   - Bots pick a fighter / colour / assist and press ready `fake_pick_seconds` after their pick phase starts.
##   - A bot-vs-bot match (when you spectate or wait in line) is decided `fake_fight_seconds` after it starts
##     (random winner), as if the two bots had fought it.
##   - Your own match (or watching one): the real rollback fight needs a real peer, so it runs as a LOCAL fight
##     instead (MatchSetup.start_online_room asks dev_local_fight): you on your side with player 1's controls, the
##     CPU on the other (watching: CPU vs CPU). The result goes back to the room like an online one, and the room
##     goes on (winner stays, loser to the back of the line...).
##   - JOIN LOBBY isn't faked (it says so): the fake room is always yours.
## Off unless: a debug build, the scene launched with F6 is the online lobby, and data/dev_fixtures.tres has
## enabled and fake_online on. Then it does nothing at all (and keeps the name DevNet).

const LOBBY := "res://scenes/online/online_lobby.tscn"
const FIXTURES := "res://data/dev_fixtures.tres"
const CODE := "00000"
const BOT_NAMES := ["Rean (bot)", "Alisa (bot)", "Machias (bot)", "Laura (bot)", "Fie (bot)", "Elliot (bot)", "Jusis (bot)"]

# --- the same signals as NetsuOnline (engine/netcode/NetsuOnline.cs) ---
signal StatusChanged(text: String)
signal CodeReady(code: String, lan_code: String, note: String)
signal ReplyCodeReady(code: String)
signal Connected(host: bool)
signal Disconnected(reason: String)
signal MessageReceived(message: Dictionary)
signal MemberJoined(id: int)
signal MemberLeft(id: int, reason: String)

# --- the same properties ---
var IsHost := false
var MyId := -1
var MaxPlayers := 8
var Code := ""
var LanCode := ""
var ReplyCode := ""
var LongCode := ""
var LastStatus := ""
var HasLobbyNumber := false
var LocalPort := 0
var Ping := -1
var IsActive: bool:
	get: return _open
var IsConnected: bool:
	get: return _open and not _bots.is_empty()
var InLobby: bool:
	get: return _open
var MemberCount: int:
	get: return _bots.size()

## True when this run uses the fake room.
var active := false

var _fx
var _open := false
var _bots := {}            # id -> {"name"}
var _joining: Array = []   # ids still to join
var _join_t := 0.0
var _events: Array = []    # [{"at": seconds, "msg": {...}}]: bot messages to the host, in time order
var _t := 0.0
var _picked := {}          # "match:id" -> true (a bot's pick is on its way)
var _decided := {}         # match id -> true (a bot-vs-bot result is on its way)
var _versus_return := ""   # the Versus mode's ReturnToScene while a local fight points it at the lobby
var _versus_index := -1


func _ready() -> void:
	set_process(false)
	if not OS.is_debug_build() or _launched_scene() != LOBBY or not ResourceLoader.exists(FIXTURES):
		return
	_fx = load(FIXTURES)
	if _fx == null or not _fx.enabled or not _fx.fake_online:
		return
	var real := get_node_or_null("/root/NetsuOnline")
	if real:
		real.name = "NetsuOnlineReal"
		real.process_mode = Node.PROCESS_MODE_DISABLED
	name = "NetsuOnline"   # the lobby, OnlineRoom and MatchSetup find this one now
	active = true
	process_mode = Node.PROCESS_MODE_ALWAYS
	set_process(true)
	print("[DevNet] fake online room: CREATE LOBBY, then %d bot(s) join." % _bot_count())


func _launched_scene() -> String:
	for arg in OS.get_cmdline_args():
		var a := str(arg)
		if a.ends_with(".tscn") or a.ends_with(".scn"):
			return a
	return ""


func _bot_count() -> int:
	return clampi(int(_fx.fake_players), 1, mini(7, MaxPlayers - 1))


# --- the calls the lobby and OnlineRoom make (same names as NetsuOnline) ---

func Host(_port: int = 7777) -> bool:
	Leave()
	IsHost = true
	MyId = 0
	_open = true
	Code = CODE
	_status("Fake lobby open (DevBoot): bots are on their way.")
	CodeReady.emit.call_deferred(Code, "", "This is the fake room (DevBoot): nobody else can join it.")
	_joining = []
	for i in _bot_count():
		_joining.append(i + 1)
	_join_t = 0.0
	return true


func Join(_code: String) -> bool:
	_status("The fake room (DevBoot) can't join a lobby: use CREATE LOBBY, the bots come to you.")
	return false


func AcceptReply(_code: String) -> bool:
	return false


func Leave() -> void:
	_open = false
	IsHost = false
	MyId = -1
	Code = ""
	_bots.clear()
	_joining.clear()
	_events.clear()
	_picked.clear()
	_decided.clear()


func IsLobbyNumber(text: String) -> bool:
	return text.length() == 5 and text.is_valid_int()


func Send(message: Dictionary) -> bool:
	if not _open:
		return false
	for id in _bots:
		_bot_hears(int(id), message)
	return not _bots.is_empty()


func SendTo(id: int, message: Dictionary) -> bool:
	if not _bots.has(id):
		return false
	_bot_hears(id, message)
	return true


func PingOf(id: int) -> int:
	return 18 + 9 * id if _bots.has(id) else -1


func SetMatch(_match: int, _p1: int, _p2: int) -> void:
	pass


func SendStreamTo(_id: int) -> void:
	pass


# --- the bots ---

func _status(text: String) -> void:
	LastStatus = text
	print("[DevNet] " + text)
	StatusChanged.emit(text)


func _process(delta: float) -> void:
	_t += delta
	_restore_versus_return()
	if not _open:
		return
	if not _joining.is_empty():
		_join_t += delta
		if _join_t >= 1.0:
			_join_t = 0.0
			_bot_join(int(_joining.pop_front()))
	while not _events.is_empty() and float(_events[0]["at"]) <= _t:
		var e: Dictionary = _events.pop_front()
		var msg: Dictionary = e["msg"]
		if _bots.has(int(msg.get("from", -1))):
			MessageReceived.emit(msg)


func _bot_join(id: int) -> void:
	_bots[id] = {"name": BOT_NAMES[(id - 1) % BOT_NAMES.size()]}
	_status("A player joined!")
	MemberJoined.emit(id)
	if _bots.size() == 1:
		Connected.emit(true)
	var room := get_node_or_null("/root/OnlineRoom")
	var version: int = room.PROTOCOL if room else 5
	_later(0.2, {"t": "hi", "name": _bots[id]["name"], "v": version, "spec": false, "icon": "", "title": "", "from": id})
	_later(0.3, {"t": "here", "state": "lobby", "from": id})


## A bot message, delivered to the host `seconds` from now (in order).
func _later(seconds: float, msg: Dictionary) -> void:
	var at := _t + seconds
	var i := _events.size()
	while i > 0 and float(_events[i - 1]["at"]) > at:
		i -= 1
	_events.insert(i, {"at": at, "msg": msg})


## A bot reads what the host sent it: the room. It picks when it's one of the two picking, and a match between two
## bots gets a result after a while.
func _bot_hears(id: int, message: Dictionary) -> void:
	if str(message.get("t", "")) != "room":
		return
	var m: Dictionary = message.get("room", {}).get("match", {})
	var state := str(m.get("state", "none"))
	var mid := int(m.get("id", -1))
	var p1 := int(m.get("p1", -1))
	var p2 := int(m.get("p2", -1))
	if state == "picking" and id in [p1, p2]:
		var key := "%d:%d" % [mid, id]
		var mine: Dictionary = m.get("picks", {}).get(str(id), {})
		if not _picked.has(key) and not bool(mine.get("ready", false)):
			_picked[key] = true
			var ms := get_node_or_null("/root/MatchSetup")
			var fighters: int = maxi(1, ms.fighter_count()) if ms else 1
			var assists: int = maxi(1, ms.assist_count()) if ms else 1
			_later(maxf(0.1, float(_fx.fake_pick_seconds)), {"t": "pick", "match": mid, "f": randi() % fighters, "c": 0,
				"a": randi() % assists, "ready": true, "from": id})
	elif state == "fighting" and _bots.has(p1) and _bots.has(p2) and id == p1 and not _decided.has(mid):
		_decided[mid] = true
		_later(maxf(1.0, float(_fx.fake_fight_seconds)), {"t": "result", "match": mid, "side": randi() % 2, "from": p1})


# --- the fight (MatchSetup.start_online_room calls this while the fake room is on) ---

## p: the room's fight (OnlineRoom._start_match). side: 0 / 1 = this computer plays that side, -1 = it watches.
## A local Versus fight: this computer on its side with player 1's controls, the CPU on the other.
func dev_local_fight(p: Dictionary, side: int) -> void:
	var ms := get_node_or_null("/root/MatchSetup")
	if ms == null:
		return
	ms.mode_name = "Versus"
	ms.humans = [side == 0, side == 1]
	ms.assist_picks = [int(p.get("a1", 0)), int(p.get("a2", 0))]
	ms.music_choice = int(p.get("music", ms.MUSIC_AUTO))
	_point_versus_at_lobby(ms)
	print("[DevNet] local fight for match %d (%s): %s" % [int(p.get("match", 0)),
		"you are player %d" % (side + 1) if side >= 0 else "watching: CPU vs CPU", "%s vs %s" % [p.get("n1", "?"), p.get("n2", "?")]])
	ms.start_match(int(p.get("f1", 0)), int(p.get("f2", 0)), 0 if side == 0 else -1, 0 if side == 1 else -1,
		int(p.get("stage", 0)), int(p.get("c1", 0)), int(p.get("c2", 0)), int(p.get("a1", 0)), int(p.get("a2", 0)))


## The Versus results screen's A / B goes back to the mode's ReturnToScene (the character select): for these fights
## it's the lobby, like an online fight. Put back as soon as the lobby is open again.
func _point_versus_at_lobby(ms) -> void:
	var cfg = ms.settings()
	for i in cfg.GameModes.size():
		if str(cfg.GameModes[i].ModeName) == "Versus":
			if _versus_index < 0:
				_versus_index = i
				_versus_return = str(cfg.GameModes[i].ReturnToScene)
			cfg.GameModes[i].ReturnToScene = LOBBY
			return


func _restore_versus_return() -> void:
	if _versus_index < 0:
		return
	var scene := get_tree().current_scene
	if scene == null or scene.scene_file_path != LOBBY:
		return
	var ms := get_node_or_null("/root/MatchSetup")
	if ms:
		ms.settings().GameModes[_versus_index].ReturnToScene = _versus_return
	_versus_index = -1
