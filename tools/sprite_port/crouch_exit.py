"""CROUCH EXIT (Oct 24 2026, late): standing up from a crouch had no state of its own. Letting go of down played the
jump LANDING state (state 11: landing pose, landing dust, landing sound), so mashing down looked and sounded like
landing from jumps. This gives every fighter a Crouch_Exit state (its own 8_<TAG>_CrouchExit animation: crouch, then
up; no dust, no sound) and points the Uncrouch move (letting go of down) and the crouching state's round-end exit at
it. State 11 and the two other landings are named "Landing" again (they were all called "Crouch_Exit").

    python crouch_exit.py             all fighters
    python crouch_exit.py flan        one fighter

Per fighter (tag CEC / FLN / LET) it writes States/<TAG>_CrouchExit.tres, appends it to 0_<TAG>_Data.tres (States),
and edits Moves/12_<TAG>_Uncrouch.tres (MoveState), States/15_<TAG>_Crouching.tres (its PlayState 11) and the
StateName of States/11-13. Backups of the edited files: _backup_stage_select/pre_crouch_exit/.
"""
import sys, os, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import fdk
from fdk import *
from tres import Tres

FORCE = '--force' in sys.argv
BK = '_backup_stage_select/pre_crouch_exit'
FIGHTERS = {'cecilia': 'CEC', 'flan': 'FLN', 'leticia': 'LET', 'noah': 'NOA'}
IDLE = 1
LANDING_NAMES = {'11': 'Landing', '12': 'Landing_Forward', '13': 'Landing_Backwards'}


def one(ch, tag):
    A = 'res://actors/%s/' % ch
    data = A + '0_%s_Data.tres' % tag
    st = A + 'States/%s_CrouchExit.tres' % tag
    anim = A + 'AnimationData/8_%s_CrouchExit_AnimData.tres' % tag
    if not os.path.exists(res_file(anim)):
        raise SystemExit('%s: no crouch exit animation (%s)' % (ch, anim))

    # its place in the state list (the states name each other by index)
    dt = Tres(open(res_file(data), encoding='utf-8').read())
    refs = list_refs(dt, 'States')
    i = dt.ext_id_for_path(st)
    ref = 'ExtResource("%s")' % i if i else None
    idx = refs.index(ref) if ref in refs else len(refs)

    # the state: the crouch exit animation, facing the opponent, nothing else (back to idle when it ends)
    write(st, State('Crouch_Exit', MOVEMENT, anim, transitions=[ev([state_ended()], [play_state(0)])],
                    enter=[change_side(), movex(0)], ai=IDLE), force=FORCE)

    def fn_data(t):
        refs = list_refs(t, 'States')
        i = t.ext_id_for_path(st) or t.add_ext('Resource', st, res_uid(st), prefer_id='st_%s_CrouchExit' % tag)
        r = 'ExtResource("%s")' % i
        if r not in refs:
            refs.append(r)
        assert refs.index(r) == idx, (refs.index(r), idx)
        t.res_set('States', '[' + ', '.join(refs) + ']')
    edit_tres(data, fn_data, BK, 'crouch exit state')

    # letting go of down -> the crouch exit
    edit_tres(A + 'Moves/12_%s_Uncrouch.tres' % tag, lambda t: t.res_set('MoveState', str(idx)), BK, 'uncrouch move')

    # the crouching state's other way out (the round is over) -> the crouch exit too
    def fn_crouching(t):
        hits = [(s, k) for s in t.sub for k, line in enumerate(s[2]) if line.strip() == 'StateIndex = 11']
        assert len(hits) <= 1, len(hits)
        for s, k in hits:
            s[2][k] = 'StateIndex = %d' % idx
    edit_tres(A + 'States/15_%s_Crouching.tres' % tag, fn_crouching, BK, 'crouching exit')

    # the landings get their names back
    for num, name in LANDING_NAMES.items():
        for f in os.listdir(res_file(A + 'States')):
            if f.startswith(num + '_') and f.endswith('.tres'):
                edit_tres(A + 'States/' + f, lambda t, name=name: t.res_set('StateName', '"%s"' % name), BK, 'landing name')
    print('%s: Crouch_Exit is state %d' % (ch, idx))


if __name__ == '__main__':
    chosen = [a for a in sys.argv[1:] if not a.startswith('--')] or list(FIGHTERS)
    for ch in chosen:
        one(ch, FIGHTERS[ch])
    for line in fdk.LOG:
        print(line)
