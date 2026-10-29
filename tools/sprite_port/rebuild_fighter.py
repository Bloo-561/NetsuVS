"""REBUILD FIGHTER: gives a fighter that already exists a fresh copy of another fighter's DATA (states, moves,
hitboxes, animation data, stance, AI, skins, VFX list), and keeps everything that makes it that fighter:
its profile, colours (Palettes/), artwork, music, sprites, command list, and the uids other files point at.
Used on Oct 24 to move Flan (whose data was a copy of Cecilia's Oct 18 placeholder kit) onto Cecilia's
current, complete data before her own drawings and moves went in (make_flan_manifest.py, moves_flan.py).

    python rebuild_fighter.py cecilia flan CEC FLN Cecilia Flan [--skip REGEX ...] [--rename REGEX=>NEW ...] [--dry]

--skip    source files (paths relative to the source folder) that are not copied; whatever pointed at them keeps
          pointing at the source fighter's file until something replaces it (moves_<fighter>.py does)
--rename  extra renames applied to the copied paths after the tag/name swap, e.g. "_4A(_|\\.)=>_6C\\1"
Rules:
- a copied file that lands on a path the fighter already had keeps that file's uid (the roster, the soundtrack...
  keep working); everything else gets a fresh uid
- the fighter's skins (Instances/) keep their own colour material (the Material ext_resource line)
- the fighter's old data files that the copy doesn't replace are MOVED to _backup_stage_select/pre_<fighter>_rebuild/
  (as .bak), replaced ones are copied there first, so the folder holds only the new data
- not touched: 0_<TAG>_Profile.tres, command_list.json, Palettes/, Artwork/, Music/, Sprites/, _incoming/
"""
import os, re, sys, shutil, random
HERE = os.path.dirname(os.path.abspath(__file__)); PROJ = os.path.abspath(os.path.join(HERE, '..', '..'))
DATA_DIRS = ['AI', 'AnimationData', 'Hitboxes', 'Instances', 'Moves', 'Stances', 'States', 'VFX']
TOP_FILES = r'^(0_\w+_Data|\w+_VFXList)\.tres$'
TEXT = ('.tres', '.tscn')
UID_RE = re.compile(r'uid://[a-z0-9]+')

def new_uid():
    v = random.getrandbits(62) | (1 << 61); txt = ''
    while v:
        c = v % 35; txt = (chr(97 + c) if c < 26 else chr(48 + c - 26)) + txt; v //= 35
    return 'uid://' + txt

def file_uid(p):
    if not os.path.exists(p): return None
    with open(p, encoding='utf-8', errors='ignore') as f: head = f.readline()
    m = re.search(r'uid="(uid://[a-z0-9]+)"', head); return m.group(1) if m else None

def data_files(folder):
    out = []
    for f in os.listdir(folder):
        if re.match(TOP_FILES, f): out.append(f)
    for d in DATA_DIRS:
        for root, _, fs in os.walk(os.path.join(folder, d)):
            for f in fs:
                if '.bak' in f or not f.endswith(TEXT): continue
                out.append(os.path.relpath(os.path.join(root, f), folder).replace('\\', '/'))
    return out

def main():
    args = list(sys.argv[1:]); skips, renames = [], []
    dry = '--dry' in args
    if dry: args.remove('--dry')
    while '--skip' in args:
        i = args.index('--skip'); skips.append(re.compile(args[i + 1])); del args[i:i + 2]
    while '--rename' in args:
        i = args.index('--rename'); a, b = args[i + 1].split('=>'); renames.append((re.compile(a), b)); del args[i:i + 2]
    src_name, dst_name, old_tag, new_tag, old_word, new_word = args[:6]
    src = os.path.join(PROJ, 'actors', src_name); dst = os.path.join(PROJ, 'actors', dst_name)
    if not os.path.isdir(dst): sys.exit('no such fighter: ' + dst + ' (use new_fighter.py for a new one)')
    bk = os.path.join(PROJ, '_backup_stage_select', 'pre_%s_rebuild' % dst_name)

    def rename(rel):
        n = '/'.join(p.replace(old_tag, new_tag).replace(old_word, new_word).replace(old_word.lower(), new_word.lower())
                     for p in rel.split('/'))
        for a, b in renames: n = a.sub(b, n)
        return n
    files = [f for f in data_files(src) if not any(s.search(f) for s in skips)]
    path_map = {'res://actors/%s/%s' % (src_name, rel): 'res://actors/%s/%s' % (dst_name, rename(rel)) for rel in files}
    texts, uid_map, kept = {}, {}, 0
    for rel in files:
        t = open(os.path.join(src, rel), encoding='utf-8').read(); texts[rel] = t
        m = re.match(r'\[gd_(?:resource|scene)[^\]]*uid="(uid://[a-z0-9]+)"', t)
        if not m: continue
        out = os.path.join(PROJ, path_map['res://actors/%s/%s' % (src_name, rel)].replace('res://', ''))
        old = file_uid(out)
        uid_map[m.group(1)] = old or new_uid(); kept += bool(old)
    # files the fighter keeps (its profile): references to the source's file go to the fighter's own
    for kept_src in ['0_%s_Profile.tres' % old_tag]:
        kept_dst = rename(kept_src); sp, dp = os.path.join(src, kept_src), os.path.join(dst, kept_dst)
        if os.path.exists(sp) and os.path.exists(dp):
            path_map['res://actors/%s/%s' % (src_name, kept_src)] = 'res://actors/%s/%s' % (dst_name, kept_dst)
            su, du = file_uid(sp), file_uid(dp)
            if su and du: uid_map[su] = du
    new_rels = set(rename(rel) for rel in files)
    old_files = data_files(dst)
    gone = [f for f in old_files if f not in new_rels]
    print('%d files from %s -> %s (%d keep their old uid), %d old %s files moved to the backup'
          % (len(files), src_name, dst_name, kept, len(gone), dst_name))
    if dry:
        for f in gone[:400]: print('  move out:', f)
        return
    items = sorted(path_map.items(), key=lambda kv: -len(kv[0]))
    os.makedirs(bk, exist_ok=True)
    def backup(rel, move):
        p = os.path.join(dst, rel); b = os.path.join(bk, rel + '.bak')
        if not os.path.exists(p): return
        os.makedirs(os.path.dirname(b), exist_ok=True)
        if move: shutil.move(p, b if not os.path.exists(b) else b + '2')
        elif not os.path.exists(b): shutil.copyfile(p, b)
    for rel in files:
        t = texts[rel]
        for a, b in items: t = t.replace('"%s"' % a, '"%s"' % b)
        t = UID_RE.sub(lambda m: uid_map.get(m.group(0), m.group(0)), t)
        new_rel = rename(rel); out = os.path.join(dst, new_rel)
        if new_rel.startswith('Instances/') and os.path.exists(out):      # the skin keeps its own colour
            om = re.search(r'\[ext_resource type="Material"[^\]]*\]', open(out, encoding='utf-8').read())
            nm = re.search(r'\[ext_resource type="Material"[^\]]*\]', t)
            if om and nm:   # (?<![a-z]): the id attribute, not the end of uid="..." (Oct 24 fix)
                keep_id = re.search(r'(?<![a-z])id="([^"]+)"', nm.group(0)).group(1)
                t = t.replace(nm.group(0), re.sub(r'(?<![a-z])id="[^"]+"', 'id="%s"' % keep_id, om.group(0)))
        backup(new_rel, move=False)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, 'w', encoding='utf-8', newline='\n').write(t)
    for rel in gone: backup(rel, move=True)
    open(os.path.join(dst, '.rebuilt_from'), 'w').write('%s (%s) -> %s (%s): %d files, %d old files moved to %s\n'
                                                       % (src_name, old_tag, dst_name, new_tag, len(files), len(gone), os.path.relpath(bk, PROJ)))
    print('done; backup:', os.path.relpath(bk, PROJ))

if __name__ == '__main__':
    main()
