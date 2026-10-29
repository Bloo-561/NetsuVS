"""SOUNDS (Oct 24 2026, night): which state plays which sound, on which frame.

    python tools/sprite_port/sounds.py             # puts every cue below into the state files
    python tools/sprite_port/sounds.py --check     # only lists what would change
    python tools/sprite_port/sounds.py --remove    # takes them all out again
    python tools/sprite_port/sounds.py cecilia     # one actor folder (cecilia, flan, leticia, mary, adin, eren, harie)

The sound files themselves are placeholders made by tools/fx/make_fight_sfx.py. To use your own sound, save it over
the .wav with the same name (Godot re-imports it). For a different name or format, change its path in SOUNDS below
and run this script again (it adds the new file to the sound list).

How a cue works: it becomes a FrameDataEvent in the state, [AtFrame(frame)] -> PlaySoundAction(Source, Index), so
you can see and edit it in Godot like any other event. Frame 0 goes into OnEnterEvents instead (then it also plays
when a hit or a throw puts the fighter into the state: a state entered that way never runs its frame 0 tick).
The events this script adds have sub-resource ids starting with "sfx_": running it again replaces them (never doubles
them), and the engine's own sound events (footsteps, jumps, landing) or yours are left alone.
Index = the sound's place in actors/_shared/sakuga/Shared_SFXList.tres (every fighter and assist uses that list); new
sounds are added at its end, so the indices already in use never move.

The fighter-data kit (fdk.py) applies these cues too whenever moves_*.py / assists.py / throws.py rewrite a state,
so re-running those scripts keeps the sounds.

Sound players: a fighter has 5 (SFX_0..4). 0 and 1 are the engine's movement sounds. This table uses 2 = swings and
shots, 3 = effects (lightning, sparkles, beams, teleports), 4 = the big ones (thunder, explosions, throws). A new
sound on a player stops the one it was playing, so things that must overlap go on different players.
Assists have one player (0): their cues always use it.

Timing: a swing's sound starts 2 frames before its first active frame (it peaks when the hit comes out), a shot's
1 frame before (the crack is instant). The hit and block sounds themselves come from the hit effects, not from here.
"""
import os, re, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fdk
from tres import Tres

SFX_LIST = 'res://actors/_shared/sakuga/Shared_SFXList.tres'
FDE = fdk.FDE + 'FrameDataEvent.cs'
AT = fdk.CON + 'AtFrameCondition.cs'
PLAY = fdk.ACT + 'PlaySoundAction.cs'

# ------------------------------------------------------------------------------------------------------------------
# the sounds: name -> (file, default player)
# ------------------------------------------------------------------------------------------------------------------
SW, FX, BIG = 2, 3, 4
C, F, L = 'res://actors/cecilia/Sounds/', 'res://actors/flan/Sounds/', 'res://actors/leticia/Sounds/'
A = 'res://actors/assists/'
SOUNDS = {
    # engine sounds used here too
    'land':               ('res://actors/_shared/sakuga/SFX/DoNotUse/Footstep_Landing2.wav', 1),
    # shared
    'throw_reach':        ('res://assets/audio/sfx/fight/throw_reach.wav', SW),
    'throw_grab':         ('res://assets/audio/sfx/fight/throw_grab.wav', BIG),
    'throw_break':        ('res://assets/audio/sfx/fight/throw_break.wav', BIG),
    # Cecilia
    'cec_slash_light':    (C + 'slash_light.wav', SW),
    'cec_slash_medium':   (C + 'slash_medium.wav', SW),
    'cec_slash_heavy':    (C + 'slash_heavy.wav', SW),
    'cec_lightning_dash': (C + 'lightning_dash.wav', FX),
    'cec_lightning_slash': (C + 'lightning_slash.wav', SW),
    'cec_dash_rush':      (C + 'dash_rush.wav', FX),
    'cec_teleport':       (C + 'teleport.wav', FX),
    'cec_counter_stance': (C + 'counter_stance.wav', FX),
    'cec_thunderclap':    (C + 'thunderclap.wav', BIG),
    'cec_thunder_barrage': (C + 'thunder_barrage.wav', BIG),
    'cec_thunder_impact': (C + 'thunder_impact.wav', BIG),
    'cec_plunge_dive':    (C + 'plunge_dive.wav', FX),
    # Flan
    'fln_punch_light':    (F + 'punch_light.wav', SW),
    'fln_punch_medium':   (F + 'punch_medium.wav', SW),
    'fln_punch_heavy':    (F + 'punch_heavy.wav', SW),
    'fln_star_fist':      (F + 'star_fist.wav', SW),
    'fln_supernova':      (F + 'supernova.wav', SW),
    'fln_armor_glint':    (F + 'armor_glint.wav', FX),
    'fln_rising_star':    (F + 'rising_star.wav', FX),
    'fln_star_burst':     (F + 'star_burst.wav', BIG),
    'fln_meteor_rise':    (F + 'meteor_rise.wav', SW),
    'fln_meteor_fall':    (F + 'meteor_fall.wav', FX),
    'fln_meteor_impact':  (F + 'meteor_impact.wav', BIG),
    'fln_meteor_impact_big': (F + 'meteor_impact_big.wav', BIG),
    'fln_radiant_rush':   (F + 'radiant_rush.wav', FX),
    'fln_radiant_burst':  (F + 'radiant_burst.wav', BIG),
    'fln_explosion_big':  (F + 'explosion_big.wav', BIG),
    # Leticia
    'let_swing_light':    (L + 'swing_light.wav', SW),
    'let_swing_medium':   (L + 'swing_medium.wav', SW),
    'let_swing_heavy':    (L + 'swing_heavy.wav', SW),
    'let_gunshot':        (L + 'gunshot.wav', SW),
    'let_gunshot_double': (L + 'gunshot_double.wav', SW),
    'let_comet_kick':     (L + 'comet_kick.wav', FX),
    'let_photon_beam':    (L + 'photon_beam.wav', FX),
    'let_ricochet':       (L + 'ricochet.wav', FX),
    'let_prism_beam':     (L + 'prism_beam.wav', BIG),
    'let_board_flip':     (L + 'board_flip.wav', SW),
    'let_board_spin':     (L + 'board_spin.wav', FX),
    'let_stardrive_charge': (L + 'stardrive_charge.wav', FX),
    'let_stardrive_beam': (L + 'stardrive_beam.wav', BIG),
    'let_crimson_rush':   (L + 'crimson_rush.wav', FX),
    'let_flame_shot':     (L + 'flame_shot.wav', SW),
    'let_flame_trap':     (L + 'flame_trap.wav', BIG),
    'let_flame_explosion': (L + 'flame_explosion.wav', BIG),
    # assists (one player each)
    'mry_encore':         (A + 'mary/Sounds/encore.wav', 0),
    'mry_fermata':        (A + 'mary/Sounds/fermata.wav', 0),
    'mry_note_chime':     (A + 'mary/Sounds/note_chime.wav', 0),
    'mry_note_burst':     (A + 'mary/Sounds/note_burst.wav', 0),
    'adn_shield_raise':   (A + 'adin/Sounds/shield_raise.wav', 0),
    'adn_shield_block':   (A + 'adin/Sounds/shield_block.wav', 0),
    'adn_shield_bash':    (A + 'adin/Sounds/shield_bash.wav', 0),
    'adn_rush_run':       (A + 'adin/Sounds/rush_run.wav', 0),
    'ern_slash':          (A + 'eren/Sounds/slash.wav', 0),
    'ern_dash':           (A + 'eren/Sounds/dash.wav', 0),
    'ern_jump':           (A + 'eren/Sounds/jump.wav', 0),
    'ern_spin':           (A + 'eren/Sounds/spin.wav', 0),
    'hre_dive':           (A + 'harie/Sounds/dive.wav', 0),
    'hre_burst':          (A + 'harie/Sounds/burst.wav', 0),
    'hre_wave':           (A + 'harie/Sounds/wave.wav', 0),
    'hre_wave_launch':    (A + 'harie/Sounds/wave_launch.wav', 0),
}

# ------------------------------------------------------------------------------------------------------------------
# the cues: state file -> [(frame, sound) or (frame, sound, player)]
# (first active frames from each state's animation data; a state's frame 0 is the frame it starts)
# ------------------------------------------------------------------------------------------------------------------
def throws(tag, folder, hit_frames):
    """the throw states every fighter has (tools/sprite_port/throws.py): reach, grab on connect, the hit(s), break"""
    s = 'res://actors/%s/States/%s_' % (folder, tag)
    return {
        s + 'Throw.tres': [(2, 'throw_reach')],
        s + 'ThrowForward.tres': [(0, 'throw_grab')] + hit_frames,
        s + 'ThrowBack.tres': [(0, 'throw_grab')] + hit_frames,
        s + 'ThrowBreak.tres': [(0, 'throw_break')],
    }


def states(folder, table):
    return {'res://actors/%s/States/%s.tres' % (folder, k): v for k, v in table.items()}


CUES = {}
# --- Cecilia: sword + lightning ------------------------------------------------------------------------------------
CUES.update(states('cecilia', {
    '63_CEC_5A': [(3, 'cec_slash_light')],
    '64_CEC_5B': [(6, 'cec_slash_medium')],
    '65_CEC_5C': [(11, 'cec_slash_heavy')],
    '66_CEC_2A': [(3, 'cec_slash_light')],
    '67_CEC_2B': [(5, 'cec_slash_medium')],
    '68_CEC_2C': [(7, 'cec_slash_medium'), (12, 'cec_slash_heavy')],
    '69_CEC_J5A': [(2, 'cec_slash_light')],
    '70_CEC_J5B': [(4, 'cec_slash_medium')],
    '71_CEC_J5C': [(7, 'cec_slash_heavy')],
    '72_CEC_4A': [(5, 'cec_slash_light')],
    # Lightning Dash: the dash, then the slash follow-ups
    '73_CEC_214A': [(7, 'cec_lightning_dash')],
    '74_CEC_214B': [(9, 'cec_lightning_dash')],
    '76_CEC_214C': [(4, 'cec_lightning_dash')],
    '75_CEC_214A_SL': [(0, 'cec_lightning_slash')],
    '77_CEC_214B_SL': [(0, 'cec_lightning_slash'), (8, 'cec_slash_medium')],
    '78_CEC_214C_SL': [(0, 'cec_lightning_slash'), (8, 'cec_slash_medium'), (16, 'cec_slash_heavy')],
    # Dash Slash: the rush, then the cut
    '79_CEC_236A': [(3, 'cec_dash_rush'), (9, 'cec_slash_heavy')],
    '80_CEC_236B': [(5, 'cec_dash_rush'), (13, 'cec_slash_heavy')],
    '81_CEC_236C': [(2, 'cec_dash_rush'), (13, 'cec_lightning_slash')],
    # Teleport Slash: the rising cut, then she blinks into the air
    '82_CEC_623A': [(4, 'cec_slash_heavy'), (14, 'cec_teleport')],
    '83_CEC_623B': [(6, 'cec_slash_heavy'), (16, 'cec_teleport')],
    '84_CEC_623C': [(3, 'cec_lightning_slash'), (13, 'cec_teleport')],
    '98_CEC_TP_LAND': [(0, 'land')],
    # Counter · Thunderclap: the stance hums; on a counter she blinks around them cutting, then the thunderclap
    '85_CEC_S1': [(0, 'cec_counter_stance')],
    '92_CEC_S1_hit': [(9, 'cec_teleport'), (12, 'cec_slash_heavy'), (17, 'cec_teleport'), (18, 'cec_slash_medium'),
                      (33, 'cec_teleport'), (35, 'cec_slash_heavy'), (49, 'cec_teleport'), (52, 'cec_slash_medium'),
                      (63, 'cec_teleport'), (65, 'cec_lightning_slash'), (75, 'cec_teleport'), (108, 'cec_thunderclap')],
    # Thunder Plunge
    '93_CEC_S2': [(9, 'cec_thunder_barrage')],
    '94_CEC_S2_air': [(0, 'cec_plunge_dive')],
    '95_CEC_S2_land': [(0, 'cec_thunder_impact')],
    # EX Dash Slash rush
    '97_CEC_RUSH': [(0, 'cec_teleport'), (7, 'cec_slash_medium'), (19, 'cec_slash_heavy'), (31, 'cec_slash_medium'),
                    (43, 'cec_slash_heavy'), (76, 'cec_thunderclap')],
}))
CUES.update(throws('CEC', 'cecilia', [(6, 'cec_slash_heavy')]))

# --- Flan: star fists ------------------------------------------------------------------------------------------------
CUES.update(states('flan', {
    '63_FLN_5A': [(3, 'fln_punch_light')],
    '64_FLN_5B': [(6, 'fln_punch_medium')],
    '65_FLN_5C': [(11, 'fln_punch_heavy')],
    '66_FLN_2A': [(3, 'fln_punch_light')],
    '67_FLN_2B': [(5, 'fln_punch_medium')],
    '68_FLN_2C': [(7, 'fln_punch_medium'), (12, 'fln_punch_heavy')],
    '69_FLN_J5A': [(2, 'fln_punch_light')],
    '70_FLN_J5B': [(4, 'fln_punch_medium')],
    '71_FLN_J5C': [(7, 'fln_punch_heavy')],
    '72_FLN_6C': [(14, 'fln_punch_heavy')],
    '73_FLN_236A': [(6, 'fln_star_fist')],
    '74_FLN_236B': [(4, 'fln_armor_glint'), (22, 'fln_star_fist')],
    '75_FLN_236C': [(14, 'fln_supernova')],
    '76_FLN_623A': [(2, 'fln_rising_star')],
    '77_FLN_623B': [(2, 'fln_rising_star')],
    '78_FLN_623C': [(2, 'fln_punch_heavy'), (10, 'fln_rising_star'), (35, 'fln_star_burst')],
    '80_FLN_DPLAND': [(0, 'land')],
    '81_FLN_214A': [(3, 'fln_meteor_rise'), (23, 'fln_meteor_fall')],
    '82_FLN_214B': [(3, 'fln_meteor_rise'), (27, 'fln_meteor_fall')],
    '83_FLN_214C': [(3, 'fln_meteor_rise'), (23, 'fln_meteor_fall')],
    '84_FLN_IMPACT': [(0, 'fln_meteor_impact')],
    '85_FLN_IMPACT_C': [(0, 'fln_meteor_impact_big')],
    '92_FLN_S1': [(22, 'fln_radiant_rush')],
    '93_FLN_S1_hit': [(5, 'fln_radiant_burst')],
    '94_FLN_S2': [(23, 'fln_rising_star')],
    '95_FLN_S2_hit': [(7, 'fln_meteor_fall')],
    '97_FLN_S2_boom': [(0, 'fln_explosion_big')],
}))
CUES.update(throws('FLN', 'flan', [(5, 'fln_punch_medium'), (12, 'fln_punch_heavy')]))

# --- Leticia: guns, beams, hover board -------------------------------------------------------------------------------
CUES.update(states('leticia', {
    '63_LET_5A': [(3, 'let_swing_light')],
    '64_LET_5B': [(6, 'let_swing_medium')],
    '65_LET_5C': [(12, 'let_gunshot_double')],
    '66_LET_2A': [(3, 'let_swing_light')],
    '67_LET_2B': [(5, 'let_gunshot')],
    '68_LET_2C': [(8, 'let_gunshot'), (13, 'let_gunshot')],
    '69_LET_J5A': [(2, 'let_swing_light')],
    '70_LET_J5B': [(5, 'let_gunshot_double')],
    '71_LET_J5C': [(7, 'let_swing_heavy')],
    '72_LET_4A': [(5, 'let_swing_light')],
    # Crossfire
    '73_LET_R1A': [(7, 'let_gunshot')],
    '74_LET_R1B': [(9, 'let_gunshot')],
    '75_LET_R2': [(5, 'let_gunshot')],
    '76_LET_R3': [(7, 'let_gunshot_double')],
    '77_LET_REX': [(4, 'let_gunshot'), (14, 'let_gunshot'), (25, 'let_gunshot_double')],
    # Rising Comet / Comet Burst
    '78_LET_623A': [(2, 'let_comet_kick')],
    '79_LET_623B': [(2, 'let_comet_kick'), (13, 'let_swing_medium')],
    '80_LET_623C': [(2, 'let_comet_kick'), (11, 'let_swing_medium'), (23, 'let_gunshot_double')],
    '98_LET_DPLAND': [(0, 'land')],
    # beams
    '81_LET_214A': [(11, 'let_photon_beam')],
    '82_LET_214B': [(13, 'let_ricochet')],
    '83_LET_214C': [(4, 'let_gunshot'), (15, 'let_ricochet'), (33, 'let_prism_beam')],
    # Flux Dive / Flux Storm: board flips, then the twirl down
    '84_LET_FA': [(8, 'let_board_flip'), (17, 'let_board_spin')],
    '85_LET_FB': [(8, 'let_board_flip'), (21, 'let_board_flip'), (30, 'let_board_spin')],
    '92_LET_FC': [(8, 'let_board_flip'), (21, 'let_board_flip'), (34, 'let_swing_heavy')],
    '93_LET_FLAND': [(0, 'land')],
    # supers
    '94_LET_S1': [(2, 'let_stardrive_charge'), (21, 'let_stardrive_beam')],
    '95_LET_S2': [(7, 'let_crimson_rush')],
    '97_LET_S2_hit': [(0, 'let_flame_trap'), (4, 'let_flame_shot'), (17, 'let_gunshot'), (24, 'let_gunshot'),
                      (35, 'let_gunshot'), (42, 'let_gunshot'), (53, 'let_gunshot_double'), (105, 'let_flame_explosion')],
}))
CUES.update(throws('LET', 'leticia', [(7, 'let_gunshot_double')]))

# --- Noah: devil arm, shadow and void (borrowed sounds until he has his own) ------------------------------------------
CUES.update(states('noah', {
    '63_NOA_5A': [(3, 'fln_punch_light')],
    '64_NOA_5B': [(6, 'fln_punch_medium')],
    '65_NOA_5C': [(11, 'fln_punch_heavy')],
    '66_NOA_2A': [(3, 'fln_punch_light')],
    '67_NOA_2B': [(5, 'fln_punch_medium')],
    '68_NOA_2C': [(8, 'fln_punch_heavy')],
    '69_NOA_J5A': [(2, 'fln_punch_light')],
    '70_NOA_J5B': [(5, 'fln_punch_medium')],
    '71_NOA_J5C': [(7, 'fln_punch_heavy')],
    '72_NOA_6C': [(7, 'fln_punch_heavy')],
    '73_NOA_236A': [(12, 'hre_wave')],
    '74_NOA_236B': [(12, 'hre_wave'), (24, 'hre_wave')],
    '75_NOA_236C': [(16, 'hre_wave_launch')],
    '76_NOA_623A': [(8, 'fln_armor_glint')],
    '77_NOA_623B': [(10, 'fln_armor_glint')],
    '78_NOA_623C': [(6, 'fln_armor_glint')],
    '79_NOA_SNAP': [(5, 'cec_teleport')],
    '80_NOA_214A': [(9, 'fln_punch_heavy')],
    '81_NOA_GRASP': [(13, 'fln_star_burst'), (27, 'fln_radiant_burst')],
    '82_NOA_214B': [(5, 'let_swing_medium'), (16, 'fln_punch_heavy')],
    '83_NOA_214C': [(7, 'fln_punch_heavy')],
    '84_NOA_DEVOUR': [(20, 'fln_star_burst'), (30, 'fln_explosion_big')],
    '85_NOA_RAY': [(13, 'let_prism_beam')],
    '92_NOA_jGRASP': [(6, 'let_swing_medium')],
    '94_NOA_jGRASP_land': [(0, 'fln_meteor_impact_big')],
    '95_NOA_jHAMMER': [(6, 'fln_punch_heavy')],
    '97_NOA_LAND': [(0, 'land')],
    '105_NOA_S1': [(13, 'fln_meteor_impact_big'), (27, 'fln_supernova'), (76, 'fln_explosion_big')],
    '107_NOA_S2': [(10, 'fln_radiant_rush')],
    '109_NOA_S2_slams': [(8, 'fln_meteor_impact'), (26, 'fln_meteor_impact'), (44, 'fln_meteor_impact_big')],
    '110_NOA_S2_finish': [(12, 'fln_star_burst'), (30, 'fln_explosion_big')],
    '111_NOA_S2_land': [(0, 'land')],
}))
CUES.update(throws('NOA', 'noah', [(6, 'fln_punch_medium'), (14, 'fln_punch_heavy')]))

# --- assists ---------------------------------------------------------------------------------------------------------
CUES.update(states('assists/mary', {
    '1_MRY_5S': [(13, 'mry_encore')],         # plays from frame 14; the song peaks on 50 (her buff)
    '2_MRY_6S': [(13, 'mry_fermata')],        # the note leaves on frame 26
    '1_MRYN_Float': [(0, 'mry_note_chime')],
    '2_MRYN_Boom': [(0, 'mry_note_burst')],
}))
CUES.update(states('assists/adin', {
    '1_ADN_5S': [(1, 'adn_shield_raise')],
    '2_ADN_5S_hit': [(0, 'adn_shield_block'), (12, 'adn_shield_bash')],
    '3_ADN_6S': [(0, 'adn_rush_run')],
    '4_ADN_6S_return': [(6, 'adn_rush_run')],
    '5_ADN_6S_hit': [(0, 'adn_shield_bash')],
}))
CUES.update(states('assists/eren', {
    '5_ERN_dash': [(0, 'ern_dash')],
    '2_ERN_hits': [(0, 'ern_slash'), (10, 'ern_slash')],
    '3_ERN_6S': [(5, 'ern_jump'), (14, 'ern_spin')],
    '4_ERN_6S_land': [(0, 'land')],
    '6_ERN_rdash': [(0, 'ern_dash')],
    '7_ERN_rhits': [(0, 'ern_slash'), (10, 'ern_slash')],
}))
CUES.update(states('assists/harie', {
    '1_HRE_5S': [(12, 'hre_dive')],
    '3_HRE_up': [(0, 'hre_burst')],
    '4_HRE_6S': [(0, 'hre_wave')],
    '5_HRE_6S_carry': [(14, 'hre_wave_launch')],
}))

GROUPS = {'cecilia': 'actors/cecilia/', 'flan': 'actors/flan/', 'leticia': 'actors/leticia/', 'noah': 'actors/noah/', 'mary': 'actors/assists/mary/',
          'adin': 'actors/assists/adin/', 'eren': 'actors/assists/eren/', 'harie': 'actors/assists/harie/'}


# ------------------------------------------------------------------------------------------------------------------
# the sound list
# ------------------------------------------------------------------------------------------------------------------
_indices = None


def sfx_indices(write=True):
    """{sound file: index in Shared_SFXList}; adds the sounds of SOUNDS that aren't in it yet (at the end)"""
    global _indices
    if _indices is not None:
        return _indices
    path = fdk.res_file(SFX_LIST)
    cur = open(path, encoding='utf-8').read()
    t = Tres(cur)
    refs = re.findall(r'ExtResource\("([^"]+)"\)', t.res_get('Sounds') or '')
    order = [(t.ext_by_id(r) or {}).get('path') for r in refs]
    added = []
    for name, (res, _) in SOUNDS.items():
        if res in order:
            continue
        if not os.path.exists(fdk.res_file(res)):
            print('missing sound file (run tools/fx/make_fight_sfx.py): ' + res)
            continue
        i = t.add_ext('AudioStream', res, fdk.res_uid(res), prefer_id='sfx_' + name)
        refs.append(i); order.append(res); added.append(res)
    if added:
        t.res_set('Sounds', '[' + ', '.join('ExtResource("%s")' % r for r in refs) + ']')
        txt = t.text()
        if write:
            open(path, 'w', encoding='utf-8', newline='\n').write(txt)
            st = fdk._state()
            if st.get(SFX_LIST) == fdk.md5(cur):
                st[SFX_LIST] = fdk.md5(txt); fdk._save_state()
        print('sound list: added %d sounds at the end of %s' % (len(added), SFX_LIST))
    _indices = {}
    for k, p in enumerate(order):
        _indices.setdefault(p, k)     # a file listed twice: its first place
    return _indices


def resolve(res):
    """[(frame, index, player)] for a state file, or None when it has no cues"""
    cues = CUES.get(res)
    if not cues:
        return None
    idx = sfx_indices()
    assist = '/actors/assists/' in res
    out = []
    for c in cues:
        frame, name = c[0], c[1]
        path, player = SOUNDS[name]
        if len(c) > 2:
            player = c[2]
        if assist:
            player = 0
        if path not in idx:
            continue
        out.append((frame, idx[path], player))
    return out


# ------------------------------------------------------------------------------------------------------------------
# patching a state's text
# ------------------------------------------------------------------------------------------------------------------
def _list(t, key):
    v = t.res_get(key)
    if not v or v == 'null':
        return []
    return re.findall(r'(?:Ext|Sub)Resource\("[^"]+"\)', v)


def _set_list(t, key, refs):
    t.res_set(key, ('[' + ', '.join(refs) + ']') if refs else 'null')


def _plain_events(t):
    """(frame, index, player, where) of the sound events NOT made by this script (to avoid doubling them)"""
    out = set()
    for key, where in (('OnTickEvents', 'tick'), ('OnEnterEvents', 'enter')):
        for r in _list(t, key):
            sid = re.search(r'"([^"]+)"', r).group(1)
            s = t.sub_get(sid)
            if not s or sid.startswith('sfx_'):
                continue
            body = '\n'.join(s[2])
            cond = re.findall(r'SubResource\("([^"]+)"\)', (re.search(r'Conditions = (.*)', body) or [None, ''])[1] or '')
            acts = re.findall(r'SubResource\("([^"]+)"\)', (re.search(r'Actions = (.*)', body) or [None, ''])[1] or '')
            frame = 0
            if cond:
                c = t.sub_get(cond[0])
                if not c or len(cond) > 1 or not t.script_of(c[2]).endswith('AtFrameCondition.cs'):
                    continue
                m = re.search(r'Frame = (\d+)', '\n'.join(c[2])); frame = int(m.group(1)) if m else 0
            for a in acts:
                sa = t.sub_get(a)
                if sa and t.script_of(sa[2]).endswith('PlaySoundAction.cs'):
                    b = '\n'.join(sa[2])
                    mi = re.search(r'\bIndex = (\d+)', b); ms = re.search(r'Source = (\d+)', b)
                    out.add((frame, int(mi.group(1)) if mi else 0, int(ms.group(1)) if ms else 0, where if cond else 'enter'))
    return out


def patch_text(text, cues):
    """the state text with this script's sound events replaced by `cues` ([(frame, index, player)]; [] = remove)"""
    t = Tres(text)
    mine = {s[0] for s in t.sub if s[0].startswith('sfx_')}
    for key in ('OnTickEvents', 'OnEnterEvents'):
        refs = _list(t, key)
        keep = [r for r in refs if re.search(r'"([^"]+)"', r).group(1) not in mine]
        if len(keep) != len(refs):
            _set_list(t, key, keep)
    t.sub = [s for s in t.sub if s[0] not in mine]
    if cues:
        existing = _plain_events(t)
        fde = t.add_ext('Script', FDE, fdk.script_uid(FDE), prefer_id='sfx_event')
        at = t.add_ext('Script', AT, fdk.script_uid(AT), prefer_id='sfx_atframe')
        play = t.add_ext('Script', PLAY, fdk.script_uid(PLAY), prefer_id='sfx_play')
        tick_new, enter_new = [], []
        for k, (frame, index, player) in enumerate(sorted(cues)):
            where = 'enter' if frame == 0 else 'tick'
            if (frame, index, player, where) in existing:
                continue
            sid = 'sfx_%d_%d' % (frame, k)
            body = ['script = ExtResource("%s")' % play]
            if player:
                body.append('Source = %d' % player)
            body.append('Index = %d' % index)
            t.sub.append([sid + '_play', 'Resource', body])
            ev = ['script = ExtResource("%s")' % fde]
            if frame:
                t.sub.append([sid + '_at', 'Resource', ['script = ExtResource("%s")' % at, 'Frame = %d' % frame]])
                ev.append('Conditions = [SubResource("%s_at")]' % sid)
            ev.append('Actions = [SubResource("%s_play")]' % sid)
            t.sub.append([sid, 'Resource', ev])
            (enter_new if frame == 0 else tick_new).append('SubResource("%s")' % sid)
        if tick_new:   # first in the list: an event that changes the state on the same frame can't skip them
            _set_list(t, 'OnTickEvents', tick_new + _list(t, 'OnTickEvents'))
        if enter_new:
            _set_list(t, 'OnEnterEvents', _list(t, 'OnEnterEvents') + enter_new)
    # drop the script references this script added if nothing uses them any more
    used_ext, _ = t.used_ids()
    t.ext = [e for e in t.ext if not (e['id'].startswith('sfx_') and e['id'] not in used_ext)]
    return t.text()


def apply_to_text(res, text):
    """used by fdk.write(): a state being (re)written by a kit script gets its cues"""
    cues = resolve(res)
    if cues is None:
        return text
    return patch_text(text, cues)


def apply(res, cues, check=False):
    path = fdk.res_file(res)
    if not os.path.exists(path):
        print('missing state: ' + res); return 'missing'
    cur = open(path, encoding='utf-8').read()
    new = patch_text(cur, cues)
    if fdk.md5(new) == fdk.md5(cur):
        return 'same'
    if check:
        return 'would change'
    kit = fdk.kit_made(res, cur)
    open(path, 'w', encoding='utf-8', newline='\n').write(new)
    if kit:     # still the kit's file: later kit runs may keep rewriting it (with the sounds, see fdk.write)
        st = fdk._state(); st[res] = fdk.md5(new); fdk._save_state()
    return 'wrote'


def main(argv):
    check = '--check' in argv; remove = '--remove' in argv
    names = [a for a in argv if not a.startswith('--')]
    prefixes = ['res://' + GROUPS[n] for n in names] if names else None
    if not check and not remove:
        sfx_indices()
    counts = {}
    for res in sorted(CUES):
        if prefixes and not any(res.startswith(p) for p in prefixes):
            continue
        cues = [] if remove else resolve(res)
        r = apply(res, cues, check)
        counts[r] = counts.get(r, 0) + 1
        if r in ('wrote', 'would change', 'missing'):
            print('%-13s %s (%d cues)' % (r, res, len(cues)))
    print(', '.join('%s %d' % kv for kv in sorted(counts.items())))


if __name__ == '__main__':
    main(sys.argv[1:])
