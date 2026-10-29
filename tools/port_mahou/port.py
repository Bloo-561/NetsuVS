"""One-time copy of the Mahou Project battle engine into NetsuVS.

Copies every file listed in file_list.txt from the Mahou project into the
NetsuVS folder layout (see mapping.json) and rewrites the res:// paths inside
scenes, resources and scripts so everything still points at the right place.
Kept in the repo as a record of where each Mahou file ended up.

Usage: python3 port.py <mahou_folder> <netsu_folder>
"""
import json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
src_root, dst_root = sys.argv[1], sys.argv[2]
mapping = json.load(open(os.path.join(HERE, "mapping.json")))
files = [l for l in open(os.path.join(HERE, "file_list.txt")).read().splitlines() if l]
TEXT = (".tscn", ".tres", ".cs", ".gd", ".gdshader", ".import", ".cfg")


def remap(path):
    for old, new in mapping:
        if path == old or path.startswith(old):
            return new + path[len(old):]
        if old.endswith((".tres", ".tscn", ".svg", ".png")) and path.startswith(old + "."):
            return new + path[len(old):]  # sidecars like Roster.tres.uid
    return None


def rewrite(text):
    for old, new in mapping:
        text = text.replace("res://" + old, "res://" + new)
    return text


copied = 0
for rel in files:
    new_rel = remap(rel)
    if new_rel is None:
        print("SKIP (no mapping):", rel)
        continue
    src = os.path.join(src_root, rel)
    dst = os.path.join(dst_root, new_rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if rel.endswith(TEXT):
        with open(src, encoding="utf-8", errors="surrogateescape") as f:
            text = f.read()
        with open(dst, "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
            f.write(rewrite(text))
    else:
        shutil.copyfile(src, dst)
    copied += 1

# Extra assembly the C# project references.
asm_src = os.path.join(src_root, "_mono_referenced_assemblies")
asm_dst = os.path.join(dst_root, "engine", "assemblies")
os.makedirs(asm_dst, exist_ok=True)
for name in os.listdir(asm_src):
    shutil.copyfile(os.path.join(asm_src, name), os.path.join(asm_dst, name))

print("copied", copied, "files")
