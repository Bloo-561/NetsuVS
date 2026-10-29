"""PAIR SCALE: how big drawing B is compared with drawing A (SIFT on the whole figure), next to
what the manifest says (scale B / scale A).  For checking that frames shown one after another
have the same size.     python pairscale.py <char> frameA:frameB [frameA:frameB ...]"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
from analyze import cfg, source_root, load, feats, similarity
from build import Port
def main(char, pairs):
    c = cfg(char); root = source_root(c); p = Port(char); cache = {}
    def F(fid):
        src = p.m['frames'][fid]['src']
        if src not in cache:
            a, g = load(os.path.join(HERE, src) if src.startswith('derived/') else os.path.join(root, src))
            cache[src] = feats(g, (a[:, :, 3] > 128).astype(np.uint8) * 255)
        return cache[src]
    for pr in pairs:
        a, b = pr.split(':')
        r = similarity(*F(a), *F(b), thr=10)
        man = p.scale_of(p.m['frames'][b]) / p.scale_of(p.m['frames'][a])
        if r: print('%-10s -> %-10s  sift %.3f (%3d inl, rot %5.1f)   manifest %.3f   %s' % (a, b, r['scale'], r['inliers'], r['rot'], man,
                    '<-- off by %+.0f%%' % ((man / r['scale'] - 1) * 100) if r['inliers'] >= 20 and abs(man / r['scale'] - 1) > 0.05 else ''))
        else: print('%-10s -> %-10s  no match                       manifest %.3f' % (a, b, man))
if __name__ == '__main__': main(sys.argv[1], sys.argv[2:])
