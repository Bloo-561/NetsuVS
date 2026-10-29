"""ASSIST CALL POSE (Oct 24): the state a fighter plays while calling an assist from neutral on the ground.

The engine (engine/sakuga/Components/NetsuAssist.cs) looks for a state named "Assist Call" in the
fighter's state list. When the player presses S standing, walking, crouching, dashing or landing,
the fighter goes into it: she stops, faces the opponent and holds the pose for FRAMES frames (can't
act or block), so a neutral call isn't free pressure. In the air or during an attack there is no pose.
A fighter without this state just calls without posing.

    python assist_pose.py              all fighters in FIGHTERS
    python assist_pose.py flan         one fighter
    python assist_pose.py --force      also overwrite files changed by hand in Godot

Per fighter it adds to manifests/<fighter>.json the animation <TAG>_AssistCall (the POSE drawing),
writes its hitbox file (hurtboxes fitted to the drawing by hitfit.py), animation data and state
(States/<TAG>_AssistCall.tres), and appends the state to the end of 0_<TAG>_Data.tres's list.
Change the drawing or the length in FIGHTERS / FRAMES and run again.
"""
import sys, os, json, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import fdk
from fdk import *

FRAMES = 30            # Oct 24: 30 frames (was the prototype's 14; a neutral call should cost more)
STATE_NAME = 'Assist Call'
# fighter: (tag, the frame drawn while calling: a key of the manifest's "frames")
FIGHTERS = {'cecilia': ('CEC', 'victory'), 'flan': ('FLN', 'victory'), 'leticia': ('LET', 'victory'), 'noah': ('NOA', 'win_2')}
FORCE = '--force' in sys.argv
BK = '_backup_stage_select/pre_assist_pose'


def one(ch, tag, pose):
    A = 'res://actors/%s/' % ch
    anim = '%s_AssistCall' % tag
    hb_name = '%s_Hitbox_AssistCall_0' % tag
    hb = A + 'Hitboxes/%s.tres' % hb_name
    ad = A + 'AnimationData/%s_AnimData.tres' % anim
    st = A + 'States/%s.tres' % anim
    # manifest: the pose for FRAMES frames, one box timeline entry
    man_path = os.path.join(HERE, 'manifests', ch + '.json')
    man = json.load(open(man_path, encoding='utf-8'))
    if pose not in man['frames']:
        raise SystemExit('%s: no frame "%s" in manifests/%s.json' % (ch, pose, ch))
    entry = {'keys': [[pose, 0]], 'duration': FRAMES, 'hitboxes': [[0, 0, hb_name]]}
    if man['animations'].get(anim) != entry:
        man['animations'][anim] = entry
        json.dump(man, open(man_path, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    if not os.path.exists(res_file(hb)) or FORCE:
        write(hb, Hitboxes(standard_hurt(3)), force=FORCE)
    if not os.path.exists(res_file(ad)) or FORCE:
        write(ad, AnimData(FRAMES, [(0, 0, hb)]), force=FORCE)
    import build, hitfit
    build.Port(ch).build_anim(anim)
    for line in hitfit.Fitter(ch).run([anim], write=True, force=FORCE):
        print('  ', line)
    # the state: face the opponent, stop, hold the pose, back to idle
    write(st, State(STATE_NAME, COMBAT, ad, transitions=[ev([state_ended()], [play_state(0)])],
                    enter=[change_side(), movex(0)], ai=2), force=FORCE)
    # at the end of the fighter's state list (the engine finds it by name)
    data = A + '0_%s_Data.tres' % tag
    def fn(t):
        if t.ext_id_for_path(st):
            refs = list_refs(t, 'States')
            if any(re.search(r'"%s"' % re.escape(t.ext_id_for_path(st)), r) for r in refs):
                return
        i = t.ext_id_for_path(st) or t.add_ext('Resource', st, res_uid(st), prefer_id='st_' + anim)
        refs = list_refs(t, 'States') + ['ExtResource("%s")' % i]
        t.res_set('States', '[' + ', '.join(refs) + ']')
    edit_tres(data, fn, BK, 'assist call state')
    print('%s: "%s" = %s' % (ch, STATE_NAME, st))


def main():
    names = [a for a in sys.argv[1:] if not a.startswith('--')] or list(FIGHTERS)
    for ch in names:
        tag, pose = FIGHTERS[ch]
        one(ch, tag, pose)
    print('\n'.join(fdk.LOG))


if __name__ == '__main__':
    main()
