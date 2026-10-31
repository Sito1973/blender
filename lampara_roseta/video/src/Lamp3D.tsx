import React, { useLayoutEffect, useRef } from 'react';
import * as THREE from 'three';
import { DESIGN, PARAMS, arcTubeData, discData, ringData, type Frame, type MeshData } from './geometry';
import { C, H, W } from './ui';

export type LampView = {
  az: number;            // azimut de la cámara, grados (modelo, Z arriba)
  el: number;            // elevación, grados
  dist: number;          // distancia al objetivo, mm
  target: [number, number, number];
  upX?: number;          // 0 = arriba de pantalla es Z del modelo, 1 = arriba es X del modelo
  hl?: number;           // índice de la varilla resaltada
  hlMix?: number;        // 0..1 color de resaltado
  extract?: number;      // 0..1 la varilla sale y se acuesta
  dim?: number;          // 0..1 atenúa las demás varillas
  fade?: number;         // 0..1 esconde todo menos la varilla sacada
  build?: number;        // varillas puestas (orden de armado)
};

// Pose de la varilla acostada: cuerda paralela a Y, panza hacia +X, flotando sobre el domo.
export const FLAT = { xcm: -DESIGN.cur.sag / 2, zF: PARAMS.H + 180 };
const FOV = 30;

function frameToMatrix(f: Frame, M: THREE.Matrix4) {
  M.set(f.e1[0], f.e2[0], f.n[0], f.pos[0], f.e1[1], f.e2[1], f.n[1], f.pos[1], f.e1[2], f.e2[2], f.n[2], f.pos[2], 0, 0, 0, 1);
  return M;
}
function geo(d: MeshData) {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(d.pos, 3));
  g.setAttribute('normal', new THREE.BufferAttribute(d.nor, 3));
  g.setIndex(new THREE.BufferAttribute(d.idx, 1));
  return g;
}
const m2t = (x: number, y: number, z: number) => new THREE.Vector3(x, z, -y);

type Ctx = {
  renderer: THREE.WebGLRenderer; scene: THREE.Scene; camera: THREE.PerspectiveCamera;
  cur: THREE.InstancedMesh; mer: THREE.InstancedMesh; ring: THREE.Mesh; disc: THREE.Mesh; ex: THREE.Mesh;
  mats: { rod: THREE.MeshStandardMaterial; ring: THREE.MeshStandardMaterial; disc: THREE.MeshStandardMaterial; hl: THREE.MeshStandardMaterial };
  M0s: THREE.Matrix4[]; flat: THREE.Matrix4; zero: THREE.Matrix4;
};

export const Lamp3D: React.FC<{ v: LampView }> = ({ v }) => {
  const ref = useRef<HTMLCanvasElement>(null);
  const ctx = useRef<Ctx | null>(null);

  useLayoutEffect(() => {
    const canvas = ref.current!;
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(1);
    renderer.setSize(W, H, false);
    renderer.setClearColor(0x000000, 0);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(FOV, W / H, 5, 60000);
    const root = new THREE.Group();
    root.rotation.x = -Math.PI / 2;
    scene.add(root);
    scene.add(new THREE.HemisphereLight(0xfff3e0, 0x1a1d21, 0.8));
    const l1 = new THREE.DirectionalLight(0xffffff, 0.9); l1.position.set(0.8, 1.6, 1.2); scene.add(l1);
    const l2 = new THREE.DirectionalLight(0xffd9a8, 0.65); l2.position.set(-1.2, -1.4, -0.6); scene.add(l2);
    const l3 = new THREE.DirectionalLight(0xffffff, 0.35); l3.position.set(0.3, -1.5, 1.4); scene.add(l3);
    const rodCol = new THREE.Color(C.rod);
    const mats = {
      rod: new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.5, metalness: 0.22, transparent: true }),
      ring: new THREE.MeshStandardMaterial({ color: rodCol, roughness: 0.5, metalness: 0.28, transparent: true }),
      disc: new THREE.MeshStandardMaterial({ color: rodCol.clone().multiplyScalar(0.9), roughness: 0.55, metalness: 0.28, transparent: true }),
      hl: new THREE.MeshStandardMaterial({ color: new THREE.Color(C.hl), roughness: 0.4, metalness: 0.15, emissive: new THREE.Color(0x401505) }),
    };
    const d = DESIGN, p = PARAMS, r = p.d / 2;
    const gC = geo(arcTubeData(d.cur.R, d.cur.phi0, d.cur.phi1, r, 96, 12));
    const gM = geo(arcTubeData(d.mer.R, d.mer.phi0, d.mer.phi1, r, 64, 12));
    const cur = new THREE.InstancedMesh(gC, mats.rod, d.nCur);
    const mer = new THREE.InstancedMesh(gM, mats.rod, Math.max(1, d.nMer));
    cur.frustumCulled = false; mer.frustumCulled = false;
    const M0s = d.rods.map((rd) => frameToMatrix(rd.frame, new THREE.Matrix4()));
    d.rods.forEach((rd, i) => (rd.type === 'cur' ? cur : mer).setMatrixAt(rd.inst, M0s[i]));
    const merCol = rodCol.clone().lerp(new THREE.Color(0xffffff), 0.3);
    d.rods.forEach((rd) => (rd.type === 'cur' ? cur : mer).setColorAt(rd.inst, rd.type === 'cur' ? rodCol : merCol));
    const ring = new THREE.Mesh(geo(ringData(d.a - p.aw / 2, d.a + p.aw / 2, -p.at, 0, 240)), mats.ring);
    const disc = new THREE.Mesh(geo(discData(p.dd / 2, d.zDiscTop - 5, d.zDiscTop, 96)), mats.disc);
    const ex = new THREE.Mesh(gC, mats.hl);
    ex.matrixAutoUpdate = false; ex.visible = false;
    [cur, mer, ring, disc, ex].forEach((o) => root.add(o));
    const half = d.cur.Th / 2;
    const flat = frameToMatrix({ e1: [1, 0, 0], e2: [0, 1, 0], n: [0, 0, 1], pos: [FLAT.xcm - d.cur.R * Math.cos(half), 0, FLAT.zF] }, new THREE.Matrix4());
    ctx.current = { renderer, scene, camera, cur, mer, ring, disc, ex, mats, M0s, flat, zero: new THREE.Matrix4().makeScale(0, 0, 0) };
    return () => {
      renderer.dispose();
      renderer.forceContextLoss();
      ctx.current = null;
    };
  }, []);

  useLayoutEffect(() => {
    const c = ctx.current;
    if (!c) return;
    const d = DESIGN;
    const hl = v.hl ?? -1, hlMix = v.hlMix ?? 0, extract = v.extract ?? 0, dim = v.dim ?? 0, fade = v.fade ?? 0;
    const build = Math.max(0, Math.min(d.rods.length, Math.round(v.build ?? d.rods.length)));
    // colores
    const rodCol = new THREE.Color(C.rod), merCol = rodCol.clone().lerp(new THREE.Color(0xffffff), 0.3), hlCol = new THREE.Color(C.hl);
    d.rods.forEach((rd, i) => {
      const base = rd.type === 'cur' ? rodCol : merCol;
      (rd.type === 'cur' ? c.cur : c.mer).setColorAt(rd.inst, i === hl ? base.clone().lerp(hlCol, hlMix) : base);
    });
    if (c.cur.instanceColor) c.cur.instanceColor.needsUpdate = true;
    if (c.mer.instanceColor) c.mer.instanceColor.needsUpdate = true;
    // varilla sacada
    d.rods.forEach((rd, i) => (rd.type === 'cur' ? c.cur : c.mer).setMatrixAt(rd.inst, i === hl && extract > 0 ? c.zero : c.M0s[i]));
    c.cur.instanceMatrix.needsUpdate = true; c.mer.instanceMatrix.needsUpdate = true;
    if (hl >= 0 && extract > 0 && d.rods[hl].type === 'cur') {
      const p0 = new THREE.Vector3(), q0 = new THREE.Quaternion(), s0 = new THREE.Vector3();
      const p1 = new THREE.Vector3(), q1 = new THREE.Quaternion(), s1 = new THREE.Vector3();
      c.M0s[hl].decompose(p0, q0, s0); c.flat.decompose(p1, q1, s1);
      const pp = p0.clone().lerp(p1, extract);
      pp.z += Math.sin(Math.PI * extract) * d.a * 0.3;
      c.ex.matrix.compose(pp, q0.clone().slerp(q1, extract), s1);
      c.ex.matrixWorldNeedsUpdate = true;
      c.ex.visible = true;
    } else c.ex.visible = false;
    // atenuar y armar
    const o = (1 - 0.88 * dim) * (1 - fade);
    [c.mats.rod, c.mats.ring, c.mats.disc].forEach((m) => { m.opacity = o; m.depthWrite = o > 0.99; });
    c.cur.visible = c.mer.visible = c.ring.visible = c.disc.visible = o > 0.003;
    c.mer.count = Math.max(0, Math.min(build, d.nMer));
    c.cur.count = Math.max(0, Math.min(build - d.nMer, d.nCur));
    // cámara
    const az = (v.az * Math.PI) / 180, el = (v.el * Math.PI) / 180, t = v.target;
    const pos = [t[0] + v.dist * Math.cos(el) * Math.cos(az), t[1] + v.dist * Math.cos(el) * Math.sin(az), t[2] + v.dist * Math.sin(el)];
    const w = v.upX ?? 0;
    c.camera.up.set(w, 1 - w, 0).normalize();
    c.camera.position.copy(m2t(pos[0], pos[1], pos[2]));
    c.camera.lookAt(m2t(t[0], t[1], t[2]));
    c.renderer.render(c.scene, c.camera);
  });

  return <canvas ref={ref} width={W} height={H} style={{ position: 'absolute', inset: 0, width: W, height: H }} />;
};
