"""6C LAUNCHERS (Oct 25 2026, night): every fighter's 6C launches, and on hit it can be jump-cancelled to chase them
into an air combo (like the Cecilia Duel prototype).

    python launchers.py            all four
    python launchers.py cecilia    one

  * Flan, Noah: their 6C (fist pump / devil uppercut) already exists: the hit becomes a launcher and the move gets
    jump cancels on hit (8 / 9 / 7).
  * Cecilia, Leticia: they had a 4A in that slot, which they keep; 6C is a new move (Rising Slash / Crescent
    Launcher) made from their 623 drawings, at the end of the state list and of the move list. Its place in the
    neutral check is set with MoveSettings.NetsuCheckOrder (32.5: after 4A, before the specials, so 236C still
    comes out as 236C). moves_<char>.py keeps it in the list when it runs again (set_stance_specials).
  * Oct 26: every ground normal (5A 5B 5C 2A 2B 2C, and 4A) can cancel into 6C on hit or block, like a gatling
    (normals_to_6c; moves_<char>.py calls it again after it rewrites the normals' cancels). Whether it combos is
    the frame data's call: 6C's startup against the normal's hitstun (a counter hit adds 12). Lights (5A / 2A / 4A)
    only combo into it on counter hit, mediums and heavies combo. Cecilia's and Leticia's 6C were slowed to
    15 frames of startup for that (Flan's and Noah's are 17).
    python launchers.py --normals          only the normals -> 6C cancels and the 6C box (BOX_6C), all four
Everything replaced is backed up once in _backup_stage_select/pre_launchers/.
"""
import sys, os, json, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import fdk
from fdk import *
from tres import Tres

BK = '_backup_stage_select/pre_launchers'
FORCE = '--force' in sys.argv
INP = 'res://actors/_shared/sakuga/Inputs/'
JUMPS = [4, 5, 6]          # stance moves: jump neutral / forward / back
# the launch: they go up about 2.4 m and come down ~45 frames later; jump-cancel on hit and you meet them in the air
LAUNCH = attack(750, 40, 16, kb=(-6000, 78000), air_kb=(-6000, 70000), reaction=8, air_reaction=8, kb_gravity=190000,
                air_gravity=190000, stop=12, gain=400)
LAUNCH_FIELDS = {'BaseDamage': 750, 'GroundHitReaction': 8, 'CrouchHitReaction': 8, 'AirHitReaction': 8,
                 'GroundHitKnockback': 'Vector2i(-6000, 78000)', 'AirHitKnockback': 'Vector2i(-6000, 70000)',
                 'GroundHitKnockbackGravity': 190000, 'AirHitKnockbackGravity': 190000, 'GroundHitstun': 40, 'AirHitstun': 40,
                 'GroundBlockstun': 16}

EXISTING = {'flan': ('FLN', '8_Hitbox_6C_2'), 'noah': ('NOA', '8_Hitbox_6C_2')}
# new 6C: drawings (manifest frames to copy, made ground-anchored), timing, the attack box index
NEW = {
  'cecilia': dict(tag='CEC', name='Rising Slash', copy={'l6c_1': 'dp_1', 'l6c_2': 'dp_4', 'l6c_3': 'dp_6'},
                  keys=[['l6c_1', 0], ['l6c_2', 14, {'dy': 30}], ['l6c_2', 19, {'dy': 50}], ['l6c_3', 26], ['idle_O0', 36]],
                  fx=None, active=(14, 18), duration=42),     # Oct 26: startup 11 -> 15
  'leticia': dict(tag='LET', name='Crescent Launcher', copy={'l6c_1': 'dp_1', 'l6c_2': 'dp_2', 'l6c_3': 'dp_3'},
                  keys=[['l6c_1', 0], ['l6c_2', 14, {'dy': 20}], ['l6c_2', 18, {'dy': 30}], ['l6c_3', 23, {'dy': 10}], ['idle_O0', 35]],
                  fx=None, active=(14, 18), duration=41),     # Oct 26: startup 10 -> 15
}
SLOT_INDEX = 32.5           # NetsuCheckOrder


TAGS = {'cecilia': 'CEC', 'flan': 'FLN', 'leticia': 'LET', 'noah': 'NOA'}
NORMALS = ['23_{t}_5A', '24_{t}_5B', '25_{t}_5C', '26_{t}_2A', '27_{t}_2B', '28_{t}_2C', '32_{t}_4A']


# Oct 26: the 6C attack box, in world pixels (x forward from her / his origin, y up from the floor). The fitted box was
# only at the fist / blade tip above the head (an anti-air): after a normal's pushback the opponent was out of reach,
# so normal -> 6C never connected. Now it covers the body in front too, out to about 1 m.
BOX_6C = [25, 110, 355, 510]
ATTACK_6C = {'cecilia': ('113_CEC_6C', 'CEC_Hitbox_6C_1'), 'leticia': ('107_LET_6C', 'LET_Hitbox_6C_1'),
             'flan': ('57_FLN_6C', '8_Hitbox_6C_2'), 'noah': ('57_NOA_6C', '8_Hitbox_6C_2')}


def reach_6c(ch):
    import hitfit
    anim, hb = ATTACK_6C[ch]
    man_path = os.path.join(HERE, 'manifests', ch + '.json'); man = json.load(open(man_path, encoding='utf-8'))
    man.setdefault('hitfit', {}).setdefault('boxes', {})[hb] = {'attack': [list(BOX_6C)]}
    json.dump(man, open(man_path, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    for line in hitfit.Fitter(ch).run([anim], write=True, force=True): print('  ', line)


def six_c_index(ch):
    """the 6C's place in the main stance's move list"""
    A = 'res://actors/%s/' % ch; tag = TAGS[ch]
    t = Tres(open(res_file(A + 'Stances/%s_Stance_Main.tres' % tag), encoding='utf-8').read())
    for i, r in enumerate(list_refs(t, 'Moves')):
        e = t.ext_by_id(re.search(r'"([^"]+)"', r).group(1))
        if e and re.search(r'/3[23]_%s_6C\.tres$' % tag, e.get('path', '')): return i
    raise SystemExit('no 6C in the stance of ' + ch)


def normals_to_6c(ch, backup=None):
    """every ground normal -> 6C on hit or block (cancel lists keep the stance's check order: after the specials)"""
    A = 'res://actors/%s/' % ch; tag = TAGS[ch]; i6 = six_c_index(ch); n = 0
    for name in NORMALS:
        res = A + 'Moves/%s.tres' % name.format(t=tag)
        if not os.path.exists(res_file(res)) or name.endswith('4A') and i6 == 32: continue   # Flan / Noah: 32 IS the 6C
        add_cancels(res, [(i6, HIT | BLOCK, (0, 999))], backup or BK); n += 1
    return n


def jump_cancels(move_res, active_from):
    add_cancels(move_res, [(j, HIT, (active_from, 999)) for j in JUMPS], BK, before_all=False)


def existing(ch):
    tag, hbname = EXISTING[ch]
    A = 'res://actors/%s/' % ch
    res = A + 'Hitboxes/%s.tres' % hbname
    def fn(t):
        for s in t.sub:
            body = s[2]
            if not any(l.startswith('BaseDamage') for l in body): continue
            keys = {l.split(' = ')[0]: n for n, l in enumerate(body)}
            for k, v in LAUNCH_FIELDS.items():
                line = '%s = %s' % (k, v)
                if k in keys: body[keys[k]] = line
                else: body.insert(len(body) - 1 if body[-1].startswith('metadata') else len(body), line)
    edit_tres(res, fn, BK, '6C launch')
    jump_cancels(A + 'Moves/32_%s_6C.tres' % tag, 16)
    print(ch, '6C launches + jump cancels on hit')


def new(ch):
    import build, hitfit
    c = NEW[ch]; tag = c['tag']; A = 'res://actors/%s/' % ch
    man_path = os.path.join(HERE, 'manifests', ch + '.json'); man = json.load(open(man_path, encoding='utf-8'))
    for fid, src in c['copy'].items():
        spec = dict(man['frames'][src]); spec.pop('anchor', None); spec.pop('at', None)
        man['frames'][fid] = spec
    anim = '113_%s_6C' % tag if ch == 'cecilia' else '107_%s_6C' % tag
    keys = [list(k) for k in c['keys']]
    if c['fx']:
        for k in keys:
            if k[1] == c['fx']['at']:
                opts = k[2] if len(k) > 2 else {}; opts.update({'fx': c['fx']['fx'], 'fx_always': True}); k[2:] = [opts]
    a0, a1 = c['active']
    hb_names = ['%s_Hitbox_6C_%d' % (tag, i) for i in range(3)]
    man['animations'][anim] = {'keys': keys, 'duration': c['duration'],
                               'hitboxes': [[0, 0, hb_names[0]], [a0, 1, hb_names[1]], [a1, 2, hb_names[2]]]}
    hf = man.setdefault('hitfit', {}); hf.setdefault('attack_part', {})[anim] = 'top'
    json.dump(man, open(man_path, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    hbs = [A + 'Hitboxes/%s.tres' % n for n in hb_names]
    write(hbs[0], Hitboxes(standard_hurt(3)), force=FORCE)
    write(hbs[1], Hitboxes(standard_hurt(3) + [box(PROX, 0, 0, 400, 500, HitType=MID), box(HIT_T, 20, 150, 260, 520, **LAUNCH)]), force=FORCE)
    write(hbs[2], Hitboxes(standard_hurt(3)), force=FORCE)
    ares = A + 'AnimationData/%s_AnimData.tres' % anim
    write(ares, AnimData(c['duration'], [(0, 0, hbs[0]), (a0, 1, hbs[1]), (a1, 2, hbs[2])]), force=FORCE)
    p = build.Port(ch); p.build_anim(anim)
    f = hitfit.Fitter(ch)
    for line in f.run([anim], write=True, force=True): print('  ', line)
    # state at the end of the list
    data = A + '0_%s_Data.tres' % tag
    t = Tres(open(res_file(data), encoding='utf-8').read())
    sres = A + 'States/%s_6C.tres' % tag
    refs = list_refs(t, 'States'); i = t.ext_id_for_path(sres)
    slot = refs.index('ExtResource("%s")' % i) if i and 'ExtResource("%s")' % i in refs else len(refs)
    write(sres, State('6C', COMBAT, ares, transitions=[ev([state_ended()], [play_state(0)])], enter=[change_side(), movex(0)],
                      ai=0x10 | 2), force=FORCE)
    set_state_slot(data, slot, sres, BK)
    # the move: specials it can cancel into = 4A's (index >= 38), plus the jump cancels on hit
    stance = A + 'Stances/%s_Stance_Main.tres' % tag
    four_a = Tres(open(res_file(A + 'Moves/32_%s_4A.tres' % tag), encoding='utf-8').read())
    sp = []
    for r in list_refs(four_a, 'CanCancelTo'):
        s = four_a.sub_get(re.search(r'"([^"]+)"', r).group(1)); body = '\n'.join(s[2])
        mi = int(re.search(r'MoveIndex = (\d+)', body).group(1))
        if mi >= 38:
            cond = int(re.search(r'Conditions = (\d+)', body).group(1))
            ft = re.search(r'FrameThreshold = Vector2i\((-?\d+), (-?\d+)\)', body)
            sp.append(cancel(mi, cond, (int(ft.group(1)), int(ft.group(2))) if ft else (0, 999)))
    mres = A + 'Moves/33_%s_6C.tres' % tag
    mv = Move('6C', slot, INP + '14_Input_6C.tres', priority=6, cancels=sp, extra={'NetsuCheckOrder': SLOT_INDEX})
    write(mres, mv, force=FORCE)
    ensure_moves(stance, [mres], BK)
    jump_cancels(mres, a0)
    print(ch, 'new 6C: state', slot, anim)


if __name__ == '__main__':
    names = [a for a in sys.argv[1:] if not a.startswith('--')] or ['flan', 'noah', 'cecilia', 'leticia']
    for ch in names:
        if '--normals' not in sys.argv:
            (existing if ch in EXISTING else new)(ch)
        print(ch, 'normals -> 6C:', normals_to_6c(ch))
        reach_6c(ch)
    print('\n'.join(fdk.LOG))
