"""ASSISTS (Oct 2026): Mary, Adin and Eren, the support characters called with S and 6S
(Dengeki Bunko Fighting Climax style; how the game runs them: engine/sakuga/Components/NetsuAssist.cs).

Everything about them is made from the tables in this file, from the drawings in
Fighting_Game_All_Sprites/Mary, Adin, Eren (see Guides/*_Assist_Sprites_README.txt, Eren/README.txt):
  sprites + animation timelines (build.py), hitbox files, states, the assist character scenes,
  Mary's music-note projectile, the aura Mary's buff puts on her fighter, select-screen icons,
  and data/assist_list.tres (which assists exist, their moves, cooldowns, where they appear).

    python assists.py                 build everything
    python assists.py eren            only one assist
    python assists.py --preview       also write preview reels: checks/assists/<name>_<move>.gif
    python assists.py --force         also overwrite files you changed in Godot (else: SKIPPED)

Units: positions in the tables are game pixels (x forward from the assist's feet, y up; 27.5 units
per px; 10000 units = 1 m). Speeds are units per second (MoveX 150000 = 15 m/s = 2500 units a
frame). Frame numbers count from the start of the state (60 = 1 second).
Tuning in Godot works too: the states, hitboxes and data/assist_list.tres are normal resources.
Files changed there are kept when this script runs again (it says SKIPPED), unless --force.
"""
import sys, os, json, re, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import fdk
from fdk import *

FORCE = '--force' in sys.argv
PREVIEW = '--preview' in sys.argv
UPX = 27.5
LEAVE = 'leave'
SRC_ROOT = 'C:/Users/elvis/Downloads/Fighting_Game_All_Sprites'

def u(px): return int(round(px * UPX))          # game px -> engine units

# --- Netsu frame-data pieces (engine/sakuga/Resources/FrameDataEvents/...) ------------------------
def buff(frames, damage_pct, gauge_pct=100, add_gauge=None):
    return Obj(ACT + 'NetsuAssistBuffAction.cs', Duration=frames, DamagePercent=damage_pct, GaugePercent=gauge_pct, AddGauge=add_gauge)
def aim(target, offset_px, frames, max_speed=None, min_speed=None):
    """X speed that brings the assist to target + offset (px along its facing) in `frames` frames"""
    return Obj(ACT + 'NetsuAimAction.cs', Target=target, OffsetX=u(offset_px), Frames=frames, MaxSpeed=max_speed, MinSpeed=min_speed)
def place(target, x_px, y_px=0, keep_height=True, face_back=None):
    return Obj(ACT + 'NetsuPlaceAction.cs', Target=target, Offset=V2i(u(x_px), u(y_px)), KeepHeight=keep_height, FaceBack=face_back)
def past(target, min_px=None, max_px=None, not_=None):
    """true when the assist is min..max px past the target along its facing (negative = short of it)"""
    return Obj(CON + 'NetsuRelativeXCondition.cs', Target=target, MinDistance=u(min_px) if min_px is not None else None,
               MaxDistance=u(max_px) if max_px is not None else None, Not=not_)
def leave_now(): return [set_active(False), movex(0), movey(0)]

# --- attacks (first pass; tune in play) ------------------------------------------------------------
def hit(damage, hitstun, blockstun, kb, air_kb=None, reaction=1, air_reaction=None, hit_type=MID, stop=10, self_stop=None,
        effect=0, gain=150, kb_gravity=None, air_gravity=None, hitstun_type=BASIC, air_hitstun_type=None, scaling=10, extra=None):
    """an assist's attack: meter goes to its fighter (gain), the assist itself is never pushed back"""
    e = {'AllowSelfPushback': False, 'ChipDamage': 0}
    if self_stop is not None: e['SelfHitStopDuration'] = self_stop
    if extra: e.update(extra)
    return attack(damage, hitstun, blockstun, kb=kb, air_kb=air_kb or kb, reaction=reaction,
                  air_reaction=air_reaction if air_reaction is not None else reaction, hit_type=hit_type, stop=stop,
                  gain=gain, opp_gain=60, effect=effect, kb_gravity=kb_gravity, air_gravity=air_gravity,
                  hitstun_type=hitstun_type, air_hitstun_type=air_hitstun_type, scaling=scaling, extra=e)

# hit reactions (the fighters' stance list): 1 ground strong, 4 air weak, 7 launch away, 8 launch up, 9 spike
EREN_HIT1 = hit(450, 30, 18, kb=(-6000, 30000), reaction=8, stop=9, self_stop=6, effect=5, kb_gravity=220000,
                air_gravity=220000, hit_type=LOW)
EREN_HIT2 = hit(550, 42, 22, kb=(-32000, 30000), reaction=7, stop=13, self_stop=8, effect=6, kb_gravity=220000,
                air_gravity=220000, hit_type=LOW, hitstun_type=HARD_KNOCKDOWN)
EREN_SPIN = hit(250, 24, 16, kb=(-12000, 0), air_kb=(-8000, 22000), reaction=1, air_reaction=4, stop=8, self_stop=5,
                effect=5, hit_type=HIGH, scaling=6)
EREN_RHIT1 = hit(350, 30, 18, kb=(-6000, 30000), reaction=8, stop=9, self_stop=6, effect=5, kb_gravity=220000,
                 air_gravity=220000, hit_type=LOW)
EREN_RHIT2 = hit(450, 42, 22, kb=(-32000, 30000), reaction=7, stop=13, self_stop=8, effect=6, kb_gravity=220000,
                 air_gravity=220000, hit_type=LOW, hitstun_type=HARD_KNOCKDOWN)
ADIN_BASH = hit(900, 52, 24, kb=(-6000, 70000), reaction=8, stop=14, self_stop=10, effect=4, kb_gravity=200000,
                air_gravity=200000, hitstun_type=KNOCKDOWN)
ADIN_RUSH = hit(1000, 60, 26, kb=(-12000, 95000), reaction=8, stop=15, self_stop=10, effect=4, kb_gravity=200000,
                air_gravity=200000, hitstun_type=KNOCKDOWN)
# the counter box: an attack that touches it is absorbed and the attacker freezes while Adin bashes
ADIN_COUNTER = dict(SelfSuperGaugeGain=200, OpponentSuperGaugeGain=0, SelfHitStopDuration=8, OpponentHitStopDuration=24,
                    HitEffectIndex=2, ClashEffectIndex=2)
MARY_BOOM = hit(850, 46, 24, kb=(-15000, 65000), reaction=8, stop=14, self_stop=4, effect=4, kb_gravity=220000,
                air_gravity=220000, hitstun_type=KNOCKDOWN, extra={'HitboxType': PROJECTILE_T})

# ------------------------------------------------------------------------------------------------------
# THE ASSISTS
#   frames:  build.py frame specs (src from the drawings folder; 'scale' 1.0 = drawn like the reference;
#            effects: 'out_h' / 'out_w' = size in game px, 'at' = where their middle goes)
#   states:  in the order of the assist's data (index 0 is always the hidden state).
#            keys = sprite timeline [frame, at, {fx, ...}] (build.py), boxes = [at, stage, kind, spec]
#            kind: 'none' | 'atk' (spec: box px [x0, y0, x1, y1] or 'fx:<frame>' + props) | 'counter'
#            tick = [(frame, action)], ranges = [((first, last), action)], end = LEAVE or a state name
#   moves:   what S / 6S do (data/assist_list.tres): spawn = where it appears (px, x in front of the caller)
# ------------------------------------------------------------------------------------------------------
def fr(src, anchor='ground', **k):
    d = {'src': src, 'anchor': anchor, 'scale': 1.0}; d.update(k); return d
def efx(src, at, out_h=None, out_w=None, flip=None):
    d = {'src': src, 'anchor': 'center', 'at': list(at), 'fx_size': [out_w, out_h]}
    if flip: d['flip'] = True
    return d
def fxk(f): return {'fx': f, 'fx_always': True}
def fxc(f): return {'fx': f}                      # only drawn once the move connects

M = 'Mary/'; MS = M + 'Shared_Character/'
MARY_FRAMES = {
    'my_appear': fr(MS + 'Mary_01_Appear.png'),
    'my_raise': fr(MS + 'Mary_02_Raise_Violin.png'),
    'my_play': fr(MS + 'Mary_03_Play_Stroke_Corrected.png'),
    'my_stroke': fr(MS + 'Mary_04_Stroke_End.png'),
    'my_lower': fr(MS + 'Mary_05_Lower_Violin.png'),
    'my_bow': fr(MS + 'Mary_06_Courtesy_Bow.png'),
    'my_leave': fr(MS + 'Mary_07_Leave.png', 'body_ground'),        # drawn facing back: she walks away
    'my_aura1': efx(M + '5S_Buff_Effects/Mary_01_Aura_Loop.png', (-10, 262), out_h=620),
    'my_aura2': efx(M + '5S_Buff_Effects/Mary_02_Aura_Loop.png', (-10, 262), out_h=620),
    'my_aura3': efx(M + '5S_Buff_Effects/Mary_03_Aura_Loop.png', (-10, 262), out_h=620),
    'my_pulse': efx(M + '5S_Buff_Effects/Mary_04_Apply_Pulse.png', (-10, 262), out_h=620),
    'note_1': efx(M + '6S_Note_Float/Mary_01_Float.png', (0, 0), out_h=150),
    'note_2': efx(M + '6S_Note_Float/Mary_02_Float.png', (0, 0), out_h=140),
    'note_3': efx(M + '6S_Note_Float/Mary_03_Float.png', (0, 0), out_h=145),
    'boom_1': efx(M + '6S_Note_Explosion/Mary_01_Flash.png', (0, 0), out_h=300),
    'boom_2': efx(M + '6S_Note_Explosion/Mary_02_Burst.png', (0, 0), out_h=420),
    'boom_3': efx(M + '6S_Note_Explosion/Mary_03_Fade.png', (0, 0), out_h=430),
}
def play_keys(start, end, aura):
    """Mary playing: bow stroke every 12 frames, the aura (5S) cycling every 4"""
    keys = []
    for i, t in enumerate(range(start, end, 4)):
        pose = 'my_play' if (t - start) // 12 % 2 == 0 else 'my_stroke'
        keys.append([pose, t, fxk('my_aura%d' % (i % 3 + 1))] if aura else [pose, t])
    return keys
MARY_5S_KEYS = [['my_appear', 0], ['my_raise', 6]] + play_keys(14, 50, True) + \
               [['my_stroke', 50, fxk('my_pulse')], ['my_stroke', 54, fxk('my_pulse')], ['my_lower', 60], ['my_bow', 68], ['my_leave', 86]]
MARY_6S_KEYS = [['my_appear', 0], ['my_raise', 6]] + play_keys(14, 38, False) + \
               [['my_lower', 46], ['my_bow', 54], ['my_leave', 72]]

MARY = dict(
    name='Mary', tag='MRY', height_px=505, reference=MS + 'Mary_01_Appear.png', icon=('my_appear', 'hair_teal'),
    frames=MARY_FRAMES,
    description='Violinist. 5S plays a song that powers up her fighter; 6S leaves a floating note that explodes.',
    states=[
        dict(key='5S', name='Encore', duration=104, keys=MARY_5S_KEYS, boxes=[[0, 0, 'none']],
             enter=[movex(0), movey(0)], tick=[(50, buff(480, 115, 125)), (86, movex(-26000))], end=LEAVE),
        dict(key='6S', name='Fermata Note', duration=90, keys=MARY_6S_KEYS, boxes=[[0, 0, 'none']],
             enter=[movex(0), movey(0)], tick=[(26, spawn_actor(0, u(120), u(300), SELF, SELF, initial_state=1)), (72, movex(-26000))],
             end=LEAVE),
    ],
    # Mary's note: its own little actor (actors/assists/mary/Instances/MRY_Note.tscn), spawned by her 6S
    spawnables=dict(note=dict(tag='MRYN', key='MaryNote', pool=1, states=[
        dict(key='Float', name='Fermata Note (floating)', duration=96,
             keys=[['note_%d' % (i % 3 + 1), i * 6] for i in range(16)], boxes=[[0, 0, 'none']],
             enter=[movex(25000), movey(0)],
             tick=[(t, movey(4000 if (t // 24) % 2 == 0 else -4000)) for t in range(0, 96, 24)],
             transitions=[ev([at_range(8, 999), past(OPPONENT, -40, 40)], [play_state(2)]),   # touches the opponent
                          ev([state_ended()], [play_state(2)])]),                                 # or the fuse runs out
        dict(key='Boom', name='Fermata Note (explosion)', duration=28,
             keys=[['boom_1', 0], ['boom_2', 4], ['boom_3', 14]],
             boxes=[[0, 0, 'none'], [2, 1, 'atk', dict(box=[-150, -150, 150, 150], props=MARY_BOOM)], [10, 2, 'none']],
             enter=[movex(0), movey(0), camera_shake(0.03, 10)], end=LEAVE),
    ])),
    moves=[
        dict(name='5S', display='Encore', direction=0, state='5S', spawn=(-430, 0), cooldown=840, ai=(500, 3700),
             desc='Mary plays behind you. When the song peaks you deal 115% damage and gain 125% Craft Gauge for 8 seconds.'),
        dict(name='6S', display='Fermata Note', direction=1, state='6S', spawn=(-380, 0), cooldown=660, ai=(150, 1800), face_caller=True,
             desc='Mary plays a note that floats forward and explodes when it reaches the opponent (or after about 1.5 s). Launches.'),
    ],
    start_cooldown=600,
    buff_aura=['5S_Buff_Effects/Mary_01_Aura_Loop.png', '5S_Buff_Effects/Mary_02_Aura_Loop.png', '5S_Buff_Effects/Mary_03_Aura_Loop.png'],
    buff_pulse='5S_Buff_Effects/Mary_04_Apply_Pulse.png',
)

A = 'Adin/'; AC = A + '5S_Counter/'; AR = A + '6S_Run_Return/'; AE = A + 'Separate_Effects/'
ADIN_FRAMES = {
    'ad_raise': fr(AC + 'Adin_01_Raise.png'),
    'ad_hold': fr(AC + 'Adin_02_Counter_Hold.png'),
    'ad_react': fr(AC + 'Adin_03_Block_React.png'),
    'ad_load': fr(AC + 'Adin_04_Bash_Load.png'),
    'ad_bash': fr(AC + 'Adin_05_Rising_Bash.png'),
    'ad_recover': fr(AC + 'Adin_06_Recovery.png'),
    'ad_run1': fr(AR + 'Adin_01_Run_Right.png', 'body_ground'),
    'ad_run2': fr(AR + 'Adin_02_Run_Right_Passing.png', 'body_ground'),
    # the return run is drawn facing back: mirrored here, the state turns him around instead
    'ad_retload': fr(AR + 'Adin_03_Return_Left_Load.png', 'body_ground', flip=True),
    'ad_ret1': fr(AR + 'Adin_04_Charge_Left_Contact.png', 'body_ground', flip=True),
    'ad_ret2': fr(AR + 'Adin_05_Charge_Left_Passing.png', 'body_ground', flip=True),
    'ad_launch': fr(AR + 'Adin_06_Launch_Bash_Left.png', 'body_ground', flip=True),
    'ad_brake': fr(AR + 'Adin_07_Brake_Left.png', 'ground', flip=True),
    'adfx_block': efx(AE + 'Adin_01_Counter_Block.png', (120, 420), out_h=250),
    'adfx_up': efx(AE + 'Adin_02_Upward_Launch.png', (215, 520), out_h=560),
    'adfx_trail': efx(AE + 'Adin_03_Charge_Trail.png', (-330, 240), out_w=640, flip=True),
    'adfx_fade': efx(AE + 'Adin_04_Launch_Fade.png', (215, 560), out_h=470),
    'adfx_up2': efx(AE + 'Adin_02_Upward_Launch.png', (225, 470), out_h=560),
    'adfx_fade2': efx(AE + 'Adin_04_Launch_Fade.png', (225, 520), out_h=470),
}
def run_keys(a, b, frames, step, fx=None):
    return [[frames[i % len(frames)], t] + ([fxk(fx)] if fx else []) for i, t in enumerate(range(a, b, step))]

ADIN = dict(
    name='Adin', tag='ADN', height_px=535, reference=AC + 'Adin_06_Recovery.png', icon=('ad_recover', 'hair_red'),
    frames=ADIN_FRAMES,
    description='Shield knight. 5S counters the next attack with a rising shield bash; 6S runs off the screen and charges back from the other side.',
    states=[
        dict(key='5S', name='Shield Counter', duration=62, keys=[['ad_raise', 0], ['ad_hold', 8], ['ad_recover', 48]],
             boxes=[[0, 0, 'none'], [8, 1, 'counter', dict(box=[-20, 20, 230, 600], props=ADIN_COUNTER)], [48, 2, 'none']],
             enter=[movex(0), movey(0)], hit_confirm=[ev(None, [play_state(2)])], end=LEAVE),
        dict(key='5S_hit', name='Shield Counter (bash)', duration=56,
             keys=[['ad_react', 0, fxk('adfx_block')], ['ad_load', 8], ['ad_bash', 14, fxc('adfx_up')],
                   ['ad_bash', 22, fxc('adfx_fade')], ['ad_recover', 32]],
             boxes=[[0, 0, 'none'], [14, 1, 'atk', dict(box=[40, 180, 340, 660], props=ADIN_BASH)], [21, 2, 'none']],
             enter=[movex(0), movey(0)], tick=[(14, reset_hit()), (14, camera_shake(0.04, 12))], end=LEAVE),
        dict(key='6S', name='Rush Return (run out)', duration=90, keys=run_keys(0, 90, ['ad_run1', 'ad_run2'], 5),
             boxes=[[0, 0, 'none']], enter=[movex(160000), movey(0)],
             transitions=[ev([past(OPPONENT, 1500)], [play_state(4)]), ev([state_ended()], [play_state(4)])], afterimages=True),
        dict(key='6S_return', name='Rush Return (charge)', duration=90,
             keys=[['ad_retload', 0]] + run_keys(8, 90, ['ad_ret1', 'ad_ret2'], 4, fx='adfx_trail'),
             boxes=[[0, 0, 'none'], [8, 1, 'atk', dict(box=[30, 40, 300, 430], props=ADIN_RUSH)]],
             enter=[movex(0), movey(0), place(OPPONENT, 1900, face_back=True)], tick=[(8, movex(165000))],
             transitions=[ev([at_range(10, 999), past(FIGHTER, 2300)], leave_now()), ev([state_ended()], leave_now())],
             hit_confirm=[ev(None, [play_state(5)])], afterimages=True),
        dict(key='6S_hit', name='Rush Return (launch)', duration=30,
             keys=[['ad_launch', 0, fxk('adfx_up2')], ['ad_launch', 6, fxk('adfx_fade2')], ['ad_brake', 14]],
             boxes=[[0, 2, 'none']], enter=[movex(50000), movey(0)], tick=[(6, movex(20000)), (14, movex(0))], end=LEAVE),
    ],
    moves=[
        dict(name='5S', display='Shield Counter', direction=0, state='5S', spawn=(330, 0), cooldown=540, ai=(0, 420),
             desc='Adin raises his shield in front of you for about 2/3 of a second. An attack that hits the shield is absorbed and he bashes the attacker into the air.'),
        dict(name='6S', display='Rush Return', direction=1, state='6S', spawn=(-220, 0), cooldown=720, ai=(300, 3700),
             desc='Adin runs through and off the screen, then charges back from behind the opponent and launches them high. Block it facing him.'),
    ],
    start_cooldown=600,
)

E = 'Eren/'; E5 = E + '5S/'; E6 = E + '6S/'; EE = E + 'Effects/'
EREN_FRAMES = {
    'er_load': fr(E5 + '01_Load.png'),
    'er_dash': fr(E5 + '02_Dash.png', 'body_ground'),
    'er_hit1': fr(E5 + '03_Low_Horizontal_Hit1.png', 'body_ground'),
    'er_link': fr(E5 + '04_Low_Link.png', 'body_ground'),
    'er_hit2': fr(E5 + '05_Low_Horizontal_Hit2.png', 'body_ground'),
    'er_recover': fr(E5 + '06_Recovery.png'),
    'er_jload': fr(E6 + '01_Jump_Load.png'),
    'er_rise': fr(E6 + '02_Rise.png', 'air'),
    'er_spin1': fr(E6 + '03_Spin_Front.png', 'air'),
    'er_spin2': fr(E6 + '04_Spin_Back.png', 'air'),
    'er_exit': fr(E6 + '05_Spin_Exit.png', 'air'),
    'er_land': fr(E6 + '06_Landing_Left.png', 'ground', flip=True),   # drawn facing back: the state turns him
    'erfx_h1': efx(EE + '5S_Hit1_Horizontal.png', (60, 78), out_w=620),
    'erfx_h2': efx(EE + '5S_Hit2_Horizontal.png', (40, 70), out_w=640),
    'erfx_s1': efx(EE + '6S_Spin_01.png', (0, 300), out_w=470),
    'erfx_s2': efx(EE + '6S_Spin_02.png', (0, 300), out_w=480),
}
def spin_keys(a, b):
    k = []
    for i, t in enumerate(range(a, b, 5)):
        k.append(['er_spin1' if i % 2 == 0 else 'er_spin2', t, fxk('erfx_s1' if i % 2 == 0 else 'erfx_s2')])
    return k
EREN_HITS_KEYS = [['er_hit1', 0, fxk('erfx_h1')], ['er_hit1', 4], ['er_link', 7], ['er_hit2', 12, fxk('erfx_h2')], ['er_hit2', 16],
                  ['er_recover', 24]]
EREN_HIT_TICKS = [(0, movex(25000)), (5, movex(0)), (7, movex(35000)), (12, movex(10000)), (12, reset_hit()), (17, movex(0))]

EREN = dict(
    name='Eren', tag='ERN', height_px=500, reference=E5 + '06_Recovery.png', icon=('er_recover', 'hair_blond'),
    frames=EREN_FRAMES,
    description='Swordsman. 5S dashes in low with two cuts; 6S jumps over the opponent with a spinning slash and comes back the other way.',
    states=[
        dict(key='5S', name='Low Double Slash (start)', duration=6, keys=[['er_load', 0]], boxes=[[0, 0, 'none']],
             enter=[movex(0), movey(0)], end='dash'),
        dict(key='hits', name='Low Double Slash', duration=46, keys=EREN_HITS_KEYS,
             boxes=[[0, 1, 'atk', dict(box='fx:erfx_h1', shrink=(0.12, 0), y=(0, 230), props=EREN_HIT1)], [5, 2, 'none'],
                    [12, 1, 'atk', dict(box='fx:erfx_h2', shrink=(0.12, 0), y=(0, 330), props=EREN_HIT2)], [17, 2, 'none']],
             tick=EREN_HIT_TICKS, end=LEAVE),
        dict(key='6S', name='Falling Spin', duration=90,
             keys=[['er_jload', 0], ['er_rise', 6]] + spin_keys(16, 46) + [['er_exit', 46]],
             boxes=[[0, 0, 'none'], [16, 1, 'atk', dict(box='fx:erfx_s2', shrink=(0.05, 0.1), props=EREN_SPIN)]],
             enter=[movex(0), movey(0)],
             tick=[(6, movey(90000)), (6, aim(OPPONENT, 160, 38, max_speed=260000)), (38, reset_hit()), (44, reset_hit())],
             ranges=[((7, 999), gravity(280000))],
             transitions=[ev([at_range(12, 999), on_ground()], [play_state(4)]), ev([state_ended()], [play_state(4)])]),
        dict(key='6S_land', name='Falling Spin (landing)', duration=10, keys=[['er_land', 0]], boxes=[[0, 0, 'none']],
             enter=[movex(0), movey(0), change_side(True)], end='rdash'),
        dict(key='dash', name='Low Double Slash (dash)', duration=22, keys=[['er_dash', 0]], boxes=[[0, 0, 'none']],
             enter=[movex(150000), movey(0)], afterimages=True,
             transitions=[ev([past(OPPONENT, -260)], [play_state(2)]), ev([state_ended()], [play_state(2)])]),
        dict(key='rdash', name='Falling Spin (dash back)', duration=16, keys=[['er_dash', 0]], boxes=[[0, 0, 'none']],
             enter=[movex(150000), movey(0)], afterimages=True,
             transitions=[ev([past(OPPONENT, -260)], [play_state(7)]), ev([state_ended()], [play_state(7)])]),
        dict(key='rhits', name='Falling Spin (double slash)', duration=46, keys=EREN_HITS_KEYS,
             boxes=[[0, 1, 'atk', dict(box='fx:erfx_h1', shrink=(0.12, 0), y=(0, 230), props=EREN_RHIT1)], [5, 2, 'none'],
                    [12, 1, 'atk', dict(box='fx:erfx_h2', shrink=(0.12, 0), y=(0, 330), props=EREN_RHIT2)], [17, 2, 'none']],
             tick=EREN_HIT_TICKS, end=LEAVE),
    ],
    moves=[
        dict(name='5S', display='Low Double Slash', direction=0, state='5S', spawn=(-300, 0), cooldown=600, ai=(0, 1800),
             desc='Eren dashes in low and cuts twice: the first cut pops the opponent up, the second knocks them down. Block low.'),
        dict(name='6S', display='Falling Spin', direction=1, state='6S', spawn=(-300, 0), cooldown=780, ai=(300, 2000),
             desc='Eren jumps over the opponent with a spinning slash (block high), lands behind them and does the low double slash back the other way.'),
    ],
    start_cooldown=600,
)

# --- HARIE (Oct 24): the drawings come on canvases of different sizes and zoom, so every frame says its own
# scale (measured on her eyes: 1.0 = like 05_Uppercut_Rise) and where one point of the drawing goes:
#   pin = [drawing x, drawing y, game x, game y]  (game px from the assist's position, y up; 'cx' / 'bot' = middle / bottom
#   of the picture).  The trap puddle sits at x 0 on the floor; she crouches behind it and dives in.
HARIE_TRAP_HIT = hit(900, 50, 22, kb=(-5000, 78000), reaction=8, stop=14, self_stop=10, effect=4, kb_gravity=210000,
                     air_gravity=210000, hitstun_type=KNOCKDOWN)
HARIE_WAVE = hit(200, 26, 16, kb=(-20000, 0), air_kb=(-20000, 16000), reaction=1, air_reaction=4, stop=6, effect=0, scaling=6)
HARIE_WAVE_END = hit(400, 44, 20, kb=(-28000, 62000), reaction=8, stop=12, effect=4, kb_gravity=220000, air_gravity=220000,
                     hitstun_type=KNOCKDOWN)
H5 = 'Harie/5S/'; H6 = 'Harie/6S/'; HE = 'Harie/Effects/'; HD = 'derived/assists/harie/'
def hfr(src, scale, pin, **k):
    d = {'src': src, 'anchor': 'center', 'scale': scale, 'pin': list(pin)}; d.update(k); return d
HARIE_FRAMES = {
    'hr_load': hfr(H5 + '01_Dive_Load.png', 1.07, (437, 1400, -170, 0)),        # crouched behind the puddle
    'hr_dive': hfr(H5 + '02_Dive.png', 1.05, (1517, 945, 70, 30)),              # hands first, about to hit the water
    'hr_sub': hfr(H5 + '03_Submerge.png', 1.05, (767, 927, 0, -6)),             # legs sinking into the puddle
    'hr_start': hfr(H5 + '04_Uppercut_Start.png', 1.56, (656, 1170, 0, -6)),    # bursts out, now in her swimsuit
    'hr_rise': hfr(H5 + '05_Uppercut_Rise.png', 1.0, (760, 1420, 85, 10)),
    'hr_apex': hfr(H5 + '06_Uppercut_Apex.png', 1.0, (760, 1420, 85, 10)),     # same canvas as 05: same placement
    'hrfx_pud1': dict(hfr(HE + '5S_Puddle_01.png', 1.0, (887, 742, 0, -6)), fx_size=[292, None]),
    'hrfx_pud2': dict(hfr(HE + '5S_Puddle_02.png', 1.0, (899, 707, 0, -6)), fx_size=[284, None]),
    'hrfx_splash': hfr(HE + '5S_Trigger_Splash.png', 1.0, (760, 1420, 85, 10)),
    'hrfx_vanish': hfr(HE + '5S_Air_Vanish.png', 1.0, (760, 1420, 85, 10)),
    # 6S: Harie swimming INSIDE the wave (made by derive_harie from the wave and swim drawings: the wave behind her,
    # then the same wave again, see-through, in front of her)
    'hr_wave1': hfr(HD + 'wave_swim_1.png', 'BASE', ('cx', 'bot', 0, -10)),
    'hr_wave2': hfr(HD + 'wave_swim_2.png', 'BASE', ('cx', 'bot', 0, -10)),
}
HARIE_WAVE_W = 820            # game px, the wave's width
HARIE_SWIM = [('Effects/6S_Wave_01.png', '6S/01_Swim.png', 1.28, (1145.5, 286)),   # wave, swimmer, swimmer scale, eyes (drawing px)
              ('Effects/6S_Wave_02.png', '6S/02_Swim.png', 1.22, (1294.5, 342))]
def derive_harie(port):
    """the two 6S pictures: Harie inside the wave, at game size (so build.py doesn't resize them again)"""
    import numpy as np
    from PIL import Image
    out = os.path.join(HERE, 'derived', 'assists', 'harie'); os.makedirs(out, exist_ok=True)
    def pm(img):
        f = np.asarray(img.convert('RGBA')).astype(np.float32) / 255; f[..., :3] *= f[..., 3:4]; return f
    def resize(img, k):
        f = pm(img); nw, nh = int(round(img.width * k)), int(round(img.height * k))
        ch = [np.array(Image.fromarray(f[..., c]).resize((nw, nh), Image.LANCZOS)) for c in range(4)]
        o = np.clip(np.dstack(ch), 0, 1); o[..., :3] = np.minimum(o[..., :3], o[..., 3:4]); return o
    def over(dst, src, x, y, alpha=None):
        s = src * alpha[..., None] if alpha is not None else src
        H_, W_ = dst.shape[:2]; h, w = s.shape[:2]
        sx0, sy0 = max(0, -x), max(0, -y); dx0, dy0 = max(0, x), max(0, y)
        w_, h_ = min(w - sx0, W_ - dx0), min(h - sy0, H_ - dy0)
        if w_ <= 0 or h_ <= 0: return
        s = s[sy0:sy0 + h_, sx0:sx0 + w_]; d = dst[dy0:dy0 + h_, dx0:dx0 + w_]; d[:] = s + d * (1 - s[..., 3:4])
    for i, (wf, sf, ss, eyes) in enumerate(HARIE_SWIM):
        wimg = Image.open(os.path.join(port.root, 'Harie', wf)); al = np.asarray(wimg.convert('RGBA'))[..., 3]
        ys, xs = np.nonzero(al > 20); W = resize(wimg, HARIE_WAVE_W / (xs.max() - xs.min() + 1))
        kh = port.BASE / ss; H = resize(Image.open(os.path.join(port.root, 'Harie', sf)), kh)
        ys, xs = np.nonzero(W[..., 3] > 0.08); wx0, wy0, wx1, wy1 = xs.min(), ys.min(), xs.max(), ys.max()
        tx, ty = wx0 + 0.80 * (wx1 - wx0), wy0 + 0.42 * (wy1 - wy0)          # where her eyes go inside the wave
        hx, hy = int(round(tx - eyes[0] * kh)), int(round(ty - eyes[1] * kh))
        pad = 400; C = np.zeros((W.shape[0] + 2 * pad, W.shape[1] + 2 * pad, 4), np.float32)
        over(C, W, pad, pad); over(C, H, pad + hx, pad + hy)
        rgb = np.where(W[..., 3:4] > 1e-4, W[..., :3] / np.maximum(W[..., 3:4], 1e-4), 0)
        white = np.clip((rgb.min(axis=2) - 0.55) / 0.4, 0, 1)                 # foam stays more solid in front of her
        yy, xx = np.mgrid[0:W.shape[0], 0:W.shape[1]]
        face = np.exp(-(((xx - tx) ** 2 + (yy - ty) ** 2) / (2 * 45.0 ** 2)))  # and her face stays readable
        over(C, W, pad, pad, alpha=(0.24 + 0.5 * white) * (1 - 0.75 * face))
        ys, xs = np.nonzero(C[..., 3] > 0.01)
        C = C[max(0, ys.min() - 2):ys.max() + 3, max(0, xs.min() - 2):xs.max() + 3]
        rgb = np.where(C[..., 3:4] > 1e-4, C[..., :3] / np.maximum(C[..., 3:4], 1e-4), 0)
        img = Image.fromarray((np.clip(np.dstack([rgb, C[..., 3:4]]), 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA')
        img.save(os.path.join(out, 'wave_swim_%d.png' % (i + 1)))
def wave_keys(a, b, step=6):
    return [['hr_wave1' if i % 2 == 0 else 'hr_wave2', t] for i, t in enumerate(range(a, b, step))]
def puddle_keys(a, b, step=12):
    return [['hrfx_pud1' if i % 2 == 0 else 'hrfx_pud2', t] for i, t in enumerate(range(a, b, step))]
HARIE_WAVE_BOX = [-200, 0, 390, 320]

HARIE = dict(
    name='Harie', tag='HRE', height_px=520, base=0.37, reference=H5 + '05_Uppercut_Rise.png', icon=('hr_load', 'box', (655, 280, 345)),
    frames=HARIE_FRAMES, derive=derive_harie, source_dirs=['Harie/5S'],
    description='Swimmer. 5S hides in a magic puddle that bursts into a rising uppercut; 6S rides a wave across the screen.',
    states=[
        dict(key='5S', name='Puddle Trap (dive)', duration=26, keys=[['hr_load', 0], ['hr_dive', 7], ['hr_sub', 14]],
             boxes=[[0, 0, 'none']], enter=[movex(0), movey(0)], end='trap'),
        dict(key='trap', name='Puddle Trap (waiting)', duration=240, keys=puddle_keys(0, 240), boxes=[[0, 0, 'none']],
             enter=[movex(0), movey(0)],
             transitions=[ev([at_range(12, 999), past(OPPONENT, -110, 110)], [play_state(3)])],   # the opponent steps on it
             end='up'),                                                                            # or the time runs out
        dict(key='up', name='Puddle Trap (uppercut)', duration=44,
             keys=[['hrfx_splash', 0], ['hr_start', 3], ['hr_rise', 8], ['hr_apex', 18], ['hrfx_vanish', 28]],   # the water bursts, she comes out of it
             boxes=[[0, 0, 'none'], [3, 1, 'atk', dict(box=[-150, 0, 170, 470], props=HARIE_TRAP_HIT)], [16, 2, 'none']],
             enter=[movex(0), movey(0), camera_shake(0.02, 6)], tick=[(7, movey(75000)), (28, movey(0))],
             ranges=[((8, 27), gravity(230000))], end=LEAVE),
        dict(key='6S', name='Swimming Wave', duration=150, keys=wave_keys(0, 150),
             boxes=[[0, 1, 'atk', dict(box=HARIE_WAVE_BOX, props=HARIE_WAVE)]], enter=[movex(75000), movey(0)],
             transitions=[ev([past(OPPONENT, 1100)], leave_now())], hit_confirm=[ev(None, [play_state(5)])], end=LEAVE),
        dict(key='6S_carry', name='Swimming Wave (carry)', duration=120, keys=wave_keys(0, 120),
             boxes=[[0, 1, 'atk', dict(box=HARIE_WAVE_BOX, props=HARIE_WAVE)], [16, 1, 'atk', dict(box=HARIE_WAVE_BOX, props=HARIE_WAVE_END)],
                    [22, 2, 'none']],
             enter=[movex(65000), movey(0)], tick=[(5, reset_hit()), (10, reset_hit()), (16, reset_hit())],
             transitions=[ev([at_range(22, 999), past(OPPONENT, 1100)], leave_now())], end=LEAVE),
    ],
    moves=[
        dict(name='5S', display='Puddle Trap', direction=0, state='5S', spawn=(300, 0), cooldown=720, ai=(0, 1100),
             reel=dict(opp=800, walk=-150),
             desc='Harie dives into a magic puddle in front of you. When the opponent steps on it (or after 4 seconds) she bursts out with a rising uppercut that launches.'),
        dict(name='6S', display='Swimming Wave', direction=1, state='6S', spawn=(-650, 0), cooldown=780, ai=(300, 3700),
             desc='A wave sweeps across the screen from behind you with Harie swimming inside it: 4 hits that carry the opponent along, the last one launches.'),
    ],
    start_cooldown=600,
)

ASSISTS = {'mary': MARY, 'adin': ADIN, 'eren': EREN, 'harie': HARIE}
ORDER = ['mary', 'adin', 'eren', 'harie']      # order on the character select / in data/assist_list.tres (keep: picks are saved by number)

# ------------------------------------------------------------------------------------------------------
# building
# ------------------------------------------------------------------------------------------------------
def char_of(k): return 'assists/' + k
def base(k): return 'res://actors/assists/%s/' % k

def state_list(k, a):
    """[(index, tag, state dict, owner)] for the assist and its spawnables"""
    out = []
    for i, s in enumerate(a['states']): out.append((i + 1, a['tag'], s, 'main'))
    for sk, sp in a.get('spawnables', {}).items():
        for i, s in enumerate(sp['states']): out.append((i + 1, sp['tag'], s, sk))
    return out

def anim_name(idx, tag, s): return '%d_%s_%s' % (idx, tag, s['key'])

def fx_scale(port, spec):
    """'fx_size' [w, h] in game px -> build.py 'scale' (drawing px per reference px)"""
    w, h = spec.pop('fx_size', [None, None])
    if w is None and h is None: return
    import numpy as np
    from PIL import Image
    img = np.array(Image.open(os.path.join(port.root, spec['src'])).convert('RGBA'))[:, :, 3]
    ys, xs = np.nonzero(img > 20)
    bw, bh = xs.max() - xs.min() + 1, ys.max() - ys.min() + 1
    k = (w / bw) if w else (h / bh)          # output px per drawing px
    spec['scale'] = round(port.BASE / k, 5)

def pin_place(port, spec):
    """'pin' [drawing x, drawing y, game x, game y] -> the 'center' anchor's 'at' (x/y may be 'cx' / 'cy' / 'bot':
    the middle / bottom of the picture); 'scale' 'BASE' = the picture is already at game size"""
    import numpy as np
    from PIL import Image
    if spec.get('scale') == 'BASE': spec['scale'] = port.BASE
    if 'pin' not in spec: return
    px, py, bx, by = spec.pop('pin')
    path = os.path.join(HERE, spec['src']) if spec['src'].startswith('derived/') else os.path.join(port.root, spec['src'])
    img = Image.open(path).convert('RGBA'); w, h = img.size
    al = np.asarray(img)[:, :, 3]; ys, xs = np.nonzero(al > 20)
    if px == 'cx': px = (xs.min() + xs.max()) / 2.0
    elif spec.get('flip'): px = w - 1 - px
    if py == 'cy': py = (ys.min() + ys.max()) / 2.0
    elif py == 'bot': py = float(ys.max())
    k = port.BASE / float(spec['scale'])
    spec['anchor'] = 'center'
    spec['at'] = [round(bx - (px - w / 2.0) * k, 2), round(by - (h / 2.0 - py) * k, 2)]

def write_manifest(k, a):
    path = os.path.join(HERE, 'manifests', 'assists', k + '.json')
    m = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    m.update({'character': char_of(k), 'tag': a['tag'], 'source_root': SRC_ROOT, 'source_root_device': '~/mnt/Fighting_Game_All_Sprites',
              'reference': a['reference'], 'fx': 'none', 'head_frac': 0.23,
              'game': {'height_px': a['height_px'], 'pixel_size': 0.00275, 'sprites_subdir': 'v2', 'origin_from_rear': 0.5}})
    if a.get('base'): m['game']['base'] = a['base']
    m['source_dirs'] = a.get('source_dirs') or m.get('source_dirs') or [os.path.dirname(a['reference'])]
    frames = json.loads(json.dumps(a['frames']))
    anims = {}
    for idx, tag, s, owner in state_list(k, a):
        name = anim_name(idx, tag, s)
        anims[name] = {'keys': s['keys'], 'duration': s['duration'], 'hitboxes': [[b[0], b[1], hb_name(idx, tag, s, n)] for n, b in enumerate(s['boxes'])]}
        if s.get('afterimages'): anims[name]['afterimages'] = True
    anims['0_%s_Hidden' % a['tag']] = {'keys': [[a['states'][0]['keys'][0][0], 0]], 'duration': 1, 'hitboxes': []}
    m['frames'] = frames; m['animations'] = anims
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(m, open(path, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    return m

def hb_name(idx, tag, s, n): return '%d_Hitbox_%s_%s_%d' % (idx, tag, s['key'], n)

def box_px(port, spec):
    b = spec['box']
    if isinstance(b, str) and b.startswith('fx:'):
        crop, off, info = port.frame(b[3:])
        x0, y0 = off; x1, y1 = off[0] + crop.shape[1], off[1] + crop.shape[0]
        sx, sy = spec.get('shrink', (0.1, 0.1))
        dx, dy = (x1 - x0) * sx, (y1 - y0) * sy
        return [x0 + dx, y0 + dy, x1 - dx, y1 - dy]
    return list(b)

def box_final(port, spec):
    b = box_px(port, spec)
    if 'x' in spec: b[0], b[2] = spec['x']
    if 'y' in spec: b[1], b[3] = spec['y']
    return b

def write_hitboxes(k, a, port):
    for idx, tag, s, owner in state_list(k, a):
        for n, b in enumerate(s['boxes']):
            at, stage, kind = b[0], b[1], b[2]; spec = b[3] if len(b) > 3 else None
            els = []
            if kind == 'atk':
                x0, y0, x1, y1 = box_final(port, spec)
                els.append(box(HIT_T, x0, y0, x1, y1, **spec['props']))
            elif kind == 'counter':
                x0, y0, x1, y1 = box_final(port, spec)
                els.append(box(COUNTER, x0, y0, x1, y1, **spec['props']))
            write(base(k) + 'Hitboxes/%s.tres' % hb_name(idx, tag, s, n), Hitboxes(els, None), force=FORCE)

def ensure_anim_files(k, a):
    """AnimationData files must exist before build.py fills them in (timeline, boxes, duration)"""
    names = [anim_name(i, t, s) for i, t, s, o in state_list(k, a)] + ['0_%s_Hidden' % a['tag']]
    for n in names:
        res = base(k) + 'AnimationData/%s_AnimData.tres' % n
        if not os.path.exists(res_file(res)):
            write(res, AnimData(1, []), force=True)
    return names

def state_obj(k, a, idx, tag, s, owner):
    sl = state_list(k, a)
    index_of = {(o, st['key']): i for i, t, st, o in sl}
    tick = [ev([at(f)], [act]) for f, act in s.get('tick', [])]
    tick += [ev([at_range(r0, r1)], [act]) for (r0, r1), act in s.get('ranges', [])]
    trans = list(s.get('transitions', []))
    end = s.get('end')
    if end == LEAVE: trans.append(ev([state_ended()], leave_now()))
    elif end: trans.append(ev([state_ended()], [play_state(index_of[(owner, end)])]))
    return State(s['name'], COMBAT, base(k) + 'AnimationData/%s_AnimData.tres' % anim_name(idx, tag, s), transitions=trans,
                 enter=s.get('enter', ()), tick=tick, exit=s.get('exit', ()), hit_confirm=s.get('hit_confirm', ()))

def write_states(k, a):
    sres = {}
    for idx, tag, s, owner in state_list(k, a):
        res = base(k) + 'States/%d_%s_%s.tres' % (idx, tag, s['key'])
        write(res, state_obj(k, a, idx, tag, s, owner), force=FORCE)
        sres.setdefault(owner, {})[idx] = res
    # the hidden state (index 0) of the assist and each spawnable
    for owner, tag in [('main', a['tag'])] + [(sk, sp['tag']) for sk, sp in a.get('spawnables', {}).items()]:
        res = base(k) + 'States/0_%s_Hidden.tres' % tag
        write(res, State('Hidden', 0, base(k) + 'AnimationData/0_%s_Hidden_AnimData.tres' % a['tag']), force=FORCE)
        sres.setdefault(owner, {})[0] = res
    return sres

def write_data(k, a, sres):
    out = {}
    for owner, tag in [('main', a['tag'])] + [(sk, sp['tag']) for sk, sp in a.get('spawnables', {}).items()]:
        states = sres[owner]
        res = base(k) + '0_%s_Data.tres' % tag
        write(res, Obj(SR + 'DataContainer.cs', States=[Ext(states[i]) for i in sorted(states)], BaseAttack=100, BaseDefense=100), force=FORCE)
        out[owner] = res
    return out

SCRIPTS = {'actor': 'res://engine/sakuga/Components/SakugaActor.cs', 'viewer': 'res://engine/sakuga/Components/AnimationViewer.cs',
           'sound': 'res://engine/sakuga/Components/SoundQueue.cs', 'body': 'res://engine/sakuga/Collision/PhysicsBody.cs',
           'states': 'res://engine/sakuga/Components/StateManager.cs', 'params': 'res://engine/sakuga/Components/SakugaParameters.cs',
           'timer': 'res://engine/sakuga/Components/FrameTimer.cs', 'pool': 'res://engine/sakuga/Components/ObjectPool.cs'}
SHADOW = 'res://actors/_shared/sakuga/Sprites/shadow_blob.png'
VIEWER = 'res://engine/ui/instances/HitboxViewer.tscn'
SFX, VOICES = 'res://actors/_shared/sakuga/Shared_SFXList.tres', 'res://actors/_shared/sakuga/Shared_VoiceLines.tres'

def scene_text(node_name, data_res, first_tex, first_off, uid, shadow=True, spawnables=None, layers=2):
    ext = []; ids = {}
    def add(kind, res, uid_=None):
        i = str(len(ext) + 1); ids[res] = i
        u_ = uid_ if uid_ is not None else (script_uid(res) if kind == 'Script' else res_uid(res))
        ext.append('[ext_resource type="%s"%s path="%s" id="%s"]' % (kind, ' uid="%s"' % u_ if u_ else '', res, i)); return i
    s_actor = add('Script', SCRIPTS['actor']); d = add('Resource', data_res); sfx = add('Resource', SFX); vo = add('Resource', VOICES)
    s_view = add('Script', SCRIPTS['viewer']); tex = add('Texture2D', first_tex, '')
    shd = add('Texture2D', SHADOW) if shadow else None
    s_snd = add('Script', SCRIPTS['sound']); hv = add('PackedScene', VIEWER); s_body = add('Script', SCRIPTS['body'])
    s_st = add('Script', SCRIPTS['states']); s_par = add('Script', SCRIPTS['params']); s_tim = add('Script', SCRIPTS['timer'])
    s_pool = add('Script', SCRIPTS['pool']) if spawnables else None
    spw = add('Resource', spawnables) if spawnables else None
    paths = ['Body', 'Parameters', 'StateManager'] + (['Pool'] if spawnables else []) + ['Animator', 'Graphics', 'Hitstop', 'Hitstun', 'Knockback', 'Bounce']
    actor_uid = script_uid(SCRIPTS['actor'])
    L = ['[gd_scene format=3 uid="%s"]' % uid, ''] + ext + ['']
    L += ['[node name="%s" type="Node" node_paths=PackedStringArray(%s)]' % (node_name, ', '.join('"%s"' % p for p in paths)),
          'process_mode = 4', 'script = ExtResource("%s")' % s_actor, 'Body = NodePath("Body")', 'Parameters = NodePath("Parameters")',
          'StateManager = NodePath("StateManager")'] + (['Pool = NodePath("Pool")'] if spawnables else []) + \
         ['AllowHit = 4', 'Animator = NodePath("Graphics/Mesh")', 'Graphics = [NodePath("Graphics")]', 'Data = ExtResource("%s")' % d] + \
         (['SpawnablesList = ExtResource("%s")' % spw] if spawnables else []) + \
         ['SFXList = ExtResource("%s")' % sfx, 'VoiceLines = ExtResource("%s")' % vo, 'Hitstop = NodePath("Parameters/Timers/Hitstop")',
          'Hitstun = NodePath("Parameters/Timers/Hitstun")', 'Knockback = NodePath("Parameters/Timers/Knockback")',
          'Bounce = NodePath("Parameters/Timers/Bounce")', 'metadata/_custom_type_script = "%s"' % actor_uid, '']
    L += ['[node name="Graphics" type="Node3D" parent="."]', 'process_mode = 3', '']
    sprites = ['Sprite'] + ['FX'] + (['FX2'] if layers > 2 else [])
    L += ['[node name="Mesh" type="Node3D" parent="Graphics" node_paths=PackedStringArray("Sprites"%s)]' % (', "Shadow"' if shadow else ''),
          'script = ExtResource("%s")' % s_view, 'Sprites = [%s]' % ', '.join('NodePath("%s")' % n for n in sprites)] + \
         (['Shadow = NodePath("Shadow")'] if shadow else []) + ['AfterimageTint = Color(0.75, 0.95, 1, 1)', '']
    L += ['[node name="Sprite" type="Sprite3D" parent="Graphics/Mesh"]', 'layers = 2', 'centered = false',
          'offset = Vector2(%d, %d)' % first_off, 'pixel_size = 0.00275', 'texture_filter = 3', 'texture = ExtResource("%s")' % tex, '']
    for n in sprites[1:]:
        L += ['[node name="%s" type="Sprite3D" parent="Graphics/Mesh"]' % n, 'visible = false', 'layers = 2', 'centered = false',
              'pixel_size = 0.00275', 'texture_filter = 3', '']
    if shadow:
        L += ['[node name="Shadow" type="Sprite3D" parent="Graphics/Mesh"]',
              'transform = Transform3D(1.3895386, 0, 0, 0, 0.9925276, 0, 0, 0, 0.7940222, 0, 0.001, 0)', 'sorting_offset = -10.0',
              'modulate = Color(1, 1, 1, 0.7058824)', 'pixel_size = 0.022', 'axis = 1', 'texture_filter = 0', 'texture = ExtResource("%s")' % shd, '']
    L += ['[node name="Sounds" type="Node3D" parent="Graphics"]', '', '[node name="SFX_0" type="AudioStreamPlayer3D" parent="Graphics/Sounds"]',
          'script = ExtResource("%s")' % s_snd, '']
    L += ['[node name="HitboxViewer" parent="." node_paths=PackedStringArray("body") instance=ExtResource("%s")]' % hv, 'process_mode = 3',
          'body = NodePath("../Body")', '']
    L += ['[node name="Body" type="Node" parent="."]', 'script = ExtResource("%s")' % s_body, 'StayOnBounds = true', 'IgnoreWalls = true',
          'HitboxesLimit = 8', 'metadata/_custom_type_script = "%s"' % script_uid(SCRIPTS['body']), '']
    L += ['[node name="StateManager" type="Node" parent="."]', 'script = ExtResource("%s")' % s_st,
          'metadata/_custom_type_script = "%s"' % script_uid(SCRIPTS['states']), '']
    if spawnables:
        L += ['[node name="Pool" type="Node" parent="."]', 'script = ExtResource("%s")' % s_pool,
              'metadata/_custom_type_script = "%s"' % script_uid(SCRIPTS['pool']), '']
    L += ['[node name="Parameters" type="Node" parent="." node_paths=PackedStringArray("Timers", "Variables", "SoundSources")]',
          'script = ExtResource("%s")' % s_par,
          'Timers = [NodePath("Timers/Hitstop"), NodePath("Timers/Hitstun"), NodePath("Timers/Knockback"), NodePath("Timers/Bounce")]',
          'Variables = []', 'SoundSources = [NodePath("../Graphics/Sounds/SFX_0")]',
          'metadata/_custom_type_script = "%s"' % script_uid(SCRIPTS['params']), '', '[node name="Timers" type="Node" parent="Parameters"]', '']
    for n, manual in [('Hitstop', True), ('Hitstun', True), ('Knockback', False), ('Bounce', False)]:
        L += ['[node name="%s" type="Node" parent="Parameters/Timers"]' % n, 'script = ExtResource("%s")' % s_tim] + \
             (['Manual = true'] if manual else []) + ['metadata/_custom_type_script = "%s"' % script_uid(SCRIPTS['timer']), '']
    return '\n'.join(L)

def write_scenes(k, a, data, port):
    out = {}
    first = a['states'][0]['keys'][0][0]
    crop, off, info = port.frame(first)
    spw_res = None
    for sk, sp in a.get('spawnables', {}).items():
        sres = base(k) + 'Instances/%s.tscn' % ({'note': 'MRY_Note'}.get(sk, sp['tag'] + '_' + sk))
        f0 = sp['states'][0]['keys'][0][0]; c0, o0, _ = port.frame(f0)
        txt = scene_text(sp['tag'] + '_' + sp['key'], data[sk], port.res_dir + '/' + f0 + '.png', o0, res_uid(sres) or new_uid(), shadow=False)
        write_text(sres, txt, force=FORCE)
        spw_res = base(k) + '%s_SpawnablesList.tres' % a['tag']
        write(spw_res, Obj(SR + 'SpawnsList.cs', SpawnObjects=[Obj(SR + 'SpawnObject.cs', Key=sp['key'], Instance=Ext(sres, 'PackedScene'), PoolSize=sp['pool'])]),
              force=FORCE)
    res = base(k) + 'Instances/%s_Assist.tscn' % a['tag']
    txt = scene_text(a['tag'] + '_Assist', data['main'], port.res_dir + '/' + first + '.png', off, res_uid(res) or new_uid(), spawnables=spw_res)
    write_text(res, txt, force=FORCE)
    out['main'] = res
    return out

IMPORT_TMPL = None
def save_png(img, res):
    """a picture the game uses directly (icons, the buff aura), with mipmaps for smooth scaling"""
    import build
    path = res_file(res); os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
    imp = path + '.import'
    if not os.path.exists(imp): open(imp, 'w').write(build.IMPORT % res)

def write_art(k, a, port):
    """icon (head shot) for the select screen / HUD, and the buff aura textures"""
    from PIL import Image
    import numpy as np
    art = base(k) + 'Artwork/'
    fid, hair = a['icon'][:2]
    spec = port.m['frames'][fid]
    src = Image.open(os.path.join(port.root, spec['src'])).convert('RGBA')
    if spec.get('flip'): src = src.transpose(Image.FLIP_LEFT_RIGHT)
    if hair == 'box':                           # icon=(frame, 'box', (x, y, size)): a square cut from the drawing
        x0, y0, side = a['icon'][2]
        save_png(src.crop((x0, y0, x0 + side, y0 + side)).resize((256, 256), Image.LANCZOS), art + 'Icon.png')
        return art + 'Icon.png'
    arr = np.array(src)
    r, g, b, al = [arr[:, :, i].astype(int) for i in range(4)]
    if hair == 'hair_red': m = (r > 150) & (g < 90) & (b < 80) & (r - g > 90)
    elif hair == 'hair_blond': m = (r > 200) & (g > 140) & (g < 215) & (b < 120) & (r - b > 110)
    else: m = (g > 140) & (b > 120) & (r < 170) & (g - r > 25)
    solid = al > 200; m &= solid
    sy, sx = np.nonzero(solid); top_body, h_body = sy.min(), sy.max() - sy.min()
    ys, xs = np.nonzero(m[: top_body + int(h_body * 0.14)])          # the crown of the head
    if len(xs) == 0: ys, xs = sy[sy < top_body + h_body * 0.14], sx[sy < top_body + h_body * 0.14]
    cx = int(np.median(xs)); top = int(ys.min())
    side = int(h_body * 0.25)
    y0 = max(0, top - side // 10)
    head = src.crop((cx - side // 2, y0, cx + side // 2, y0 + side)).resize((256, 256), Image.LANCZOS)
    save_png(head, art + 'Icon.png')
    if a.get('buff_aura'):
        srcs = a['buff_aura'] + [a['buff_pulse']]
        root = port.root
        imgs = [Image.open(os.path.join(root, 'Mary', s)).convert('RGBA') for s in srcs]
        # all four share one canvas size: scale them alike so one offset fits every picture
        al = np.array(imgs[0])[:, :, 3]; ys, xs = np.nonzero(al > 20)
        k_ = 640.0 / (ys.max() - ys.min() + 1)
        size = (int(imgs[0].width * k_), int(imgs[0].height * k_))
        names = ['BuffAura_1.png', 'BuffAura_2.png', 'BuffAura_3.png', 'BuffPulse.png']
        for img, n in zip(imgs, names): save_png(img.resize(size, Image.LANCZOS), art + n)
        bottom = (imgs[0].height - 1 - ys.max()) * k_
        a['_aura_offset'] = (-size[0] / 2.0, -bottom - 8)
        a['_aura_files'] = [art + n for n in names]
    return art + 'Icon.png'

def write_assist_list(entries):
    els = []
    for k in ORDER:
        if k not in entries: continue
        a, scene, icon = entries[k]
        sl = {st['key']: i for i, t, st, o in state_list(k, a) if o == 'main'}
        moves = [Obj(SR + 'NetsuAssistMove.cs', MoveName=m['name'], DisplayName=m['display'], Direction=m['direction'] or None,
                     StateIndex=sl[m['state']], SpawnOffset=V2i(u(m['spawn'][0]), u(m['spawn'][1])), OnGround=True,
                     Cooldown=m['cooldown'], AIRange=V2i(u(m['ai'][0]), u(m['ai'][1])), Description=m['desc'],
                     NetsuFaceCaller=m.get('face_caller') or None) for m in a['moves']]
        f = dict(AssistName=a['name'], Instance=Ext(scene, 'PackedScene'), Icon=Ext(icon, 'Texture2D'), Moves=moves,
                 StartingCooldown=a['start_cooldown'], MaxOnScreen=600, Description=a['description'])
        if a.get('_aura_files'):
            f['BuffAura'] = [Ext(r, 'Texture2D') for r in a['_aura_files'][:3]]
            f['BuffPulse'] = Ext(a['_aura_files'][3], 'Texture2D')
            f['BuffAuraOffset'] = V2(*a['_aura_offset'])
            f['BuffAuraTint'] = Raw('Color(1, 1, 1, 0.8)')
        els.append(Obj(SR + 'NetsuAssistElement.cs', **f))
    write('res://data/assist_list.tres', Obj(SR + 'NetsuAssistList.cs', Assists=els), force=True)

def build_one(k):
    import build
    a = ASSISTS[k]
    # 1. manifest (frames + timelines); effect sizes -> scales
    write_manifest(k, a)
    if not os.path.exists(os.path.join(HERE, 'analysis', char_of(k) + '.json')):
        import analyze
        analyze.main(char_of(k))                  # measures the drawings once (the reference's size is what's used)
    port = build.Port(char_of(k))
    if a.get('derive'): a['derive'](port)         # pictures made from the drawings by script (derived/)
    for fid, spec in port.m['frames'].items():
        if 'fx_size' in spec: fx_scale(port, spec)
        pin_place(port, spec)
    json.dump(port.m, open(os.path.join(HERE, 'manifests', 'assists', k + '.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    port = build.Port(char_of(k))
    # 2. hitboxes, 3. animation data + sprites
    write_hitboxes(k, a, port)
    for n in ensure_anim_files(k, a):
        port.build_anim(n); print('built', k, n)
    # 4. states, data, scenes, pictures
    sres = write_states(k, a)
    data = write_data(k, a, sres)
    scenes = write_scenes(k, a, data, port)
    icon = write_art(k, a, port)
    return a, scenes['main'], icon

def main():
    names = [n for n in sys.argv[1:] if not n.startswith('--')] or ORDER
    entries = {}
    for k in ORDER:
        if k in names: entries[k] = build_one(k)
        else:
            # keep the others in the list as they are (their files already exist)
            a = ASSISTS[k]
            scene = base(k) + 'Instances/%s_Assist.tscn' % a['tag']
            if os.path.exists(res_file(scene)):
                import build
                port = build.Port(char_of(k)); write_art(k, a, port)
                entries[k] = (a, scene, base(k) + 'Artwork/Icon.png')
    write_assist_list(entries)
    print('\n'.join(fdk.LOG))
    if PREVIEW:
        import assistreel
        for k in names: assistreel.reel_all(k)

if __name__ == '__main__':
    main()
