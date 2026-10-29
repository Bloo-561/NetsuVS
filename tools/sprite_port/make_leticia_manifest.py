# One-off helper that wrote manifests/leticia.json (frames + the standard animations).
# Edit the JSON directly from now on (re-running this rewrites the entries it makes in "frames", "animations" and "hitfit").
# Her specials and supers are added to the JSON by moves_leticia.py.
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, 'manifests', 'leticia.json')
m = json.load(open(P, encoding='utf-8'))
m['game'] = {'height_px': 520, 'pixel_size': 0.00275, 'sprites_subdir': 'v2', 'origin_from_rear': 0.5}
L = 'Leticia/'
F = {}
def fr(fid, src, **kw): F[fid] = {'src': L + src, **kw}

# --- idle: one drawing (Idle_01) breathing; the eyes come from the blink drawings (Idle_04 half, Idle_05 closed)
rows = [[0, 1.0], [300, 1.0], [560, 0.65], [800, 0.2], [880, 0.0], [1500, 0.0]]
A = 8.0
lv = {'m3': -A, 'm2': -A * 0.866, 'm1': -A * 0.5, '0': 0.0, 'p1': A * 0.5, 'p2': A * 0.866, 'p3': A}
for k, v in lv.items():
    fr('idle_O' + k, '01_Idle/Leticia_01_Idle_01.png', anchor='ref', breath=round(v, 2), breath_rows=rows)
blink = {'HB': {'src': L + '01_Idle/Leticia_01_Idle_04.png', 'shift': [-0.49, -0.64], 'box': [585, 145, 725, 240], 'feather': 6},
         'B': {'src': L + '01_Idle/Leticia_01_Idle_05.png', 'shift': [-0.66, 0.04], 'box': [585, 145, 725, 240], 'feather': 6}}
for e, k in [('HB', 'm3'), ('B', 'm2'), ('HB', 'm2'), ('HB', 'm1')]:
    fr('idle_%s%s' % (e, k), '01_Idle/Leticia_01_Idle_01.png', anchor='ref', breath=round(lv[k], 2), breath_rows=rows, blink=blink[e])

# --- walks: body centre fixed, feet on the floor. The walk drawings are taller than the idle at the
# same head size, so their scales sit halfway between "same head size" and "same height" as the idle
# (frame-to-frame ratios from pairscale.py keep each cycle even)
WF = [0.95, 1.10, 1.04, 1.135]; WB = [0.92, 0.92, 0.935, 0.935]
for i in range(4):
    fr('wf_%d' % (i + 1), 'Forward/Leticia_Walk_Forward_0%d.png' % (i + 1), anchor='body_ground', scale=WF[i])
    fr('wb_%d' % (i + 1), 'Backward/Leticia_Walk_Backward_0%d.png' % (i + 1), anchor='body_ground', scale=WB[i])

# --- crouch, dash, damage
for i in range(3): fr('crouch_%d' % (i + 1), '03_Crouch/Leticia_03_Crouch_0%d.png' % (i + 1))
fr('dash_1', '04_Dash/Leticia_04_Dash_01.png', anchor='body_ground')
fr('dash_2', '04_Dash/Leticia_04_Dash_02.png', anchor='body_ground', scale_like=L + '04_Dash/Leticia_04_Dash_01.png')
fr('dash_3', '04_Dash/Leticia_04_Dash_03.png', anchor='air', scale=1.25)
fr('dash_4', '04_Dash/Leticia_04_Dash_04.png', anchor='body_ground')
fr('dmg', '02_Damage/Leticia_02_Damage_01.png', scale=0.97)
fr('dmg_air', '02_Damage/Leticia_02_Damage_01.png', anchor='air', scale=0.97)

# --- normals
N = '06_Ground_Normals/'
for mv, files in [('5a', ['5A/Leticia_5A_01_Startup', '5A/Leticia_5A_02_Jab', '5A/Leticia_5A_03_Recovery']),
                  ('2a', ['2A/Leticia_2A_01_Startup', '2A/Leticia_2A_02_Jab', '2A/Leticia_2A_03_Recovery']),
                  ('5b', ['5B/Leticia_5B_01_Load', '5B/Leticia_5B_02_Pivot_and_Swing', '5B/Leticia_5B_03_Brace_and_Recover']),
                  ('2b', ['2B/Leticia_2B_01_Aim', '2B/Leticia_2B_02_Burst_Start', '2B/Leticia_2B_03_Burst_Peak', '2B/Leticia_2B_04_Burst_Fade']),
                  ('5c', ['5C/Leticia_5C_01_Startup_Corrected', '5C/Leticia_5C_02_Large_Double_Burst', '5C/Leticia_5C_03_Burst_Fade']),
                  ('2c', ['2C/Leticia_2C_01_Startup_Corrected', '2C/Leticia_2C_02_First_Shot', '2C/Leticia_2C_03_Second_Shot_Corrected', '2C/Leticia_2C_04_Recovery'])]:
    for i, f in enumerate(files):
        fr('%s_%d' % (mv, i + 1), N + f + '.png')
for i in (1, 2, 3): F['5b_%d' % i]['scale'] = 1.0          # back views: the head matcher can't see her face
F['2c_3'].update(scale=1.12, anchor='body_ground')    # turned away: only one foot is on the floor
for mv in ('jA', 'jB', 'jC'):
    for i in (1, 2, 3):
        fr('%s_%d' % (mv.lower(), i), '07_Air_Normals/%s/Leticia_%s_0%d.png' % (mv, mv, i), anchor='air')
F['jc_2']['scale'] = 0.99

# --- specials: 236 rekka, 623 rising kicks, 214 beams, j.236 flux board
for i in range(7): fr('rk_%d' % (i + 1), '08_236_Rekka/Leticia_08_236_Rekka_0%d.png' % (i + 1))
for i in (3, 4): F['rk_%d' % i]['scale'] = 0.84
for i in range(8): fr('dp_%d' % (i + 1), '09_623_DP/Leticia_09_623_DP_0%d.png' % (i + 1), **({} if i in (0, 7) else {'anchor': 'air'}))
for i in range(3): fr('co_%d' % (i + 1), '10_214_Beams/Character_Only/Leticia_Character_Only_0%d.png' % (i + 1))
for i in range(2, 9): fr('cb_%d' % i, '10_214_Beams/Combined/Leticia_Combined_0%d.png' % i)
for i in range(9):   # landing / dismount stand on the floor; their "rear foot" would be the board's tail, so the body centre is used
    fr('fb_%d' % (i + 1), '11_j236_Flux_Board/Leticia_11_j236_Flux_Board_0%d.png' % (i + 1), anchor='body_ground' if i in (6, 8) else 'air')
for i in (3, 6): F['fb_%d' % i]['scale'] = 1.0
F['fb_9']['scale'] = 0.93
for i in range(4):
    fr('fbfx_%d' % (i + 1), '12_Flux_Board_Effects/Leticia_12_Flux_Board_Effects_0%d.png' % (i + 1), anchor='center', scale=1.0, at=[0, 230])
F['fbfx_3']['at'] = [0, 80]                                  # the spin ring goes around the board
F['fbfx_4'].update(at=[-150, 320], scale=1.1)                # the corkscrew trails above and behind her

# --- movement on the board, backstep, downed, victory
M = '13_Movement_and_Victory/'
# the board movement drawings: scales from frame-to-frame matches (pairscale.py), so jumps and air dashes stay even
fr('ad_1', M + 'Leticia_AirDash_01.png', anchor='air', scale=1.05); fr('ad_2', M + 'Leticia_AirDash_02.png', anchor='air', scale=1.01)
fr('bad_1', M + 'Leticia_BackAirDash_01.png', anchor='air', scale=0.99); fr('bad_2', M + 'Leticia_BackAirDash_02.png', anchor='air', scale=1.07)
fr('bs_1', M + 'Leticia_BackStep_01.png', anchor='body_ground'); fr('bs_2', M + 'Leticia_BackStep_02.png', anchor='body_ground')
fr('bj_1', M + 'Leticia_BoardJump_01.png', anchor='body_ground', scale=1.05); fr('bj_2', M + 'Leticia_BoardJump_02.png', anchor='air', scale=0.985)
fr('bj_3', M + 'Leticia_BoardJump_03.png', anchor='air', scale=1.075)
fr('down', M + 'Leticia_Downed_01.png', anchor='lying', scale=1.15)
fr('victory', M + 'Leticia_Victory_01.png')

# --- supers
S = '14_Supers/'
fr('s1_1', S + 'Super1_01_Charge.png'); fr('s1_3', S + 'Super1_03_Recovery.png')
# the beam pose without its beam: the long beam layers (derive_leticia.py) draw it from the muzzles on
fr('s1_2', S + 'Super1_02_Beam.png', erase=[[700, 0, 1774, 640], [880, 640, 1774, 887]])
for i, n in enumerate(['01_BoardRush', '02_OrbTrigger', '03_OrbitHigh', '04_OrbitBack', '05_OrbitLow', '06_Land', '07_HairFlip', '08_HairFlipEnd']):
    fr('s2_%d' % (i + 1), S + 'Super2_%s.png' % n, anchor='air' if i in (1, 2, 3, 4) else 'body_ground')
for i in (3, 4, 5): F['s2_%d' % i]['scale'] = 0.92
fr('s2fx_orb', S + 'Super2_VFX_01_Orb.png', anchor='center', scale=0.9, at=[0, 260])
fr('s2fx_hit', S + 'Super2_VFX_02_OrbHit.png', anchor='center', scale=0.9, at=[0, 260])
fr('s2fx_boom', S + 'Super2_VFX_03_Explosion.png', anchor='center', scale=0.8, at=[0, 260])
fr('burst_boom', S + 'Super2_VFX_03_Explosion.png', anchor='center', scale=0.8, at=[70, 250])

# --- block stand-ins (no block drawings yet): braced backstep, crouched load, crossed arms in the air
fr('block_st', M + 'Leticia_BackStep_01.png', anchor='body_ground')
fr('block_cr', '09_623_DP/Leticia_09_623_DP_01.png')
fr('block_air', '07_Air_Normals/jB/Leticia_jB_01.png', anchor='air')
m.setdefault('frames', {}).update(F)   # update, so frames added by moves_leticia.py stay

# --- animations (names = AnimationData files without _AnimData.tres); keys: [frame, at, {rot, dx, dy, fx}]
AN = {}
def an(name, keys, **kw): AN[name] = {'keys': keys, **kw}
idle = [('Om3', 0), ('Om2', 5), ('Om1', 10), ('O0', 15), ('Op1', 20), ('Op2', 25), ('Op3', 30), ('Op2', 35), ('Op1', 40), ('O0', 45), ('Om1', 50), ('Om2', 55),
        ('Om3', 60), ('HBm3', 62), ('Bm2', 65), ('HBm2', 69), ('HBm1', 70), ('Om1', 72), ('O0', 75), ('Op1', 80), ('Op2', 85), ('Op3', 90), ('Op2', 95),
        ('Op1', 100), ('O0', 105), ('Om1', 110), ('Om2', 115)]
an('0_LET_Neutral', [['idle_' + a, t] for a, t in idle], duration=120)
an('1_LET_MoveF', [['wf_%d' % (i + 1), i * 9] for i in range(4)], duration=36)
an('2_LET_MoveB', [['wb_%d' % (i + 1), i * 10] for i in range(4)], duration=40)
an('3_LET_Jump', [['bj_1', 0], ['bj_2', 4], ['bj_3', 19]])
an('3b_LET_JumpForward', [['bj_1', 0], ['bj_2', 4, {'rot': -4}], ['bj_2', 10, {'rot': -8}], ['bj_3', 19]])
an('3c_LET_JumpBackward', [['bj_1', 0], ['bj_2', 4, {'rot': 6}], ['bj_2', 10, {'rot': 10}], ['bj_3', 19, {'rot': 4}]])
an('4_LET_Falling', [['bj_3', 0]])
an('5_LET_Landing', [['bj_1', 0], ['fb_9', 6]])
an('6_LET_CrouchEnter', [['crouch_1', 0], ['crouch_2', 4]])
an('7_LET_Crouching', [['crouch_2', 0]])
an('8_LET_CrouchExit', [['crouch_3', 0], ['crouch_1', 5]])
an('9_LET_DashFw', [['dash_1', 0], ['dash_2', 4], ['dash_3', 9], ['dash_3', 14, {'dy': -4}], ['dash_3', 19], ['dash_3', 24, {'dy': -4}], ['dash_3', 29]])
an('10_LET_RunStop', [['dash_4', 0]])
an('11_LET_DashBw', [['bs_1', 0], ['bs_2', 4], ['bs_1', 16]])
an('12_LET_AirDashFw', [['ad_1', 0], ['ad_2', 4], ['bj_3', 18]])
an('13_LET_AirDashDir', [['ad_1', 0], ['ad_2', 4], ['bj_3', 24]])
an('14_LET_AirDashBw', [['bad_1', 0], ['bad_2', 4], ['bj_3', 18]])
# Leticia has one damage drawing (heavy stagger): light hits use it with a smaller recoil
an('15_LET_Hit_Weak', [['dmg', 0, {'dx': -6, 'rot': 2}], ['dmg', 2, {'dx': -4, 'rot': 1}], ['dmg', 4, {'dx': -2}], ['dmg', 6]])
an('16_LET_Hit_Strong', [['dmg', 0, {'dx': -16, 'rot': 6}], ['dmg', 2, {'dx': -12, 'rot': 4}], ['dmg', 4, {'dx': -8, 'rot': 2}], ['dmg', 6, {'dx': -4}], ['dmg', 7]])
an('17_LET_Hit_Crouch', [['crouch_2', 0, {'dx': -6, 'rot': 4}], ['crouch_2', 2, {'dx': -4, 'rot': 2}], ['crouch_2', 4, {'dx': -2, 'rot': 1}], ['crouch_2', 7]])
an('18_LET_Hit_Sweep', [['dmg_air', 0, {'rot': 24}], ['dmg_air', 2, {'rot': 20}], ['dmg_air', 4, {'rot': 16}], ['dmg_air', 6, {'rot': 12}]])
an('19_LET_Hit_AirWeak', [['dmg_air', 0, {'rot': 10}], ['dmg_air', 2, {'rot': 12}], ['dmg_air', 4, {'rot': 9}], ['dmg_air', 6, {'rot': 5}]])
an('20_LET_Hit_AirStrong', [['dmg_air', 0, {'rot': 16}], ['dmg_air', 2, {'rot': 20}], ['dmg_air', 4, {'rot': 16}], ['dmg_air', 6, {'rot': 10}]])
an('21_LET_Hit_Fall1', [['dmg_air', 0, {'rot': 150}]])
an('21_LET_Hit_Fall2', [['dmg_air', 0, {'rot': 90}]])
an('21_LET_Hit_FallTransition', [['dmg_air', 0, {'rot': 45}]])
an('22_LET_Hit_Knockdown1', [['down', 0, {'dy': 14}], ['down', 6, {'dy': 6}]])
an('22_LET_Hit_Knockdown2', [['down', 0]])
an('22_LET_Hit_Knockdown3', [['down', 0], ['down', 4, {'dx': -4}], ['down', 8]])
an('23_LET_Hit_Down', [['down', 0]])
an('24_LET_Hit_GetUp', [['crouch_2', 0], ['crouch_3', 6]])
an('25_LET_Hit_LaunchAway', [['dmg_air', 0, {'rot': 35}]])
an('25_LET_Hit_LaunchDown', [['dmg_air', 0, {'rot': 120}]])
an('25_LET_Hit_LaunchUp', [['dmg_air', 0, {'rot': 15}]])
an('26_LET_Hit_GroundBounce', [['dmg_air', 0, {'rot': 90}], ['dmg_air', 12, {'rot': 60}]])
an('26_LET_Hit_WallBounce', [['dmg_air', 0, {'rot': -20}], ['dmg_air', 1, {'rot': 30}]])
an('27_LET_Hit_Crumple', [['dmg', 0], ['dmg', 10, {'rot': -6, 'dy': -6}], ['crouch_1', 20], ['crouch_2', 32]])
an('28_LET_Hit_KO', [['down', 0]])
an('29_LET_Stand_Block_Transition', [['block_st', 0]])
an('30_LET_Stand_Block', [['block_st', 0]])
an('31_LET_Stand_Blockstun', [['block_st', 0, {'dx': -6, 'rot': 2}], ['block_st', 2, {'dx': -4, 'rot': 1}], ['block_st', 4, {'dx': -2}], ['block_st', 7]])
an('32_LET_Crouch_Block_Transition', [['block_cr', 0]])
an('33_LET_Crouch_Block', [['block_cr', 0]])
an('34_LET_Crouch_Blockstun', [['block_cr', 0, {'dx': -6, 'rot': 2}], ['block_cr', 2, {'dx': -4, 'rot': 1}], ['block_cr', 4, {'dx': -2}], ['block_cr', 7]])
an('35_LET_Air_Block_Transition', [['block_air', 0]])
an('36_LET_Air_Block', [['block_air', 0]])
an('37_LET_Air_Blockstun', [['block_air', 0, {'dx': -6, 'rot': 3}], ['block_air', 2, {'dx': -4, 'rot': 2}], ['block_air', 4, {'dx': -2, 'rot': 1}], ['block_air', 7]])
an('48_LET_5A', [['5a_1', 0], ['5a_2', 5], ['5a_3', 11]])
an('49_LET_5B', [['5b_1', 0], ['5b_2', 8], ['5b_3', 18]])
an('50_LET_5C', [['5c_1', 0], ['5c_2', 13], ['5c_3', 21]])
an('51_LET_2A', [['2a_1', 0], ['2a_2', 5], ['2a_3', 10]])
an('52_LET_2B', [['2b_1', 0], ['2b_2', 5], ['2b_3', 7], ['2b_4', 11]])
an('53_LET_2C', [['2c_1', 0], ['2c_2', 9], ['2c_3', 14], ['2c_4', 22]], afterimages=False)
an('54_LET_j5A', [['ja_1', 0], ['ja_2', 4], ['ja_3', 10]])
an('55_LET_j5B', [['jb_1', 0], ['jb_2', 6], ['jb_3', 12]])
an('56_LET_j5C', [['jc_1', 0], ['jc_2', 9], ['jc_3', 16]])
an('57_LET_4A', [['5a_1', 0], ['5a_2', 7, {'dx': 12}], ['5a_3', 14]])
an('100_LET_Intro', [['s2_6', 0], ['s2_7', 30], ['s2_8', 52], ['idle_O0', 90]])
an('101_LET_Outro', [['victory', 0]])
an('200_LET_Recovery_Backwards', [['fb_4', 0], ['fb_3', 5], ['fb_2', 10], ['fb_8', 15]])
an('200_LET_Recovery_Forward', [['fb_2', 0], ['fb_3', 5], ['fb_4', 10], ['fb_8', 15]])
an('200_LET_Recovery_Neutral', [['fb_8', 0]])
an('1000_LET_Cancel', [['s1_1', 0]])
an('1001_LET_Burst', [['s1_1', 0, {'fx': 'burst_boom', 'fx_always': True}], ['s1_1', 14]])
an('LET_Breakthrough', [['5b_1', 0], ['5b_2', 8], ['5b_3', 18]])
m.setdefault('animations', {}).update(AN)

HF = {
    'skip': ['-1_Hitbox_CollisionOnly', '-2_Hitbox_CollisionOnly_Low', '100_Hitbox_Burst', '100_Hitbox_Cancel', 'LET_Hitbox_Invincible',
             'LET_Hitbox_Breakthrough_nhb2', '18_Hitbox_Grab_stUp', '19_Hitbox_Grab'],
    'split': {'3_Hitbox_FDash': {'3_Hitbox_AirDash': ['12_LET_AirDashFw', '13_LET_AirDashDir']},
              '4_Hitbox_BDash': {'4_Hitbox_AirDashBw': ['14_LET_AirDashBw']},
              '0_Hitbox_Horizontal': {'0_Hitbox_Lying': ['23_LET_Hit_Down']},
              '0_Hitbox_Basic': {'0_Hitbox_Lying': ['22_LET_Hit_Knockdown1', '22_LET_Hit_Knockdown2', '22_LET_Hit_Knockdown3']}},
    'fit_from': {'0_Hitbox_Basic': ['0_LET_Neutral', 0], '1_Hitbox_Crouch': ['7_LET_Crouching', 0], '3_Hitbox_FDash': ['9_LET_DashFw', 9],
                 '3_Hitbox_AirDash': ['12_LET_AirDashFw', 8], '4_Hitbox_AirDashBw': ['14_LET_AirDashBw', 8], '0_Hitbox_Lying': ['23_LET_Hit_Down', 0]},
    'attack_part': {'48_LET_5A': 'weapon', '51_LET_2A': 'weapon', '57_LET_4A': 'weapon', '49_LET_5B': 'weapon',
                    '52_LET_2B': 'trail', '50_LET_5C': 'trail', '53_LET_2C': 'trail', '55_LET_j5B': 'trail_all', '56_LET_j5C': 'trail'},
    'hair': {'hsv': [[160, 179, 90, 110], [0, 3, 90, 110]], 'head_frac': 0.24},
    'min_fx': 600,          # her lasers are thin
    'boxes': {},
}
hf = m.setdefault('hitfit', {})   # merged, so boxes / parts added by moves_leticia.py stay
for k, v in HF.items():
    if isinstance(v, dict) and isinstance(hf.get(k), dict): hf[k].update(v)
    else: hf[k] = v
json.dump(m, open(P, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(len(F), 'frames', len(AN), 'animations')
