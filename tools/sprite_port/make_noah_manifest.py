# One-off helper that writes manifests/noah.json (frames + the standard animations), Oct 25 evening, from
# Fighting_Game_All_Sprites/Noah_Complete (see its COMMAND_LIST.md, README.txt and the folder notes).
# Re-running rewrites the entries it makes in "frames", "animations" and "hitfit" (moves_noah.py adds the specials).
#
# Scales (drawing px per reference px, reference = Basics/PNG/Idle_Reference.png). The packs were not drawn at one
# scale (not even the Basics folder), so each drawing's scale comes from two measures that mostly agree: SIFT on the
# head (analyze.py) and the size of the red belt card (rigid, seen in nearly every pose); where they disagree the
# pack's own registration note decides (God Press: standing pose 461 px on its 800x600 canvas -> 1.10).
# sizefix.py then checks neighbouring frames against each other.
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, 'manifests', 'noah.json')
m = json.load(open(P, encoding='utf-8'))
m['fx'] = 'purple'
m['game'] = {'height_px': 540, 'pixel_size': 0.00275, 'sprites_subdir': 'v2', 'origin_from_rear': 0.5}

R = 'Noah_Complete/'
B = R + 'Basics/PNG/'
IC = R + 'Idle/Composite_PNG/'
J = R + 'Movement/Jump_and_Run/PNG/'
NA = R + 'Normals/Air/'
D = 'derived/noah/'
F = {}
def fr(fid, src, **kw): F[fid] = {'src': src, **kw}

# --- idle: the pack's 16 body + aura composites (aura behind the devil arm), all on one 1024x1536 canvas
fr('idle_0_1', IC + 'Idle_00_Aura_01.png', scale=3.57)
for b in range(4):
    for a in range(1, 5):
        if (b, a) == (0, 1): continue
        fr('idle_%d_%d' % (b, a), IC + 'Idle_%02d_Aura_%02d.png' % (b, a), anchor='like', like='idle_0_1')
# --- basics (scale per drawing: see the top)
BS = {'5A_Hit': 1.17, '5A_Recover': 1.2, '5B_Hit': 1.15, '5C_Hit': 1.17, '6C_Hit': 1.15, 'AirDash_Back': 1.2, 'AirDash_Forward': 1.16,
      'AirDash_Recover': 1.1, 'Backstep': 1.18, 'Crouch_Exit': 1.12, 'Crouch_Hold': 1.14, 'Crouch_Lower': 1.18, 'Damage_Heavy': 1.36,
      'Damage_Light': 1.36, 'Downed': 1.16, 'Win_01': 1.0, 'Win_02': 1.0, 'Win_03': 1.06, 'Win_04': 1.17, 'Win_05': 1.15, 'Win_06': 1.12,
      '2A_Recover': 1.2, '2B_Recover': 1.24, '2C_Follow': 1.17, 'Idle_Reference': 1.0}
def bs(fid, name, **kw): fr(fid, B + name + '.png', scale=BS[name], **kw)
bs('stand', 'Idle_Reference')
bs('backstep', 'Backstep', anchor='body_ground')
bs('airdash_f', 'AirDash_Forward', anchor='air'); bs('airdash_b', 'AirDash_Back', anchor='air'); bs('airdash_rec', 'AirDash_Recover', anchor='air')
bs('crouch_1', 'Crouch_Lower'); bs('crouch_2', 'Crouch_Hold'); bs('crouch_x', 'Crouch_Exit')
bs('dmg_l', 'Damage_Light', anchor='hips'); bs('dmg_h', 'Damage_Heavy', anchor='hips')
bs('dmg_l_air', 'Damage_Light', anchor='air'); bs('dmg_h_air', 'Damage_Heavy', anchor='air')
bs('down', 'Downed', anchor='lying')
for i in range(1, 7): bs('win_%d' % i, 'Win_%02d' % i)
bs('5a_rec', '5A_Recover'); bs('2a_rec', '2A_Recover'); bs('2b_rec', '2B_Recover'); bs('2c_follow', '2C_Follow')
# --- jump and run (one 640x600 canvas each, fixed scale within the sequence)
for i in range(1, 7): fr('jump_%d' % i, J + 'Jump_%02d.png' % i, scale=0.93, anchor='air')
F['jump_1']['anchor'] = 'hips'; F['jump_6']['anchor'] = 'hips'
for i in range(1, 5): fr('run_%d' % i, J + 'Run_Low_Arm_%02d.png' % i, scale=0.92, anchor='body_ground')
# --- normals: the corrected active poses (derived/noah: cleaned, see derive_noah.py)
for n in ('5A', '5B', '5C', '6C'): fr(n.lower() + '_act', D + n + '_Active.png', scale=1.8)
for n in ('2A', '2B', '2C'): fr(n.lower() + '_act', D + n + '_Active.png', scale=1.85)
for mv in ('jA', 'jB', 'jC'):
    for i in range(1, 5): fr('%s_%d' % (mv.lower(), i), NA + '%s/Frame_%02d.png' % (mv, i), scale=1.7, anchor='air')
# block stand-ins (no block drawings): braced backstep, crouch, air-dash recovery
fr('block_st', B + 'Backstep.png', scale=BS['Backstep'], anchor='body_ground')
fr('block_cr', B + 'Crouch_Hold.png', scale=BS['Crouch_Hold'])
fr('block_air', B + 'AirDash_Recover.png', scale=BS['AirDash_Recover'], anchor='air')
m['frames'] = {k: v for k, v in m.get('frames', {}).items() if k not in F}
m['frames'].update(F)

AN = {}
def an(name, keys, **kw): AN[name] = {'keys': keys, **kw}
# idle: the pack's animation.json (90 ms per picture -> 5 / 6 frames)
seq = json.load(open(os.path.join(os.path.expanduser('~/mnt/Fighting_Game_All_Sprites'), R + 'Idle/animation.json')))['sequence'] \
    if os.path.exists(os.path.join(os.path.expanduser('~/mnt/Fighting_Game_All_Sprites'), R + 'Idle/animation.json')) else None
keys, t = [], 0
if seq:
    for n, s in enumerate(seq):
        b, a = int(s['file'][5:7]), int(s['file'][13:15])
        keys.append(['idle_%d_%d' % (b, a), t]); t += 5 if n % 2 == 0 else 6
else:
    for n in range(16): keys.append(['idle_0_%d' % (n % 4 + 1), t]); t += 6
an('0_NOA_Neutral', keys, duration=t)
an('1_NOA_MoveF', [['run_1', 0], ['run_2', 9], ['run_3', 18], ['run_4', 27]], duration=36)
an('2_NOA_MoveB', [['run_4', 0], ['run_3', 10], ['run_2', 20], ['run_1', 30]], duration=40)
an('3_NOA_Jump', [['jump_1', 0], ['jump_2', 4], ['jump_3', 8], ['jump_4', 16], ['jump_5', 24]])
an('3b_NOA_JumpForward', [['jump_1', 0], ['jump_2', 4, {'rot': -4}], ['jump_3', 8, {'rot': -6}], ['jump_4', 16, {'rot': -4}], ['jump_5', 24]])
an('3c_NOA_JumpBackward', [['jump_1', 0], ['jump_2', 4, {'rot': 5}], ['jump_3', 8, {'rot': 7}], ['jump_4', 16, {'rot': 4}], ['jump_5', 24]])
an('4_NOA_Falling', [['jump_5', 0]])
an('5_NOA_Landing', [['jump_6', 0], ['crouch_x', 7]])
an('6_NOA_CrouchEnter', [['crouch_1', 0], ['crouch_2', 4]])
an('7_NOA_Crouching', [['crouch_2', 0]])
an('8_NOA_CrouchExit', [['crouch_2', 0], ['crouch_x', 4]])
an('9_NOA_DashFw', [['run_1', 0], ['run_2', 5], ['run_3', 10], ['run_4', 15], ['run_1', 20], ['run_2', 25]])
an('10_NOA_RunStop', [['crouch_x', 0], ['stand', 9]])
an('11_NOA_DashBw', [['backstep', 0], ['backstep', 7, {'dx': -4}], ['jump_6', 18]])
an('12_NOA_AirDashFw', [['airdash_f', 0], ['airdash_f', 4], ['airdash_rec', 18]])
an('13_NOA_AirDashDir', [['airdash_f', 0], ['airdash_f', 4], ['airdash_rec', 24]])
an('14_NOA_AirDashBw', [['airdash_b', 0], ['airdash_b', 4], ['airdash_rec', 18]])
an('15_NOA_Hit_Weak', [['dmg_l', 0, {'dx': -8, 'rot': 2}], ['dmg_l', 2, {'dx': -6, 'rot': 1}], ['dmg_l', 4, {'dx': -4}], ['dmg_l', 6, {'dx': -2}], ['dmg_l', 7]])
an('16_NOA_Hit_Strong', [['dmg_h', 0, {'dx': -16, 'rot': 5}], ['dmg_h', 2, {'dx': -12, 'rot': 3}], ['dmg_h', 4, {'dx': -8, 'rot': 2}], ['dmg_h', 6, {'dx': -4}], ['dmg_h', 7]])
an('17_NOA_Hit_Crouch', [['crouch_2', 0, {'dx': -6, 'rot': 4}], ['crouch_2', 2, {'dx': -4, 'rot': 2}], ['crouch_2', 4, {'dx': -2, 'rot': 1}], ['crouch_2', 7]])
an('18_NOA_Hit_Sweep', [['dmg_h_air', 0, {'rot': 24}], ['dmg_h_air', 2, {'rot': 20}], ['dmg_h_air', 4, {'rot': 16}], ['dmg_h_air', 6, {'rot': 12}]])
an('19_NOA_Hit_AirWeak', [['dmg_l_air', 0, {'rot': 10}], ['dmg_l_air', 2, {'rot': 12}], ['dmg_l_air', 4, {'rot': 9}], ['dmg_l_air', 6, {'rot': 5}]])
an('20_NOA_Hit_AirStrong', [['dmg_h_air', 0, {'rot': 16}], ['dmg_h_air', 2, {'rot': 20}], ['dmg_h_air', 4, {'rot': 16}], ['dmg_h_air', 6, {'rot': 10}]])
an('21_NOA_Hit_Fall1', [['dmg_h_air', 0, {'rot': 150}]])
an('21_NOA_Hit_Fall2', [['dmg_h_air', 0, {'rot': 90}]])
an('21_NOA_Hit_FallTransition', [['dmg_h_air', 0, {'rot': 45}]])
an('22_NOA_Hit_Knockdown1', [['down', 0, {'dy': 14}], ['down', 6, {'dy': 6}]])
an('22_NOA_Hit_Knockdown2', [['down', 0]])
an('22_NOA_Hit_Knockdown3', [['down', 0], ['down', 4, {'dx': -4}], ['down', 8]])
an('23_NOA_Hit_Down', [['down', 0]])
an('24_NOA_Hit_GetUp', [['crouch_2', 0], ['crouch_x', 6]])
an('25_NOA_Hit_LaunchAway', [['dmg_h_air', 0, {'rot': 35}]])
an('25_NOA_Hit_LaunchDown', [['dmg_h_air', 0, {'rot': 120}]])
an('25_NOA_Hit_LaunchUp', [['dmg_h_air', 0, {'rot': 15}]])
an('26_NOA_Hit_GroundBounce', [['dmg_h_air', 0, {'rot': 90}], ['dmg_h_air', 12, {'rot': 60}]])
an('26_NOA_Hit_WallBounce', [['dmg_h_air', 0, {'rot': -20}], ['dmg_h_air', 1, {'rot': 30}]])
an('27_NOA_Hit_Crumple', [['dmg_h', 0], ['dmg_l', 10, {'rot': -6, 'dy': -6}], ['crouch_1', 20], ['crouch_2', 32]])
an('28_NOA_Hit_KO', [['down', 0]])
an('29_NOA_Stand_Block_Transition', [['block_st', 0]])
an('30_NOA_Stand_Block', [['block_st', 0]])
an('31_NOA_Stand_Blockstun', [['block_st', 0, {'dx': -6, 'rot': 2}], ['block_st', 2, {'dx': -4, 'rot': 1}], ['block_st', 4, {'dx': -2}], ['block_st', 7]])
an('32_NOA_Crouch_Block_Transition', [['block_cr', 0]])
an('33_NOA_Crouch_Block', [['block_cr', 0]])
an('34_NOA_Crouch_Blockstun', [['block_cr', 0, {'dx': -6, 'rot': 2}], ['block_cr', 2, {'dx': -4, 'rot': 1}], ['block_cr', 4, {'dx': -2}], ['block_cr', 7]])
an('35_NOA_Air_Block_Transition', [['block_air', 0]])
an('36_NOA_Air_Block', [['block_air', 0]])
an('37_NOA_Air_Blockstun', [['block_air', 0, {'dx': -6, 'rot': 3}], ['block_air', 2, {'dx': -4, 'rot': 2}], ['block_air', 4, {'dx': -2, 'rot': 1}], ['block_air', 7]])
# normals: the hitbox timing his data came with (Flan's, i.e. Cecilia's frame data); the drawings change on the active frames
an('48_NOA_5A', [['stand', 0], ['5a_act', 5], ['5a_rec', 9], ['stand', 17]])
an('49_NOA_5B', [['stand', 0], ['crouch_x', 4], ['5b_act', 8], ['stand', 20]])
an('50_NOA_5C', [['stand', 0], ['5a_rec', 6], ['5c_act', 13], ['5c_act', 20, {'dx': -4}], ['stand', 26]])
an('51_NOA_2A', [['crouch_2', 0], ['2a_act', 5], ['2a_rec', 8], ['crouch_2', 13]])
an('52_NOA_2B', [['crouch_2', 0], ['2b_act', 7], ['2b_rec', 11], ['crouch_2', 18]])
an('53_NOA_2C', [['crouch_2', 0], ['2c_act', 9], ['2c_follow', 20], ['crouch_2', 32]], afterimages=False)
an('54_NOA_j5A', [['ja_1', 0], ['ja_2', 4], ['ja_3', 8], ['ja_4', 11]])
an('55_NOA_j5B', [['jb_1', 0], ['jb_2', 6], ['jb_3', 8], ['jb_4', 12]])
an('56_NOA_j5C', [['jc_1', 0], ['jc_2', 6], ['jc_3', 9], ['jc_4', 16]])
an('57_NOA_6C', [['stand', 0], ['crouch_x', 6], ['6c_act', 16], ['6c_act', 22, {'dy': -4}], ['stand', 28]], duration=38,
   hitboxes=[[0, 0, '8_Hitbox_6C_0'], [6, 0, '8_Hitbox_6C_1'], [16, 1, '8_Hitbox_6C_2'], [20, 2, '8_Hitbox_6C_3'], [26, 2, '8_Hitbox_6C_4']])
an('100_NOA_Intro', [['idle_0_1', 0], ['win_4', 30], ['win_5', 44], ['win_6', 60], ['idle_0_1', 88]])
an('101_NOA_Outro', [['win_1', 0], ['win_2', 21], ['win_3', 35], ['win_4', 56], ['win_5', 66], ['win_6', 87]])
an('200_NOA_Recovery_Backwards', [['jump_4', 0], ['jump_4', 5, {'rot': 90}], ['jump_4', 10, {'rot': 180}], ['jump_4', 15, {'rot': 270}]])
an('200_NOA_Recovery_Forward', [['jump_4', 0], ['jump_4', 5, {'rot': -90}], ['jump_4', 10, {'rot': -180}], ['jump_4', 15, {'rot': -270}]])
an('200_NOA_Recovery_Neutral', [['jump_5', 0]])
an('1000_NOA_Cancel', [['crouch_x', 0], ['6c_act', 4], ['6c_act', 8]])
an('1001_NOA_Burst', [['crouch_x', 0], ['6c_act', 4], ['6c_act', 30], ['stand', 34]])
an('NOA_Breakthrough', [['stand', 0], ['crouch_x', 4], ['5b_act', 8], ['stand', 20]])
m['animations'] = {k: v for k, v in m.get('animations', {}).items() if k not in AN}
m['animations'].update(AN)

HF = {
    'skip': ['-1_Hitbox_CollisionOnly', '-2_Hitbox_CollisionOnly_Low', '100_Hitbox_Burst', '100_Hitbox_Cancel', 'NOA_Hitbox_Invincible',
             'NOA_Hitbox_Breakthrough_nhb2', '18_Hitbox_Grab_stUp', '19_Hitbox_Grab'],
    'split': {'3_Hitbox_FDash': {'3_Hitbox_AirDash': ['12_NOA_AirDashFw', '13_NOA_AirDashDir']},
              '4_Hitbox_BDash': {'4_Hitbox_AirDashBw': ['14_NOA_AirDashBw']},
              '0_Hitbox_Horizontal': {'0_Hitbox_Lying': ['23_NOA_Hit_Down']},
              '0_Hitbox_Basic': {'0_Hitbox_Lying': ['22_NOA_Hit_Knockdown1', '22_NOA_Hit_Knockdown2', '22_NOA_Hit_Knockdown3']}},
    'fit_from': {'0_Hitbox_Basic': ['0_NOA_Neutral', 0], '1_Hitbox_Crouch': ['7_NOA_Crouching', 0], '3_Hitbox_FDash': ['9_NOA_DashFw', 5],
                 '3_Hitbox_AirDash': ['12_NOA_AirDashFw', 8], '4_Hitbox_AirDashBw': ['14_NOA_AirDashBw', 8], '0_Hitbox_Lying': ['23_NOA_Hit_Down', 0],
                 '2_Hitbox_Jump': ['4_NOA_Falling', 0]},
    'attack_part': {'53_NOA_2C': 'edge', '55_NOA_j5B': 'edge', '57_NOA_6C': 'top'},
    'min_fx': 400,
    'fresh_size': True,
    'boxes': {},
}
hf = m.setdefault('hitfit', {})
for k, v in HF.items():
    if isinstance(v, dict) and isinstance(hf.get(k), dict): hf[k].update(v)
    else: hf[k] = v
m['artwork'] = {'name': 'Noah', 'cutin_ex': R + 'Artwork/Noah_EX_Cut_In.png'}
json.dump(m, open(P, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(len(F), 'frames', len(AN), 'animations; idle', t, 'frames')
