/*
 * ANTIBODY brain, JavaScript port.
 *
 * ANTIBODY is the canon Prescription champion of 2026-09-27 (experiments/cvx/SOTA_20260927.md):
 * CHAIN540 + REACH + TAP + HSV. The reference decider is
 * experiments/cvx/cascade_leaf5b_x.py `_choose_d3_chain_s_leaf5` with the steer_run arm
 * "s5b_hsv512": leaf "winner", topk2=8, fixpoint cascades, w_chain=540, ws=20,
 * w_excav=24, w_hang=40, w5=[0,0,0,512], and the reach_fw_tap mask with tap=2.
 *
 * Board encoding (same as the sims): flat 128 cells, index r*8+c, row 0 at the top.
 *   col: 0 empty, 1..3 colour   vir: 1 = virus   lnk: 0 none, 1 up, 2 down, 3 left, 4 right
 * Action a = var*8 + col.  var 0: H (a,b)  var 1: H (b,a)  var 2: V a on top  var 3: V b on top.
 *
 * Non-clearing leaves are scored with the full leaf kernel (_eval_rtl) on the child board;
 * the Python CMD-7 delta path computes the same number incrementally.
 */
(function (root) {
  "use strict";
  const ROWS = 16, COLS = 8, N = 128;
  const LINK_NONE = 0, LINK_UP = 1, LINK_DOWN = 2, LINK_LEFT = 3, LINK_RIGHT = 4;
  const LDR = [0, -1, 1, 0, 0], LDC = [0, 0, 0, -1, 1];

  // fast_rtl_x.variant("winner")
  const W_BIAS = 5000, W_MAXH = 12, W_HOLES = 20, W_TOPRISK = 90, W_SPAWN = 150, W_SETUP = 32,
    W_MATCHED = 48, W_BURIED = 48, W_RDYEXT = 8, W_VRDY = 8, W_POLL = 6, W_WVIR = 180, W_WCELLS = 10;
  const WIN = 30000, W_EXCAV = 24, W_HANG = 40, W_CHAIN = 540, WS = 20, TOPK2 = 8, W_HSV = 512;
  const VAR_OF_O4 = [2, 3, 0, 1], THIRD_X = [1, 2, 3, 2], THIRD_Y = [2, 3, 1, 2];

  function virusCount(vir) {
    let s = 0;
    for (let i = 0; i < N; i++) if (vir[i]) s++;
    return s;
  }

  function topOcc(col, c) {
    for (let r = 0; r < ROWS; r++) if (col[r * COLS + c] !== 0) return r;
    return ROWS;
  }

  // fast_sim_x._resting -> writes [r0,c0,r1,c1] into out, returns ok
  function resting(col, v, column, out) {
    if (v < 2) {
      if (column < 0 || column + 1 >= COLS) return false;
      const t0 = topOcc(col, column), t1 = topOcc(col, column + 1);
      const r = (t0 < t1 ? t0 : t1) - 1;
      if (r < 0) return false;
      out[0] = r; out[1] = column; out[2] = r; out[3] = column + 1;
      return true;
    }
    if (column < 0 || column >= COLS) return false;
    const bottom = topOcc(col, column) - 1, top = bottom - 1;
    if (top < 0) return false;
    out[0] = top; out[1] = column; out[2] = bottom; out[3] = column;
    return true;
  }

  // ---------------------------------------------------------------- leaf kernel
  function evalRtl(col, vir) {
    let maxh = 0, holes = 0, toprisk = 0, spawn = 0, buried = 0, matched = 0;
    for (let c = 0; c < COLS; c++) {
      let seen = false, fillcnt = 0, curcol = 0, curlen = 0, vseen = 0;
      for (let r = 0; r < ROWS; r++) {
        const idx = r * COLS + c, cc = col[idx];
        if (cc !== 0) {
          if (!seen) { seen = true; const h = ROWS - r; if (h > maxh) maxh = h; }
          if (vir[idx]) {
            const same = curcol === cc;
            if (same) matched++;
            if (vseen < 2) buried += fillcnt - (same ? curlen : 0);
            vseen++;
            curcol = 0; curlen = 0;
          } else if (curcol === cc) {
            curlen++;
          } else {
            curcol = cc; curlen = 1;
          }
          fillcnt++;
          if (r < 3) toprisk++;
          if (r < 4 && (c === 3 || c === 4)) spawn++;
        } else {
          if (seen) holes++;
          curcol = 0; curlen = 0;
        }
      }
    }
    let rdy = 0, vrdy = 0, poll = 0;
    for (let vr = 0; vr < ROWS; vr++) {
      const rb = vr * COLS;
      for (let vc = 0; vc < COLS; vc++) {
        if (!vir[rb + vc]) continue;
        const vcol = col[rb + vc];
        let runH = 1, p = vc;
        while (p !== 0 && col[rb + p - 1] === vcol) { runH++; p--; }
        let lo = p;
        while (lo !== 0 && (col[rb + lo - 1] === 0 || col[rb + lo - 1] === vcol)) lo--;
        p = vc;
        while (p !== 7 && col[rb + p + 1] === vcol) { runH++; p++; }
        let hi = p;
        while (hi !== 7 && (col[rb + hi + 1] === 0 || col[rb + hi + 1] === vcol)) hi++;
        let runV = 1; p = vr;
        while (p !== 0 && col[(p - 1) * COLS + vc] === vcol) { runV++; p--; }
        let vlo = p;
        while (vlo !== 0 && (col[(vlo - 1) * COLS + vc] === 0 || col[(vlo - 1) * COLS + vc] === vcol)) vlo--;
        p = vr;
        while (p !== 15 && col[(p + 1) * COLS + vc] === vcol) { runV++; p++; }
        let vhi = p;
        while (vhi !== 15 && (col[(vhi + 1) * COLS + vc] === 0 || col[(vhi + 1) * COLS + vc] === vcol)) vhi++;
        const hq = (hi - lo + 1) >= 4 ? runH * runH : 0;
        const vq = (vhi - vlo + 1) >= 4 ? runV * runV : 0;
        rdy += hq > vq ? hq : vq;
        vrdy += runV * runV;
        for (let pc = 0; pc < COLS; pc++) {
          const j = rb + pc;
          if (pc !== vc && col[j] !== 0 && !vir[j] && col[j] !== vcol) poll++;
        }
        for (let pr = 0; pr < ROWS; pr++) {
          const j = pr * COLS + vc;
          if (pr !== vr && col[j] !== 0 && !vir[j] && col[j] !== vcol) poll++;
        }
      }
    }
    let setup = 0;
    for (let wr = 0; wr < ROWS; wr++) {
      const rb = wr * COLS;
      for (let wc = 0; wc < 6; wc++) {
        const c0 = col[rb + wc];
        if (c0 !== 0 && col[rb + wc + 1] === c0 && col[rb + wc + 2] === c0) {
          let t = vir[rb + wc] || vir[rb + wc + 1] || vir[rb + wc + 2];
          if (!t && wc !== 0 && vir[rb + wc - 1] && col[rb + wc - 1] === c0) t = 1;
          if (!t && wc < 5 && vir[rb + wc + 3] && col[rb + wc + 3] === c0) t = 1;
          if (t) setup++;
        }
      }
    }
    for (let wc = 0; wc < COLS; wc++) {
      for (let wr = 0; wr < 14; wr++) {
        const i = wr * COLS + wc, c0 = col[i];
        if (c0 !== 0 && col[i + COLS] === c0 && col[i + 2 * COLS] === c0) {
          let t = vir[i] || vir[i + COLS] || vir[i + 2 * COLS];
          if (!t && wr !== 0 && vir[i - COLS] && col[i - COLS] === c0) t = 1;
          if (!t && wr < 13 && vir[i + 3 * COLS] && col[i + 3 * COLS] === c0) t = 1;
          if (t) setup++;
        }
      }
    }
    let s = W_BIAS - W_MAXH * maxh - W_HOLES * holes - W_TOPRISK * toprisk - W_SPAWN * spawn
      + W_SETUP * setup + W_MATCHED * matched - W_BURIED * buried + W_RDYEXT * rdy
      + W_VRDY * vrdy - W_POLL * poll;
    s = s & 0xFFFF;
    if (s >= 0x8000) s -= 0x10000;
    return s;
  }

  function leafv(col, vir) {
    return virusCount(vir) === 0 ? WIN : evalRtl(col, vir);
  }

  // HSV: -512 per virus high (row < 9) in the spawn columns 3..5
  function x5(col, vir) {
    let hsv = 0;
    for (let r = 0; r < 9; r++) {
      for (let c = 3; c < 6; c++) {
        const i = r * COLS + c;
        if (col[i] !== 0 && vir[i]) hsv++;
      }
    }
    return -W_HSV * hsv;
  }

  function excav(col, vir) {
    let total = 0;
    for (let c = 0; c < COLS; c++) {
      let r = 0;
      while (r < ROWS && col[r * COLS + c] === 0) r++;
      if (r >= ROWS) continue;
      let vr = -1;
      for (let rr = r + 1; rr < ROWS; rr++) if (vir[rr * COLS + c]) { vr = rr; break; }
      if (vr < 0 || vir[r * COLS + c]) continue;
      const top = col[r * COLS + c];
      let run = 1, rr = r + 1;
      while (rr < vr && col[rr * COLS + c] !== 0 && col[rr * COLS + c] === top && !vir[rr * COLS + c]) { run++; rr++; }
      const m = run < 3 ? run : 3;
      total += m * m;
    }
    return total;
  }

  function hang(col, vir) {
    let total = 0;
    for (let r = 0; r < ROWS - 1; r++) {
      for (let c = 0; c < COLS; c++) {
        const idx = r * COLS + c;
        if (col[idx] === 0 || vir[idx] || col[idx + COLS] !== 0) continue;
        let rr = r + 2;
        while (rr < ROWS && col[rr * COLS + c] === 0) rr++;
        if (rr < ROWS && col[rr * COLS + c] === col[idx]) total++;
      }
    }
    return total;
  }

  function stranded(col, vir) {
    let n = 0;
    for (let r = 0; r < 16; r++) {
      for (let c = 0; c < 8; c++) {
        const i = r * 8 + c;
        if (col[i] === 0 || vir[i]) continue;
        const k = col[i];
        if ((r > 0 && col[i - 8] === k) || (r < 15 && col[i + 8] === k) ||
            (c > 0 && col[i - 1] === k) || (c < 7 && col[i + 1] === k)) continue;
        n++;
      }
    }
    return n;
  }

  // ---------------------------------------------------------------- linked resolve
  function findClears(col, mask) {
    mask.fill(0);
    for (let r = 0; r < ROWS; r++) {
      let i = 0;
      while (i < COLS) {
        const v = col[r * COLS + i];
        if (v === 0) { i++; continue; }
        let j = i;
        while (j < COLS && col[r * COLS + j] === v) j++;
        if (j - i >= 4) for (let k = i; k < j; k++) mask[r * COLS + k] = 1;
        i = j;
      }
    }
    for (let c = 0; c < COLS; c++) {
      let i = 0;
      while (i < ROWS) {
        const v = col[i * COLS + c];
        if (v === 0) { i++; continue; }
        let j = i;
        while (j < ROWS && col[j * COLS + c] === v) j++;
        if (j - i >= 4) for (let k = i; k < j; k++) mask[k * COLS + c] = 1;
        i = j;
      }
    }
    let n = 0;
    for (let i = 0; i < N; i++) if (mask[i]) n++;
    return n;
  }

  function applyClear(col, vir, lnk, mask) {
    let nv = 0;
    for (let idx = 0; idx < N; idx++) {
      if (!mask[idx]) continue;
      if (vir[idx]) nv++;
      const lk = lnk[idx];
      if (lk !== LINK_NONE) {
        const pr = ((idx / COLS) | 0) + LDR[lk], pc = (idx % COLS) + LDC[lk];
        if (pr >= 0 && pr < ROWS && pc >= 0 && pc < COLS && !mask[pr * COLS + pc]) lnk[pr * COLS + pc] = LINK_NONE;
      }
    }
    for (let idx = 0; idx < N; idx++) if (mask[idx]) { col[idx] = 0; vir[idx] = 0; lnk[idx] = LINK_NONE; }
    return nv;
  }

  const gB0 = new Int32Array(N), gB1 = new Int32Array(N), gKey = new Int32Array(N),
    gOrd = new Int32Array(N), gSeen = new Uint8Array(N);

  function gravity(col, vir, lnk) {
    for (;;) {
      gSeen.fill(0);
      let nb = 0;
      for (let r = 0; r < ROWS; r++) {
        for (let c = 0; c < COLS; c++) {
          const idx = r * COLS + c;
          if (col[idx] === 0 || vir[idx] || gSeen[idx]) continue;
          const lk = lnk[idx];
          if (lk === LINK_NONE) {
            gSeen[idx] = 1; gB0[nb] = idx; gB1[nb] = -1; gKey[nb] = r; nb++;
          } else {
            const pr = r + LDR[lk], pc = c + LDC[lk];
            const ok = pr >= 0 && pr < ROWS && pc >= 0 && pc < COLS;
            const pidx = ok ? pr * COLS + pc : -1;
            if (ok && !gSeen[pidx]) {
              gSeen[idx] = 1; gSeen[pidx] = 1; gB0[nb] = idx; gB1[nb] = pidx; gKey[nb] = r > pr ? r : pr; nb++;
            } else {
              gSeen[idx] = 1; gB0[nb] = idx; gB1[nb] = -1; gKey[nb] = r; nb++;
            }
          }
        }
      }
      if (nb === 0) break;
      stableDesc(gKey, nb, gOrd);
      let moved = false;
      for (let s = 0; s < nb; s++) {
        const k = gOrd[s], k0 = gB0[k], k1 = gB1[k];
        let fall = true;
        for (let t = 0; t < 2; t++) {
          const kk = t === 0 ? k0 : k1;
          if (kk < 0) continue;
          if (((kk / COLS) | 0) + 1 >= ROWS) { fall = false; break; }
          const nk = kk + COLS;
          if (nk !== k0 && nk !== k1 && col[nk] !== 0) { fall = false; break; }
        }
        if (!fall) continue;
        const c0v = col[k0], v0v = vir[k0], l0v = lnk[k0];
        col[k0] = 0; vir[k0] = 0; lnk[k0] = LINK_NONE;
        let c1v = 0, v1v = 0, l1v = 0;
        if (k1 >= 0) { c1v = col[k1]; v1v = vir[k1]; l1v = lnk[k1]; col[k1] = 0; vir[k1] = 0; lnk[k1] = LINK_NONE; }
        col[k0 + COLS] = c0v; vir[k0 + COLS] = v0v; lnk[k0 + COLS] = l0v;
        if (k1 >= 0) { col[k1 + COLS] = c1v; vir[k1 + COLS] = v1v; lnk[k1 + COLS] = l1v; }
        moved = true;
      }
      if (!moved) break;
    }
  }

  // stable insertion sort, descending (equal keys keep ascending index)
  function stableDesc(keys, m, order) {
    for (let i = 0; i < m; i++) order[i] = i;
    for (let i = 1; i < m; i++) {
      const v = order[i], kv = keys[v];
      let j = i - 1;
      while (j >= 0 && keys[order[j]] < kv) { order[j + 1] = order[j]; j--; }
      order[j + 1] = v;
    }
  }

  // Returns [cells, viruses, chain]; resolves in place to the fixpoint.
  function resolve(col, vir, lnk, mask) {
    let cells = 0, nv = 0, chain = 0, n;
    while ((n = findClears(col, mask)) > 0) {
      chain++;
      cells += n;
      nv += applyClear(col, vir, lnk, mask);
      gravity(col, vir, lnk);
    }
    return [cells, nv, chain];
  }

  function anyClearLines(col, r0, c0, r1, c1) {
    for (let k = 0; k < 2; k++) {
      if (k === 1 && r1 === r0) continue;
      const rr = k === 0 ? r0 : r1;
      let i = 0;
      while (i < COLS) {
        const v = col[rr * COLS + i];
        if (v === 0) { i++; continue; }
        let j = i;
        while (j < COLS && col[rr * COLS + j] === v) j++;
        if (j - i >= 4) return true;
        i = j;
      }
    }
    for (let k = 0; k < 2; k++) {
      if (k === 1 && c1 === c0) continue;
      const cc = k === 0 ? c0 : c1;
      let i = 0;
      while (i < ROWS) {
        const v = col[i * COLS + cc];
        if (v === 0) { i++; continue; }
        let j = i;
        while (j < ROWS && col[j * COLS + cc] === v) j++;
        if (j - i >= 4) return true;
        i = j;
      }
    }
    return false;
  }

  // ---------------------------------------------------------------- search
  const rest = new Int32Array(4);
  const LR = { ok: 0, nv: 0, cells: 0, lv: 0, ch: 0 };

  // _leaf_chain5. Child board (when produced) goes to ccol/cvir/clnk.
  function leafChain(pcol, pvir, plnk, parentVirs, v, column, pa, pb, ccol, cvir, clnk, mask, wantBoard) {
    LR.ok = 0; LR.nv = 0; LR.cells = 0; LR.lv = 0; LR.ch = 0;
    if (!resting(pcol, v, column, rest)) return LR;
    LR.ok = 1;
    const r0 = rest[0], c0 = rest[1], r1 = rest[2], c1 = rest[3];
    const col0 = (v === 0 || v === 2) ? pa : pb, col1 = (v === 0 || v === 2) ? pb : pa;
    const i0 = r0 * COLS + c0, i1 = r1 * COLS + c1;
    pcol[i0] = col0; pcol[i1] = col1;
    const clearing = anyClearLines(pcol, r0, c0, r1, c1);
    pcol[i0] = 0; pcol[i1] = 0;
    if (clearing || wantBoard) {
      ccol.set(pcol); cvir.set(pvir); clnk.set(plnk);
      ccol[i0] = col0; ccol[i1] = col1; cvir[i0] = 0; cvir[i1] = 0;
      if (v < 2) { clnk[i0] = LINK_RIGHT; clnk[i1] = LINK_LEFT; } else { clnk[i0] = LINK_DOWN; clnk[i1] = LINK_UP; }
    }
    if (clearing) {
      const res = resolve(ccol, cvir, clnk, mask);
      LR.cells = res[0]; LR.nv = res[1]; LR.ch = res[2];
      let lv = leafv(ccol, cvir);
      if (virusCount(cvir) !== 0) lv += x5(ccol, cvir);
      LR.lv = lv;
      return LR;
    }
    if (parentVirs === 0) { LR.lv = WIN; return LR; }
    if (wantBoard) {
      LR.lv = evalRtl(ccol, cvir) + x5(ccol, cvir);
      return LR;
    }
    pcol[i0] = col0; pcol[i1] = col1;
    LR.lv = evalRtl(pcol, pvir) + x5(pcol, pvir);
    pcol[i0] = 0; pcol[i1] = 0;
    return LR;
  }

  function immChain(nv, cells, ch) {
    let v = W_WVIR * nv + W_WCELLS * cells;
    if (ch > 1) v += W_CHAIN * (ch - 1);
    return v;
  }

  function mk() { return new Int8Array(N); }
  const c1 = mk(), v1 = mk(), l1 = mk(), s2c = mk(), s2v = mk(), s2l = mk(),
    tc = mk(), tv = mk(), tl = mk(), mask = mk();
  const b2col = [], b2vir = [], b2lnk = [];
  for (let i = 0; i < 32; i++) { b2col.push(mk()); b2vir.push(mk()); b2lnk.push(mk()); }
  const keys2 = new Float64Array(32), imms2 = new Float64Array(32), order2 = new Int32Array(32);

  function expectedThird(b2c, b2v, b2l) {
    const nvir = virusCount(b2v);
    if (nvir === 0) return WIN;
    let tot = 0;
    for (let t = 0; t < 4; t++) {
      const x = THIRD_X[t], y = THIRD_Y[t];
      let best3 = 0, have3 = false;
      for (let o4 = 0; o4 < 4; o4++) {
        const v = VAR_OF_O4[o4];
        for (let cl = 0; cl < 8; cl++) {
          const r = leafChain(b2c, b2v, b2l, nvir, v, cl, x, y, tc, tv, tl, mask, false);
          if (!r.ok) continue;
          const vv = immChain(r.nv, r.cells, r.ch) + r.lv;
          if (!have3 || vv > best3) { best3 = vv; have3 = true; }
        }
      }
      tot += have3 ? best3 : leafv(b2c, b2v) + x5(b2c, b2v);
    }
    return Math.floor(tot / 4);
  }

  /**
   * choose(col, vir, lnk, ca, cb, na, nb, allowed) -> action (var*8+col) or -1.
   * `allowed` is an int array[32] (the REACH mask); pass null to allow everything.
   * The input arrays are not modified.
   */
  function choose(col0, vir0, lnk0, ca, cb, na, nb, allowed) {
    const pcol = Int8Array.from(col0), pvir = Int8Array.from(vir0), plnk = Int8Array.from(lnk0);
    const nvir0 = virusCount(pvir);
    let bestVal = 0, bestAct = -1, have = false;
    for (let o4 = 0; o4 < 4; o4++) {
      const v = VAR_OF_O4[o4];
      for (let cl = 0; cl < 8; cl++) {
        if (allowed && !allowed[v * 8 + cl]) continue;
        const r1 = leafChain(pcol, pvir, plnk, nvir0, v, cl, ca, cb, c1, v1, l1, mask, true);
        if (!r1.ok) continue;
        const leaf1 = r1.lv, imm1 = immChain(r1.nv, r1.cells, r1.ch);
        let val;
        const nvir1 = virusCount(v1);
        if (nvir1 === 0) {
          val = imm1 + WIN;
        } else {
          let m2 = 0;
          for (let o42 = 0; o42 < 4; o42++) {
            const v2 = VAR_OF_O4[o42];
            for (let cl2 = 0; cl2 < 8; cl2++) {
              const r2 = leafChain(c1, v1, l1, nvir1, v2, cl2, na, nb, s2c, s2v, s2l, mask, true);
              if (!r2.ok) continue;
              const imm2 = immChain(r2.nv, r2.cells, r2.ch);
              keys2[m2] = imm2 + r2.lv;
              imms2[m2] = imm2;
              b2col[m2].set(s2c); b2vir[m2].set(s2v); b2lnk[m2].set(s2l);
              m2++;
            }
          }
          if (m2 === 0) {
            val = imm1 + leaf1;
          } else {
            stableDesc(keys2, m2, order2);
            const kk2 = TOPK2 > m2 ? m2 : TOPK2;
            let best2 = 0, have2 = false;
            for (let s = 0; s < kk2; s++) {
              const k2 = order2[s];
              const e = virusCount(b2vir[k2]) === 0 ? imms2[k2] + WIN
                : imms2[k2] + expectedThird(b2col[k2], b2vir[k2], b2lnk[k2]);
              if (!have2 || e > best2) { best2 = e; have2 = true; }
            }
            val = imm1 + leaf1 + Math.floor((best2 - leaf1) / 2);
          }
          val += W_EXCAV * excav(c1, v1) + W_HANG * hang(c1, v1);
        }
        val -= WS * stranded(c1, v1);
        if (!have || val > bestVal) { bestVal = val; bestAct = v * 8 + cl; have = true; }
      }
    }
    return bestAct;
  }

  // ---------------------------------------------------------------- REACH (reach_fw_tap.py, tap=P)
  const T_LAT = 19, G0 = 8, F0 = 3;
  const NROT = [0, 2, 1, 1];
  const DT = [0, 2, 5, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7];
  const SPEED_TABLE = [0x45, 0x43, 0x41, 0x3F, 0x3D, 0x3B, 0x39, 0x37, 0x35, 0x33, 0x31, 0x2F, 0x2D, 0x2B, 0x29, 0x27,
    0x25, 0x23, 0x21, 0x1F, 0x1D, 0x1B, 0x19, 0x17, 0x15, 0x13, 0x12, 0x11, 0x10, 0x0F, 0x0E, 0x0D,
    0x0C, 0x0B, 0x0A, 0x09, 0x09, 0x08, 0x08, 0x07, 0x07, 0x06, 0x06, 0x05, 0x05, 0x05, 0x05, 0x05,
    0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x04, 0x04, 0x04, 0x04, 0x04, 0x03, 0x03, 0x03, 0x03,
    0x03, 0x02, 0x02, 0x02, 0x02, 0x02, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00];
  const SPEED_BASE = [0x0F, 0x19, 0x1F]; // LOW, MED, HI

  function tableThreshold(pillsPlaced, speed) {
    return SPEED_TABLE[SPEED_BASE[speed] + Math.min(49, Math.floor(pillsPlaced / 10))];
  }

  function tops(col) {
    const t = new Array(COLS);
    for (let c = 0; c < COLS; c++) t[c] = topOcc(col, c);
    return t;
  }
  const tickFrame = (n, thr) => G0 + thr + n * (thr + 1);
  const rowAt = (t, thr) => (t < G0 + thr ? 0 : Math.floor((t - G0 - thr) / (thr + 1)) + 1);

  function fits(x, row, vert, col) {
    if (vert) {
      if (!(x >= 0 && x < COLS) || row >= ROWS) return false;
      return col[row * COLS + x] === 0 && (row - 1 < 0 || col[(row - 1) * COLS + x] === 0);
    }
    if (!(x >= 0 && x + 1 < COLS) || row >= ROWS) return false;
    return col[row * COLS + x] === 0 && col[row * COLS + x + 1] === 0;
  }
  function restFrom(col, x, row, vert) {
    let r = row;
    while (fits(x, r + 1, vert, col)) r++;
    return r;
  }
  function straightRest(top, x, vert) {
    return vert ? top[x] - 1 : Math.min(top[x], top[x + 1]) - 1;
  }
  function freeRowsBelow(col, row, lo, hi) {
    let y = 0;
    for (let r = row + 1; r < ROWS; r++) {
      let empty = true;
      for (let c = lo; c <= hi; c++) if (col[r * COLS + c] !== 0) { empty = false; break; }
      if (!empty) break;
      y++;
    }
    return y;
  }
  function prophDir(col, top) {
    if (top[3] > 2 && top[4] > 2) return 0;
    const gl = col[2] === 0 && col[COLS + 2] === 0;
    const gr = col[5] === 0 && col[COLS + 5] === 0;
    if (top[4] > top[3]) return gr ? 1 : (gl ? -1 : 0);
    return gl ? -1 : (gr ? 1 : 0);
  }

  function reachable(col, top, thr, v, column, tap) {
    const vert = v === 2 || v === 3;
    let x = 3, lastPress = -1;
    const pd = prophDir(col, top);
    if (pd !== 0) {
      let lockf = tickFrame(restFrom(col, x, 0, false), thr);
      for (let f = F0; f < T_LAT; f += tap) {
        if (f >= lockf) break;
        lastPress = f;
        const r = rowAt(f, thr);
        if (fits(x + pd, r, false, col)) {
          x += pd;
          lockf = tickFrame(restFrom(col, x, r, false), thr);
        }
      }
      if (lockf <= T_LAT) {
        const r = lockf > G0 + thr ? rowAt(lockf, thr) : 0;
        const land = restFrom(col, x, Math.min(r, restFrom(col, x, 0, false)), false);
        return v === 0 && x === column && land === straightRest(top, x, false);
      }
    }
    let r = rowAt(T_LAT - 1, thr);
    let lockf = tickFrame(restFrom(col, x, r, false), thr);
    const nrot = NROT[v];
    let f = T_LAT;
    if (lastPress >= 0) f = Math.max(T_LAT, lastPress + tap);
    let done = 0;
    while (done < nrot) {
      if (f >= lockf) return false;
      r = rowAt(f, thr);
      if (done === 0) {
        if (fits(x, r, true, col)) { done = 1; lockf = tickFrame(restFrom(col, x, r, true), thr); }
      } else {
        if (fits(x, r, false, col)) done = 2;
        else if (fits(x - 1, r, false, col)) { x -= 1; done = 2; }
        if (done === 2) lockf = tickFrame(restFrom(col, x, r, false), thr);
      }
      f += tap;
    }
    const t1 = f;
    const d = Math.abs(column - x);
    r = rowAt(Math.max(t1 - 1, 0), thr);
    const sd = column > x ? 1 : -1;
    for (let i = 1; i <= d; i++) {
      const ti = t1 + (i - 1) * tap;
      if (ti >= lockf) return false;
      const y = freeRowsBelow(col, rowAt(ti - 1, thr), Math.min(x, column), Math.max(x, column));
      if (DT[y] === 0) return false;
      r = rowAt(ti, thr);
      if (!fits(x + sd, r, vert, col)) return false;
      x += sd;
      lockf = tickFrame(restFrom(col, x, r, vert), thr);
    }
    return restFrom(col, x, r, vert) === straightRest(top, x, vert);
  }

  function reachMask(col, thr, tap) {
    tap = tap || 2;
    const top = tops(col);
    const out = new Array(32).fill(0);
    let any = false;
    for (let a = 0; a < 32; a++) {
      const v = a >> 3, c = a & 7, vert = v === 2 || v === 3;
      if (!vert && c + 1 >= COLS) continue;
      const rr = vert ? top[c] - 1 : Math.min(top[c], top[c + 1]) - 1;
      if (rr - (vert ? 1 : 0) < 0) continue;
      if (reachable(col, top, thr, v, c, tap)) { out[a] = 1; any = true; }
    }
    if (!any) out.fill(1);
    return out;
  }

  const api = {
    choose, reachMask, tableThreshold, evalRtl, resolve, gravity, findClears, applyClear,
    constants: { T_LAT, G0, F0, DT, SPEED_TABLE, SPEED_BASE, ROWS, COLS },
    decide(col, vir, lnk, ca, cb, na, nb, pillsPlaced, speed) {
      const mask = reachMask(col, tableThreshold(pillsPlaced, speed), 2);
      return { action: choose(col, vir, lnk, ca, cb, na, nb, mask), mask };
    },
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.AntibodyBrain = api;
})(typeof self !== "undefined" ? self : this);
