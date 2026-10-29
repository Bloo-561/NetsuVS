"""Moves files the game doesn't need into DELETE/ (Oct 24 2026 cleanup).

    python tools/make_delete_folder.py --dry      list what would move and how much space it frees
    python tools/make_delete_folder.py            move them

Everything keeps its path inside DELETE/ (DELETE/stages/celdic/src/cache/... ), so any of it can be put back
by moving it to the same place again (DELETE/put_back.py does that for everything). DELETE/ has a .gdignore:
Godot never looks inside it. Delete the whole folder when you're happy.

Groups (see GROUPS below): stage bake caches and preview renders, the old Oct 22 Windows export and
game.zip, the import cache of files that no longer exist, Cecilia's and Flan's retired 1x sprites and
their art sheets (_incoming), tool previews and old push folders, Python caches, the unused first
GeoFront stage, first-backup copies next to AnimationData files.
Needs tools/scan_unused.py's list (/tmp/unused.json) for the per-file groups.
"""
import os, re, sys, json, glob, shutil, time
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEL = os.path.join(ROOT, 'DELETE')
DRY = '--dry' in sys.argv
UNUSED = set(json.load(open('/tmp/unused.json'))) if os.path.exists('/tmp/unused.json') else set()


def rel(p):
    return os.path.relpath(p, ROOT).replace('\\', '/')


def size_of(path):
    if os.path.isfile(path):
        return os.path.getsize(path)
    total = 0
    for d, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(d, f))
            except OSError:
                pass
    return total


def imported_files(src_rel):
    """the .godot/imported files a source's .import points at (+ its .md5 stamp)"""
    imp = os.path.join(ROOT, src_rel + '.import')
    if not os.path.exists(imp):
        return []
    t = open(imp, encoding='utf-8', errors='ignore').read()
    out = set(re.findall(r'"res://(\.godot/imported/[^"]+)"', t))
    for p in list(out):
        m = re.match(r'(.*-[0-9a-f]{32})', p)
        if m:
            out.add(m.group(1) + '.md5')
    return sorted(p for p in out if os.path.exists(os.path.join(ROOT, p)))


def with_sidecars(src_rel):
    """an asset + its .import / .uid + its imported cache files"""
    out = [src_rel]
    for side in ('.import', '.uid'):
        if os.path.exists(os.path.join(ROOT, src_rel + side)):
            out.append(src_rel + side)
    return out + imported_files(src_rel)


def orphan_imports():
    """.godot/imported files no .import file in the project points at any more. Cache files are named
    <source>-<32 hex>.<ext> (+ <source>-<hash>.md5); a file whose <source>-<hash> belongs to a current
    import is kept, whatever its extension (.ctex, .s3tc.ctex, .sample, .md5...)."""
    stems = set()
    for d, dirs, files in os.walk(ROOT):
        r = rel(d)
        if r.startswith(('.godot', '.git', '_backup_stage_select', 'DELETE')):
            dirs[:] = []
            continue
        for f in files:
            if f.endswith('.import'):
                t = open(os.path.join(d, f), encoding='utf-8', errors='ignore').read()
                for p in re.findall(r'"res://(\.godot/imported/[^"]+)"', t):
                    m = re.match(r'(.*-[0-9a-f]{32})', p)
                    stems.add(m.group(1) if m else p)
    out = []
    for d, _, files in os.walk(os.path.join(ROOT, '.godot', 'imported')):
        for f in files:
            p = rel(os.path.join(d, f))
            m = re.match(r'(.*-[0-9a-f]{32})', p)
            if (m.group(1) if m else p) in stems:
                continue
            out.append(p)
    return out


def groups():
    g = []
    # 1. stage bake caches (the bake scripts make them again) and preview renders
    g.append(('Stage bake caches (stages/*/src/cache): numpy caches the Blender bake scripts rebuild',
              [rel(p) for p in glob.glob(os.path.join(ROOT, 'stages', '*', 'src', 'cache'))] +
              [rel(p) for p in glob.glob(os.path.join(ROOT, 'stages', '*', 'src', '_old'))]))
    g.append(('Stage preview renders (stages/*/renders): pictures from the bake, not used by the game',
              [rel(p) for p in glob.glob(os.path.join(ROOT, 'stages', '*', 'renders'))]))
    # 2. old builds
    g.append(('Old Windows build from Oct 22 (export/) and game.zip: re-export from Godot for a current build',
              [rel(p) for p in glob.glob(os.path.join(ROOT, 'export', '*')) if not p.endswith('.gdignore')] +
              ['game.zip']))
    # 3. stale import cache
    g.append(('Import cache of files that no longer exist (.godot/imported)', orphan_imports() +
              [p for p in ['.godot/cecilia_art.zip', '.godot/uid_cache.bin.old'] if os.path.exists(os.path.join(ROOT, p))]))
    # 4. retired sprites and art sheets (only files nothing refers to)
    items = []
    for folder in ['actors/cecilia/Sprites/', 'actors/flan/Sprites/']:
        for p in sorted(UNUSED):
            if p.startswith(folder) and not p.startswith(folder + 'v2/'):
                items += with_sidecars(p)
    g.append(("Cecilia's and Flan's retired 1x sprites (replaced by Sprites/v2; nothing uses them)", items))
    items = []
    for folder in ['actors/cecilia/_incoming', 'actors/flan/_incoming']:
        if os.path.isdir(os.path.join(ROOT, folder)):
            for d, _, files in os.walk(os.path.join(ROOT, folder)):
                for f in files:
                    p = rel(os.path.join(d, f))
                    if p.endswith('.import'):
                        continue
                    items += with_sidecars(p)
    g.append(('Old art sheets for the 1x sprites (actors/*/_incoming; the finished art is in Fighting_Game_All_Sprites)', items))
    # 5. the first GeoFront (reactor chamber): not in the stage list, its README says unused
    items = []
    for p in ['stages/geofront/geofront.tscn', 'stages/geofront/geofront.glb', 'stages/geofront/geofront_gf_machines.png',
              'stages/geofront/geofront_gf_walls.png', 'stages/geofront/geofront_thumb.png',
              'stages/geofront/textures/floor_light.png', 'stages/geofront/gf_floor.gdshader',
              'stages/geofront/gf_glow.gdshader', 'stages/geofront/gf_screen.gdshader']:
        if os.path.exists(os.path.join(ROOT, p)):
            items += with_sidecars(p)
    g.append(('The first GeoFront stage (reactor chamber): not in the stage list (the vault version is)', items))
    # 6. tool leftovers
    g.append(('Tool previews and old push folders (tools/sprite_port/checks, work; actors/cecilia/_claude_checks)',
              [p for p in ['tools/sprite_port/checks', 'tools/sprite_port/work', 'actors/cecilia/_claude_checks']
               if os.path.exists(os.path.join(ROOT, p))]))
    pyc = []
    for d, dirs, files in os.walk(ROOT):
        r = rel(d)
        if r.startswith(('.git', '.godot', 'DELETE', '_backup_stage_select')):
            dirs[:] = []
            continue
        if os.path.basename(d) == '__pycache__':
            pyc.append(r)
            dirs[:] = []
    g.append(('Python caches (__pycache__)', pyc))
    bak = []
    for d, dirs, files in os.walk(ROOT):
        r = rel(d)
        if r.startswith(('.git', '.godot', 'DELETE', '_backup_stage_select', 'stages')) or '/_incoming' in '/' + r:
            dirs[:] = [] if r.startswith(('.git', '.godot', 'DELETE', '_backup_stage_select')) else dirs
            continue
        for f in files:
            if re.search(r'\.bak(_[a-z_0-9]+)?$', f) and '/AnimationData' in '/' + r:
                bak.append(rel(os.path.join(d, f)))
    g.append(('First-backup copies next to AnimationData files (*.bak_sprite_port, *.bak_hitfit...)', bak))
    return g


def main():
    gs = groups()
    total = 0
    plan = []
    seen = set()
    for title, items in gs:
        items = [p for p in items if p not in seen and os.path.exists(os.path.join(ROOT, p))]
        seen.update(items)
        s = sum(size_of(os.path.join(ROOT, p)) for p in items)
        total += s
        print('%8.1f MB  %5d  %s' % (s / 1e6, len(items), title))
        plan.append((title, items, s))
    print('%8.1f MB  total' % (total / 1e6))
    if DRY:
        return
    os.makedirs(DEL, exist_ok=True)
    open(os.path.join(DEL, '.gdignore'), 'w').close()
    log = json.load(open(os.path.join(DEL, 'moved.json'))) if os.path.exists(os.path.join(DEL, 'moved.json')) else []
    for title, items, s in plan:
        for p in items:
            src = os.path.join(ROOT, p)
            dst = os.path.join(DEL, p)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.exists(dst):
                dst = dst + '.%d' % int(time.time())
            os.rename(src, dst)
            log.append({'from': p, 'to': rel(dst), 'group': title})
    json.dump(log, open(os.path.join(DEL, 'moved.json'), 'w'), indent=0)
    # keep the export folder for the next export, hidden from Godot
    os.makedirs(os.path.join(ROOT, 'export'), exist_ok=True)
    open(os.path.join(ROOT, 'export', '.gdignore'), 'w').close()
    with open(os.path.join(DEL, 'README.txt'), 'w', encoding='utf-8') as f:
        f.write('DELETE - files the game does not need (moved here on %s).\n\n' % time.strftime('%Y-%m-%d'))
        f.write('Godot ignores this folder (.gdignore). When you are happy the game works, delete the whole folder.\n')
        f.write('Everything keeps its old path inside this folder; moved.json lists each file.\n')
        f.write('To put everything back:  python DELETE/put_back.py   (one file: move it back to the same path).\n\n')
        for title, items, s in plan:
            f.write('%8.1f MB  %5d items  %s\n' % (s / 1e6, len(items), title))
        f.write('%8.1f MB  total\n' % (total / 1e6))
    with open(os.path.join(DEL, 'put_back.py'), 'w', encoding='utf-8') as f:
        f.write('"""Moves everything in DELETE/ back where it was (from moved.json)."""\n'
                'import os, json\n'
                'D = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(D)\n'
                'for e in json.load(open(os.path.join(D, "moved.json"))):\n'
                '    src = os.path.join(ROOT, e["to"]); dst = os.path.join(ROOT, e["from"])\n'
                '    if os.path.exists(src) and not os.path.exists(dst):\n'
                '        os.makedirs(os.path.dirname(dst), exist_ok=True); os.rename(src, dst)\n'
                'print("done")\n')
    print('moved; see DELETE/README.txt')


if __name__ == '__main__':
    main()
