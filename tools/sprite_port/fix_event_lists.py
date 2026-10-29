"""Fix event lists that hold bare actions (Oct 24 2026).

The engine's state event lists (TransitionEvents, OnEnterEvents, OnTickEvents, OnExitEvents, OnHitConfirmEvents,
OnHitReactionEvents) are typed FrameDataEvent[]. The kit used to write bare actions into them
(OnEnterEvents = [ChangeSideAction, MoveXAction]); Godot then can't convert the list when it loads the state
(an InvalidCastException in the output) and drops the WHOLE list, so those actions never ran: specials didn't
turn to face the opponent or stop their momentum, DPs and supers had no invincibility, assists didn't dash.

This wraps every run of bare actions in one FrameDataEvent without conditions (it runs every time, like the
actions were meant to) and keeps everything else (uid, ids, order). fdk.py's State() now does the same for new
files. Files the kit made get their recorded checksum updated, so later tool runs don't think they were edited
by hand.

    python fix_event_lists.py            # fix every .tres under actors/
    python fix_event_lists.py --check    # only list what needs fixing
"""
import glob, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, '..', '..'))
FDE_PATH = 'res://engine/sakuga/Resources/FrameDataEvents/FrameDataEvent.cs'
STATE_FILE = os.path.join(HERE, 'analysis', 'fdk_written.json')
EVENT_LISTS = ('TransitionEvents', 'OnEnterEvents', 'OnTickEvents', 'OnExitEvents', 'OnHitConfirmEvents', 'OnHitReactionEvents')


def md5(s):
    return hashlib.md5(s.replace('\r\n', '\n').encode('utf-8')).hexdigest()


def fde_uid():
    p = os.path.join(PROJ, FDE_PATH.replace('res://', '') + '.uid')
    return open(p).read().strip() if os.path.exists(p) else None


def fix_text(text):
    """returns (new_text, wrapped_count)"""
    ext = {}   # id -> path
    for m in re.finditer(r'^\[ext_resource [^\]]*path="([^"]+)"[^\]]*id="([^"]+)"\]', text, re.M):
        ext[m.group(2)] = m.group(1)
    sub_script = {}   # sub id -> script path
    for m in re.finditer(r'^\[sub_resource type="Resource" id="([^"]+)"\]\n(?:.*\n)*?script = ExtResource\("([^"]+)"\)', text, re.M):
        sub_script[m.group(1)] = ext.get(m.group(2), '')

    def is_event(sub_id):
        return sub_script.get(sub_id, '').endswith('/FrameDataEvent.cs')

    def is_action(sub_id):
        p = sub_script.get(sub_id, '')
        return '/FrameDataEvents/Actions/' in p or p.endswith('Action.cs')

    lines = text.split('\n')
    new_subs = []
    counter = [0]
    used_ids = set(sub_script)
    fde_id = next((i for i, p in ext.items() if p == FDE_PATH), None)
    need_ext = fde_id is None
    if need_ext:
        fde_id = 'netsu_fde'
        while fde_id in ext:
            fde_id += '_'

    def new_event(actions):
        counter[0] += 1
        i = 'netsu_ev%d' % counter[0]
        while i in used_ids:
            counter[0] += 1
            i = 'netsu_ev%d' % counter[0]
        used_ids.add(i)
        new_subs.append('[sub_resource type="Resource" id="%s"]\nscript = ExtResource("%s")\nActions = [%s]\n'
                        % (i, fde_id, ', '.join('SubResource("%s")' % a for a in actions)))
        return i

    wrapped = 0
    for n, line in enumerate(lines):
        m = re.match(r'^(%s) = \[(.*)\]$' % '|'.join(EVENT_LISTS), line)
        if not m:
            continue
        ids = re.findall(r'SubResource\("([^"]+)"\)', m.group(2))
        if not any(is_action(i) and not is_event(i) for i in ids):
            continue
        out, run = [], []
        for i in ids:
            if is_event(i) or not is_action(i):
                if run:
                    out.append(new_event(run)); run = []
                out.append(i)
            else:
                run.append(i)
        if run:
            out.append(new_event(run))
        wrapped += 1
        lines[n] = '%s = [%s]' % (m.group(1), ', '.join('SubResource("%s")' % i for i in out))
    if not wrapped:
        return text, 0
    text = '\n'.join(lines)
    # the new events go after every other sub-resource (they refer to the actions), right before [resource]
    idx = text.find('\n[resource]')
    text = text[:idx + 1] + '\n'.join(new_subs) + '\n' + text[idx + 1:]
    if need_ext:
        uid = fde_uid()
        line = '[ext_resource type="Script"%s path="%s" id="%s"]' % (' uid="%s"' % uid if uid else '', FDE_PATH, fde_id)
        # new ext_resource lines go at the top of the list (project rule)
        first = re.search(r'^\[ext_resource ', text, re.M)
        if first:
            text = text[:first.start()] + line + '\n' + text[first.start():]
        else:
            head_end = text.find('\n') + 1
            text = text[:head_end] + '\n' + line + '\n' + text[head_end:]
    # load_steps (if the file has it) counts resources: keep it right
    m = re.search(r'load_steps=(\d+)', text.split('\n', 1)[0])
    if m:
        steps = len(re.findall(r'^\[(?:ext|sub)_resource ', text, re.M)) + 1
        text = text.replace('load_steps=%s' % m.group(1), 'load_steps=%d' % steps, 1)
    return text, wrapped


def main():
    check = '--check' in sys.argv
    written = json.load(open(STATE_FILE)) if os.path.exists(STATE_FILE) else {}
    changed = 0
    for path in sorted(glob.glob(os.path.join(PROJ, 'actors', '**', '*.tres'), recursive=True)):
        if '/_backup' in path.replace('\\', '/'):
            continue
        text = open(path, encoding='utf-8').read()
        new, wrapped = fix_text(text)
        if not wrapped:
            continue
        rel = 'res://' + os.path.relpath(path, PROJ).replace('\\', '/')
        print(('needs fixing: ' if check else 'fixed: ') + rel + ' (%d list%s)' % (wrapped, 's' if wrapped > 1 else ''))
        changed += 1
        if check:
            continue
        kit_made = rel in written and written[rel] == md5(text)
        open(path, 'w', encoding='utf-8', newline='\n').write(new)
        if kit_made:
            written[rel] = md5(new)
    if not check and changed:
        json.dump(written, open(STATE_FILE, 'w'), indent=1, sort_keys=True)
    print('%d file%s %s' % (changed, '' if changed == 1 else 's', 'need fixing' if check else 'fixed'))


if __name__ == '__main__':
    main()
