"""Put every move's cancel list in the engine's priority order (Oct 24 2026).

The engine checks a move's CanCancelTo list FROM THE TOP and takes the first move whose input matches.
5A / 5B / 5C have no direction in their input (any direction works), so when 5C came before 2C in a list,
pressing 2C during a cancel gave 5C: 2B > 2C came out as 2B > 5C, 5A > 2B as 5A > 5B, and so on.
When nothing is being cancelled the engine checks moves from the highest move index down (2C = 28 before
5C = 25), which is why the same buttons worked in neutral.

This sorts the cancel lists of the NORMALS (move files 23_ to 32_: 5A ... j.C, 4A / 6C) from the highest move
index to the lowest, the same order as neutral, so cancels and neutral pick the same move for the same input.
Nothing else in the files changes (ids, uids, values). fdk.add_cancels keeps new lists in this order too.
Specials keep the order their tables give (a follow-up like Leticia's 6X has to be checked before the 66 dash).

    python sort_cancels.py            # every fighter
    python sort_cancels.py flan       # one fighter
    python sort_cancels.py --check    # only list what would change
"""
import glob, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, '..', '..'))
STATE_FILE = os.path.join(HERE, 'analysis', 'fdk_written.json')
FIGHTERS = ['cecilia', 'flan', 'leticia']


def md5(s):
    return hashlib.md5(s.replace('\r\n', '\n').encode('utf-8')).hexdigest()


def sort_text(text):
    """returns (new_text, (old_order, new_order)) or (text, None)"""
    m = re.search(r'^CanCancelTo = \[(.*)\]$', text, re.M)
    if not m:
        return text, None
    refs = re.findall(r'SubResource\("([^"]+)"\)', m.group(1))
    subs = {mm.group(1): mm.group(2) for mm in re.finditer(r'^\[sub_resource type="Resource" id="([^"]+)"\]\n(.*?)(?=^\[|\Z)', text, re.S | re.M)}
    idx = {}
    for r in refs:
        mi = re.search(r'MoveIndex = (\d+)', subs.get(r, ''))
        idx[r] = int(mi.group(1)) if mi else 0
    new = sorted(refs, key=lambda r: -idx[r])   # stable: equal indices keep their order
    if new == refs:
        return text, None
    line = 'CanCancelTo = [' + ', '.join('SubResource("%s")' % r for r in new) + ']'
    return text[:m.start()] + line + text[m.end():], ([idx[r] for r in refs], [idx[r] for r in new])


def main():
    check = '--check' in sys.argv
    names = [a for a in sys.argv[1:] if not a.startswith('--')] or FIGHTERS
    written = json.load(open(STATE_FILE)) if os.path.exists(STATE_FILE) else {}
    changed = 0
    for ch in names:
        for path in sorted(glob.glob(os.path.join(PROJ, 'actors', ch, 'Moves', '*.tres'))):
            num = re.match(r'(\d+)_', os.path.basename(path))
            if not num or not 23 <= int(num.group(1)) <= 32:
                continue
            text = open(path, encoding='utf-8').read()
            new, orders = sort_text(text)
            if not orders:
                continue
            changed += 1
            print('%s %s: %s -> %s' % (ch, os.path.basename(path), orders[0], orders[1]))
            if check:
                continue
            rel = 'res://' + os.path.relpath(path, PROJ).replace('\\', '/')
            kit_made = rel in written and written[rel] == md5(text)
            open(path, 'w', encoding='utf-8', newline='\n').write(new)
            if kit_made:
                written[rel] = md5(new)
    if changed and not check:
        json.dump(written, open(STATE_FILE, 'w'), indent=1, sort_keys=True)
    print('%d list%s %s' % (changed, '' if changed == 1 else 's', 'to sort' if check else 'sorted'))


if __name__ == '__main__':
    main()
