"""NEW CHARACTER TOOL
Copies an existing fighter folder into a new one, ready to be re-skinned.

    python tools/new_character/new_character.py <source> <new> <OLD_PREFIX> <NEW_PREFIX> [OldName NewName]
    e.g.  python tools/new_character/new_character.py cecilia rean CEC REA Cecilia Rean

What it does (run from the project folder, with Godot CLOSED):
  1. copies actors/<source>/ to actors/<new>/
  2. renames files: CEC -> REA, Cecilia -> Rean
  3. gives every copied file a NEW unique id (uid), so Godot never confuses the
     copy with the original (otherwise the new fighter would secretly load the
     old fighter's sprites)
  4. fixes every res:// path and uid inside the copied files

The copy behaves exactly like the original until you change its sprites, moves
and stats. Add it to data/roster.tres to make it selectable.
"""
import os
import random
import re
import shutil
import string
import sys

TEXT = (".tres", ".tscn", ".import", ".uid", ".gd", ".cs", ".gdshader", ".cfg")
UID_CHARS = string.ascii_lowercase + string.digits


def new_uid():
    return "uid://" + "".join(random.choice(UID_CHARS) for _ in range(13))


def main():
    if len(sys.argv) < 5:
        print(__doc__)
        sys.exit(1)
    src_name, dst_name, old_pre, new_pre = sys.argv[1:5]
    old_word, new_word = (sys.argv[5], sys.argv[6]) if len(sys.argv) >= 7 else (None, None)
    root = os.getcwd()
    src = os.path.join(root, "actors", src_name)
    dst = os.path.join(root, "actors", dst_name)
    if not os.path.isdir(src):
        sys.exit("No such fighter folder: " + src)
    if os.path.exists(dst):
        sys.exit("Already exists: " + dst + " (pick another name or move it away first)")

    def rename(name):
        name = name.replace(old_pre, new_pre)
        if old_word:
            name = name.replace(old_word, new_word).replace(old_word.lower(), new_word.lower())
        return name

    # 1+2: copy with renamed file names, remembering old path -> new path
    path_map = {}
    for dp, dn, fn in os.walk(src):
        rel_dir = os.path.relpath(dp, src)
        new_dir = os.path.join(dst, *[rename(p) for p in rel_dir.split(os.sep)]) if rel_dir != "." else dst
        os.makedirs(new_dir, exist_ok=True)
        for f in fn:
            new_f = rename(f)
            shutil.copyfile(os.path.join(dp, f), os.path.join(new_dir, new_f))
            old_res = "res://actors/%s/%s" % (src_name, os.path.join(rel_dir, f).replace(os.sep, "/").lstrip("./"))
            new_rel = os.path.relpath(os.path.join(new_dir, new_f), dst).replace(os.sep, "/")
            path_map[old_res] = "res://actors/%s/%s" % (dst_name, new_rel)

    # 3: collect every uid DEFINED by the copied files and invent replacements
    uid_map = {}
    for dp, dn, fn in os.walk(dst):
        for f in fn:
            p = os.path.join(dp, f)
            if not f.endswith(TEXT):
                continue
            with open(p, encoding="utf-8", errors="surrogateescape") as fh:
                t = fh.read()
            if f.endswith(".uid"):
                old = t.strip()
            elif f.endswith(".import"):
                m = re.search(r'^uid="(uid://[a-z0-9]+)"', t, re.M)
                old = m.group(1) if m else None
            else:
                m = re.match(r'\[gd_(?:resource|scene)[^\]]*uid="(uid://[a-z0-9]+)"', t)
                old = m.group(1) if m else None
            if old and old not in uid_map:
                uid_map[old] = new_uid()

    # 4: rewrite paths and uids inside the copy
    path_items = sorted(path_map.items(), key=lambda kv: -len(kv[0]))
    uid_re = re.compile(r"uid://[a-z0-9]+")
    changed = 0
    for dp, dn, fn in os.walk(dst):
        for f in fn:
            if not f.endswith(TEXT):
                continue
            p = os.path.join(dp, f)
            with open(p, encoding="utf-8", errors="surrogateescape", newline="") as fh:
                t = fh.read()
            n = t
            for old, new in path_items:
                n = n.replace(old, new)
            n = uid_re.sub(lambda m: uid_map.get(m.group(0), m.group(0)), n)
            if n != t:
                with open(p, "w", encoding="utf-8", errors="surrogateescape", newline="") as fh:
                    fh.write(n)
                changed += 1
    print("Copied %d files to actors/%s, new ids: %d, files updated: %d"
          % (len(path_map), dst_name, len(uid_map), changed))


if __name__ == "__main__":
    main()
