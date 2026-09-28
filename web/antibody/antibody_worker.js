// Runs the ANTIBODY search off the main thread so the bottles keep animating.
importScripts("antibody_brain.js");
self.onmessage = (e) => {
  const m = e.data;
  const t0 = performance.now();
  const d = self.AntibodyBrain.decide(m.col, m.vir, m.lnk, m.ca, m.cb, m.na, m.nb, m.placed, m.speed);
  self.postMessage({ id: m.id, action: d.action, mask: d.mask, ms: performance.now() - t0 });
};
