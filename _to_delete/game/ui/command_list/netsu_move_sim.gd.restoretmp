class_name NetsuMoveSim
extends RefCounted
## A small stand-in for the fight engine, for the command list's preview (Nov 2 2026): plays a move from the
## fighter's own data against an opponent and records every frame, so the preview shows how the move really
## connects. It reads the same resources the engine plays (states, their events, hitboxes, the stance's hit
## reactions, spawnables), so new moves and changes show up by themselves.
##
## Nov 2 (second pass): follows the engine's frame (GameManager.GameLoop) step by step:
##   PreTick   hitstop / hitstun / knockback timers, knockdown + get-up, frame advance, TransitionEvents
##   Tick      OnTickEvents, then the Netsu holds (EX hold, carry, float)
##   Simulate  movement (position += velocity / 120), hits (counters first), push boxes
##   then      who is on the left (facing for ChangeSideAction)
## and ports the event types and hit rules the four fighters use (SakugaActor.HitDamage / ThrowHit / CounterHit,
## bounces, OTG, the Netsu actions). Not simulated: inputs (a few are pretended: see hold_up / hold_fwd), walls,
## meter, health, blocking, frame properties (invincibility). Units are the engine's: 10000 = 1 metre, y up.
##
## The queue (setup's `states`): ints or {"state": i, "when": ...}. when = "neutral" (default: when she'd go back to
## neutral; a natural move into it counts too), "apex" (in the air, once she starts falling), "cancel" (the parent
## move's cancel window: "mask" = CancelCondition bits, "min" / "max" = frames, "in" = only from that state),
## "after" ("frames" after the previous one started: a held dash let go), "now". "show": true marks the move the row is about (the EX / super pause and the opponent placing start there).

const DEFAULT_GRAVITY := 260000
const LAUNCH_GRAVITY := 200000          # SakugaActor.NetsuLaunchGravity
const AIR_UNTECH_BONUS := 8             # GameManager.NetsuAirUntechBonus
const EX_HOLD_GRACE := 20               # GameManager.NetsuExHoldGraceFrames
const KD_IMPACT := 28                   # GameManager.NetsuKnockdownImpactFrames
const KD_LYING := 22
const KD_GETUP := 22
const GETUP_REACTION := 18              # SakugaActor.NetsuGetUpReaction
const SUPER_HOLD_MAX := 150
const CARRY_RELEASE_HITSTUN := 22
const CARRY_MAX := 45
const CEILING := 250000
const PAUSE_EX := 30                    # GameManager.NetsuPauseExFrames
const PAUSE_SUPER := 60
const BAR := 10000
const SUPER := 30000
const MAX_FRAMES := 600
const TAIL_FRAMES := 24
# StateType / HitstunType / MasterStance / HitboxType / CancelCondition values
const T_COMBAT := 2
const T_BLOCKING := 3
const T_HIT := 4
const HS_BASIC := 1
const HS_KNOCKDOWN := 2
const HS_HARD := 3
const HS_GRABBED := 6
const ON_THE_GROUND := 2
const BOX_HURT := 0
const BOX_HIT := 1
const BOX_PROJECTILE := 3
const BOX_THROW := 4
const BOX_COUNTER := 5
const WHIFF := 1
const HIT := 2
const KARA := 8

## FrameDataEvent scripts are told apart by their file names (C# classes): "MoveXAction" etc.
static var _kind_cache := {}

class Actor:
	var data: Resource
	var states: Array = []
	var stance: Resource
	var state := 0
	var frame := 0
	var pos := Vector2i.ZERO
	var vel := Vector2i.ZERO
	var gravity := DEFAULT_GRAVITY
	var side := 1                 # PlayerSide: the way she faces
	var left := true              # IsLeftSide: left of the other fighter (the game sets it every frame)
	var hitstop := 0
	var hitstun := 0
	var hitstun_type := 0
	var knockback := 0
	var bounce := 0
	var bounce_x := 0
	var bounce_y := 0
	var cancel := WHIFF | KARA    # CancelConditions
	var hit_done := false         # HitBodies holds the opponent
	var active := true
	var fighter := true
	var owner: Actor = null
	var opponent: Actor = null
	var life := 0
	var scale := 1.0
	var flash := 0
	var passive := false
	var queue: Array = []
	var down := 0                 # NetsuDownFrames
	var ex_hold := false
	var ex_state := -1
	var ex_frame := 0
	var ex_age := 0
	var carry := 0
	var float_frame := 0
	var float_total := 0
	var float_rise := 0
	var float_rise_frames := 1
	var orbit := 0
	var grav_decay := 0           # Prorations.GravityDecayFactor: each air hit lifts them 2500 less
	var in_move := false          # the attacker is still in the move being shown (StanceManager.CurrentMove)
	var hold_up := 0              # pretended input: -1 down, 1 up
	var hold_fwd := 0             # pretended input: 1 forward, -1 back

	func cur_state() -> Resource:
		return states[state] if state >= 0 and state < states.size() else null

	func anim() -> Resource:
		var s := cur_state()
		return s.get("AnimationData") if s != null else null

	func duration() -> int:
		var ad := anim()
		return int(ad.get("Duration")) if ad != null and ad.get("Duration") != null else 1

	func state_type() -> int:
		var s := cur_state()
		return int(s.get("Type")) if s != null and s.get("Type") != null else 0

	func base_stance() -> int:
		var s := cur_state()
		return int(s.get("BaseStance")) if s != null and s.get("BaseStance") != null else 0

	func state_name() -> String:
		var s := cur_state()
		return str(s.get("StateName")) if s != null and s.get("StateName") != null else ""

	## PhysicsBody.IsOnGround: at floor height, whatever the speed.
	func on_ground() -> bool:
		return pos.y <= 0

	func lying() -> bool:
		return fighter and on_ground() and state_type() == T_HIT and base_stance() == ON_THE_GROUND

	## SakugaActor.IsAirState
	func air_state() -> bool:
		return not on_ground() or base_stance() == ON_THE_GROUND


var actors: Array = []
var attacker: Actor
var defender: Actor
var frames: Array = []      # recorded: [{"actors": [{ad, frame, pos, side, scale, flash, shake, fighter}], "sparks": [...], "pause": {}}]
var _sparks: Array = []
var spawn_resolver: Callable   # (data: Resource) -> SpawnsList resource or null
## The move the row is about (MoveSettings): its EX / super pause, EX hold. Set by setup's opts.
var move: Resource = null
var move_name := ""
var _pause := 0
var _pause_total := 0
var _pause_super := false
var _pause_state := -1
var _pause_frame := 0
var _shown := false
var _reach := -1
var _def_attack := {}       # the opponent attacks into a counter: {"state", "at"}
var _frame_no := 0
var _starting := false
var _item_age := 0          # frames since the last listed state started (for "after")
## Debugging (tools only): set tracing = true before record() to get one line per frame in `trace`, and every state
## change in `enters` ([who, state index, frame number]; who = "att", "def" or "obj").
var tracing := false
var trace: Array = []
var enters: Array = []


static func _kind(o) -> String:
	if o == null:
		return ""
	var s = o.get_script()
	if s == null:
		return ""
	var path := str(s.resource_path)
	if not _kind_cache.has(path):
		_kind_cache[path] = path.get_file().get_basename()
	return _kind_cache[path]


static func _g(o, key: String, fallback = null):
	if o == null:
		return fallback
	var v = o.get(key)
	return fallback if v == null else v


static func _actor(data: Resource) -> Actor:
	var a := Actor.new()
	a.data = data
	a.states = _g(data, "States", [])
	var stances: Array = _g(data, "Stances", [])
	a.stance = stances[0] if not stances.is_empty() else null
	a.scale = float(_g(data, "NetsuScale", 1000)) / 1000.0
	if a.scale <= 0.0:
		a.scale = 1.0
	return a


static func _item_state(item) -> int:
	return int(item["state"]) if item is Dictionary else int(item)


## Sets up the attacker (playing the queue `states`) and an opponent standing in front of her, in reach of the move's
## first attack box. air = start in the air (falling from 1.4 m). opts: "move" (MoveSettings of the shown move),
## "name", "hold_up" / "hold_fwd" (inputs she holds: MoveX / MoveY with UseInput).
func setup(att_data: Resource, states: Array, def_data: Resource, air: bool = false, distance: int = -1, att_x: int = 0, opts: Dictionary = {}) -> void:
	actors.clear()
	frames.clear()
	_sparks.clear()
	move = opts.get("move", null)
	move_name = str(opts.get("name", ""))
	attacker = _actor(att_data)
	attacker.side = 1
	attacker.left = true
	attacker.pos = Vector2i(att_x, 14000 if air else 0)
	attacker.hold_up = int(opts.get("hold_up", 0))
	attacker.hold_fwd = int(opts.get("hold_fwd", 0))
	var queue: Array = []
	for it in states:
		queue.append((it as Dictionary).duplicate() if it is Dictionary else {"state": int(it)})
	var shown_i := 0
	for i in queue.size():
		if queue[i].get("show", false):
			shown_i = i
	_reach = distance if distance > 0 else _start_distance([_item_state(queue[shown_i])] if not queue.is_empty() else [])
	if def_data != null:
		defender = _actor(def_data)
		defender.side = -1
		defender.left = false
		defender.pos = Vector2i(att_x + _reach, 0)
		defender.opponent = attacker
		attacker.opponent = defender
		actors.append(defender)
		_play(defender, 0)
		_plan_counter(queue, shown_i)
	actors.append(attacker)
	if queue.is_empty():
		return
	queue[shown_i]["show"] = true
	attacker.queue = queue.slice(1)
	_start_item(queue[0])


## Someone who just stands there playing a state (an assist's caller in her call pose): drawn, never hits.
func add_extra(data: Resource, state: int, pos: Vector2i, side: int = 1) -> void:
	var a := _actor(data)
	a.side = side
	a.left = side > 0
	a.pos = pos
	a.passive = true
	actors.insert(0, a)
	_play(a, state)


## How far apart they start: so the move's first attack box reaches the opponent's front (between 0.75 and 3 m).
func _start_distance(states: Array) -> int:
	for s in states:
		if s < 0 or s >= attacker.states.size() or attacker.states[s] == null:
			continue
		var ad = _g(attacker.states[s], "AnimationData")
		for key in _g(ad, "Hitboxes", []):
			for el in _g(_g(key, "HitboxData"), "Hitboxes", []):
				var t := int(_g(el, "HitboxType", 0))
				if t == BOX_HIT or t == BOX_PROJECTILE or t == BOX_THROW:
					var c: Vector2i = _g(el, "Center", Vector2i.ZERO)
					var sz: Vector2i = _g(el, "Size", Vector2i.ZERO)
					return clampi(c.x + sz.x / 2 - 2500, 5500, 30000)
	return 16000


## A counter (the shown move has COUNTER boxes): the opponent attacks into it (her 5C, else 5B, else 5A), timed to
## arrive a few frames into the counter window and placed where it reaches.
func _plan_counter(queue: Array, shown_i: int) -> void:
	_def_attack = {}
	if queue.is_empty():
		return
	var st := _item_state(queue[shown_i])
	var start := _box_frame(attacker, st, BOX_COUNTER)
	if start < 0:
		return
	var moves: Array = _g(defender.stance, "Moves", [])
	var pick = null
	for want in ["5C", "5B", "5A"]:
		for m in moves:
			if m != null and str(_g(m, "MoveName", "")) == want:
				pick = m
				break
		if pick != null:
			break
	if pick == null:
		return
	var ds := int(_g(pick, "MoveState", -1))
	var startup := _box_frame(defender, ds, BOX_HIT)
	if startup < 0:
		return
	var pause := _pause_length() if _flash_at_start() else 0
	_def_attack = {"state": ds, "at": maxi(0, shown_i + pause + start + 3 - startup)}
	# close enough for her attack to reach the counter box
	var reach := 9000
	var ad = _g(defender.states[ds], "AnimationData")
	for key in _g(ad, "Hitboxes", []):
		for el in _g(_g(key, "HitboxData"), "Hitboxes", []):
			if el != null and int(_g(el, "HitboxType", 0)) == BOX_HIT:
				var c: Vector2i = _g(el, "Center", Vector2i.ZERO)
				var sz: Vector2i = _g(el, "Size", Vector2i.ZERO)
				reach = maxi(reach, c.x + sz.x / 2)
	_reach = clampi(reach - 2500, 6000, 26000)
	defender.pos.x = attacker.pos.x + _reach


## First frame a state's AnimationData has a box of this type (-1 if never).
func _box_frame(a: Actor, st: int, box_type: int) -> int:
	if st < 0 or st >= a.states.size() or a.states[st] == null:
		return -1
	var ad = _g(a.states[st], "AnimationData")
	for key in _g(ad, "Hitboxes", []):
		for el in _g(_g(key, "HitboxData"), "Hitboxes", []):
			if el != null and int(_g(el, "HitboxType", 0)) == box_type:
				return int(_g(key, "AtFrame", 0))
	return -1


func _flash_at_start() -> bool:
	return move != null and int(_g(move, "SuperFlash", 0)) > 0 and not bool(_g(move, "NetsuFlashOnHit", false)) \
		and int(_g(move, "SuperGaugeRequired", 0)) >= BAR


func _pause_length() -> int:
	var f := int(_g(move, "NetsuPauseFrames", -1)) if move != null else -1
	if f >= 0:
		return f
	return PAUSE_SUPER if int(_g(move, "SuperGaugeRequired", 0)) >= SUPER else PAUSE_EX


func _start_item(item: Dictionary) -> void:
	if item.get("show", false):
		_show_starts()
	_item_age = 0
	_starting = true   # a listed state started on purpose isn't "back to neutral" (a dash is a movement state)
	_play(attacker, int(item["state"]))
	_starting = false


## The shown move starts: the opponent is put in its reach (if she's just standing there) and an EX / super stops
## the fight first (GameManager.NetsuStartPause), the fighter's pause pose playing if the move has one.
func _show_starts() -> void:
	if _shown:
		return
	_shown = true
	attacker.in_move = true
	if defender != null and defender.state_type() <= 1 and _def_attack.is_empty():
		defender.pos.x = attacker.pos.x + _reach * attacker.side
		defender.left = defender.pos.x < attacker.pos.x
		defender.side = 1 if defender.left else -1
	if _flash_at_start():
		_start_pause(_pause_length(), int(_g(move, "SuperGaugeRequired", 0)) >= SUPER, int(_g(move, "NetsuPauseState", -1)))
		if int(_g(move, "SuperGaugeRequired", 0)) >= SUPER:
			attacker.vel = Vector2i.ZERO   # a super stops her where it starts


func _start_pause(n: int, is_super: bool, pose: int = -1) -> void:
	if n <= 0:
		return
	_pause = n
	_pause_total = n
	_pause_super = is_super
	_pause_state = pose
	_pause_frame = 0


func _play(a: Actor, state: int, reset: bool = true) -> void:
	if state < 0 or state >= a.states.size() or a.states[state] == null:
		return
	if a == attacker and not a.queue.is_empty() and not _starting:
		var next: Dictionary = a.queue[0]
		var t := int(_g(a.states[state], "Type", 0))
		if state == int(next["state"]):
			a.queue.pop_front()   # she got there by herself
			if next.get("show", false):
				_show_starts()
		elif t <= 1 and str(next.get("when", "neutral")) == "neutral":
			a.queue.pop_front()   # back to neutral: the next listed move instead
			state = int(next["state"])
			if next.get("show", false):
				_show_starts()
	if a == attacker and a.in_move and int(_g(a.states[state], "Type", 0)) <= 1 and a.queue.is_empty():
		a.in_move = false
	_run_events(a, _g(a.cur_state(), "OnExitEvents", []))
	if tracing:
		enters.append(["att" if a == attacker else ("def" if a == defender else "obj"), state, _frame_no])
	if a.state != state or reset:
		a.frame = 0
	a.state = state
	a.hit_done = false
	a.cancel = WHIFF | KARA
	_run_events(a, _g(a.cur_state(), "OnEnterEvents", []))


# --- Events ----------------------------------------------------------------------------------

func _run_events(a: Actor, events) -> void:
	if events == null:
		return
	for ev in events:
		if ev == null or not a.active:
			continue
		var actions: Array = _g(ev, "Actions", [])
		var ok := true
		for c in _g(ev, "Conditions", []):
			if c != null and not _check(a, c, actions):
				ok = false
				break
		if not ok:
			continue
		for act in actions:
			if act != null:
				_act(a, act)


## True when this event's actions play the next state she's queued for (an input check before it counts as pressed).
func _leads_to_queue(a: Actor, actions: Array) -> bool:
	if a != attacker or a.queue.is_empty():
		return false
	var want := int(a.queue[0]["state"])
	for act in actions:
		if act != null and _kind(act) == "PlayStateAction" and _state_of(a, act) == want:
			return true
	return false


func _state_of(a: Actor, act) -> int:
	var idx := int(_g(act, "StateIndex", -1))
	if idx < 0:
		var want := str(_g(act, "StateName", ""))
		for i in a.states.size():
			if a.states[i] != null and str(_g(a.states[i], "StateName", "")) == want:
				return i
	return idx


static func _compare(v: int, mode: int, value: int) -> bool:
	match mode:   # CompareMode: EQUAL, DIFFERENT, GREATER, GREATER_EQUAL, LESS, LESS_EQUAL
		0: return v == value
		1: return v != value
		2: return v > value
		3: return v >= value
		4: return v < value
		5: return v <= value
	return false


func _target_x(a: Actor, rel: int) -> int:
	match rel:   # RelativeTo: WORLD, SELF, OPPONENT, FIGHTER
		1: return a.pos.x
		2: return a.opponent.pos.x if a.opponent != null else 0
		3: return a.owner.pos.x if a.owner != null else a.pos.x
	return 0


func _target_y(a: Actor, rel: int) -> int:
	match rel:
		1: return a.pos.y
		2: return a.opponent.pos.y if a.opponent != null else 0
		3: return a.owner.pos.y if a.owner != null else a.pos.y
	return 0


## SakugaActor.GenerateTargetPosition
func _gen_target(a: Actor, target: Vector2i, index: int, rx: int, ry: int) -> Vector2i:
	var x := 0
	var y := 0
	var opp := a.opponent
	match rx:
		1:
			x = a.pos.x
			target.x *= a.side
		2:
			if opp != null:
				x = opp.pos.x
				target.x *= opp.side
		3:
			if index == 1 and opp != null:
				x = opp.pos.x
				target.x *= opp.side
			else:
				x = a.pos.x
				target.x *= a.side
	match ry:
		1:
			y = a.pos.y
		2:
			y = opp.pos.y if opp != null else 0
		3:
			y = opp.pos.y if index == 1 and opp != null else a.pos.y
	return Vector2i(target.x + x, target.y + y)


func _check(a: Actor, c, actions: Array) -> bool:
	var no := bool(_g(c, "Not", false))
	var r := false
	match _kind(c):
		"AtFrameCondition":
			var f := int(_g(c, "Frame", 0))
			var m := int(_g(c, "Modulo", 0))
			r = (a.frame % m == f) if m > 0 else a.frame == f
		"AtFrameRangeCondition":
			r = a.frame >= int(_g(c, "MinFrame", 0)) and a.frame <= int(_g(c, "MaxFrame", 0))
			return (not r) if no else r
		"StateEndedCondition":
			r = a.frame >= a.duration()
		"OnGroundCondition":
			r = a.on_ground()
		"IsFallingCondition":
			r = not a.on_ground() and a.vel.y <= 0
		"CheckHitCondition":
			r = (a.cancel & int(_g(c, "HitCheck", HIT))) != 0
		"OnKnockbackCondition":
			r = a.knockback > 0
		"OnHitstunCondition":
			r = a.hitstun > 0
		"OnHitstopCondition":
			r = a.hitstop > 0
		"RoundRunningCondition":
			r = true
		"CheckInputCondition":
			r = _leads_to_queue(a, actions)   # she presses what leads to the next listed move, nothing else
		"CanBounceGroundCondition":
			r = a.bounce > 0 and a.bounce_y > 0
		"CanBounceWallCondition":
			r = a.bounce > 0 and a.bounce_x > 0
		"CanBounceCondition":
			var by := a.bounce > 0 and a.bounce_y > 0
			var bx := a.bounce > 0 and a.bounce_x > 0
			var gb := bool(_g(c, "GroundBounce", false)) and (by if no else not by)
			var wb := bool(_g(c, "WallBounce", false)) and (bx if no else not bx)
			return gb or wb
		"CheckXVelocityCondition":
			var vx := absi(a.vel.x) if bool(_g(c, "Absolute", false)) else a.vel.x
			r = _compare(vx, int(_g(c, "CompareMode", 0)), int(_g(c, "Value", 0)))
		"CheckYVelocityCondition":
			var vy := absi(a.vel.y) if bool(_g(c, "Absolute", false)) else a.vel.y
			r = _compare(vy, int(_g(c, "CompareMode", 0)), int(_g(c, "Value", 0)))
		"CheckHealthCondition":
			r = _compare(int(_g(a.data, "MaxHealth", 10000)), int(_g(c, "CompareMode", 0)), int(_g(c, "Value", 0)))
		"NetsuRelativeXCondition":
			var d := (a.pos.x - _target_x(a, int(_g(c, "Target", 2)))) * a.side
			r = d >= int(_g(c, "MinDistance", -1000000)) and d <= int(_g(c, "MaxDistance", 1000000))
		"CheckDistanceCondition":
			var rel := int(_g(c, "RelativeTo", 0))
			var tp := _gen_target(a, Vector2i.ZERO, int(_g(c, "Index", 0)), rel, rel)
			var dist := absi(a.pos.x - tp.x)
			if no:
				return dist < int(_g(c, "MinDistance", 0)) or dist > int(_g(c, "MaxDistance", 0))
			return dist >= int(_g(c, "MinDistance", 0)) and dist <= int(_g(c, "MaxDistance", 0))
		"NetsuOpponentHitReactionCondition":
			r = a.opponent != null and a.opponent.state_type() == T_HIT
		"NetsuOpponentOnGroundCondition":
			r = a.opponent != null and a.opponent.on_ground()
		_:
			r = false   # walls, side-change inputs, Overdrive, timers...: never true here
	return (not r) if no else r


func _act(a: Actor, act) -> void:
	match _kind(act):
		"PlayStateAction":
			_play(a, _state_of(a, act), bool(_g(act, "Reset", true)))
		"MoveXAction":
			if a.knockback > 0:
				return
			var dir := a.side
			if bool(_g(act, "UseInput", false)):
				dir = a.hold_fwd * a.side   # RIGHT / LEFT held (screen directions)
			var v := int(_g(act, "Velocity", 0)) * dir
			a.vel.x = _accelerate(a.vel.x, v) if bool(_g(act, "UseInertia", false)) else v
		"MoveYAction":
			if a.knockback > 0:
				return
			var v := int(_g(act, "Velocity", 0))
			if bool(_g(act, "UseInput", false)):
				v *= a.hold_up
			a.vel.y = _accelerate(a.vel.y, v) if bool(_g(act, "UseInertia", false)) else v
		"AddGravityAction":
			if bool(_g(act, "SetValue", false)):
				a.gravity = DEFAULT_GRAVITY if bool(_g(act, "UseDefault", false)) else int(_g(act, "Force", DEFAULT_GRAVITY))
			a.vel.y -= a.gravity / 60
		"GoToFrameActions":
			a.frame = int(_g(act, "Frame", 0))
		"ResetHitAction":
			a.hit_done = false
		"StopKnockbackAction":
			if not bool(_g(act, "KeepXVelocity", false)):
				a.vel.x = 0
			a.knockback = 0
		"ChangeSideAction":
			if bool(_g(act, "Forced", false)):
				a.left = not a.left
			a.side = 1 if a.left else -1
		"BounceXAction":
			if bool(_g(act, "CustomIntensity", false)):
				a.bounce_x = int(_g(act, "Intensity", 0))
			a.vel.x = a.vel.x * -a.bounce_x / 100
			a.bounce_x = 0
			a.bounce = 0
		"BounceYAction":
			if bool(_g(act, "CustomIntensity", false)):
				a.bounce_y = int(_g(act, "Intensity", 0))
			a.vel.y = a.vel.y * -a.bounce_y / 100
			a.bounce_y = 0
			a.bounce = 0
		"TeleportAction":
			_move_to(a, _gen_target(a, _g(act, "TargetPosition", Vector2i.ZERO), int(_g(act, "Index", 0)),
				int(_g(act, "xRelativeTo", 0)), int(_g(act, "yRelativeTo", 0))))
		"SetActiveAction":
			if not bool(_g(act, "Active", true)) and not a.fighter:
				a.active = false
		"SpawnActorAction":
			_spawn(a, act)
		"NetsuPlaceAction":
			var off: Vector2i = _g(act, "Offset", Vector2i.ZERO)
			var tgt := int(_g(act, "Target", 2))
			var px := _target_x(a, tgt) + off.x * a.side
			var py := a.pos.y if bool(_g(act, "KeepHeight", true)) else _target_y(a, tgt) + off.y
			_move_to(a, Vector2i(px, maxi(0, py)))
			if bool(_g(act, "FaceBack", false)):
				a.left = a.side < 0
				a.side = 1 if a.left else -1
		"NetsuSkyRiseAction":
			var vy := int(_g(act, "Velocity", 0))
			if vy != 0:
				a.vel.y = vy
			var gy := int(_g(act, "Gravity", 0))
			if gy != 0:
				a.vel.y -= gy / 60
		"NetsuSlideToAction":
			var o := a.opponent
			if o != null:
				var target := o.pos.x + int(_g(act, "Offset", 9000)) * a.side
				var step := maxi(1, int(_g(act, "Step", 5000)))
				var sx := mini(target, a.pos.x + step) if a.pos.x < target else maxi(target, a.pos.x - step)
				a.vel = Vector2i(0, a.vel.y)
				_move_to(a, Vector2i(sx, a.pos.y))
		"NetsuOrbitAction":
			var o := a.opponent
			if o != null:
				if bool(_g(act, "Start", false)) or a.orbit == 0:
					a.orbit = -1 if a.pos.x <= o.pos.x else 1
				var off: Vector2i = _g(act, "Offset", Vector2i.ZERO)
				var ox := o.pos.x + off.x * a.orbit
				var oy := clampi(o.pos.y + off.y, 0, CEILING)
				a.vel = Vector2i.ZERO
				_move_to(a, Vector2i(ox, oy))
				if ox != o.pos.x:
					a.left = ox < o.pos.x
					a.side = 1 if a.left else -1
		"NetsuPushOpponentAction":
			var o := a.opponent
			var dist := int(_g(act, "Distance", 2000))
			if o != null and dist > 0:
				var dir := 1 if o.pos.x > a.pos.x else (-1 if o.pos.x < a.pos.x else a.side)
				_move_to(o, Vector2i(o.pos.x + dist * dir, o.pos.y))
		"NetsuPullOpponentAction":
			var o := a.opponent
			if o != null and o.hitstun_type != HS_GRABBED:
				var dx := a.pos.x - o.pos.x
				if absi(dx) <= int(_g(act, "Radius", 30000)):
					var step := mini(absi(dx), maxi(int(_g(act, "Speed", 500)), 0))
					var ly := o.pos.y
					var rate := int(_g(act, "LiftRate", 0))
					if rate > 0:
						ly = o.pos.y + (int(_g(act, "Lift", 0)) - o.pos.y) * clampi(rate, 1, 1000) / 1000
					_move_to(o, Vector2i(o.pos.x + (step if dx > 0 else -step), clampi(ly, 0, CEILING)))
		"NetsuBounceOpponentAction":
			_bounce_opponent(a, act)
		"NetsuFreezeOpponentAction":
			if a.opponent != null and int(_g(act, "Frames", 20)) > 0:
				a.opponent.hitstop = int(_g(act, "Frames", 20))
		"NetsuRestandAction":
			var o := a.opponent
			if o != null and not o.on_ground():
				o.knockback = 0
				o.vel = Vector2i.ZERO
				o.pos.y = 0
		"NetsuHitstopAction":
			var self_stop := int(_g(act, "Self", -1))
			if self_stop >= 0:
				a.hitstop = self_stop
			var opp_stop := int(_g(act, "Opponent", -1))
			if opp_stop >= 0 and a.opponent != null and a.opponent.state_type() == T_HIT:
				a.opponent.hitstop = opp_stop
		"NetsuSuperFlashAction":
			# a move that flashes on hit (a counter super): the pause starts here
			if a == attacker or a.owner == attacker:
				var n := int(_g(act, "Frames", 20))
				if bool(_g(act, "CutIn", true)) and move != null and int(_g(move, "SuperGaugeRequired", 0)) >= BAR:
					n = _pause_length()
				_start_pause(n, move != null and int(_g(move, "SuperGaugeRequired", 0)) >= SUPER)
		"NetsuHoldOpponentAction":
			var o := a.opponent
			if o != null and o.state_type() == T_HIT:
				var off: Vector2i = _g(act, "Offset", Vector2i(6000, 10000))
				var rate := int(_g(act, "LiftRate", 0))
				var hx: int
				var hy: int
				if rate > 0:
					hx = o.pos.x
					hy = o.pos.y + (off.y - o.pos.y) * clampi(rate, 1, 1000) / 1000
				else:
					var me := a.pos + (a.vel / 120 * 2 if a.hitstop <= 0 else Vector2i.ZERO)
					hx = me.x + off.x * a.side
					hy = me.y + off.y
				o.vel = Vector2i.ZERO
				_move_to(o, Vector2i(hx, clampi(hy, 0, CEILING)))
		"NetsuMoveOpponentAction":
			var o := a.opponent
			if o != null:
				var target := a.pos.x + int(_g(act, "X", -7000)) * a.side
				_move_to(o, Vector2i(target, o.pos.y))
				if bool(_g(act, "TurnAround", true)) and target != a.pos.x:
					a.left = a.pos.x < target
					a.side = 1 if a.left else -1
					o.left = target < a.pos.x
					o.side = 1 if o.left else -1
		"NetsuDamageOpponentAction":
			var o := a.opponent
			if o != null and o.state_type() == T_HIT:
				var hs := int(_g(act, "Hitstop", 16))
				o.hitstop = hs
				a.hitstop = hs
				o.flash = 6
				_sparks.append({"pos": o.pos + Vector2i(0, 9000), "age": 0, "big": true})
		_:
			pass


## PhysicsBody.MoveTo (fighters stay between the floor and the ceiling).
func _move_to(a: Actor, p: Vector2i) -> void:
	a.pos = p
	if a.fighter:
		a.pos.y = clampi(a.pos.y, 0, CEILING)


func _bounce_opponent(a: Actor, act) -> void:
	var o := a.opponent
	if o == null or o.lying() or o.state_type() != T_HIT or o.hitstun_type == HS_GRABBED:
		return
	var ht := int(_g(act, "HitstunType", -1))
	if ht >= 0:
		o.hitstun_type = ht
	var kb: Vector2i = _g(act, "Knockback", Vector2i.ZERO)
	var reactions = _g(o.stance, "HitReactions", [])
	var pop := int(_g(act, "GroundedPopVelocity", 0))
	var by := int(_g(act, "BounceY", 0))
	if pop > 0 and by > 0 and o.on_ground():
		if int(_g(act, "Hitstun", 0)) > 0:
			o.hitstun = int(_g(act, "Hitstun", 0))
		var gr := int(_g(act, "GroundedHitReaction", 8))
		if gr >= 0 and reactions.size() > 0:
			_play(o, int(reactions[clampi(gr, 0, reactions.size() - 1)]))
		o.pos.y += 1500
		_push(o, int(_g(act, "KnockbackTime", 8)), kb.x * -a.side, pop, int(_g(act, "KnockbackGravity", LAUNCH_GRAVITY)))
		o.bounce = 0
		return
	if int(_g(act, "Hitstun", 0)) > 0:
		o.hitstun = int(_g(act, "Hitstun", 0))
	var hr := int(_g(act, "HitReaction", -1))
	if hr >= 0 and reactions.size() > 0:
		_play(o, int(reactions[clampi(hr, 0, reactions.size() - 1)]))
	if kb != Vector2i.ZERO:
		_push(o, int(_g(act, "KnockbackTime", 8)), kb.x * -a.side, kb.y, int(_g(act, "KnockbackGravity", LAUNCH_GRAVITY)))
	o.bounce = maxi(int(_g(act, "BounceTime", 120)), 1)
	o.bounce_x = int(_g(act, "BounceX", 0))
	o.bounce_y = by


## SakugaActor.PushActor
func _push(o: Actor, time: int, vx: int, vy: int, gravity: int) -> void:
	o.vel = Vector2i(vx, vy)
	o.gravity = gravity
	o.knockback = time


## PhysicsBody.AddLateralAcceleration / AddVerticalAcceleration.
static func _accelerate(cur: int, target: int) -> int:
	if target > 0:
		if cur < 0:
			return cur + 6666
		if cur < target:
			return mini(cur + 6000, target)
		return target
	if target < 0:
		if cur > 0:
			return cur - 6666
		if cur > target:
			return maxi(cur - 6000, target)
		return target
	return cur - mini(absi(cur), 4166) * signi(cur)


func _spawn(a: Actor, act) -> void:
	if not spawn_resolver.is_valid():
		return
	var owner_data := a.data if a.fighter else a.owner.data
	var list = spawn_resolver.call(owner_data)
	var objs: Array = _g(list, "SpawnObjects", [])
	var idx := int(_g(act, "Index", -1))
	var key := str(_g(act, "Key", ""))
	var obj = null
	if idx >= 0 and idx < objs.size():
		obj = objs[idx]
	elif key != "":
		for o in objs:
			if o != null and str(_g(o, "Key", "")) == key:
				obj = o
	if obj == null:
		return
	var data := _scene_data(_g(obj, "Instance"))
	if data == null:
		return
	var s := _actor(data)
	s.fighter = false
	s.scale = 1.0   # the engine only scales fighters (SakugaActor.Render: NetsuScale when GetMaster() == null)
	s.owner = a if a.fighter else a.owner
	s.opponent = s.owner.opponent
	s.side = a.side
	s.left = a.side > 0
	s.pos = _gen_target(a, _g(act, "TargetPosition", Vector2i.ZERO), int(_g(act, "Index", 0)),
		int(_g(act, "xRelativeTo", 1)), int(_g(act, "yRelativeTo", 1)))
	actors.append(s)
	_play(s, int(_g(act, "InitialState", 0)))


## The DataContainer of a spawnable's scene (its root's Data), read without making the scene.
static func _scene_data(scene) -> Resource:
	if scene == null or not scene is PackedScene:
		return null
	var st: SceneState = scene.get_state()
	for p in st.get_node_property_count(0):
		if st.get_node_property_name(0, p) == "Data":
			return st.get_node_property_value(0, p)
	return null


# --- Boxes and hits --------------------------------------------------------------------------

static func _settings_at(ad, frame: int):
	var cur = null
	for key in _g(ad, "Hitboxes", []):
		if key == null:
			continue
		if int(_g(key, "AtFrame", 0)) <= frame:
			cur = key
		else:
			break
	return _g(cur, "HitboxData") if cur != null else null


static func _box_rect(a: Actor, el) -> Rect2i:
	var c: Vector2i = _g(el, "Center", Vector2i.ZERO)
	var s: Vector2i = _g(el, "Size", Vector2i.ZERO)
	var cx := a.pos.x + c.x * a.side
	return Rect2i(cx - s.x / 2, a.pos.y + c.y - s.y / 2, s.x, s.y)


func _boxes(a: Actor, types: Array) -> Array:
	var out: Array = []
	var hs = _settings_at(a.anim(), a.frame)
	for el in _g(hs, "Hitboxes", []):
		if el != null and int(_g(el, "HitboxType", 0)) in types:
			out.append([el, _box_rect(a, el)])
	return out


func _try_hits(a: Actor) -> void:
	var target := a.opponent
	if target == null or a.hit_done or a.hitstop > 0 or not a.active:
		return
	var attacks := _boxes(a, [BOX_HIT, BOX_PROJECTILE, BOX_THROW])
	if attacks.is_empty():
		return
	var hurt := _boxes(target, [BOX_HURT])
	if hurt.is_empty():
		return
	for at in attacks:
		for h in hurt:
			var r: Rect2i = at[1]
			var hr: Rect2i = h[1]
			if r.intersects(hr):
				if int(_g(at[0], "HitboxType", 1)) == BOX_THROW:
					_throw(a, target, at[0])
				else:
					_hit(a, target, at[0], r.intersection(hr))
				return


## The opponent's attack touching a COUNTER box of the attacker (or of something she spawned).
func _try_counter(d: Actor) -> void:
	if d.hit_done or d.hitstop > 0:
		return
	var attacks := _boxes(d, [BOX_HIT])
	if attacks.is_empty():
		return
	for c in actors:
		if c == d or not c.active or c.passive:
			continue
		for cb in _boxes(c, [BOX_COUNTER]):
			for at in attacks:
				var r: Rect2i = at[1]
				var cr: Rect2i = cb[1]
				if r.intersects(cr):
					# SakugaActor.CounterHit: both stop; the counter's on-hit events play its strike
					d.hit_done = true
					d.hitstop = int(_g(cb[0], "OpponentHitStopDuration", 12))
					var contact := r.intersection(cr)
					_sparks.append({"pos": Vector2i(contact.position.x + contact.size.x / 2, contact.position.y + contact.size.y / 2), "age": 0, "big": true})
					_confirm(c, d, int(_g(cb[0], "SelfHitStopDuration", 12)))
					return


## SakugaActor.HitConfirm: hitstop, on-hit events; a switch to another state gets a fresh hit.
func _confirm(a: Actor, target: Actor, stop: int) -> void:
	a.hitstop = stop
	a.cancel |= HIT
	var before_state := a.state
	var before_frame := a.frame
	_run_events(a, _g(a.cur_state(), "OnHitConfirmEvents", []))
	var switched := a.state != before_state or a.frame < before_frame
	a.hit_done = not switched


func _root(a: Actor) -> Actor:
	return a if a.fighter else a.owner


func _hit(a: Actor, target: Actor, box, contact: Rect2i) -> void:
	var root := _root(a)
	var spark := {"pos": Vector2i(contact.position.x + contact.size.x / 2, contact.position.y + contact.size.y / 2), "age": 0,
		"big": int(_g(box, "BaseDamage", 0)) >= 700}
	if target.lying():
		# OTG: inside the window it's damage only (no reaction); supers can't hit them there; past it they're invincible
		var is_super := move != null and root == attacker and int(_g(move, "SuperGaugeRequired", 0)) >= SUPER
		if is_super or target.down > KD_IMPACT + KD_LYING:
			return
		a.hit_done = true
		target.hitstop = int(_g(box, "OpponentHitStopDuration", 12))
		target.flash = 5
		_sparks.append(spark)
		a.hitstop = int(_g(box, "SelfHitStopDuration", 12))
		return
	var juggled := target.state_type() == T_HIT and target.hitstun_type in [HS_KNOCKDOWN, HS_HARD] \
		and not bool(_g(box, "NetsuAllowRestand", false))
	var ground := not target.air_state() and not juggled
	var stun := int(_g(box, "GroundHitstun" if ground else "AirHitstun", 12))
	if not ground:
		stun += AIR_UNTECH_BONUS
	target.hitstun = maxi(stun, 8 if ground else 1)
	target.hitstun_type = int(_g(box, "GroundHitstunType" if ground else "AirHitstunType", HS_BASIC))
	if juggled and target.hitstun_type < HS_KNOCKDOWN:
		target.hitstun_type = HS_KNOCKDOWN
	if bool(_g(box, "NetsuSoftKnockdown", false)):
		target.hitstun_type = HS_BASIC
	var reaction := int(_g(box, "GroundHitReaction" if ground else "AirHitReaction", 0))
	if ground and target.base_stance() == 1:
		reaction = int(_g(box, "CrouchHitReaction", reaction))
	var kb: Vector2i = _g(box, "GroundHitKnockback" if ground else "AirHitKnockback", Vector2i.ZERO)
	var kbt := int(_g(box, "GroundHitKnockbackTime" if ground else "AirHitKnockbackTime", 8))
	var grav := int(_g(box, "GroundHitKnockbackGravity" if ground else "AirHitKnockbackGravity", 0))
	if grav <= 0 and (kb.y > 0 or not target.on_ground()):
		grav = LAUNCH_GRAVITY
	# she turns to face whoever hit her
	target.left = not a.left
	target.side = 1 if target.left else -1
	target.hitstop = int(_g(box, "OpponentHitStopDuration", 12))
	var reactions = _g(target.stance, "HitReactions", [])
	if reactions.size() > 0:
		_play(target, int(reactions[clampi(reaction, 0, reactions.size() - 1)]))
	_push(target, kbt, kb.x * -a.side, kb.y - 2500 * target.grav_decay, grav if grav > 0 else target.gravity)
	if target.air_state():
		target.grav_decay += 1
	target.flash = 5
	# float (Leticia's j.236) / carry (Flan's rising Star Rush) / EX hold
	target.float_frame = 0
	if int(_g(box, "NetsuFloatFrames", 0)) > 0 and (not target.on_ground() or bool(_g(box, "NetsuFloatFromGround", false))):
		target.float_frame = 1
		target.float_total = int(_g(box, "NetsuFloatFrames", 0))
		target.float_rise = maxi(0, int(_g(box, "NetsuFloatRise", 0)))
		target.float_rise_frames = clampi(int(_g(box, "NetsuFloatRiseFrames", 1)), 1, 63)
	target.carry = 1 if bool(_g(box, "NetsuCarryUp", false)) and a.fighter else 0
	target.ex_hold = false
	if root == attacker and attacker.in_move and move != null:
		var cost := int(_g(move, "SuperGaugeRequired", 0))
		if cost >= BAR and cost < SUPER and not str(_g(move, "MoveName", "")).contains("Pushblock"):
			target.ex_hold = true
			target.ex_state = attacker.state
			target.ex_frame = attacker.frame
			target.ex_age = 0
	if int(_g(box, "BounceTime", 0)) > 0:
		target.bounce = int(_g(box, "BounceTime", 0))
		target.bounce_x = int(_g(box, "BounceXIntensity", 0))
		target.bounce_y = int(_g(box, "BounceYIntensity", 0))
	else:
		target.bounce = 0
		target.bounce_x = 0
		target.bounce_y = 0
	_sparks.append(spark)
	var self_stop := int(_g(box, "SelfHitStopDuration", 12))
	if not a.fighter and a.owner != null and int(_g(box, "HitboxType", 1)) != BOX_PROJECTILE:
		a.owner.hitstop = self_stop
	_confirm(a, target, self_stop)


## SakugaActor.ThrowDamage / ThrowHit: grabbed (frozen for the throw's hitstop), the throw reaction; the thrower's
## on-hit events play the throw.
func _throw(a: Actor, target: Actor, box) -> void:
	if target.state_type() == T_HIT or target.lying():
		return
	var stop := int(_g(box, "ThrowHitstop", 12))
	target.hitstun_type = HS_GRABBED
	target.left = not a.left
	target.side = 1 if target.left else -1
	target.hitstop = stop
	var reactions = _g(target.stance, "HitReactions", [])
	if reactions.size() > 0:
		_play(target, int(reactions[clampi(int(_g(box, "ThrowHitReaction", 0)), 0, reactions.size() - 1)]))
	_confirm(a, target, stop)


# --- Running ---------------------------------------------------------------------------------

func _push_apart() -> void:
	if defender == null:
		return
	var pa = _g(_settings_at(attacker.anim(), attacker.frame), "Pushbox")
	var pd = _g(_settings_at(defender.anim(), defender.frame), "Pushbox")
	if pa == null or pd == null or defender.hitstun_type == HS_GRABBED:
		return
	var ra := _box_rect(attacker, pa)
	var rd := _box_rect(defender, pd)
	if not ra.intersects(rd):
		return
	var overlap := mini(ra.end.x, rd.end.x) - maxi(ra.position.x, rd.position.x)
	if overlap <= 0:
		return
	var dir := 1 if defender.pos.x >= attacker.pos.x else -1
	attacker.pos.x -= dir * overlap / 2
	defender.pos.x += dir * (overlap - overlap / 2)


## The knockdown counter, get-up and "stay down" (SakugaActor.NetsuKnockdownTick / NetsuGetUpWhenDue /
## NetsuKeepLying). Returns true while the lying animation holds its last frames.
func _knockdown(a: Actor) -> bool:
	if not a.fighter or a == attacker or a.passive:
		return false
	var getup := -1
	var reactions = _g(a.stance, "HitReactions", [])
	if reactions.size() > GETUP_REACTION:
		getup = int(reactions[GETUP_REACTION])
	if a.lying():
		a.down += 1
	elif a.down > 0 and ((a.state_type() == T_HIT and a.base_stance() == ON_THE_GROUND) or a.state == getup):
		a.down += 1
	else:
		a.down = 0
	var limit := KD_IMPACT + KD_LYING
	if a.down > 0 and a.state == getup and a.down >= limit + KD_GETUP:
		_play(a, 0)
		return false
	var held := _held_down(a)
	if a.down >= limit and a.lying() and not held and getup >= 0:
		_play(a, getup)
		return false
	return a.lying() and (a.down < limit or held) and a.frame >= a.duration() - 2


## SakugaActor.NetsuHeldDownBySuper (simplified): a super (or a NetsuHoldDown state) keeps them down until it's over.
func _held_down(a: Actor) -> bool:
	if not a.lying() or attacker.state_type() != T_COMBAT:
		return false
	var st := attacker.cur_state()
	if bool(_g(st, "NetsuHoldDown", false)) and attacker.frame < attacker.duration() - 1:
		return a.down < 20 + SUPER_HOLD_MAX
	var is_super := move != null and attacker.in_move and int(_g(move, "SuperGaugeRequired", 0)) >= SUPER
	return is_super and attacker.frame < attacker.duration() - 1 and a.down < 20 + SUPER_HOLD_MAX


## SakugaActor.NetsuExStillGoing: the EX that hit her still has an attack window to come (or is in the one that hit).
func _ex_going() -> bool:
	var a := attacker
	if not a.in_move or a.state_type() != T_COMBAT:
		return false
	var wins: Array = _g(a.anim(), "Hitboxes", [])
	if wins.is_empty():
		return false
	var dur := a.duration()
	var hit_frame := defender.ex_frame if a.state == defender.ex_state else -1
	var next_end := -1
	var next_start := 1 << 30
	var cur_end := -1
	var last_end := -1
	for w in wins:
		if w == null or _g(w, "HitboxData") == null:
			continue
		var dmg := false
		for e in _g(_g(w, "HitboxData"), "Hitboxes", []):
			if e != null and int(_g(e, "BaseDamage", 0)) > 0:
				dmg = true
				break
		if not dmg:
			continue
		var at := int(_g(w, "AtFrame", 0))
		var end := dur
		for n in wins:
			if n != null and int(_g(n, "AtFrame", 0)) > at and int(_g(n, "AtFrame", 0)) < end:
				end = int(_g(n, "AtFrame", 0))
		last_end = maxi(last_end, end)
		if at > hit_frame and at < next_start:
			next_start = at
			next_end = end
		if at <= hit_frame and end >= hit_frame:
			cur_end = maxi(cur_end, end)
	var deadline := next_end if next_end >= 0 else cur_end
	return deadline >= 0 and a.frame <= mini(deadline, last_end)


## Tick extras for the opponent: float, carry, EX hold (SakugaActor.NetsuFloatTick / NetsuCarryTick / NetsuExHoldTick).
func _holds(d: Actor) -> void:
	if d.float_frame > 0:
		if (d.on_ground() and d.float_frame > 1) or d.state_type() != T_HIT or d.float_frame > d.float_total:
			d.float_frame = 0
		else:
			var v0 := d.float_rise * 2 * 60 / d.float_rise_frames
			d.vel.y = v0 * (d.float_rise_frames - (d.float_frame - 1)) / d.float_rise_frames
			d.float_frame += 1
	if d.carry > 0:
		var a := attacker
		var going := d.state_type() == T_HIT and a.state_type() != T_HIT and a.state_type() != T_BLOCKING and a.vel.y > 0 and d.carry <= CARRY_MAX
		if not going:
			d.carry = 0
			if d.state_type() == T_HIT:
				d.vel.y = mini(d.vel.y, 0)
				d.vel.x = a.vel.x / 2
				d.hitstun = maxi(d.hitstun, CARRY_RELEASE_HITSTUN)
		else:
			d.vel = a.vel
			d.hitstun = maxi(d.hitstun, 2)
			d.carry += 1
	if d.ex_hold:
		d.ex_age += 1
		if d.state_type() != T_HIT or d.ex_age > EX_HOLD_GRACE or not _ex_going():
			d.ex_hold = false
		else:
			if not d.on_ground() and d.vel.y < 0:
				d.vel.y = 0
			d.hitstun = maxi(d.hitstun, 2)


## The attacker's queue: the next listed move starts at the top of a jump or in a cancel window.
func _queue_tick() -> void:
	var a := attacker
	if a.queue.is_empty() or a.hitstop > 0:
		return
	var next: Dictionary = a.queue[0]
	var go := false
	_item_age += 1
	match str(next.get("when", "neutral")):
		"now":
			go = true
		"after":
			go = _item_age >= int(next.get("frames", 20))
		"apex":
			# just past the top of the jump, on the way down (where jump-ins are done)
			go = not a.on_ground() and a.vel.y <= -8000 and a.state_type() <= 1
		"cancel":
			var only := int(next.get("in", -1))
			var mask := int(next.get("mask", WHIFF | HIT))
			var lo := int(next.get("min", 0))
			var hi := int(next.get("max", 999))
			if (only < 0 or a.state == only) and a.frame >= lo and a.frame <= hi and (a.cancel & mask) != 0:
				# a hit-confirm follow-up waits for the hit while the parent still has attack frames to come
				go = not ((mask & HIT) != 0 and (a.cancel & HIT) == 0 and _attack_ahead(a) and a.frame < hi)
	if go:
		a.queue.pop_front()
		_start_item(next)


func _attack_ahead(a: Actor) -> bool:
	for key in _g(a.anim(), "Hitboxes", []):
		if key != null and int(_g(key, "AtFrame", 0)) >= a.frame:
			for el in _g(_g(key, "HitboxData"), "Hitboxes", []):
				if el != null and int(_g(el, "HitboxType", 0)) in [BOX_HIT, BOX_PROJECTILE, BOX_THROW]:
					return true
	return false


func _step() -> void:
	if _pause > 0:
		# the EX / super pause: nothing moves; her pause pose (if the move has one) plays
		_pause -= 1
		_pause_frame += 1
		return
	if not _def_attack.is_empty() and _frame_no >= int(_def_attack["at"]) and defender.state_type() <= 1:
		_play(defender, int(_def_attack["state"]))
		_def_attack = {}
	# PreTick
	for a in actors:
		if not a.active:
			continue
		a.life += 1
		if a.flash > 0:
			a.flash -= 1
		if a.hitstop > 0:
			a.hitstop -= 1
			if a.hitstop > 0:
				continue
		var hold_down: bool = _knockdown(a)
		if a.hitstun > 0 and a.hitstun_type < HS_HARD:
			a.hitstun -= 1
		if a.knockback > 0:
			a.knockback -= 1
		if a.bounce > 0:
			a.bounce -= 1
		if a.fighter and a.state_type() != T_HIT:
			a.hitstun = 0
			a.hitstun_type = 0
			a.ex_hold = false
			a.grav_decay = 0
		var was_hit: bool = a.state_type() == T_HIT
		var prev: int = a.state
		var ad = a.anim()
		var hs_hold := int(_g(ad, "HitstunHold", -1))
		var locked: bool = a.hitstun > 0 and hs_hold >= 0 and a.hitstun >= a.duration() - hs_hold + 1 and a.frame >= hs_hold
		if not locked and not hold_down:
			a.frame += 1
			for key in _g(ad, "Hitboxes", []):
				if key != null and bool(_g(key, "NetsuRehit", false)) and int(_g(key, "AtFrame", 0)) == a.frame:
					a.hit_done = false
			if a.frame >= 3:
				a.cancel &= ~KARA
		_run_events(a, _g(a.cur_state(), "TransitionEvents", []))
		# NetsuNoFreeFall: an air hit reaction that ends into neutral holds its last frame until she lands
		if a.fighter and a != attacker and was_hit and not a.on_ground() and a.state != prev and a.hitstun_type != HS_GRABBED \
				and not (a.state_type() in [T_HIT, T_BLOCKING]) and not a.state_name().begins_with("Recovery_"):
			a.state = prev
			a.frame = maxi(0, a.duration() - 1)
		if not a.fighter and (a.life > 300 or absi(a.pos.x) > 160000):
			a.active = false
	_queue_tick()
	# Tick
	for a in actors:
		if not a.active or a.hitstop > 0:
			continue
		_run_events(a, _g(a.cur_state(), "OnTickEvents", []))
		if a == defender:
			_holds(a)
	# Simulate: movement, hits, push boxes
	for a in actors:
		if not a.active or a.hitstop > 0:
			continue
		a.pos += a.vel / 120
		if a.fighter:
			a.pos.y = clampi(a.pos.y, 0, CEILING)
	if defender != null and defender.state_type() == T_COMBAT:
		_try_counter(defender)
	for a in actors:
		if a != defender and a.active and not a.passive:
			_try_hits(a)
	_push_apart()
	# who is on the left (GameManager), for ChangeSideAction
	if defender != null:
		if attacker.pos.x < defender.pos.x:
			attacker.left = true
			defender.left = false
		elif attacker.pos.x > defender.pos.x:
			attacker.left = false
			defender.left = true
	for s in _sparks:
		s["age"] += 1
	_sparks = _sparks.filter(func(s): return s["age"] < 14)


func _snapshot() -> Dictionary:
	var list: Array = []
	for a in actors:
		if not a.active:
			continue
		var ad = a.anim()
		var fr: int = a.frame
		if _pause > 0 and a == attacker and _pause_state >= 0 and _pause_state < a.states.size():
			ad = _g(a.states[_pause_state], "AnimationData")
			fr = _pause_frame
		list.append({"ad": ad, "frame": fr, "pos": a.pos, "side": a.side, "scale": a.scale,
			"flash": a.flash > 0, "shake": a.hitstop > 0 and a.state_type() == T_HIT, "fighter": a.fighter,
			"attacker": a == attacker})
	var sparks: Array = []
	for s in _sparks:
		sparks.append(s.duplicate())
	var out := {"actors": list, "sparks": sparks}
	if _pause > 0:
		out["pause"] = {"t": _pause_total - _pause, "n": _pause_total, "super": _pause_super, "pos": attacker.pos,
			"name": move_name}
	return out


func _trace_line(f: int) -> String:
	var out := "%3d" % f
	if _pause > 0:
		out += " PAUSE %d/%d" % [_pause_total - _pause, _pause_total]
	for a in [attacker, defender]:
		if a == null:
			continue
		out += " | %s[%d] f%d pos(%d,%d) vel(%d,%d) hs%d/%d kb%d stop%d" % [a.state_name(), a.state, a.frame,
			a.pos.x, a.pos.y, a.vel.x, a.vel.y, a.hitstun, a.hitstun_type, a.knockback, a.hitstop]
	return out


## Plays it all out and records the frames. Stops a little after both are back to neutral (or at MAX_FRAMES).
func record() -> Array:
	frames.clear()
	var calm := 0
	var started := false
	for f in MAX_FRAMES:
		_frame_no = f
		frames.append(_snapshot())
		if tracing:
			trace.append(_trace_line(f))
		_step()
		var att_free := attacker.state_type() <= 1 and attacker.on_ground() and attacker.queue.is_empty() and _pause <= 0
		var def_free := defender == null or (defender.state_type() <= 1 and defender.hitstun <= 0 and _def_attack.is_empty())
		if f > 6:
			started = true
		if started and att_free and def_free:
			calm += 1
			if calm >= TAIL_FRAMES:
				break
		else:
			calm = 0
	return frames
