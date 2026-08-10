"""
Shippable model shapes + the EXACT fixed-point they would ship in.

Every model here evaluates to a plain Python/numpy INTEGER pipeline that mirrors what
the RTL would do:  uint8 features -> uint8 threshold compares -> int12 table values ->
int16 accumulator -> Delta.  There is no float in the shipped path.

Pre-registered format (PREREG_SHIPPABLE.md section 5):
  feature  uint8, own integer grid, scale = a fixed power of two (all 1 here)
  thresh   uint8, SAME grid, so the compare is exact
  value    signed 12-bit, single per-model power-of-two scale
  accum    int16, wrapping -- overflow is CHECKED on every corpus row
"""
import numpy as np

VAL_BITS = 12
VAL_MIN, VAL_MAX = -(1 << (VAL_BITS - 1)), (1 << (VAL_BITS - 1)) - 1
MUT_BITS = 3                       # killed-mutant quantiser (PREREG section 5)
MUT_MIN, MUT_MAX = -(1 << (MUT_BITS - 1)), (1 << (MUT_BITS - 1)) - 1


def quantise_features(X, scales):
    """float feature matrix -> uint8 on the declared grid.  Returns (Xq, err) where
    err[j] is the max absolute representation error for feature j."""
    Xq = np.empty(X.shape, dtype=np.uint8)
    err = []
    for j, s in enumerate(scales):
        v = X[:, j] * s
        q = np.clip(np.rint(v), 0, 255)
        err.append(float(np.abs(v - q).max() / s))
        Xq[:, j] = q.astype(np.uint8)
    return Xq, err


# --------------------------------------------------------------------- LUT model
class AdditiveLUT:
    """Delta(x) = sum_j LUT_j[x_j].  One BRAM read + one add per feature.
    Silicon: 8 reads from one M10K at base_j + x_j, 8 adds."""
    kind = "additive_lut"

    def __init__(self, feats, sizes, luts):
        self.feats, self.sizes = list(feats), list(sizes)
        self.luts = [np.asarray(l, dtype=np.float64) for l in luts]

    def raw(self, Xq):
        s = np.zeros(Xq.shape[0])
        for j, l in enumerate(self.luts):
            s += l[np.minimum(Xq[:, j], len(l) - 1)]
        return s

    def quantise(self, bits=VAL_BITS):
        lo, hi = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
        mx = max(np.abs(l).max() for l in self.luts)
        scale = mx / hi if mx > 0 else 1.0
        q = [np.clip(np.rint(l / scale), lo, hi).astype(np.int32) for l in self.luts]
        return QuantLUT(self.feats, q, scale, bits)

    def n_params(self):
        return int(sum(self.sizes))


class QuantLUT:
    def __init__(self, feats, luts, scale, bits):
        self.feats, self.luts, self.scale, self.bits = feats, luts, scale, bits

    def delta(self, Xq):
        acc = np.zeros(Xq.shape[0], dtype=np.int64)
        for j, l in enumerate(self.luts):
            acc += l[np.minimum(Xq[:, j], len(l) - 1)]
        return acc

    def param_bits(self):
        return int(sum(len(l) for l in self.luts) * self.bits)

    def cycles(self):
        return 2 * len(self.luts) + 2      # 1 read + 1 add per feature, sequential

    def ops(self):
        return f"{len(self.luts)} BRAM reads + {len(self.luts)} int adds; 0 multiplies"


# ------------------------------------------------------------------- PWL (hinge)
class HingePWL:
    """Delta(x) = sum_j PWL_j(x_j), each PWL_j a CONTINUOUS 4-segment monotone hinge.
    Strictly a sub-family of AdditiveLUT; kept because PREREG section 4 declared it."""
    kind = "hinge_pwl"

    def __init__(self, feats, sizes, curves, breaks):
        self.feats, self.sizes = list(feats), list(sizes)
        self.curves = [np.asarray(c, dtype=np.float64) for c in curves]
        self.breaks = breaks                       # per feature: (b1,b2,b3)

    def raw(self, Xq):
        s = np.zeros(Xq.shape[0])
        for j, c in enumerate(self.curves):
            s += c[np.minimum(Xq[:, j], len(c) - 1)]
        return s

    def quantise(self, bits=VAL_BITS):
        lo, hi = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
        mx = max(np.abs(c).max() for c in self.curves)
        scale = mx / hi if mx > 0 else 1.0
        q = [np.clip(np.rint(c / scale), lo, hi).astype(np.int32) for c in self.curves]
        m = QuantLUT(self.feats, q, scale, bits)
        m.hinge = True
        m.breaks = self.breaks
        return m

    def n_params(self):
        # 3 breakpoints (uint8) + 4 slopes (int8) + 1 intercept (int12) per feature
        return 8 * len(self.curves)


# ------------------------------------------------------------------ tree ensemble
class TreeEnsemble:
    """Sequential quantised-threshold trees.  depth<=D, thresholds uint8 on the
    feature's own integer grid (lossless: x <= floor(t) for integer x)."""
    kind = "trees"

    def __init__(self, feats, trees, depth):
        self.feats, self.trees, self.depth = list(feats), trees, depth

    def raw(self, Xq):
        return _tree_eval(self.trees, Xq.astype(np.int32), None)

    def quantise(self, bits=VAL_BITS):
        lo, hi = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
        mx = max(abs(v) for t in self.trees for v in t["leaf_val"])
        scale = mx / hi if mx > 0 else 1.0
        qt = []
        for t in self.trees:
            q = dict(t)
            q["leaf_q"] = np.clip(np.rint(np.asarray(t["leaf_val"]) / scale),
                                  lo, hi).astype(np.int32)
            qt.append(q)
        return QuantTrees(self.feats, qt, scale, self.depth, bits)

    def n_params(self):
        return sum(len(t["feat"]) * 2 + len(t["leaf_val"]) for t in self.trees)


def _tree_eval(trees, Xq, key):
    n = Xq.shape[0]
    out = np.zeros(n, dtype=np.float64 if key is None else np.int64)
    for t in trees:
        node = np.zeros(n, dtype=np.int32)
        feat = np.asarray(t["feat"], dtype=np.int32)
        thr = np.asarray(t["thr"], dtype=np.int32)
        left = np.asarray(t["left"], dtype=np.int32)
        right = np.asarray(t["right"], dtype=np.int32)
        isleaf = np.asarray(t["is_leaf"], dtype=bool)
        vals = np.asarray(t["leaf_val"] if key is None else t[key])
        leafid = np.asarray(t["leaf_id"], dtype=np.int32)
        for _ in range(t["depth"]):
            live = ~isleaf[node]
            if not live.any():
                break
            f = feat[node]
            go_left = Xq[np.arange(n), np.where(f >= 0, f, 0)] <= thr[node]
            nxt = np.where(go_left, left[node], right[node])
            node = np.where(live, nxt, node)
        out += vals[leafid[node]]
    return out


class QuantTrees:
    def __init__(self, feats, trees, scale, depth, bits):
        self.feats, self.trees, self.scale = feats, trees, scale
        self.depth, self.bits = depth, bits

    def delta(self, Xq):
        return _tree_eval(self.trees, Xq.astype(np.int32), "leaf_q").astype(np.int64)

    def param_bits(self):
        nf = max(1, int(np.ceil(np.log2(len(self.feats)))))
        tot = 0
        for t in self.trees:
            n_int = int((~np.asarray(t["is_leaf"], dtype=bool)).sum())
            n_leaf = len(t["leaf_val"])
            tot += n_int * (nf + 8) + n_leaf * self.bits
        return int(tot)

    def cycles(self):
        # depth compares (1 cycle each, sequential) + 1 accumulate per tree
        return len(self.trees) * (self.depth + 1)

    def ops(self):
        return (f"{len(self.trees)}x({self.depth} uint8 compares + 1 BRAM read + "
                f"1 int add); 0 multiplies")


def extract_hgb_trees(model, depth):
    """sklearn HistGradientBoostingClassifier -> plain node arrays."""
    trees = []
    for it in model._predictors:
        nd = it[0].nodes
        feat, thr, left, right, isleaf, leafval, leafid = [], [], [], [], [], [], []
        for k in range(len(nd)):
            r = nd[k]
            isleaf.append(bool(r["is_leaf"]))
            if r["is_leaf"]:
                feat.append(-1)
                thr.append(0)
                left.append(k)
                right.append(k)
                leafid.append(len(leafval))
                leafval.append(float(r["value"]))
            else:
                feat.append(int(r["feature_idx"]))
                # integer features: x <= t  <=>  x <= floor(t).  Lossless in uint8.
                thr.append(int(np.clip(np.floor(r["num_threshold"]), 0, 255)))
                left.append(int(r["left"]))
                right.append(int(r["right"]))
                leafid.append(0)
        trees.append(dict(feat=feat, thr=thr, left=left, right=right,
                          is_leaf=isleaf, leaf_val=leafval, leaf_id=leafid,
                          depth=depth))
    return trees
