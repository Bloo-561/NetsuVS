"""Shared constants for the Cecilia v2 pipeline.

Every number here was measured from the reference crops in Milestone 1
(see refs/landmarks.json and the Milestone 1 plan). Nothing is guessed.

Coordinate conventions (Blender, 1 unit = 1 m, Z up):
  - She faces -Y. Her LEFT is +X.
  - Soles on z = 0. Torso centre line on x = 0 (front/back views).
  - y = 0 is the mid-depth of her waist in the side view.
  - Front ref is seen from -Y (Blender Front view, numpad 1).
  - Back ref is seen from +Y (Blender Back view, ctrl+numpad 1).
  - Side ref shows her RIGHT side, seen from -X (Blender Left view,
    ctrl+numpad 3); she faces screen-right in it.

Image coordinates are continuous: u grows to the right from the crop's left
edge, v grows downward from the crop's top edge, pixel i spans [i, i+1].
"""
import os

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPTS)                      # .../actors/cecilia/3d_v2
REFS = os.path.join(ROOT, "refs")
MASKS = os.path.join(REFS, "masks")
RENDERS = os.path.join(ROOT, "renders")
BLEND = os.path.join(ROOT, "cecilia_v2.blend")

HEIGHT_M = 1.58           # ahoge tip to sole, from the brief
FIG_PX = 680.0            # figure height in every crop (50 % edge coverage masks)
PX = HEIGHT_M / FIG_PX    # metres per reference pixel = 0.0023235 m

# sole_v   : bottom edge of the lowest figure row (50 % coverage mask)
# centre_u : x = 0 line. front: mean centre of hair dome / jacket / waist.
#            back: placed so the mirrored back best overlaps the front
#                  (sub-pixel search, soles aligned); torso centre is 265.4.
#            side: mid-depth of the waist (rows 251-257) -> y = 0.
VIEWS = {
    "front": dict(file="cecilia_ref_front.png", W=549, H=706, sole_v=695.0, centre_u=270.13),
    "back":  dict(file="cecilia_ref_back.png",  W=533, H=706, sole_v=694.0, centre_u=264.30),
    "side":  dict(file="cecilia_ref_side.png",  W=220, H=706, sole_v=696.0, centre_u=129.75),
}
VIEW_ORDER = ("front", "back", "side")

# Silhouette IoU targets from the brief
IOU_TARGET = {"front": 0.95, "back": 0.95, "side": 0.92}

# Where the reference image planes sit (behind the model for each view)
REF_PLANE_OFFSET = 1.0
CAM_DISTANCE = 6.0


def ref_path(view):
    return os.path.join(REFS, VIEWS[view]["file"])


def mask_path(view):
    return os.path.join(MASKS, "mask_%s.png" % view)


def img_to_world(view, u, v):
    """Continuous image coords of a ref crop -> world (x, y, z) on the x=0 / y=0 plane."""
    c = VIEWS[view]
    z = (c["sole_v"] - v) * PX
    h = (u - c["centre_u"]) * PX
    if view == "front":
        return (h, 0.0, z)
    if view == "back":
        return (-h, 0.0, z)
    if view == "side":
        return (0.0, -h, z)
    raise ValueError(view)


def world_to_img(view, x, y, z):
    """World point -> continuous image coords (u, v) in that ref crop."""
    c = VIEWS[view]
    v = c["sole_v"] - z / PX
    if view == "front":
        h = x
    elif view == "back":
        h = -x
    elif view == "side":
        h = -y
    else:
        raise ValueError(view)
    return (c["centre_u"] + h / PX, v)


def image_centre_world(view):
    c = VIEWS[view]
    return img_to_world(view, c["W"] / 2.0, c["H"] / 2.0)
