"""FIGHTER DATA KIT: writes Mahou SakugaEngine resources (states, moves, motion inputs, hitbox
files, animation data) from short Python descriptions, so moves and whole fighters can be made,
remade and reviewed by script instead of clicking through the inspector.

Everything it writes is a normal Godot resource: open it in Godot and edit as usual.
Re-running a script keeps every file's uid, and never overwrites a file that was edited by hand
since this kit last wrote it (it says so and skips it; pass force=True to write anyway).

    from fdk import *
    st = State('Opening Edge A', COMBAT, anim_res, enter=[...], tick=[ev([at(5)], [movex(160000)])])
    write('res://actors/cecilia/States/79_CEC_236A.tres', st)
"""
import os, re, sys, json, random, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); PROJ = os.path.abspath(os.path.join(HERE, '..', '..'))
SR = 'res://engine/sakuga/Resources/'
FDE = SR + 'FrameDataEvents/'
ACT = FDE + 'Actions/'
CON = FDE + 'Conditions/'

# ------------------------------------------------------------------ uids
_script_uids = None
def script_uid(res):
    global _script_uids
    if _script_uids is None:
        _script_uids = {}
        p = os.path.join(HERE, 'analysis', 'script_uids.tsv')
        if os.path.exists(p):
            for line in open(p, encoding='utf-8'):
                if '\t' in line:
                    k, v = line.rstrip('\n').split('\t'); _script_uids['res://' + k] = v
        for root, _, files in os.walk(os.path.join(PROJ, 'engine')):
            for f in files:
                if f.endswith('.cs.uid') or f.endswith('.gd.uid'):
                    rel = os.path.relpath(os.path.join(root, f[:-4]), PROJ).replace('\\', '/')
                    _script_uids.setdefault('res://' + rel, open(os.path.join(root, f), encoding='utf-8').read().strip())
    return _script_uids.get(res)

def res_file(res): return os.path.join(PROJ, res.replace('res://', ''))
def res_uid(res):
    p = res_file(res)
    if not os.path.exists(p): return None
    if not p.endswith(('.tres', '.tscn')):   # pictures, sounds: Godot keeps the uid in the .import file
        imp = p + '.import'
        if not os.path.exists(imp): return None
        m = re.search(r'uid="([^"]+)"', open(imp, encoding='utf-8', errors='ignore').read())
        return m.group(1) if m else None
    with open(p, encoding='utf-8', errors='ignore') as f: head = f.readline()
    m = re.search(r'uid="([^"]+)"', head); return m.group(1) if m else None

def new_uid():
    v = random.getrandbits(62) | (1 << 61); txt = ''
    while v:
        c = v % 35; txt = (chr(97 + c) if c < 26 else chr(48 + c - 26)) + txt; v //= 35
    return 'uid://' + txt

# ------------------------------------------------------------------ values
class Obj:
    """a sub-resource: Obj(script_res_path, Field=value, ...); None values are left out (engine default)."""
    def __init__(self, script, **fields): self.script = script; self.fields = fields
class Ext:
    """a reference to another resource file (ExtResource)."""
    def __init__(self, res, type='Resource'): self.res = res; self.type = type
class V2i:
    def __init__(self, x, y): self.x, self.y = int(x), int(y)
class V2:
    def __init__(self, x, y): self.x, self.y = float(x), float(y)
class Packed:
    def __init__(self, kind, vals): self.kind, self.vals = kind, list(vals)
class Raw:
    def __init__(self, text): self.text = text

class Writer:
    def __init__(self):
        self.ext = []; self.ext_ids = {}; self.subs = []; self.n = 0
    def ext_id(self, res, type):
        key = (res, type)
        if key not in self.ext_ids:
            i = str(len(self.ext) + 1)
            uid = script_uid(res) if type == 'Script' else res_uid(res)
            self.ext.append((type, uid, res, i)); self.ext_ids[key] = i
        return self.ext_ids[key]
    def val(self, v):
        if v is None: return 'null'
        if isinstance(v, bool): return 'true' if v else 'false'
        if isinstance(v, int): return str(v)
        if isinstance(v, float): return repr(v)
        if isinstance(v, str): return '"' + v.replace('\\', '\\\\').replace('"', '\\"') + '"'
        if isinstance(v, V2i): return 'Vector2i(%d, %d)' % (v.x, v.y)
        if isinstance(v, V2): return 'Vector2(%s, %s)' % (fmt_f(v.x), fmt_f(v.y))
        if isinstance(v, Packed): return '%s(%s)' % (v.kind, ', '.join(str(x) for x in v.vals))
        if isinstance(v, Raw): return v.text
        if isinstance(v, Ext): return 'ExtResource("%s")' % self.ext_id(v.res, v.type)
        if isinstance(v, Obj): return 'SubResource("%s")' % self.sub(v)
        if isinstance(v, (list, tuple)): return '[' + ', '.join(self.val(x) for x in v) + ']'
        raise TypeError(v)
    def body(self, o):
        lines = ['script = ExtResource("%s")' % self.ext_id(o.script, 'Script')]
        for k, v in o.fields.items():
            if v is None: continue
            lines.append('%s = %s' % (k, self.val(v)))
        return lines
    def sub(self, o):
        lines = self.body(o)            # children first (they get lower ids, written earlier)
        self.n += 1; i = 's%d' % self.n
        self.subs.append((i, lines)); return i
    def text(self, root, script_class, uid):
        res_lines = self.body(root)
        out = ['[gd_resource type="Resource" script_class="%s" format=3%s]' % (script_class, ' uid="%s"' % uid if uid else ''), '']
        for t, u, p, i in self.ext:
            out.append('[ext_resource type="%s"%s path="%s" id="%s"]' % (t, ' uid="%s"' % u if u else '', p, i))
        out.append('')
        for i, lines in self.subs:
            out.append('[sub_resource type="Resource" id="%s"]' % i); out += lines; out.append('')
        out.append('[resource]'); out += res_lines; out.append('')
        return '\n'.join(out)

def fmt_f(x):
    return ('%d' % x) if float(x).is_integer() else repr(float(x))

# ------------------------------------------------------------------ writing with hand-edit safety
STATE_FILE = os.path.join(HERE, 'analysis', 'fdk_written.json')
_written = None
def _state():
    global _written
    if _written is None:
        _written = json.load(open(STATE_FILE)) if os.path.exists(STATE_FILE) else {}
    return _written
def _save_state():
    json.dump(_state(), open(STATE_FILE, 'w'), indent=1, sort_keys=True)
def md5(s): return hashlib.md5(s.replace('\r\n', '\n').encode('utf-8')).hexdigest()

LOG = []
def write_text(res, text, force=False, backup_dir=None):
    """write a resource text file; keeps hand edits (see module doc)."""
    path = res_file(res); st = _state()
    if os.path.exists(path):
        cur = open(path, encoding='utf-8').read()
        if md5(cur) == md5(text): return 'same'
        if res in st and st[res] != md5(cur) and not force:
            LOG.append('SKIPPED (edited by hand): ' + res); return 'skipped'
        if res not in st and not force:
            LOG.append('SKIPPED (not made by this kit; use force=True): ' + res); return 'skipped'
        if backup_dir:
            bk = os.path.join(PROJ, backup_dir, os.path.basename(path) + '.bak')
            if not os.path.exists(bk):
                os.makedirs(os.path.dirname(bk), exist_ok=True); open(bk, 'w', encoding='utf-8').write(cur)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8', newline='\n').write(text)
    st[res] = md5(text); _save_state(); LOG.append('wrote ' + res)
    return 'wrote'

def write(res, root, script_class=None, force=False):
    """write a resource built from Obj; keeps the existing file's uid (or makes a new one).
    A state (FighterState) also gets its sound cues from sounds.py (Oct 24 night), so rewriting it keeps its sounds."""
    uid = res_uid(res) or new_uid()
    w = Writer()
    text = w.text(root, script_class or os.path.basename(root.script).replace('.cs', ''), uid)
    if root.script.endswith('FighterState.cs'):
        try:
            if HERE not in sys.path:
                sys.path.insert(0, HERE)
            import sounds
            text = sounds.apply_to_text(res, text)
        except ImportError:
            pass
    return write_text(res, text, force)

# ------------------------------------------------------------------ frame data events
COMBAT, MOVEMENT, BLOCKING, HIT_REACTION, LOCKED = 2, 1, 3, 4, 5
def ev(conds=None, acts=()):
    return Obj(FDE + 'FrameDataEvent.cs', Conditions=list(conds) if conds else None, Actions=list(acts))
# conditions
def at(frame, modulo=None, not_=None): return Obj(CON + 'AtFrameCondition.cs', Frame=frame or None, Modulo=modulo, Not=not_)
def at_range(a, b, not_=None): return Obj(CON + 'AtFrameRangeCondition.cs', MinFrame=a, MaxFrame=b, Not=not_)
def state_ended(): return Obj(CON + 'StateEndedCondition.cs')
def on_ground(not_=None): return Obj(CON + 'OnGroundCondition.cs', Not=not_)
def is_falling(not_=None): return Obj(CON + 'IsFallingCondition.cs', Not=not_)
def check_input(input_res, not_=None): return Obj(CON + 'CheckInputCondition.cs', Input=Ext(input_res), Not=not_)
def check_hit(conditions, not_=None): return Obj(CON + 'CheckHitCondition.cs', HitCheck=conditions, Not=not_)
def side_changed(not_=None): return Obj(CON + 'CheckSideChangeCondition.cs', Not=not_)
def distance(lo, hi, rel=2, index=0, not_=None): return Obj(CON + 'CheckDistanceCondition.cs', MinDistance=lo, MaxDistance=hi, RelativeTo=rel, Index=index or None, Not=not_)
def check_var(name, value, compare=0, by_index=None): return Obj(CON + 'CheckCustomVariableCondition.cs', ByIndex=by_index, ByName=name, Value=value, CompareMode=compare or None)
def check_timer(name, not_=None): return Obj(CON + 'CheckTimerCondition.cs', ByName=name, Not=not_)
def rel_x(lo=None, hi=None, target=2, not_=None):
    """true when the actor is lo..hi units past the target along its facing (negative = still short of it);
    target: OPPONENT 2 (default), FIGHTER 3, WORLD 0 (x 0)"""
    return Obj(CON + 'NetsuRelativeXCondition.cs', Target=target, MinDistance=lo, MaxDistance=hi, Not=not_)
# actions
def movex(v, inertia=None, use_input=None): return Obj(ACT + 'MoveXAction.cs', Velocity=v, UseInertia=inertia, UseInput=use_input)
def movey(v, inertia=None): return Obj(ACT + 'MoveYAction.cs', Velocity=v, UseInertia=inertia)
def gravity(force=None, set_value=True):
    return Obj(ACT + 'AddGravityAction.cs', SetValue=set_value, UseDefault=(force is None) or None, Force=force)
def play_state(index=0, reset=None): return Obj(ACT + 'PlayStateAction.cs', StateIndex=index or None, Reset=reset)
def goto_frame(f): return Obj(ACT + 'GoToFrameActions.cs', Frame=f)
def change_side(forced=None): return Obj(ACT + 'ChangeSideAction.cs', Forced=forced)
INV_STRIKE, INV_THROW, INV_PROJ, LOCK_MOVE = 1, 2, 4, 16
SET, ADD, SUB = 0, 1, 2
def frame_props(props, mode=SET): return Obj(ACT + 'SetFramePropertiesAction.cs', Properties=props, ChangeMode=mode)
def reset_hit(): return Obj(ACT + 'ResetHitAction.cs')
WORLD, SELF, OPPONENT, FIGHTER, SPAWNABLE = 0, 1, 2, 3, 4
def teleport(x, y, xrel=SELF, yrel=SELF, index=None):
    return Obj(ACT + 'TeleportAction.cs', Index=index, TargetPosition=V2i(x, y), xRelativeTo=xrel, yRelativeTo=yrel)
def spawn_actor(index, x=0, y=0, xrel=SELF, yrel=SELF, initial_state=None):
    return Obj(ACT + 'SpawnActorAction.cs', TargetPosition=V2i(x, y), xRelativeTo=xrel, yRelativeTo=yrel, Index=index, InitialState=initial_state)
def spawn_vfx(index, x=0, y=0, xrel=SELF, yrel=SELF, attach=None):
    return Obj(ACT + 'SpawnVFXAction.cs', TargetPosition=V2i(x, y), xRelativeTo=xrel, yRelativeTo=yrel, Index=index, AttachToParent=attach)
def camera_shake(amp=0.03, duration=12, wavelength=None): return Obj(ACT + 'CameraShakeAction.cs', Amplitude=float(amp), WaveLength=wavelength, Duration=duration)
def stop_knockback(keep_x=None): return Obj(ACT + 'StopKnockbackAction.cs', KeepXVelocity=keep_x)
def set_active(on): return Obj(ACT + 'SetActiveAction.cs', Active=on)
def set_var(name, value, mode=0, by_index=None): return Obj(ACT + 'SetCustomVariableAction.cs', ByIndex=by_index, ByName=name, ChangeMode=mode or None, NewValue=value)
def play_sound(index, source=None, random_range=None, voice=False):
    return Obj(ACT + 'PlaySoundAction.cs', SoundType=1 if voice else None, Source=source, Index=index, IsRandom=True if random_range else None, Range=random_range)
def interrupt_move(): return Obj(ACT + 'InterruptMoveAction.cs')
def set_super_gauge(v, absolute=None): return Obj(ACT + 'SetSuperGaugeAction.cs', Value=v, Absolute=absolute)
def super_flash(frames=20, cut_in=True):
    """Oct 24: the super flash + cut-in started from a state (counter supers: the move has NetsuFlashOnHit)"""
    return Obj(ACT + 'NetsuSuperFlashAction.cs', Frames=frames, CutIn=None if cut_in else False)
def wall_pop(pop=80000, max_back=30000):
    """Oct 24: on a wall bounce, the opponent pops up (works during knockback, unlike movey)"""
    return Obj(ACT + 'NetsuWallPopAction.cs', Pop=pop, MaxBackSpeed=max_back)

NULL = Raw('null')
def events(items):
    """an event list as the engine needs it: FrameDataEvents only. Bare actions (enter=[change_side(), movex(0)])
    are wrapped into one event without conditions (consecutive actions share it). Oct 24 fix: the engine's lists
    are typed FrameDataEvent[], and a bare action in one made Godot drop the WHOLE list when loading (an
    InvalidCastException in the output), so every special's start-up actions (face the opponent, stop, invincibility)
    never ran."""
    out, run = [], []
    for it in items:
        if isinstance(it, Obj) and it.script.endswith('FrameDataEvent.cs'):
            if run:
                out.append(ev(acts=run)); run = []
            out.append(it)
        else:
            run.append(it)
    if run:
        out.append(ev(acts=run))
    return out
def State(name, type, anim_res, transitions=(), enter=(), tick=(), exit=(), hit_confirm=(), hit_reaction=(), ai=0, base_stance=None,
          show_stage=None):
    # empty event lists are written as "= null" (like Godot does): the engine then gets an empty list, not nothing
    # show_stage (Oct 25): FighterState.NetsuShowStage, a super's dark backdrop clears during this state
    return Obj(SR + 'FighterState.cs', StateName=name, BaseStance=base_stance, Type=type, AnimationData=Ext(anim_res),
               TransitionEvents=events(transitions) or NULL, OnEnterEvents=events(enter) or NULL, OnTickEvents=events(tick) or NULL,
               OnExitEvents=events(exit) or NULL, OnHitConfirmEvents=events(hit_confirm) or NULL,
               OnHitReactionEvents=events(hit_reaction) or NULL, NetsuShowStage=show_stage or None, AIFlags=ai or None)

# ------------------------------------------------------------------ moves
WHIFF, HIT, BLOCK, KARA = 1, 2, 4, 8
def cancel(move_index, conditions=HIT | BLOCK, frames=(0, 999)):
    return Obj(SR + 'MoveCancelSettings.cs', MoveIndex=move_index, Conditions=conditions, FrameThreshold=V2i(*frames))
def Move(name, state_index, input_res, priority=7, move_end=2, cancels=(), meter=None, flash=None, ground=True, air=False,
         distance=None, accept_combat=True, accept_null=True, overridable=True, extra=None):
    f = dict(MoveName=name, MoveState=state_index, Inputs=Ext(input_res), SuperFlash=flash, Priority=priority, MoveEnd=move_end,
             SuperGaugeRequired=meter, DistanceArea=V2i(*distance) if distance else None,
             CanCancelTo=list(cancels) or None, CanBeOverrided=overridable, IgnoreSamePriority=False,
             AcceptNullStates=accept_null, AcceptCombatStates=accept_combat, UseOnGround=ground or None, UseOnAir=air or None)
    if extra: f.update(extra)
    return Obj(SR + 'MoveSettings.cs', **f)

# ------------------------------------------------------------------ motion inputs
# numpad directions -> engine flags (DOWN 1, LEFT(back) 2, RIGHT(forward) 4, UP 8), character relative
NUM = {1: 3, 2: 1, 3: 5, 4: 2, 5: 0, 6: 4, 7: 10, 8: 8, 9: 12}
BTN = {'A': 1, 'B': 2, 'C': 4, 'D': 8, 'S': 8}
HOLD = 1
def _seq(d=None, hold=False, buttons=0, button_mode=None):
    return Obj(SR + 'InputSequence.cs', Directional=NUM[d] if d else None, DirectionalMode=HOLD if (hold and d) else None,
               Buttons=buttons or None, ButtonMode=button_mode)
def motion_variants(motion):
    """the lenient variants the existing inputs use: hold-style steps, a neutral gap, button with
    the last direction, last direction tapped."""
    m = [int(c) for c in motion]
    if m == [2, 3, 6] or m == [2, 1, 4]:
        a, b, c = m
        return [[(a, 1), (b, 1), (c, 1), None, 'B'],
                [(a, 1), (b, 1), (c, 1), (0, 0), 'B'],
                [(a, 1), (b, 1), ('Bwith', c)],
                [(a, 1), (b, 1), (c, 0), ('Bwith', c)]]
    if m == [6, 2, 3]:
        return [[(6, 1), (0, 0), (2, 1), (3, 1), 'B'], [(6, 1), (0, 0), (2, 1), (3, 1), ('Bwith', 3)],
                [(6, 1), (0, 0), (2, 1), ('Bwith', 3)], [(6, 1), (2, 1), (3, 1), 'B'], [(6, 1), (2, 1), ('Bwith', 3)],
                [(6, 1), (3, 1), (2, 1), (3, 1), 'B'], [(6, 1), (3, 1), (2, 1), ('Bwith', 3)], [(3, 1), (2, 1), (3, 1), 'B'],
                [(3, 1), (2, 1), ('Bwith', 3)], [(6, 1), (3, 1), (2, 1), (3, 1), ('Bwith', 3)]]
    if m == [2, 2]:
        return [[(2, 0), (0, 0), (2, 0), 'B'], [(2, 0), (0, 0), ('Bwith', 2)]]
    if m == [2, 3, 6, 2, 3, 6] or m == [2, 1, 4, 2, 1, 4]:
        # supers: the first quarter circle, then the stick comes back through the diagonal or neutral (or
        # straight down), then any variant of the second one
        a, b, c = m[:3]
        firsts = [[(a, 1), (b, 1), (c, 1)], [(a, 1), (b, 1), (c, 1), (b, 1)], [(a, 1), (b, 1), (c, 1), (0, 0)]]
        return [f + v for f in firsts for v in motion_variants(motion[:3])]
    raise ValueError('add variants for motion ' + motion)
def MotionInputs(motion, button_sets, buffer=None):
    """motion like '236', button_sets like ['B', 'C'] (either) or ['BC'] (together)."""
    opts = []
    for bs in button_sets:
        bits = 0
        for ch in bs: bits |= BTN[ch]
        together_hold = len(bs) == 2   # "press B and C together" also accepts B held + C pressed
        for var in motion_variants(motion):
            seq = []
            for step in var:
                if step is None: continue
                if step == 'B': seq.append(_seq(buttons=bits))
                elif isinstance(step, tuple) and step[0] == 'Bwith': seq.append(_seq(step[1], True, bits))
                elif step == (0, 0): seq.append(_seq())
                else: seq.append(_seq(step[0], bool(step[1])))
            opts.append(Obj(SR + 'InputOption.cs', Inputs=seq))
        if together_hold:
            b1, b2 = BTN[bs[0]], BTN[bs[1]]
            var = motion_variants(motion)[0]
            seq = [_seq(s[0], bool(s[1])) for s in var if isinstance(s, tuple) and s != (0, 0) and s[0] != 'Bwith']
            seq += [_seq(buttons=b1, button_mode=1), _seq(buttons=b2)]
            opts.append(Obj(SR + 'InputOption.cs', Inputs=seq))
    return Obj(SR + 'MotionInputs.cs', ValidInputs=opts, AbsoluteDirection=True, InputBuffer=buffer)

# ------------------------------------------------------------------ hitboxes
HURT, HIT_T, PROX, PROJECTILE_T, THROW_T, COUNTER, DEFLECT = 0, 1, 2, 3, 4, 5, 6
HIGH, MID, LOW, UNBLOCKABLE = 0, 1, 2, 3
NONE, BASIC, KNOCKDOWN, HARD_KNOCKDOWN = 0, 1, 2, 3
BASE_ELEMENT = dict(SelfSuperGaugeGain=25, OpponentSuperGaugeGain=10, HitEffectIndex=0, BlockEffectIndex=1, ClashEffectIndex=2,
                    AirHitKnockbackGravity=300000, AirBlockKnockbackGravity=30, SelfPushbackForce=0, SelfPushbackDuration=0,
                    BounceXIntensity=0, BounceYIntensity=0)
def box(type, x0=-60, y0=0, x1=60, y1=100, upx=27.5, **props):
    """a HitboxElement from a world-pixel rectangle (x forward, y up); props = damage etc."""
    f = dict(Center=V2i(round((x0 + x1) / 2 * upx / 100) * 100, round((y0 + y1) / 2 * upx / 100) * 100),
             Size=V2i(max(100, round((x1 - x0) * upx / 100) * 100), max(100, round((y1 - y0) * upx / 100) * 100)))
    if type: f['HitboxType'] = type
    if type in (HURT, PROX, COUNTER): f.update({k: v for k, v in BASE_ELEMENT.items()})
    f.update(props)
    return Obj(SR + 'HitboxElement.cs', **f)
def attack(damage, hitstun, blockstun, kb=(-30000, 0), air_kb=(-12000, 40000), reaction=1, air_reaction=4, crouch_reaction=None,
           hit_type=MID, stop=12, block_stop=None, gain=400, opp_gain=100, hitstun_type=BASIC, air_hitstun_type=None,
           air_hitstun=None, block_kb=None, air_block_kb=(-12000, 0), effect=6, scaling=10, kb_gravity=None, air_gravity=None,
           guard_crush=None, pushback=None, extra=None):
    """the damage side of an attack box, with the fields Cecilia's existing moves use."""
    p = dict(OpponentSuperGaugeGain=opp_gain, SelfSuperGaugeGain=gain, HitEffectIndex=effect, HitType=hit_type, BaseDamage=damage,
             SelfHitStopDuration=stop, OpponentHitStopDuration=stop, BlockStopDuration=block_stop or stop, DamageScalingSubtract=scaling,
             GroundHitstunType=hitstun_type, GroundHitReaction=reaction or None, CrouchHitReaction=crouch_reaction if crouch_reaction is not None else (reaction if reaction not in (0, 1) else 2),
             GroundHitKnockback=V2i(*kb), GroundHitKnockbackGravity=kb_gravity, GroundHitstun=hitstun,
             GroundBlockKnockback=V2i(*(block_kb or (kb[0], 0))), GroundBlockstun=blockstun,
             AirHitstunType=air_hitstun_type if air_hitstun_type is not None else hitstun_type, AirHitReaction=air_reaction,
             AirHitKnockback=V2i(*air_kb), AirHitKnockbackGravity=air_gravity, AirHitstun=air_hitstun or hitstun,
             AirBlockKnockback=V2i(*air_block_kb), AirBlockstun=blockstun, GuardCrush=guard_crush)
    if pushback is not None: p.update(SelfPushbackForce=pushback)
    if extra: p.update(extra)
    return p
PUSHBOX_STD = 'res://actors/_shared/sakuga/HitboxTemplates/Box_Neutral_std.tres'
def Hitboxes(elements, pushbox=PUSHBOX_STD):
    return Obj(SR + 'HitboxSettings.cs', Pushbox=Ext(pushbox) if pushbox else None, Hitboxes=list(elements))
def standard_hurt(n=3, w=230, h=480):
    """placeholder hurtboxes for a new pose (hitfit.py fits them to the drawing afterwards)."""
    if n == 3:
        return [box(HURT, -w * 0.25, h * 0.78, w * 0.25, h), box(HURT, -w * 0.35, h * 0.4, w * 0.35, h * 0.8), box(HURT, -w * 0.5, 0, w * 0.5, h * 0.44)]
    return [box(HURT, -w * 0.4, h * 0.46, w * 0.4, h), box(HURT, -w * 0.5, 0, w * 0.5, h * 0.54)][:n]

# ------------------------------------------------------------------ animation data
def AnimData(duration, hitbox_states, afterimages=None, hitstun_hold=None):
    """hitbox_states: [(at_frame, stage, hitbox_res)]; the sprite timeline is added by build.py."""
    hs = [Obj(SR + 'HitboxState.cs', AtFrame=a or None, animationStage=s or None, HitboxData=Ext(r)) for a, s, r in hitbox_states]
    return Obj(SR + 'AnimationData.cs', Duration=duration, HitstunHold=hitstun_hold, Animations=[], Hitboxes=hs, Afterimages=afterimages)

# ------------------------------------------------------------------ editing existing lists
from tres import Tres
def edit_tres(res, fn, backup_dir, label):
    """load res with Tres, fn(t) edits it in place, write back (one backup per file)."""
    path = res_file(res); cur = open(path, encoding='utf-8').read()
    t = Tres(cur); fn(t); txt = t.text()
    if md5(txt) == md5(cur): return False
    bk = os.path.join(PROJ, backup_dir, os.path.basename(path) + '.bak')
    if not os.path.exists(bk):
        os.makedirs(os.path.dirname(bk), exist_ok=True); open(bk, 'w', encoding='utf-8').write(cur)
    open(path, 'w', encoding='utf-8', newline='\n').write(txt); LOG.append('%s: %s' % (label, res))
    return True

def kit_made(res, cur):
    """True when the file's text is what a tool of this kit last wrote (fdk_written.json, or hitfit.py's
    record for a hitbox file), i.e. nobody changed it in Godot since."""
    h = md5(cur)
    if _state().get(res) == h: return True
    m = re.match(r'res://actors/([^/]+)/Hitboxes/([^/]+)\.tres$', res)
    if m:
        p = os.path.join(HERE, 'analysis', m.group(1) + '_hitfit.json')
        if os.path.exists(p) and json.load(open(p)).get(m.group(2)) == h: return True
    return False

def attack_lines(props):
    """the lines of an attack box (HITBOX element) with these values, as written when the file is made
    (without the script, Center and Size lines)"""
    lines = Writer().body(box(HIT_T, 0, 0, 10, 10, **props))
    return [l for l in lines[1:] if not l.startswith(('Center = ', 'Size = '))]

def patch_attacks(res, props, force=False):
    """puts a move table's attack values (damage, stun, knockback...) into the attack boxes of an existing
    hitbox file. Their size and position (fitted by hitfit.py) and the other boxes stay as they are.
    A file changed in Godot since the kit last wrote it is kept (SKIPPED) unless force."""
    path = res_file(res); cur = open(path, encoding='utf-8').read()
    t = Tres(cur); new = attack_lines(props); n = 0
    for s in t.sub:
        if 'HitboxType = %d' % HIT_T not in s[2]: continue
        s[2] = [l for l in s[2] if l.startswith(('script = ', 'Center = ', 'Size = '))] + new; n += 1
    text = t.text()
    if not n or md5(text) == md5(cur): return 'same'
    if not force and not kit_made(res, cur):
        LOG.append('SKIPPED (edited by hand): ' + res); return 'skipped'
    open(path, 'w', encoding='utf-8', newline='\n').write(text)
    _state()[res] = md5(text); _save_state(); LOG.append('attack values updated: ' + res)
    return 'wrote'

def list_refs(t, key):
    v = t.res_get(key)
    if not v or v == 'null': return []
    return re.findall(r'(?:Ext|Sub)Resource\("[^"]+"\)', v)

def set_state_slot(data_res, slot, state_res, backup_dir):
    """put a state into the fighter's state list at a position (extends the list if needed)."""
    def fn(t):
        refs = list_refs(t, 'States')
        i = t.add_ext('Resource', state_res, res_uid(state_res), prefer_id='st_' + re.sub(r'\W', '_', os.path.basename(state_res)[:-5]))
        ref = 'ExtResource("%s")' % i
        idle = refs[0]
        while len(refs) <= slot: refs.append(idle)
        refs[slot] = ref
        t.res_set('States', '[' + ', '.join(refs) + ']')
    return edit_tres(data_res, fn, backup_dir, 'state %d' % slot)

def ensure_moves(stance_res, move_res_list, backup_dir):
    """make sure these moves are in the stance's Moves list (appended in this order); returns their indices."""
    out = {}
    def fn(t):
        refs = list_refs(t, 'Moves')
        for mr in move_res_list:
            i = t.ext_id_for_path(mr)
            if i is None:
                i = t.add_ext('Resource', mr, res_uid(mr), prefer_id='mv_' + re.sub(r'\W', '_', os.path.basename(mr)[:-5]))
            ref = 'ExtResource("%s")' % i
            if ref not in refs: refs.append(ref)
            out[mr] = refs.index(ref)
        t.res_set('Moves', '[' + ', '.join(refs) + ']')
    edit_tres(stance_res, fn, backup_dir, 'moves')
    return out

def check_order(move_res):
    """{stance move index: the place it is checked at} for moves with MoveSettings.NetsuCheckOrder (Oct 26: Cecilia's
    and Leticia's 6C sit at the end of the move list but are checked as 32.5, after the normals and before the
    specials). Cancel lists follow the same order, so 236C in a cancel isn't read as 6C. Read from the fighter's
    main stance; {} when there is none."""
    m = re.match(r'res://actors/([^/]+)/', move_res)
    if not m: return {}
    sdir = res_file('res://actors/%s/Stances/' % m.group(1))
    if not os.path.isdir(sdir): return {}
    out = {}
    for fn in os.listdir(sdir):
        if not fn.endswith('_Stance_Main.tres'): continue
        t = Tres(open(os.path.join(sdir, fn), encoding='utf-8').read())
        for i, r in enumerate(list_refs(t, 'Moves')):
            e = t.ext_by_id(re.search(r'"([^"]+)"', r).group(1))
            if not e: continue
            p = res_file(e['path'])
            if os.path.exists(p):
                mm = re.search(r'NetsuCheckOrder = (-?[\d.]+)', open(p, encoding='utf-8').read())
                if mm and float(mm.group(1)) >= 0: out[i] = float(mm.group(1))
    return out


def add_cancels(move_res, entries, backup_dir, before_all=True, priority_order=True):
    """entries: [(move_index, conditions, (f0, f1))]; added to CanCancelTo.
    The engine takes the FIRST entry whose input matches, and 5A/5B/5C accept any direction, so the list is kept
    from the highest move index to the lowest (the order the engine checks moves in neutral: 2C before 5C).
    priority_order=False keeps the old behaviour (new entries in front, or at the end with before_all=False)."""
    def fn(t):
        refs = list_refs(t, 'CanCancelTo')
        mcs = t.ext_id_for_path(SR + 'MoveCancelSettings.cs') or t.add_ext('Script', SR + 'MoveCancelSettings.cs', script_uid(SR + 'MoveCancelSettings.cs'), prefer_id='mcs')
        have = {}
        for r in refs:
            sid = re.search(r'"([^"]+)"', r).group(1); s = t.sub_get(sid)
            if s:
                m = re.search(r'MoveIndex = (\d+)', '\n'.join(s[2]))
                if m: have[int(m.group(1))] = r
        new = []
        for idx, cond, fr in entries:
            if idx in have: continue
            sid = 'fdk_%d' % idx
            t.sub.append([sid, 'Resource', ['script = ExtResource("%s")' % mcs, 'MoveIndex = %d' % idx, 'Conditions = %d' % cond, 'FrameThreshold = Vector2i(%d, %d)' % fr]])
            new.append('SubResource("%s")' % sid)
        refs = (new + refs) if before_all else (refs + new)
        if priority_order:
            order = check_order(move_res)
            def move_index(r):
                s = t.sub_get(re.search(r'"([^"]+)"', r).group(1))
                m = re.search(r'MoveIndex = (\d+)', '\n'.join(s[2])) if s else None
                i = int(m.group(1)) if m else 0
                return order.get(i, i)
            refs = sorted(refs, key=lambda r: -move_index(r))
        t.res_set('CanCancelTo', '[' + ', '.join(refs) + ']')
    return edit_tres(move_res, fn, backup_dir, 'cancels')
