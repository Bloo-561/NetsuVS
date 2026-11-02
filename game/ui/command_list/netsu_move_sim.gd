class_name NetsuMoveSim
extends RefCounted
## A small stand-in for the fight engine, for the command list's preview (Nov 2 2026): plays a move from the
## fighter's own data against an opponent and records every frame, so the preview shows how the move really
## connects: it moves the fighter (MoveX / MoveY / gravity events), checks her attack boxes against the opponent's
## hurtboxes, and on a hit plays the opponent's hit reaction (the hitbox's GroundHitReaction / AirHitReaction ->
## the opponent's stance HitReactions), knockback, hitstun and hitstop, and the attacker's hit-confirm follow-ups.
## Projectiles (SpawnActorAction) are spawned and run the same way.
##
## It reads the same resources the engine plays, so new moves and changes show up by themselves. It is not the
## engine: things it doesn't know (inputs, walls, meter, a few Netsu actions) are skipped. Units are the engine's:
## 10000 = 1 metre, y up, velocity added as velocity / 120 a frame (PhysicsBody.Move).

const DEFAULT_GRAVITY := 260000
const MAX_FRAMES := 420
const TAIL_FRAMES := 24

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
	var side := 1
	var hitstop := 0
	var hitstun := 0
	var knockback := 0
	var hit_flags := 0
	var hit_done := false
	var active := true
	var fighter := true
	var owner: Actor = null
	var opponent: Actor = null
	var life := 0
	var scale := 1.0
	var flash := 0
	var passive := false
	var queue: Array = []

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

	func on_ground() -> bool:
		return pos.y <= 0 and vel.y <= 0


var actors: Array = []
var attacker: Actor
var defender: Actor
var frames: Array = []      # recorded: [{"actors": [{ad, frame, pos, side, scale, flash, shake}], "sparks": [...]}]
var _sparks: Array = []
var _spawn_lists := {}      # Actor data -> SpawnsList resource
var spawn_resolver: Callable   # (data: Resource) -> SpawnsList resource or null


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


## Sets up the attacker (playing `states`, one after another when the move doesn't get there by itself) and an
## opponent standing in front of her, in reach of the move's first attack box. air = start in the air.
func setup(att_data: Resource, states: Array, def_data: Resource, air: bool = false, distance: int = -1, att_x: int = 0) -> void:
	actors.clear()
	frames.clear()
	_sparks.clear()
	attacker = _actor(att_data)
	attacker.side = 1
	attacker.pos = Vector2i(att_x, 14000 if air else 0)
	if def_data != null:
		defender = _actor(def_data)
		defender.side = -1
		defender.pos = Vector2i(att_x + (distance if distance > 0 else _start_distance(states)), 0)
		defender.opponent = attacker
		attacker.opponent = defender
		actors.append(defender)
		_play(defender, 0)
	actors.append(attacker)
	attacker.queue = states.slice(1)
	if not states.is_empty():
		_play(attacker, int(states[0]))


## Someone who just stands there playing a state (an assist's caller in her call pose): drawn, never hits.
func add_extra(data: Resource, state: int, pos: Vector2i, side: int = 1) -> void:
	var a := _actor(data)
	a.side = side
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
				if t == 1 or t == 3 or t == 4:
					var c: Vector2i = _g(el, "Center", Vector2i.ZERO)
					var sz: Vector2i = _g(el, "Size", Vector2i.ZERO)
					return clampi(c.x + sz.x / 2 - 1500, 7500, 30000)
	return 16000


func _play(a: Actor, state: int, reset: bool = true) -> void:
	if state < 0 or state >= a.states.size() or a.states[state] == null:
		return
	if a == attacker and not a.queue.is_empty():
		# the listed states: a natural move to the next one is kept; going back to neutral plays the next one instead
		var t := int(_g(a.states[state], "Type", 0))
		if state == int(a.queue[0]):
			a.queue.pop_front()
		elif t <= 1:
			state = int(a.queue.pop_front())
	_run_events(a, _g(a.cur_state(), "OnExitEvents", []))
	if a.state != state or reset:
		a.frame = 0
	a.state = state
	a.hit_done = false
	a.hit_flags = 0
	_run_events(a, _g(a.cur_state(), "OnEnterEvents", []))


# --- Events ----------------------------------------------------------------------------------

func _run_events(a: Actor, events) -> void:
	if events == null:
		return
	for ev in events:
		if ev == null or not a.active:
			continue
		var ok := true
		for c in _g(ev, "Conditions", []):
			if c != null and not _check(a, c):
				ok = false
				break
		if not ok:
			continue
		for act in _g(ev, "Actions", []):
			if act != null:
				_act(a, act)


func _check(a: Actor, c) -> bool:
	var no := bool(_g(c, "Not", false))
	var r := false
	match _kind(c):
		"AtFrameCondition":
			var f := int(_g(c, "Frame", 0))
			var m := int(_g(c, "Modulo", 0))
			r = (a.frame % m == f) if m > 0 else a.frame == f
		"AtFrameRangeCondition":
			r = a.frame >= int(_g(c, "MinFrame", 0)) and a.frame <= int(_g(c, "MaxFrame", 0))
			if no:
				return not r
			return r
		"StateEndedCondition":
			r = a.frame >= a.duration()
		"OnGroundCondition":
			r = a.on_ground()
		"IsFallingCondition":
			r = a.vel.y < 0
		"CheckHitCondition":
			r = (a.hit_flags & int(_g(c, "HitCheck", 2))) != 0
		"OnKnockbackCondition":
			r = a.knockback > 0
		"RoundRunningCondition":
			r = true
		"NetsuOpponentHitReactionCondition":
			r = a.opponent != null and a.opponent.state_type() == 4
		"NetsuOpponentOnGroundCondition":
			r = a.opponent != null and a.opponent.on_ground()
		_:
			r = false   # inputs, walls, health...: never true here
	return (not r) if no else r


func _act(a: Actor, act) -> void:
	match _kind(act):
		"PlayStateAction":
			var idx := int(_g(act, "StateIndex", -1))
			if idx < 0:
				var want := str(_g(act, "StateName", ""))
				for i in a.states.size():
					if a.states[i] != null and str(_g(a.states[i], "StateName", "")) == want:
						idx = i
						break
			_play(a, idx, bool(_g(act, "Reset", true)))
		"MoveXAction":
			if a.knockback > 0:
				return
			var v := int(_g(act, "Velocity", 0)) * a.side
			if bool(_g(act, "UseInput", false)):
				v = 0
			if bool(_g(act, "UseInertia", false)):
				a.vel.x = _accelerate(a.vel.x, v)
			else:
				a.vel.x = v
		"MoveYAction":
			if a.knockback > 0:
				return
			var v := int(_g(act, "Velocity", 0))
			if bool(_g(act, "UseInput", false)):
				v = 0
			if bool(_g(act, "UseInertia", false)):
				a.vel.y = _accelerate(a.vel.y, v)
			else:
				a.vel.y = v
		"AddGravityAction":
			if bool(_g(act, "SetValue", false)):
				a.gravity = DEFAULT_GRAVITY if bool(_g(act, "UseDefault", false)) else int(_g(act, "Force", DEFAULT_GRAVITY))
			a.vel.y -= a.gravity / 60
		"GoToFrameActions":
			a.frame = int(_g(act, "Frame", 0))
		"ResetHitAction":
			a.hit_done = false
		"StopKnockbackAction":
			a.knockback = 0
		"SetActiveAction":
			if not bool(_g(act, "Active", true)) and not a.fighter:
				a.active = false
		"SpawnActorAction":
			_spawn(a, act)
		"NetsuHoldOpponentAction":
			var o := a.opponent
			if o != null and o.state_type() == 4:
				var off: Vector2i = _g(act, "Offset", Vector2i(6000, 10000))
				var rate := int(_g(act, "LiftRate", 0))
				if rate > 0:
					o.pos.y += (off.y - o.pos.y) * clampi(rate, 1, 1000) / 1000
				else:
					o.pos = a.pos + Vector2i(off.x * a.side, off.y)
				o.vel = Vector2i.ZERO
		"NetsuMoveOpponentAction":
			var o := a.opponent
			if o != null:
				o.pos.x = a.pos.x + int(_g(act, "X", -7000)) * a.side
		"NetsuDamageOpponentAction":
			var o := a.opponent
			if o != null and o.state_type() == 4:
				var hs := int(_g(act, "Hitstop", 16))
				o.hitstop = hs
				a.hitstop = hs
				o.flash = 6
				_sparks.append({"pos": o.pos + Vector2i(0, 9000), "age": 0, "big": true})
		_:
			pass


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
	s.owner = a if a.fighter else a.owner
	s.opponent = s.owner.opponent
	s.side = a.side
	var target: Vector2i = _g(act, "TargetPosition", Vector2i.ZERO)
	var base := a.pos
	var rx := int(_g(act, "xRelativeTo", 1))
	var ry := int(_g(act, "yRelativeTo", 1))
	var x := target.x * a.side + (a.pos.x if rx == 1 or rx == 3 else (s.opponent.pos.x if rx == 2 and s.opponent != null else 0))
	var y := target.y + (a.pos.y if ry == 1 or ry == 3 else (s.opponent.pos.y if ry == 2 and s.opponent != null else 0))
	s.pos = Vector2i(x, y)
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


func _hurtboxes(a: Actor) -> Array:
	var out: Array = []
	var hs = _settings_at(a.anim(), a.frame)
	for el in _g(hs, "Hitboxes", []):
		if el != null and int(_g(el, "HitboxType", 0)) == 0:
			out.append(_box_rect(a, el))
	return out


func _try_hits(a: Actor) -> void:
	var target := a.opponent
	if target == null or a.hit_done or a.hitstop > 0 or not a.active:
		return
	var hs = _settings_at(a.anim(), a.frame)
	var hurt := _hurtboxes(target)
	if hurt.is_empty():
		return
	for el in _g(hs, "Hitboxes", []):
		var t := int(_g(el, "HitboxType", 0))
		if el == null or not (t == 1 or t == 3 or t == 4):
			continue
		var r := _box_rect(a, el)
		for h in hurt:
			if r.intersects(h):
				_hit(a, target, el, r.intersection(h))
				return


func _hit(a: Actor, target: Actor, box, contact: Rect2i) -> void:
	a.hit_done = true
	a.hit_flags |= 2
	var ground := target.on_ground()
	target.hitstun = int(_g(box, "GroundHitstun" if ground else "AirHitstun", 12))
	var reaction := int(_g(box, "GroundHitReaction" if ground else "AirHitReaction", 0))
	var kb: Vector2i = _g(box, "GroundHitKnockback" if ground else "AirHitKnockback", Vector2i.ZERO)
	var kbt := int(_g(box, "GroundHitKnockbackTime" if ground else "AirHitKnockbackTime", 8))
	var grav := int(_g(box, "GroundHitKnockbackGravity" if ground else "AirHitKnockbackGravity", 0))
	if grav <= 0 and (kb.y > 0 or not ground):
		grav = DEFAULT_GRAVITY
	var reactions = _g(target.stance, "HitReactions", [])
	if reaction >= 0 and reaction < reactions.size():
		_play(target, int(reactions[reaction]))
	target.vel = Vector2i(kb.x * target.side, kb.y)   # negative X = back, away from the attacker (seen from them)
	target.gravity = grav if grav > 0 else target.gravity
	target.knockback = kbt
	target.hitstop = int(_g(box, "OpponentHitStopDuration", 12))
	target.flash = 5
	var self_stop := int(_g(box, "SelfHitStopDuration", 12))
	a.hitstop = self_stop
	if not a.fighter and a.owner != null and int(_g(box, "HitboxType", 1)) != 3:
		a.owner.hitstop = self_stop
	_sparks.append({"pos": Vector2i(contact.position.x + contact.size.x / 2, contact.position.y + contact.size.y / 2), "age": 0,
		"big": int(_g(box, "BaseDamage", 0)) >= 700})
	_run_events(a, _g(a.cur_state(), "OnHitConfirmEvents", []))


# --- Running ---------------------------------------------------------------------------------

func _push_apart() -> void:
	if defender == null:
		return
	var pa = _g(_settings_at(attacker.anim(), attacker.frame), "Pushbox")
	var pd = _g(_settings_at(defender.anim(), defender.frame), "Pushbox")
	if pa == null or pd == null:
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


func _step() -> void:
	for a in actors:
		if not a.active:
			continue
		a.life += 1
		if a.flash > 0:
			a.flash -= 1
		if a.hitstop > 0:
			a.hitstop -= 1
			continue
		_run_events(a, _g(a.cur_state(), "OnTickEvents", []))
		a.pos += a.vel / 120
		if a.pos.y < 0:
			a.pos.y = 0
			if a.vel.y < 0:
				a.vel.y = 0
		if a.knockback > 0:
			a.knockback -= 1
		if a.hitstun > 0:
			a.hitstun -= 1
	for a in actors:
		if a != defender and a.active and not a.passive:
			_try_hits(a)
	_push_apart()
	for a in actors:
		if not a.active or a.hitstop > 0:
			continue
		var ad = a.anim()
		var hold := int(_g(ad, "HitstunHold", -1))
		var locked: bool = a.hitstun > 0 and hold >= 0 and a.hitstun >= a.duration() - hold + 1 and a.frame >= hold
		if not locked:
			a.frame += 1
			for key in _g(ad, "Hitboxes", []):
				if key != null and bool(_g(key, "NetsuRehit", false)) and int(_g(key, "AtFrame", 0)) == a.frame:
					a.hit_done = false
		_run_events(a, _g(a.cur_state(), "TransitionEvents", []))
		if not a.fighter and (a.life > 300 or absi(a.pos.x) > 160000):
			a.active = false
	for s in _sparks:
		s["age"] += 1
	_sparks = _sparks.filter(func(s): return s["age"] < 14)


func _snapshot() -> Dictionary:
	var list: Array = []
	for a in actors:
		if not a.active:
			continue
		list.append({"ad": a.anim(), "frame": a.frame, "pos": a.pos, "side": a.side, "scale": a.scale,
			"flash": a.flash > 0, "shake": a.hitstop > 0 and a.state_type() == 4, "fighter": a.fighter})
	var sparks: Array = []
	for s in _sparks:
		sparks.append(s.duplicate())
	return {"actors": list, "sparks": sparks}


## Plays it all out and records the frames. Stops a little after both are back to neutral (or at MAX_FRAMES).
func record() -> Array:
	frames.clear()
	var calm := 0
	var started := false
	for f in MAX_FRAMES:
		frames.append(_snapshot())
		_step()
		var att_free := attacker.state_type() <= 1 and attacker.on_ground() and attacker.queue.is_empty()
		var def_free := defender == null or (defender.state_type() <= 1 and defender.hitstun <= 0)
		if f > 6:
			started = true
		if started and att_free and def_free:
			calm += 1
			if calm >= TAIL_FRAMES:
				break
		else:
			calm = 0
	return frames
