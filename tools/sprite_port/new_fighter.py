"""NEW FIGHTER: copies a fighter's DATA (states, moves, hitboxes, animation data, stance, AI,
skins, palettes, VFX list) into a new fighter folder with fresh uids, ready to be re-skinned
with build.py and given new moves.  Art, music, 3D files, backups and work folders are NOT
copied (the copy keeps pointing at the old fighter's sprites until build.py replaces them).

    python new_fighter.py cecilia leticia CEC LET Cecilia Leticia [--skip REGEX ...]

--skip: files (paths relative to the source folder) matching a regex are not copied; anything
that pointed at them keeps pointing at the original fighter's file until you replace it.
Refuses to overwrite an existing folder.
"""
import os, re, sys, shutil, random
HERE = os.path.dirname(os.path.abspath(__file__)); PROJ = os.path.abspath(os.path.join(HERE, '..', '..'))
DATA_DIRS = ['AI', 'AnimationData', 'Hitboxes', 'Instances', 'Moves', 'Palettes', 'Stances', 'States', 'VFX']
TOP_FILES = r'^(0_\w+_Data|0_\w+_Profile|\w+_VFXList)\.tres$|^command_list\.json$'
TEXT = ('.tres', '.tscn', '.json')

def new_uid():
    v = random.getrandbits(62) | (1 << 61); txt = ''
    while v:
        c = v % 35; txt = (chr(97 + c) if c < 26 else chr(48 + c - 26)) + txt; v //= 35
    return 'uid://' + txt

def main():
    args = [a for a in sys.argv[1:]]
    skips = []
    while '--skip' in args:
        i = args.index('--skip'); skips.append(re.compile(args[i + 1])); del args[i:i + 2]
    src_name, dst_name, old_tag, new_tag, old_word, new_word = args[:6]
    src = os.path.join(PROJ, 'actors', src_name); dst = os.path.join(PROJ, 'actors', dst_name)
    if os.path.exists(dst): sys.exit('already exists: ' + dst)
    def rename(n):
        return n.replace(old_tag, new_tag).replace(old_word, new_word).replace(old_word.lower(), new_word.lower())
    files = []
    for f in os.listdir(src):
        if re.match(TOP_FILES, f): files.append(f)
    for d in DATA_DIRS:
        for root, _, fs in os.walk(os.path.join(src, d)):
            for f in fs:
                if '.bak' in f or f.endswith('.import') or f.endswith('.png'): continue
                if not f.endswith(TEXT): continue
                files.append(os.path.relpath(os.path.join(root, f), src).replace('\\', '/'))
    files = [f for f in files if not any(s.search(f) for s in skips)]
    path_map = {}
    for rel in files:
        new_rel = '/'.join(rename(p) for p in rel.split('/'))
        path_map['res://actors/%s/%s' % (src_name, rel)] = 'res://actors/%s/%s' % (dst_name, new_rel)
    uid_map = {}
    texts = {}
    for rel in files:
        t = open(os.path.join(src, rel), encoding='utf-8').read()
        texts[rel] = t
        m = re.match(r'\[gd_(?:resource|scene)[^\]]*uid="(uid://[a-z0-9]+)"', t)
        if m: uid_map[m.group(1)] = new_uid()
    items = sorted(path_map.items(), key=lambda kv: -len(kv[0]))
    uid_re = re.compile(r'uid://[a-z0-9]+')
    for rel in files:
        t = texts[rel]
        for a, b in items: t = t.replace('"%s"' % a, '"%s"' % b)
        t = uid_re.sub(lambda m: uid_map.get(m.group(0), m.group(0)), t)
        out = os.path.join(PROJ, path_map['res://actors/%s/%s' % (src_name, rel)].replace('res://', ''))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, 'w', encoding='utf-8', newline='\n').write(t)
    open(os.path.join(dst, '.copied_from'), 'w').write('%s (%s) -> %s (%s), %d files\n' % (src_name, old_tag, dst_name, new_tag, len(files)))
    print('copied %d files to actors/%s, %d new uids' % (len(files), dst_name, len(uid_map)))

if __name__ == '__main__':
    main()
