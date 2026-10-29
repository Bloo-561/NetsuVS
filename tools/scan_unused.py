"""Find asset files nothing in the project refers to (pictures, sounds, models, fonts...).

    python tools/scan_unused.py [--json out.json]

How it decides: every text file Godot reads (.tscn .tres .gd .cs .json .cfg .godot .import .gdshader
.uid) is searched for res:// paths and uid:// ids. A file counts as used when one of those points at it
(directly, by uid, or through its .import / .uid side file), or when it matches a path the scripts
build at run time (DYNAMIC below). Folders with a .gdignore are invisible to Godot and are reported
separately. Nothing is moved: this only lists.
"""
import os, re, sys, json, fnmatch
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SKIP_DIRS = {'.godot', '.git', '_backup_stage_select', 'DELETE'}
TEXT = ('.tscn', '.tres', '.gd', '.cs', '.json', '.cfg', '.godot', '.gdshader', '.import', '.uid', '.csproj', '.md')
ASSET = ('.png', '.jpg', '.jpeg', '.webp', '.svg', '.tga', '.bmp', '.exr', '.hdr', '.wav', '.ogg', '.mp3', '.glb', '.gltf',
         '.fbx', '.obj', '.blend', '.ttf', '.otf', '.woff', '.woff2', '.ogv', '.webm', '.mp4', '.zip', '.res', '.mesh',
         '.tres', '.tscn', '.gdshader', '.material')
# paths the scripts put together at run time (kept even though no file names them in full)
DYNAMIC = [
    'actors/*/Artwork/CutIn_EX.png', 'actors/*/Artwork/CutIn_Super.png', 'actors/*/command_list.json',
    'actors/*/Sprites/v2/idle*.png',  # the character select's little idle sprite
]


def walk(root):
    for d, dirs, files in os.walk(root):
        rel = os.path.relpath(d, root).replace('\\', '/')
        if rel == '.':
            rel = ''
        if any(rel == s or rel.startswith(s + '/') for s in SKIP_DIRS):
            dirs[:] = []
            continue
        ignored = os.path.exists(os.path.join(d, '.gdignore'))
        for f in files:
            yield (rel + '/' + f).lstrip('/'), ignored
        if ignored:
            # still walk below, but everything there is invisible to Godot
            pass


def main():
    files = {}
    gdignored = set()
    for rel, ign in walk(ROOT):
        files[rel] = ign
    # anything under a .gdignore folder (at any depth) is invisible to Godot
    ign_dirs = [os.path.dirname(p) for p in files if p.endswith('.gdignore')]
    for p in files:
        for d in ign_dirs:
            if d == '' or p == d or p.startswith(d + '/'):
                if d != '':
                    gdignored.add(p)
                break
    uid_of = {}      # uid -> file it belongs to
    texts = {}
    for p in files:
        if p in gdignored or not p.endswith(TEXT):
            continue
        try:
            t = open(os.path.join(ROOT, p), encoding='utf-8', errors='ignore').read()
        except OSError:
            continue
        texts[p] = t
        if p.endswith('.import'):
            m = re.search(r'uid="(uid://[a-z0-9]+)"', t)
            if m: uid_of[m.group(1)] = p[:-7]
        elif p.endswith('.uid'):
            m = re.search(r'(uid://[a-z0-9]+)', t)
            if m: uid_of[m.group(1)] = p[:-4]
        elif p.endswith(('.tscn', '.tres')):
            m = re.search(r'^\[gd_(?:scene|resource)[^\]]*uid="(uid://[a-z0-9]+)"', t)
            if m: uid_of[m.group(1)] = p
    # edges: file -> files it points at (by res:// path or uid://)
    edges = {}
    for p, t in texts.items():
        if p.endswith(('.import', '.uid', '.md')):
            continue    # side files describe their own file; docs don't load anything
        out = set()
        for m in re.finditer(r'res://([^"\'\s\)\]>]+)', t):
            out.add(m.group(1).rstrip('.,;:'))
        for m in re.finditer(r'uid://[a-z0-9]+', t):
            if m.group(0) in uid_of:
                out.add(uid_of[m.group(0)])
        edges[p] = out
    # roots: the project file, every script, json and shader (code is always kept), run-time paths
    roots = [p for p in texts if p.endswith(('.godot', '.gd', '.cs', '.json', '.cfg', '.gdshader', '.csproj'))]
    roots += [p for p in files if any(fnmatch.fnmatch(p, pat) for pat in DYNAMIC)]
    used = set(roots)
    stack = list(roots)
    while stack:
        p = stack.pop()
        for q in edges.get(p, ()):
            if q not in used:
                used.add(q)
                stack.append(q)
    unused = []
    for p, ign in files.items():
        if p in gdignored or not p.lower().endswith(ASSET):
            continue
        if p in used:
            continue
        unused.append(p)
    size = lambda p: os.path.getsize(os.path.join(ROOT, p))
    by_dir = {}
    for p in unused:
        d = os.path.dirname(p)
        by_dir.setdefault(d, [0, 0])
        by_dir[d][0] += 1
        by_dir[d][1] += size(p)
    for d, (n, b) in sorted(by_dir.items(), key=lambda kv: -kv[1][1]):
        print('%8.1f MB %5d  %s' % (b / 1e6, n, d))
    print('unused asset files:', len(unused), '%.1f MB' % (sum(size(p) for p in unused) / 1e6))
    if '--json' in sys.argv:
        json.dump(sorted(unused), open(sys.argv[sys.argv.index('--json') + 1], 'w'), indent=0)


if __name__ == '__main__':
    main()
