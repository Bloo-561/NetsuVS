"""SIZE FIX (Oct 25 2026): find the pictures that make a fighter grow or shrink on screen, and fix their scale.

Each drawing's "scale" (drawing px per reference px: how big the artist drew her in that picture) comes from
analyze.py, which matches one thing per drawing (its head against the reference drawing's head, or the whole
figure, or a neighbour). A weak match leaves that picture 5-20 % too big or too small, and the game shows her pop
bigger or smaller when it switches to it. This measures every picture four ways and only acts where they agree:

  solve  every pair of drawings the fighter uses is compared (SIFT on the figure, as the game shows it); the scales
         that agree best with all of the comparisons (weighted least squares on log ratios, outliers down-weighted)
  sift   the reference drawing's face (FACE below: bangs, eyes, chin) found in the drawing with SIFT
  ncc    that face's size refined by colour correlation (sizes 0.86-1.14 x the SIFT one, tilts -12..12 degrees)
  ecc    the same refined by OpenCV's ECC alignment (affine)

For each picture: how big she shows on screen compared with the idle pose by each measure (+ = too big; each
measure's overall bias, its median over all the pictures, taken off). The face measures all look at the face, so they
count as one view (their median); the solve is the other (the body). With both views: their average, fixed when it's
FLAG (5 %) or more and both views agree on the direction. With one view only (no face match: turned away, hidden;
or a picture the comparisons don't reach): fixed when it's SOLO_FLAG (8 %) or more and well backed (the solve: 6+
agreeing comparisons; the face: 2+ measures that agree). A fix sets the manifest "scale" to now x (1 + error), so the
game shows the picture idle-sized.

    python sizefix.py leticia             report (worst first)
    python sizefix.py leticia --write     + set the scales in manifests/<char>.json (old value kept in "scale_note")
                                            and print the animations to rebuild:
                                            python build.py <char> <anims> ; python hitfit.py <char> <anims> --write
    python sizefix.py leticia --sheet     + checks/<char>/sizefix.png: each face cut from the game sprites at game
                                            size (green box = the idle face), before the fix

Pair comparisons are cached in analysis/<char>_pairs.json (delete it if the drawings change).
"""
import os, sys, json, math, itertools
import numpy as np, cv2
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from analyze import load, similarity, font
from build import Port

# the face in each fighter's reference drawing (x0, y0, x1, y1, drawing px): bangs, eyes, cheeks, chin
FACE = {'leticia': (575, 85, 725, 250), 'cecilia': (640, 125, 775, 340), 'flan': (448, 226, 528, 301)}
FLAG = 0.05
SPREAD = 0.04
SOLO_FLAG = 0.08        # one view only (body or face): fixed when it's this far off...
SOLO_SUP = 6            # ...the body (solve) backed by this many agreeing comparisons
MIN_INL = 25            # whole-figure pair comparisons
FACE_INL = 12           # face SIFT matches
sift_fig = cv2.SIFT_create(nfeatures=4000)
sift_face = cv2.SIFT_create(nfeatures=12000, contrastThreshold=0.02)
bf = cv2.BFMatcher(cv2.NORM_L2)


def body_frames(p):
    """frames showing the fighter (an animation key's first item; effect layers placed on another frame skipped)
    -> {frame: animations}"""
    uses = {}
    for n, a in p.m['animations'].items():
        for k in a.get('keys', []):
            uses.setdefault(k[0], set()).add(n)
    return {f: u for f, u in uses.items() if f in p.m['frames'] and p.m['frames'][f].get('anchor') not in ('like', 'attach', 'center')}


def dkey(sp):
    return sp['src'] + ('|flip' if sp.get('flip') else '')


def drawing(p, key):
    src = key.split('|')[0]
    path = os.path.join(HERE, src) if src.startswith('derived/') else os.path.join(p.root, src)
    a, g = load(path)
    if key.endswith('|flip'):
        a = a[:, ::-1].copy(); g = g[:, ::-1].copy()
    return a, g


def rgb_on_grey(a):
    al = a[:, :, 3:4].astype(np.float32) / 255
    return a[:, :, :3].astype(np.float32) * al + 128 * (1 - al)


# ------------------------------------------------------------------ measure 1: solve from all pairs
def solve(p, char, keys):
    ref = p.m['reference']
    cache_path = os.path.join(HERE, 'analysis', char + '_pairs.json')
    pairs = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
    feats = {}

    def F(key):
        if key not in feats:
            a, g = drawing(p, key)
            f = min(1.0, 1400.0 / max(g.shape))
            if f < 1.0:
                g = cv2.resize(g, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
                a = cv2.resize(a, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
            k, d = sift_fig.detectAndCompute(g, (a[:, :, 3] > 128).astype(np.uint8) * 255)
            feats[key] = (k, d, f)
        return feats[key]

    allk = sorted(set(keys) | {ref})
    todo = [(a, b) for a, b in itertools.combinations(allk, 2) if '%s>%s' % (a, b) not in pairs]
    if todo:
        print('comparing %d pairs of drawings...' % len(todo), flush=True)
    for i, (a, b) in enumerate(todo):
        ka, da, fa = F(a); kb, db, fb = F(b)
        s = similarity(ka, da, kb, db, thr=10)
        pairs['%s>%s' % (a, b)] = None if not s else [s['scale'] * fa / fb, s['inliers'], s['rot']]
        if i % 500 == 499:
            print('  %d / %d' % (i + 1, len(todo)), flush=True)
            json.dump(pairs, open(cache_path, 'w'))
    if todo:
        json.dump(pairs, open(cache_path, 'w'))
    idx = {k: i for i, k in enumerate(allk)}
    E = []
    for k, v in pairs.items():
        a, b = k.split('>')
        if a not in idx or b not in idx or not v:
            continue
        r, inl, rot = v
        if inl < MIN_INL or abs(rot) > 60 or not (0.4 < r < 2.5):
            continue
        E.append((idx[a], idx[b], math.log(r), min(inl, 200)))
    for k in allk:   # analyze.py's good head matches against the reference
        src = k.split('|')[0]
        m = p.an.get(src) or {}
        sm = m.get('sift') or {}
        if src != ref and m.get('scale_how') == 'head' and sm.get('inliers', 0) >= 40 and not k.endswith('|flip'):
            E.append((idx[ref], idx[k], math.log(m['scale']), min(sm['inliers'], 200)))
    n = len(allk)
    w_extra = np.ones(len(E)); x = np.zeros(n); res = np.zeros(len(E))
    for it in range(12):
        A = np.zeros((len(E) + 1, n)); y = np.zeros(len(E) + 1); W = np.zeros(len(E) + 1)
        for e, (i, j, l, wgt) in enumerate(E):
            A[e, i] = -1; A[e, j] = 1; y[e] = l; W[e] = wgt * w_extra[e]
        A[-1, idx[ref]] = 1; W[-1] = 1e6
        sw = np.sqrt(W)
        x, *_ = np.linalg.lstsq(A * sw[:, None], y * sw, rcond=None)
        res = A[:-1] @ x - y[:-1]
        w_extra = np.where(np.abs(res) <= 0.04, 1.0, 0.04 / np.maximum(np.abs(res), 1e-9))
    support = np.zeros(n)
    for e, (i, j, l, wgt) in enumerate(E):
        if abs(res[e]) < 0.06:
            support[i] += 1; support[j] += 1
    return {k: (math.exp(x[idx[k]]), int(support[idx[k]])) for k in allk}


# ------------------------------------------------------------------ measures 2-4: the face
def face_measures(p, char, keys):
    ra, rg = load(os.path.join(p.root, p.m['reference']))
    x0, y0, x1, y1 = FACE[char]
    mask = np.zeros(rg.shape, np.uint8); mask[y0:y1, x0:x1] = 255
    mask &= (ra[:, :, 3] > 100).astype(np.uint8) * 255
    rk, rd = sift_face.detectAndCompute(rg, mask)
    ref_rgb = rgb_on_grey(ra)
    T = ref_rgb[y0:y1, x0:x1]
    mx = 20
    Tg = cv2.GaussianBlur(rg[y0 - mx:y1 + mx, x0 - mx:x1 + mx].astype(np.float32), (0, 0), 1.0)
    out = {}
    for key in keys:
        a, g = drawing(p, key)
        k, d = sift_face.detectAndCompute(g, (a[:, :, 3] > 100).astype(np.uint8) * 255)
        r = {}
        if d is not None and len(k) >= 8:
            mm = bf.knnMatch(rd, d, k=2)
            good = [m[0] for m in mm if len(m) == 2 and m[0].distance < 0.8 * m[1].distance]
            if len(good) >= 6:
                s = np.float32([rk[m.queryIdx].pt for m in good]); t = np.float32([k[m.trainIdx].pt for m in good])
                M, inl = cv2.estimateAffinePartial2D(s, t, method=cv2.RANSAC, ransacReprojThreshold=4, maxIters=10000, confidence=0.998)
                if M is not None and int(inl.sum()) >= FACE_INL:
                    sc = float(np.hypot(M[0, 0], M[1, 0])); rot = float(np.degrees(np.arctan2(M[1, 0], M[0, 0])))
                    r['sift'] = (sc, int(inl.sum()), rot, M)
        if 'sift' in r:
            sc, inl, rot, M = r['sift']
            img = rgb_on_grey(a)
            c_img = M @ np.array([(x0 + x1) / 2, (y0 + y1) / 2, 1.0])
            best = (-2, None)
            win = 24
            th, tw = T.shape[:2]; H, W = th + 2 * win, tw + 2 * win
            for f_s in np.arange(0.86, 1.141, 0.01):
                for dr in range(-12, 13, 3):
                    ss = sc * f_s; tr = np.radians(rot + dr)
                    A = ss * np.array([[np.cos(tr), -np.sin(tr)], [np.sin(tr), np.cos(tr)]])
                    off = c_img[:2] - A @ np.array([W / 2, H / 2])
                    Mo = np.hstack([A, off[:, None]]).astype(np.float32)
                    w_img = cv2.warpAffine(img, Mo, (W, H), flags=cv2.WARP_INVERSE_MAP | cv2.INTER_LINEAR, borderValue=(128, 128, 128))
                    v = cv2.minMaxLoc(cv2.matchTemplate(w_img, T, cv2.TM_CCOEFF_NORMED))[1]
                    if v > best[0]:
                        best = (v, ss)
            if best[0] >= 0.5:
                r['ncc'] = (best[1], best[0])
            # ECC (affine), started from the SIFT match
            Wm = M.copy().astype(np.float32)
            Wm[:, 2] = Wm[:, 2] + Wm[:, :2] @ np.array([x0 - mx, y0 - mx], np.float32)
            try:
                cc, Wo = cv2.findTransformECC(Tg, cv2.GaussianBlur(g.astype(np.float32), (0, 0), 1.0), Wm, cv2.MOTION_AFFINE,
                                              (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-6), None, 5)
                if cc >= 0.6:
                    r['ecc'] = (float(np.sqrt(abs(np.linalg.det(Wo[:, :2])))), float(cc))
            except cv2.error:
                pass
        out[key] = r
    return out


def main(char, write, sheet):
    p = Port(char)
    frames = body_frames(p)
    keys = sorted({dkey(p.m['frames'][f]) for f in frames})
    solved = solve(p, char, keys)
    faces = face_measures(p, char, keys)
    rows = []
    for f, us in frames.items():
        sp = p.m['frames'][f]; key = dkey(sp)
        now = p.scale_of(sp)
        est = {}
        s, sup = solved.get(key, (None, 0))
        if s is not None and sup >= 3:
            est['solve'] = s / now - 1
        fm = faces.get(key, {})
        for name in ('sift', 'ncc', 'ecc'):
            if name in fm:
                est[name] = fm[name][0] / now - 1
        rows.append(dict(f=f, now=now, est=est, uses=sorted(us), sup=sup, ref=(key == p.m['reference'])))
    # each measure's own bias (the colour-matching ones read faces a few % small overall): its median over every
    # picture is taken as "right" and subtracted, so only a picture's difference from the others counts
    bias = {}
    for name in ('solve', 'sift', 'ncc', 'ecc'):
        v = [r['est'][name] for r in rows if name in r['est'] and not r['ref']]
        bias[name] = float(np.median(v)) if len(v) >= 10 else 0.0
    print('bias removed: ' + ', '.join('%s %+.1f%%' % (k, v * 100) for k, v in bias.items()))
    for r in rows:
        r['est'] = {k: (v - bias[k] if not r['ref'] else v) for k, v in r['est'].items()}
        # two views: the body (solve) and the face (the median of sift / ncc / ecc: they all look at the face, so
        # they count as one). Both: their average, fixed when it's FLAG or more and they agree on the direction.
        # One view only: fixed when it's SOLO_FLAG or more (the solve with SOLO_SUP+ comparisons behind it; the
        # face with 2+ measures that agree).
        e = r['est']
        body = e.get('solve')
        fv = [e[k] for k in ('sift', 'ncc', 'ecc') if k in e]
        face = float(np.median(fv)) if fv else None
        face_ok = face is not None and (len(fv) >= 2 and sum(1 for v in fv if abs(v - face) <= max(SPREAD, 0.35 * abs(face))) >= 2)
        if body is not None and face_ok:
            med = (body + face) / 2
            fix = abs(med) >= FLAG and body * face > 0
        elif body is not None:
            med = body
            fix = abs(body) >= SOLO_FLAG and r['sup'] >= SOLO_SUP
        elif face_ok:
            med = face
            fix = abs(face) >= SOLO_FLAG
        else:
            med = face if face is not None else None
            fix = False
        r['med'] = med; r['face'] = face; r['fix'] = fix
    rows.sort(key=lambda r: (r['med'] is None, -abs(r['med'] or 0)))
    print('%-12s %7s %7s %4s %7s %7s %7s %7s  %s' % ('frame', 'scale', 'solve', 'sup', 'sift', 'ncc', 'ecc', 'error', 'animations'))
    for r in rows:
        e = r['est']
        cell = lambda k: ('%+6.1f%%' % (e[k] * 100)) if k in e else '      -'
        med = ('%+6.1f%%' % (r['med'] * 100)) if r['med'] is not None else '      -'
        print('%-12s %7.3f %s %4d %s %s %s %s %s %s' % (r['f'], r['now'], cell('solve'), r['sup'], cell('sift'), cell('ncc'), cell('ecc'), med,
                                                        '*' if r['fix'] else ' ', ', '.join(r['uses'])[:60]))
    todo = [r for r in rows if r['fix']]
    print('%d pictures; %d to fix (body and face: %d%%+ the same way; one view only: %d%%+)' % (len(rows), len(todo), FLAG * 100, SOLO_FLAG * 100))
    if sheet:
        draw_sheet(p, char, rows, faces)
    if write and todo:
        man_path = os.path.join(HERE, 'manifests', char + '.json')
        m = json.load(open(man_path, encoding='utf-8'))
        anims = set()
        for r in todo:
            sp = m['frames'][r['f']]
            new = r['now'] * (1 + r['med'])
            sp['scale'] = round(new, 4)
            sp.pop('scale_like', None); sp.pop('scale_mul', None)
            sp['scale_note'] = 'sizefix.py Oct 25: was %.3f (showed %+.1f%%)' % (r['now'], r['med'] * 100)
            anims |= set(r['uses'])
        json.dump(m, open(man_path, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
        print('set %d scales in manifests/%s.json' % (len(todo), char))
        print('ANIMS ' + ' '.join(sorted(anims)))


def draw_sheet(p, char, rows, faces):
    x0, y0, x1, y1 = FACE[char]
    fw, fh = x1 - x0, y1 - y0
    cells = []
    for r in rows:
        sp = p.m['frames'][r['f']]; key = dkey(sp)
        fm = faces.get(key, {})
        if 'sift' not in fm:
            continue
        sc, inl, rot, M = fm['sift']
        a, g = drawing(p, key)
        k = p.BASE / p.scale_of(sp)
        Wc, Hc = int(fw * 1.6 * p.BASE), int(fh * 1.6 * p.BASE)
        c = M @ np.array([(x0 + x1) / 2, (y0 + y1) / 2, 1.0])
        th = np.radians(rot)
        A = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]]) / k
        off = c - A @ np.array([Wc / 2, Hc / 2])
        Mo = np.hstack([A, off[:, None]]).astype(np.float32)
        out = cv2.warpAffine(a.astype(np.float32), Mo, (Wc, Hc), flags=cv2.WARP_INVERSE_MAP | cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        cell = Image.new('RGBA', (Wc, Hc + 18), (55, 55, 66, 255))
        cell.alpha_composite(Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGBA'), (0, 0))
        d = ImageDraw.Draw(cell)
        bw, bh = fw * p.BASE, fh * p.BASE
        d.rectangle([Wc / 2 - bw / 2, Hc / 2 - bh / 2, Wc / 2 + bw / 2, Hc / 2 + bh / 2], outline=(0, 255, 120, 255))
        d.text((3, Hc + 2), '%s %s' % (r['f'], ('%+.0f%%' % (r['med'] * 100)) if r['med'] is not None else ''), fill=(255, 255, 255, 255), font=font(12))
        cells.append(cell)
    if not cells:
        return
    cols = 8
    cw = max(c.width for c in cells); ch = max(c.height for c in cells)
    sh = Image.new('RGB', (cw * cols, ch * ((len(cells) + cols - 1) // cols)), (30, 30, 36))
    for i, c in enumerate(cells):
        sh.paste(c.convert('RGB'), ((i % cols) * cw, (i // cols) * ch))
    od = os.path.join(HERE, 'checks', char); os.makedirs(od, exist_ok=True)
    sh.save(os.path.join(od, 'sizefix.png'))
    print('wrote checks/%s/sizefix.png (green box = the idle face size)' % char)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    main(args[0], '--write' in sys.argv, '--sheet' in sys.argv)
