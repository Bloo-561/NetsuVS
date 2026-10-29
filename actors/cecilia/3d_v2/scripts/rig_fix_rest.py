"""Milestone 7 repair: put every rigid part back at its Milestone 6 rest transform.

An earlier rig_build._remove_old() read the parts' world matrices while the rig
was posed and baked that pose into them (the face, ears, headband, sword parts,
belts, brooch and bows then floated off their bones in every pose). Both
rig_build and rig_weights now work from the rest pose only. This script
restores the transforms recorded from backup/m6/cecilia_v2.blend
(_m6_object_world.json: matrix_basis, no parents) and re-binds the parts to
their bones. It is safe to run again.

Run: import runpy; runpy.run_path(r"<3d_v2>\\scripts\\rig_fix_rest.py")["run"]()
"""
import json
import os
import sys

import bpy
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))


def run():
    import rig_weights
    rec = json.load(open(os.path.join(HERE, "_m6_object_world.json")))
    rig = bpy.data.objects[rig_weights.RIG]
    out = {}
    for name, bone in rig_weights.RIGID.items():
        ob = bpy.data.objects.get(name)
        if ob is None or name not in rec:
            out[name] = "missing"
            continue
        M6 = Matrix(rec[name]["basis"])
        ob.parent = None
        ob.matrix_parent_inverse = Matrix.Identity(4)
        ob.matrix_basis = M6
        rig_weights._parent_to_bone(ob, rig, bone)
        err = max(abs(a - b) for ra, rb in zip(rig_weights.rest_world(ob), M6) for a, b in zip(ra, rb))
        out[name] = round(err, 9)
    return out


if __name__ == "__main__":
    print(run())
