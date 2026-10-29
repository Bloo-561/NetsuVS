# One-off helper that wrote manifests/cecilia.json. Edit the JSON directly from now on
# (re-running this would overwrite your edits).
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, 'manifests', 'cecilia.json')
m = json.load(open(P))
C = 'Cecilia_Original_Idle_Style/'; S = 'Cecilia_214_and_Supers/'; M = 'Cecilia/13_Movement_and_Victory/'
m['game'] = {'height_px': 500, 'pixel_size': 0.00275, 'sprites_subdir': 'v2', 'origin_from_rear': 0.5}
F = {}
def fr(fid, src, **kw): F[fid] = {'src': src, **kw}

# --- idle: one drawing (01_ready) breathing; eyes from the blink drawings
rows = [[0, 1.0], [230, 1.0], [560, 0.7], [860, 0.25], [905, 0.0], [1500, 0.0]]
A = 8.5
lv = {'m3': -A, 'm2': -A * 0.866, 'm1': -A * 0.5, '0': 0.0, 'p1': A * 0.5, 'p2': A * 0.866, 'p3': A}
for k, v in lv.items():
    fr('idle_O' + k, C + '01_Idle/01_ready.png', anchor='ref', breath=round(v, 2), breath_rows=rows)
blink = {'HB': {'src': C + '01_Idle/04_half_blink.png', 'shift': [9.4, 0.1], 'box': [625, 205, 800, 295], 'feather': 6},
         'B': {'src': C + '01_Idle/05_blink.png', 'shift': [10.0, 0.3], 'box': [625, 205, 800, 295], 'feather': 6}}
for e, k in [('HB', 'm3'), ('B', 'm2'), ('HB', 'm2'), ('HB', 'm1')]:
    fr('idle_%s%s' % (e, k), C + '01_Idle/01_ready.png', anchor='ref', breath=round(lv[k], 2), breath_rows=rows, blink=blink[e])

# --- core drawings
fr('crouch_1', C + '02_Crouch/01_transition.png'); fr('crouch_2', C + '02_Crouch/02_low_crouch.png')
for mv, d in [('5a', '03_Standing_5A'), ('2a', '04_Crouching_2A'), ('5b', '07_Ground_5B'), ('2b', '08_Ground_2B'), ('5c', '09_Ground_5C'), ('2c', '10_Ground_2C')]:
    for i, n in enumerate(['01_startup', '02_attack', '03_recovery']):
        fr('%s_%d' % (mv, i + 1), C + d + '/' + n + '.png')
for mv, d in [('ja', '11_Air_5A'), ('jb', '12_Air_5B'), ('jc', '13_Air_5C')]:
    for i, n in enumerate(['01_startup', '02_attack', '03_recovery']):
        fr('%s_%d' % (mv, i + 1), C + d + '/' + n + '.png', anchor='air')
fr('hit_l1', C + '05_Light_Damage/01_impact.png'); fr('hit_l2', C + '05_Light_Damage/02_recovery.png')
fr('hit_h1', C + '06_Heavy_Damage/01_impact.png'); fr('hit_h2', C + '06_Heavy_Damage/02_recovery.png')
fr('hit_l1_air', C + '05_Light_Damage/01_impact.png', anchor='air'); fr('hit_h1_air', C + '06_Heavy_Damage/01_impact.png', anchor='air')
for i, n in enumerate(['01_preparation', '02_dash', '03_slash', '04_recovery']):
    fr('d236_%d' % (i + 1), C + '14_236_Dash_Slash/' + n + '.png')
fr('dp_1', C + '15_623_Teleport/01_startup.png')
fr('dp_fx', C + '15_623_Teleport/02_normal_slash_effect.png', anchor='center', scale=1.0, at=[60, 330])
fr('dp_fx_ex', C + '15_623_Teleport/03_EX_slash_effect.png', anchor='center', scale=1.0, at=[60, 330])
fr('dp_4', C + '15_623_Teleport/04_reappear.png', anchor='air'); fr('dp_5', C + '15_623_Teleport/05_float_down.png', anchor='air')
fr('dp_6', C + '15_623_Teleport/06_landing.png')
L = S + '01_214_Lightning_Dash/'
fr('ld_charge', L + '01_charge.png')
fr('ld_hold', L + '02_held_lightning_form.png', anchor='center', scale=1.0, at=[0, 250])
for i in (1, 2, 3):
    fr('ld_loop%d' % i, L + '0%d_dash_loop_%d.png' % (i + 2, i), anchor='center', scale=1.0, at=[40, 230])
fr('ld_s1', L + '06_single_slash.png'); fr('ld_s2', L + '07_second_slash.png'); fr('ld_s3', L + '08_EX_third_slash.png'); fr('ld_rec', L + '09_recovery.png')
K = S + '02_Counter_Super/'
for i, n in enumerate(['01_counter_stance', '02_dash_preparation', '03_dash_slash', '04_launcher', '05_knockdown_slash', '06_kick', '07_final_slash',
                       '08_sheathing_start_corrected', '09_sheathing_nearly_closed', '10_sheath_click']):
    fr('cs_%d' % (i + 1), K + n + '.png', **({'anchor': 'air'} if i in (3, 4) else {}))
for i, n in enumerate(['11_explosion_ignition', '12_explosion_peak', '13_explosion_fade']):
    fr('cs_boom%d' % (i + 1), K + n + '.png', anchor='center', scale=0.75, at=[0, 260])
O = S + '03_AOE_Super_Corrected/'
fr('aoe_1', O + '01_front_preparation.png'); fr('aoe_2', O + '02_blade_ground_plunge.png'); fr('aoe_air', O + '03_air_blade_first_descent.png', anchor='air')
for i, n in enumerate(['04_surge_start', '05_surge_peak', '06_surge_fade']):
    fr('aoe_fx%d' % (i + 1), O + n + '.png', anchor='center', scale=0.8, at=[0, 110])
fr('aoe_rec', O + '07_recovery.png')
fr('airdash_1', M + 'Cecilia_AirDash_01.png', anchor='air'); fr('airdash_2', M + 'Cecilia_AirDash_02.png', anchor='air')
fr('bairdash_1', M + 'Cecilia_BackAirDash_01.png', anchor='air'); fr('bairdash_2', M + 'Cecilia_BackAirDash_02.png', anchor='air')
fr('backstep_1', M + 'Cecilia_BackStep_01.png'); fr('backstep_2', M + 'Cecilia_BackStep_02.png')
fr('down', M + 'Cecilia_Downed_01.png', anchor='lying', flip=True, scale=1.25)
fr('victory', M + 'Cecilia_Victory_01.png')
for i in range(4):
    fr('wf_%d' % (i + 1), 'Cecilia/Forward/Cecilia_Walk_Forward_0%d.png' % (i + 1))
    fr('wb_%d' % (i + 1), 'Cecilia/Backward/Cecilia_Walk_Backward_0%d.png' % (i + 1))
fr('block_st', K + '01_counter_stance.png'); fr('block_cr', C + '15_623_Teleport/01_startup.png')
fr('block_air', M + 'Cecilia_BackAirDash_01.png', anchor='air')
m['frames'] = F

# --- animations (names = AnimationData files without _AnimData.tres); keys: [frame, at, {rot, dx, dy, fx}]
AN = {}
def an(name, keys, **kw): AN[name] = {'keys': keys, **kw}
idle = [('Om3', 0), ('Om2', 5), ('Om1', 10), ('O0', 15), ('Op1', 20), ('Op2', 25), ('Op3', 30), ('Op2', 35), ('Op1', 40), ('O0', 45), ('Om1', 50), ('Om2', 55),
        ('Om3', 60), ('HBm3', 62), ('Bm2', 65), ('HBm2', 69), ('HBm1', 70), ('Om1', 72), ('O0', 75), ('Op1', 80), ('Op2', 85), ('Op3', 90), ('Op2', 95),
        ('Op1', 100), ('O0', 105), ('Om1', 110), ('Om2', 115)]
an('0_CEC_Neutral', [['idle_' + a, t] for a, t in idle], duration=120)
an('1_CEC_MoveF', [['wf_%d' % (i + 1), i * 8] for i in range(4)], duration=32)
an('2_CEC_MoveB', [['wb_%d' % (i + 1), i * 8] for i in range(4)], duration=32)
an('3_CEC_Jump', [['crouch_1', 0], ['ja_3', 4], ['dp_5', 19]])
an('3b_CEC_JumpForward', [['crouch_1', 0], ['ja_3', 4], ['airdash_1', 8, {'rot': -90}], ['airdash_1', 11, {'rot': -180}],
                          ['airdash_1', 14, {'rot': -270}], ['airdash_1', 17], ['dp_5', 20]])
an('3c_CEC_JumpBackward', [['crouch_1', 0], ['bairdash_1', 4], ['airdash_1', 8, {'rot': 90}], ['airdash_1', 11, {'rot': 180}],
                           ['airdash_1', 14, {'rot': 270}], ['bairdash_1', 17], ['dp_5', 20]])
an('4_CEC_Falling', [['dp_5', 0]])
an('5_CEC_Landing', [['crouch_1', 0], ['dp_6', 7]])
an('6_CEC_CrouchEnter', [['crouch_1', 0], ['crouch_2', 4]])
an('7_CEC_Crouching', [['crouch_2', 0]])
an('8_CEC_CrouchExit', [['crouch_2', 0], ['crouch_1', 4]])
an('9_CEC_DashFw', [['d236_1', 0], ['d236_2', 4], ['d236_2', 9, {'dy': -3}], ['d236_2', 14], ['d236_2', 19, {'dy': -3}], ['d236_2', 24], ['d236_2', 29, {'dy': -3}]])
an('10_CEC_RunStop', [['crouch_1', 0], ['dp_6', 9]])
an('11_CEC_DashBw', [['backstep_1', 0], ['backstep_2', 7], ['crouch_1', 18]])
an('12_CEC_AirDashFw', [['airdash_1', 0], ['airdash_2', 4], ['dp_5', 18]])
an('13_CEC_AirDashDir', [['airdash_1', 0], ['airdash_2', 4], ['dp_5', 24]])
an('14_CEC_AirDashBw', [['bairdash_1', 0], ['bairdash_2', 4], ['dp_5', 18]])
an('15_CEC_Hit_Weak', [['hit_l1', 0, {'dx': -8, 'rot': 2}], ['hit_l1', 2, {'dx': -6, 'rot': 1}], ['hit_l2', 4, {'dx': -4}], ['hit_l2', 6, {'dx': -2}], ['hit_l2', 7]])
an('16_CEC_Hit_Strong', [['hit_h1', 0, {'dx': -16, 'rot': 6}], ['hit_h1', 2, {'dx': -12, 'rot': 4}], ['hit_h2', 4, {'dx': -8, 'rot': 2}], ['hit_h2', 6, {'dx': -4}], ['hit_h2', 7]])
an('17_CEC_Hit_Crouch', [['crouch_2', 0, {'dx': -6, 'rot': 4}], ['crouch_2', 2, {'dx': -4, 'rot': 2}], ['crouch_2', 4, {'dx': -2, 'rot': 1}], ['crouch_2', 7]])
an('18_CEC_Hit_Sweep', [['hit_h1_air', 0, {'rot': 24}], ['hit_h1_air', 2, {'rot': 20}], ['hit_h1_air', 4, {'rot': 16}], ['hit_h1_air', 6, {'rot': 12}]])
an('19_CEC_Hit_AirWeak', [['hit_l1_air', 0, {'rot': 10}], ['hit_l1_air', 2, {'rot': 12}], ['hit_l1_air', 4, {'rot': 9}], ['hit_l1_air', 6, {'rot': 5}]])
an('20_CEC_Hit_AirStrong', [['hit_h1_air', 0, {'rot': 16}], ['hit_h1_air', 2, {'rot': 20}], ['hit_h1_air', 4, {'rot': 16}], ['hit_h1_air', 6, {'rot': 10}]])
an('21_CEC_Hit_Fall1', [['hit_h1_air', 0, {'rot': 150}]])
an('21_CEC_Hit_Fall2', [['hit_h1_air', 0, {'rot': 90}]])
an('21_CEC_Hit_FallTransition', [['hit_h1_air', 0, {'rot': 45}]])
an('22_CEC_Hit_Knockdown1', [['down', 0, {'dy': 14}], ['down', 6, {'dy': 6}]])
an('22_CEC_Hit_Knockdown2', [['down', 0]])
an('22_CEC_Hit_Knockdown3', [['down', 0], ['down', 4, {'dx': -4}], ['down', 8]])
an('23_CEC_Hit_Down', [['down', 0]])
an('24_CEC_Hit_GetUp', [['crouch_2', 0], ['crouch_1', 6]])
an('25_CEC_Hit_LaunchAway', [['hit_h1_air', 0, {'rot': 35}]])
an('25_CEC_Hit_LaunchDown', [['hit_h1_air', 0, {'rot': 120}]])
an('25_CEC_Hit_LaunchUp', [['hit_h1_air', 0, {'rot': 15}]])
an('26_CEC_Hit_GroundBounce', [['hit_h1_air', 0, {'rot': 90}], ['hit_h1_air', 12, {'rot': 60}]])
an('26_CEC_Hit_WallBounce', [['hit_h1_air', 0, {'rot': -20}], ['hit_h1_air', 1, {'rot': 30}]])
an('27_CEC_Hit_Crumple', [['hit_h2', 0], ['hit_h1', 10, {'rot': -6, 'dy': -6}], ['crouch_1', 20], ['crouch_2', 32]])
an('28_CEC_Hit_KO', [['down', 0]])
an('29_CEC_Stand_Block_Transition', [['block_st', 0]])
an('30_CEC_Stand_Block', [['block_st', 0]])
an('31_CEC_Stand_Blockstun', [['block_st', 0, {'dx': -6, 'rot': 2}], ['block_st', 2, {'dx': -4, 'rot': 1}], ['block_st', 4, {'dx': -2}], ['block_st', 7]])
an('32_CEC_Crouch_Block_Transition', [['block_cr', 0]])
an('33_CEC_Crouch_Block', [['block_cr', 0]])
an('34_CEC_Crouch_Blockstun', [['block_cr', 0, {'dx': -6, 'rot': 2}], ['block_cr', 2, {'dx': -4, 'rot': 1}], ['block_cr', 4, {'dx': -2}], ['block_cr', 7]])
an('35_CEC_Air_Block_Transition', [['block_air', 0]])
an('36_CEC_Air_Block', [['block_air', 0]])
an('37_CEC_Air_Blockstun', [['block_air', 0, {'dx': -6, 'rot': 3}], ['block_air', 2, {'dx': -4, 'rot': 2}], ['block_air', 4, {'dx': -2, 'rot': 1}], ['block_air', 7]])
an('48_CEC_5A', [['5a_1', 0], ['5a_2', 5], ['5a_3', 11]])
an('49_CEC_5B', [['5b_1', 0], ['5b_2', 8], ['5b_3', 18]])
an('50_CEC_5C', [['5c_1', 0], ['5c_2', 13], ['5c_3', 21]])
an('51_CEC_2A', [['2a_1', 0], ['2a_2', 5], ['2a_3', 10]])
an('52_CEC_2B', [['2b_1', 0], ['2b_2', 7], ['2b_3', 13]])
an('53_CEC_2C', [['2c_1', 0], ['2c_2', 9], ['2c_3', 25]])
an('54_CEC_j5A', [['ja_1', 0], ['ja_2', 4], ['ja_3', 10]])
an('55_CEC_j5B', [['jb_1', 0], ['jb_2', 6], ['jb_3', 12]])
an('56_CEC_j5C', [['jc_1', 0], ['jc_2', 9], ['jc_3', 18]])
an('57_CEC_4A', [['5a_1', 0], ['5a_2', 7, {'dx': 12}], ['5a_3', 14]])
an('60_CEC_LD_A', [['ld_charge', 0], ['ld_loop1', 7], ['ld_loop2', 9], ['ld_s1', 11], ['ld_rec', 19]])
ldb = [['ld_charge', 0], ['ld_hold', 12], ['ld_charge', 16], ['ld_loop1', 22], ['ld_loop2', 24], ['ld_loop3', 26], ['ld_s1', 28], ['ld_s2', 32], ['ld_rec', 41]]
an('61_CEC_LD_B', ldb)
an('62_CEC_LD_Bfar', [list(k) for k in ldb])
ex = [['ld_charge', 0], ['ld_loop1', 7], ['ld_loop2', 9], ['ld_s1', 11], ['ld_loop3', 16], ['ld_loop1', 18], ['ld_s2', 20], ['ld_loop2', 25], ['ld_loop3', 27],
      ['ld_s3', 29], ['ld_loop1', 34], ['ld_loop2', 36], ['ld_s1', 38], ['ld_s2', 41], ['ld_rec', 50], ['ld_s3', 64, {'fx': 'cs_boom2'}], ['ld_rec', 73]]
an('63_CEC_LD_EX', ex)
an('64_CEC_LD_A_Hold', [['ld_hold', 0], ['ld_rec', 4]])
an('65_CEC_LD_B_Hold', [['ld_hold', 0], ['ld_loop1', 3], ['ld_loop2', 5], ['ld_s1', 8], ['ld_s2', 12], ['ld_rec', 20]])
an('100_CEC_Intro', [['cs_8', 0], ['cs_9', 20], ['cs_10', 40], ['cs_10', 44, {'fx': 'cs_boom1'}], ['cs_10', 50, {'fx': 'cs_boom2'}],
                     ['cs_10', 58, {'fx': 'cs_boom3'}], ['cs_10', 66], ['idle_O0', 90]])
an('101_CEC_Outro', [['victory', 0]])
an('200_CEC_Recovery_Backwards', [['airdash_1', 0], ['airdash_1', 5, {'rot': 90}], ['airdash_1', 10, {'rot': 180}], ['airdash_1', 15, {'rot': 270}]])
an('200_CEC_Recovery_Forward', [['airdash_1', 0], ['airdash_1', 5, {'rot': -90}], ['airdash_1', 10, {'rot': -180}], ['airdash_1', 15, {'rot': -270}]])
an('200_CEC_Recovery_Neutral', [['bairdash_2', 0]])
an('1000_CEC_Cancel', [['ld_charge', 0]])
an('1001_CEC_Burst', [['ld_charge', 0, {'fx': 'cs_boom1'}], ['ld_charge', 6, {'fx': 'cs_boom2'}], ['ld_charge', 20, {'fx': 'cs_boom3'}], ['ld_charge', 30]])
an('CEC_Breakthrough', [['5b_1', 0], ['5b_2', 8], ['5b_3', 18]])
m['animations'] = AN
json.dump(m, open(P, 'w'), indent=1)
print(len(F), 'frames', len(AN), 'animations')
