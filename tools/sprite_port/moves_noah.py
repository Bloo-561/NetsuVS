"""NOAH'S MOVES (Oct 25 2026 evening): his specials and supers, built from the drawings in
Fighting_Game_All_Sprites/Noah_Complete (see its COMMAND_LIST.md: the pack's own move list).

  236A        Shade Wave          gathers energy in the devil arm, swipes low then up: one wave rolls along the floor
  236B        Twin Shade          the same, then a gesture with his human hand sends a second wave
  236C        Umbral Wall         (2 bars) two gestures raise a wall of energy that pushes slowly forward: three hits, launches
  623A        Event Horizon       a black hole opens close in front of him (it waits ~5 s)
  623B        Event Horizon       the black hole opens far away, around mid-screen
  623C        Twin Horizon        (2 bars) both holes at once, invincible start
  623 again   Collapse            (while a hole is open) finger snap: every hole sucks the opponent in and bursts; the near
                                  hole throws them away from Noah, the far one throws them toward him
  214A        Void Grasp          low straight-arm grab lunge; on hit he drains them (two hits) and STOCKS the energy
  214B        Abyss Hammer        jumps forward, turns and smashes the devil arm down (overhead)
  214C        Void Devour         (2 bars) invincible lunge; grabs the face, lifts, drains, purple explosion; stocks energy
  214 + A / B Overflow Ray        (with stocked energy) a horizontal purple beam about four of him long; uses the stock
  j.214A      Fallen Grasp        air grab: drags them diagonally down to the floor into a ground explosion (air combo ender)
  j.214B      Abyss Hammer (air)  the overhead smash from a jump
  236236 / 236 + B+C   Raging Storm  (3 bars) crossed-arm charge through the super pause, overhead windup, ground slam,
                                  a storm of purple fire around him holds them up, then the last burst throws them away
  214214 / 214 + B+C   God Press    (3 bars) sliding grab; carries them to the wall, slams them into it three times, lifts
                                  them and blasts them; the blast throws Noah back onto one knee
Names are placeholders: rename them in the Move files (MoveName, shown in the cut-in) and command_list.json.

    python moves_noah.py          writes everything
    python moves_noah.py --states only rewrites the state files
    python moves_noah.py --anims=a,b   only rebuilds those animations' sprites / boxes
    python moves_noah.py --force  overwrites files changed in Godot too

His waves, the energy wall and the black holes are actors of their own (actors/noah/projectiles/, spawned from his
SpawnablesList NOA_SpawnablesList.tres): they keep going after he recovers. Engine pieces made for him:
NetsuSpawnTriggerAction (the snap sets the waiting holes off), NetsuPullOpponentAction (the holes' suction).
Two custom variables on his skins: 3 "Stock" (1 = energy stocked: 214 + A / B is the beam) and 4 "HoleTimer"
(counts down from 300 while a hole is open: 623 is the snap).
Speeds are real engine speeds (units per second, 10000 = 1 m; position += speed / 60 every frame).
"""
import sys, os, json, re, copy
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import fdk
from fdk import *
from tres import Tres

CH, TAG = 'noah', 'NOA'
A = 'res://actors/noah/'
PJ = 'noah/projectiles'
PA = 'res://actors/noah/projectiles/'
BK = '_backup_stage_select/pre_noah_moves'
FORCE = '--force' in sys.argv
DRY = '--dry' in sys.argv
STATES_ONLY = '--states' in sys.argv
def _arg(name, default=None):
    for a in sys.argv:
        if a.startswith('--%s=' % name): return a.split('=', 1)[1]
    return default
ONLY = _arg('anims')
UPX = 27.5
def u(px): return int(round(px * UPX))
INP = 'res://actors/_shared/sakuga/Inputs/'
IDLE, FALLING, LANDING = 0, 10, 11
FIRST_SPECIAL = 41
STOCK, HOLE = 3, 4             # his custom variables (Parameters/Variables: 0-2 are the jump / air dash ones)
HOLE_FRAMES = 300

def hb(name): return A + 'Hitboxes/%s.tres' % name
def an(name): return A + 'AnimationData/%s_AnimData.tres' % name
def hold_opp(x, y, lift=None):
    return Obj(ACT + 'NetsuHoldOpponentAction.cs', Offset=V2i(x, y), LiftRate=lift)
def pull(radius, speed, lift_rate=None, lift=None):
    return Obj(ACT + 'NetsuPullOpponentAction.cs', Radius=radius, Speed=speed, LiftRate=lift_rate, Lift=lift)
def trigger_holes():
    return Obj(ACT + 'NetsuSpawnTriggerAction.cs', Index=2, FromStates=Packed('PackedInt32Array', [1, 3]),
               ToStates=Packed('PackedInt32Array', [2, 4]))
def var_cond(index, value, compare, mode=0):
    return Obj(SR + 'CustomVariableCondition.cs', ByIndex=index, Value=value, CompareMode=compare, Mode=mode or None)
def var_change(index, value, mode=0):
    return Obj(SR + 'CustomVariableChange.cs', ByIndex=index, Value=value, Mode=mode or None)
EQUAL, GREATER_EQUAL = 0, 3
DECREASE = 2

# ---------------------------------------------------------------------------------------------
# attacks (first pass; tune in the frame data sheet). reaction: 0 weak, 1 strong, 5 air, 6 crumple, 7 launch away,
# 8 launch up, 9 launch down
WAVE = attack(700, 22, 14, kb=(-30000, 0), air_kb=(-20000, 35000), reaction=1, air_reaction=5, stop=10, gain=300)
WALL1 = attack(450, 30, 16, kb=(-6000, 0), air_kb=(-6000, 20000), reaction=1, air_reaction=5, stop=8, gain=0, scaling=4)
WALL3 = attack(800, 50, 18, kb=(-15000, 115000), air_kb=(-15000, 115000), reaction=8, air_reaction=8, hitstun_type=KNOCKDOWN,
               kb_gravity=200000, air_gravity=200000, stop=16, gain=0, scaling=5)   # Oct 25 night: the wall throws them sky-high
SUCK = attack(150, 30, 12, kb=(0, 0), air_kb=(0, 6000), reaction=1, air_reaction=5, stop=4, gain=100, scaling=2, air_gravity=1)
BURST_NEAR = attack(800, 40, 18, kb=(-70000, 55000), air_kb=(-70000, 55000), reaction=7, air_reaction=7, hitstun_type=KNOCKDOWN,
                    kb_gravity=200000, stop=14, gain=300)
BURST_FAR = attack(800, 40, 18, kb=(55000, 50000), air_kb=(55000, 50000), reaction=8, air_reaction=8, hitstun_type=KNOCKDOWN,
                   kb_gravity=200000, stop=14, gain=300)
GRASP = attack(300, 70, 18, kb=(0, 0), air_kb=(0, 0), reaction=1, air_reaction=5, stop=12, gain=200, air_gravity=1)
DRAIN = attack(400, 60, 20, kb=(0, 0), air_kb=(0, 0), reaction=1, air_reaction=5, stop=8, gain=200, scaling=3, air_gravity=1)
DRAIN_END = attack(500, 40, 20, kb=(-45000, 35000), air_kb=(-45000, 35000), reaction=7, air_reaction=7, hitstun_type=KNOCKDOWN,
                   kb_gravity=220000, stop=14, gain=300)
HAMMER = attack(900, 24, 16, kb=(-25000, 0), air_kb=(-15000, -50000), reaction=1, air_reaction=9, stop=13, gain=400, hit_type=HIGH)
GRASP_C = attack(300, 90, 20, kb=(0, 0), air_kb=(0, 0), reaction=1, air_reaction=5, stop=14, gain=0, air_gravity=1, scaling=2)
DEVOUR = attack(300, 90, 20, kb=(0, 0), air_kb=(0, 0), reaction=5, air_reaction=5, stop=6, gain=0, scaling=2, air_gravity=1)
DEVOUR_END = attack(1300, 45, 20, kb=(-70000, 100000), air_kb=(-70000, 100000), reaction=7, air_reaction=7, hitstun_type=HARD_KNOCKDOWN,
                    kb_gravity=200000, air_gravity=200000, stop=22, gain=0, scaling=5)   # Oct 25 night: the explosion blows them away
RAY = attack(380, 30, 16, kb=(-12000, 0), air_kb=(-12000, 15000), reaction=1, air_reaction=5, stop=6, gain=150, scaling=3)
RAY_END = attack(500, 36, 18, kb=(-60000, 35000), air_kb=(-60000, 35000), reaction=7, air_reaction=7, hitstun_type=KNOCKDOWN,
                 kb_gravity=200000, stop=12, gain=200)
AIR_GRAB = attack(300, 80, 16, kb=(0, 0), air_kb=(0, 0), reaction=5, air_reaction=5, stop=10, gain=200, air_gravity=1,
                  hitstun_type=HARD_KNOCKDOWN)
GROUND_BLAST = attack(900, 40, 20, kb=(-30000, 60000), air_kb=(-30000, 60000), reaction=8, air_reaction=8,
                      hitstun_type=HARD_KNOCKDOWN, kb_gravity=220000, stop=16, gain=300)
AIR_HAMMER = attack(800, 24, 16, kb=(-20000, 0), air_kb=(-15000, -60000), reaction=1, air_reaction=9, stop=12, gain=400, hit_type=HIGH)
# Raging Storm: the slam pops them up, the storm keeps them up (lifted in place), the last burst throws them away
RS_SLAM = attack(400, 60, 20, kb=(0, 50000), air_kb=(0, 30000), reaction=8, air_reaction=5, stop=14, gain=0, scaling=0,
                 hitstun_type=HARD_KNOCKDOWN, air_gravity=1)
RS_STORM = attack(200, 45, 20, kb=(0, 0), air_kb=(0, 4000), reaction=5, air_reaction=5, stop=3, gain=0, scaling=1, air_gravity=1,
                  hitstun_type=HARD_KNOCKDOWN, pushback=0)
RS_END = attack(1000, 60, 24, kb=(-45000, 60000), air_kb=(-45000, 60000), reaction=7, air_reaction=7, hitstun_type=HARD_KNOCKDOWN,
                kb_gravity=200000, stop=20, gain=0, scaling=0)
# God Press: the grab holds them on his palm, three wall slams, the lift, the discharge
GP_GRAB = attack(300, 90, 20, kb=(0, 0), air_kb=(0, 0), reaction=1, air_reaction=5, stop=12, gain=0, scaling=0, air_gravity=1,
                 hitstun_type=HARD_KNOCKDOWN)
GP_SLAM = attack(300, 60, 20, kb=(0, 0), air_kb=(0, 0), reaction=5, air_reaction=5, stop=8, gain=0, scaling=1, air_gravity=1,
                 hitstun_type=HARD_KNOCKDOWN)
GP_SPARK = attack(200, 60, 20, kb=(0, 0), air_kb=(0, 0), reaction=5, air_reaction=5, stop=3, gain=0, scaling=1, air_gravity=1,
                  hitstun_type=HARD_KNOCKDOWN)
GP_END = attack(1600, 60, 30, kb=(-45000, 80000), air_kb=(-45000, 80000), reaction=8, air_reaction=8, hitstun_type=HARD_KNOCKDOWN,
                kb_gravity=200000, stop=22, gain=0, scaling=0)

# ---------------------------------------------------------------------------------------------
# his special / super drawings and effect layers (added to manifests/noah.json "frames")
R = 'Noah_Complete/'
S = R + 'Specials/'
GP = R + 'Supers/214214_God_Press/'
RS = R + 'Supers/Raging_Storm/'
FRAMES = {}
def fr(fid, src, **kw): FRAMES[fid] = {'src': src, **kw}
# scales per drawing (see make_noah_manifest.py: head SIFT + belt card)
fr('k_start', S + '214A/01_Startup.png', scale=3.15)
fr('k_lunge', S + '214A/02_Straight_Grab_Lunge.png', scale=3.05)
fr('k_recoil', S + '214A/04_Compact_Recoil.png', scale=2.95)
fr('k_absorb', S + '214A/05_Absorb.png', scale=2.82)
fr('k_rec', S + '214A/06_Recovery.png', scale=2.6)
fr('h_prep', S + '214B/01_Prepare.png', scale=2.72)
fr('h_turn', S + '214B/02_Jump_Turn.png', scale=2.72, anchor='air')
fr('h_smash', S + '214B/03_Overhead_Active.png', scale=2.72, anchor='air')
fr('h_follow', S + '214B/04_Followthrough.png', scale=2.8, anchor='air')
fr('h_land', S + '214B/05_Land.png', scale=2.9)
fr('h_rec', S + '214B/06_Recover.png', scale=2.58)
fr('x_face', S + '214EX/03_Face_Grab.png', scale=3.0)
fr('x_lift', S + '214EX/04_Lift.png', scale=2.66)
fr('x_drain', S + '214EX/05_Drain.png', scale=2.58)
fr('x_recoil', S + '214EX/07_Recoil.png', scale=2.72)
fr('ray_pose', S + '214_Stocked_Beam/Pained_Horizontal_Release.png', scale=2.85)
fr('w_gather', S + '236/01_Gather.png', scale=2.93)
fr('w_windup', S + '236/02_Low_Windup.png', scale=3.27)
fr('w_devil', S + '236/03_Devil_Arm_Release.png', scale=2.95)
fr('w_human', S + '236/04_Human_Arm_Release.png', scale=2.67)
fr('bh_summon', S + '623/Summon_Hand_Out.png', scale=2.55)
fr('bh_snap', S + '623/Activate_Finger_Snap.png', scale=2.55)
fr('ag_reach', S + 'Air_214A/01_Reach.png', scale=3.5, anchor='air')
fr('ag_grab', S + 'Air_214A/02_Grab.png', scale=3.45, anchor='air')
fr('ag_down', S + 'Air_214A/03_Diagonal_Descent.png', scale=3.4, anchor='air')
fr('ag_land', S + 'Air_214A/04_Land.png', scale=3.4)
for i, f in [('01', 'Lean_Back'), ('02', 'Sliding_Grab_Carry'), ('05', 'Wall_Pullback'), ('06', 'Wall_Slam'), ('07', 'Lift'),
             ('08', 'Energy_Discharge'), ('09', 'Blast_Knockback'), ('10', 'One_Knee_Landing'), ('11', 'Push_Up'), ('12', 'Standing_Recovery')]:
    fr('gp_' + i, GP + 'Character/%s_%s.png' % (i, f), scale=1.24, anchor='pin', pin=[400, 550])
FRAMES['gp_09']['anchor'] = 'air'
FRAMES['gp_09'].pop('pin')
for p in ['00', '10', '11', '12', '13', '14', '15', '51', '52', '53', '54', '55', '60', '65']:
    fr('rs_' + p, RS + 'Character/Pose_%s.png' % p, scale=1.15, anchor='pin', pin=[520, 820])
# effects held at a point of a pose ("attach": [pose, point on the pose's drawing, point on the effect])
fr('fx_ray', S + '214_Stocked_Beam/Purple_Beam_Effect.png', anchor='attach', attach=['ray_pose', [1148, 278], [30, 406]], scale=None)
for i in range(1, 7):
    fr('fx_dex_%d' % i, S + '214EX/Explosion/Frame_%02d.png' % i, anchor='attach', attach=['x_drain', [1100, 70], [256, 256]], scale=None)
for i in range(1, 5):
    fr('fx_blast_%d' % i, S + 'Air_214A/Ground_Blast/Frame_%02d.png' % i, anchor='attach', attach=['ag_land', [1357, 732], [384, 490]], scale=None)
    fr('fx_wall_%d' % i, GP + 'Effects/wallfx_%02d.png' % i, anchor='attach', attach=['gp_06', [735, 190], [660, 230]], scale=None)
for i in range(1, 7):
    fr('fx_final_%d' % i, GP + 'Effects/finalfx_%02d.png' % i, anchor='attach', attach=['gp_08', [585, 120], [256, 256]], scale=None)
for st, n in [('charge', 5), ('slam', 4), ('loop', 6), ('fade', 4)]:
    for i in range(n):
        fr('fx_rs_%s_%d' % (st, i), RS + 'Effects/%s_%02d.png' % (st, i), anchor='like', like='rs_00')
# effect sizes in game px (his standing height is 540): scale = BASE / (game px per drawing px)
FX_WIDTH = {'fx_ray': 1300, 'fx_dex': 300, 'fx_blast': 520, 'fx_wall': 330, 'fx_final': 360}

def fill_fx_scales(port):
    """the effects' 'scale' from their wanted width (the drawing's full canvas width -> FX_WIDTH game px)"""
    from PIL import Image
    for fid, spec in FRAMES.items():
        if spec.get('scale', 1) is not None: continue
        key = next(k for k in FX_WIDTH if fid == k or fid.startswith(k + '_'))
        w = Image.open(os.path.join(port.root, spec['src'])).width
        spec['scale'] = round(port.BASE / (FX_WIDTH[key] / float(w)), 5)
def fx(f): return {'fx': f, 'fx_always': True}
def fxc(f): return {'fx': f}

# ---------------------------------------------------------------------------------------------
# the moves.  keys: [frame, at, {options}]; boxes: [at, stage, kind, props, None, manual box (world px)]
# Positions of the held opponent (hold_opp): engine units, x along his facing, y above his feet.
RAY_BOX = [[150, 250, 2200, 430]]        # the beam: from his hand to ~4 of him in front
RS_BOX = [[-430, 0, 430, 720]]           # the storm all around him
WALL_LIMIT, CARRY_STOP = 120000, 36000   # GlobalVariables.WallLimit; where the carry stops
GP_HOLD = (14000, 2000)                  # on his palm during the carry / slams (they're held up by the face)
SLAM_HOLD = (15500, 2500)
PULL_HOLD = (13000, 2500)
LIFT_HOLD = (12000, 9000)

def loop(keys_fn, start, n, step):
    return [[keys_fn(i), start + i * step] for i in range(n)]

MOVES = {
  # ---- 236: waves (actor 0 / the wall: actor 1)
  '236A': dict(slot=73, name='Shade Wave', input=('236', ['A']), move_file='53_NOA_ShadeWave_A', hbp='30_Hitbox_ShadeWave_A',
      duration=44, keys=[['w_gather', 0], ['w_windup', 6], ['w_devil', 13], ['w_devil', 24, {'dx': -4}], ['stand', 34]],
      boxes=[[0, 0, 'pose'], [13, 2, 'pose']],
      tick=[(14, spawn_actor(0, u(150), 0, initial_state=1))], enter=[change_side(), movex(0)], priority=7,
      cancels=[('S1', WHIFF | HIT | BLOCK, (16, 40)), ('S1bc', WHIFF | HIT | BLOCK, (16, 40))]),
  '236B': dict(slot=74, name='Twin Shade', input=('236', ['B', 'C']), move_file='54_NOA_ShadeWave_B', hbp='31_Hitbox_ShadeWave_B',
      duration=58, keys=[['w_gather', 0], ['w_windup', 6], ['w_devil', 13], ['w_human', 25], ['w_human', 36, {'dx': -4}], ['stand', 46]],
      boxes=[[0, 0, 'pose'], [13, 2, 'pose']],
      tick=[(14, spawn_actor(0, u(150), 0, initial_state=1)), (26, spawn_actor(0, u(150), 0, initial_state=1))],
      enter=[change_side(), movex(0)], priority=7,
      cancels=[('S1', WHIFF | HIT | BLOCK, (28, 54)), ('S1bc', WHIFF | HIT | BLOCK, (28, 54))]),
  '236C': dict(slot=75, name='Umbral Wall', input=('236', ['C']), move_file='55_NOA_UmbralWall', hbp='32_Hitbox_UmbralWall',
      duration=50, keys=[['w_gather', 0], ['w_devil', 8], ['w_human', 18], ['w_human', 30, {'dx': -4}], ['stand', 40]],
      boxes=[[0, 0, 'none'], [20, 2, 'pose']],
      tick=[(18, spawn_actor(1, u(180), 0, initial_state=1)), (20, frame_props(0))],
      enter=[change_side(), movex(0), frame_props(INV_STRIKE | INV_THROW | INV_PROJ)], exit=[frame_props(0)],
      meter=4000, flash=15, priority=9, afterimages=True, ai=0x10 | 2 | 0x1000),
  # ---- 623: black holes (actor 2: 1 near idle, 2 near suction, 3 far idle, 4 far suction)
  '623A': dict(slot=76, name='Event Horizon', input=('623', ['A']), move_file='56_NOA_EventHorizon_A', hbp='33_Hitbox_EventHorizon_A',
      duration=36, keys=[['stand', 0], ['bh_summon', 5], ['bh_summon', 22, {'dx': -3}], ['stand', 28]],
      boxes=[[0, 0, 'pose'], [5, 2, 'pose']],
      tick=[(10, spawn_actor(2, u(330), u(320), initial_state=1)), (10, set_var('', HOLE_FRAMES, 0, by_index=HOLE))],
      enter=[change_side(), movex(0)], priority=7),
  '623B': dict(slot=77, name='Event Horizon', input=('623', ['B', 'C']), move_file='57_NOA_EventHorizon_B', hbp='34_Hitbox_EventHorizon_B',
      duration=40, keys=[['stand', 0], ['bh_summon', 6], ['bh_summon', 25, {'dx': -3}], ['stand', 32]],
      boxes=[[0, 0, 'pose'], [6, 2, 'pose']],
      tick=[(12, spawn_actor(2, u(1300), u(320), initial_state=3)), (12, set_var('', HOLE_FRAMES, 0, by_index=HOLE))],
      enter=[change_side(), movex(0)], priority=7),
  '623C': dict(slot=78, name='Twin Horizon', input=('623', ['C']), move_file='58_NOA_TwinHorizon', hbp='35_Hitbox_TwinHorizon',
      duration=38, keys=[['stand', 0], ['bh_summon', 4], ['bh_summon', 24, {'dx': -3}], ['stand', 30]],
      boxes=[[0, 0, 'none'], [12, 2, 'pose']],
      # Oct 25 night: the far hole collapses at once (pulls them in from across the screen and throws them toward Noah,
      # into the near hole, which waits and launches them away on contact)
      tick=[(8, spawn_actor(2, u(330), u(320), initial_state=1)), (8, spawn_actor(2, u(1300), u(320), initial_state=4)),
            (8, set_var('', HOLE_FRAMES, 0, by_index=HOLE)), (12, frame_props(0))],
      enter=[change_side(), movex(0), frame_props(INV_STRIKE | INV_THROW)], exit=[frame_props(0)],
      meter=4000, flash=15, priority=9, ai=0x10 | 2 | 0x1000),
  'SNAP': dict(slot=79, name='Collapse', input=('623', ['A', 'B', 'C']), move_file='59_NOA_Collapse', hbp='36_Hitbox_Collapse',
      duration=28, keys=[['bh_snap', 0], ['bh_snap', 16, {'dx': -3}], ['stand', 22]],
      boxes=[[0, 0, 'pose']], tick=[(6, trigger_holes())], enter=[movex(0)], priority=10,
      move_extra={'VariablesRequirement': [var_cond(HOLE, 1, GREATER_EQUAL, DECREASE)], 'VariablesChange': [var_change(HOLE, 0)]}),
  # ---- 214: the grab lunge and the drain (stocks energy)
  '214A': dict(slot=80, name='Void Grasp', input=('214', ['A']), move_file='60_NOA_VoidGrasp', hbp='37_Hitbox_VoidGrasp',
      duration=46, keys=[['k_start', 0], ['k_lunge', 10], ['k_lunge', 24, {'dx': -6}], ['k_rec', 30], ['stand', 40]],
      boxes=[[0, 0, 'pose+prox'], [12, 1, 'atk', GRASP, None, [[30, 60, 470, 340]]], [18, 2, 'pose'], [30, 2, 'pose']],
      tick=[(10, movex(150000)), (18, movex(0))], enter=[change_side(), movex(0)],
      hit_confirm=[ev([check_hit(HIT)], [play_state(81)])], priority=7, ai=0x10 | 2),
  'GRASP': dict(slot=81, name='Void Grasp (drain)', hbp='38_Hitbox_VoidGrasp_Drain', duration=56,
      keys=[['k_recoil', 0], ['k_absorb', 14], ['k_absorb', 26, {'dx': -3}], ['k_rec', 36], ['stand', 48]],
      boxes=[[0, 0, 'pose'], [14, 1, 'atk_inv', DRAIN], [16, 2, 'pose'], [28, 1, 'atk_inv', DRAIN_END], [30, 2, 'pose']],
      tick=[(14, reset_hit()), (28, reset_hit()), (14, set_var('', 1, 0, by_index=STOCK)), (28, camera_shake(0.02, 8))],
      tick_ranges=[((0, 27), hold_opp(9500, 0))],
      enter=[movex(0), movey(0)], priority=7, ai=0x10 | 2),
  '214B': dict(slot=82, name='Abyss Hammer', input=('214', ['B', 'C']), move_file='61_NOA_AbyssHammer', hbp='39_Hitbox_AbyssHammer',
      duration=120, keys=[['h_prep', 0], ['h_turn', 6], ['h_smash', 18], ['h_follow', 24]],
      boxes=[[0, 0, 'pose'], [18, 1, 'atk', HAMMER], [24, 2, 'pose']],
      tick=[(6, movey(62000)), (6, movex(20000))], tick_ranges=[((7, 400), gravity())],
      enter=[change_side(), movex(0)], meteor_land=97, land_from=12, priority=7, ai=0x10 | 2),
  '214C': dict(slot=83, name='Void Devour', input=('214', ['C']), move_file='62_NOA_VoidDevour', hbp='40_Hitbox_VoidDevour',
      duration=48, keys=[['k_start', 0], ['k_lunge', 8], ['k_lunge', 24, {'dx': -6}], ['k_rec', 32], ['stand', 42]],
      boxes=[[0, 0, 'none'], [10, 1, 'atk_inv', GRASP_C, None, [[30, 60, 500, 380]]], [18, 2, 'pose'], [32, 2, 'pose']],
      tick=[(8, movex(170000)), (18, movex(0)), (18, frame_props(0))],
      enter=[change_side(), movex(0), frame_props(INV_STRIKE | INV_THROW | INV_PROJ)], exit=[frame_props(0)],
      hit_confirm=[ev([check_hit(HIT)], [play_state(84)])], meter=4000, flash=15, priority=9, afterimages=True,
      ai=0x10 | 2 | 0x1000),
  'DEVOUR': dict(slot=84, name='Void Devour (drain)', hbp='41_Hitbox_VoidDevour_Drain', duration=84,
      keys=[['x_face', 0], ['x_lift', 10], ['x_drain', 22], ['x_drain', 30, fx('fx_dex_1')], ['x_drain', 33, fx('fx_dex_2')],
            ['x_drain', 36, fx('fx_dex_3')], ['x_drain', 40, fx('fx_dex_4')], ['x_drain', 45, fx('fx_dex_5')], ['x_drain', 50, fx('fx_dex_6')],
            ['x_recoil', 56], ['stand', 72]],
      boxes=[[0, 0, 'none'], [22, 1, 'atk_inv', DEVOUR], [24, 2, 'none'], [30, 1, 'atk_inv', DEVOUR], [32, 2, 'none'],
             [36, 1, 'atk_inv', DEVOUR_END], [40, 2, 'pose']],
      tick=[(22, reset_hit()), (30, reset_hit()), (36, reset_hit()), (22, set_var('', 1, 0, by_index=STOCK)),
            (36, camera_shake(0.05, 14)), (56, movex(-20000)), (64, movex(0)), (40, frame_props(0))],
      tick_ranges=[((0, 9), hold_opp(9000, 0)), ((10, 35), hold_opp(8000, 2500))],
      enter=[movex(0), movey(0), frame_props(INV_STRIKE | INV_THROW | INV_PROJ)], exit=[frame_props(0)], priority=9,
      afterimages=True, ai=0x10 | 2 | 0x1000),
  'RAY': dict(slot=85, name='Overflow Ray', input=('214', ['A', 'B', 'C']), move_file='63_NOA_OverflowRay', hbp='42_Hitbox_OverflowRay',
      duration=58, keys=[['k_start', 0], ['ray_pose', 8], ['ray_pose', 14, dict(fx('fx_ray'), fx_sx=1.65, fx_dx=-45)], ['ray_pose', 36], ['k_rec', 40], ['stand', 50]],
      boxes=[[0, 0, 'pose'], [14, 1, 'atk', RAY, None, RAY_BOX], [18, 2, 'pose'], [22, 1, 'atk', RAY, None, RAY_BOX],
             [26, 2, 'pose'], [30, 1, 'atk', RAY_END, None, RAY_BOX], [34, 2, 'pose']],
      tick=[(22, reset_hit()), (30, reset_hit()), (14, camera_shake(0.02, 20))], enter=[change_side(), movex(0)], priority=9,
      move_extra={'VariablesRequirement': [var_cond(STOCK, 1, GREATER_EQUAL)], 'VariablesChange': [var_change(STOCK, 0)]},
      ai=0x10 | 2),
  # ---- air 214
  'jGRASP': dict(slot=92, name='Fallen Grasp', input=('214', ['A']), move_file='64_NOA_FallenGrasp', hbp='43_Hitbox_FallenGrasp',
      duration=90, keys=[['ag_reach', 0], ['ag_grab', 6], ['ag_down', 16]],
      boxes=[[0, 0, 'pose'], [8, 1, 'atk', AIR_GRAB], [14, 2, 'pose']],
      tick=[(0, movex(0)), (0, movey(10000)), (16, movex(20000))], tick_ranges=[((1, 15), gravity(30000)), ((16, 400), gravity())],
      hit_confirm=[ev([check_hit(HIT)], [play_state(93)])], air_land=True, land_from=4, air=True, ground=False, priority=8,
      ai=0x10 | 4),
  'jGRASP_hit': dict(slot=93, name='Fallen Grasp (drag)', hbp='44_Hitbox_FallenGrasp_Drag', duration=120,
      keys=[['ag_grab', 0], ['ag_down', 4]],
      boxes=[[0, 0, 'none']],
      tick=[(4, movex(60000)), (4, movey(-170000))], tick_ranges=[((0, 999), hold_opp(9000, -3000))],
      enter=[movex(0), movey(0), frame_props(INV_STRIKE | INV_THROW | INV_PROJ)], exit=[frame_props(0)],
      meteor_land=94, land_from=2, priority=8, ai=0x10 | 4),
  'jGRASP_land': dict(slot=94, name='Fallen Grasp (blast)', hbp='45_Hitbox_FallenGrasp_Blast', duration=42,
      keys=[['ag_land', 0, fx('fx_blast_1')], ['ag_land', 3, fx('fx_blast_2')], ['ag_land', 7, fx('fx_blast_3')],
            ['ag_land', 13, fx('fx_blast_4')], ['ag_land', 18], ['crouch_x', 28], ['stand', 34]],
      boxes=[[0, 1, 'atk_inv', GROUND_BLAST], [6, 2, 'pose']],
      tick=[(0, camera_shake(0.04, 12)), (6, frame_props(0))],
      enter=[movex(0), movey(0), frame_props(INV_STRIKE | INV_THROW)], exit=[frame_props(0)], priority=8, ai=0x10 | 2),
  'jHAMMER': dict(slot=95, name='Abyss Hammer', input=('214', ['B', 'C']), move_file='65_NOA_AbyssHammer_Air', hbp='46_Hitbox_AbyssHammer_Air',
      duration=90, keys=[['h_turn', 0], ['h_smash', 8], ['h_follow', 14]],
      boxes=[[0, 0, 'pose'], [8, 1, 'atk', AIR_HAMMER], [14, 2, 'pose']],
      tick=[(0, movex(0)), (0, movey(14000)), (8, movey(-80000)), (8, movex(20000))],
      tick_ranges=[((1, 7), gravity(40000)), ((9, 400), gravity())],
      meteor_land=97, land_from=4, air=True, ground=False, priority=8, ai=0x10 | 4),
  'LAND': dict(slot=97, name='Abyss Hammer (landing)', hbp='47_Hitbox_HammerLanding', duration=24,
      keys=[['h_land', 0], ['h_rec', 10], ['stand', 18]], boxes=[[0, 0, 'pose'], [10, 0, 'pose']],
      enter=[movex(0), movey(0)], ai=0x10 | 2),
  # ---- supers
  'S1': dict(slot=105, name='Raging Storm', input=('236236', ['A', 'B', 'C']), move_file='66_NOA_RagingStorm', hbp='48_Hitbox_RagingStorm',
      duration=126,
      keys=[['rs_10', 0], ['rs_11', 3], ['rs_12', 6], ['rs_13', 9], ['rs_14', 12], ['rs_15', 15, fx('fx_rs_slam_0')],
            ['rs_15', 18, fx('fx_rs_slam_1')], ['rs_15', 21, fx('fx_rs_slam_2')], ['rs_15', 24, fx('fx_rs_slam_3')]]
           + [['rs_15', 27 + i * 5, fx('fx_rs_loop_%d' % (i % 6))] for i in range(10)]
           + [['rs_15', 77, fx('fx_rs_fade_0')], ['rs_15', 81, fx('fx_rs_fade_1')], ['rs_51', 85, fx('fx_rs_fade_2')],
              ['rs_52', 89, fx('fx_rs_fade_3')], ['rs_53', 94], ['rs_54', 99], ['rs_55', 104], ['rs_60', 110], ['rs_65', 118]],
      boxes=[[0, 0, 'none'], [15, 1, 'atk_inv', RS_SLAM, None, RS_BOX], [18, 2, 'none']]
            + sum([[[27 + i * 6, 1, 'atk_inv', RS_STORM, None, RS_BOX], [29 + i * 6, 2, 'none']] for i in range(8)], [])
            + [[77, 1, 'atk_inv', RS_END, None, RS_BOX], [80, 2, 'none'], [94, 2, 'pose']],
      tick=[(15, reset_hit()), (15, camera_shake(0.05, 14))] + [(27 + i * 6, reset_hit()) for i in range(8)]
           + [(77, reset_hit()), (77, camera_shake(0.07, 18)), (94, frame_props(0))],
      tick_ranges=[((18, 76), hold_opp(0, 11000, 120))],
      enter=[change_side(), movex(0), movey(0), frame_props(INV_STRIKE | INV_THROW | INV_PROJ)], exit=[frame_props(0)],
      meter=6000, flash=20, priority=10, afterimages=True, ai=0x10 | 2 | 0x1000,
      move_extra={'NetsuPauseFrames': 75, 'NetsuPauseState': 106}),
  'S1_charge': dict(slot=106, name='Raging Storm (charge)', hbp='49_Hitbox_RagingStorm_Charge', duration=25,
      # only its picture is used: the crossed-arm charge that loops through the super's pause (MoveSettings.NetsuPauseState)
      keys=[['rs_00', 0, fx('fx_rs_charge_0')], ['rs_00', 5, fx('fx_rs_charge_1')], ['rs_00', 10, fx('fx_rs_charge_2')],
            ['rs_00', 15, fx('fx_rs_charge_3')], ['rs_00', 20, fx('fx_rs_charge_4')]],
      boxes=[[0, 0, 'none']], ai=0x10 | 2),
  'S2': dict(slot=107, name='God Press', input=('214214', ['A', 'B', 'C']), move_file='67_NOA_GodPress', hbp='50_Hitbox_GodPress',
      duration=54, keys=[['gp_01', 0], ['gp_02', 10], ['gp_02', 28, {'dx': -6}], ['gp_12', 36], ['stand', 46]],
      boxes=[[0, 0, 'none'], [12, 1, 'atk_inv', GP_GRAB, None, [[30, 40, 520, 420]]], [26, 2, 'pose']],
      tick=[(10, movex(190000)), (26, movex(0)), (26, frame_props(0))],
      enter=[change_side(), movex(0), frame_props(INV_STRIKE | INV_THROW | INV_PROJ)], exit=[frame_props(0)],
      hit_confirm=[ev([check_hit(HIT)], [play_state(108)])], meter=6000, flash=20, priority=10, ai=0x10 | 2 | 0x1000),
  'S2_carry': dict(slot=108, name='God Press (carry)', hbp='51_Hitbox_GodPress_Carry', duration=40,
      keys=[['gp_02', 0]], boxes=[[0, 0, 'none-pass']],
      tick=[(0, movex(240000))], tick_ranges=[((0, 999), hold_opp(*GP_HOLD))],
      # to the wall he faces (stops 3.6 m from the stage's end, so they're slammed where the camera still shows them),
      # or for 40 frames at most
      transitions=[ev([rel_x(lo=WALL_LIMIT - CARRY_STOP, target=0)], [play_state(109)]), ev([state_ended()], [play_state(109)])],
      enter=[frame_props(INV_STRIKE | INV_THROW | INV_PROJ), movey(0)], exit=[frame_props(0)], priority=10, afterimages=True,
      ai=0x10 | 2 | 0x1000),
  'S2_slams': dict(slot=109, name='God Press (wall slams)', hbp='52_Hitbox_GodPress_Slam', duration=54,
      keys=sum([[['gp_05', c * 18], ['gp_06', c * 18 + 8, fx('fx_wall_1')], ['gp_06', c * 18 + 10, fx('fx_wall_2')],
                 ['gp_06', c * 18 + 12, fx('fx_wall_3')], ['gp_06', c * 18 + 14, fx('fx_wall_4')]] for c in range(3)], []),
      boxes=sum([[[c * 18 + 8, 1, 'atk_inv-pass', GP_SLAM, None, [[300, 0, 900, 700]]], [c * 18 + 10, 2, 'none-pass']] for c in range(3)],
                [[0, 0, 'none-pass']]),
      tick=sum([[(c * 18 + 8, reset_hit()), (c * 18 + 8, camera_shake(0.04, 10))] for c in range(3)], [(0, movex(0))]),
      tick_ranges=sum([[((c * 18, c * 18 + 7), hold_opp(*PULL_HOLD)), ((c * 18 + 8, c * 18 + 17), hold_opp(*SLAM_HOLD))] for c in range(3)], []),
      transitions=[ev([state_ended()], [play_state(110)])],
      enter=[frame_props(INV_STRIKE | INV_THROW | INV_PROJ), movex(0), movey(0)], exit=[frame_props(0)], priority=10,
      ai=0x10 | 2 | 0x1000),
  'S2_finish': dict(slot=110, name='God Press (discharge)', hbp='53_Hitbox_GodPress_Discharge', duration=110,
      keys=[['gp_07', 0], ['gp_08', 12], ['gp_08', 14, fx('fx_final_1')], ['gp_08', 18, fx('fx_final_2')], ['gp_08', 22, fx('fx_final_3')],
            ['gp_08', 26, fx('fx_final_4')], ['gp_08', 30, fx('fx_final_5')], ['gp_09', 36, fx('fx_final_6')], ['gp_09', 42]],
      boxes=[[0, 0, 'none-pass'], [18, 1, 'atk_inv-pass', GP_SPARK, None, [[200, 150, 800, 800]]], [20, 2, 'none-pass'],
             [24, 1, 'atk_inv-pass', GP_SPARK, None, [[200, 150, 800, 800]]], [26, 2, 'none-pass'],
             [30, 1, 'atk_inv-pass', GP_END, None, [[150, 100, 850, 850]]], [34, 2, 'none']],
      tick=[(18, reset_hit()), (24, reset_hit()), (30, reset_hit()), (30, camera_shake(0.08, 22)),
            (36, movex(-36000)), (36, movey(62000)), (40, frame_props(0))],
      tick_ranges=[((0, 11), hold_opp(*LIFT_HOLD)), ((12, 29), hold_opp(LIFT_HOLD[0], LIFT_HOLD[1] + 1000)), ((37, 400), gravity())],
      enter=[frame_props(INV_STRIKE | INV_THROW | INV_PROJ), movex(0), movey(0)], exit=[frame_props(0)],
      meteor_land=111, land_from=40, priority=10, afterimages=True, ai=0x10 | 2 | 0x1000),
  'S2_land': dict(slot=111, name='God Press (landing)', hbp='54_Hitbox_GodPress_Landing', duration=44,
      keys=[['gp_10', 0], ['gp_11', 16], ['gp_12', 28], ['stand', 38]], boxes=[[0, 0, 'pose'], [16, 0, 'pose']],
      enter=[movex(0), movey(0)], tick=[(0, camera_shake(0.02, 6))], ai=0x10 | 2),
}
DP_LAND = 97
# moves that play a state made above (the B+C super inputs, as for every fighter)
EXTRA_MOVES = {
  'S1bc': dict(state=105, name='Raging Storm', input=('236', ['BC']), move_file='68_NOA_RagingStorm_BC', meter=6000, flash=20, priority=10,
               move_extra={'NetsuPauseFrames': 75, 'NetsuPauseState': 106}),
  'S2bc': dict(state=107, name='God Press', input=('214', ['BC']), move_file='69_NOA_GodPress_BC', meter=6000, flash=20, priority=10),
}
GROUND_CANCEL_ORDER = ['S2', 'S1', 'S2bc', 'S1bc', 'RAY', 'SNAP', '214C', '214B', '214A', '623C', '623B', '623A', '236C', '236B', '236A']
AIR_CANCEL_ORDER = ['jGRASP', 'jHAMMER']
GROUND_NORMALS = ['23_NOA_5A', '24_NOA_5B', '25_NOA_5C', '26_NOA_2A', '27_NOA_2B', '28_NOA_2C', '32_NOA_6C']
AIR_NORMALS = ['29_NOA_j_5A', '30_NOA_j_5B', '31_NOA_j_5C']
# stance order: the neutral lookup runs from the END of the list (later = checked first): the beam (needs the stock)
# before 214 A / B, the snap (needs an open hole) before 623, the supers before everything
STANCE_ORDER = ['236A', '236B', '236C', '623A', '623B', '623C', '214A', '214B', '214C', 'jGRASP', 'jHAMMER', 'RAY', 'SNAP',
                'S1bc', 'S2bc', 'S1', 'S2']
INPUTS = {('236', 'A'): '44_Input_236A', ('236', 'B|C'): '45_Input_236B_or_C', ('236', 'C'): '20_Input_236C',
          ('623', 'A'): '46_Input_623A', ('623', 'B|C'): '47_Input_623B_or_C', ('623', 'C'): '24_Input_623C',
          ('214', 'A'): '40_Input_214A', ('214', 'B|C'): '41_Input_214B_or_C', ('214', 'C'): '21_Input_214C',
          ('236', 'BC'): '25_Input_236BC', ('214', 'BC'): '48_Input_214BC', ('236236', 'A|B|C'): '49_Input_236236',
          ('214214', 'A|B|C'): '50_Input_214214', ('214', 'A|B'): '54_Input_214A_or_B', ('214', 'A|B|C'): '57_Input_214_any', ('623', 'A|B|C'): '56_Input_623_any'}
MANUAL_BOXES = {}

# ---------------------------------------------------------------------------------------------
# his projectiles: actors of their own (index in NOA_SpawnablesList = the spawn_actor index above)
PR = 'Noah_Complete/Specials/'
def pfx(src, width, pin, at, **kw):
    """an effect frame of a projectile: drawing `width` game px wide, its point `pin` (drawing px) at `at` (world px
    from the projectile's origin)"""
    return dict(src=src, width=width, pin=pin, at=at, **kw)
PFRAMES = {}
for i in range(1, 5):
    PFRAMES['wave_%d' % i] = pfx(PR + '236/Traveling_Wave/Frame_%02d.png' % i, 400, (560, 490), (60, 0))
    PFRAMES['wall_%d' % i] = pfx(PR + '236/EX_Wall/Frame_%02d.png' % i, 580, (560, 505), (60, 0))
    PFRAMES['hole_%d' % i] = pfx(PR + '623/Hole_Idle/Frame_%02d.png' % i, 300, (400, 250), (0, 0))
    PFRAMES['suck_%d' % i] = pfx(PR + '623/Suction/Frame_%02d.png' % i, 520, (384, 256), (0, 0))
WAVE_BOX = [[-70, 0, 200, 270]]
WALL_BOX = [[-300, 0, 260, 560]]
SUCK_BOX = [[-180, -180, 180, 180]]
BURST_BOX = [[-170, -170, 170, 170]]
CONTACT_BOX = [[-120, -120, 120, 120]]
CONTACT_NEAR = attack(600, 40, 18, kb=(-60000, 50000), air_kb=(-60000, 50000), reaction=7, air_reaction=7, hitstun_type=KNOCKDOWN,
                      kb_gravity=200000, stop=12, gain=300)
CONTACT_FAR = attack(600, 40, 18, kb=(50000, 55000), air_kb=(50000, 55000), reaction=8, air_reaction=8, hitstun_type=KNOCKDOWN,
                     kb_gravity=200000, stop=12, gain=300)
def hole_closed():
    """a hole that burst on contact clears Noah's HoleTimer, unless his other hole still waits (engine: NetsuOwnerVariableAction)"""
    return Obj(ACT + 'NetsuOwnerVariableAction.cs', ByIndex=HOLE, Value=0, OnlyIfLastOfPool=2, WaitingStates=Packed('PackedInt32Array', [1, 3]))
HOLE_PULL = (u(1300), 800)     # suction reach (1300 px = 3.6 m) and speed (units per frame: ~4.8 m/s)
PROJ = {
  'wave': dict(tag='NOW', key='NoahWave', pool=3, file='NOA_Wave', states=[
      dict(key='Roll', name='Shade Wave', duration=72, keys=[['wave_%d' % (i % 4 + 1), i * 4] for i in range(18)],
           boxes=[[0, 1, 'atk', WAVE, WAVE_BOX]], enter=[movex(95000), movey(0)],
           hit_confirm=[ev(acts=[play_state(2)])], end='leave'),
      dict(key='Fade', name='Shade Wave (fade)', duration=8, keys=[['wave_4', 0]], boxes=[[0, 0, 'none']], enter=[movex(0)], end='leave'),
  ]),
  'wall': dict(tag='NOX', key='NoahWall', pool=1, file='NOA_Wall', states=[
      dict(key='Push', name='Umbral Wall', duration=60, keys=[['wall_%d' % (i % 4 + 1), i * 5] for i in range(12)],
           boxes=[[2, 1, 'atk', WALL1, WALL_BOX], [6, 2, 'none'], [16, 1, 'atk', WALL1, WALL_BOX], [20, 2, 'none'],
                  [30, 1, 'atk', WALL3, WALL_BOX], [34, 2, 'none']],
           enter=[movex(16000), movey(0)], tick=[(16, reset_hit()), (30, reset_hit())], end='leave'),
  ]),
  'hole': dict(tag='NOH', key='NoahHole', pool=2, file='NOA_Hole', states=[
      # Oct 25 night: the waiting holes hit on contact (like the Cecilia Duel prototype): the near one launches them away,
      # the far one throws them toward Noah, and the hole bursts (5 / 6). The snap still works on a waiting hole.
      dict(key='NearIdle', name='Event Horizon (near)', duration=HOLE_FRAMES, keys=[['hole_%d' % (i % 4 + 1), i * 6] for i in range(HOLE_FRAMES // 6)],
           boxes=[[0, 0, 'none'], [6, 1, 'atk', CONTACT_NEAR, CONTACT_BOX]], enter=[movex(0), movey(0)],
           hit_confirm=[ev(acts=[play_state(5), hole_closed()])], end='leave_hole'),
      dict(key='NearSuck', name='Collapse (near)', duration=48, keys=[['suck_%d' % (i % 4 + 1), i * 4] for i in range(10)] + [['hole_1', 40]],
           boxes=[[0, 0, 'none'], [12, 1, 'atk', SUCK, SUCK_BOX], [14, 2, 'none'], [24, 1, 'atk', SUCK, SUCK_BOX], [26, 2, 'none'],
                  [36, 1, 'atk', BURST_NEAR, BURST_BOX], [40, 2, 'none']],
           enter=[movex(0), movey(0)], tick=[(12, reset_hit()), (24, reset_hit()), (36, reset_hit()), (36, camera_shake(0.03, 10))],
           ranges=[((0, 35), pull(*HOLE_PULL))], end='leave'),
      dict(key='FarIdle', name='Event Horizon (far)', duration=HOLE_FRAMES, keys=[['hole_%d' % (i % 4 + 1), i * 6] for i in range(HOLE_FRAMES // 6)],
           boxes=[[0, 0, 'none'], [6, 1, 'atk', CONTACT_FAR, CONTACT_BOX]], enter=[movex(0), movey(0)],
           hit_confirm=[ev(acts=[play_state(6), hole_closed()])], end='leave_hole'),
      dict(key='FarSuck', name='Collapse (far)', duration=48, keys=[['suck_%d' % (i % 4 + 1), i * 4] for i in range(10)] + [['hole_1', 40]],
           boxes=[[0, 0, 'none'], [12, 1, 'atk', SUCK, SUCK_BOX], [14, 2, 'none'], [24, 1, 'atk', SUCK, SUCK_BOX], [26, 2, 'none'],
                  [36, 1, 'atk', BURST_FAR, BURST_BOX], [40, 2, 'none']],
           enter=[movex(0), movey(0)], tick=[(12, reset_hit()), (24, reset_hit()), (36, reset_hit()), (36, camera_shake(0.03, 10))],
           ranges=[((0, 35), pull(*HOLE_PULL))], end='leave'),
      dict(key='NearPop', name='Event Horizon (near, burst)', duration=14, keys=[['suck_3', 0], ['suck_4', 5], ['hole_1', 10]],
           boxes=[[0, 0, 'none']], enter=[movex(0), movey(0)], end='leave'),
      dict(key='FarPop', name='Event Horizon (far, burst)', duration=14, keys=[['suck_3', 0], ['suck_4', 5], ['hole_1', 10]],
           boxes=[[0, 0, 'none']], enter=[movex(0), movey(0)], end='leave'),
  ]),
}
PROJ_ORDER = ['wave', 'wall', 'hole']     # = the spawn_actor indices 0, 1, 2

def build_projectiles(noah_port):
    """manifest, sprites, hitboxes, states, data, scenes and the SpawnablesList for his projectiles"""
    import build, assists
    from PIL import Image
    mp = os.path.join(HERE, 'manifests', PJ + '.json'); os.makedirs(os.path.dirname(mp), exist_ok=True)
    nm = json.load(open(os.path.join(HERE, 'manifests', CH + '.json'), encoding='utf-8'))
    m = {k: nm[k] for k in ('source_root', 'source_root_device', 'reference', 'game')}
    m.update({'character': PJ, 'tag': 'NOP', 'fx': 'none', 'head_frac': 0.23, 'source_dirs': [os.path.dirname(nm['reference'])]})
    frames = {}
    base_k = noah_port.BASE
    for fid, f in PFRAMES.items():
        img = Image.open(os.path.join(noah_port.root, f['src'])); w, h = img.size
        k = f['width'] / float(w)                       # output px per drawing px
        px, py = f['pin']; bx, by = f['at']
        frames[fid] = {'src': f['src'], 'scale': round(base_k / k, 5), 'anchor': 'center',
                       'at': [round(bx - (px - w / 2.0) * k, 2), round(by - (h / 2.0 - py) * k, 2)]}
    m['frames'] = frames
    anims = {}
    for pk in PROJ_ORDER:
        p = PROJ[pk]
        for i, s in enumerate(p['states']):
            name = '%d_%s_%s' % (i + 1, p['tag'], s['key'])
            anims[name] = {'keys': s['keys'], 'duration': s['duration'],
                           'hitboxes': [[b[0], b[1], '%d_Hitbox_%s_%s_%d' % (i + 1, p['tag'], s['key'], n)] for n, b in enumerate(s['boxes'])]}
        anims['0_%s_Hidden' % p['tag']] = {'keys': [[p['states'][0]['keys'][0][0], 0]], 'duration': 1, 'hitboxes': []}
    m['animations'] = anims
    json.dump(m, open(mp, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    ap = os.path.join(HERE, 'analysis', PJ + '.json'); os.makedirs(os.path.dirname(ap), exist_ok=True)
    if not os.path.exists(ap):
        import shutil; shutil.copyfile(os.path.join(HERE, 'analysis', CH + '.json'), ap)
    port = build.Port(PJ)
    spawn_objs = []
    for pk in PROJ_ORDER:
        p = PROJ[pk]; tag = p['tag']
        states = {}
        for i, s in enumerate(p['states']):
            idx = i + 1; aname = '%d_%s_%s' % (idx, tag, s['key'])
            hbs = []
            for n, b in enumerate(s['boxes']):
                at_, stage, kind = b[0], b[1], b[2]
                els = []
                if kind == 'atk':
                    for (x0, y0, x1, y1) in b[4]: els.append(box(HIT_T, x0, y0, x1, y1, **dict(b[3], HitboxType=PROJECTILE_T, AllowSelfPushback=False)))
                hres = PA + 'Hitboxes/%d_Hitbox_%s_%s_%d.tres' % (idx, tag, s['key'], n)
                write(hres, Hitboxes(els, None), force=True); hbs.append((at_, stage, hres))
            ares = PA + 'AnimationData/%s_AnimData.tres' % aname
            write(ares, AnimData(s['duration'], hbs), force=True)
            port.build_anim(aname)
            tick = [ev([at(f)], [act]) for f, act in s.get('tick', [])]
            tick += [ev([at_range(a0, a1)], [act]) for (a0, a1), act in s.get('ranges', [])]
            trans = []
            if s.get('end') in ('leave', 'leave_hole'): trans.append(ev([state_ended()], [set_active(False), movex(0), movey(0)]))
            sres = PA + 'States/%d_%s_%s.tres' % (idx, tag, s['key'])
            write(sres, State(s['name'], COMBAT, ares, transitions=trans, enter=s.get('enter', ()), tick=tick,
                              hit_confirm=s.get('hit_confirm', ())), force=True)
            states[idx] = sres
        hidden_a = PA + 'AnimationData/0_%s_Hidden_AnimData.tres' % tag
        write(hidden_a, AnimData(1, []), force=True); port.build_anim('0_%s_Hidden' % tag)
        hres = PA + 'States/0_%s_Hidden.tres' % tag
        write(hres, State('Hidden', 0, hidden_a), force=True); states[0] = hres
        dres = PA + '0_%s_Data.tres' % tag
        write(dres, Obj(SR + 'DataContainer.cs', States=[Ext(states[i]) for i in sorted(states)], BaseAttack=100, BaseDefense=100), force=True)
        f0 = p['states'][0]['keys'][0][0]; c0, o0, _ = port.frame(f0)
        scene = PA + 'Instances/%s.tscn' % p['file']
        txt = assists.scene_text(tag + '_' + p['key'], dres, port.res_dir + '/' + f0 + '.png', o0, res_uid(scene) or new_uid(), shadow=False)
        write_text(scene, txt, force=True)
        spawn_objs.append(Obj(SR + 'SpawnObject.cs', Key=p['key'], Instance=Ext(scene, 'PackedScene'), PoolSize=p['pool']))
        print('projectile', pk, 'states', len(states), flush=True)
    spw = A + 'NOA_SpawnablesList.tres'
    write(spw, Obj(SR + 'SpawnsList.cs', SpawnObjects=spawn_objs), force=True)
    return spw

def patch_skins(spw):
    """his four skins: his own SpawnablesList, and the Stock / HoleTimer variables (Parameters/Variables 3 and 4)"""
    spw_uid = res_uid(spw)
    for n in range(4):
        p = res_file(A + 'Instances/NOA_Fighter_Skin%02d.tscn' % n)
        t = open(p, encoding='utf-8').read(); t0 = t
        t = re.sub(r'\[ext_resource type="Resource"[^\]]*path="res://actors/_shared/sakuga/Shared_SpawnablesList.tres" id="([^"]+)"\]',
                   lambda m_: '[ext_resource type="Resource" uid="%s" path="%s" id="%s"]' % (spw_uid, spw, m_.group(1)), t)
        if 'name="Stock"' not in t:
            cv = re.search(r'\[ext_resource type="Script"[^\]]*path="res://engine/sakuga/Components/CustomVariable.cs" id="([^"]+)"\]', t).group(1)
            t = t.replace('NodePath("Variables/IsDashJump")]', 'NodePath("Variables/IsDashJump"), NodePath("Variables/Stock"), NodePath("Variables/HoleTimer")]')
            add = ('\n[node name="Stock" type="Node" parent="Parameters/Variables"]\nscript = ExtResource("%s")\nReset = true\nMaxValue = 1\n'
                   'metadata/_custom_type_script = "uid://dqqr3jnsmcig6"\n'
                   '\n[node name="HoleTimer" type="Node" parent="Parameters/Variables"]\nscript = ExtResource("%s")\nReset = true\nMaxValue = %d\n'
                   'StartingFactor = 1\nStartingMode = 2\nmetadata/_custom_type_script = "uid://dqqr3jnsmcig6"\n') % (cv, cv, HOLE_FRAMES)
            # after the IsDashJump node block
            i = t.index('[node name="IsDashJump"'); j = t.find('\n[node', i + 10)
            t = (t[:j] + '\n' + add + t[j:]) if j >= 0 else (t.rstrip('\n') + '\n' + add)
        if t != t0:
            open(p, 'w', encoding='utf-8', newline='\n').write(t); fdk.LOG.append('skin: ' + p)

# ---------------------------------------------------------------------------------------------
def input_res(motion, buttons):
    res = INP + INPUTS[(motion, '|'.join(buttons))] + '.tres'
    if not os.path.exists(res_file(res)):
        write(res, MotionInputs(motion, buttons))
    return res

def hitbox_files(mk, m):
    names = []
    for i, b in enumerate(m['boxes']):
        at_, stage, kind = b[0], b[1], b[2]; props = b[3] if len(b) > 3 else None
        manual = b[5] if len(b) > 5 else None
        name = '%s_%d' % (m['hbp'], i); res = hb(name); names.append((at_, stage, name, kind))
        if manual: MANUAL_BOXES[name] = manual
        if os.path.exists(res_file(res)) and not FORCE:
            if props and kind.split('-')[0] in ('atk', 'atk_inv') and not DRY: patch_attacks(res, props)
            continue
        els = []; base = kind.split('-')[0]; pushbox = None if kind.endswith('-pass') else PUSHBOX_STD
        if base in ('pose', 'pose+prox', 'atk'): els += standard_hurt(3)
        if base in ('pose+prox', 'atk'): els.append(box(PROX, 0, 0, 400, 450, HitType=MID))
        if base in ('atk', 'atk_inv'): els.append(box(HIT_T, 40, 100, 300, 360, **props))
        if not DRY: write(res, Hitboxes(els, pushbox), force=FORCE)
    return names

def strip_old_cancels(move_res):
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
    def fn(t):
        old = list_refs(t, 'Moves')
        refs = old[:FIRST_SPECIAL]
        for mr in move_res_list:
            i = t.ext_id_for_path(mr) or t.add_ext('Resource', mr, res_uid(mr), prefer_id='mv_' + re.sub(r'\W', '_', os.path.basename(mr)[:-5]))
            refs.append('ExtResource("%s")' % i)
        for r in old[FIRST_SPECIAL:]:
            e = t.ext_by_id(re.search(r'"([^"]+)"', r).group(1))
            if e and re.search(r'(_Throw|_6C)\.tres$', e.get('path', '')) and r not in refs:
                refs.append(r)
        t.res_set('Moves', '[' + ', '.join(refs) + ']'); t.prune()
    edit_tres(stance_res, fn, BK, 'stance specials')

def set_state_slots(data_res, slots, clear_from=73):
    def fn(t):
        refs = list_refs(t, 'States'); idle = refs[0]
        for n in range(clear_from, len(refs)):
            e = t.ext_by_id(re.search(r'"([^"]+)"', refs[n]).group(1))
            if e and not e.get('path', '').startswith(A): refs[n] = idle
        for slot in sorted(slots):
            sr = slots[slot]
            i = t.add_ext('Resource', sr, res_uid(sr), prefer_id='st_' + re.sub(r'\W', '_', os.path.basename(sr)[:-5]))
            while len(refs) <= slot: refs.append(idle)
            refs[slot] = 'ExtResource("%s")' % i
        t.res_set('States', '[' + ', '.join(refs) + ']'); t.prune()
    return edit_tres(data_res, fn, BK, 'state slots')

TWO_B_CHAINS = [24, 25, 28, 4, 5, 6]

def write_states():
    for mk, m in MOVES.items():
        m['anim'] = '%d_%s_%s' % (m['slot'], TAG, mk)
        sres = A + 'States/%d_%s_%s.tres' % (m['slot'], TAG, mk); m['state_res'] = sres
        tick = [ev([at(fr_)], [act]) for fr_, act in m.get('tick', [])]
        tick += [ev([at_range(a0, b0)], [act]) for (a0, b0), act in m.get('tick_ranges', [])]
        trans = list(m.get('transitions', []))
        if m.get('air_land'):
            trans += [ev([at_range(m.get('land_from', 10), 999), on_ground()], [play_state(DP_LAND)]), ev([state_ended()], [play_state(FALLING)])]
        elif m.get('meteor_land'):
            trans += [ev([at_range(m.get('land_from', 10), 999), on_ground()], [play_state(m['meteor_land'])]),
                      ev([state_ended()], [play_state(FALLING)])]
        elif not m.get('transitions'):
            trans += [ev([state_ended()], [play_state(IDLE)])]
        st = State(m['name'], COMBAT, an(m['anim']), transitions=trans, enter=m.get('enter', ()), tick=tick, exit=m.get('exit', ()),
                   hit_confirm=m.get('hit_confirm', ()), ai=m.get('ai', 0x10 | (4 if m.get('air') else 2)), show_stage=m.get('show_stage'))
        write(sres, st, force=FORCE)

def main():
    if STATES_ONLY:
        write_states(); print('\n'.join(fdk.LOG)); return
    import build
    man_path = os.path.join(HERE, 'manifests', CH + '.json')
    man = json.load(open(man_path, encoding='utf-8'))
    port0 = build.Port(CH)
    fill_fx_scales(port0)
    man['frames'].update(copy.deepcopy(FRAMES))
    hf = man.setdefault('hitfit', {}); hf.setdefault('boxes', {}); hf.setdefault('attack_part', {})
    hf['attack_part'].update({'80_NOA_214A': 'edge', '83_NOA_214C': 'edge', '82_NOA_214B': 'trail', '95_NOA_jHAMMER': 'trail',
                              '92_NOA_jGRASP': 'edge', '107_NOA_S2': 'edge', '94_NOA_jGRASP_land': 'trail_all'})
    anims = []
    for mk, m in MOVES.items():
        aname = '%d_%s_%s' % (m['slot'], TAG, mk)
        m['anim'] = aname; anims.append(aname)
        entry = {'keys': m['keys'], 'duration': m['duration']}
        if m.get('afterimages'): entry['afterimages'] = True
        man['animations'][aname] = entry
        names = hitbox_files(mk, m); m['hb_names'] = names
        entry['hitboxes'] = [[a0, stage, name] for a0, stage, name, kind in names]
        ares = an(aname)
        if not os.path.exists(res_file(ares)) or FORCE:
            if not DRY: write(ares, AnimData(m['duration'], [(a0, stage, hb(name)) for a0, stage, name, kind in names],
                                             afterimages=True if m.get('afterimages') else None), force=FORCE)
    for name, bx in MANUAL_BOXES.items(): hf['boxes'][name] = {'attack': bx}
    if DRY:
        for mk, m in MOVES.items(): print(mk, m['anim'], [n[2] for n in m['hb_names']])
        return
    json.dump(man, open(man_path, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    todo = anims if not ONLY else [a for a in anims if a in ONLY.split(',')]
    p = build.Port(CH)
    for a in todo:
        p.build_anim(a); print('built', a, flush=True)
    import hitfit
    f = hitfit.Fitter(CH)
    for line in f.run(todo, write=True, force=FORCE): print('  ', line, flush=True)
    write_states()
    allm = dict(MOVES); allm.update(EXTRA_MOVES)
    for mk, m in allm.items():
        if 'input' in m: m['move_res'] = A + 'Moves/%s.tres' % m['move_file']
    order = [allm[k]['move_res'] for k in STANCE_ORDER]
    idx = {k: FIRST_SPECIAL + n for n, k in enumerate(STANCE_ORDER)}
    for mk, m in allm.items():
        if 'input' not in m: continue
        cancels = [cancel(idx[k], c, fr_) for k, c, fr_ in m.get('cancels', [])]
        extra = dict(m.get('move_extra') or {})
        mv = Move(m['name'], m['state'] if 'state' in m else m['slot'], input_res(*m['input']), priority=m.get('priority', 7),
                  meter=m.get('meter'), flash=m.get('flash'), ground=m.get('ground', True), air=m.get('air', False), cancels=cancels,
                  extra=extra or None)
        write(m['move_res'], mv, force=FORCE)
    set_state_slots(A + '0_%s_Data.tres' % TAG, {m['slot']: m['state_res'] for m in MOVES.values()})
    set_stance_specials(A + 'Stances/%s_Stance_Main.tres' % TAG, order)
    for n in GROUND_NORMALS + AIR_NORMALS: strip_old_cancels(A + 'Moves/%s.tres' % n)
    for n in GROUND_NORMALS:
        add_cancels(A + 'Moves/%s.tres' % n, [(idx[k], HIT | BLOCK, (0, 999)) for k in GROUND_CANCEL_ORDER], BK)
    for n in AIR_NORMALS:
        add_cancels(A + 'Moves/%s.tres' % n, [(idx[k], HIT | BLOCK, (0, 999)) for k in AIR_CANCEL_ORDER], BK)
    import launchers; launchers.normals_to_6c(CH, BK)   # Oct 26: every ground normal can cancel into 6C
    spw = build_projectiles(p)
    patch_skins(spw)
    print('\n'.join(fdk.LOG))
    print('move indices:', idx)

if __name__ == '__main__':
    main()
