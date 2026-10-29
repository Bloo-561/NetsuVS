"""LETICIA'S MOVES (Oct 24): her specials and supers, built from the drawings in
Fighting_Game_All_Sprites/Leticia (see Guides/Cecilia_and_Leticia_All_Assets_README.txt).

  236A / 236B  Crossfire            shot; follow up with 6+A/B/C (turned shot), then 6+A/B/C again (low finisher)
  236C         Crossfire EX         (2 bars) invincible start, all three shots, knockdown
  623A / 623B  Rising Comet         rising crescent kick (B: two kicks, invincible start)
  623C         Comet Burst          (2 bars) two kicks and a downward shot that spikes them to the floor
  214A         Photon Line          straight beam across the whole screen
  214B         Ricochet Prism       Oct 25: two angles (after Hollow Point): B tapped bounces off the floor first, B held
                                    goes up first; both zigzag floor / head height across the whole screen
  214C         Prism Overdrive      (2 bars) straight shot, ricochet, then the big beam (both full screen)
  j.236A / B   Flux Dive            (in the air) the board flips once (B: twice), then she twirls down at an angle; Oct 25:
                                    the last twirl spikes them down (an air combo ender)
  j.236C       Flux Storm           (2 bars, in the air) three flips, then back to normal air control
  236BC        Stardrive Cannon     (3 bars) huge sustained beam across the screen
  214BC        Crimson Waltz        (3 bars) board rush; on hit: the flame prison floats them up and she circles it on her
                                    board firing into it (Oct 25: one smooth flight, 1 1/4 laps), lands, hair flip, explosion
Names are placeholders: rename them in the Move files (MoveName, shown in the cut-in) and command_list.json.

    python moves_leticia.py          writes everything (Godot closed, or reload the project after)
    python moves_leticia.py --dry    only prints what it would do
    python moves_leticia.py --states only rewrites the state files (movement, timing, cancels into states)
    python moves_leticia.py --only=214A,214B   only those moves' sprites and boxes (states, moves, cancels untouched)

Edit the tables below and run again: frame timings, damage, movement. Files you change in Godot
afterwards are kept (the script says SKIPPED); add --force to overwrite them with the table values.
Pipeline per move: manifest keys -> build.py (sprites + timeline) -> hitbox files -> hitfit.py
(boxes fitted to the drawings) -> state, input, move files -> registered in 0_LET_Data / the stance.
"""
import sys, os, json, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import fdk
from fdk import *
from tres import Tres

CH, TAG = 'leticia', 'LET'
A = 'res://actors/leticia/'
BK = '_backup_stage_select/pre_leticia_moves'
FORCE = '--force' in sys.argv
DRY = '--dry' in sys.argv
STATES_ONLY = '--states' in sys.argv
UPX = 27.5
INP = 'res://actors/_shared/sakuga/Inputs/'
IDLE, FALLING, LANDING = 0, 10, 11
FIRST_SPECIAL = 41          # stance moves 0-40 are the shared system/normal moves; hers start here

def hb(name): return A + 'Hitboxes/%s.tres' % name
def an(name): return A + 'AnimationData/%s_AnimData.tres' % name

# ---------------------------------------------------------------------------------------------
# attack properties (first pass; her 5C does 650, 2C 460)
RK1A = attack(500, 20, 14, kb=(-25000, 0), air_kb=(-12000, 30000), reaction=1, air_reaction=4, stop=10, gain=300)
RK1B = attack(650, 22, 15, kb=(-30000, 0), air_kb=(-15000, 32000), reaction=1, air_reaction=4, stop=11, gain=350)
RK2 = attack(550, 22, 15, kb=(-25000, 0), air_kb=(-12000, 30000), reaction=1, air_reaction=4, stop=10, gain=300)
RK3 = attack(800, 30, 18, kb=(-45000, 25000), air_kb=(-40000, 30000), reaction=7, air_reaction=7, hitstun_type=KNOCKDOWN,
             kb_gravity=200000, stop=14, gain=400, hit_type=LOW)
REX = [attack(400, 40, 18, kb=(-6000, 0), air_kb=(-4000, 20000), reaction=1, air_reaction=5, stop=8, gain=0, scaling=5),
       attack(400, 40, 18, kb=(-6000, 0), air_kb=(-4000, 20000), reaction=1, air_reaction=5, stop=8, gain=0, scaling=5),
       # Oct 25 night: the last shot sends them flying across the screen into a wall bounce: they pop off it high
       # enough to juggle (like Cecilia's 236B: NetsuScreenWall counts the screen edge as a wall)
       attack(900, 60, 20, kb=(-105000, 72000), air_kb=(-105000, 72000), reaction=7, air_reaction=7, hitstun_type=KNOCKDOWN,
              kb_gravity=130000, air_gravity=130000, stop=18, gain=0, scaling=5, extra=dict(BounceTime=120, BounceXIntensity=40))]
DPA = attack(900, 36, 18, kb=(-10000, 60000), air_kb=(-10000, 60000), reaction=8, air_reaction=8, hitstun_type=KNOCKDOWN,
             kb_gravity=220000, stop=13, gain=400)
DPB = [attack(600, 40, 18, kb=(-5000, 80000), air_kb=(-5000, 80000), reaction=8, air_reaction=8, hitstun_type=KNOCKDOWN,
              kb_gravity=240000, stop=10, gain=300),
       attack(700, 40, 18, kb=(-12000, 62000), air_kb=(-12000, 62000), reaction=8, air_reaction=8, hitstun_type=KNOCKDOWN,
              kb_gravity=220000, stop=13, gain=300)]
# Oct 25 night: the two kicks send them very high; if the second one HITS she rides her board up over them and slams them
# back into the floor (CB_SLAM / CB_LAND); on block or a whiff she ends with the old downward shot
DPC = [attack(450, 60, 20, kb=(-4000, 120000), air_kb=(-4000, 120000), reaction=8, air_reaction=8, stop=8, gain=0, scaling=4,
              kb_gravity=240000, air_gravity=240000),
       attack(450, 60, 20, kb=(-4000, 95000), air_kb=(-4000, 95000), reaction=8, air_reaction=8, stop=10, gain=0, scaling=4,
              kb_gravity=240000, air_gravity=240000),
       attack(800, 45, 20, kb=(-10000, -90000), air_kb=(-10000, -90000), reaction=9, air_reaction=9, hitstun_type=HARD_KNOCKDOWN,
              kb_gravity=200000, stop=16, gain=0, scaling=5)]
BEAM_A = attack(600, 24, 16, kb=(-30000, 0), air_kb=(-20000, 25000), reaction=1, air_reaction=5, stop=10, gain=350)
BEAM_B = attack(700, 30, 16, kb=(-15000, 50000), air_kb=(-15000, 50000), reaction=8, air_reaction=8, hitstun_type=KNOCKDOWN,
                kb_gravity=220000, stop=12, gain=350)
BEAM_C = [attack(350, 50, 18, kb=(-5000, 0), air_kb=(-3000, 20000), reaction=1, air_reaction=5, stop=6, gain=0, scaling=4),
          attack(400, 50, 18, kb=(-5000, 0), air_kb=(-3000, 15000), reaction=1, air_reaction=5, stop=6, gain=0, scaling=4),
          attack(300, 40, 18, kb=(-5000, 0), air_kb=(-3000, 10000), reaction=1, air_reaction=5, stop=5, gain=0, scaling=3),
          # Oct 25 night: the big beam blasts them across the screen into a wall bounce
          attack(900, 60, 20, kb=(-105000, 72000), air_kb=(-105000, 72000), reaction=7, air_reaction=7, hitstun_type=KNOCKDOWN,
                 kb_gravity=130000, air_gravity=130000, stop=18, gain=0, scaling=5, extra=dict(BounceTime=120, BounceXIntensity=40))]
FLIP = attack(600, 22, 14, kb=(-20000, 20000), air_kb=(-15000, 30000), reaction=1, air_reaction=5, stop=10, gain=300, hit_type=HIGH)
FLIP_EX = [attack(450, 40, 16, kb=(-6000, 30000), air_kb=(-6000, 30000), reaction=8, air_reaction=8, stop=8, gain=0, scaling=4, hit_type=HIGH),
           attack(450, 40, 16, kb=(-6000, 30000), air_kb=(-6000, 30000), reaction=8, air_reaction=8, stop=8, gain=0, scaling=4, hit_type=HIGH),
           # Oct 25 night: the last flip spikes them into the floor so hard they bounce back up (juggle after it)
           attack(800, 40, 20, kb=(-20000, -110000), air_kb=(-20000, -110000), reaction=9, air_reaction=9, hitstun_type=KNOCKDOWN,
                  kb_gravity=200000, air_gravity=200000, stop=18, gain=0, scaling=5, hit_type=HIGH,
                  extra=dict(BounceTime=60, BounceXIntensity=0, BounceYIntensity=70))]
TWIRL = attack(250, 20, 12, kb=(-8000, 0), air_kb=(-6000, 15000), reaction=1, air_reaction=5, stop=5, gain=100, hit_type=HIGH)
# Oct 25: Flux Dive's last twirl spikes them down to the floor (her air combo ender)
TWIRL_END = attack(600, 30, 14, kb=(-15000, 0), air_kb=(-18000, -70000), reaction=1, air_reaction=9, air_hitstun_type=KNOCKDOWN,
                   kb_gravity=200000, stop=12, gain=300, hit_type=HIGH)
S1_HIT = attack(160, 30, 20, kb=(-4000, 0), air_kb=(-4000, 8000), reaction=1, air_reaction=5, stop=3, gain=0, scaling=2, pushback=0)
S1_END = attack(1200, 50, 24, kb=(-50000, 50000), air_kb=(-50000, 50000), reaction=7, air_reaction=7, hitstun_type=HARD_KNOCKDOWN,
                kb_gravity=200000, stop=18, gain=0, scaling=0)
# Crimson Waltz: the rush and every orbit shot hold the opponent where they are (no push, almost no gravity)
S2_RUSH = attack(200, 60, 20, kb=(0, 0), air_kb=(0, 0), reaction=1, air_reaction=5, stop=12, gain=0, scaling=0, air_gravity=1)
# Oct 25: the prison's shots keep them in an air hit (reaction 5) with a hard knockdown, so they can't recover while it
# floats them (NetsuHoldOpponentAction lift), however long the combo was
S2_SHOT = attack(100, 45, 20, kb=(0, 0), air_kb=(0, 0), reaction=5, air_reaction=5, stop=3, gain=0, scaling=1, air_gravity=1,
                 hitstun_type=HARD_KNOCKDOWN)
S2_END = attack(1500, 60, 30, kb=(-30000, 70000), air_kb=(-30000, 70000), reaction=8, air_reaction=8, hitstun_type=HARD_KNOCKDOWN,
                kb_gravity=200000, stop=20, gain=0, scaling=0)

# ---------------------------------------------------------------------------------------------
# effect layers placed for one move (added to the manifest's frames)
S = 'Leticia/14_Supers/'
FRAMES = {}
# Crimson Waltz (Oct 25): the flame prison, its hit flash and its explosion, one picture each centred on her origin; every
# key of the orbit moves it (fx_dx / fx_dy, world px) to where the prison is seen from her that frame (cw_path below)
FRAMES['cw_orb'] = {'src': S + 'Super2_VFX_01_Orb.png', 'anchor': 'center', 'scale': 0.9, 'at': [0, 0]}
FRAMES['cw_orbhit'] = {'src': S + 'Super2_VFX_02_OrbHit.png', 'anchor': 'center', 'scale': 0.9, 'at': [0, 0]}
FRAMES['cw_boom'] = {'src': S + 'Super2_VFX_03_Explosion.png', 'anchor': 'center', 'scale': 0.7, 'at': [0, 0]}
for v in 'abc':   # the long Super 1 beam (derive_leticia.py), placed on Super1_02_Beam's canvas
    FRAMES['s1_beam_' + v] = {'src': 'derived/leticia/super1_beam_%s.png' % v, 'anchor': 'like', 'like': 's1_2'}
# Oct 24: the beams run across the whole screen. A short piece of each drawn beam (derive_leticia.py) is stretched
# until it ends BEAM_REACH world px in front of her (build.py fx_reach, SpriteModifier.Scale); the attack boxes go
# just as far (MANUAL boxes below). 4450 px = 12.2 m: past the far edge of the screen at the widest camera.
BEAM_REACH = 4450
for name, like in (('photon_ext', 'cb_2'), ('prism_ext', 'cb_6')):
    FRAMES[name] = {'src': 'derived/leticia/%s.png' % name, 'anchor': 'like', 'like': like}
def beam_fx(f, **more): return dict({'fx': f, 'fx_always': True, 'fx_reach': BEAM_REACH, 'fx_strip': True}, **more)
# Oct 24 late: Ricochet Prism (214B) and the ricochet of Prism Overdrive (214C) bounce across the whole screen too: a
# long picture made from the drawing (derive_leticia.py ricochet_long: the drawn down leg and its mirror image,
# bounce after bounce), placed like cb_4 (which erases its own beam). Their attack boxes (ricochet_boxes, worked out
# in main() from where the drawing sits in the game): the rising first shot, then one box over the whole zigzag.
FRAMES['ricochet_long'] = {'src': 'derived/leticia/ricochet_long.png', 'anchor': 'like', 'like': 'cb_4'}
RICOCHET_BOXES, RICOCHET_BOXES_EX = [], []
# Oct 25: Ricochet Prism's two angles (derive_leticia.py ricochet_paths): B tapped bounces off the floor first, B held goes
# up first (held on frame RICOCHET_HOLD_AT: 214BH). Their boxes follow the zigzag (zigzag_boxes, in main()).
FRAMES['ricochet_down'] = {'src': 'derived/leticia/ricochet_down.png', 'anchor': 'like', 'like': 'cb_4'}
FRAMES['ricochet_up'] = {'src': 'derived/leticia/ricochet_up.png', 'anchor': 'like', 'like': 'cb_4'}
RICOCHET_DOWN_BOXES, RICOCHET_UP_BOXES = [], []
RICOCHET_HOLD_AT = 10
HOLD_BC = INP + '43_Input_HoldB_or_C.tres'
FRAME_PATCH = {'s1_2': {'erase': [[700, 0, 1774, 640], [880, 640, 1774, 887]]},   # its own beam: the layer draws it
               'cb_2': {'erase': [[1600, 0, 1774, 887]]},       # the laser's tip: photon_ext carries it on
               'cb_6': {'erase': [[1440, 0, 1774, 887]]},       # the big beam's arrow tip: prism_ext carries it on
               'cb_4': {'erase': [[800, 0, 1536, 1024]]},       # the ricochet: ricochet_long carries it on
               'fbfx_3': {'at': [0, 80]},                       # Flux Dive: the spin ring around the board
               'fbfx_4': {'at': [-150, 320], 'scale': 1.1}}     # and the corkscrew trailing above and behind her
def fx(f): return {'fx': f, 'fx_always': True}

# ---------------------------------------------------------------------------------------------
# Crimson Waltz (Oct 25): after the rush hits, the prison floats them up to CW_LIFT and she flies around it on her board:
# a smooth path worked out here, one point per frame (NetsuOrbitAction, from the opponent, towards her starting side),
# lift-off, 1 1/4 laps of an ellipse round the prison (up over it first), then down to the floor in front of it.
def hold_opp(x=0, y=0, lift=None):   # keeps the opponent while they're hit (lift: floated in place up to y, per mille a frame)
    return Obj(ACT + 'NetsuHoldOpponentAction.cs', Offset=V2i(x, y), LiftRate=lift)
def orbit(x, y, start=None): return Obj(ACT + 'NetsuOrbitAction.cs', Offset=V2i(int(round(x)), int(round(y))), Start=start)
CW_LIFT, CW_LIFT_RATE, CW_WALL_ROOM = 24000, 110, 26000   # their feet go to 2.4 m; kept 2.6 m from the walls (the orbit fits)
CW_ORB_Y = 8000              # the prison's centre above their feet
CW_RX, CW_RY = 20000, 15000  # her orbit round it
CW_HER_MID = 7000            # her middle above her feet (on the board)
CW_START = (12000, 0)        # where the rush leaves her (snapped there as it hits: during the hit freeze)
CW_LIFTOFF, CW_ORBIT, CW_DESCENT = 10, 60, 12   # frames
CW_LAPS = 1.25
CW_LAND = (24000, -27000)    # below the floor: she lands (her height is clamped to the floor) 2.4 m in front of it
CW_SHOTS = [4] + [CW_LIFTOFF + 4 + 8 * i for i in range(7)]   # the trigger shot, then one every 8 frames round the orbit
CW_BOOM = CW_LIFTOFF + CW_ORBIT + CW_DESCENT + 22              # the prison explodes (her hair flip has started)
def _sm(u): u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)
def cw_path():
    """[(x, y)] per frame 0 .. lift-off + orbit + descent: her feet from the opponent's (x towards her side)"""
    import math
    orb = lambda th: (CW_RX * math.cos(th), CW_ORB_Y + CW_RY * math.sin(th) - CW_HER_MID)
    pts = []
    x1, y1 = orb(0.0)
    for f in range(CW_LIFTOFF):
        u = _sm((f + 1) / CW_LIFTOFF)
        pts.append((CW_START[0] + (x1 - CW_START[0]) * u, CW_START[1] + (y1 - CW_START[1]) * u))
    for f in range(CW_ORBIT):
        u = (f + 1) / CW_ORBIT
        pts.append(orb(2 * math.pi * CW_LAPS * u))
    xe, ye = pts[-1]
    for f in range(CW_DESCENT):
        u = (f + 1) / CW_DESCENT
        pts.append((xe + (CW_LAND[0] - xe) * _sm(u), ye + (CW_LAND[1] - ye) * u * u))   # drops faster and faster
    return pts
def cw_pose(f, x, y):
    """her drawing on frame f: the trigger, then by where she is round the prison"""
    import math
    if f < CW_LIFTOFF: return 's2_2'
    if f >= CW_LIFTOFF + CW_ORBIT: return 'fb_6'
    th = math.degrees(math.atan2(y - (CW_ORB_Y - CW_HER_MID), x)) % 360
    if th < 50 or th >= 320: return 's2_2'   # level with it on her side: firing at it
    if th < 140: return 's2_3'               # above: firing down into it
    if th < 230: return 's2_4'               # behind it
    return 's2_5'                            # under it: firing up
def cw_orb_at(x, y):
    """the prison's centre seen from her (world px: forward = towards it, up), for fx_dx / fx_dy"""
    return round(abs(x) / UPX), round((CW_ORB_Y - y) / UPX)
def cw_keys_boxes():
    pts = cw_path(); keys = []; boxes = [[0, 0, 'none-pass']]; t = 0
    for f, (x, y) in enumerate(pts):
        dx, dy = cw_orb_at(x, y)
        hit = f in CW_SHOTS
        keys.append([cw_pose(f, x, y), f, {'fx': 'cw_orbhit' if hit else 'cw_orb', 'fx_always': True, 'fx_dx': dx, 'fx_dy': dy}])
        if hit:
            boxes += [[f, 1, 'atk_inv-pass', S2_SHOT, None, [[dx - 170, dy - 210, dx + 170, dy + 210]]], [f + 2, 2, 'none-pass']]
    land = len(pts)
    dx, dy = cw_orb_at(CW_LAND[0], -CW_LIFT)       # on the floor, the prison CW_LIFT up in front of her
    keys += [['s2_6', land, {'fx': 'cw_orb', 'fx_always': True, 'fx_dx': dx, 'fx_dy': dy}],
             ['s2_7', land + 6, {'fx': 'cw_orb', 'fx_always': True, 'fx_dx': dx, 'fx_dy': dy}],
             ['s2_8', CW_BOOM - 4, {'fx': 'cw_orb', 'fx_always': True, 'fx_dx': dx, 'fx_dy': dy}],
             ['s2_8', CW_BOOM, {'fx': 'cw_boom', 'fx_always': True, 'fx_dx': dx, 'fx_dy': dy}], ['s2_8', CW_BOOM + 16]]
    boxes += [[CW_BOOM, 1, 'atk_inv-pass', S2_END, None, [[dx - 260, dy - 260, dx + 260, dy + 260]]], [CW_BOOM + 4, 2, 'none-pass'],
              [CW_BOOM + 16, 2, 'pose']]
    return keys, boxes, pts
CW_KEYS, CW_BOXES, CW_PTS = cw_keys_boxes()

# ---------------------------------------------------------------------------------------------
# the moves.  keys: [frame, at, {options}] (see build.py); boxes: [at, stage, kind, props]
#   kind 'pose' = hurtboxes only (fitted), 'pose+prox' = + proximity guard, 'atk' = hurt + proximity + attack (fitted),
#   'atk_inv' = attack only (no hurtboxes: invincible), 'none' = nothing hittable; '-pass' = no pushbox either.
#   'manual' (6th item) = attack box in world px instead of the fitted one.
# input: (motion, [buttons]); a move without 'input' is a state only (reached from another state).
FLUX_DESCENT = [['fb_5', 0, fx('fbfx_3')], ['fb_6', 4, fx('fbfx_4')]]
def flux_keys(flips, start, descent):
    keys = [['fb_1', 0]]; t = 5
    for i in range(flips):
        keys += [['fb_2', t], ['fb_3', t + 4, fx('fbfx_1')], ['fb_4', t + 8, fx('fbfx_2')]]; t += 13
    if descent:
        for j in range(12):
            f, d, o = FLUX_DESCENT[j % 2]; keys.append([f, t + 8 * (j // 2) + d, o])
    return keys, t

KEYS_FA, T_FA = flux_keys(1, 5, True)
KEYS_FB, T_FB = flux_keys(2, 5, True)
KEYS_FC, T_FC = flux_keys(3, 5, False)
KEYS_FC.append(['fb_8', T_FC])

def beam_keys(start, end):
    keys = []; seq = 'abac'
    for i, t in enumerate(range(start, end, 3)): keys.append(['s1_2', t, dict(fx('s1_beam_' + seq[i % 4]), fx_reach=BEAM_REACH)])
    return keys

# cancels: the engine takes the FIRST entry whose input matches. Supers go before the 6X follow-ups (6 + B + C, the end of
# 236BC, also counts as 6X) and the follow-ups before the 66 dash (6, 6X after 236 also reads as 66).
MOVES = {
  'R1A': dict(slot=73, name='Crossfire', input=('236', ['A']), move_file='53_LET_Crossfire_A', hbp='30_Hitbox_Crossfire_A',
      duration=34, keys=[['rk_1', 0], ['rk_2', 8], ['rk_7', 22]],
      boxes=[[0, 0, 'pose+prox'], [8, 1, 'atk', RK1A], [12, 2, 'pose'], [22, 2, 'pose']],
      tick=[(8, movex(-10000)), (12, movex(0))], enter=[change_side(), movex(0)], priority=7,
      cancels=[('S2', HIT, (8, 40)), ('S1', HIT, (8, 40)), ('R2', WHIFF | HIT | BLOCK, (12, 26)), ('DASHC', HIT | BLOCK, (12, 30))]),
  'R1B': dict(slot=74, name='Crossfire', input=('236', ['B', 'C']), move_file='54_LET_Crossfire_B', hbp='31_Hitbox_Crossfire_B',
      duration=38, keys=[['rk_1', 0], ['rk_2', 10], ['rk_7', 24]],
      boxes=[[0, 0, 'pose+prox'], [10, 1, 'atk', RK1B], [14, 2, 'pose'], [24, 2, 'pose']],
      tick=[(10, movex(-12000)), (14, movex(0))], enter=[change_side(), movex(0)], priority=7,
      cancels=[('S2', HIT, (10, 40)), ('S1', HIT, (10, 40)), ('R2', WHIFF | HIT | BLOCK, (14, 28)), ('DASHC', HIT | BLOCK, (14, 32))]),
  'R2': dict(slot=75, name='Crossfire: Pivot', input=('6', ['X']), move_file='55_LET_Crossfire_2', hbp='32_Hitbox_Crossfire_2',
      duration=32, keys=[['rk_3', 0], ['rk_4', 6], ['rk_7', 20]],
      boxes=[[0, 0, 'pose'], [6, 1, 'atk', RK2], [10, 2, 'pose'], [20, 2, 'pose']],
      tick=[(0, movex(14000)), (6, movex(0))], priority=8, skip_check=True,
      cancels=[('S2', HIT, (6, 30)), ('S1', HIT, (6, 30)), ('R3', WHIFF | HIT | BLOCK, (10, 24)), ('DASHC', HIT | BLOCK, (10, 28))]),
  'R3': dict(slot=76, name='Crossfire: Finale', input=('6', ['X']), move_file='56_LET_Crossfire_3', hbp='33_Hitbox_Crossfire_3',
      duration=40, keys=[['rk_5', 0], ['rk_6', 8], ['rk_7', 24]],
      boxes=[[0, 0, 'pose'], [8, 1, 'atk', RK3], [12, 2, 'pose'], [24, 2, 'pose']],
      tick=[(8, movex(-14000)), (13, movex(0))], priority=9, skip_check=True,
      cancels=[('S2', HIT, (8, 34)), ('S1', HIT, (8, 34)), ('DASHC', HIT | BLOCK, (12, 36))]),
  'REX': dict(slot=77, name='Crossfire EX', input=('236', ['C']), move_file='57_LET_Crossfire_EX', hbp='34_Hitbox_Crossfire_EX',
      duration=56, keys=[['rk_1', 0], ['rk_2', 5], ['rk_3', 12], ['rk_4', 15], ['rk_5', 22], ['rk_6', 26], ['rk_7', 42]],
      boxes=[[0, 0, 'none'], [5, 1, 'atk_inv', REX[0]], [9, 2, 'none'], [15, 1, 'atk_inv', REX[1]], [19, 2, 'none'],
             [26, 1, 'atk_inv', REX[2]], [31, 2, 'pose'], [42, 2, 'pose']],
      tick=[(15, reset_hit()), (26, reset_hit()), (31, frame_props(0))],
      enter=[change_side(), movex(0), frame_props(INV_STRIKE | INV_THROW)], exit=[frame_props(0)],
      meter=4000, flash=15, priority=9, afterimages=True, ai=0x10 | 2 | 0x1000),
  '623A': dict(slot=78, name='Rising Comet', input=('623', ['A']), move_file='58_LET_RisingComet_A', hbp='35_Hitbox_RisingComet_A',
      duration=120, keys=[['dp_1', 0], ['dp_2', 4], ['dp_3', 14], ['dp_7', 22]],
      boxes=[[0, 0, 'pose'], [4, 1, 'atk', DPA], [10, 2, 'pose'], [14, 2, 'pose'], [22, 2, 'pose']],
      tick=[(4, movey(95000)), (4, movex(15000))], tick_ranges=[((5, 400), gravity())],
      enter=[change_side(), movex(0)], air_land=True, priority=8),
  '623B': dict(slot=79, name='Rising Comet', input=('623', ['B', 'C']), move_file='59_LET_RisingComet_B', hbp='36_Hitbox_RisingComet_B',
      duration=120, keys=[['dp_1', 0], ['dp_2', 4], ['dp_3', 12], ['dp_4', 15], ['dp_7', 26]],
      boxes=[[0, 0, 'none'], [4, 1, 'atk_inv', DPB[0]], [9, 2, 'pose'], [15, 1, 'atk', DPB[1]], [20, 2, 'pose'], [26, 2, 'pose']],
      tick=[(4, movey(105000)), (4, movex(14000)), (15, reset_hit()), (7, frame_props(0))], tick_ranges=[((5, 400), gravity())],
      enter=[change_side(), movex(0), frame_props(INV_STRIKE | INV_THROW)], exit=[frame_props(0)], air_land=True, priority=8,
      ai=0x10 | 2 | 0x1000),
  '623C': dict(slot=80, name='Comet Burst', input=('623', ['C']), move_file='60_LET_CometBurst', hbp='37_Hitbox_CometBurst',
      duration=120, keys=[['dp_1', 0], ['dp_2', 4], ['dp_3', 10], ['dp_4', 13], ['dp_5', 20], ['dp_6', 24], ['dp_7', 32]],
      boxes=[[0, 0, 'none'], [4, 1, 'atk_inv', DPC[0]], [9, 2, 'none'], [13, 1, 'atk_inv', DPC[1]], [18, 2, 'none'],
             [24, 1, 'atk_inv', DPC[2], None, [[150, -150, 420, 260]]], [29, 2, 'pose'], [32, 2, 'pose']],
      tick=[(4, movey(150000)), (4, movex(12000)), (13, reset_hit()), (20, movey(0)), (24, reset_hit()), (24, movey(25000)),
            (29, frame_props(0))],
      transitions=[ev([at_range(14, 21), check_hit(HIT)], [play_state(108)])],
      tick_ranges=[((5, 19), gravity()), ((20, 23), gravity(30000)), ((25, 400), gravity())],
      enter=[change_side(), movex(0), frame_props(INV_STRIKE | INV_THROW)], exit=[frame_props(0)], air_land=True,
      meter=4000, flash=15, priority=9, ai=0x10 | 2 | 0x1000),
  '214A': dict(slot=81, name='Photon Line', input=('214', ['A']), move_file='61_LET_PhotonLine', hbp='38_Hitbox_PhotonLine',
      duration=40, keys=[['rk_1', 0], ['cb_2', 12, beam_fx('photon_ext')], ['cb_8', 26]],
      boxes=[[0, 0, 'pose+prox'], [12, 1, 'atk', BEAM_A, None, [[51, 360, BEAM_REACH, 418]]], [16, 2, 'pose'], [26, 2, 'pose']],
      enter=[change_side(), movex(0)], priority=7, cancels=[('S2', HIT, (12, 36)), ('S1', HIT, (12, 36)), ('DASHC', HIT | BLOCK, (16, 36))]),
  '214B': dict(slot=82, name='Ricochet Prism', input=('214', ['B', 'C']), move_file='62_LET_RicochetPrism', hbp='39_Hitbox_RicochetPrism',
      # Oct 25: tapped, the shot bounces off the floor first; B still held on frame 10 = 214BH (it goes up first)
      duration=46, keys=[['cb_3', 0], ['cb_4', 14, fx('ricochet_down')], ['cb_8', 30]],
      boxes=[[0, 0, 'pose+prox'], [14, 1, 'atk', BEAM_B, None, RICOCHET_DOWN_BOXES], [19, 2, 'pose'], [30, 2, 'pose']],
      transitions=[ev([at(RICOCHET_HOLD_AT), check_input(HOLD_BC)], [play_state(106), goto_frame(RICOCHET_HOLD_AT)])],
      enter=[change_side(), movex(0)], priority=7, cancels=[('S2', HIT, (14, 40)), ('S1', HIT, (14, 40)), ('DASHC', HIT | BLOCK, (19, 40))]),
  '214BH': dict(slot=106, name='Ricochet Prism (held)', hbp='49_Hitbox_RicochetPrism_Held',
      # Oct 25: the same move from frame 10 on (214B's cancels still apply: same frames), the shot going up first
      duration=46, keys=[['cb_3', 0], ['cb_4', 14, fx('ricochet_up')], ['cb_8', 30]],
      boxes=[[0, 0, 'pose+prox'], [14, 1, 'atk', BEAM_B, None, RICOCHET_UP_BOXES], [19, 2, 'pose'], [30, 2, 'pose']]),
  '214C': dict(slot=83, name='Prism Overdrive', input=('214', ['C']), move_file='63_LET_PrismOverdrive', hbp='40_Hitbox_PrismOverdrive',
      duration=70, keys=[['rk_1', 0], ['cb_2', 5, beam_fx('photon_ext')], ['cb_3', 12], ['cb_4', 16, fx('ricochet_long')], ['cb_5', 26],
                         ['cb_6', 34, beam_fx('prism_ext')], ['cb_6', 38, beam_fx('prism_ext', dx=-3, fx_dx=-3)], ['cb_7', 46], ['cb_8', 56]],
      boxes=[[0, 0, 'none'], [5, 1, 'atk_inv', BEAM_C[0], None, [[51, 360, BEAM_REACH, 418]]], [9, 2, 'none'],
             [16, 1, 'atk_inv', BEAM_C[1], None, RICOCHET_BOXES_EX], [20, 2, 'none'],
             [34, 1, 'atk_inv', BEAM_C[2], None, [[2, 262, BEAM_REACH, 465]]], [38, 1, 'atk_inv', BEAM_C[3], None, [[0, 262, BEAM_REACH, 465]]],
             [42, 2, 'pose'], [56, 2, 'pose']],
      tick=[(16, reset_hit()), (34, reset_hit()), (38, reset_hit()), (34, camera_shake(0.03, 10)), (42, frame_props(0)),
            (46, movex(-20000)), (52, movex(0))],
      enter=[change_side(), movex(0), frame_props(INV_STRIKE | INV_THROW)], exit=[frame_props(0)],
      meter=4000, flash=15, priority=9, ai=0x10 | 2 | 0x1000),
  'FA': dict(slot=84, name='Flux Dive', input=('236', ['A']), move_file='64_LET_FluxDive_A', hbp='41_Hitbox_FluxDive_A',
      duration=120, keys=KEYS_FA,
      # Oct 25: one twirl hit as the descent starts, and it spikes them down (was six small ones: she often landed before
      # the last, so it never ended a combo)
      boxes=[[0, 0, 'pose'], [9, 1, 'atk', FLIP], [17, 2, 'pose'], [T_FA, 1, 'atk', TWIRL_END], [T_FA + 6, 2, 'pose']],
      tick=[(0, movey(30000)), (0, movex(10000)), (T_FA, movex(50000)), (T_FA, movey(-70000)), (T_FA, reset_hit())],
      tick_ranges=[((1, T_FA - 1), gravity(120000))], flux_land=True, air=True, ground=False, priority=7, ai=0x10 | 4),
  'FB': dict(slot=85, name='Flux Dive', input=('236', ['B', 'C']), move_file='65_LET_FluxDive_B', hbp='42_Hitbox_FluxDive_B',
      duration=130, keys=KEYS_FB,
      boxes=[[0, 0, 'pose'], [9, 1, 'atk', FLIP], [17, 2, 'pose'], [22, 1, 'atk', FLIP], [30, 2, 'pose'],
             [T_FB, 1, 'atk', TWIRL_END], [T_FB + 6, 2, 'pose']],
      tick=[(0, movey(35000)), (0, movex(10000)), (22, reset_hit()), (T_FB, movex(55000)), (T_FB, movey(-75000)), (T_FB, reset_hit())],
      tick_ranges=[((1, T_FB - 1), gravity(100000))], flux_land=True, air=True, ground=False, priority=7, ai=0x10 | 4),
  'FC': dict(slot=92, name='Flux Storm', input=('236', ['C']), move_file='66_LET_FluxStorm', hbp='43_Hitbox_FluxStorm',
      duration=T_FC + 14, keys=KEYS_FC,
      boxes=[[0, 0, 'none'], [9, 1, 'atk_inv', FLIP_EX[0]], [17, 2, 'none'], [22, 1, 'atk_inv', FLIP_EX[1]], [30, 2, 'none'],
             [35, 1, 'atk_inv', FLIP_EX[2]], [43, 2, 'pose']],
      tick=[(0, movey(40000)), (0, movex(8000)), (22, reset_hit()), (35, reset_hit()), (43, frame_props(0))],
      tick_ranges=[((1, 400), gravity(90000))], enter=[frame_props(INV_STRIKE | INV_THROW)], exit=[frame_props(0)],
      air_land_normal=True, air=True, ground=False, meter=4000, flash=15, priority=9, ai=0x10 | 4 | 0x1000),
  'FLAND': dict(slot=93, name='Flux Dive (landing)', hbp='44_Hitbox_FluxLanding', duration=18,
      keys=[['fb_7', 0], ['fb_9', 8]], boxes=[[0, 0, 'pose'], [8, 0, 'pose']], enter=[movex(0), movey(0)], ai=0x10 | 2),
  'S1': dict(slot=94, name='Stardrive Cannon', input=('236', ['BC']), move_file='67_LET_StardriveCannon', hbp='45_Hitbox_StardriveCannon',
      duration=100, keys=[['s1_1', 0]] + beam_keys(22, 72) + [['s1_3', 74]],
      boxes=[[0, 0, 'none'], [22, 1, 'atk_inv', S1_HIT, None, [[258, 198, BEAM_REACH, 464]]],
             [67, 1, 'atk_inv', S1_END, None, [[258, 198, BEAM_REACH, 464]]], [72, 2, 'none'], [74, 2, 'pose']],
      tick=[(t, reset_hit()) for t in range(27, 63, 5)] + [(22, camera_shake(0.04, 46)), (22, movex(-10000)), (40, movex(0)),
            (74, frame_props(0))],
      enter=[change_side(), movex(0), frame_props(INV_STRIKE | INV_THROW | INV_PROJ)], exit=[frame_props(0)],
      meter=6000, flash=20, priority=10, ai=0x10 | 2 | 0x1000),
  'S2': dict(slot=95, name='Crimson Waltz', input=('214', ['BC']), move_file='68_LET_CrimsonWaltz', hbp='46_Hitbox_CrimsonWaltz_Rush',
      duration=52, keys=[['fb_1', 0], ['s2_1', 8], ['s2_6', 38]],
      boxes=[[0, 0, 'none'], [8, 1, 'atk_inv', S2_RUSH], [38, 2, 'pose']],
      tick=[(8, movex(220000)), (38, movex(0)), (38, frame_props(0))],
      enter=[change_side(), movex(0), frame_props(INV_STRIKE | INV_THROW | INV_PROJ)], exit=[frame_props(0)],
      hit_confirm=[ev([check_hit(HIT)], [play_state(97)])], meter=6000, flash=20, priority=10, ai=0x10 | 2 | 0x1000),
  'S2_hit': dict(slot=97, name='Crimson Waltz (flame prison)', hbp='50_Hitbox_CrimsonWaltz_Flight', duration=CW_BOOM + 24,
      # Oct 25: the prison floats them up (lift, kept off the walls so the orbit fits) and she flies round it on her board,
      # one point of cw_path() per frame (was: five jumps from point to point); the stage shows (NetsuShowStage) and the
      # camera frames the whole flight
      keys=CW_KEYS, boxes=CW_BOXES,
      # every frame: first the lift (until the explosion, which then throws them), then her point (from where they are now)
      pre_ranges=[((0, CW_BOOM - 1), hold_opp(CW_WALL_ROOM, CW_LIFT, lift=CW_LIFT_RATE))],
      tick=[(f, orbit(x, y)) for f, (x, y) in enumerate(CW_PTS)] + [(f, reset_hit()) for f in CW_SHOTS + [CW_BOOM]] +
           [(f, camera_shake(0.02, 6)) for f in CW_SHOTS] + [(CW_BOOM, camera_shake(0.06, 20)), (CW_BOOM + 16, frame_props(0))],
      enter=[frame_props(INV_STRIKE | INV_THROW | INV_PROJ), movex(0), movey(0), orbit(*CW_START, start=True)],
      exit=[frame_props(0)], priority=10, afterimages=True, ai=0x10 | 2 | 0x1000, show_stage=True),
  'DPLAND': dict(slot=98, name='Rising Comet (landing)', hbp='48_Hitbox_RisingCometLanding', duration=14,
      keys=[['dp_8', 0]], boxes=[[0, 0, 'pose']], enter=[movex(0), movey(0)], ai=0x10 | 2),
}
FLUX_LAND, DP_LAND = MOVES['FLAND']['slot'], MOVES['DPLAND']['slot']

# Oct 24: the speeds above were tuned on previews (movereel.py) that moved her at half the game's
# speed: the engine moves position += speed / 60 every frame, the old preview did speed / 120.
# Halving every speed AND gravity here keeps each move exactly as the previews showed it
# (same arcs, same timing). New moves: write the speeds you want, then set them with SPEED_FIX 1.
SPEED_FIX = 0.5
def _fix_speeds(moves, k):
    seen = set()
    for m in moves.values():
        acts = list(m.get('enter', [])) + list(m.get('exit', [])) + [a for _, a in m.get('tick', [])] + [a for _, a in m.get('tick_ranges', [])]
        for a in acts:
            if id(a) in seen or not hasattr(a, 'script'): continue
            seen.add(id(a)); kind = os.path.basename(a.script)
            if kind in ('MoveXAction.cs', 'MoveYAction.cs') and a.fields.get('Velocity'):
                a.fields['Velocity'] = int(round(a.fields['Velocity'] * k))
            elif kind == 'AddGravityAction.cs':
                a.fields['Force'] = int(round((a.fields.get('Force') or 260000) * k)); a.fields['UseDefault'] = None; a.fields['SetValue'] = True
_fix_speeds(MOVES, SPEED_FIX)
# Oct 25 night: Comet Burst's board slam (speeds here are real engine speeds: added after the fix above)
CB_SLAM_HIT = attack(300, 60, 20, kb=(0, 0), air_kb=(0, 0), reaction=5, air_reaction=5, hitstun_type=HARD_KNOCKDOWN, stop=8,
                     gain=0, scaling=2, air_gravity=1)
CB_SLAM_END = attack(1000, 50, 20, kb=(-12000, 42000), air_kb=(-12000, 42000), reaction=8, air_reaction=8,
                     hitstun_type=HARD_KNOCKDOWN, kb_gravity=200000, air_gravity=200000, stop=18, gain=0, scaling=5)
MOVES['CB_SLAM'] = dict(slot=108, name='Comet Burst (board slam)', hbp='50_Hitbox_CometBurst_Slam', duration=90,
    keys=[['fb_2', 0, fx('fbfx_2')], ['fb_3', 5, fx('fbfx_2')], ['fb_4', 10, fx('fbfx_1')], ['fb_4', 16]],
    boxes=[[0, 0, 'none'], [10, 1, 'atk_inv', CB_SLAM_HIT, None, [[-100, -300, 420, 250]]], [13, 2, 'none']],
    tick=[(0, movex(0)), (0, movey(36000)), (10, movey(-210000)), (10, movex(16000)), (10, camera_shake(0.02, 6))],
    tick_ranges=[((1, 9), gravity(70000)), ((0, 9), hold_opp(6500, -3000)), ((10, 999), hold_opp(6500, -6000))],
    enter=[frame_props(INV_STRIKE | INV_THROW | INV_PROJ)], exit=[frame_props(0)], land_to=109, priority=9, ai=0x10 | 2 | 0x1000)
MOVES['CB_LAND'] = dict(slot=109, name='Comet Burst (impact)', hbp='51_Hitbox_CometBurst_Impact', duration=34,
    keys=[['fb_7', 0], ['fb_9', 14], ['dp_8', 24]],
    boxes=[[0, 1, 'atk_inv', CB_SLAM_END, None, [[-120, 0, 480, 320]]], [4, 2, 'pose']],
    tick=[(0, camera_shake(0.07, 16)), (4, frame_props(0))],
    enter=[movex(0), movey(0), frame_props(INV_STRIKE | INV_THROW)], exit=[frame_props(0)], priority=9, ai=0x10 | 2)
# which normals cancel into what (first match wins: supers -> EX -> 214 -> 623 -> 236)
GROUND_CANCEL_ORDER = ['S2', 'S1', '214C', '214B', '214A', '623C', '623B', '623A', 'REX', 'R1B', 'R1A']
AIR_CANCEL_ORDER = ['FC', 'FB', 'FA']
GROUND_NORMALS = ['23_LET_5A', '24_LET_5B', '25_LET_5C', '26_LET_2A', '27_LET_2B', '28_LET_2C', '32_LET_4A', '33_LET_6C']
AIR_NORMALS = ['29_LET_j_5A', '30_LET_j_5B', '31_LET_j_5C']
# stance order (the neutral lookup runs from the END of the list, so later = checked first)
STANCE_ORDER = ['R1A', 'R1B', 'R2', 'R3', 'REX', '623A', '623B', '623C', '214A', '214B', '214C', 'FA', 'FB', 'FC', 'S1', 'S2']
INPUTS = {('236', 'A'): '44_Input_236A', ('236', 'B|C'): '45_Input_236B_or_C', ('236', 'C'): '20_Input_236C',
          ('623', 'A'): '46_Input_623A', ('623', 'B|C'): '47_Input_623B_or_C', ('623', 'C'): '24_Input_623C',
          ('214', 'A'): '40_Input_214A', ('214', 'B|C'): '41_Input_214B_or_C', ('214', 'C'): '21_Input_214C',
          ('236', 'BC'): '25_Input_236BC', ('214', 'BC'): '48_Input_214BC', ('6', 'X'): '27_Input_6X'}
MANUAL_BOXES = {}


def ricochet_boxes(port, close=False):
    """Ricochet Prism's attack boxes, in world px from her feet (y up): the first shot (from the gun up to the first
    bounce), then ONE box over the whole zigzag: from the first bounce to BEAM_REACH, from the low bounces to the high
    ones (+ the line's half thickness). The bounce points are the drawing's (derive_leticia.RICOCHET), placed where
    cb_4 sits in the game. A fighter's body uses only its first 16 boxes (PhysicsBody.HitboxesLimit, hurt and
    proximity boxes included): the first version (two boxes per leg, 56 in all) never hit past ~1100 px.
    close=True (Prism Overdrive): also the space between her and the gun, so the ricochet hits an opponent right next
    to her too (the EX's hits combo at any distance; the B version's shot goes over their head there)."""
    import derive_leticia as dl
    c = dl.RICOCHET
    crop, off, info = port.frame('cb_4')
    k, (Ax, Ay), (Wx, Wy) = info['k'], info['A'], info['W']
    world = lambda x, y: (Wx + x * k - Ax, Wy - (y * k - Ay))
    t = 24                                            # half the line's thickness + a little, world px
    (sx, sy), (ax, ay), (lx, ly) = world(c['start'], c.get('start_y', 168)), world(*c['apex']), world(*c['low'])
    boxes = [[round(sx), round(min(sy, ay) - t), round(ax), round(max(sy, ay) + t)],     # gun -> first bounce
             [round(ax), round(ly - t), BEAM_REACH, round(ay + t)]]                     # the zigzag
    if close:
        boxes.insert(0, [0, round(ly - t), round(sx), round(ay + t)])
    return boxes


def zigzag_boxes(port, kind):
    """Oct 25: Ricochet Prism's attack boxes for one of its two angles (derive_leticia.zigzag_verts), in world px from her
    feet (y up): two per leg of the zigzag (its two halves), up to BEAM_REACH. ~22 boxes: her body takes up to 32
    (PhysicsBody.HitboxesLimit in her fighter scenes, raised for this)."""
    import derive_leticia as dl
    crop, off, info = port.frame('cb_4')
    k, (Ax, Ay), (Wx, Wy) = info['k'], info['A'], info['W']
    world = lambda x, y: (Wx + x * k - Ax, Wy - (y * k - Ay))
    t = 24
    pts = [world(x, y) for x, y in dl.zigzag_verts(kind)]
    boxes = []
    for (xa, ya), (xb, yb) in zip(pts[:-1], pts[1:]):
        xm, ym = (xa + xb) / 2, (ya + yb) / 2
        for (x0, y0), (x1, y1) in (((xa, ya), (xm, ym)), ((xm, ym), (xb, yb))):
            if x0 >= BEAM_REACH: return boxes
            boxes.append([round(x0), round(min(y0, y1) - t), round(min(x1, BEAM_REACH)), round(max(y0, y1) + t)])
    return boxes


# moves that reuse a state she already has. Shot dash: her shots cancel into her forward dash on hit or block
# ("she zones to get in"); it only works as a cancel (SkipCheck), never from neutral.
EXTRA_MOVES = {
  'DASHC': dict(name='Dash (shot cancel)', state=16, input_res=INP + '9_Input_66.tres', move_file='69_LET_ShotDash', priority=6,
                move_end=1, extra={'SkipCheck': True, 'MoveEndState': 17}),
}

# ---------------------------------------------------------------------------------------------
def input_res(motion, buttons):
    res = INP + INPUTS[(motion, '|'.join(buttons))] + '.tres'
    if not os.path.exists(res_file(res)): raise SystemExit('missing input ' + res)
    return res

def hitbox_files(mk, m):
    """skeleton hitbox files (boxes get fitted by hitfit.py afterwards)"""
    names = []
    for i, b in enumerate(m['boxes']):
        at, stage, kind = b[0], b[1], b[2]; props = b[3] if len(b) > 3 else None
        manual = b[5] if len(b) > 5 else None
        name = '%s_%d' % (m['hbp'], i); res = hb(name); names.append((at, stage, name, kind))
        if manual is not None: MANUAL_BOXES[name] = manual   # (RICOCHET_BOXES are filled in main())
        if os.path.exists(res_file(res)) and not FORCE:     # made before: only the table's attack values go in
            if props and kind.split('-')[0] in ('atk', 'atk_inv') and not DRY: patch_attacks(res, props)
            continue
        els = []; base = kind.split('-')[0]; pushbox = None if kind.endswith('-pass') else PUSHBOX_STD
        if base in ('pose', 'pose+prox', 'atk'): els += standard_hurt(3)
        if base in ('pose+prox', 'atk'):
            els.append(box(PROX, 0, 0, 400, 450, HitType=MID))
        if base in ('atk', 'atk_inv'):
            els.append(box(HIT_T, 40, 100, 300, 360, **props))
        if not DRY: write(res, Hitboxes(els, pushbox), force=FORCE)
    return names

def strip_old_cancels(move_res):
    """drop cancels into the stance's special-move slots (they pointed at the moves this fighter was copied from)"""
    def fn(t):
        refs = list_refs(t, 'CanCancelTo'); keep = []
        for r in refs:
            sid = re.search(r'"([^"]+)"', r).group(1); s = t.sub_get(sid)
            m = re.search(r'MoveIndex = (\d+)', '\n'.join(s[2])) if s else None
            if m and int(m.group(1)) >= FIRST_SPECIAL: continue
            keep.append(r)
        t.res_set('CanCancelTo', '[' + ', '.join(keep) + ']'); t.prune()
    return edit_tres(move_res, fn, BK, 'old cancels removed')

def set_stance_specials(stance_res, move_res_list):
    """the stance's moves: 0..FIRST_SPECIAL-1 stay, then exactly these (in this order); returns their indices"""
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
    return {mr: FIRST_SPECIAL + n for n, mr in enumerate(move_res_list)}

def set_state_slots(data_res, slots):
    """slots: {index: state_res}; extends the list with idle if needed; drops references nothing uses any more"""
    def fn(t):
        refs = list_refs(t, 'States'); idle = refs[0]
        for slot in sorted(slots):
            sr = slots[slot]
            i = t.add_ext('Resource', sr, res_uid(sr), prefer_id='st_' + re.sub(r'\W', '_', os.path.basename(sr)[:-5]))
            while len(refs) <= slot: refs.append(idle)
            refs[slot] = 'ExtResource("%s")' % i
        t.res_set('States', '[' + ', '.join(refs) + ']'); t.prune()
    return edit_tres(data_res, fn, BK, 'state slots')

TWO_B_CHAINS = [24, 25, 28, 4, 5, 6]   # 2B -> 5B, 5C, 2C and the jump cancels (stance move indices)

def patch_normals():
    """her normals came from Cecilia's: the shots stand still (no lunges/slides), 2C fires twice"""
    # Oct 24: 2B chains into 5B, 5C, 2C and the jump cancels, like Cecilia's 2B (it could only go into specials)
    add_cancels(A + 'Moves/27_LET_2B.tres', [(i, HIT | BLOCK, (0, 999)) for i in TWO_B_CHAINS], BK, before_all=False)
    def no_lunge(state, ids_to_zero):
        def fn(t):
            for s in t.sub:
                if t.script_of(s[2]).endswith('MoveXAction.cs'):
                    v = re.search(r'Velocity = (-?\d+)', '\n'.join(s[2]))
                    if v and int(v.group(1)) in ids_to_zero: s[2] = [l for l in s[2] if not l.startswith('Velocity = ')]
        edit_tres(A + 'States/%s.tres' % state, fn, BK, 'no lunge')
    no_lunge('65_LET_5C', {50000}); no_lunge('67_LET_2B', {40000}); no_lunge('68_LET_2C', {60000})
    def second_shot(t):
        if any('fdk_reset14' == s[0] for s in t.sub): return
        fde = t.ext_id_for_path(FDE + 'FrameDataEvent.cs') or t.add_ext('Script', FDE + 'FrameDataEvent.cs', script_uid(FDE + 'FrameDataEvent.cs'), prefer_id='fde')
        atc = t.add_ext('Script', CON + 'AtFrameCondition.cs', script_uid(CON + 'AtFrameCondition.cs'), prefer_id='atc')
        rha = t.add_ext('Script', ACT + 'ResetHitAction.cs', script_uid(ACT + 'ResetHitAction.cs'), prefer_id='rha')
        t.sub.append(['fdk_at14', 'Resource', ['script = ExtResource("%s")' % atc, 'Frame = 14']])
        t.sub.append(['fdk_rst14', 'Resource', ['script = ExtResource("%s")' % rha]])
        t.sub.append(['fdk_reset14', 'Resource', ['script = ExtResource("%s")' % fde, 'Conditions = [SubResource("fdk_at14")]',
                                                  'Actions = [SubResource("fdk_rst14")]']])
        refs = list_refs(t, 'OnTickEvents') + ['SubResource("fdk_reset14")']
        t.res_set('OnTickEvents', '[' + ', '.join(refs) + ']')
    edit_tres(A + 'States/68_LET_2C.tres', second_shot, BK, '2C second shot')

def write_states():
    for mk, m in MOVES.items():
        m['anim'] = '%d_%s_%s' % (m['slot'], TAG, mk)
        sres = A + 'States/%d_%s_%s.tres' % (m['slot'], TAG, mk); m['state_res'] = sres
        tick = [ev([at_range(a, b)], [act]) for (a, b), act in m.get('pre_ranges', [])]   # Oct 25: ranges that go first
        tick += [ev([at(fr)], [act]) for fr, act in m.get('tick', [])]
        tick += [ev([at_range(a, b)], [act]) for (a, b), act in m.get('tick_ranges', [])]
        trans = list(m.get('transitions', []))
        if m.get('air_land'):          # rising kicks: land into their own landing pose
            trans += [ev([at_range(10, 999), on_ground()], [play_state(DP_LAND)]), ev([state_ended()], [play_state(FALLING)])]
        elif m.get('flux_land'):       # board dive: land on the board, step off
            trans += [ev([at_range(3, 999), on_ground()], [play_state(FLUX_LAND)]), ev([state_ended()], [play_state(FALLING)])]
        elif m.get('land_to'):         # Oct 25 night: a dive that lands into its own impact state
            trans += [ev([at_range(2, 999), on_ground()], [play_state(m['land_to'])]), ev([state_ended()], [play_state(FALLING)])]
        elif m.get('air_land_normal'):
            trans += [ev([at_range(3, 999), on_ground()], [play_state(LANDING)]), ev([state_ended()], [play_state(FALLING)])]
        else:
            trans += [ev([state_ended()], [play_state(IDLE)])]
        st = State(m['name'], COMBAT, an(m['anim']), transitions=trans, enter=m.get('enter', ()), tick=tick, exit=m.get('exit', ()),
                   hit_confirm=m.get('hit_confirm', ()), ai=m.get('ai', 0x10 | (4 if m.get('air') else 2)), show_stage=m.get('show_stage'))
        write(sres, st, force=FORCE)

def main():
    if STATES_ONLY:
        write_states(); print('\n'.join(fdk.LOG)); return
    man_path = os.path.join(HERE, 'manifests', CH + '.json')
    man = json.load(open(man_path, encoding='utf-8'))
    man['frames'].update(FRAMES)
    for fid, patch in FRAME_PATCH.items(): man['frames'][fid].update(patch)
    hf = man.setdefault('hitfit', {}); hf.setdefault('boxes', {}); hf.setdefault('attack_part', {})
    hf['attack_part'].setdefault('95_LET_S2', 'edge')        # the board rush hits with her front, not the board's glow
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
        if not os.path.exists(res_file(ares)) or FORCE:
            if not DRY: write(ares, AnimData(m['duration'], [(a0, stage, hb(name)) for a0, stage, name, kind in names],
                                             afterimages=True if m.get('afterimages') else None), force=FORCE)
    for name, bx in MANUAL_BOXES.items(): hf['boxes'][name] = {'attack': bx}
    if DRY:
        for mk, m in MOVES.items(): print(mk, m['anim'], [n[2] for n in m['hb_names']])
        return
    json.dump(man, open(man_path, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    # sprites + timelines
    import build
    p = build.Port(CH)
    # the ricochet's boxes, wherever the drawing sits in the game (written for hitfit below)
    RICOCHET_BOXES[:] = ricochet_boxes(p)
    RICOCHET_BOXES_EX[:] = ricochet_boxes(p, close=True)
    RICOCHET_DOWN_BOXES[:] = zigzag_boxes(p, 'down')
    RICOCHET_UP_BOXES[:] = zigzag_boxes(p, 'up')
    for name, bx in (('39_Hitbox_RicochetPrism_1', RICOCHET_DOWN_BOXES), ('49_Hitbox_RicochetPrism_Held_1', RICOCHET_UP_BOXES)):
        hf['boxes'][name] = {'attack': bx}
    print('ricochet (Oct 25): tapped %d boxes, held %d' % (len(RICOCHET_DOWN_BOXES), len(RICOCHET_UP_BOXES)))
    json.dump(man, open(man_path, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print('ricochet boxes: B %s, EX %s' % (RICOCHET_BOXES, RICOCHET_BOXES_EX))
    # --only=214A,214B: only those moves' sprites and boxes (states, moves and cancels are left as they are)
    only = next((a.split('=', 1)[1].split(',') for a in sys.argv if a.startswith('--only=')), None)
    if only:
        anims = [a for a in anims if any(a.endswith('_' + k) for k in only)]
    for a in anims:
        p.build_anim(a); print('built', a)
    # boxes fitted to the drawings
    import hitfit
    f = hitfit.Fitter(CH)
    for line in f.run(anims, write=True, force=FORCE): print('  ', line)
    if only:
        print('\n'.join(fdk.LOG)); return
    # states
    write_states()
    # moves (inputs are the shared ones)
    for mk, m in MOVES.items():
        if 'input' not in m: continue
        mres = A + 'Moves/%s.tres' % m['move_file']; m['move_res'] = mres
    order = [MOVES[k]['move_res'] for k in STANCE_ORDER]
    idx = {k: FIRST_SPECIAL + n for n, k in enumerate(STANCE_ORDER)}
    for n, (k, e) in enumerate(EXTRA_MOVES.items()):
        idx[k] = FIRST_SPECIAL + len(STANCE_ORDER) + n
        e['move_res'] = A + 'Moves/%s.tres' % e['move_file']; order.append(e['move_res'])
        write(e['move_res'], Move(e['name'], e['state'], e['input_res'], priority=e['priority'], move_end=e['move_end'],
                                  extra=e['extra']), force=FORCE)
    for mk, m in MOVES.items():
        if 'input' not in m: continue
        cancels = [cancel(idx[k], c, fr) for k, c, fr in m.get('cancels', [])]
        mv = Move(m['name'], m['slot'], input_res(*m['input']), priority=m.get('priority', 7), meter=m.get('meter'), flash=m.get('flash'),
                  ground=m.get('ground', True), air=m.get('air', False), cancels=cancels,
                  extra={'SkipCheck': True} if m.get('skip_check') else None)
        write(m['move_res'], mv, force=FORCE)
    # register: state slots, stance moves, cancels from the normals
    set_state_slots(A + '0_%s_Data.tres' % TAG, {m['slot']: m['state_res'] for m in MOVES.values()})
    set_stance_specials(A + 'Stances/%s_Stance_Main.tres' % TAG, order)
    for n in GROUND_NORMALS + AIR_NORMALS: strip_old_cancels(A + 'Moves/%s.tres' % n)
    for n in GROUND_NORMALS:
        add_cancels(A + 'Moves/%s.tres' % n, [(idx[k], HIT | BLOCK, (0, 999)) for k in GROUND_CANCEL_ORDER], BK)
    for n in AIR_NORMALS:
        add_cancels(A + 'Moves/%s.tres' % n, [(idx[k], HIT | BLOCK, (0, 999)) for k in AIR_CANCEL_ORDER], BK)
    import launchers; launchers.normals_to_6c(CH, BK)   # Oct 26: every ground normal can cancel into 6C
    patch_normals()
    print('\n'.join(fdk.LOG))
    print('move indices:', idx)

if __name__ == '__main__':
    main()
