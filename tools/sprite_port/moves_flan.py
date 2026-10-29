"""FLAN'S MOVES (Oct 24): her specials and supers, built from the drawings in
Fighting_Game_All_Sprites/Flan_All_Sprites (see its COMMAND_LIST.md: the pack's own move list).

  236A        Star Fist             short low lunging punch
  236B        Twirling Star Fist    comical arm twirl (absorbs one hit), then the same punch with radiant light
  236C        Supernova Fist        (2 bars) twirl during the flash, invincible punch with big light; crumples them
  623A / 623B Rising Star           low uppercut, held overhead while she rises, radiant burst at the peak
                                    (B: higher, stronger, invincible start); press A/B/C at the peak for Falling Star
  (follow-up) Falling Star          diagonal beam down-forward that slams them to the floor (623A/B only)
  623C        Spiral Star           (2 bars) invincible: holds the first hit, then a fast spinning rise, burst at the top
  214A / 214B Meteor Drop           rising knee, then a falling punch (overhead) into a radiant ground impact (B: higher)
  214C        Meteor Impact         (2 bars) A's path, invincible start, bigger energy, the impact crumples them
  j.236A / B  Falling Star (air)    (Oct 25) the same beam from any jump: brings them down (air combo ender)
  236BC       Radiant Breaker       (3 bars) windmill windup, dash punch; on hit: braced radiant burst, recoil, roll
  214BC       Big Bang Crash        (3 bars) Oct 25: she twirls through the 1.5 s super pause (charging the punch),
                                    then the rising diagonal punch; on hit she rockets ~12 m up into the sky with
                                    them on her fist, leaps over them at the top, slams them and drags them back
                                    down to the floor, where the fist's impact sets off the six-stage explosion
Names are placeholders: rename them in the Move files (MoveName, shown in the cut-in) and command_list.json.

    python moves_flan.py          writes everything (Godot closed, or reload the project after)
    python moves_flan.py --dry    only prints what it would do
    python moves_flan.py --states only rewrites the state files (movement, timing, cancels into states)
    python moves_flan.py --anims=94_FLN_S2,95_FLN_S2_hit   only rebuilds those animations' sprites / boxes

Edit the tables below and run again: frame timings, damage, movement. Files you change in Godot
afterwards are kept (the script says SKIPPED); add --force to overwrite them with the table values.
Pipeline per move: manifest keys -> build.py (sprites + timeline) -> hitbox files -> hitfit.py
(boxes fitted to the drawings) -> state, input, move files -> registered in 0_FLN_Data / the stance.
Speeds are real engine speeds (units per second, 10000 = 1 m; position += speed / 60 every frame):
preview them with  python movereel.py flan out.gif 76_FLN_623A 80_FLN_DPLAND
"""
import sys, os, json, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import fdk
from fdk import *
from tres import Tres

CH, TAG = 'flan', 'FLN'
A = 'res://actors/flan/'
BK = '_backup_stage_select/pre_flan_moves'
FORCE = '--force' in sys.argv
DRY = '--dry' in sys.argv
STATES_ONLY = '--states' in sys.argv
def _arg(name, default=None):
    for a in sys.argv:
        if a.startswith('--%s=' % name): return a.split('=', 1)[1]
    return default
ONLY = _arg('anims')      # --anims=a,b: build / fit only these animations (the rest of the run is the same)
UPX = 27.5
INP = 'res://actors/_shared/sakuga/Inputs/'
IDLE, FALLING, LANDING = 0, 10, 11
FIRST_SPECIAL = 41          # stance moves 0-40 are the shared system/normal moves; hers start here

def hb(name): return A + 'Hitboxes/%s.tres' % name
def an(name): return A + 'AnimationData/%s_AnimData.tres' % name
def set_armor(v): return Obj(ACT + 'SetArmorAction.cs', Value=v)   # v hits absorbed (half damage); -1 = none (0 is ignored)
def hold_opp(x, y):   # Oct 25: keeps the opponent (while being hit) at (x along her facing, y above her feet), every frame it runs
    return Obj(ACT + 'NetsuHoldOpponentAction.cs', Offset=V2i(x, y))
def sky_rise(v=0, g=0, height=120000, margin=5000):
    # Oct 25: sets the vertical speed (v) / pulls it back (g) like movey / gravity, both scaled down on stages whose camera
    # can't go height units up (StageElement.NetsuCameraTop): the climb lasts as long everywhere, tops out under the ceiling
    return Obj(ACT + 'NetsuSkyRiseAction.cs', Velocity=v or None, Gravity=g or None, Height=height, Margin=margin)

# ---------------------------------------------------------------------------------------------
# attack properties (first pass; her 5C does 650, 2C 460). reaction: the opponent's hit reaction
# (stance HitReactions: 0 weak, 1 strong, 5 air, 6 crumple, 7 launch away, 8 launch up, 9 launch down)
P236A = attack(900, 24, 14, kb=(-40000, 0), air_kb=(-25000, 30000), reaction=1, air_reaction=5, stop=11, gain=400)
P236B = attack(1300, 30, 16, kb=(-70000, 25000), air_kb=(-50000, 35000), reaction=7, air_reaction=7, hitstun_type=KNOCKDOWN,
               kb_gravity=200000, stop=14, gain=450)
# Oct 25 night (bigger EX moves): Supernova Fist blasts them across the screen into a wall bounce (juggle after it)
P236C = attack(1600, 70, 20, kb=(-110000, 90000), air_kb=(-110000, 90000), reaction=7, air_reaction=7, hitstun_type=KNOCKDOWN,
               kb_gravity=130000, air_gravity=130000, stop=20, gain=0, scaling=5, extra=dict(BounceTime=120, BounceXIntensity=40))
DP1 = attack(450, 30, 16, kb=(-4000, 45000), air_kb=(-4000, 45000), reaction=8, air_reaction=8, stop=9, gain=200)
DP2 = attack(350, 30, 16, kb=(-3000, 55000), air_kb=(-3000, 55000), reaction=8, air_reaction=8, stop=6, gain=150)
DPA_TOP = attack(700, 36, 18, kb=(-12000, 40000), air_kb=(-12000, 40000), reaction=8, air_reaction=8, hitstun_type=KNOCKDOWN,
                 kb_gravity=220000, stop=13, gain=300)
DPB_TOP = attack(900, 40, 18, kb=(-14000, 48000), air_kb=(-14000, 48000), reaction=8, air_reaction=8, hitstun_type=KNOCKDOWN,
                 kb_gravity=220000, stop=15, gain=350)
BEAM = attack(800, 40, 20, kb=(-20000, -80000), air_kb=(-20000, -80000), reaction=9, air_reaction=9, hitstun_type=HARD_KNOCKDOWN,
              kb_gravity=200000, stop=15, gain=200)
DPC_HOLD = attack(400, 60, 20, kb=(0, 0), air_kb=(0, 8000), reaction=1, air_reaction=5, stop=16, gain=0, scaling=4, air_gravity=1)
DPC_SPIN = attack(250, 40, 18, kb=(-2000, 60000), air_kb=(-2000, 60000), reaction=8, air_reaction=8, stop=5, gain=0, scaling=3)
DPC_TOP = attack(900, 45, 20, kb=(-12000, 115000), air_kb=(-12000, 115000), reaction=8, air_reaction=8, hitstun_type=HARD_KNOCKDOWN,
                 kb_gravity=200000, air_gravity=200000, stop=18, gain=0, scaling=5)   # Oct 25 night: sky-high
KNEE = attack(600, 22, 14, kb=(-15000, 30000), air_kb=(-10000, 35000), reaction=1, air_reaction=5, stop=10, gain=300)
DROP = attack(800, 24, 16, kb=(-25000, 0), air_kb=(-15000, -40000), reaction=1, air_reaction=5, stop=12, gain=300, hit_type=HIGH)
DROP_C = attack(700, 30, 18, kb=(-10000, 0), air_kb=(-10000, -40000), reaction=1, air_reaction=5, stop=12, gain=0, hit_type=HIGH, scaling=4)
IMPACT = attack(700, 26, 16, kb=(-40000, 30000), air_kb=(-30000, 40000), reaction=7, air_reaction=7, hitstun_type=KNOCKDOWN,
                kb_gravity=220000, stop=12, gain=300, hit_type=LOW)
# Oct 25 night: the EX impact is a pillar of light that launches them high (juggle after it)
IMPACT_C = attack(1100, 70, 20, kb=(-4000, 105000), air_kb=(-4000, 105000), reaction=8, air_reaction=8, crouch_reaction=8, stop=18,
                  kb_gravity=200000, air_gravity=200000, gain=0, scaling=5, hit_type=LOW)
# Radiant Breaker: the rush holds them, the burst hits four times, the last one blasts them away
S1_RUSH = attack(300, 60, 20, kb=(0, 0), air_kb=(0, 0), reaction=1, air_reaction=5, stop=12, gain=0, scaling=0, air_gravity=1)
S1_BURST = attack(250, 45, 20, kb=(-3000, 0), air_kb=(-3000, 3000), reaction=1, air_reaction=5, stop=4, gain=0, scaling=1, air_gravity=1,
                  pushback=0)
S1_END = attack(1500, 60, 24, kb=(-90000, 40000), air_kb=(-90000, 40000), reaction=7, air_reaction=7, hitstun_type=HARD_KNOCKDOWN,
                kb_gravity=200000, stop=20, gain=0, scaling=0)
# Big Bang Crash (Oct 25): the punch lifts them onto her fist and she rockets up into the sky with them (they're held
# there: NetsuHoldOpponentAction), three hits on the way up; at the top she leaps over them and slams them, the dive
# drags them down under her fist, the explosion finishes. Hard knockdown from the first hit: no air recovery.
# Total 3350 (as before the rework).
S2_RISE_BOX = [[-20, 60, 330, 700]]   # sprite px from her feet (x forward, y up): -0.05..0.9 m ahead, 0.17..1.9 m up
S2_LIFT_BOX = [[60, 120, 420, 820]]   # where she holds them on the way up (0.6 m ahead, 0.4 m up: S2_HOLD_UP)
S2_SLAM_BOX = [[-40, -480, 330, 150]]  # under her fist (0.3 m ahead, 1 m below her feet: S2_HOLD_DOWN)
S2_HOLD_UP, S2_HOLD_DOWN = (6000, 4000), (3000, -10000)   # her fist in their stomach / on their shoulders
S2_RISE = attack(400, 90, 20, kb=(0, 30000), air_kb=(0, 0), reaction=5, air_reaction=5, stop=14, gain=0, scaling=0, air_gravity=1,
                 hitstun_type=HARD_KNOCKDOWN)
S2_LIFT = attack(100, 60, 20, kb=(0, 0), air_kb=(0, 0), reaction=5, air_reaction=5, stop=0, gain=0, scaling=1, air_gravity=1,
                 hitstun_type=HARD_KNOCKDOWN)
S2_SLAM = attack(350, 60, 20, kb=(0, 0), air_kb=(0, 0), reaction=5, air_reaction=5, stop=10, gain=0, scaling=1, air_gravity=1,
                 hitstun_type=HARD_KNOCKDOWN)
S2_BOOM = attack(300, 45, 20, kb=(0, 25000), air_kb=(0, 25000), reaction=8, air_reaction=8, stop=4, gain=0, scaling=1, kb_gravity=60000,
                 air_gravity=60000)
S2_END = attack(1400, 60, 30, kb=(-30000, 80000), air_kb=(-30000, 80000), reaction=8, air_reaction=8, hitstun_type=HARD_KNOCKDOWN,
                kb_gravity=200000, stop=22, gain=0, scaling=0)
# the rise: 360000 up, slowed by 540000 a second: 40 frames to the top, ~12 m up (less on a stage with a lower camera
# top: sky_rise). The dive: 250000 down, faster by 900000 a second: ~19 frames back to the floor.
S2_UP, S2_UP_G, S2_UP_FRAMES = 360000, 540000, 40
S2_DOWN, S2_DOWN_G = -250000, 900000
S2_TOP_FRAMES = 10    # at the top: she hops ~1.1 m over them (they slide under her fist), then the slam
S2_HOP = 144000       # up at the top's first frame, slowed to 0 by its last (gravity S2_HOP * 6)
def _s2_top_hold():
    out = []
    for f in range(S2_TOP_FRAMES):
        s = f / (S2_TOP_FRAMES - 1.0); s = s * s * (3 - 2 * s)
        out.append((f, hold_opp(int(round(S2_HOLD_UP[0] + (S2_HOLD_DOWN[0] - S2_HOLD_UP[0]) * s)),
                                int(round(S2_HOLD_UP[1] + (S2_HOLD_DOWN[1] - S2_HOLD_UP[1]) * s)))))
    return out

# ---------------------------------------------------------------------------------------------
# effect layers (added to the manifest's frames). "attach": [frame, point on that drawing, point on the effect]
R = 'Flan_All_Sprites/'
EXT = R + '02_Basics/Flan_Basics_v2/PNG/5C_Radiant_Extension.png'     # starburst on its left, light streak to the right
BURST = R + '07_623_AB_Latest/Flan_623_AB_v3/Peak_Burst.png'          # radial burst, centre (768, 516)
FX6 = R + '06_623_Base_and_C/Flan_623/Effects/'
EXP = R + '10_214214_Super/Flan_214214_Final/Effects/Explosion_0%d.png'
FRAMES = {
    'fx_5c': {'src': EXT, 'anchor': 'attach', 'attach': ['5c_2', [733, 478], [400, 414]], 'scale': 6.0},     # short reach
    'fx_236b': {'src': EXT, 'anchor': 'attach', 'attach': ['p236', [730, 423], [400, 414]], 'scale': 5.0},
    'fx_236c': {'src': EXT, 'anchor': 'attach', 'attach': ['p236', [730, 423], [400, 414]], 'scale': 3.4},
    'dp_burst_a': {'src': BURST, 'anchor': 'attach', 'attach': ['dp_held', [243, 35], [768, 516]], 'scale': 5.0},
    'dp_burst_b': {'src': BURST, 'anchor': 'attach', 'attach': ['dp_held', [243, 35], [768, 516]], 'scale': 3.5},
    'dp_burst_c': {'src': BURST, 'anchor': 'attach', 'attach': ['dp_rise2', [218, 6], [768, 516]], 'scale': 2.6},
    'spin_c': {'src': FX6 + 'Spin_C.png', 'anchor': 'attach', 'attach': ['dp_rise2', [28, 1], [0, 0]], 'scale': 1.0},
    'k214_exfx': {'src': BURST, 'anchor': 'attach', 'attach': ['k214_impact', [235, 255], [768, 516]], 'scale': 2.4},
    's1_burst': {'src': 'derived/flan/radiant_burst.png', 'anchor': 'attach', 'attach': ['s1_fire', [563, 461], [215, 515]], 'scale': 1.0596},
    'fx_burst': {'src': BURST, 'anchor': 'center', 'at': [0, 250], 'scale': 2.2},
}
for i in (1, 2, 3):   # the beam's canvas sits at (350, 260) of Beam_Aim_01's (the pack's preview GIF), same scale
    FRAMES['beam_%d' % i] = {'src': FX6 + 'Beam_0%d.png' % i, 'anchor': 'attach', 'attach': ['dp_aim', [350.6, 260.4], [0, 0]], 'scale': 1.0}
for i in range(1, 7):  # the explosion: (255.7, 458.2) of its canvas is the ground point under Ground_Impact (preview GIF)
    FRAMES['exp_%d' % i] = {'src': EXP % i, 'anchor': 'pin', 'pin': [255.7, 458.2], 'scale': 0.4016}
FRAME_PATCH = {}
def fx(f): return {'fx': f, 'fx_always': True}

# ---------------------------------------------------------------------------------------------
# the moves.  keys: [frame, at, {options}] (see build.py); boxes: [at, stage, kind, props]
#   kind 'pose' = hurtboxes only (fitted), 'pose+prox' = + proximity guard, 'atk' = hurt + proximity + attack (fitted),
#   'atk_inv' = attack only (no hurtboxes: invincible), 'none' = nothing hittable; '-pass' = no pushbox either.
#   'manual' (6th item) = attack box in world px instead of the fitted one.
# input: (motion, [buttons]); a move without 'input' is a state only (reached from another state).
def twirl(start, n, step=3, pre='w236_'):
    return [[pre + '%d' % (i % 4 + 1), start + i * step] for i in range(n)]
def twirl3(start, n, step=4):     # the 214214 windup has three drawings
    return [['s2_w%d' % (i % 3 + 1), start + i * step] for i in range(n)]
SPIN = ['dp_rise2', 'dp_spin', 'dp_rise2_m']
def spin_keys(start, n, step=3):
    return [[SPIN[i % 3], start + i * step, fx('spin_c')] for i in range(n)]

MOVES = {
  '236A': dict(slot=73, name='Star Fist', input=('236', ['A']), move_file='53_FLN_StarFist_A', hbp='30_Hitbox_StarFist_A',
      duration=36, keys=[['dash_1', 0], ['p236', 8], ['p236', 20, {'dx': -6}], ['crouch_1', 26]],
      boxes=[[0, 0, 'pose+prox'], [8, 1, 'atk', P236A], [12, 2, 'pose'], [26, 2, 'pose']],
      tick=[(4, movex(90000)), (12, movex(0))], enter=[change_side(), movex(0)], priority=7,
      cancels=[('S1', HIT, (8, 30)), ('S2', HIT, (8, 30))]),
  '236B': dict(slot=74, name='Twirling Star Fist', input=('236', ['B', 'C']), move_file='54_FLN_StarFist_B', hbp='31_Hitbox_StarFist_B',
      duration=52, keys=twirl(0, 8) + [['p236', 24, fx('fx_236b')], ['p236', 31], ['p236', 38, {'dx': -6}], ['crouch_1', 42]],
      boxes=[[0, 0, 'pose+prox'], [24, 1, 'atk', P236B], [30, 2, 'pose'], [42, 2, 'pose']],
      tick=[(4, set_armor(1)), (21, movex(110000)), (24, set_armor(-1)), (30, movex(0))], enter=[change_side(), movex(0)],
      exit=[set_armor(-1)], priority=7, cancels=[('S1', HIT, (24, 44)), ('S2', HIT, (24, 44))], ai=0x10 | 2),
  '236C': dict(slot=75, name='Supernova Fist', input=('236', ['C']), move_file='55_FLN_StarFist_EX', hbp='32_Hitbox_StarFist_EX',
      duration=50, keys=twirl(0, 5) + [['p236', 16, fx('fx_236c')], ['p236', 30], ['p236', 36, {'dx': -6}], ['crouch_1', 40]],
      boxes=[[0, 0, 'none'], [16, 1, 'atk_inv', P236C], [22, 2, 'pose'], [40, 2, 'pose']],
      tick=[(13, movex(130000)), (22, movex(0)), (22, frame_props(0))],
      enter=[change_side(), movex(0), frame_props(INV_STRIKE | INV_THROW)], exit=[frame_props(0)],
      meter=4000, flash=15, priority=9, afterimages=True, cancels=[('S1', HIT, (16, 46)), ('S2', HIT, (16, 46))], ai=0x10 | 2 | 0x1000),
  '623A': dict(slot=76, name='Rising Star', input=('623', ['A']), move_file='56_FLN_RisingStar_A', hbp='33_Hitbox_RisingStar_A',
      duration=120, keys=[['dp_hit', 0], ['dp_held', 7], ['dp_held', 19, fx('dp_burst_a')], ['dp_apex', 26], ['dp_fall', 32]],
      boxes=[[0, 0, 'pose'], [3, 1, 'atk', DP1], [7, 2, 'pose'], [8, 1, 'atk', DP2], [15, 2, 'pose'], [19, 1, 'atk', DPA_TOP], [24, 2, 'pose']],
      tick=[(6, movey(80000)), (6, movex(12000)), (8, reset_hit()), (19, reset_hit())], tick_ranges=[((7, 400), gravity())],
      enter=[change_side(), movex(0)], air_land=True, priority=8, cancels=[('BEAM', WHIFF | HIT | BLOCK, (22, 34))]),
  '623B': dict(slot=77, name='Rising Star', input=('623', ['B', 'C']), move_file='57_FLN_RisingStar_B', hbp='34_Hitbox_RisingStar_B',
      duration=120, keys=[['dp_hit', 0], ['dp_held', 7], ['dp_held', 23, fx('dp_burst_b')], ['dp_apex', 30], ['dp_fall', 36]],
      boxes=[[0, 0, 'none'], [3, 1, 'atk_inv', DP1], [7, 2, 'pose'], [8, 1, 'atk', DP2], [17, 2, 'pose'], [23, 1, 'atk', DPB_TOP], [28, 2, 'pose']],
      tick=[(6, movey(96000)), (6, movex(12000)), (8, reset_hit()), (23, reset_hit()), (8, frame_props(0))],
      tick_ranges=[((7, 400), gravity())], enter=[change_side(), movex(0), frame_props(INV_STRIKE | INV_THROW)], exit=[frame_props(0)],
      air_land=True, priority=8, cancels=[('BEAM', WHIFF | HIT | BLOCK, (26, 38))], ai=0x10 | 2 | 0x1000),
  'BEAM': dict(slot=79, name='Falling Star', input=('5', ['X']), move_file='59_FLN_FallingStar', hbp='36_Hitbox_FallingStar',
      duration=60, keys=[['dp_aim', 0], ['dp_aim', 4, fx('beam_1')], ['dp_aim', 8, fx('beam_2')], ['dp_aim', 12, fx('beam_3')], ['dp_fall', 18]],
      boxes=[[0, 0, 'pose'], [4, 1, 'atk', BEAM], [12, 2, 'pose'], [18, 2, 'pose']],
      tick=[(0, movex(0)), (0, movey(8000)), (18, movey(0))], tick_ranges=[((1, 17), gravity(30000)), ((19, 400), gravity())],
      air_land=True, air=True, ground=False, skip_check=True, priority=9, ai=0x10 | 4),
  '623C': dict(slot=78, name='Spiral Star', input=('623', ['C']), move_file='58_FLN_SpiralStar', hbp='35_Hitbox_SpiralStar',
      duration=120, keys=[['dp_hit', 0]] + spin_keys(12, 8) + [['dp_rise2', 36, fx('dp_burst_c')], ['dp_apex', 42], ['dp_fall', 48]],
      boxes=[[0, 0, 'none'], [3, 1, 'atk_inv', DPC_HOLD], [7, 2, 'none'], [12, 1, 'atk_inv', DPC_SPIN], [32, 2, 'none'],
             [36, 1, 'atk_inv', DPC_TOP], [41, 2, 'pose']],
      tick=[(11, movey(115000)), (11, movex(6000)), (12, reset_hit()), (16, reset_hit()), (20, reset_hit()), (24, reset_hit()),
            (28, reset_hit()), (36, reset_hit()), (36, camera_shake(0.03, 10)), (41, frame_props(0))],
      tick_ranges=[((12, 400), gravity())], enter=[change_side(), movex(0), frame_props(INV_STRIKE | INV_THROW)], exit=[frame_props(0)],
      air_land=True, land_from=14,   # Oct 24: she only leaves the ground on frame 11 (it "landed" on frame 10 and never rose)
      meter=4000, flash=15, priority=9, afterimages=True, ai=0x10 | 2 | 0x1000),
  'DPLAND': dict(slot=80, name='Rising Star (landing)', hbp='37_Hitbox_StarLanding', duration=16,
      keys=[['jump_load', 0], ['crouch_1', 8]], boxes=[[0, 0, 'pose'], [8, 0, 'pose']], enter=[movex(0), movey(0)], ai=0x10 | 2),
  '214A': dict(slot=81, name='Meteor Drop', input=('214', ['A']), move_file='60_FLN_MeteorDrop_A', hbp='38_Hitbox_MeteorDrop_A',
      duration=120, keys=[['k214_idle', 0], ['k214_knee', 4], ['k214_load', 19], ['k214_punch', 24]],
      boxes=[[0, 0, 'pose'], [5, 1, 'atk', KNEE], [12, 2, 'pose'], [24, 1, 'atk', DROP]],
      tick=[(4, movey(68000)), (4, movex(30000)), (12, reset_hit()), (19, movey(0)), (19, movex(6000)), (24, movey(-100000)),
            (24, movex(30000))],
      tick_ranges=[((5, 18), gravity()), ((19, 23), gravity(20000)), ((25, 400), gravity())],
      enter=[change_side(), movex(0)], meteor_land=84, priority=7, ai=0x10 | 2,
      cancels=[('S1', HIT, (0, 60)), ('S2', HIT, (0, 60))]),
  '214B': dict(slot=82, name='Meteor Drop', input=('214', ['B', 'C']), move_file='61_FLN_MeteorDrop_B', hbp='39_Hitbox_MeteorDrop_B',
      duration=120, keys=[['k214_idle', 0], ['k214_knee', 4], ['k214_load', 23], ['k214_punch', 28]],
      boxes=[[0, 0, 'pose'], [5, 1, 'atk', KNEE], [14, 2, 'pose'], [28, 1, 'atk', DROP]],
      tick=[(4, movey(84000)), (4, movex(32000)), (14, reset_hit()), (23, movey(0)), (23, movex(6000)), (28, movey(-110000)),
            (28, movex(32000))],
      tick_ranges=[((5, 22), gravity()), ((23, 27), gravity(20000)), ((29, 400), gravity())],
      enter=[change_side(), movex(0)], meteor_land=84, priority=7, ai=0x10 | 2,
      cancels=[('S1', HIT, (0, 60)), ('S2', HIT, (0, 60))]),
  '214C': dict(slot=83, name='Meteor Impact', input=('214', ['C']), move_file='62_FLN_MeteorImpact', hbp='40_Hitbox_MeteorImpact',
      duration=120, keys=[['k214_idle', 0], ['k214_knee', 4], ['k214_load', 19], ['k214_punch', 24]],
      boxes=[[0, 0, 'none'], [5, 1, 'atk_inv', KNEE], [12, 2, 'pose'], [24, 1, 'atk', DROP_C]],
      tick=[(4, movey(68000)), (4, movex(30000)), (12, frame_props(0)), (12, reset_hit()), (19, movey(0)), (19, movex(6000)),
            (24, movey(-110000)),
            (24, movex(34000))],
      tick_ranges=[((5, 18), gravity()), ((19, 23), gravity(20000)), ((25, 400), gravity())],
      enter=[change_side(), movex(0), frame_props(INV_STRIKE | INV_THROW)], exit=[frame_props(0)], meteor_land=85,
      meter=4000, flash=15, priority=9, afterimages=True, ai=0x10 | 2 | 0x1000,
      cancels=[('S1', HIT, (0, 60)), ('S2', HIT, (0, 60))]),
  'IMPACT': dict(slot=84, name='Meteor Drop (impact)', hbp='41_Hitbox_MeteorDrop_Impact', duration=30,
      keys=[['k214_impact', 0], ['k214_idle', 18]], boxes=[[0, 1, 'atk', IMPACT], [5, 2, 'pose'], [18, 2, 'pose']],
      enter=[movex(0), movey(0)], tick=[(0, camera_shake(0.02, 8))], ai=0x10 | 2),
  'IMPACT_C': dict(slot=85, name='Meteor Impact (impact)', hbp='42_Hitbox_MeteorImpact_Impact', duration=34,
      keys=[['k214_impact', 0, fx('k214_exfx')], ['k214_impact', 10], ['k214_idle', 20]],
      boxes=[[0, 1, 'atk_inv', IMPACT_C], [6, 2, 'pose'], [20, 2, 'pose']],
      enter=[movex(0), movey(0)], tick=[(0, camera_shake(0.04, 12))], ai=0x10 | 2),
  'S1': dict(slot=92, name='Radiant Breaker', input=('236', ['BC']), move_file='63_FLN_RadiantBreaker', hbp='43_Hitbox_RadiantBreaker',
      duration=66, keys=twirl(0, 8, pre='s1_w') + [['s1_dash', 24], ['s1_dash', 44, {'dx': -8}], ['s1_exit', 48], ['s1_idle', 58]],
      boxes=[[0, 0, 'none'], [24, 1, 'atk_inv', S1_RUSH], [44, 2, 'pose'], [58, 2, 'pose']],
      tick=[(24, movex(165000)), (44, movex(0)), (44, frame_props(0))],
      enter=[change_side(), movex(0), frame_props(INV_STRIKE | INV_THROW | INV_PROJ)], exit=[frame_props(0)],
      hit_confirm=[ev([check_hit(HIT)], [play_state(93)])], meter=6000, flash=20, priority=10, ai=0x10 | 2 | 0x1000),
  'S1_hit': dict(slot=93, name='Radiant Breaker (burst)', hbp='44_Hitbox_RadiantBreaker_Burst', duration=96,
      keys=[['s1_fire', 0], ['s1_fire', 6, fx('s1_burst')], ['s1_fire', 36], ['s1_recoil', 40], ['s1_roll', 52],
            ['s1_roll', 56, {'rot': 60}], ['s1_roll', 60, {'rot': 120}], ['s1_roll', 64, {'rot': 180}], ['s1_exit', 68], ['s1_idle', 82]],
      boxes=[[0, 0, 'none-pass'], [6, 1, 'atk_inv-pass', S1_BURST], [10, 2, 'none-pass'], [12, 1, 'atk_inv-pass', S1_BURST],
             [16, 2, 'none-pass'], [18, 1, 'atk_inv-pass', S1_BURST], [22, 2, 'none-pass'], [24, 1, 'atk_inv-pass', S1_BURST],
             [28, 2, 'none-pass'], [30, 1, 'atk_inv-pass', S1_END], [36, 2, 'none'], [68, 2, 'pose']],
      tick=[(6, reset_hit()), (12, reset_hit()), (18, reset_hit()), (24, reset_hit()), (30, reset_hit()), (6, camera_shake(0.03, 24)),
            (30, camera_shake(0.06, 16)), (40, movex(-55000)), (40, movey(36000)), (52, movex(-25000)), (66, movex(0)), (68, frame_props(0))],
      tick_ranges=[((41, 400), gravity())],
      enter=[frame_props(INV_STRIKE | INV_THROW | INV_PROJ), movex(0), movey(0)], exit=[frame_props(0)], priority=10,
      afterimages=True, ai=0x10 | 2 | 0x1000),
  'S2': dict(slot=94, name='Big Bang Crash', input=('214', ['BC']), move_file='64_FLN_BigBangCrash', hbp='45_Hitbox_BigBangCrash',
      # Oct 25: she twirls through the super's pause (90 frames: S2_charge), so the punch comes 12 frames after it (was 24)
      duration=110, keys=twirl3(0, 3) + [['s2_diag', 12], ['s2_load', 30], ['jump_fall', 38]],
      # Oct 24 night: the fitted box (her raised fist only) passed over anyone not right on top of her, so even 5B > super
      # whiffed (5B's push leaves ~0.7 m): the rise's attack box now covers the space in front of her, feet to above her head
      boxes=[[0, 0, 'none'], [12, 1, 'atk_inv', S2_RISE, None, S2_RISE_BOX], [28, 2, 'pose']],
      tick=[(12, movex(45000)), (12, movey(105000)), (28, frame_props(0)), (28, movex(12000))], tick_ranges=[((13, 400), gravity())],
      enter=[change_side(), movex(0), frame_props(INV_STRIKE | INV_THROW | INV_PROJ)], exit=[frame_props(0)], air_land=True,
      land_from=16,   # she twirls on the ground until frame 12
      hit_confirm=[ev([check_hit(HIT)], [play_state(95)])], meter=6000, flash=20, priority=10, ai=0x10 | 2 | 0x1000,
      move_extra={'NetsuPauseFrames': 90, 'NetsuPauseState': 105}),
  'S2_charge': dict(slot=105, name='Big Bang Crash (charge)', hbp='49_Hitbox_BigBangCrash_Charge', duration=15,
      # Oct 25: only its picture is used: the twirl that loops through the super's 90-frame pause (MoveSettings.NetsuPauseState)
      keys=[['s2_w1', 0], ['s2_w2', 5], ['s2_w3', 10]], boxes=[[0, 0, 'none']], ai=0x10 | 2),
  'S2_hit': dict(slot=95, name='Big Bang Crash (rise)', hbp='46_Hitbox_BigBangCrash_Rise', duration=S2_UP_FRAMES + 20,
      # Oct 25: up into the sky with them on her fist (was: a short dive from half a metre up)
      keys=[['s2_diag', 0]],
      boxes=[[0, 0, 'none-pass'], [8, 1, 'atk_inv-pass', S2_LIFT, None, S2_LIFT_BOX], [10, 2, 'none-pass'],
             [16, 1, 'atk_inv-pass', S2_LIFT, None, S2_LIFT_BOX], [18, 2, 'none-pass'],
             [24, 1, 'atk_inv-pass', S2_LIFT, None, S2_LIFT_BOX], [26, 2, 'none-pass']],
      tick=[(1, sky_rise(v=S2_UP)), (8, reset_hit()), (16, reset_hit()), (24, reset_hit())],
      tick_ranges=[((1, S2_UP_FRAMES), sky_rise(g=S2_UP_G)), ((0, 999), hold_opp(*S2_HOLD_UP))],
      transitions=[ev([at_range(S2_UP_FRAMES, 999)], [play_state(106)])],
      enter=[frame_props(INV_STRIKE | INV_THROW | INV_PROJ), movex(0), movey(0)],
      exit=[frame_props(0)], priority=10, afterimages=True, ai=0x10 | 2 | 0x1000, show_stage=True),
  'S2_top': dict(slot=106, name='Big Bang Crash (slam)', hbp='48_Hitbox_BigBangCrash_Slam', duration=90,
      # Oct 25: at the top she hops over them, slams them (10) and dives, dragging them down under her fist
      keys=[['s2_load', 0], ['s2_down', S2_TOP_FRAMES]],
      boxes=[[0, 0, 'none-pass'], [S2_TOP_FRAMES, 1, 'atk_inv-pass', S2_SLAM, None, S2_SLAM_BOX], [S2_TOP_FRAMES + 2, 2, 'none-pass']],
      tick=[(S2_TOP_FRAMES, movey(0)), (S2_TOP_FRAMES, reset_hit()), (S2_TOP_FRAMES, camera_shake(0.05, 14)),
            (S2_TOP_FRAMES + 1, movey(S2_DOWN))],
      # the holds come last in the frame (after her speed is set: they place the opponent where she'll be)
      tick_ranges=[((0, S2_TOP_FRAMES - 1), gravity(S2_HOP * 6)), ((S2_TOP_FRAMES + 2, 400), gravity(S2_DOWN_G)),
                   ((S2_TOP_FRAMES, 999), hold_opp(*S2_HOLD_DOWN))] + [((f, f), h) for f, h in _s2_top_hold()],
      enter=[frame_props(INV_STRIKE | INV_THROW | INV_PROJ), movex(0), movey(S2_HOP)],
      exit=[frame_props(0)], meteor_land=97, land_from=S2_TOP_FRAMES + 1, priority=10, afterimages=True, ai=0x10 | 2 | 0x1000,
      show_stage=True),
  'S2_boom': dict(slot=97, name='Big Bang Crash (explosion)', hbp='47_Hitbox_BigBangCrash_Boom', duration=100,
      keys=[['s2_impact', 0, fx('exp_1')], ['s2_impact', 3, fx('exp_2')], ['s2_impact', 7, fx('exp_3')], ['s2_impact', 13, fx('exp_4')],
            ['s2_impact', 19, fx('exp_5')], ['s2_impact', 26, fx('exp_6')], ['s2_impact', 32], ['s2_stand', 40], ['s2_sweat', 54]],
      boxes=[[0, 1, 'atk_inv', S2_BOOM], [4, 2, 'none'], [6, 1, 'atk_inv', S2_BOOM], [10, 2, 'none'],
             [12, 1, 'atk_inv', S2_BOOM], [16, 2, 'none'], [19, 1, 'atk_inv', S2_END], [25, 2, 'none'], [40, 2, 'pose']],
      tick=[(6, reset_hit()), (12, reset_hit()), (19, reset_hit()), (0, camera_shake(0.07, 30)), (40, frame_props(0))],
      enter=[frame_props(INV_STRIKE | INV_THROW | INV_PROJ), movex(0), movey(0)], exit=[frame_props(0)], priority=10, ai=0x10 | 2 | 0x1000,
      show_stage=True),   # Oct 25: the stage stays in view (no dark backdrop) from the rise to the end
}
DP_LAND = MOVES['DPLAND']['slot']
SPEED_FIX = 1.0       # speeds above are real engine speeds (movereel.py shows them as the game does)
# which normals cancel into what (first match wins: supers -> EX -> 214 -> 623 -> 236)
GROUND_CANCEL_ORDER = ['S2', 'S1', '214C', '214B', '214A', '623C', '623B', '623A', '236C', '236B', '236A']
AIR_CANCEL_ORDER = ['jBEAM']   # Oct 25: her air normals cancel into the air Falling Star (an air combo ender)
GROUND_NORMALS = ['23_FLN_5A', '24_FLN_5B', '25_FLN_5C', '26_FLN_2A', '27_FLN_2B', '28_FLN_2C', '32_FLN_6C']
AIR_NORMALS = ['29_FLN_j_5A', '30_FLN_j_5B', '31_FLN_j_5C']
# stance order (the neutral lookup runs from the END of the list, so later = checked first). Oct 25: jBEAM goes last,
# so every move before it keeps its index
STANCE_ORDER = ['236A', '236B', '236C', '623A', '623B', '623C', 'BEAM', '214A', '214B', '214C', 'S1', 'S2', 'jBEAM']
INPUTS = {('236', 'A'): '44_Input_236A', ('236', 'B|C'): '45_Input_236B_or_C', ('236', 'C'): '20_Input_236C',
          ('623', 'A'): '46_Input_623A', ('623', 'B|C'): '47_Input_623B_or_C', ('623', 'C'): '24_Input_623C',
          ('214', 'A'): '40_Input_214A', ('214', 'B|C'): '41_Input_214B_or_C', ('214', 'C'): '21_Input_214C',
          ('236', 'BC'): '25_Input_236BC', ('214', 'BC'): '48_Input_214BC', ('5', 'X'): '26_Input_5X',
          ('236', 'A|B'): '55_Input_236A_or_B'}
MANUAL_BOXES = {}
# moves that play a state made above (no animation of their own). Oct 25: the Falling Star from any jump (236 + A or
# B in the air): the same beam as the Rising Star's follow-up, as an air combo ender
EXTRA_MOVES = {
  'jBEAM': dict(state=79, name='Falling Star', input=('236', ['A', 'B']), move_file='65_FLN_FallingStar_Air', air=True, ground=False,
                priority=8),
}

# the standard animations that get effect layers (keys as in make_flan_manifest.py, plus the effect)
ANIM_FX = {
  '50_FLN_5C': [['5c_1', 0], ['5c_2', 13, fx('fx_5c')], ['5c_2', 18], ['5c_3', 21]],
  '1001_FLN_Burst': [['6c_1', 0], ['6c_2', 4, fx('fx_burst')], ['6c_2', 24], ['6c_3', 34]],
}

# ---------------------------------------------------------------------------------------------
def input_res(motion, buttons):
    res = INP + INPUTS[(motion, '|'.join(buttons))] + '.tres'
    if not os.path.exists(res_file(res)):
        if DRY: raise SystemExit('missing input ' + res)
        write(res, MotionInputs(motion, buttons))   # Oct 25: a new one (the air Falling Star's 236 + A or B)
    return res

def hitbox_files(mk, m):
    """skeleton hitbox files (boxes get fitted by hitfit.py afterwards)"""
    names = []
    for i, b in enumerate(m['boxes']):
        at, stage, kind = b[0], b[1], b[2]; props = b[3] if len(b) > 3 else None
        manual = b[5] if len(b) > 5 else None
        name = '%s_%d' % (m['hbp'], i); res = hb(name); names.append((at, stage, name, kind))
        if manual: MANUAL_BOXES[name] = manual
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

def set_state_slots(data_res, slots, clear_from=73):
    """slots: {index: state_res}; extends the list with idle if needed. Slots from clear_from on that still point at
    another fighter's files (the copy's leftovers) go back to idle; references nothing uses any more are dropped."""
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

def set_fields(res, fields, label):
    """set top-level fields of a resource file ([resource] block)"""
    def fn(t):
        for k, v in fields.items(): t.res_set(k, v)
    return edit_tres(res, fn, BK, label)

def set_hitbox_attack(res, values):
    """change damage-side values of the attack element(s) of a hitbox file (text keys, e.g. BaseDamage)"""
    path = res_file(res); txt = open(path, encoding='utf-8').read()
    t = Tres(txt)
    for s in t.sub:
        body = '\n'.join(s[2])
        if 'HitboxType = 1' not in body: continue
        for k, v in values.items():
            if any(l.startswith(k + ' = ') for l in s[2]): s[2] = [('%s = %s' % (k, v)) if l.startswith(k + ' = ') else l for l in s[2]]
            else: s[2].append('%s = %s' % (k, v))
    new = t.text()
    if new != txt:
        bk = os.path.join(fdk.PROJ, BK, os.path.basename(path) + '.bak')
        if not os.path.exists(bk): os.makedirs(os.path.dirname(bk), exist_ok=True); open(bk, 'w', encoding='utf-8').write(txt)
        open(path, 'w', encoding='utf-8', newline='\n').write(new); fdk.LOG.append('attack values: ' + res)

TWO_B_CHAINS = [24, 25, 28, 4, 5, 6]   # 2B -> 5B, 5C, 2C and the jump cancels (stance move indices)

def patch_normals():
    """her normals came from Cecilia's: 6C (was Cecilia's 4A) becomes her fist pump, she walks slower"""
    # Oct 24: 2B chains into 5B, 5C, 2C and the jump cancels, like Cecilia's 2B (it could only go into specials)
    add_cancels(A + 'Moves/27_FLN_2B.tres', [(i, HIT | BLOCK, (0, 999)) for i in TWO_B_CHAINS], BK, before_all=False)
    set_fields(A + 'Moves/32_FLN_6C.tres', {}, '6C')
    def six_c(t):
        t.res_set('MoveName', '"6C"')
        e = t.ext_by_id(re.search(r'ExtResource\("([^"]+)"\)', t.res_get('Inputs')).group(1))
        e['path'] = INP + '14_Input_6C.tres'; e['uid'] = res_uid(INP + '14_Input_6C.tres')
        # 6C is a heavy: it chains into nothing but specials (Cecilia's 4A chained into 5A / 2A / itself)
        keep = []
        for r in list_refs(t, 'CanCancelTo'):
            sid = re.search(r'"([^"]+)"', r).group(1); s = t.sub_get(sid)
            mm = re.search(r'MoveIndex = (\d+)', '\n'.join(s[2])) if s else None
            if mm and int(mm.group(1)) in (23, 26, 32): continue
            keep.append(r)
        t.res_set('CanCancelTo', '[' + ', '.join(keep) + ']'); t.prune()
    edit_tres(A + 'Moves/32_FLN_6C.tres', six_c, BK, '6C move')
    edit_tres(A + 'States/72_FLN_6C.tres', lambda t: t.res_set('StateName', '"6C"'), BK, '6C state')
    # Oct 25 night: 6C is a launcher (launchers.py; jump-cancel on hit)
    import launchers
    set_hitbox_attack(hb('8_Hitbox_6C_2'), dict(launchers.LAUNCH_FIELDS, SelfHitStopDuration=12, OpponentHitStopDuration=12,
                                                BlockStopDuration=12))
    def walk(v_old, v_new):
        def fn(t):
            for s in t.sub:
                if t.script_of(s[2]).endswith('MoveXAction.cs'):
                    s[2] = [('Velocity = %d' % v_new) if l == 'Velocity = %d' % v_old else l for l in s[2]]
        return fn
    edit_tres(A + 'States/1_FLN_MoveForwardState.tres', walk(32000, 26000), BK, 'walk speed')
    edit_tres(A + 'States/2_FLN_MoveBackwardsState.tres', walk(-21000, -19000), BK, 'walk speed')

def write_states():
    for mk, m in MOVES.items():
        m['anim'] = '%d_%s_%s' % (m['slot'], TAG, mk)
        sres = A + 'States/%d_%s_%s.tres' % (m['slot'], TAG, mk); m['state_res'] = sres
        tick = [ev([at(fr)], [act]) for fr, act in m.get('tick', [])]
        tick += [ev([at_range(a, b)], [act]) for (a, b), act in m.get('tick_ranges', [])]
        trans = list(m.get('transitions', []))
        if m.get('air_land'):          # air moves: land into the landing pose (not before land_from: she has to be up first)
            trans += [ev([at_range(m.get('land_from', 10), 999), on_ground()], [play_state(DP_LAND)]), ev([state_ended()], [play_state(FALLING)])]
        elif m.get('meteor_land'):     # falling punches: the fist hits the floor -> its impact state
            trans += [ev([at_range(m.get('land_from', 10), 999), on_ground()], [play_state(m['meteor_land'])]),
                      ev([state_ended()], [play_state(FALLING)])]
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
    for name, keys in ANIM_FX.items(): man['animations'][name]['keys'] = keys
    hf = man.setdefault('hitfit', {}); hf.setdefault('boxes', {}); hf.setdefault('attack_part', {})
    hf['attack_part'].update({'92_FLN_S1': 'edge', '94_FLN_S2': 'top', '97_FLN_S2_boom': 'trail_all'})
    for k in [k for k in hf['boxes'] if k.startswith('46_Hitbox_BigBangCrash_Dive_')]: del hf['boxes'][k]   # Oct 25: now the rise
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
    todo = anims + list(ANIM_FX)
    if ONLY: todo = [a for a in todo if a in ONLY.split(',')]
    # sprites + timelines
    import build
    p = build.Port(CH)
    for a in todo:
        p.build_anim(a); print('built', a, flush=True)
    # boxes fitted to the drawings
    import hitfit
    f = hitfit.Fitter(CH)
    for line in f.run(todo, write=True, force=FORCE): print('  ', line, flush=True)
    # states
    write_states()
    # moves (inputs are the shared ones)
    for mk, m in list(MOVES.items()) + list(EXTRA_MOVES.items()):
        if 'input' not in m: continue
        m['move_res'] = A + 'Moves/%s.tres' % m['move_file']
    allm = dict(MOVES); allm.update(EXTRA_MOVES)
    order = [allm[k]['move_res'] for k in STANCE_ORDER]
    idx = {k: FIRST_SPECIAL + n for n, k in enumerate(STANCE_ORDER)}
    for mk, m in allm.items():
        if 'input' not in m: continue
        cancels = [cancel(idx[k], c, fr) for k, c, fr in m.get('cancels', [])]
        extra = dict(m.get('move_extra') or {})
        if m.get('skip_check'): extra['SkipCheck'] = True
        mv = Move(m['name'], m['state'] if 'state' in m else m['slot'], input_res(*m['input']), priority=m.get('priority', 7),
                  meter=m.get('meter'), flash=m.get('flash'), ground=m.get('ground', True), air=m.get('air', False), cancels=cancels,
                  extra=extra or None)
        write(m['move_res'], mv, force=FORCE)
    # register: state slots, stance moves, cancels from the normals
    set_state_slots(A + '0_%s_Data.tres' % TAG, {m['slot']: m['state_res'] for m in MOVES.values()})
    set_stance_specials(A + 'Stances/%s_Stance_Main.tres' % TAG, order)
    for n in GROUND_NORMALS + AIR_NORMALS: strip_old_cancels(A + 'Moves/%s.tres' % n)
    for n in GROUND_NORMALS:
        add_cancels(A + 'Moves/%s.tres' % n, [(idx[k], HIT | BLOCK, (0, 999)) for k in GROUND_CANCEL_ORDER], BK)
    for n in AIR_NORMALS:
        if AIR_CANCEL_ORDER: add_cancels(A + 'Moves/%s.tres' % n, [(idx[k], HIT | BLOCK, (0, 999)) for k in AIR_CANCEL_ORDER], BK)
    import launchers; launchers.normals_to_6c(CH, BK)   # Oct 26: every ground normal can cancel into 6C
    patch_normals()
    print('\n'.join(fdk.LOG))
    print('move indices:', idx)

if __name__ == '__main__':
    main()
