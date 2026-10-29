"""MOVEMENT TUNING (Oct 24 2026): air dashes and the dash jump, so movement stays fast but controlled.

Every fighter's movement states came from Mahou's template with the same numbers. Two of them made the
fighters "fly":
  - the dash jump kept the full dash speed (74000) for the whole jump: about 5 m in one jump;
  - the air dash (and its up / down versions) went 74000 and the fall after it KEPT that speed, so one air
    dash crossed about 4.4 m and the fighter drifted on at dash speed until she landed.
Now the dash jump is 48000 (1.5x a normal jump), the air dash 64000, and when an air dash ends the fighter
falls on at about jump speed (it slows to END_X).

    python tune_movement.py            all fighters in FIGHTERS
    python tune_movement.py flan       one fighter
    python tune_movement.py --check    only print what would change

Wall bounces (Oct 24): the hit state for bouncing off a wall (34_*_Hit_Bounce_Wall) now pops the opponent up
(NetsuWallPopAction: at least WALL_POP upward, coming back off the wall at most WALL_BACK), so a wall bounce
(Cecilia's 236B in the corner) can be followed up with 5B into an air combo.

Numbers are engine speeds (units per second, 10000 = 1 m). Change MOVES below and run again; the script
finds each value by what it was, so running it twice changes nothing more. Per-fighter numbers: copy a line
into OVERRIDES.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, '..', '..'))
FIGHTERS = {'cecilia': 'CEC', 'flan': 'FLN', 'leticia': 'LET', 'noah': 'NOA'}
MOVEX = 'res://engine/sakuga/Resources/FrameDataEvents/Actions/MoveXAction.cs'

# state file (without the tag) -> {'speed': {old: new}, 'end_x': speed when the state ends (None = leave)}
MOVES = {
    '6_{tag}_DashJumpState': {'speed': {74000: 48000}},
    '19_{tag}_ForwardAirDashState': {'speed': {74000: 64000}, 'end_x': 32000},
    '20_{tag}_ForwardAirDashUpState': {'speed': {74000: 56000}, 'end_x': 30000},
    '21_{tag}_ForwardAirDashDownState': {'speed': {74000: 56000}, 'end_x': 30000},
    '22_{tag}_BackwardsAirDashState': {'end_x': -21000},
    '34_{tag}_Hit_Bounce_Wall': {'wall_pop': True},
}
# Oct 24 night, tested in the corner: coming back off the wall at 1.75 m/s floated them back over her head (her 5B
# stepped under them and they landed behind her). Now they pop almost straight up and fall by the wall: 5B can hit
# them for ~12 frames after her 236B recovers.
WALL_POP, WALL_BACK = 90000, 8000
POP = 'res://engine/sakuga/Resources/FrameDataEvents/Actions/NetsuWallPopAction.cs'
FDE = 'res://engine/sakuga/Resources/FrameDataEvents/FrameDataEvent.cs'
OVERRIDES = {}   # e.g. {'flan': {'6_{tag}_DashJumpState': {'speed': {74000: 44000}}}}


def sub_blocks(text):
    """[(id, start, end, body)] of every sub_resource"""
    out = []
    for m in re.finditer(r'^\[sub_resource type="Resource" id="([^"]+)"\]\n(.*?)(?=^\[|\Z)', text, re.S | re.M):
        out.append((m.group(1), m.start(), m.end(), m.group(2)))
    return out


def ext_ids(text):
    return {m.group(2): m.group(1) for m in re.finditer(r'^\[ext_resource [^\]]*path="([^"]+)"[^\]]*id="([^"]+)"\]', text, re.M)}


def script_uid(path):
    p = os.path.join(PROJ, path.replace('res://', '') + '.uid')
    return open(p).read().strip() if os.path.exists(p) else None


def add_ext(text, path, new_id):
    """an ext_resource line for a script, at the top of the list (project rule); returns (text, id)"""
    ext = ext_ids(text)
    for i, p in ext.items():
        if p == path:
            return text, i
    while new_id in ext:
        new_id += '_'
    uid = script_uid(path)
    line = '[ext_resource type="Script"%s path="%s" id="%s"]\n' % (' uid="%s"' % uid if uid else '', path, new_id)
    m = re.search(r'^\[ext_resource ', text, re.M)
    return text[:m.start()] + line + text[m.start():], new_id


def wall_pop(text):
    """OnEnterEvents gets an event with NetsuWallPopAction (or its numbers are brought up to date)"""
    body = 'Pop = %d\nMaxBackSpeed = %d\n' % (WALL_POP, WALL_BACK)
    if POP in text:
        pop_id = ext_ids(text)
        pop_id = next(i for i, p in pop_id.items() if p == POP)
        m = re.search(r'(script = ExtResource\("%s"\)\n)(?:Pop = -?\d+\n)?(?:MaxBackSpeed = -?\d+\n)?' % re.escape(pop_id), text)
        new = text[:m.start()] + m.group(1) + body + text[m.end():]
        return new, (['wall pop %d / %d' % (WALL_POP, WALL_BACK)] if new != text else [])
    text, pop_id = add_ext(text, POP, 'netsu_pop')
    text, fde_id = add_ext(text, FDE, 'netsu_fde')
    blocks = ('[sub_resource type="Resource" id="netsu_pop_a"]\nscript = ExtResource("%s")\n%s\n'
              '[sub_resource type="Resource" id="netsu_pop_e"]\nscript = ExtResource("%s")\nActions = [SubResource("netsu_pop_a")]\n\n'
              % (pop_id, body, fde_id))
    i = text.find('[resource]')
    text = text[:i] + blocks + text[i:]
    m = re.search(r'^OnEnterEvents = (.*)$', text, re.M)
    cur = m.group(1).strip()
    if cur in ('null', '[]'):
        new = '[SubResource("netsu_pop_e")]'
    else:
        new = cur[:-1] + ', SubResource("netsu_pop_e")]'
    text = text[:m.start()] + 'OnEnterEvents = ' + new + text[m.end():]
    return text, ['wall pop %d / %d (added)' % (WALL_POP, WALL_BACK)]


def tune(text, spec):
    changes = []
    if spec.get('wall_pop'):
        text, ch = wall_pop(text)
        changes += ch
    ext = ext_ids(text)
    movex_id = next((i for i, p in ext.items() if p == MOVEX), None)
    # 1. speeds: MoveX actions with the old value
    for old, new in spec.get('speed', {}).items():
        pat = re.compile(r'(script = ExtResource\("%s"\)\n(?:[^\[\n].*\n)*?)Velocity = %d\n' % (re.escape(movex_id or '?'), old))
        text, n = pat.subn(lambda m: m.group(1) + 'Velocity = %d\n' % new, text)
        if n:
            changes.append('MoveX %d -> %d (%d)' % (old, new, n))
    # 2. the speed it ends with: a MoveX in the StateEnded -> PlayState transition event
    end_x = spec.get('end_x')
    if end_x is not None and movex_id:
        res = text.split('\n[resource]', 1)[1]
        m = re.search(r'^TransitionEvents = \[SubResource\("([^"]+)"\)', res, re.M)
        blocks = {b[0]: b for b in sub_blocks(text)}
        ev = blocks.get(m.group(1)) if m else None
        if ev and 'Actions = [' in ev[3]:
            acts = re.findall(r'SubResource\("([^"]+)"\)', re.search(r'Actions = \[(.*)\]', ev[3]).group(1))
            mx = [a for a in acts if 'script = ExtResource("%s")' % movex_id in blocks[a][3]]
            if mx:
                b = blocks[mx[0]]
                body = b[3]
                if re.search(r'Velocity = (-?\d+)', body):
                    nb = re.sub(r'Velocity = -?\d+', 'Velocity = %d' % end_x, body)
                else:
                    nb = body.replace('script = ExtResource("%s")\n' % movex_id, 'script = ExtResource("%s")\nVelocity = %d\n' % (movex_id, end_x))
                if nb != body:
                    text = text[:b[1]] + text[b[1]:b[2]].replace(body, nb) + text[b[2]:]
                    changes.append('end speed -> %d' % end_x)
            else:
                new_id = 'netsu_endx'
                block = '[sub_resource type="Resource" id="%s"]\nscript = ExtResource("%s")\nVelocity = %d\n\n' % (new_id, movex_id, end_x)
                # define it before the event that uses it, and put it first in the event's actions
                text = text[:ev[1]] + block + text[ev[1]:]
                text = text.replace(ev[3], ev[3].replace('Actions = [', 'Actions = [SubResource("%s"), ' % new_id, 1), 1)
                changes.append('end speed %d (added)' % end_x)
    return text, changes


def main():
    check = '--check' in sys.argv
    names = [a for a in sys.argv[1:] if not a.startswith('--')] or list(FIGHTERS)
    for ch in names:
        tag = FIGHTERS[ch]
        moves = dict(MOVES)
        moves.update(OVERRIDES.get(ch, {}))
        for name, spec in moves.items():
            path = os.path.join(PROJ, 'actors', ch, 'States', name.format(tag=tag) + '.tres')
            if not os.path.exists(path):
                print('%s: no %s' % (ch, os.path.basename(path)))
                continue
            text = open(path, encoding='utf-8').read()
            new, changes = tune(text, spec)
            if changes:
                print('%s %s: %s' % (ch, os.path.basename(path), ', '.join(changes)))
                if not check:
                    open(path, 'w', encoding='utf-8', newline='\n').write(new)


if __name__ == '__main__':
    main()
