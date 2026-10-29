"""CHECK REFERENCES: every [ext_resource] in a folder's .tres / .tscn files points at a file that
exists, and its uid (if written) matches that file's own uid. Also lists uids used by two files.

    python check_refs.py actors/leticia [data ...]        (folders relative to the project)
    python check_refs.py actors data --fix                 also corrects stale uids (Godot would warn
                                                           "invalid UID, using text path" and load by path;
                                                           the fix writes the uid the file really has)
Changed files are backed up once in _backup_stage_select/pre_uid_fix/.
"""
import os, re, sys, collections, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); PROJ = os.path.abspath(os.path.join(HERE, '..', '..'))

def own_uid(path):
    if path.endswith(('.tres', '.tscn')):
        m = re.search(r'uid="(uid://[a-z0-9]+)"', open(path, encoding='utf-8', errors='ignore').readline()); return m.group(1) if m else None
    for side in (path + '.import', path + '.uid'):
        if os.path.exists(side):
            t = open(side, encoding='utf-8', errors='ignore').read()
            m = re.search(r'uid="?(uid://[a-z0-9]+)', t); return m.group(1) if m else None
    return None

def main(folders, fix=False):
    bad = 0; n = 0; fixed = 0
    for f in folders:
        for root, dirs, files in os.walk(os.path.join(PROJ, f)):
            if os.path.exists(os.path.join(root, '.gdignore')): dirs[:] = []; continue
            for fn in files:
                if not fn.endswith(('.tres', '.tscn')): continue
                p = os.path.join(root, fn); txt = open(p, encoding='utf-8', errors='ignore').read(); rel = os.path.relpath(p, PROJ)
                def check(m):
                    nonlocal bad, n, fixed
                    a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1))); n += 1
                    tgt = os.path.join(PROJ, a.get('path', '').replace('res://', ''))
                    if not os.path.exists(tgt): print('MISSING  %s -> %s' % (rel, a.get('path'))); bad += 1; return m.group(0)
                    u = own_uid(tgt)
                    if a.get('uid') and u and a['uid'] != u:
                        print('UID      %s -> %s (says %s, file is %s)' % (rel, a['path'], a['uid'], u)); bad += 1
                        if fix: fixed += 1; return m.group(0).replace('uid="%s"' % a['uid'], 'uid="%s"' % u)
                    return m.group(0)
                new = re.sub(r'^\[ext_resource ([^\]]*)\]', check, txt, flags=re.M)
                if fix and new != txt:
                    bk = os.path.join(PROJ, '_backup_stage_select', 'pre_uid_fix', rel + '.bak')
                    if not os.path.exists(bk): os.makedirs(os.path.dirname(bk), exist_ok=True); shutil.copyfile(p, bk)
                    open(p, 'w', encoding='utf-8', newline='\n').write(new)
    print('%d references checked, %d problems%s' % (n, bad, (', %d fixed' % fixed) if fix else ''))
    uids = collections.defaultdict(list)
    for root, dirs, files in os.walk(PROJ):
        if os.path.exists(os.path.join(root, '.gdignore')) or '/.godot' in root or '/.git' in root: dirs[:] = []; continue
        for fn in files:
            if fn.endswith(('.tres', '.tscn')):
                u = own_uid(os.path.join(root, fn))
                if u: uids[u].append(os.path.relpath(os.path.join(root, fn), PROJ))
    for u, ps in uids.items():
        if len(ps) > 1: print('SAME UID %s: %s' % (u, ', '.join(ps)))

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    main(args or ['actors', 'data'], fix='--fix' in sys.argv)
