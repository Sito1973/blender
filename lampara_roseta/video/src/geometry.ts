// Geometría de la lámpara roseta: la misma del archivo de Blender y del Diseñador Roseta.
// Domo = casquete esférico. Cada pétalo es un círculo de la esfera que pasa por el polo,
// así que cada curva (medio pétalo, del disco al aro) es un arco plano de radio fijo.

export type V3 = [number, number, number];
export type Frame = { e1: V3; e2: V3; n: V3; pos: V3 };
export type Params = { D: number; H: number; N: number; m: number; rh: number; d: number; aw: number; at: number; dd: number; mer: boolean };
export type Piece = { R: number; phi0: number; phi1: number; Th: number; L: number; chord: number; sag: number };
export type Rod = { type: 'cur' | 'mer'; side?: 'A' | 'B'; k: number; inst: number; name: string; frame: Frame };
export type Design = {
  p: Params; a: number; Rs: number; zc: number; paso: number; alpha: number;
  cur: Piece & { hubAz: number; rimAz: number; midZ: number };
  mer: Piece; rods: Rod[]; nMer: number; nCur: number; zDiscTop: number;
};

export const PARAMS: Params = { D: 900, H: 250, N: 24, m: 4, rh: 70, d: 6, aw: 20, at: 5, dd: 170, mer: true };

const PI = Math.PI;
const deg = (r: number) => (r * 180) / PI;
const cross = (a: V3, b: V3): V3 => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const rotZ = (v: V3, t: number): V3 => [Math.cos(t) * v[0] - Math.sin(t) * v[1], Math.sin(t) * v[0] + Math.cos(t) * v[1], v[2]];
const rotFrame = (f: Frame, t: number): Frame => ({ e1: rotZ(f.e1, t), e2: rotZ(f.e2, t), n: rotZ(f.n, t), pos: rotZ(f.pos, t) });

export function applyFrame(f: Frame, q: V3): V3 {
  return [
    f.pos[0] + q[0] * f.e1[0] + q[1] * f.e2[0] + q[2] * f.n[0],
    f.pos[1] + q[0] * f.e1[1] + q[1] * f.e2[1] + q[2] * f.n[1],
    f.pos[2] + q[0] * f.e1[2] + q[1] * f.e2[2] + q[2] * f.n[2],
  ];
}

export function computeDesign(p: Params): Design {
  const a = p.D / 2, H = p.H, N = p.N, rh = p.rh, r = p.d / 2;
  const Rs = (a * a + H * H) / (2 * H), zc = H - Rs;
  const paso = (2 * PI) / N, alpha = (p.m * paso) / 2;
  const thRim = Math.asin(Math.min(1, a / Rs)), thHub = Math.asin(Math.min(1, rh / Rs));
  const petal = (thq: number) => {
    const Qx = Rs * Math.sin(thq), Qz = Rs * Math.cos(thq);
    const Cx = Qx / 2, Cz = (Rs + Qz) / 2;
    const rho = Math.hypot(Qx, Rs - Qz) / 2;
    return { Cx, Cz, rho, ux: -Cx / rho, uz: (Rs - Cz) / rho };
  };
  type Pe = ReturnType<typeof petal>;
  const pt = (pe: Pe, s: number): V3 => [pe.Cx + pe.rho * Math.cos(s) * pe.ux, pe.rho * Math.sin(s), pe.Cz + pe.rho * Math.cos(s) * pe.uz];
  const bis = (f: (x: number) => boolean, lo: number, hi: number) => {
    for (let i = 0; i < 64; i++) { const mid = (lo + hi) / 2; if (f(mid)) lo = mid; else hi = mid; }
    return (lo + hi) / 2;
  };
  const sRim = (pe: Pe) => bis((s) => pt(pe, s)[2] + zc > 0, 0, PI);
  const rimAz = (thq: number) => { const pe = petal(thq); const q = pt(pe, sRim(pe)); return Math.atan2(q[1], q[0]); };
  const thq = bis((t) => rimAz(t) < alpha, thRim + 1e-9, PI * 0.97);
  const pe = petal(thq);
  const s1 = sRim(pe);
  const s0 = bis((s) => { const q = pt(pe, s); return Math.hypot(q[0], q[1]) < rh; }, 0, s1);
  const Th = s1 - s0, sm = (s0 + s1) / 2, rho = pe.rho;
  const hubP = pt(pe, s0), rimP = pt(pe, s1), midP = pt(pe, sm);
  const frameSide = (w: number): Frame => {
    const c = Math.cos(sm), s = Math.sin(sm);
    const e1: V3 = [c * pe.ux, s * w, c * pe.uz];
    const e2: V3 = [-s * pe.ux, c * w, -s * pe.uz];
    return { e1, e2, n: cross(e1, e2), pos: [pe.Cx, 0, pe.Cz + zc] };
  };
  const fA = frameSide(1), fB = frameSide(-1);
  const cur = {
    R: rho, phi0: -Th / 2, phi1: Th / 2, Th, L: rho * Th, chord: 2 * rho * Math.sin(Th / 2), sag: rho * (1 - Math.cos(Th / 2)),
    hubAz: deg(Math.atan2(hubP[1], hubP[0])), rimAz: deg(Math.atan2(rimP[1], rimP[0])), midZ: midP[2] + zc,
  };
  const ThM = thRim - thHub;
  const mer: Piece = { R: Rs, phi0: PI / 2 - thRim, phi1: PI / 2 - thHub, Th: ThM, L: Rs * ThM, chord: 2 * Rs * Math.sin(ThM / 2), sag: Rs * (1 - Math.cos(ThM / 2)) };
  const merOff = p.m % 2 === 0 ? paso / 2 : 0;
  const rods: Rod[] = [];
  if (p.mer) {
    for (let k = 0; k < N; k++) {
      const ps = merOff + k * paso;
      const e1: V3 = [Math.cos(ps), Math.sin(ps), 0], e2: V3 = [0, 0, 1];
      rods.push({ type: 'mer', k, inst: k, name: 'M' + String(k + 1).padStart(2, '0'), frame: { e1, e2, n: cross(e1, e2), pos: [0, 0, zc] } });
    }
  }
  const nMer = rods.length;
  ([['A', fA], ['B', fB]] as const).forEach(([side, f]) => {
    for (let k = 0; k < N; k++) {
      rods.push({ type: 'cur', side, k, inst: (side === 'A' ? 0 : N) + k, name: String(k + 1).padStart(2, '0') + side, frame: rotFrame(f, k * paso) });
    }
  });
  const zS = (x: number) => zc + Math.sqrt(Rs * Rs - x * x);
  return { p, a, Rs, zc, paso, alpha, cur, mer, rods, nMer, nCur: 2 * N, zDiscTop: zS((rh + p.dd / 2) / 2) - r };
}

export type MeshData = { pos: Float32Array; nor: Float32Array; idx: Uint32Array };

export function arcTubeData(R: number, phi0: number, phi1: number, r: number, segs: number, rad: number): MeshData {
  const pos: number[] = [], nor: number[] = [], idx: number[] = [];
  for (let i = 0; i <= segs; i++) {
    const ph = phi0 + ((phi1 - phi0) * i) / segs, c = Math.cos(ph), s = Math.sin(ph);
    for (let j = 0; j < rad; j++) {
      const b = (2 * PI * j) / rad, cb = Math.cos(b), sb = Math.sin(b);
      const nx = c * cb, ny = s * cb, nz = sb;
      pos.push(R * c + r * nx, R * s + r * ny, r * nz);
      nor.push(nx, ny, nz);
    }
  }
  for (let i = 0; i < segs; i++) for (let j = 0; j < rad; j++) {
    const A = i * rad + j, B = i * rad + ((j + 1) % rad), C = (i + 1) * rad + j, D = (i + 1) * rad + ((j + 1) % rad);
    idx.push(A, C, B, B, C, D);
  }
  for (const [ci, sg] of [[0, -1], [segs, 1]]) {
    const ph = phi0 + ((phi1 - phi0) * ci) / segs, c = Math.cos(ph), s = Math.sin(ph);
    const T = [-s * sg, c * sg, 0], base = pos.length / 3;
    pos.push(R * c, R * s, 0); nor.push(T[0], T[1], T[2]);
    for (let j = 0; j < rad; j++) {
      const b = (2 * PI * j) / rad, cb = Math.cos(b), sb = Math.sin(b);
      pos.push(R * c + r * c * cb, R * s + r * s * cb, r * sb); nor.push(T[0], T[1], T[2]);
    }
    for (let j = 0; j < rad; j++) {
      const p1 = base + 1 + j, p2 = base + 1 + ((j + 1) % rad);
      if (sg < 0) idx.push(base, p1, p2); else idx.push(base, p2, p1);
    }
  }
  return { pos: new Float32Array(pos), nor: new Float32Array(nor), idx: new Uint32Array(idx) };
}

export function ringData(rin: number, rout: number, z0: number, z1: number, segs: number): MeshData {
  const pos: number[] = [], nor: number[] = [], idx: number[] = [];
  const strip = (fn: (c: number, s: number, u: number) => V3, nfn: (c: number, s: number) => V3, flip: boolean) => {
    const base = pos.length / 3;
    for (let i = 0; i <= segs; i++) {
      const t = (2 * PI * i) / segs, c = Math.cos(t), s = Math.sin(t);
      const A = fn(c, s, 0), B = fn(c, s, 1), n = nfn(c, s);
      pos.push(...A, ...B); nor.push(...n, ...n);
    }
    for (let k = 0; k < segs; k++) {
      const a0 = base + 2 * k, a1 = a0 + 1, b0 = a0 + 2, b1 = a0 + 3;
      if (!flip) idx.push(a0, b0, a1, a1, b0, b1); else idx.push(a0, a1, b0, a1, b1, b0);
    }
  };
  strip((c, s, u) => { const rr = u ? rout : rin; return [rr * c, rr * s, z1]; }, () => [0, 0, 1], true);
  strip((c, s, u) => { const rr = u ? rout : rin; return [rr * c, rr * s, z0]; }, () => [0, 0, -1], false);
  strip((c, s, u) => [rout * c, rout * s, u ? z1 : z0], (c, s) => [c, s, 0], false);
  strip((c, s, u) => [rin * c, rin * s, u ? z1 : z0], (c, s) => [-c, -s, 0], true);
  return { pos: new Float32Array(pos), nor: new Float32Array(nor), idx: new Uint32Array(idx) };
}

export function discData(rr: number, z0: number, z1: number, segs: number): MeshData {
  const pos: number[] = [], nor: number[] = [], idx: number[] = [];
  for (const [z, nz] of [[z1, 1], [z0, -1]]) {
    const base = pos.length / 3;
    pos.push(0, 0, z); nor.push(0, 0, nz);
    for (let i = 0; i < segs; i++) { const t = (2 * PI * i) / segs; pos.push(rr * Math.cos(t), rr * Math.sin(t), z); nor.push(0, 0, nz); }
    for (let k = 0; k < segs; k++) {
      const p1 = base + 1 + k, p2 = base + 1 + ((k + 1) % segs);
      if (nz > 0) idx.push(base, p1, p2); else idx.push(base, p2, p1);
    }
  }
  const base = pos.length / 3;
  for (let i = 0; i <= segs; i++) {
    const t = (2 * PI * i) / segs, c = Math.cos(t), s = Math.sin(t);
    pos.push(rr * c, rr * s, z0, rr * c, rr * s, z1); nor.push(c, s, 0, c, s, 0);
  }
  for (let k = 0; k < segs; k++) { const a0 = base + 2 * k, a1 = a0 + 1, b0 = a0 + 2, b1 = a0 + 3; idx.push(a0, b0, a1, a1, b0, b1); }
  return { pos: new Float32Array(pos), nor: new Float32Array(nor), idx: new Uint32Array(idx) };
}

// Datos de taller (los mismos que muestra el Diseñador Roseta)
export const DESIGN = computeDesign(PARAMS);
export const SHOP = (() => {
  const d = PARAMS.d, r = d / 2;
  const cut = Math.ceil((DESIGN.cur.L + 30) / 10) * 10;
  const per = Math.floor(6000 / (cut + 3));
  const bars = Math.ceil(DESIGN.nCur / per);
  const k = (3.395 * 250) / (200000 * d); // retorno elástico, acero 1020/A36
  const form = 1 / (1 / DESIGN.cur.R + k) - r;
  return { cut, per, bars, leftover: 6000 - per * (cut + 3), form, wrapR: form + r };
})();

export const fmt = (x: number, dec = 1) => x.toLocaleString('es-CO', { minimumFractionDigits: dec, maximumFractionDigits: dec });
