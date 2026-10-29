"""CECILIA'S MOVES (Oct 24, second pass): the move list of the HTML prototype ("Cecilia Duel"),
built from her finished drawings.

  236A / 236B  Dash Slash            dash, then a slash (B: longer; knocks them back a short way, and if that
                                     carries them into a wall they bounce off it high enough to follow up)
  236C         EX Dash Slash         (2 bars) strike-invincible dash; on hit she grabs them in a lightning rush:
                                     four passes through them, then a cross slash that ends in a hard knockdown
  214A / 214B  Lightning Dash        charge, strike-invincible lightning travel that stops in front of them,
                                     then a slash (mid, -2 on block). Oct 25: a rekka: 214 + A/B again = second slash
                                     (mid, -7 on block), and again = third slash (mid, hard knockdown on hit, -10)
  214C         EX Lightning Dash     (2 bars) three slashes, the last knocks down hard
  623A / 623B  Teleport Slash        invincible start: she vanishes into a slash that sweeps forward from where she
                                     stood (launches), reappears ahead and drops. Oct 25: lower, further, quick fall
  623C         EX Teleport Slash     (2 bars) two-hit X cut
  j.236A / B   Skyfall Slash         (Oct 25, in the air) a short hang, then a fast diving slash down-forward to the
                                     floor; slams an airborne opponent down (an air combo ender)
  j.236C       EX Skyfall Slash      (2 bars) invincible dive, and a lightning X on landing that hits both sides and
                                     pops them up (+3 on block)
  236236 + any Thunder Plunge        (super) blade into the ground, five lightning hits all around her; in the air
                                     she drops blade-first and plunges on landing
  214214 + any Counter · Thunderclap (super) counter stance; if they hit her she answers with a full combo that
                                     ends in an explosion; a whiff leaves her open. The super flash and cut-in
                                     only come when the counter catches something (the stance gives nothing away)
Supers also come out with 236 + B+C / 214 + B+C (the button scheme the other fighters use).
Costs: EX 2 bars, supers 3 bars (the game's 6-bar Craft Gauge; the prototype's 3-bar gauge charges 1 and 2).

    python moves_cecilia.py          writes everything (Godot closed, or reload the project after)
    python moves_cecilia.py --dry    only prints what it would do
    python moves_cecilia.py --states only rewrites the state files (movement, timing, cancels into states)

Edit the tables below and run again: frame timings, damage, movement. Files you change in Godot
afterwards are kept (the script says SKIPPED); add --force to overwrite them with the table values.
Pipeline per move: manifest keys -> build.py (sprites + timeline) -> hitbox files -> hitfit.py
(boxes fitted to the drawings) -> state, input, move files -> registered in 0_CEC_Data / the stance.
Speeds are engine speeds (units per second, 10000 = 1 m; position += speed / 60 every frame).
Preview: python movereel.py cecilia out.gif 79_CEC_236A ...   (--chain for a move and its follow-ups)
Also here: her 2B chains into her other normals, j.C falls like j.A / j.B, 5B's blade and 5C's slash
(derive_cecilia.py makes the pictures).
"""
import sys, os, json, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import fdk
from fdk import *
from tres import Tres

CH, TAG = 'cecilia', 'CEC'
A = 'res://actors/cecilia/'
BK = '_backup_stage_select/pre_cecilia_movelist'
FORCE = '--force' in sys.argv
DRY = '--dry' in sys.argv
STATES_ONLY = '--states' in sys.argv
def _arg(name, default=None):
    for a in sys.argv:
        if a.startswith('--%s=' % name): return a.split('=', 1)[1]
    return default
# --phase=1,2,3,4 runs only those steps (all by default): 1 manifest + skeleton files, 2 sprites (build.py),
# 3 boxes (hitfit.py), 4 states / inputs / moves / registering. --anims=a,b limits 2 and 3 to those animations.
PHASES = set(int(x) for x in _arg('phase', '1,2,3,4').split(','))
ONLY = _arg('anims')
SKEL = not DRY and 1 in PHASES
UPX = 27.5
INP = 'res://actors/_shared/sakuga/Inputs/'
IDLE, FALLING, LANDING = 0, 10, 11
FIRST_SPECIAL = 41          # stance moves 0-40 are the shared system/normal moves; hers start here
EX, SUPER = 4000, 6000

def hb(name): return A + 'Hitboxes/%s.tres' % name
def an(name): return A + 'AnimationData/%s_AnimData.tres' % name
def fx(f): return {'fx': f, 'fx_always': True}

# ---------------------------------------------------------------------------------------------
# attack properties: the prototype's damage x 100 (its health is 100, ours 10000), its hitstun / blockstun /
# hitstop; pushback and launches in this game's units. First pass: tune in play.
WALL = dict(BounceTime=90, BounceXIntensity=35)          # 236B: a wall bounces them back (and pops them up: tune_movement.py)
DS = {
  'A': attack(900, 20, 14, kb=(-55000, 0), air_kb=(-30000, 35000), reaction=1, air_reaction=5, stop=8, gain=400),
  # Oct 24: a short push (about 2.5 m with the slide) instead of across the screen; near a wall they hit it and bounce
  'B': attack(1000, 40, 15, kb=(-50000, 26000), air_kb=(-50000, 26000), reaction=7, air_reaction=7, hitstun_type=KNOCKDOWN,
              kb_gravity=120000, air_gravity=120000, block_kb=(-48000, 0), stop=10, gain=400, extra=WALL),
  'C_GRAB': attack(300, 60, 15, kb=(0, 0), air_kb=(0, 0), reaction=1, air_reaction=5, stop=10, gain=0, scaling=2, air_gravity=1,
                   block_kb=(-30000, 0)),
  'C_SLASH': attack(700, 20, 15, kb=(-55000, 0), air_kb=(-30000, 35000), reaction=1, air_reaction=5, stop=8, gain=0, scaling=4),
}
RUSH_HIT = attack(300, 60, 20, kb=(0, 0), air_kb=(0, 0), reaction=1, air_reaction=5, stop=4, gain=0, scaling=2, air_gravity=1,
                  pushback=0)
# Oct 25: the last hit pops them up only a little (was 72000): they're back on the floor (hard knockdown) before she
# recovers, so nothing combos after it any more, but it still shows the launch
# Oct 25 night (bigger EX moves): the last hit blasts them high and far across the screen; they come down a long way off
# with a hard knockdown, so it still doesn't combo
RUSH_END = attack(1000, 60, 30, kb=(-85000, 80000), air_kb=(-85000, 80000), reaction=7, air_reaction=7, hitstun_type=HARD_KNOCKDOWN,
                  kb_gravity=200000, air_gravity=200000, stop=20, gain=0, scaling=0, pushback=0)
def _q(d, last, ex=False):
    if last:
        return attack(d, 22, 14, kb=(-45000, 42000) if ex else (-55000, 0), air_kb=(-40000, 42000) if ex else (-30000, 35000),
                      reaction=7 if ex else 1, air_reaction=7 if ex else 5, hitstun_type=KNOCKDOWN if ex else BASIC,
                      kb_gravity=220000 if ex else None, stop=10, gain=0 if ex else 350, scaling=4 if ex else 10)
    return attack(d, 24, 16, kb=(-12000, 0), air_kb=(-8000, 25000), reaction=1, air_reaction=5, stop=6,
                  gain=0 if ex else 300, scaling=4 if ex else 10)
# Oct 25: Lightning Dash is a rekka (three slashes, 214 + A/B for each next one), all mids:
#   R1 (after the dash) -2 on block, R2 -7 (punishable), R3 -10 and a hard knockdown on hit.
#   (block advantage = blockstun - (frames from the hit to the end of the state))
R1 = attack(800, 18, 14, kb=(-14000, 0), air_kb=(-10000, 25000), reaction=1, air_reaction=5, stop=9, gain=300)
R2 = attack(700, 19, 14, kb=(-14000, 0), air_kb=(-10000, 25000), reaction=1, air_reaction=5, stop=9, gain=300)
R3 = attack(1000, 30, 16, kb=(-40000, 45000), air_kb=(-40000, 45000), reaction=7, air_reaction=7, hitstun_type=HARD_KNOCKDOWN,
            kb_gravity=220000, stop=13, gain=350)
# Oct 25 night (bigger EX moves): the third slash throws them sky-high
EX3 = attack(900, 22, 16, kb=(-30000, 112000), air_kb=(-30000, 112000), reaction=8, air_reaction=8, hitstun_type=HARD_KNOCKDOWN,
             kb_gravity=200000, air_gravity=200000, stop=16, gain=0, scaling=4)
LD = {'C': [_q(500, False, True), _q(500, False, True), EX3]}
TS = {   # Oct 25: launched away and up (was nearly straight up)
  'A': [attack(1000, 24, 14, kb=(-28000, 52000), air_kb=(-28000, 52000), reaction=8, air_reaction=8, hitstun_type=KNOCKDOWN,
               kb_gravity=220000, stop=10, gain=400)],
  'B': [attack(1200, 24, 14, kb=(-30000, 58000), air_kb=(-30000, 58000), reaction=8, air_reaction=8, hitstun_type=KNOCKDOWN,
               kb_gravity=220000, stop=10, gain=400)],
  'C': [attack(600, 24, 14, kb=(-3000, 40000), air_kb=(-3000, 40000), reaction=8, air_reaction=8, hitstun_type=KNOCKDOWN,
               kb_gravity=220000, stop=6, gain=0, scaling=4),
        # Oct 25 night: the X cut's second slash launches them very high
        attack(900, 24, 14, kb=(-10000, 120000), air_kb=(-10000, 120000), reaction=8, air_reaction=8, hitstun_type=HARD_KNOCKDOWN,
               kb_gravity=210000, air_gravity=210000, stop=14, gain=0, scaling=4)],
}
# Skyfall Slash (j.236, Oct 25): a mid; on the ground it's a normal hit, an airborne opponent is slammed to the floor
J236 = {'A': attack(900, 18, 12, kb=(-20000, 0), air_kb=(-15000, -60000), reaction=1, air_reaction=9, air_hitstun_type=KNOCKDOWN,
                    stop=10, gain=350),
        'B': attack(1000, 18, 12, kb=(-22000, 0), air_kb=(-15000, -60000), reaction=1, air_reaction=9, air_hitstun_type=KNOCKDOWN,
                    stop=11, gain=350),
        'C': attack(600, 30, 16, kb=(-6000, 0), air_kb=(-4000, -30000), reaction=1, air_reaction=5, stop=8, gain=0, scaling=4)}
# the EX's lightning X on landing: hits both sides, pops them up for a follow-up (+3 on block: blockstun 20, 17 frames)
# Oct 25 night: the lightning X is a pillar that launches them high (juggle after it)
J236_X = attack(900, 50, 20, kb=(0, 100000), air_kb=(0, 100000), reaction=8, air_reaction=8, hitstun_type=KNOCKDOWN,
                kb_gravity=210000, air_gravity=210000, stop=14, gain=0, scaling=4)
# Thunder Plunge: four hits hold them, the fifth launches; Counter Thunderclap: every hit keeps them in place, the explosion ends it
TP = [attack(450, 30, 16, kb=(0, 0), air_kb=(0, 15000), reaction=1, air_reaction=5, stop=5, gain=0, scaling=3, pushback=0)
      for _ in range(4)]
TP_END = attack(900, 50, 16, kb=(-20000, 75000), air_kb=(-20000, 75000), reaction=8, air_reaction=8, hitstun_type=KNOCKDOWN,
                kb_gravity=220000, stop=12, gain=0, scaling=0)
CT = [attack(d, 170, 30, kb=(0, 0), air_kb=(0, 0), reaction=1, air_reaction=5, stop=s, gain=0, scaling=2, air_gravity=150000)
      for d, s in [(400, 8), (400, 10), (400, 10), (400, 10), (500, 8)]]
CT_END = attack(1300, 50, 30, kb=(-25000, 60000), air_kb=(-25000, 60000), reaction=7, air_reaction=7, hitstun_type=HARD_KNOCKDOWN,
                kb_gravity=200000, stop=20, gain=0, scaling=0)

# boxes the fitter can't guess (world px: x forward from her, y up from the floor)
AOE = [[-640, -10, 640, 360]]                 # Thunder Plunge: the surge all around her
DP_BOX = {'A': [[-40, 30, 520, 500]], 'B': [[-40, 30, 600, 540]], 'C': [[-60, 30, 600, 560]]}   # 623: the slash sweeping forward
DIVE_BOX = [[-40, -100, 420, 520]]            # j.236: the downward swing ahead of her (head height to below her feet), then the dive
XBURST = [[-430, -10, 430, 520]]              # j.236C: the lightning X on landing, both sides
RUSH_BOX = [[-260, -10, 260, 440]]            # the rush passes: she cuts through them
BEHIND = [[-480, -10, -120, 520]]             # the rush finish: behind her
# Oct 26: the air Thunder Plunge drags them down: anyone the plunge touches on the way down is grabbed by the lightning
# and carried to the floor with her (S2_drag: NetsuHoldOpponentAction), so the landing surge hits them all the way.
# DRAG_BOX: world px around her as she falls (below her feet and a little in front); DRAG_HOLD: where they're carried
# (engine units, x along her facing, y above her feet).
DRAG_BOX = [[-140, -320, 300, 380]]
DRAG_HOLD = (5500, 0)
TP_DRAG = attack(300, 90, 20, kb=(0, 0), air_kb=(0, 0), reaction=1, air_reaction=5, hitstun_type=HARD_KNOCKDOWN, stop=8,
                 gain=0, scaling=2, air_gravity=1)
def hold_opp(x, y):   # keeps the opponent (while being hit) at (x along her facing, y above her feet), every frame it runs
    return Obj(ACT + 'NetsuHoldOpponentAction.cs', Offset=V2i(x, y))
BOOM = [[-760, -10, -60, 560]]                # the Thunderclap explosion: behind her (the drawing's boom is 400 px back)
def boom(f): return {'fx': f, 'fx_dx': -400, 'fx_always': True}

# ---------------------------------------------------------------------------------------------
# the moves.  keys: [frame, at, {options}] (see build.py); boxes: [at, stage, kind, props, (unused), manual box]
#   kind 'pose' = hurtboxes only (fitted), 'pose+prox' = + proximity guard, 'atk' = hurt + proximity + attack (fitted),
#   'atk_inv' = attack only (no hurtboxes: invincible), 'none' = nothing hittable, 'counter' = counter box only;
#   '-pass' = no pushbox either. A manual box (6th item) replaces the fitted attack box.
# input: (motion, [buttons]); a move without 'input' is a state only (reached from another state).
SLOTS = dict(LD_A=73, LD_B=74, LD_A_SL=75, LD_C=76, LD_B_SL=77, LD_C_SL=78, RUSH=97, TP_LAND=98,
             R2=106, R3=107, J236A=108, J236B=109, J236C=110, J236_LAND=111, J236C_LAND=112)
def ld(v, charge, travel, speed, slash_slot):
    """Lightning Dash: charge, then strike-invincible lightning travel that stops ~0.9 m in front of them (or after
    `travel` frames) and goes into the slashes"""
    t0 = charge
    return dict(duration=charge + travel + 2,
        keys=[['ld_charge', 0], ['ld_hold', t0]] + [['ld_loop%d' % (i % 3 + 1), t0 + 3 + 2 * i] for i in range((travel - 3) // 2 + 1)],
        boxes=[[0, 0, 'pose'], [t0, 0, 'none']],
        tick=[(t0, movex(speed)), (t0, frame_props(INV_STRIKE | INV_THROW))],
        enter=[change_side(), movex(0)],
        transitions=[ev([at_range(t0 + 1, t0 + travel), rel_x(-9000)], [play_state(slash_slot)]),
                     ev([at_range(t0 + travel, 999)], [play_state(slash_slot)])],
        exit=[movex(0)], afterimages=True, ai=0x10 | 2)
def rekka(pic, hit, attack, block_adv, step=0):
    """one slash of the Lightning Dash rekka: `pic` from frame 0 (a step forward first when `step`), the attack on
    frames hit..hit+2, then the recovery pose. The state's length is worked out from the block advantage wanted."""
    duration = hit + attack['GroundBlockstun'] - block_adv - 1     # (measured in the game: one frame less)
    tick = [(hit, movex(0))]
    if step: tick = [(0, movex(step))] + tick
    return dict(duration=duration, keys=[[pic, 0], ['ld_rec', hit + 6]],
                boxes=[[0, 0, 'pose'], [hit, 1, 'atk', attack], [hit + 3, 2, 'pose'], [hit + 6, 2, 'pose']],
                tick=tick, enter=[change_side(), movex(0)] if step else [movex(0)], ai=0x10 | 2)
def ld_slash(attacks, rec, ex=False):
    """the slashes after the dash: 8 frames each (hit on their 2nd-4th frame), then the recovery pose"""
    pics = ['ld_s1', 'ld_s2', 'ld_s3']
    n = len(attacks)
    keys = [[pics[i], 8 * i] for i in range(n)] + [['ld_rec', 8 * n]]
    boxes = [[0, 0, 'pose']]
    for i, a in enumerate(attacks):
        if i: boxes.append([8 * i, 2, 'pose'])
        boxes += [[8 * i + 2, 1, 'atk', a], [8 * i + 5, 2, 'pose']]
    boxes.append([8 * n, 2, 'pose'])
    tick = [(8 * i + 2, reset_hit()) for i in range(1, n)] + [(6, frame_props(0))]
    return dict(duration=8 * n + rec, keys=keys, boxes=boxes, tick=tick,
                enter=[movex(0), frame_props(INV_STRIKE | INV_THROW)], exit=[frame_props(0)], ai=0x10 | 2)
def tp(start, inv, hits, re_x, re_y, ex=False, box=None):
    """Teleport Slash: startup, she vanishes (9 frames; the slash sweeps forward from where she stood), reappears
    ahead and a little up, hangs 3 frames and drops (normal gravity) into the landing state.
    Oct 25: was 11 frames vanished, reappearing high and floating down for ~40 frames (about 80 frames in all);
    now about 42-45 frames in all, like other games' uppercuts, and more forward than up."""
    v = start; re = start + 9
    boxes = [[0, 0, 'pose'], [v, 0, 'none-pass']]
    tick = [(inv, frame_props(0)), (re, teleport(re_x, re_y, SELF, SELF)), (re, movex(0)), (re, movey(0))]
    for i, (fr, a) in enumerate(hits):
        boxes += [[v + fr, 1, 'atk_inv-pass', a, None, box], [v + fr + 2, 0, 'none-pass']]
        if i: tick.append((v + fr, reset_hit()))
    boxes += [[re, 2, 'pose'], [re + 3, 2, 'pose']]
    return dict(duration=200, keys=[['dp_1', 0], ['dp_fx_ex_flat' if ex else 'dp_fx_flat', v], ['dp_4', re], ['dp_5', re + 3]],
                boxes=boxes, tick=tick, tick_ranges=[((re + 3, 999), gravity())],
                enter=[change_side(), movex(0), frame_props(INV_STRIKE | INV_THROW)], exit=[frame_props(0)],
                transitions=[ev([at_range(re + 2, 999), on_ground()], [play_state(SLOTS['TP_LAND'])]),
                             ev([state_ended()], [play_state(FALLING)])],
                priority=8 if not ex else 9, ai=0x10 | 2 | (0x1000 if ex else 0))

def dive(v, hover, sx, sy):
    """Skyfall Slash: a short hang in the air (sword up), then a straight dive down-forward at (sx, sy) with the
    blade out (the attack, until she lands), into the landing (A/B) or the lightning X (C). Strike-invincible (C)."""
    ex = v == 'C'
    land = SLOTS['J236C_LAND'] if ex else SLOTS['J236_LAND']
    return dict(duration=90, keys=[['jc_1', 0], ['jc_2', hover, fx('j236_trail')]],
        boxes=[[0, 0, 'none' if ex else 'pose'], [hover, 1, 'atk_inv' if ex else 'atk', J236[v], None, DIVE_BOX]],
        tick=[(0, movex(0)), (0, movey(0)), (hover, movex(sx)), (hover, movey(sy))],
        tick_ranges=[((0, hover - 1), gravity(1))],
        enter=[frame_props(INV_STRIKE | INV_THROW)] if ex else [], exit=[frame_props(0)] if ex else [],
        transitions=[ev([at_range(hover, 999), on_ground()], [play_state(land)])], loop=True,
        afterimages=True, ai=0x10 | 4 | (0x1000 if ex else 0))

MOVES = {
  # --- 236 Dash Slash -------------------------------------------------------------------------------
  '236A': dict(slot=79, name='Dash Slash', input=('236', ['A']), move_file='57_CEC_236A', hbp='40_Hitbox_236A',
      duration=33, keys=[['d236_1', 0], ['d236_2', 4], ['d236_3', 11], ['d236_4', 19]],
      boxes=[[0, 0, 'pose+prox'], [4, 0, 'pose+prox'], [11, 1, 'atk', DS['A']], [15, 2, 'pose'], [19, 2, 'pose']],
      tick=[(4, movex(108000)), (11, movex(30000)), (13, movex(0))], enter=[change_side(), movex(0)], priority=7,
      cancels=[('S1', HIT, (11, 40)), ('S2', HIT, (11, 40))], ai=0x10 | 2),
  '236B': dict(slot=80, name='Dash Slash', input=('236', ['B', 'C']), move_file='58_CEC_236B', hbp='41_Hitbox_236B',
      duration=41, keys=[['d236_1', 0], ['d236_2', 6], ['d236_3', 15], ['d236_4', 23]],
      boxes=[[0, 0, 'pose+prox'], [6, 0, 'pose+prox'], [15, 1, 'atk', DS['B']], [19, 2, 'pose'], [23, 2, 'pose']],
      tick=[(6, movex(115000)), (15, movex(30000)), (17, movex(0))], enter=[change_side(), movex(0)], priority=7,
      cancels=[('S1', HIT, (15, 48)), ('S2', HIT, (15, 48))], ai=0x10 | 2),
  '236C': dict(slot=81, name='EX Dash Slash', input=('236', ['C']), move_file='59_CEC_236C', hbp='42_Hitbox_236C',
      duration=38, keys=[['d236_1', 0], ['d236_2', 3], ['d236_3', 15], ['d236_4', 22]],
      boxes=[[0, 0, 'none'], [3, 1, 'atk_inv', DS['C_GRAB']], [15, 1, 'atk', DS['C_SLASH']], [18, 2, 'pose']],
      tick=[(3, movex(150000)), (15, movex(25000)), (15, reset_hit()), (17, movex(0)), (17, frame_props(0))],
      enter=[change_side(), movex(0), frame_props(INV_STRIKE | INV_THROW)], exit=[frame_props(0)],
      hit_confirm=[ev([at_range(3, 14), check_hit(HIT)], [play_state(SLOTS['RUSH'])])],   # the dash grabs; the slash after it doesn't
      meter=EX, flash=15, priority=9, afterimages=True, ai=0x10 | 2 | 0x1000),
  'RUSH': dict(slot=SLOTS['RUSH'], name='EX Dash Slash (rush)', hbp='57_Hitbox_DashRush', duration=105,
      keys=[['d236_3', 0], ['d236_2', 8], ['d236_3', 13], ['d236_2', 20], ['d236_3', 25], ['d236_2', 32], ['d236_3', 37],
            ['d236_2', 44], ['d236_3', 49], ['d236_4', 56]],
      boxes=[[0, 0, 'none-pass']] + sum([[[8 + 12 * k + 2, 1, 'atk_inv-pass', RUSH_HIT, None, RUSH_BOX],
                                          [8 + 12 * k + 5, 0, 'none-pass']] for k in range(4)], []) +
            [[78, 1, 'atk_inv-pass', RUSH_END, None, BEHIND], [82, 2, 'none-pass'], [96, 2, 'pose']],
      tick=[(0, teleport(7900, 0, OPPONENT, WORLD)), (78, camera_shake(0.06, 16)), (96, frame_props(0))] +
           sum([[(8 + 12 * k, change_side()), (8 + 12 * k, movex(237000)), (8 + 12 * k + 4, movex(0)),
                 (8 + 12 * k + 2, reset_hit())] for k in range(4)], []) + [(78, reset_hit())],
      enter=[movex(0), movey(0), frame_props(INV_STRIKE | INV_THROW | INV_PROJ)], exit=[frame_props(0)],
      priority=10, afterimages=True, ai=0x10 | 2 | 0x1000),
  # --- 214 Lightning Dash (Oct 25: a rekka) ------------------------------------------------------------
  # 214A / 214B: the dash, then the first slash. 214 + A/B again during it (hit or block) = the second slash,
  # and again during that = the third. R2 / R3 only come out from the slash before them (IsSequenceFromStates).
  # The follow-up comes first in the cancel lists: two 214s in a row also read as the 214214 counter super.
  # (SkipCheck: they are never looked for in neutral, only as these cancels.)
  '214A': dict(slot=SLOTS['LD_A'], name='Lightning Dash', input=('214', ['A']), move_file='66_CEC_214A', hbp='51_Hitbox_214A',
      priority=7, cancels=[('214R2', HIT | BLOCK, (2, 17)), ('S2', HIT, (0, 60)), ('S1', HIT, (0, 60))],
      **ld('A', 8, 14, 160000, SLOTS['LD_A_SL'])),
  '214B': dict(slot=SLOTS['LD_B'], name='Lightning Dash', input=('214', ['B', 'C']), move_file='67_CEC_214B', hbp='52_Hitbox_214B',
      priority=7, cancels=[('214R2', HIT | BLOCK, (2, 17)), ('S2', HIT, (0, 60)), ('S1', HIT, (0, 60))],
      **ld('B', 10, 16, 170000, SLOTS['LD_B_SL'])),
  '214C': dict(slot=SLOTS['LD_C'], name='EX Lightning Dash', input=('214', ['C']), move_file='68_CEC_214C', hbp='53_Hitbox_214C',
      meter=EX, flash=15, priority=9, cancels=[('S1', HIT, (0, 60)), ('S2', HIT, (0, 60))],
      **ld('C', 5, 18, 180000, SLOTS['LD_C_SL'])),
  '214A_SL': dict(slot=SLOTS['LD_A_SL'], name='Lightning Dash (slash)', hbp='54_Hitbox_214A_Slash', **rekka('ld_s1', 2, R1, -2)),
  '214B_SL': dict(slot=SLOTS['LD_B_SL'], name='Lightning Dash (slash)', hbp='55_Hitbox_214B_Slash', **rekka('ld_s1', 2, R1, -2)),
  '214R2': dict(slot=SLOTS['R2'], name='Lightning Dash: Second Slash', input=('214', ['A', 'B']), move_file='69_CEC_214R2',
      hbp='59_Hitbox_214R2', priority=8, move_extra={'SkipCheck': True, 'IsSequenceFromStates': Packed('PackedInt32Array', [SLOTS['LD_A_SL'], SLOTS['LD_B_SL']])},
      cancels=[('214R3', HIT | BLOCK, (7, 26)), ('S2', HIT, (7, 28)), ('S1', HIT, (7, 28))], **rekka('ld_s2', 7, R2, -7, step=90000)),
  '214R3': dict(slot=SLOTS['R3'], name='Lightning Dash: Final Slash', input=('214', ['A', 'B']), move_file='70_CEC_214R3',
      hbp='60_Hitbox_214R3', priority=9, move_extra={'SkipCheck': True, 'IsSequenceFromStates': Packed('PackedInt32Array', [SLOTS['R2']])},
      cancels=[('S1', HIT, (8, 34)), ('S2', HIT, (8, 34))], **rekka('ld_s3', 8, R3, -10, step=90000)),
  '214C_SL': dict(slot=SLOTS['LD_C_SL'], name='EX Lightning Dash (slashes)', hbp='56_Hitbox_214C_Slash', **ld_slash(LD['C'], 12, True)),
  # --- 623 Teleport Slash -----------------------------------------------------------------------------
  '623A': dict(slot=82, name='Teleport Slash', input=('623', ['A']), move_file='60_CEC_623A', hbp='43_Hitbox_623A',
      **tp(4, 13, [(2, TS['A'][0])], 15000, 7000, box=DP_BOX['A'])),
  '623B': dict(slot=83, name='Teleport Slash', input=('623', ['B', 'C']), move_file='61_CEC_623B', hbp='44_Hitbox_623B',
      **tp(6, 15, [(2, TS['B'][0])], 19000, 8000, box=DP_BOX['B'])),
  '623C': dict(slot=84, name='EX Teleport Slash', input=('623', ['C']), move_file='62_CEC_623C', hbp='45_Hitbox_623C',
      meter=EX, flash=15, **tp(3, 20, [(2, TS['C'][0]), (6, TS['C'][1])], 17000, 8500, ex=True, box=DP_BOX['C'])),
  'TP_LAND': dict(slot=SLOTS['TP_LAND'], name='Teleport Slash (landing)', hbp='58_Hitbox_TP_Land', duration=12,
      keys=[['dp_6', 0]], boxes=[[0, 2, 'pose']], enter=[movex(0), movey(0)], ai=0x10 | 2),
  # --- j.236 Skyfall Slash (Oct 25) ---------------------------------------------------------------------
  'J236A': dict(slot=SLOTS['J236A'], name='Skyfall Slash', input=('236', ['A']), move_file='71_CEC_J236A', hbp='61_Hitbox_J236A',
      air=True, ground=False, priority=7, cancels=[('S2_air', HIT, (0, 60))], **dive('A', 3, 120000, -280000)),
  'J236B': dict(slot=SLOTS['J236B'], name='Skyfall Slash', input=('236', ['B', 'C']), move_file='72_CEC_J236B', hbp='62_Hitbox_J236B',
      air=True, ground=False, priority=7, cancels=[('S2_air', HIT, (0, 60))], **dive('B', 4, 170000, -260000)),
  'J236C': dict(slot=SLOTS['J236C'], name='EX Skyfall Slash', input=('236', ['C']), move_file='73_CEC_J236C', hbp='63_Hitbox_J236C',
      air=True, ground=False, meter=EX, flash=15, priority=9, **dive('C', 3, 140000, -300000)),
  'J236_LAND': dict(slot=SLOTS['J236_LAND'], name='Skyfall Slash (landing)', hbp='64_Hitbox_J236_Land', duration=15,
      keys=[['d236_4', 0, fx('j236_streak')], ['d236_4', 5]], boxes=[[0, 2, 'pose']], enter=[movex(0), movey(0)], ai=0x10 | 2),
  'J236C_LAND': dict(slot=SLOTS['J236C_LAND'], name='EX Skyfall Slash (lightning)', hbp='65_Hitbox_J236C_Land', duration=16,
      keys=[['d236_4', 0, fx('j236c_x')], ['d236_4', 8]],
      boxes=[[0, 1, 'atk_inv', J236_X, None, XBURST], [4, 2, 'pose']], tick=[(0, camera_shake(0.04, 10)), (4, frame_props(0))],
      enter=[movex(0), movey(0), frame_props(INV_STRIKE | INV_THROW)], exit=[frame_props(0)], ai=0x10 | 2),
  # --- supers -------------------------------------------------------------------------------------------
  'S1': dict(slot=85, name='Counter · Thunderclap', input=('214214', ['A', 'B', 'C'], '214|BC'),
      move_file='63_CEC_SakuraMorningMoon', hbp='46_Hitbox_Sakura_Stance',
      duration=72, keys=[['cs_1', 0], ['ld_rec', 47]],
      boxes=[[0, 0, 'pose'], [1, 1, 'counter'], [47, 2, 'pose']],
      enter=[movex(0)], hit_confirm=[ev(None, [play_state(92)])], meter=SUPER, priority=10, ai=0x10 | 2 | 0x1000,
      move_extra={'NetsuFlashOnHit': True}),   # no flash / cut-in in the stance: S1_hit starts them
  'S1_hit': dict(slot=92, name='Counter · Thunderclap (counter hit)', hbp='47_Hitbox_Sakura_Attack', duration=150,
      keys=[['cs_2', 0], ['cs_3', 10], ['cs_4', 18], ['cs_5', 34], ['cs_6', 50], ['cs_7', 64], ['cs_8', 76], ['cs_9', 92],
            ['cs_10', 106], ['cs_10', 110, boom('cs_boom1')], ['cs_10', 116, boom('cs_boom2')], ['cs_10', 128, boom('cs_boom3')],
            ['cs_10', 140]],
      boxes=[[0, 0, 'none'], [13, 1, 'atk_inv', CT[0]], [16, 2, 'none'], [19, 1, 'atk_inv', CT[1]], [22, 2, 'none'],
             [36, 1, 'atk_inv', CT[2]], [39, 2, 'none'], [53, 1, 'atk_inv', CT[3]], [56, 2, 'none'],
             [66, 1, 'atk_inv', CT[4]], [69, 2, 'none'], [110, 1, 'atk_inv', CT_END, None, BOOM], [116, 2, 'none']],
      tick=[(10, teleport(13000, 0, OPPONENT, WORLD)), (13, reset_hit()), (18, teleport(9000, 0, OPPONENT, WORLD)),
            (18, movey(60000)), (19, reset_hit()), (34, teleport(8000, 6000, OPPONENT, WORLD)), (34, movey(0)), (36, reset_hit()),
            (50, teleport(9000, 0, OPPONENT, WORLD)), (53, reset_hit()), (64, teleport(11000, 0, OPPONENT, WORLD)),
            (66, reset_hit()), (76, teleport(-11000, 0, OPPONENT, WORLD)), (110, reset_hit()), (110, camera_shake(0.05, 16))],
      tick_ranges=[((19, 33), gravity(160000)), ((35, 49), gravity())],
      enter=[super_flash(20), frame_props(INV_STRIKE | INV_THROW | INV_PROJ), movex(0)], exit=[frame_props(0)], priority=10,
      afterimages=True, ai=0x10 | 2 | 0x1000),
  'S2': dict(slot=93, name='Thunder Plunge', input=('236236', ['A', 'B', 'C'], '236|BC'), move_file='64_CEC_Raijin',
      hbp='48_Hitbox_Raijin', duration=66,
      keys=[['aoe_1', 0], ['aoe_2', 10, fx('aoe_fx1')], ['aoe_2', 16, fx('aoe_fx2')], ['aoe_2', 34, fx('aoe_fx3')],
            ['aoe_2', 46], ['aoe_rec', 48]],
      boxes=[[0, 0, 'none'], [12, 1, 'aoe', TP[0]], [15, 2, 'none'], [17, 1, 'aoe', TP[1]], [20, 2, 'none'],
             [22, 1, 'aoe', TP[2]], [25, 2, 'none'], [26, 2, 'pose'], [27, 1, 'atk', TP[3], None, AOE], [30, 2, 'pose'],
             [32, 1, 'atk', TP_END, None, AOE], [35, 2, 'pose']],
      tick=[(17, reset_hit()), (22, reset_hit()), (27, reset_hit()), (32, reset_hit()), (10, camera_shake(0.05, 22)),
            (26, frame_props(0))],
      enter=[change_side(), frame_props(INV_STRIKE | INV_THROW | INV_PROJ), movex(0)], exit=[frame_props(0)],
      meter=SUPER, flash=20, priority=10, ai=0x10 | 2 | 0x1000),
  'S2_air': dict(slot=94, name='Thunder Plunge', input=('236236', ['A', 'B', 'C'], '236|BC'), move_file='65_CEC_Raijin_Air',
      hbp='49_Hitbox_Raijin_Air', duration=60, keys=[['aoe_air', 0]],
      boxes=[[0, 0, 'none'], [1, 1, 'atk_inv', TP_DRAG, None, DRAG_BOX]],   # Oct 26: the plunge catches them on the way down
      enter=[frame_props(INV_STRIKE | INV_THROW | INV_PROJ), movex(0), movey(-160000)], exit=[frame_props(0)],
      hit_confirm=[ev(None, [play_state(114)])],
      transitions=[ev([on_ground()], [play_state(95)])], loop=True, meter=SUPER, flash=20, priority=10, air=True, ground=False,
      ai=0x10 | 4 | 0x1000),
  'S2_drag': dict(slot=114, name='Thunder Plunge (drag)', hbp='66_Hitbox_Raijin_Drag', duration=60, keys=[['aoe_air', 0]],
      boxes=[[0, 0, 'none']],
      enter=[frame_props(INV_STRIKE | INV_THROW | INV_PROJ), movex(0), movey(-160000)], exit=[frame_props(0)],
      tick_ranges=[((0, 999), hold_opp(*DRAG_HOLD))],
      transitions=[ev([on_ground()], [play_state(95)])], loop=True, priority=10, ai=0x10 | 4 | 0x1000),
  'S2_land': dict(slot=95, name='Thunder Plunge (landing)', hbp='50_Hitbox_Raijin_Land', duration=58,
      keys=[['aoe_1', 0], ['aoe_2', 2, fx('aoe_fx1')], ['aoe_2', 8, fx('aoe_fx2')], ['aoe_2', 26, fx('aoe_fx3')],
            ['aoe_2', 38], ['aoe_rec', 40]],
      boxes=[[0, 0, 'none'], [4, 1, 'aoe', TP[0]], [7, 2, 'none'], [9, 1, 'aoe', TP[1]], [12, 2, 'none'], [14, 1, 'aoe', TP[2]],
             [17, 2, 'none'], [19, 1, 'aoe', TP[3]], [22, 2, 'none'], [24, 1, 'aoe', TP_END], [27, 2, 'none'], [40, 2, 'pose']],
      tick=[(9, reset_hit()), (14, reset_hit()), (19, reset_hit()), (24, reset_hit()), (2, camera_shake(0.05, 22)),
            (40, frame_props(0))],
      enter=[frame_props(INV_STRIKE | INV_THROW | INV_PROJ), movex(0), movey(0)], exit=[frame_props(0)], priority=10, ai=0x10 | 2),
}
# which normals cancel into what (first match wins, so supers -> EX -> B -> A; 214 before 623 before 236)
GROUND_CANCEL_ORDER = ['S1', 'S2', '214C', '214B', '214A', '623C', '623B', '623A', '236C', '236B', '236A']
AIR_CANCEL_ORDER = ['S2_air', 'J236C', 'J236B', 'J236A']   # Oct 25: air normals cancel into the Skyfall Slash too
GROUND_NORMALS = ['23_CEC_5A', '24_CEC_5B', '25_CEC_5C', '26_CEC_2A', '27_CEC_2B', '28_CEC_2C', '32_CEC_4A', '33_CEC_6C']
AIR_NORMALS = ['29_CEC_j_5A', '30_CEC_j_5B', '31_CEC_j_5C']
# stance order (the neutral lookup runs from the END of the list, so later = checked first)
STANCE_ORDER = ['236A', '236B', '236C', 'J236A', 'J236B', 'J236C', '623A', '623B', '623C', '214A', '214B', '214C', '214R2', '214R3',
                'S2_air', 'S2', 'S1']
INPUTS = {('236', 'A'): '44_Input_236A', ('236', 'B|C'): '45_Input_236B_or_C', ('236', 'C'): '20_Input_236C',
          ('623', 'A'): '46_Input_623A', ('623', 'B|C'): '47_Input_623B_or_C', ('623', 'C'): '24_Input_623C',
          ('214', 'A'): '40_Input_214A', ('214', 'B|C'): '41_Input_214B_or_C', ('214', 'C'): '21_Input_214C',
          ('214', 'A|B'): '54_Input_214A_or_B',
          ('236236', 'A|B|C'): '49_Input_236236', ('214214', 'A|B|C'): '50_Input_214214'}
MANUAL_BOXES = {}

# --- her normals: 5B's blade finished, 5C shows the follow-through with the slash (derive_cecilia.py) --------------
FRAMES = {'5c_arc': {'src': 'derived/cecilia/5c_arc.png', 'anchor': 'like', 'like': '5c_2'}}
# Oct 25: the Teleport Slash's slash turned flatter and set further forward (the move goes more forward than up);
# the Skyfall Slash's streak (the same slash, mirrored: down-forward) and its EX's lightning X around her
_DP = 'Cecilia_Original_Idle_Style/15_623_Teleport/'
FRAMES.update({
    'dp_fx_flat': {'src': _DP + '02_normal_slash_effect.png', 'anchor': 'center', 'scale': 1.0, 'rotate': -24, 'at': [210, 290]},
    'dp_fx_ex_flat': {'src': _DP + '03_EX_slash_effect.png', 'anchor': 'center', 'scale': 1.0, 'rotate': -14, 'at': [200, 300]},
    'j236_trail': {'src': _DP + '02_normal_slash_effect.png', 'anchor': 'center', 'scale': 1.15, 'flip': True, 'at': [-150, 430]},
    'j236_streak': {'src': _DP + '02_normal_slash_effect.png', 'anchor': 'center', 'scale': 1.0, 'flip': True, 'at': [-170, 330]},
    'j236c_x': {'src': _DP + '03_EX_slash_effect.png', 'anchor': 'center', 'scale': 0.95, 'at': [0, 290]},
})
FRAME_PATCH = {'5b_2': {'src': 'derived/cecilia/5b_attack.png', 'scale': 0.882044300549845}}
ANIM_FX = {
  '49_CEC_5B': [['5b_1', 0], ['5b_2', 8], ['5b_3', 18]],
  '50_CEC_5C': [['5c_1', 0], ['5c_3', 13, fx('5c_arc')], ['5c_3', 19]],
}
TWO_B_CHAINS = [24, 25, 28, 4, 5, 6]   # 2B -> 5B, 5C, 2C and the jump cancels, like 5B (it had only specials left)

# ---------------------------------------------------------------------------------------------
def input_res(motion, buttons, alt=None):
    key = (motion, '|'.join(buttons)); name = INPUTS[key]
    res = INP + name + '.tres'
    if motion in ('236236', '214214'):        # supers: double motion + any button, or the old motion + B+C
        mi = MotionInputs(motion, buttons)
        if alt:
            m2, b2 = alt.split('|'); mi.fields['ValidInputs'] = mi.fields['ValidInputs'] + MotionInputs(m2, [b2]).fields['ValidInputs']
        if not DRY: write(res, mi, force=FORCE)
    elif not os.path.exists(res_file(res)):
        if DRY: raise SystemExit('missing input ' + res)
        write(res, MotionInputs(motion, buttons))   # Oct 25: a new one (the rekka's 214 + A or B)
    return res

def hitbox_files(mk, m):
    """skeleton hitbox files (boxes get fitted by hitfit.py afterwards)"""
    names = []
    for i, b in enumerate(m['boxes']):
        at, stage, kind = b[0], b[1], b[2]; props = b[3] if len(b) > 3 else None
        manual = b[5] if len(b) > 5 else None
        name = '%s_%d' % (m['hbp'], i); res = hb(name); names.append((at, stage, name, kind))
        if manual: MANUAL_BOXES[name] = manual
        if kind.split('-')[0] == 'aoe': MANUAL_BOXES.setdefault(name, AOE)
        if not SKEL: continue
        if os.path.exists(res_file(res)) and not FORCE:     # made before: only the table's attack values go in
            if props and kind.split('-')[0] in ('atk', 'atk_inv', 'aoe'): patch_attacks(res, props)
            continue
        els = []; base = kind.split('-')[0]; pushbox = None if kind.endswith('-pass') else PUSHBOX_STD
        if base in ('pose', 'pose+prox', 'atk'): els += standard_hurt(3)
        if base in ('pose+prox', 'atk'):
            els.append(box(PROX, 0, 0, 400, 450, HitType=MID))
        if base in ('atk', 'atk_inv', 'aoe'):
            els.append(box(HIT_T, 40, 100, 300, 360, **props))
        if base == 'counter':
            els.append(box(COUNTER, -40, 0, 170, 470, SelfSuperGaugeGain=0, OpponentSuperGaugeGain=0, SelfHitStopDuration=20,
                           OpponentHitStopDuration=24))
        write(res, Hitboxes(els, pushbox), force=FORCE)
    return names

def strip_old_cancels(move_res):
    """drop cancels into the stance's special-move slots (they are added again below, with the new indices)"""
    def fn(t):
        refs = list_refs(t, 'CanCancelTo'); keep = []
        for r in refs:
            sid = re.search(r'"([^"]+)"', r).group(1); s = t.sub_get(sid)
            mm = re.search(r'MoveIndex = (\d+)', '\n'.join(s[2])) if s else None
            if mm and int(mm.group(1)) >= FIRST_SPECIAL: continue
            keep.append(r)
        t.res_set('CanCancelTo', '[' + ', '.join(keep) + ']'); t.prune()
    return edit_tres(move_res, fn, BK, 'old cancels removed')

def set_stance_specials(stance_res, move_res_list):
    """the stance's moves: 0..FIRST_SPECIAL-1 stay, then exactly these (in this order)"""
    def fn(t):
        old = list_refs(t, 'Moves')
        refs = old[:FIRST_SPECIAL]
        for mr in move_res_list:
            i = t.ext_id_for_path(mr) or t.add_ext('Resource', mr, res_uid(mr), prefer_id='mv_' + re.sub(r'\W', '_', os.path.basename(mr)[:-5]))
            refs.append('ExtResource("%s")' % i)
        # Oct 24 night: moves other tools add after the specials stay at the end (the B+C throw, throws.py)
        for r in old[FIRST_SPECIAL:]:
            e = t.ext_by_id(re.search(r'"([^"]+)"', r).group(1))
            if e and re.search(r'(_Throw|_6C)\.tres$', e.get('path', '')) and r not in refs:
                refs.append(r)
        t.res_set('Moves', '[' + ', '.join(refs) + ']'); t.prune()
    edit_tres(stance_res, fn, BK, 'stance specials')

def set_state_slots(data_res, slots):
    """slots: {index: state_res}; extends the list with idle if needed; references nothing uses any more are dropped"""
    def fn(t):
        refs = list_refs(t, 'States'); idle = refs[0]
        for slot in sorted(slots):
            sr = slots[slot]
            i = t.add_ext('Resource', sr, res_uid(sr), prefer_id='st_' + re.sub(r'\W', '_', os.path.basename(sr)[:-5]))
            while len(refs) <= slot: refs.append(idle)
            refs[slot] = 'ExtResource("%s")' % i
        t.res_set('States', '[' + ', '.join(refs) + ']'); t.prune()
    return edit_tres(data_res, fn, BK, 'state slots')

def patch_normals():
    """2B chains into her other normals again; j.C falls like j.A / j.B (it stopped in the air and floated)"""
    add_cancels(A + 'Moves/27_CEC_2B.tres', [(i, HIT | BLOCK, (0, 999)) for i in TWO_B_CHAINS], BK, before_all=False)
    def jc(t):
        grav = t.ext_id_for_path(ACT + 'AddGravityAction.cs') or t.add_ext('Script', ACT + 'AddGravityAction.cs',
                                                                          script_uid(ACT + 'AddGravityAction.cs'), prefer_id='grav')
        fde = t.ext_id_for_path(FDE + 'FrameDataEvent.cs')
        if t.sub_get('fdk_jc_fall'): return
        t.sub.append(['fdk_jc_gravity', 'Resource', ['script = ExtResource("%s")' % grav, 'SetValue = true', 'UseDefault = true']])
        t.sub.append(['fdk_jc_fall', 'Resource', ['script = ExtResource("%s")' % fde, 'Conditions = null',
                                                 'Actions = [SubResource("fdk_jc_gravity")]']])
        t.res_set('OnTickEvents', '[SubResource("fdk_jc_fall")]'); t.prune()
    edit_tres(A + 'States/71_CEC_J5C.tres', jc, BK, 'j.C gravity')

def write_states():
    for mk, m in MOVES.items():
        m['anim'] = '%d_%s_%s' % (m['slot'], TAG, mk)
        sres = A + 'States/%d_%s_%s.tres' % (m['slot'], TAG, mk); m['state_res'] = sres
        tick = [ev([at(fr)], [act]) for fr, act in m.get('tick', [])]
        tick += [ev([at_range(a, b)], [act]) for (a, b), act in m.get('tick_ranges', [])]
        trans = list(m.get('transitions', []))
        if m.get('loop'):
            trans += [ev([state_ended()], [goto_frame(m['duration'] - 1)])]
        elif not trans:
            trans += [ev([state_ended()], [play_state(IDLE)])]
        st = State(m['name'], COMBAT, an(m['anim']), transitions=trans, enter=m.get('enter', ()), tick=tick, exit=m.get('exit', ()),
                   hit_confirm=m.get('hit_confirm', ()), ai=m.get('ai', 0x10 | (4 if m.get('air') else 2)))
        if not DRY: write(sres, st, force=FORCE)

COMMANDS = {
    "fighter": "Cecilia Richter",
    "note": "Numpad notation, facing right: 6 = forward, 4 = back, 2 = down, 8 = up, 236 = quarter circle forward. Craft Gauge: 6 bars, kept between rounds. EX = 2 bars, supers = 3 bars. Overdrive: more damage and Craft Gauge until the Burst gauge runs out.",
    "sections": [
        {"title": "Normals", "moves": [
            ["5A / 5B / 5C", "A / B / C", "chains A > B > C"], ["2A / 2B / 2C", "2 + A / B / C", ""], ["4A", "4 + A", ""],
            ["Air A / B / C", "in air: A / B / C", ""]]},
        {"title": "Specials", "moves": [
            ["Dash Slash", "236 + A / B", "B knocks back; into a wall it bounces them (follow up with 5B)"],
            ["EX Dash Slash", "236 + C (2 bars)", "Hit-grab rush ending in a hard knockdown; without 2 bars = B"],
            ["Lightning Dash", "214 + A / B", "Strike-invincible dash, then a slash"],
            ["  Second Slash", "214 + A / B again", "During the first slash (hit or block)"],
            ["  Final Slash", "214 + A / B again", "Hard knockdown on hit; unsafe on block"],
            ["EX Lightning Dash", "214 + C (2 bars)", "Three slashes, the last knocks down hard; without 2 bars = B"],
            ["Teleport Slash", "623 + A / B", "Invincible start, sweeps forward and launches"],
            ["EX Teleport Slash", "623 + C (2 bars)", "Two-hit X cut; without 2 bars = B"],
            ["Skyfall Slash", "in air: 236 + A / B", "Diving slash; slams airborne opponents down"],
            ["EX Skyfall Slash", "in air: 236 + C (2 bars)", "Invincible dive, lightning X on landing (+3 on block)"]]},
        {"title": "Supers (3 bars)", "moves": [
            ["Thunder Plunge", "236236 + any", "Ground or air (236 + B+C works too)"],
            ["Counter · Thunderclap", "214214 + any", "Counter stance: the flash only comes when it catches a hit (214 + B+C works too)"]]},
        {"title": "System", "moves": [
            ["Dash / Back dash", "66 / 44", ""], ["Super jump", "2 then 8", ""], ["Air dash", "in air: 66 / 44", ""],
            ["Throw", "B + C (close)", "4 + B+C throws behind you"], ["Throw break", "B + C as you're grabbed", "12-frame window"],
            ["Burst", "A + C", "full Burst gauge, works in hitstun"], ["Overdrive", "A + B + C", "full Burst gauge"],
            ["Pushblock", "A + B", "while blocking, 1 bar"], ["Recover", "any button", "when knocked down"]]},
    ],
}

def main():
    if STATES_ONLY:
        write_states(); print('\n'.join(fdk.LOG)); return
    man_path = os.path.join(HERE, 'manifests', CH + '.json')
    man = json.load(open(man_path, encoding='utf-8'))
    bk = os.path.join(fdk.PROJ, BK, 'cecilia.json.bak')
    if SKEL and not os.path.exists(bk):
        os.makedirs(os.path.dirname(bk), exist_ok=True); open(bk, 'w', encoding='utf-8').write(open(man_path, encoding='utf-8').read())
    man['frames'].update(FRAMES)
    for fid, patch in FRAME_PATCH.items(): man['frames'][fid].update(patch)
    for name, keys in ANIM_FX.items(): man['animations'][name]['keys'] = keys
    hf = man.setdefault('hitfit', {}); hf.setdefault('boxes', {}); hf.setdefault('attack_part', {})
    # the old Luminous Divider (214 + hold versions) is replaced by Lightning Dash; its animations leave the manifest
    for k in [k for k in man['animations'] if re.match(r'\d+_CEC_LD_', k)]: del man['animations'][k]
    for k in [k for k in hf['attack_part'] if k.startswith('30_Hitbox_LD_')]: del hf['attack_part'][k]
    for k in list(hf['boxes']):      # manual boxes are set again below (box numbers moved)
        if any(k.startswith(m['hbp'] + '_') for m in MOVES.values()): del hf['boxes'][k]
    hf['attack_part'].update({'50_CEC_5C': 'trail'})
    anims = []
    for mk, m in MOVES.items():
        aname = '%d_%s_%s' % (m['slot'], TAG, mk)
        m['anim'] = aname; anims.append(aname)
        entry = {'keys': m['keys'], 'duration': m['duration']}
        if m.get('afterimages'): entry['afterimages'] = True
        man['animations'][aname] = entry
        names = hitbox_files(mk, m); m['hb_names'] = names
        entry['hitboxes'] = [[a0, stage, name] for a0, stage, name, kind in names]   # box timeline (build.py)
        ares = an(aname)
        if SKEL and (not os.path.exists(res_file(ares)) or FORCE):
            write(ares, AnimData(m['duration'], [(a0, stage, hb(name)) for a0, stage, name, kind in names],
                                 afterimages=True if m.get('afterimages') else None), force=FORCE)
    for name, bx in MANUAL_BOXES.items(): hf['boxes'][name] = {'attack': bx}
    if DRY:
        for mk, m in MOVES.items(): print(mk, m['anim'], [n[2] for n in m['hb_names']])
        return
    if SKEL:
        json.dump(man, open(man_path, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
        print('\n'.join(fdk.LOG)); del fdk.LOG[:]
    todo = anims + list(ANIM_FX)
    if ONLY: todo = [a for a in todo if a in ONLY.split(',')]
    # sprites + timelines
    if 2 in PHASES:
        import build
        p = build.Port(CH)
        for a in todo:
            p.build_anim(a); print('built', a, flush=True)
    # boxes fitted to the drawings
    if 3 in PHASES:
        import hitfit
        f = hitfit.Fitter(CH)
        for line in f.run(todo, write=True, force=FORCE): print('  ', line, flush=True)
    if 4 not in PHASES: return
    write_states()
    # moves (the supers' inputs are written here: double motion + any button, or motion + B+C)
    for mk, m in MOVES.items():
        if 'input' not in m: continue
        m['move_res'] = A + 'Moves/%s.tres' % m['move_file']
    idx = {k: FIRST_SPECIAL + n for n, k in enumerate(STANCE_ORDER)}
    for mk, m in MOVES.items():
        if 'input' not in m: continue
        motion, buttons = m['input'][0], m['input'][1]
        cancels = [cancel(idx[k], c, fr) for k, c, fr in m.get('cancels', [])]
        mv = Move(m['name'], m['slot'], input_res(motion, buttons, m['input'][2] if len(m['input']) > 2 else None),
                  priority=m.get('priority', 7), meter=m.get('meter'), flash=m.get('flash'),
                  ground=m.get('ground', True), air=m.get('air', False), cancels=cancels, extra=m.get('move_extra'))
        write(m['move_res'], mv, force=FORCE)
    # register: state slots, stance moves, cancels from the normals
    set_state_slots(A + '0_%s_Data.tres' % TAG, {m['slot']: m['state_res'] for m in MOVES.values()})
    set_stance_specials(A + 'Stances/%s_Stance_Main.tres' % TAG, [MOVES[k]['move_res'] for k in STANCE_ORDER])
    for n in GROUND_NORMALS + AIR_NORMALS: strip_old_cancels(A + 'Moves/%s.tres' % n)
    for n in GROUND_NORMALS:
        add_cancels(A + 'Moves/%s.tres' % n, [(idx[k], HIT | BLOCK, (0, 999)) for k in GROUND_CANCEL_ORDER], BK)
    for n in AIR_NORMALS:
        add_cancels(A + 'Moves/%s.tres' % n, [(idx[k], HIT | BLOCK, (0, 999)) for k in AIR_CANCEL_ORDER], BK)
    import launchers; launchers.normals_to_6c(CH, BK)   # Oct 26: every ground normal can cancel into 6C
    patch_normals()
    cl = os.path.join(fdk.PROJ, 'actors', CH, 'command_list.json')
    txt = json.dumps(COMMANDS, indent='\t', ensure_ascii=False)
    # Oct 25 night: the json is edited directly now (6C, the EX moves' texts): only written when it doesn't exist
    if not os.path.exists(cl):
        bk = os.path.join(fdk.PROJ, BK, 'command_list.json.bak')
        if not os.path.exists(bk): os.makedirs(os.path.dirname(bk), exist_ok=True); open(bk, 'w', encoding='utf-8').write(open(cl, encoding='utf-8').read())
        open(cl, 'w', encoding='utf-8', newline='\n').write(txt); print('wrote command_list.json')
    print('\n'.join(fdk.LOG))
    print('move indices:', idx)

if __name__ == '__main__':
    main()
