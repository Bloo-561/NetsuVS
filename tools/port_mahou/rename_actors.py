"""Second port step: rename Mahou's fighter folders to the characters' real names
(Mahou kept old 'Goku' / 'Yamcha' folder names for Silverwing and Caramello)
and fix every res:// path in the project that points at them."""
import os, sys
root = sys.argv[1]
renames = [("actors/goku", "actors/silverwing"), ("actors/yamcha", "actors/caramello")]
for old, new in renames:
    if os.path.isdir(os.path.join(root, old)) and not os.path.exists(os.path.join(root, new)):
        os.rename(os.path.join(root, old), os.path.join(root, new))
TEXT = (".tscn", ".tres", ".cs", ".gd", ".gdshader", ".import", ".cfg", ".godot")
changed = 0
for dp, dn, fn in os.walk(root):
    if ".godot" in dp.split(os.sep):
        continue
    for f in fn:
        if not f.endswith(TEXT):
            continue
        p = os.path.join(dp, f)
        with open(p, encoding="utf-8", errors="surrogateescape", newline="") as fh:
            t = fh.read()
        n = t
        for old, new in renames:
            n = n.replace("res://" + old + "/", "res://" + new + "/")
        if n != t:
            with open(p, "w", encoding="utf-8", errors="surrogateescape", newline="") as fh:
                fh.write(n)
            changed += 1
print("rewrote", changed, "files")
