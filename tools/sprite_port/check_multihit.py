"""MULTI-HIT CHECK for the move tables (moves_<fighter>.py):

    python check_multihit.py [fighter ...]        (no names: every moves_*.py)

The engine lets an attack hit each opponent only once per state: a later hit in the same state
connects only after a ResetHitAction (reset_hit() in the move's tick list) since the previous hit.
This lists every state where a later attack window has no reset since the one before it (a knee,
then a falling punch...). Fix: add (first frame of the later hit, reset_hit()) to that move's tick
list, then run  python moves_<fighter>.py --states.  Hit-confirm follow-ups that are states of their
own don't need it (a new state starts with a clean slate)."""
import sys, os, glob, importlib
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ATTACK_KINDS = ('atk', 'aoe')          # box kinds of the tables that carry an attack (atk, atk_inv, atk_inv-pass, aoe)

def windows(boxes):
    """first frame of each attack window: an attack box after a non-attack one, or with another attack"""
    out, prev_atk, prev_att = [], False, None
    for b in boxes:
        kind = b[2]; att = b[3] if len(b) > 3 else None
        atk = isinstance(kind, str) and kind.startswith(ATTACK_KINDS)
        if atk and (not prev_atk or att is not prev_att): out.append(b[0])
        prev_atk, prev_att = atk, att
    return out

def resets(mv):
    return sorted(fr for fr, a in mv.get('tick', []) if 'ResetHitAction' in str(getattr(a, 'script', '')))

def check(fighter):
    m = importlib.import_module('moves_' + fighter)
    out = []
    for key, mv in m.MOVES.items():
        w, r = windows(mv.get('boxes', [])), resets(mv)
        for a, b in zip(w, w[1:]):
            if not any(a < x <= b for x in r): out.append((key, mv.get('slot'), a, b))
    return out

if __name__ == '__main__':
    names = sys.argv[1:] or sorted(os.path.basename(p)[6:-3] for p in glob.glob(os.path.join(HERE, 'moves_*.py')))
    total = 0
    for n in names:
        bad = check(n); total += len(bad)
        for key, slot, a, b in bad:
            print('%s %s (state slot %s): the hit at frame %d has no reset_hit() since the hit at frame %d' % (n, key, slot, b, a))
        print('%s: %s' % (n, 'ok' if not bad else '%d to fix' % len(bad)))
    sys.exit(1 if total else 0)
