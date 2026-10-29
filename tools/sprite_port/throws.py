"""THROWS (Oct 24 2026, night): every fighter throws with B+C and breaks throws with B+C.

  B+C (close, standing)   grab; if it catches, she throws them forward
  4 + B+C                 the same grab, but she throws them behind her (they switch sides; out of the corner)
  B+C while grabbed       throw break: both are pushed apart ("Escaped"); the window is the grab's freeze
                          (BREAK_WINDOW frames)
  A whiffed throw has a long recovery (punishable). Nobody can be thrown in block / hit stun, for a few frames
  after it (engine: SakugaActor.NetsuThrowProtectFrames), or in the air.

    python throws.py              all fighters in FIGHTERS
    python throws.py flan         one fighter
    python throws.py --force      also overwrite files changed by hand in Godot

There are no throw drawings yet, so the poses are borrowed from existing animations (POSES below: an animation and
one of its keys, copied with its sprite layers and its hurtboxes). Swap in real throw art later: change POSES /
the timings and run again (or build the animations with build.py like any other move).

Per fighter (tag = CEC / FLN / LET) it writes:
  Hitboxes/<TAG>_Hitbox_Throw*.tres              hurtboxes copied from the borrowed poses + the grab / attack boxes
  AnimationData/<TAG>_Throw*_AnimData.tres       the sprite timeline (copied keys) and the box timeline
  States/<TAG>_Throw.tres                        reach (grab box on frames 4-6), whiff recovery
  States/<TAG>_ThrowForward.tres, _ThrowBack.tres  the throw itself (strike-invincible until it lands)
  States/<TAG>_Grabbed.tres                      the one being thrown (a hit reaction)
  States/<TAG>_ThrowBreak.tres                   after a throw break (both fighters)
  Moves/<TAG>_Throw.tres                         B+C, checked as if at 37.5 in the move list (NetsuCheckOrder):
                                                 after supers / specials / Overdrive / Burst / Pushblock, before the
                                                 normals, so 236 + B+C is still a super and B+C isn't a 5C
and appends the states to 0_<TAG>_Data.tres, the move to the stance, the grabbed state to the stance's
HitReactions at index GRABBED_REACTION (20 for everyone: a grab box names the reaction by its index in the THROWN
fighter's list), and sets the stance's throw break input (B+C) and state. The shared inputs go to
actors/_shared/sakuga/Inputs/51_Input_Throw.tres (B+C, not holding down), 52_Input_ThrowBreak.tres (B+C),
53_Input_HoldBack.tres (holding back: 1, 4 or 7).
"""
import sys, os, re, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import fdk
from fdk import *
from tres import Tres

FORCE = '--force' in sys.argv
BK = '_backup_stage_select/pre_throws'
INP = 'res://actors/_shared/sakuga/Inputs/'
THROW_INPUT, BREAK_INPUT, BACK_INPUT = INP + '51_Input_Throw.tres', INP + '52_Input_ThrowBreak.tres', INP + '53_Input_HoldBack.tres'
MOVE_OPP = ACT + 'NetsuMoveOpponentAction.cs'

GRABBED_REACTION = 20     # index in every fighter's HitReactions list (after the 20 Mahou ones)
CHECK_ORDER = 37.5        # where the neutral move check looks at the throw (see the top)
BREAK_WINDOW = 10         # frames frozen on the grab = the time to break it with B+C (Oct 27: 10)
GRAB_FRAMES = (3, 6)      # the grab box is out from frame 3 (4-frame start-up, Oct 27) until frame 6 (3 active frames)
THROW_LEN = 28            # a whiffed throw: 28 frames in all (punishable)
BACK_DISTANCE = -6500     # back throw: the opponent is put this far behind her (0.65 m), then thrown "forward"
BREAK_LEN = 16            # the throw break pose (both fighters, pushed apart by the engine)
BREAK_PUSH = 8            # ...for this many frames (0.53 m each)
GRAB_TIMEOUT = 90         # safety: a grabbed fighter that is never hit goes back to standing

IDLE, GROUND, AIR, MOVE, ATTACK, HITSTUN, BLOCKSTUN, KNOCKDOWN_F = 1, 2, 4, 8, 16, 32, 64, 128

# boxes in world px from her feet (x forward, y up; 100 px = 0.275 m)
GRAB_BOX = (40, 90, 320, 430)          # 0.11 - 0.88 m in front, 0.25 - 1.18 m up
HIT_BOX = (-40, 0, 470, 720)           # the throw's hit: anywhere the grabbed opponent can be

def throw_hit(damage, effect=6, gain=600):
    """the hit that ends a throw: launches them away into a knockdown (they can recover on landing)"""
    return attack(damage, 50, 0, kb=(-42000, 38000), air_kb=(-42000, 38000), reaction=7, air_reaction=7,
                  hitstun_type=KNOCKDOWN, kb_gravity=150000, air_gravity=150000, stop=14, gain=gain, opp_gain=200,
                  effect=effect, scaling=20)
KNEE = attack(350, 30, 0, kb=(0, 0), air_kb=(0, 0), reaction=1, air_reaction=5, stop=8, gain=200, opp_gain=50,
              effect=0, scaling=0)

# the borrowed poses: (animation, key index) -> copied with its sprite layers; hurtboxes come from the box state
# that animation shows at that key
FIGHTERS = {
  'cecilia': dict(tag='CEC',
      reach=[('48_CEC_5A', 0, 0), ('48_CEC_5A', 1, 3), ('48_CEC_5A', 2, 9), ('48_CEC_5A', 0, 18)],
      # grab with the sheathed blade, then an iai cut sends them flying
      throw=[('48_CEC_5A', 1, 0), ('49_CEC_5B', 1, 8), ('49_CEC_5B', 2, 14), ('48_CEC_5A', 0, 24)], throw_len=32,
      hits=[(8, 11, throw_hit(1100, effect=6))],
      grabbed=('16_CEC_Hit_Strong', 0), brk=('31_CEC_Stand_Blockstun', 0)),
  'flan': dict(tag='FLN',
      reach=[('48_FLN_5A', 0, 0), ('48_FLN_5A', 1, 3), ('48_FLN_5A', 2, 9), ('48_FLN_5A', 0, 18)],
      # grab, knee to the stomach, then a straight punch
      throw=[('48_FLN_5A', 1, 0), ('81_FLN_214A', 1, 6), ('49_FLN_5B', 1, 14), ('49_FLN_5B', 2, 21), ('48_FLN_5A', 0, 28)],
      throw_len=34, hits=[(6, 9, KNEE), (14, 17, throw_hit(750, effect=4, gain=400))],
      grabbed=('16_FLN_Hit_Strong', 0), brk=('31_FLN_Stand_Blockstun', 0)),
  'leticia': dict(tag='LET',
      reach=[('48_LET_5A', 0, 0), ('48_LET_5A', 1, 3), ('48_LET_5A', 2, 9), ('48_LET_5A', 0, 18)],
      # gun to the chest, then both guns at point blank
      throw=[('48_LET_5A', 1, 0), ('50_LET_5C', 1, 8), ('50_LET_5C', 2, 14), ('48_LET_5A', 0, 24)], throw_len=32,
      hits=[(8, 11, throw_hit(1100, effect=4))],
      grabbed=('16_LET_Hit_Strong', 0), brk=('31_LET_Stand_Blockstun', 0)),
  'noah': dict(tag='NOA',
      reach=[('48_NOA_5A', 0, 0), ('48_NOA_5A', 1, 3), ('48_NOA_5A', 2, 9), ('48_NOA_5A', 0, 18)],
      # the devil arm grabs, drains for a moment, then a straight devil-arm punch
      throw=[('48_NOA_5A', 1, 0), ('81_NOA_GRASP', 1, 6), ('50_NOA_5C', 1, 14), ('50_NOA_5C', 2, 21), ('48_NOA_5A', 0, 28)],
      throw_len=34, hits=[(6, 9, KNEE), (14, 17, throw_hit(800, effect=4, gain=400))],
      grabbed=('16_NOA_Hit_Strong', 0), brk=('31_NOA_Stand_Blockstun', 0)),
}

COMMAND_LINES = [["Throw", "B + C (close)", "4 + B+C throws behind you"],
                 ["Throw break", "B + C as you're grabbed", "%d-frame window" % BREAK_WINDOW]]


# ------------------------------------------------------------------ reading existing animations
def raw_fields(t, lines):
    """the fields of a sub-resource as fdk values (ExtResource -> Ext, the rest kept as written)"""
    f = {}
    for l in lines:
        k, _, v = l.partition(' = ')
        if k == 'script':
            continue
        m = re.fullmatch(r'ExtResource\("([^"]+)"\)', v)
        if m:
            e = t.ext_by_id(m.group(1)); f[k] = Ext(e['path'], e['type'])
        elif 'SubResource(' in v or 'ExtResource(' in v:
            raise SystemExit('nested resource in a copied field: ' + l)
        else:
            f[k] = Raw(v)
    return f

class Anim:
    def __init__(self, ch, name):
        self.res = 'res://actors/%s/AnimationData/%s_AnimData.tres' % (ch, name)
        self.t = Tres(open(res_file(self.res), encoding='utf-8').read())
        t = self.t
        self.keys = []
        for sid in re.findall(r'SubResource\("([^"]+)"\)', t.res_get('Animations') or ''):
            s = t.sub_get(sid); body = s[2]
            at = re.search(r'^AtFrame = (\d+)', '\n'.join(body), re.M)
            mods = []
            for mid in re.findall(r'SubResource\("([^"]+)"\)', '\n'.join(l for l in body if l.startswith('Modifiers'))):
                ms = t.sub_get(mid)
                mods.append((t.script_of(ms[2]), raw_fields(t, ms[2])))
            self.keys.append((int(at.group(1)) if at else 0, mods))
        self.boxes = []
        for sid in re.findall(r'SubResource\("([^"]+)"\)', t.res_get('Hitboxes') or ''):
            body = '\n'.join(t.sub_get(sid)[2])
            at = re.search(r'^AtFrame = (\d+)', body, re.M); hd = re.search(r'^HitboxData = ExtResource\("([^"]+)"\)', body, re.M)
            self.boxes.append((int(at.group(1)) if at else 0, t.ext_by_id(hd.group(1))['path']))
    def key(self, i, at):
        """an AnimationSettings Obj: the i-th key's sprite layers, at another frame"""
        mods = [Obj(script, **fields) for script, fields in self.keys[i][1]]
        return Obj(SR + 'AnimationSettings.cs', AtFrame=at or None, Modifiers=mods)
    def hitbox_at(self, i):
        """the hitbox file this animation shows at its i-th key"""
        frame = self.keys[i][0]; cur = self.boxes[0][1]
        for at, path in self.boxes:
            if at <= frame: cur = path
        return cur

def hurt_of(hitbox_res):
    """(hurtbox elements as Objs, pushbox res) of a hitbox file"""
    t = Tres(open(res_file(hitbox_res), encoding='utf-8').read())
    els = []
    for sid in re.findall(r'SubResource\("([^"]+)"\)', t.res_get('Hitboxes') or ''):
        s = t.sub_get(sid)
        typ = re.search(r'^HitboxType = (\d+)', '\n'.join(s[2]), re.M)
        if typ and int(typ.group(1)) != HURT:
            continue
        els.append(Obj(SR + 'HitboxElement.cs', **raw_fields(t, s[2])))
    pb = t.res_get('Pushbox')
    m = re.fullmatch(r'ExtResource\("([^"]+)"\)', pb or '')
    return els, (t.ext_by_id(m.group(1))['path'] if m else None)


# ------------------------------------------------------------------ writing
def write_anim(res, duration, keys, box_states):
    """keys: [AnimationSettings Obj]; box_states: [(at, stage, hitbox res)]"""
    hs = [Obj(SR + 'HitboxState.cs', AtFrame=a or None, animationStage=s or None, HitboxData=Ext(r)) for a, s, r in box_states]
    write(res, Obj(SR + 'AnimationData.cs', Duration=duration, Animations=keys, Hitboxes=hs), force=FORCE)

def write_box(res, hurt_from=None, extra=(), pushbox=True):
    els, pb = hurt_of(hurt_from) if hurt_from else ([], PUSHBOX_STD)
    write(res, Hitboxes(list(els) + list(extra), (pb or PUSHBOX_STD) if pushbox else None), force=FORCE)

def shared_inputs():
    # B+C, not holding down (2B / 2C stay crouching normals); the engine lets B and C come up to 2 frames apart
    write(THROW_INPUT, Obj(SR + 'MotionInputs.cs', ValidInputs=[Obj(SR + 'InputOption.cs', Inputs=[
        Obj(SR + 'InputSequence.cs', Directional=1, DirectionalMode=4, Buttons=6)])]), force=FORCE)
    write(BREAK_INPUT, Obj(SR + 'MotionInputs.cs', ValidInputs=[Obj(SR + 'InputOption.cs', Inputs=[
        Obj(SR + 'InputSequence.cs', Buttons=6)])]), force=FORCE)
    write(BACK_INPUT, Obj(SR + 'MotionInputs.cs', ValidInputs=[Obj(SR + 'InputOption.cs', Inputs=[
        Obj(SR + 'InputSequence.cs', Directional=2, DirectionalMode=1)])]), force=FORCE)


def one(ch, cfg):
    tag = cfg['tag']; A = 'res://actors/%s/' % ch
    hb = lambda n: A + 'Hitboxes/%s_Hitbox_%s.tres' % (tag, n)
    an = lambda n: A + 'AnimationData/%s_%s_AnimData.tres' % (tag, n)
    st = lambda n: A + 'States/%s_%s.tres' % (tag, n)
    anims = {}
    def anim(name):
        if name not in anims: anims[name] = Anim(ch, name)
        return anims[name]
    data = A + '0_%s_Data.tres' % tag
    stance = A + 'Stances/%s_Stance_Main.tres' % tag
    move = A + 'Moves/%s_Throw.tres' % tag

    # where the states go (indices first: the states name each other by index)
    names = ['Throw', 'ThrowForward', 'ThrowBack', 'Grabbed', 'ThrowBreak']
    dt = Tres(open(res_file(data), encoding='utf-8').read())
    refs = list_refs(dt, 'States'); idx = {}; n_next = len(refs)
    for nm in names:
        i = dt.ext_id_for_path(st(nm))
        pos = refs.index('ExtResource("%s")' % i) if i and ('ExtResource("%s")' % i) in refs else None
        if pos is None:
            pos = n_next; n_next += 1
        idx[nm] = pos

    # --- the reach (grab box on GRAB_FRAMES) and the whiff
    r = cfg['reach']
    reach_keys = [anim(a).key(k, af) for a, k, af in r]
    grab = box(THROW_T, *GRAB_BOX, GroundThrow=True, AirThrow=False, ThrowHitstop=BREAK_WINDOW,
               ThrowHitstopAfterHit=BREAK_WINDOW, ThrowHitReaction=GRABBED_REACTION)
    reach_pose = anim(r[1][0]).hitbox_at(r[1][1])
    write_box(hb('Throw_0'), anim(r[0][0]).hitbox_at(r[0][1]))
    write_box(hb('Throw_1'), reach_pose, [grab])
    write_box(hb('Throw_2'), reach_pose)
    write_box(hb('Throw_3'), anim(r[2][0]).hitbox_at(r[2][1]))
    write_anim(an('Throw'), THROW_LEN, reach_keys,
               [(0, 0, hb('Throw_0')), (GRAB_FRAMES[0], 1, hb('Throw_1')), (GRAB_FRAMES[1], 2, hb('Throw_2')),
                (r[2][2], 2, hb('Throw_3')), (r[3][2], 2, hb('Throw_0'))])

    # --- the throw: strike-invincible until the last hit has landed, then the recovery poses' hurtboxes
    th = cfg['throw']; hits = cfg['hits']
    throw_keys = [anim(a).key(k, af) for a, k, af in th]
    states = [(0, 0, hb('ThrowHit_hold'))]
    write_box(hb('ThrowHit_hold'))     # nothing hittable (no hurtboxes), pushbox kept
    for n, (f0, f1, props) in enumerate(hits):
        write_box(hb('ThrowHit_%d' % n), extra=[box(HIT_T, *HIT_BOX, **props)])
        states.append((f0, 1, hb('ThrowHit_%d' % n)))
        states.append((f1, 2, hb('ThrowHit_hold')))
    last_hit_end = hits[-1][1]
    for n, (a, k, af) in enumerate(th):
        if af > last_hit_end:
            write_box(hb('ThrowHit_rec%d' % n), anim(a).hitbox_at(k))
            states.append((af, 2, hb('ThrowHit_rec%d' % n)))
    states.sort(key=lambda s: s[0])
    write_anim(an('ThrowHit'), cfg['throw_len'], throw_keys, states)

    # --- grabbed (the thrown fighter) and the throw break pose
    ga, gk = cfg['grabbed']
    write_box(hb('Grabbed'), anim(ga).hitbox_at(gk))
    write_anim(an('Grabbed'), GRAB_TIMEOUT, [anim(ga).key(gk, 0)], [(0, 0, hb('Grabbed'))])
    ba, bk = cfg['brk']
    write_box(hb('ThrowBreak'), anim(ba).hitbox_at(bk))
    write_anim(an('ThrowBreak'), BREAK_LEN, [anim(ba).key(bk, 0)], [(0, 0, hb('ThrowBreak'))])

    # --- states
    to_idle = [ev([state_ended()], [play_state(0)])]
    write(st('Throw'), State('Throw', COMBAT, an('Throw'), transitions=to_idle, enter=[movex(0)],
                             hit_confirm=[ev([check_input(BACK_INPUT)], [play_state(idx['ThrowBack'])]),
                                          ev([check_input(BACK_INPUT, not_=True)], [play_state(idx['ThrowForward'])])],
                             ai=ATTACK | GROUND), force=FORCE)
    # the grab just landed: frame 0 is frozen for the break window; the hits' boxes come from the animation.
    # Hits are reset after the freeze (the grab counted as one) and before every further hit.
    tick = [ev([at(1)], [reset_hit(), movex(0)])] + [ev([at(f0)], [reset_hit()]) for f0, f1, p in hits[1:]]
    write(st('ThrowForward'), State('Throw Forward', COMBAT, an('ThrowHit'), transitions=to_idle, tick=tick,
                                    ai=ATTACK | GROUND), force=FORCE)
    back_tick = [ev([at(1)], [Obj(MOVE_OPP, X=BACK_DISTANCE, TurnAround=True), reset_hit(), movex(0)])] + tick[1:]
    write(st('ThrowBack'), State('Throw Back', COMBAT, an('ThrowHit'), transitions=to_idle, tick=back_tick,
                                 ai=ATTACK | GROUND), force=FORCE)
    write(st('Grabbed'), State('Grabbed', HIT_REACTION, an('Grabbed'), transitions=to_idle,
                               enter=[stop_knockback(), movex(0), movey(0)], ai=HITSTUN | GROUND), force=FORCE)
    # the engine pushes both apart (SakugaActor.ThrowEscapeAction); stop after BREAK_PUSH frames (~1.5 m apart)
    write(st('ThrowBreak'), State('Throw Break', COMBAT, an('ThrowBreak'), transitions=to_idle,
                                  tick=[ev([at(BREAK_PUSH)], [stop_knockback(), movex(0)])], ai=GROUND), force=FORCE)

    # --- the fighter's state list
    def fn_data(t):
        refs = list_refs(t, 'States')
        for nm in names:
            i = t.ext_id_for_path(st(nm)) or t.add_ext('Resource', st(nm), res_uid(st(nm)), prefer_id='st_%s_%s' % (tag, nm))
            ref = 'ExtResource("%s")' % i
            if ref not in refs:
                refs.append(ref)
            assert refs.index(ref) == idx[nm], (nm, refs.index(ref), idx[nm])
        t.res_set('States', '[' + ', '.join(refs) + ']')
    edit_tres(data, fn_data, BK, 'throw states')

    # --- the move
    # accept_combat: B+C pressed during the end of another move is kept in the buffer like a normal (it would
    # otherwise fall through to 5C); it is never a cancel (no move lists it)
    write(move, Move('Throw', idx['Throw'], THROW_INPUT, priority=7, move_end=2, accept_combat=True, accept_null=True,
                     overridable=False, extra={'NetsuCheckOrder': CHECK_ORDER}), force=FORCE)
    mi = ensure_moves(stance, [move], BK)[move]

    # --- the stance: grabbed reaction at GRABBED_REACTION, throw break input and state
    def fn_stance(t):
        hr = t.res_get('HitReactions'); vals = [int(x) for x in re.findall(r'-?\d+', hr.split('(', 1)[1])]
        if idx['Grabbed'] not in vals:
            if len(vals) != GRABBED_REACTION:
                raise SystemExit('%s: HitReactions has %d entries, expected %d' % (ch, len(vals), GRABBED_REACTION))
            vals.append(idx['Grabbed'])
        elif vals.index(idx['Grabbed']) != GRABBED_REACTION:
            raise SystemExit('%s: the grabbed state is at HitReactions[%d], not %d' % (ch, vals.index(idx['Grabbed']), GRABBED_REACTION))
        t.res_set('HitReactions', 'PackedInt32Array(%s)' % ', '.join(str(v) for v in vals))
        i = t.ext_id_for_path(BREAK_INPUT) or t.add_ext('Resource', BREAK_INPUT, res_uid(BREAK_INPUT), prefer_id='in_throwbreak')
        t.res_set('ThrowEscapeInput', 'ExtResource("%s")' % i, after='BlockReactions')
        t.res_set('GroundThrowEscapeState', str(idx['ThrowBreak']))
        t.res_set('AirThrowEscapeState', str(idx['ThrowBreak']))
    edit_tres(stance, fn_stance, BK, 'throw break')

    # --- the command list (pause menu)
    cl = os.path.join(fdk.PROJ, 'actors', ch, 'command_list.json')
    d = json.load(open(cl, encoding='utf-8'))
    for sec in d['sections']:
        if sec['title'] == 'System':
            sec['moves'] = [m for m in sec['moves'] if m[0] not in ('Throw', 'Throw break')]
            at_ = next((n for n, m in enumerate(sec['moves']) if m[0] == 'Burst'), len(sec['moves']))
            sec['moves'][at_:at_] = COMMAND_LINES
    cur = open(cl, encoding='utf-8').read()
    txt = json.dumps(d, indent='\t', ensure_ascii=False) + ('\n' if cur.endswith('\n') else '')
    if cur != txt:
        open(cl, 'w', encoding='utf-8').write(txt)
    print('%s: Throw = move %d; states %s; grabbed = HitReactions[%d]' % (ch, mi, idx, GRABBED_REACTION))


def main():
    names = [a for a in sys.argv[1:] if not a.startswith('--')] or list(FIGHTERS)
    shared_inputs()
    for ch in names:
        one(ch, FIGHTERS[ch])
    print('\n'.join(fdk.LOG))


if __name__ == '__main__':
    main()
