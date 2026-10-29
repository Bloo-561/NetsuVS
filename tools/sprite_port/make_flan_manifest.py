# One-off helper that wrote manifests/flan.json (frames + the standard animations) on Oct 24, from
# Fighting_Game_All_Sprites/Flan_All_Sprites (see its COMMAND_LIST.md and the pack READMEs).
# Edit the JSON directly from now on (re-running this rewrites the entries it makes in "frames", "animations" and "hitfit").
# Her specials and supers (and their effect layers) are added to the JSON by moves_flan.py.
#
# Scales (drawing px per reference px, reference = 02_Basics/Idle_Reference.png), from head matches and the
# packs' own preview GIFs (every pack draws its poses at one scale):
#   01 idles 1.226 | 02 basics, 03 low normals, 04 air normals 1.0 | 05 236 1.078 | 06/07 623 1.0 | 08 214 0.73
#   09 236236 0.69 (grounded anchor 450,700) | 10 214214 0.745 (grounded anchor 450,760)
# Placement: the 02/03/01 drawings are centred on their canvases by bounding box (not registered), so each
# pose is anchored by its own feet; 04 air normals are registered on the waist (480,440); 09/10 on their anchors.
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, 'manifests', 'flan.json')
m = json.load(open(P, encoding='utf-8'))
m['fx'] = 'radiant'     # her golden energy (soft glow); her yellow frills are opaque and don't count
m['game'] = {'height_px': 490, 'base': 0.95331, 'pixel_size': 0.00275, 'sprites_subdir': 'v2', 'origin_from_rear': 0.5}
# base = 490 / 514: Idle_Reference.png is 514 px from beret to soles, Flan stands 490 px (2x sprites)

R = 'Flan_All_Sprites/'
I = R + '01_Idles/Flan_Idle_Pivot_v2/Normal/'
B = R + '02_Basics/Flan_Basics_v2/PNG/'
L = R + '03_Low_Normals/Flan_Crouch_and_Command_Normals/PNG/'
J = R + '04_Air_Normals/Flan_Air_Normals/PNG/'
Q = R + '05_236/Flan_236_Standalone/'
D6 = R + '06_623_Base_and_C/Flan_623/PNG/'
D7 = R + '07_623_AB_Latest/Flan_623_AB_v3/'
K = R + '08_214/Flan_214_Animations/PNG/'
S1 = R + '09_236236_Super/Flan_236236_Locked/PNG/'
S2 = R + '10_214214_Super/Flan_214214_Final/PNG/'
F = {}
def fr(fid, src, **kw): F[fid] = {'src': src, **kw}

# --- idle (Revision 2): base, breathing, blink and the pivot towards the viewer, drawn on one canvas.
# The base stands on its rear foot like every move's first pose; the others keep their place on the canvas.
fr('idle_base', I + '00_Base.png', scale=1.226)
for fid, f in [('idle_inhale', '01_Inhale'), ('idle_exhale', '02_Exhale'), ('idle_blink', '03_Blink'), ('idle_shiftb', '04_Shift_Back'),
               ('idle_shiftf', '05_Shift_Forward'), ('idle_half', '06_Turn_Half'), ('idle_center', '07_Turn_Center')]:
    fr(fid, I + f + '.png', anchor='like', like='idle_base')

# --- basics (02): walks and dashes keep the body centre fixed, jumps/air dashes use the air point
G = dict(scale=1.0)
for i in (1, 2):
    fr('walk_f%d' % i, B + 'Walk_Forward_0%d.png' % i, anchor='body_ground', **G)
    fr('walk_b%d' % i, B + 'Walk_Back_0%d.png' % i, anchor='body_ground', **G)
    fr('dash_%d' % i, B + 'Dash_Forward_0%d.png' % i, anchor='body_ground', **G)
    fr('backstep_%d' % i, B + 'Backstep_0%d.png' % i, anchor='body_ground', **G)
    fr('airdash_f%d' % i, B + 'AirDash_Forward_0%d.png' % i, anchor='air', **G)
    fr('airdash_b%d' % i, B + 'AirDash_Back_0%d.png' % i, anchor='air', **G)
fr('jump_load', B + 'Jump_01_Load.png', anchor='hips', **G)
fr('jump_rise', B + 'Jump_02_Rise.png', anchor='air', **G)
fr('jump_fall', B + 'Jump_03_Fall.png', anchor='air', **G)
fr('dmg_l', B + 'Damage_Light.png', anchor='hips', **G)
fr('dmg_h', B + 'Damage_Heavy.png', anchor='hips', **G)
fr('dmg_l_air', B + 'Damage_Light.png', anchor='air', **G)
fr('dmg_h_air', B + 'Damage_Heavy.png', anchor='air', **G)
fr('down', B + 'Downed_01.png', anchor='lying', **G)
fr('victory', B + 'Win_01.png', **G)
for mv in ('5A', '5B', '5C'):
    for i, ph in enumerate(['Start', 'Hit', 'Recover']):
        fr('%s_%d' % (mv.lower(), i + 1), B + '%s_0%d_%s.png' % (mv, i + 1, ph), **G)
for i in (1, 2, 3): F['5c_%d' % i]['anchor'] = 'front'     # 5C balances on her front leg
# --- crouch and low normals (03)
fr('crouch_1', L + 'Crouch_01_Lower.png', **G)
fr('crouch_2', L + 'Crouch_02_Hold.png', **G)
for mv in ('2A', '2B'):
    for i, ph in enumerate(['Start', 'Hit', 'Recover']):
        fr('%s_%d' % (mv.lower(), i + 1), L + '%s_0%d_%s.png' % (mv, i + 1, ph), **G)
fr('2c_1', L + '2C_01_Push.png', **G); fr('2c_2', L + '2C_02_Slide_Hit.png', **G); fr('2c_3', L + '2C_03_Brake.png', **G)
fr('6c_1', L + '6C_01_Load.png', **G); fr('6c_2', L + '6C_02_Pump.png', anchor='front', **G); fr('6c_3', L + '6C_03_Recover.png', **G)
# --- air normals (04): registered on the waist at (480, 440) of every canvas
for mv in ('jA', 'jB', 'jC'):
    for i, ph in enumerate(['Start', 'Hit', 'Recover']):
        fr('%s_%d' % (mv.lower(), i + 1), J + '%s_0%d_%s.png' % (mv, i + 1, ph), anchor='pin', pin=[480, 440], pin_at='air', **G)

# --- specials and supers (the moves are in moves_flan.py)
for i in range(1, 5): fr('w236_%d' % i, Q + 'Windup_0%d.png' % i, scale=1.078)
fr('p236', Q + 'Punch_01.png', anchor='hips', scale=1.078)   # lunge: the hips stay over her origin, the engine carries her
fr('dp_hit', D6 + 'Hit_01.png', scale=1.0)
fr('dp_held', D7 + 'Held_Uppercut.png', anchor='air', scale=1.0)
for fid, f in [('dp_rise1', 'Rise_01'), ('dp_rise2', 'Rise_02'), ('dp_apex', 'Apex_01'), ('dp_aim', 'Beam_Aim_01'),
               ('dp_spin', 'Spin_Back_01'), ('dp_fall', 'Fall_Front_01')]:
    fr(fid, D6 + f + '.png', anchor='air', scale=1.0)
fr('dp_rise2_m', D6 + 'Rise_02.png', anchor='air', scale=1.0, flip=True)     # the third spin orientation (623C)
fr('k214_idle', K + 'Idle.png', scale=0.73)
fr('k214_knee', K + 'Knee.png', anchor='air', scale=0.73)
fr('k214_load', K + 'Descent_Load.png', anchor='air', scale=0.73)
fr('k214_punch', K + 'Descent_Punch.png', anchor='air', scale=0.73)
fr('k214_impact', K + 'Impact.png', anchor='hips', scale=0.73)
for fid, f in [('s1_idle', 'Idle'), ('s1_w1', 'Windup_01'), ('s1_w2', 'Windup_02'), ('s1_w3', 'Windup_03'), ('s1_w4', 'Windup_04'),
               ('s1_dash', 'Dash_Punch'), ('s1_fire', 'Fire'), ('s1_recoil', 'Recoil'), ('s1_roll', 'Roll'), ('s1_exit', 'Roll_Exit')]:
    fr(fid, S1 + f + '.png', anchor='pin', pin=[450, 700], scale=0.69)
for i in range(1, 5): F['s1_w%d' % i]['anchor'] = 'ground'   # the windup loop is drawn ~90 px ahead of the anchor: start in place
fr('roll_air', S1 + 'Roll.png', anchor='air', scale=0.69)       # air recovery flips
for fid, f in [('s2_w1', 'Windup_01'), ('s2_w2', 'Windup_02'), ('s2_w3', 'Windup_03'), ('s2_diag', 'Diagonal_Punch'),
               ('s2_load', 'Downward_Load'), ('s2_down', 'Downward_Punch'), ('s2_impact', 'Ground_Impact'), ('s2_stand', 'Stand'),
               ('s2_sweat', 'Sweat_Wipe')]:
    fr(fid, S2 + f + '.png', anchor='pin', pin=[450, 760], scale=0.745)

# --- block stand-ins (no block drawings yet): braced backstep, crouch guard, compact air guard
fr('block_st', B + 'Backstep_01.png', anchor='body_ground', **G)
fr('block_cr', L + 'Crouch_02_Hold.png', **G)
fr('block_air', J + 'jA_01_Start.png', anchor='pin', pin=[480, 440], pin_at='air', **G)
m['frames'] = {k: v for k, v in m.get('frames', {}).items() if k not in F}
m['frames'].update(F)   # update, so frames added by moves_flan.py stay

# --- animations (names = AnimationData files without _AnimData.tres); keys: [frame, at, {rot, dx, dy, fx}]
AN = {}
def an(name, keys, **kw): AN[name] = {'keys': keys, **kw}
# idle: the pack's animation.json sequence and holds (ms -> frames at 60 fps)
SEQ = [0, 6, 7, 6, 0, 1, 0, 6, 7, 6, 0, 2, 0, 3, 0, 6, 7, 6, 0, 0]
MS = [300, 180, 300, 180, 300, 300, 300, 180, 300, 180, 300, 300, 300, 100, 300, 180, 300, 180, 300, 300]
IDF = ['idle_base', 'idle_inhale', 'idle_exhale', 'idle_blink', 'idle_shiftb', 'idle_shiftf', 'idle_half', 'idle_center']
keys, t = [], 0
for s, ms in zip(SEQ, MS):
    if not keys or keys[-1][0] != IDF[s]: keys.append([IDF[s], t])
    t += round(ms * 60 / 1000)
an('0_FLN_Neutral', keys, duration=t)
an('1_FLN_MoveF', [['walk_f1', 0], ['walk_f2', 10], ['walk_f1', 20], ['walk_f2', 30]], duration=40)
an('2_FLN_MoveB', [['walk_b1', 0], ['walk_b2', 11], ['walk_b1', 22], ['walk_b2', 33]], duration=44)
an('3_FLN_Jump', [['jump_load', 0], ['jump_rise', 4], ['jump_fall', 19]])
an('3b_FLN_JumpForward', [['jump_load', 0], ['jump_rise', 4, {'rot': -4}], ['jump_rise', 10, {'rot': -8}], ['jump_fall', 19, {'rot': -4}]])
an('3c_FLN_JumpBackward', [['jump_load', 0], ['jump_rise', 4, {'rot': 5}], ['jump_rise', 10, {'rot': 9}], ['jump_fall', 19, {'rot': 4}]])
an('4_FLN_Falling', [['jump_fall', 0]])
an('5_FLN_Landing', [['jump_load', 0], ['crouch_1', 7]])
an('6_FLN_CrouchEnter', [['crouch_1', 0], ['crouch_2', 4]])
an('7_FLN_Crouching', [['crouch_2', 0]])
an('8_FLN_CrouchExit', [['crouch_2', 0], ['crouch_1', 4]])
an('9_FLN_DashFw', [['dash_1', 0], ['dash_2', 5], ['dash_1', 11], ['dash_2', 17], ['dash_1', 23], ['dash_2', 29]])
an('10_FLN_RunStop', [['jump_load', 0], ['crouch_1', 9]])
an('11_FLN_DashBw', [['backstep_1', 0], ['backstep_2', 7], ['jump_load', 18]])
an('12_FLN_AirDashFw', [['airdash_f1', 0], ['airdash_f2', 4], ['jump_fall', 18]])
an('13_FLN_AirDashDir', [['airdash_f1', 0], ['airdash_f2', 4], ['jump_fall', 24]])
an('14_FLN_AirDashBw', [['airdash_b1', 0], ['airdash_b2', 4], ['jump_fall', 18]])
an('15_FLN_Hit_Weak', [['dmg_l', 0, {'dx': -8, 'rot': 2}], ['dmg_l', 2, {'dx': -6, 'rot': 1}], ['dmg_l', 4, {'dx': -4}], ['dmg_l', 6, {'dx': -2}], ['dmg_l', 7]])
an('16_FLN_Hit_Strong', [['dmg_h', 0, {'dx': -16, 'rot': 5}], ['dmg_h', 2, {'dx': -12, 'rot': 3}], ['dmg_h', 4, {'dx': -8, 'rot': 2}], ['dmg_h', 6, {'dx': -4}], ['dmg_h', 7]])
an('17_FLN_Hit_Crouch', [['crouch_2', 0, {'dx': -6, 'rot': 4}], ['crouch_2', 2, {'dx': -4, 'rot': 2}], ['crouch_2', 4, {'dx': -2, 'rot': 1}], ['crouch_2', 7]])
an('18_FLN_Hit_Sweep', [['dmg_h_air', 0, {'rot': 24}], ['dmg_h_air', 2, {'rot': 20}], ['dmg_h_air', 4, {'rot': 16}], ['dmg_h_air', 6, {'rot': 12}]])
an('19_FLN_Hit_AirWeak', [['dmg_l_air', 0, {'rot': 10}], ['dmg_l_air', 2, {'rot': 12}], ['dmg_l_air', 4, {'rot': 9}], ['dmg_l_air', 6, {'rot': 5}]])
an('20_FLN_Hit_AirStrong', [['dmg_h_air', 0, {'rot': 16}], ['dmg_h_air', 2, {'rot': 20}], ['dmg_h_air', 4, {'rot': 16}], ['dmg_h_air', 6, {'rot': 10}]])
an('21_FLN_Hit_Fall1', [['dmg_h_air', 0, {'rot': 150}]])
an('21_FLN_Hit_Fall2', [['dmg_h_air', 0, {'rot': 90}]])
an('21_FLN_Hit_FallTransition', [['dmg_h_air', 0, {'rot': 45}]])
an('22_FLN_Hit_Knockdown1', [['down', 0, {'dy': 14}], ['down', 6, {'dy': 6}]])
an('22_FLN_Hit_Knockdown2', [['down', 0]])
an('22_FLN_Hit_Knockdown3', [['down', 0], ['down', 4, {'dx': -4}], ['down', 8]])
an('23_FLN_Hit_Down', [['down', 0]])
an('24_FLN_Hit_GetUp', [['crouch_2', 0], ['crouch_1', 6]])
an('25_FLN_Hit_LaunchAway', [['dmg_h_air', 0, {'rot': 35}]])
an('25_FLN_Hit_LaunchDown', [['dmg_h_air', 0, {'rot': 120}]])
an('25_FLN_Hit_LaunchUp', [['dmg_h_air', 0, {'rot': 15}]])
an('26_FLN_Hit_GroundBounce', [['dmg_h_air', 0, {'rot': 90}], ['dmg_h_air', 12, {'rot': 60}]])
an('26_FLN_Hit_WallBounce', [['dmg_h_air', 0, {'rot': -20}], ['dmg_h_air', 1, {'rot': 30}]])
an('27_FLN_Hit_Crumple', [['dmg_h', 0], ['dmg_l', 10, {'rot': -6, 'dy': -6}], ['crouch_1', 20], ['crouch_2', 32]])
an('28_FLN_Hit_KO', [['down', 0]])
an('29_FLN_Stand_Block_Transition', [['block_st', 0]])
an('30_FLN_Stand_Block', [['block_st', 0]])
an('31_FLN_Stand_Blockstun', [['block_st', 0, {'dx': -6, 'rot': 2}], ['block_st', 2, {'dx': -4, 'rot': 1}], ['block_st', 4, {'dx': -2}], ['block_st', 7]])
an('32_FLN_Crouch_Block_Transition', [['block_cr', 0]])
an('33_FLN_Crouch_Block', [['block_cr', 0]])
an('34_FLN_Crouch_Blockstun', [['block_cr', 0, {'dx': -6, 'rot': 2}], ['block_cr', 2, {'dx': -4, 'rot': 1}], ['block_cr', 4, {'dx': -2}], ['block_cr', 7]])
an('35_FLN_Air_Block_Transition', [['block_air', 0]])
an('36_FLN_Air_Block', [['block_air', 0]])
an('37_FLN_Air_Blockstun', [['block_air', 0, {'dx': -6, 'rot': 3}], ['block_air', 2, {'dx': -4, 'rot': 2}], ['block_air', 4, {'dx': -2, 'rot': 1}], ['block_air', 7]])
# normals: Cecilia's frame data (the hitbox timing her data came with); the drawings change on its active frames
an('48_FLN_5A', [['5a_1', 0], ['5a_2', 5], ['5a_3', 11]])
an('49_FLN_5B', [['5b_1', 0], ['5b_2', 8], ['5b_3', 18]])
an('50_FLN_5C', [['5c_1', 0], ['5c_2', 13], ['5c_3', 21]])            # + the radiant extension (moves_flan.py)
an('51_FLN_2A', [['2a_1', 0], ['2a_2', 5], ['2a_3', 10]])
an('52_FLN_2B', [['2b_1', 0], ['2b_2', 7], ['2b_3', 13]])
an('53_FLN_2C', [['2c_1', 0], ['2c_2', 9], ['2c_3', 25]], afterimages=False)
an('54_FLN_j5A', [['ja_1', 0], ['ja_2', 4], ['ja_3', 10]])
an('55_FLN_j5B', [['jb_1', 0], ['jb_2', 6], ['jb_3', 12]])
an('56_FLN_j5C', [['jc_1', 0], ['jc_2', 9], ['jc_3', 18]])
# 6C: slow overhead fist pump (new timing: active 16-19)
an('57_FLN_6C', [['6c_1', 0], ['6c_2', 16], ['6c_3', 26]], duration=38,
   hitboxes=[[0, 0, '8_Hitbox_6C_0'], [6, 0, '8_Hitbox_6C_1'], [16, 1, '8_Hitbox_6C_2'], [20, 2, '8_Hitbox_6C_3'], [26, 2, '8_Hitbox_6C_4']])
an('100_FLN_Intro', [['idle_base', 0], ['6c_1', 34], ['6c_2', 42], ['6c_3', 74], ['idle_base', 90]])
an('101_FLN_Outro', [['victory', 0]])
an('200_FLN_Recovery_Backwards', [['roll_air', 0], ['roll_air', 5, {'rot': 90}], ['roll_air', 10, {'rot': 180}], ['roll_air', 15, {'rot': 270}]])
an('200_FLN_Recovery_Forward', [['roll_air', 0], ['roll_air', 5, {'rot': -90}], ['roll_air', 10, {'rot': -180}], ['roll_air', 15, {'rot': -270}]])
an('200_FLN_Recovery_Neutral', [['jump_fall', 0]])
an('1000_FLN_Cancel', [['s1_w1', 0], ['s1_w2', 4], ['s1_w3', 8]])
an('1001_FLN_Burst', [['6c_1', 0], ['6c_2', 4], ['6c_2', 30], ['6c_3', 34]])      # + the burst light (moves_flan.py)
an('FLN_Breakthrough', [['5b_1', 0], ['5b_2', 8], ['5b_3', 18]])
m['animations'] = {k: v for k, v in m.get('animations', {}).items() if k not in AN}
m['animations'].update(AN)

HF = {
    'skip': ['-1_Hitbox_CollisionOnly', '-2_Hitbox_CollisionOnly_Low', '100_Hitbox_Burst', '100_Hitbox_Cancel', 'FLN_Hitbox_Invincible',
             'FLN_Hitbox_Breakthrough_nhb2', '18_Hitbox_Grab_stUp', '19_Hitbox_Grab'],
    'split': {'3_Hitbox_FDash': {'3_Hitbox_AirDash': ['12_FLN_AirDashFw', '13_FLN_AirDashDir']},
              '4_Hitbox_BDash': {'4_Hitbox_AirDashBw': ['14_FLN_AirDashBw']},
              '0_Hitbox_Horizontal': {'0_Hitbox_Lying': ['23_FLN_Hit_Down']},
              '0_Hitbox_Basic': {'0_Hitbox_Lying': ['22_FLN_Hit_Knockdown1', '22_FLN_Hit_Knockdown2', '22_FLN_Hit_Knockdown3']}},
    'fit_from': {'0_Hitbox_Basic': ['0_FLN_Neutral', 0], '1_Hitbox_Crouch': ['7_FLN_Crouching', 0], '3_Hitbox_FDash': ['9_FLN_DashFw', 5],
                 '3_Hitbox_AirDash': ['12_FLN_AirDashFw', 8], '4_Hitbox_AirDashBw': ['14_FLN_AirDashBw', 8], '0_Hitbox_Lying': ['23_FLN_Hit_Down', 0],
                 '2_Hitbox_Jump': ['4_FLN_Falling', 0]},
    'attack_part': {'53_FLN_2C': 'edge', '55_FLN_j5B': 'edge', '57_FLN_6C': 'top'},
    'min_fx': 400,
    'fresh_size': True,   # her boxes came from Cecilia's sword moves: size them from the punches
    'boxes': {},
}
hf = m.setdefault('hitfit', {})   # merged, so boxes / parts added by moves_flan.py stay
for k, v in HF.items():
    if isinstance(v, dict) and isinstance(hf.get(k), dict): hf[k].update(v)
    else: hf[k] = v
m['artwork'] = {'name': 'Flan', 'cutin_ex': R + '12_EX_Cut_In/Flan_EX_Cut_In.png'}
json.dump(m, open(P, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(len(F), 'frames', len(AN), 'animations; idle', t, 'frames')
