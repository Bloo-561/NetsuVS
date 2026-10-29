"""WALL BOUNCE FOR THE WHOLE FLIGHT (Oct 25 2026, night).

A wall-bounce hit (BounceTime + BounceXIntensity, e.g. Cecilia's 236B, Leticia's EX Crossfire / Prism Overdrive, Flan's
Supernova Fist) only checked for the wall in the first state of the flight (30 Hit_LaunchAway, ~30 frames), so a long
throw across the screen never bounced: the check ended before they got there. This adds the same check (on a wall or the
screen edge: OnWallsCondition, in the air, a bounce still pending -> BounceX, play 34 Hit_Bounce_Wall) to the falling states
that follow it, 35 Hit_UpToDown and 36 Hit_Falling, for every fighter.

Also (same night) GROUND BOUNCE: a spike with BounceTime + BounceYIntensity (Leticia's EX Flux Storm) makes them bounce
back up off the floor (they fly up again in 31 Hit_LaunchUp, then the usual knockdown) instead of landing in 32 Hit_LaunchDown:
first a check in 32 (on the ground + a bounce pending -> BounceY 0 clears it, MoveY pops them up GROUND_POP, play 31).

    python wall_bounce_air.py
Backups: _backup_stage_select/pre_wall_bounce_air/.
"""
import os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from fdk import edit_tres, script_uid
from tres import Tres

BK = '_backup_stage_select/pre_wall_bounce_air'
FDE = 'res://engine/sakuga/Resources/FrameDataEvents/'
SCRIPTS = {'ev': FDE + 'FrameDataEvent.cs', 'walls': FDE + 'Conditions/OnWallsCondition.cs', 'ground': FDE + 'Conditions/OnGroundCondition.cs',
           'canb': FDE + 'Conditions/CanBounceWallCondition.cs', 'bx': FDE + 'Actions/BounceXAction.cs', 'play': FDE + 'Actions/PlayStateAction.cs'}
FIGHTERS = {'cecilia': 'CEC', 'flan': 'FLN', 'leticia': 'LET', 'noah': 'NOA'}
STATES = ['35_{t}_Hit_UpToDown', '36_{t}_Hit_Falling']
BOUNCE_STATE = 34
GROUND_STATE, GROUND_BOUNCE_STATE, GROUND_POP = '32_{t}_Hit_LaunchDown', 31, 85000   # 31 Hit_LaunchUp: 33 ends on the spot (it's on the floor)
GSCRIPTS = {'ev': FDE + 'FrameDataEvent.cs', 'ground': FDE + 'Conditions/OnGroundCondition.cs', 'canb': FDE + 'Conditions/CanBounceCondition.cs',
            'by': FDE + 'Actions/BounceYAction.cs', 'my': FDE + 'Actions/MoveYAction.cs', 'play': FDE + 'Actions/PlayStateAction.cs',
            'tp': FDE + 'Actions/TeleportAction.cs'}


def patch_ground(t):
    if any(s[0] == 'gba_tp' for s in t.sub):
        return
    if any(s[0] == 'gba_ev' for s in t.sub):     # an older version of this patch: made again
        t.sub = [s for s in t.sub if not s[0].startswith('gba_')]
        t.res_set('TransitionEvents', (t.res_get('TransitionEvents') or '').replace('SubResource("gba_ev"), ', ''))
    ids = {}
    for k, p in GSCRIPTS.items():
        ids[k] = t.ext_id_for_path(p) or t.add_ext('Script', p, script_uid(p), prefer_id='gba_' + k)
    def sub(sid, key, *lines):
        t.sub.append([sid, 'Resource', ['script = ExtResource("%s")' % ids[key]] + list(lines) +
                      ['metadata/_custom_type_script = "%s"' % script_uid(GSCRIPTS[key])]])
    sub('gba_ground', 'ground')
    sub('gba_canb', 'canb', 'GroundBounce = true', 'Not = true')      # Not = a ground bounce IS pending
    sub('gba_by', 'by', 'CustomIntensity = true')                      # intensity 0: clears it
    sub('gba_my', 'my', 'Velocity = %d' % GROUND_POP)
    sub('gba_tp', 'tp', 'TargetPosition = Vector2i(0, 1500)', 'xRelativeTo = 1', 'yRelativeTo = 1')   # off the floor first
    sub('gba_play', 'play', 'StateIndex = %d' % GROUND_BOUNCE_STATE)
    sub('gba_ev', 'ev', 'Conditions = [SubResource("gba_ground"), SubResource("gba_canb")]',
        'Actions = [SubResource("gba_by"), SubResource("gba_tp"), SubResource("gba_my"), SubResource("gba_play")]')
    refs = re.findall(r'SubResource\("[^"]+"\)', t.res_get('TransitionEvents') or '')
    t.res_set('TransitionEvents', '[' + ', '.join(['SubResource("gba_ev")'] + refs) + ']')


def patch(t):
    if any(s[0] == 'wba_ev' for s in t.sub):
        return
    ids = {}
    for k, p in SCRIPTS.items():
        ids[k] = t.ext_id_for_path(p) or t.add_ext('Script', p, script_uid(p), prefer_id='wba_' + k)
    def sub(sid, key, *lines):
        t.sub.append([sid, 'Resource', ['script = ExtResource("%s")' % ids[key]] + list(lines) +
                      ['metadata/_custom_type_script = "%s"' % script_uid(SCRIPTS[key])]])
    sub('wba_walls', 'walls')
    sub('wba_air', 'ground', 'Not = true')
    sub('wba_canb', 'canb')
    sub('wba_bx', 'bx')
    sub('wba_play', 'play', 'StateIndex = %d' % BOUNCE_STATE)
    sub('wba_ev', 'ev', 'Conditions = [SubResource("wba_walls"), SubResource("wba_air"), SubResource("wba_canb")]',
        'Actions = [SubResource("wba_bx"), SubResource("wba_play")]')
    cur = t.res_get('TransitionEvents')
    refs = re.findall(r'SubResource\("[^"]+"\)', cur or '')
    t.res_set('TransitionEvents', '[' + ', '.join(['SubResource("wba_ev")'] + refs) + ']')


if __name__ == '__main__':
    for ch, tag in FIGHTERS.items():
        for s in STATES:
            res = 'res://actors/%s/States/%s.tres' % (ch, s.format(t=tag))
            edit_tres(res, patch, BK, 'wall bounce in flight')
            print(res)
        res = 'res://actors/%s/States/%s.tres' % (ch, GROUND_STATE.format(t=tag))
        edit_tres(res, patch_ground, BK, 'ground bounce')
        print(res)
