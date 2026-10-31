import React from 'react';
import { Easing, interpolate, useCurrentFrame } from 'remotion';
import { DESIGN, SHOP, fmt } from './geometry';
import { FLAT, Lamp3D, type LampView } from './Lamp3D';
import { C, Check, F, Reveal, StepHeader, lerp, prog } from './ui';

const cur = DESIGN.cur;
const deg = (r: number) => (r * 180) / Math.PI;
const HL = Math.max(0, DESIGN.rods.findIndex((r) => r.name === '18A'));

/* ---------------- 1 · Título ---------------- */
export const S1Title: React.FC = () => {
  const f = useCurrentFrame();
  const t = f / 150;
  const v: LampView = { az: lerp(-64, -46, t), el: -21, dist: lerp(4150, 3900, t), target: [0, 0, 440] };
  return (
    <>
      <Lamp3D v={v} />
      <Reveal from={6} style={{ top: 200, left: 80, right: 80, fontFamily: F.mono, fontSize: 30, letterSpacing: '0.12em', color: C.brass }}>
        LÁMPARA ROSETA · ESTRUCTURA EN VARILLA
      </Reveal>
      <Reveal from={14} style={{ top: 262, left: 74, right: 60, fontFamily: F.display, fontWeight: 700, fontSize: 172, lineHeight: 0.88, color: C.ink, textTransform: 'uppercase' }}>
        Cómo se hace<br />la varilla
      </Reveal>
      <Reveal from={34} style={{ top: 600, left: 80, right: 80, fontFamily: F.body, fontWeight: 500, fontSize: 50, color: C.muted }}>
        Paso a paso, en un minuto
      </Reveal>
    </>
  );
};

/* ---------------- 2 · Una sola pieza (sale del domo y se acuesta) ---------------- */
export const S_PX = 1.6667; // px por mm en la vista de la pieza (escena 2 y 3)
const DRAW_Y = 1180;        // cuerda de la pieza en pantalla
const TOP_DIST = 960 / (S_PX * Math.tan((15 * Math.PI) / 180));
export const S2OnePiece: React.FC = () => {
  const f = useCurrentFrame();
  const rise = prog(f, 120, 222);
  const finalT: [number, number, number] = [FLAT.xcm + (DRAW_Y - 960) / S_PX, 0, FLAT.zF];
  const v: LampView = {
    az: lerp(-46, -180, rise), el: lerp(-21, 90, rise), dist: lerp(3900, TOP_DIST, rise),
    target: [lerp(0, finalT[0], rise), 0, lerp(440, finalT[2], rise)],
    upX: prog(f, 185, 222),
    hl: HL, hlMix: prog(f, 14, 32), extract: prog(f, 60, 150), dim: prog(f, 52, 92), fade: prog(f, 165, 222),
  };
  return (
    <>
      <Lamp3D v={v} />
      <Reveal from={12} to={112} style={{ top: 200, left: 80, right: 80, color: C.ink }}>
        <div style={{ fontFamily: F.body, fontWeight: 500, fontSize: 52 }}>La lámpara tiene</div>
        <div style={{ fontFamily: F.display, fontWeight: 700, fontSize: 190, lineHeight: 0.92, textTransform: 'uppercase' }}>
          <span style={{ color: C.hl }}>48</span> curvas
        </div>
      </Reveal>
      <Reveal from={116} to={226} style={{ top: 200, left: 80, right: 80, color: C.ink }}>
        <div style={{ fontFamily: F.body, fontWeight: 500, fontSize: 52 }}>y todas son</div>
        <div style={{ fontFamily: F.display, fontWeight: 700, fontSize: 150, lineHeight: 0.92, textTransform: 'uppercase' }}>
          la misma <span style={{ color: C.hl }}>pieza</span>
        </div>
      </Reveal>
    </>
  );
};

/* ---------------- 3 · Las medidas ---------------- */
const half = cur.Th / 2;
const PX = (xmm: number, ymm: number): [number, number] => [540 + xmm * S_PX, DRAW_Y - ymm * S_PX];
const Rp = cur.R * S_PX;
const yc = -cur.R * Math.cos(half);
const [ctrX, ctrY] = PX(0, yc);
const [rx, ry] = PX(cur.R * Math.sin(half), 0);
const [lx, ly] = PX(-cur.R * Math.sin(half), 0);
const [, topY] = PX(0, cur.sag);
const ARC_D = `M ${rx} ${ry} A ${Rp} ${Rp} 0 0 0 ${lx} ${ly}`;

export const S3Measures: React.FC = () => {
  const f = useCurrentFrame();
  const eje = prog(f, 18, 44), chord = prog(f, 40, 66), sag = prog(f, 68, 92), rad = prog(f, 94, 124), len = prog(f, 128, 166);
  const angR = Math.atan2(ry - ctrY, rx - ctrX), angL = Math.atan2(ly - ctrY, lx - ctrX);
  const ra = 92;
  const runner = prog(f, 130, 170, Easing.inOut(Easing.cubic));
  const runA = Math.PI / 2 - half + 2 * half * runner;
  return (
    <>
      <Reveal from={6} style={{ top: 175, left: 80, right: 80, fontFamily: F.mono, fontSize: 30, letterSpacing: '0.12em', color: C.brass }}>LA PIEZA</Reveal>
      <Reveal from={10} style={{ top: 222, left: 76, right: 60, fontFamily: F.display, fontWeight: 700, fontSize: 124, lineHeight: 0.92, color: C.ink, textTransform: 'uppercase' }}>Un arco plano</Reveal>
      <Reveal from={22} style={{ top: 360, left: 80, right: 80, fontFamily: F.body, fontWeight: 500, fontSize: 48, lineHeight: 1.25, color: C.muted }}>
        Varilla lisa de 6 mm doblada a un radio fijo. Apoyada en la mesa no cojea.
      </Reveal>
      <svg width={1080} height={1920} style={{ position: 'absolute', inset: 0 }}>
        {/* radios, centro y ángulo */}
        <g opacity={rad}>
          <line x1={ctrX} y1={ctrY} x2={lerp(ctrX, rx, rad)} y2={lerp(ctrY, ry, rad)} stroke={C.muted} strokeWidth={3} strokeDasharray="12 9" />
          <line x1={ctrX} y1={ctrY} x2={lerp(ctrX, lx, rad)} y2={lerp(ctrY, ly, rad)} stroke={C.muted} strokeWidth={3} strokeDasharray="12 9" />
          <path d={`M ${ctrX + ra * Math.cos(angR)} ${ctrY + ra * Math.sin(angR)} A ${ra} ${ra} 0 0 0 ${ctrX + ra * Math.cos(angL)} ${ctrY + ra * Math.sin(angL)}`} fill="none" stroke={C.cota} strokeWidth={4} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - rad} />
          <path d={`M ${ctrX - 16} ${ctrY} H ${ctrX + 16} M ${ctrX} ${ctrY - 16} V ${ctrY + 16}`} stroke={C.cota} strokeWidth={4} fill="none" />
          <text x={ctrX} y={ctrY - ra - 18} textAnchor="middle" fontFamily={F.mono} fontSize={40} fontWeight={600} fill={C.cota}>{fmt(deg(cur.Th))}°</text>
          <text x={ctrX} y={ctrY + 58} textAnchor="middle" fontFamily={F.body} fontSize={34} fill={C.muted}>centro del doblez</text>
          <g transform={`translate(${lerp(ctrX, rx, 0.56) + 26} ${lerp(ctrY, ry, 0.56) + 22}) rotate(${(angR * 180) / Math.PI})`}>
            <text x={0} y={0} textAnchor="middle" fontFamily={F.mono} fontSize={38} fontWeight={500} fill={C.ink}>R {fmt(cur.R)} mm</text>
          </g>
        </g>
        {/* varilla */}
        <path d={ARC_D} fill="none" stroke={C.hl} strokeWidth={6 * S_PX} />
        <path d={ARC_D} fill="none" stroke={C.eje} strokeWidth={3} strokeDasharray="22 8 4 8" opacity={eje} />
        {/* largo: punto que recorre el arco */}
        {runner > 0 && runner < 1 ? <circle cx={540 + Rp * Math.cos(runA)} cy={ctrY - Rp * Math.sin(runA)} r={14} fill={C.ink} /> : null}
        <text x={540} y={topY - 34} textAnchor="middle" fontFamily={F.mono} fontSize={42} fontWeight={600} fill={C.ink} opacity={len}>largo {fmt(cur.L)} mm</text>
        {/* cuerda */}
        <line x1={lerp(540, rx, 0)} y1={ry} x2={lerp(540, rx, chord)} y2={ry} stroke={C.cota} strokeWidth={4} />
        <line x1={540} y1={ly} x2={lerp(540, lx, chord)} y2={ly} stroke={C.cota} strokeWidth={4} />
        <text x={540} y={ry + 58} textAnchor="middle" fontFamily={F.mono} fontSize={42} fontWeight={600} fill={C.cota} opacity={chord}>cuerda {fmt(cur.chord)} mm</text>
        {/* flecha */}
        <line x1={540} y1={ry} x2={540} y2={lerp(ry, topY, sag)} stroke={C.cota} strokeWidth={4} />
        <text x={520} y={(ry + topY) / 2 + 14} textAnchor="end" fontFamily={F.mono} fontSize={38} fontWeight={600} fill={C.cota} opacity={sag}>flecha {fmt(cur.sag)}</text>
      </svg>
      <Reveal from={168} style={{ top: 1560, left: 80, right: 80, display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', borderTop: `2px solid ${C.line}`, paddingTop: 24 }}>
        <span style={{ fontFamily: F.display, fontWeight: 700, fontSize: 84, color: C.hl, textTransform: 'uppercase' }}>Hacer 48</span>
        <span style={{ fontFamily: F.body, fontWeight: 500, fontSize: 40, color: C.muted, textAlign: 'right' }}>la mitad se monta<br />volteada</span>
      </Reveal>
    </>
  );
};

/* ---------------- 4 · Cortar ---------------- */
export const S4Cut: React.FC = () => {
  const f = useCurrentFrame();
  const x0 = 90, x1 = 990, y = 1010, s = (x1 - x0) / 6000, piece = SHOP.cut + 3;
  const nCuts = SHOP.per;
  const cutT = (k: number) => 34 + k * 8.5; // frame de cada corte
  const sep = prog(f, cutT(nCuts) + 6, cutT(nCuts) + 26);
  const pieces = Array.from({ length: nCuts + 1 }, (_, k) => {
    const a = k * piece, b = k < nCuts ? (k + 1) * piece - 3 : 6000;
    const done = k < nCuts ? f >= cutT(k + 1) : f >= cutT(nCuts);
    return { a, b, done, left: k === nCuts };
  });
  return (
    <>
      <StepHeader n={1} title="Cortar" caption={`${DESIGN.nCur} tramos de ${SHOP.cut} mm`} caption2={`${fmt(cur.L)} de pieza más un sobrante para recortar al final.`} c2From={26} />
      <svg width={1080} height={1920} style={{ position: 'absolute', inset: 0 }}>
        <text x={x0} y={y - 54} fontFamily={F.mono} fontSize={32} fill={C.muted} opacity={prog(f, 12, 24)}>barra de 6 m</text>
        {pieces.map((pc, k) => {
          const gap = sep * (k - nCuts / 2) * 7;
          const xa = x0 + pc.a * s + gap, xb = x0 + pc.b * s + gap;
          const col = pc.left ? (pc.done ? '#6b6760' : C.rod) : pc.done ? C.hl : C.rod;
          return <rect key={k} x={xa} y={y - 10} width={Math.max(1, xb - xa)} height={20} rx={4} fill={col} opacity={prog(f, 4, 16)} />;
        })}
        {Array.from({ length: nCuts }, (_, k) => {
          const cx = x0 + ((k + 1) * piece - 1.5) * s, t0 = cutT(k + 1);
          const sp = prog(f, t0 - 4, t0 + 8);
          if (sp <= 0 || sp >= 1) return null;
          return (
            <g key={k} opacity={1 - sp}>
              {[-70, -35, 0, 35, 70, 110, -110].map((a, i) => {
                const rr = 18 + 46 * sp, ang = ((a - 90) * Math.PI) / 180;
                return <line key={i} x1={cx + 10 * Math.cos(ang)} y1={y + 10 * Math.sin(ang)} x2={cx + rr * Math.cos(ang)} y2={y + rr * Math.sin(ang)} stroke="#ffd27a" strokeWidth={4} strokeLinecap="round" />;
              })}
            </g>
          );
        })}
        <g opacity={prog(f, cutT(1), cutT(1) + 10)}>
          <path d={`M ${x0} ${y + 46} V ${y + 66} M ${x0 + SHOP.cut * s} ${y + 46} V ${y + 66} M ${x0} ${y + 56} H ${x0 + SHOP.cut * s}`} stroke={C.ink} strokeWidth={3} />
          <text x={x0 + (SHOP.cut * s) / 2} y={y + 106} textAnchor="middle" fontFamily={F.mono} fontSize={32} fill={C.ink}>{SHOP.cut}</text>
        </g>
        <text x={x1} y={y + 106} textAnchor="end" fontFamily={F.mono} fontSize={30} fill={C.muted} opacity={sep}>sobran {Math.round(SHOP.leftover)}</text>
        {/* 6 barras */}
        {Array.from({ length: SHOP.bars }, (_, i) => (
          <rect key={i} x={x0} y={1270 + i * 34} width={(x1 - x0) * prog(f, 120 + i * 5, 136 + i * 5)} height={14} rx={4} fill={C.rod} opacity={0.9} />
        ))}
      </svg>
      <Reveal from={112} style={{ top: 1500, left: 80, right: 80, fontFamily: F.body, fontWeight: 500, fontSize: 46, lineHeight: 1.3, color: C.ink }}>
        Salen <b style={{ color: C.hl }}>{SHOP.per} por barra</b>: compra <b style={{ color: C.hl }}>{SHOP.bars} barras</b> de 6 m. Te quedan {SHOP.per * SHOP.bars - DESIGN.nCur} tramos para probar.
      </Reveal>
    </>
  );
};

/* ---------------- 5 a 8 · Taller: trazar, horma, doblar, revisar ---------------- */
const SW = 1.3;
const O = { x: 540, y: 1330 };
const R = cur.R, RF = SHOP.form, RW = SHOP.wrapR;
const A0 = Math.PI / 2 - half, A1 = Math.PI / 2 + half;
const EXTRA = 15;
const LROD = cur.L + 2 * EXTRA;
const AST = A0 - EXTRA / R;
const toS = (rmm: number, a: number): [number, number] => [O.x + rmm * SW * Math.cos(a), O.y - rmm * SW * Math.sin(a)];
const arcPath = (rmm: number, aFrom: number, aTo: number) => {
  const [x0, y0] = toS(rmm, aFrom), [x1, y1] = toS(rmm, aTo);
  const sweep = aTo > aFrom ? 0 : 1, large = Math.abs(aTo - aFrom) > Math.PI ? 1 : 0;
  return `M ${x0} ${y0} A ${rmm * SW} ${rmm * SW} 0 ${large} ${sweep} ${x1} ${y1}`;
};
const NS = 140;
function bentShape(theta: number): [number, number][] {
  const pts: [number, number][] = [], sc = RW * theta;
  for (let i = 0; i <= NS; i++) {
    const s = (LROD * i) / NS;
    if (s <= sc) pts.push(toS(RW, AST + s / RW));
    else {
      const at = AST + theta, [bx, by] = toS(RW, at);
      pts.push([bx + (s - sc) * SW * -Math.sin(at), by + (s - sc) * SW * -Math.cos(at)]);
    }
  }
  return pts;
}
function finalShape(): [number, number][] {
  const pts: [number, number][] = [];
  for (let i = 0; i <= NS; i++) pts.push(toS(R, AST + (LROD * i) / NS / R));
  return pts;
}
const poly = (pts: [number, number][]) => 'M ' + pts.map((p) => `${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(' L ');

// tiempos (frames locales del taller)
export const T_TRAZ = 0, T_HORMA = 210, T_DOBLAR = 420, T_REV = 630, T_END = 810;

export const Workshop: React.FC = () => {
  const f = useCurrentFrame();
  const board = prog(f, 0, 14);
  // trazar
  const draw = prog(f, 30, 140, Easing.inOut(Easing.sin));
  const pa = lerp(A1, A0, draw);
  const strOn = f < T_HORMA - 20 ? prog(f, 22, 30) : 1 - prog(f, T_HORMA - 20, T_HORMA);
  const chordChk = prog(f, 150, 172) * (1 - prog(f, T_HORMA - 14, T_HORMA));
  // horma
  const saw = prog(f, T_HORMA + 24, T_HORMA + 92);
  const formFill = prog(f, T_HORMA + 86, T_HORMA + 110);
  const extras = prog(f, T_HORMA + 110, T_HORMA + 130);
  const gapNote = prog(f, T_HORMA + 128, T_HORMA + 146) * (1 - prog(f, T_DOBLAR - 12, T_DOBLAR));
  // doblar
  const rodIn = prog(f, T_DOBLAR + 6, T_DOBLAR + 22);
  const bend = prog(f, T_DOBLAR + 28, T_DOBLAR + 128, Easing.inOut(Easing.quad));
  const release = prog(f, T_DOBLAR + 138, T_DOBLAR + 162, Easing.out(Easing.back(1.4)));
  const clampOn = rodIn * (1 - prog(f, T_DOBLAR + 132, T_DOBLAR + 142));
  const okBend = prog(f, T_DOBLAR + 166, T_DOBLAR + 182) * (1 - prog(f, T_REV - 10, T_REV));
  // revisar
  const marks = prog(f, T_REV + 8, T_REV + 22);
  const cut = prog(f, T_REV + 30, T_REV + 58);
  const gauge = prog(f, T_REV + 62, T_REV + 80);
  const formDim = 1 - 0.55 * prog(f, T_REV, T_REV + 20);

  let rod: [number, number][] = [];
  if (f >= T_DOBLAR) {
    const A = bentShape(bend * (LROD / RW)), B = finalShape();
    rod = release > 0 ? A.map((p, i) => [lerp(p[0], B[i][0], release), lerp(p[1], B[i][1], release)] as [number, number]) : A;
  }
  // en el paso 5 las puntas sobrantes se recortan
  const iCut0 = Math.round((EXTRA / LROD) * NS), iCut1 = NS - iCut0;
  const mainRod = f >= T_REV ? rod.slice(iCut0, iCut1 + 1) : rod;
  const tipL = rod.slice(0, iCut0 + 1), tipR = rod.slice(iCut1);
  const fall = (pts: [number, number][], dir: number): [number, number][] =>
    pts.map(([x, y]) => [x + dir * 50 * cut, y + 160 * cut * cut]);

  const [s0x, s0y] = toS(RW, AST);
  const clampAng = -((AST * 180) / Math.PI);
  const [e0x, e0y] = toS(R, A0), [e1x, e1y] = toS(R, A1), [tx, ty] = toS(R, Math.PI / 2);
  const stop = toS(RF + 9, AST - 0.075);
  const screws: [number, number][] = [[540, 1185], [430, 1205], [650, 1205]];

  return (
    <svg width={1080} height={1920} style={{ position: 'absolute', inset: 0 }} opacity={board}>
      {/* tabla */}
      <rect x={160} y={860} width={760} height={570} rx={14} fill={C.board} stroke={C.boardEdge} strokeWidth={3} />
      {[0, 1, 2, 3, 4, 5].map((i) => (
        <path key={i} d={`M 175 ${905 + i * 88} C 380 ${895 + i * 88}, 700 ${918 + i * 88}, 905 ${902 + i * 88}`} stroke="#ffffff" strokeOpacity={0.07} strokeWidth={3} fill="none" />
      ))}
      {/* horma */}
      {f >= T_HORMA ? (
        <g opacity={formDim}>
          <path d={`${arcPath(RF, 0.38, Math.PI - 0.38)} Z`} fill={C.form} opacity={formFill} />
          <path d={arcPath(RF, 0.38, Math.PI - 0.38)} fill="none" stroke="#e8cf9f" strokeWidth={4} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - saw} />
          <g opacity={extras}>
            {screws.map(([x, y], i) => <circle key={i} cx={x} cy={y} r={9} fill="#c9c4bb" stroke="#5f584d" strokeWidth={3} />)}
            <rect x={stop[0] - 16} y={stop[1] - 24} width={32} height={48} rx={5} fill={C.form} stroke="#e8cf9f" strokeWidth={3} transform={`rotate(${clampAng} ${stop[0]} ${stop[1]})`} />
          </g>
          <text x={540} y={1300} textAnchor="middle" fontFamily={F.mono} fontSize={34} fill="#f1dcb5" opacity={extras * (1 - prog(f, T_DOBLAR + 20, T_DOBLAR + 34))}>horma R {fmt(RF, 0)}</text>
        </g>
      ) : null}
      {/* trazo a lápiz (eje de la pieza) */}
      <path d={f < T_HORMA ? arcPath(R, A1, pa) : arcPath(R, A1, A0)} fill="none" stroke={C.pencil} strokeWidth={4} opacity={0.95} />
      {/* clavo y cordel */}
      <g opacity={strOn}>
        <line x1={O.x} y1={O.y} x2={toS(R, pa)[0]} y2={toS(R, pa)[1]} stroke="#efe6d2" strokeWidth={3} />
        <circle cx={O.x} cy={O.y} r={11} fill="#c9c4bb" stroke="#4a443b" strokeWidth={3} />
        <circle cx={toS(R, pa)[0]} cy={toS(R, pa)[1]} r={10} fill={C.pencil} stroke="#f2c46b" strokeWidth={4} />
        <text x={O.x + 22} y={O.y + 44} fontFamily={F.body} fontSize={34} fill="#f3e9d7">clavo</text>
        <g transform={`translate(${(O.x + toS(R, pa)[0]) / 2} ${(O.y + toS(R, pa)[1]) / 2}) rotate(${(() => { let a = -(pa * 180) / Math.PI; if (a < -90) a += 180; return a; })()})`}>
          <text x={0} y={-14} textAnchor="middle" fontFamily={F.mono} fontSize={30} fill="#f3e9d7">cordel {fmt(R)} mm</text>
        </g>
      </g>
      {/* comprobar cuerda */}
      <g opacity={chordChk}>
        <line x1={e1x} y1={e1y} x2={e0x} y2={e0y} stroke={C.cota} strokeWidth={4} strokeDasharray="14 8" />
        <text x={540} y={e0y + 52} textAnchor="middle" fontFamily={F.mono} fontSize={36} fontWeight={600} fill="#ffd1c9">cuerda {fmt(cur.chord)} mm</text>
        <Check x={e0x + 46} y={e0y - 6} t={chordChk} />
      </g>
      {/* diferencia horma / pieza */}
      <g opacity={gapNote}>
        <path d={`M ${tx} ${ty + 6} V ${O.y - RF * SW - 6}`} stroke={C.ink} strokeWidth={3} />
        <path d={`M ${tx - 10} ${ty + 16} L ${tx} ${ty + 4} L ${tx + 10} ${ty + 16} M ${tx - 10} ${O.y - RF * SW - 16} L ${tx} ${O.y - RF * SW - 4} L ${tx + 10} ${O.y - RF * SW - 16}`} stroke={C.ink} strokeWidth={3} fill="none" />
        <text x={tx + 20} y={(ty + O.y - RF * SW) / 2 + 12} fontFamily={F.mono} fontSize={32} fill={C.ink}>{fmt(R - RF, 0)} mm</text>
      </g>
      {/* varilla */}
      {rod.length ? (
        <g opacity={rodIn}>
          <path d={poly(mainRod)} fill="none" stroke={C.hl} strokeWidth={11} strokeLinecap="round" strokeLinejoin="round" />
          {f >= T_REV ? (
            <g opacity={1 - cut}>
              <path d={poly(fall(tipL, -1))} fill="none" stroke={C.hl} strokeWidth={11} strokeLinecap="round" />
              <path d={poly(fall(tipR, 1))} fill="none" stroke={C.hl} strokeWidth={11} strokeLinecap="round" />
            </g>
          ) : null}
        </g>
      ) : null}
      {/* prensa */}
      <g opacity={clampOn} transform={`translate(${s0x} ${s0y}) rotate(${clampAng})`}>
        <rect x={-22} y={-58} width={44} height={116} rx={8} fill="#55595f" stroke="#2c2f33" strokeWidth={3} />
        <rect x={22} y={-8} width={70} height={16} rx={4} fill="#8a8f96" />
        <rect x={86} y={-30} width={14} height={60} rx={4} fill="#c64b2b" />
      </g>
      {/* ok doblado */}
      <g opacity={okBend}>
        <Check x={tx - 190} y={ty - 66} t={okBend} size={54} />
        <text x={tx - 152} y={ty - 54} fontFamily={F.body} fontWeight={600} fontSize={38} fill={C.ok}>coincide con el trazo</text>
      </g>
      {/* marcas de corte y chispas */}
      <g opacity={marks * (1 - prog(f, T_REV + 60, T_REV + 70))}>
        {[A0, A1].map((a, i) => {
          const [ax, ay] = toS(R - 22, a), [bx, by] = toS(R + 22, a);
          return <line key={i} x1={ax} y1={ay} x2={bx} y2={by} stroke={C.cota} strokeWidth={5} />;
        })}
      </g>
      {[A0, A1].map((a, i) => {
        const sp = prog(f, T_REV + 28, T_REV + 44);
        if (sp <= 0 || sp >= 1) return null;
        const [cx, cy] = toS(R, a);
        return (
          <g key={i} opacity={1 - sp}>
            {[0, 50, 100, 150, 200, 250, 300].map((d, j) => {
              const ang = ((d + i * 25) * Math.PI) / 180, rr = 14 + 40 * sp;
              return <line key={j} x1={cx + 8 * Math.cos(ang)} y1={cy + 8 * Math.sin(ang)} x2={cx + rr * Math.cos(ang)} y2={cy + rr * Math.sin(ang)} stroke="#ffd27a" strokeWidth={4} strokeLinecap="round" />;
            })}
          </g>
        );
      })}
      {/* galga de 3 topes */}
      <g opacity={gauge}>
        {[[e1x - 24, e1y + 14], [e0x + 24, e0y + 14], [tx, ty - 26]].map(([x, y], i) => (
          <rect key={i} x={x - 16} y={y - 16} width={32} height={32} rx={5} fill="#3d4a5c" stroke="#9fb4cf" strokeWidth={3} />
        ))}
        <text x={540} y={1395} textAnchor="middle" fontFamily={F.body} fontSize={34} fill="#f3e9d7">galga: 3 topes</text>
      </g>
    </svg>
  );
};

export const CheckList: React.FC = () => {
  const f = useCurrentFrame();
  const rows = [`Cuerda ${fmt(cur.chord)} mm`, `Flecha ${fmt(cur.sag)} mm`, 'Plana: apoyada no cojea'];
  return (
    <svg width={1080} height={1920} style={{ position: 'absolute', inset: 0 }}>
      {rows.map((r, i) => {
        const t = prog(f, 78 + i * 16, 92 + i * 16);
        return (
          <g key={i} opacity={t} transform={`translate(${(1 - t) * 30} 0)`}>
            <Check x={112} y={1500 + i * 70} t={t} />
            <text x={152} y={1514 + i * 70} fontFamily={F.body} fontWeight={600} fontSize={44} fill={C.ink}>{r}</text>
          </g>
        );
      })}
    </svg>
  );
};

/* ---------------- 9 · Repetir y armar ---------------- */
export const S9Assemble: React.FC = () => {
  const f = useCurrentFrame();
  const build = interpolate(f, [6, 118], [0, DESIGN.rods.length], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.quad) });
  const curvas = Math.max(0, Math.min(DESIGN.nCur, Math.round(build) - DESIGN.nMer));
  const v: LampView = { az: lerp(-70, -25, f / 180), el: lerp(-22, -28, f / 180), dist: 3900, target: [0, 0, 440], build };
  const end = prog(f, 118, 136);
  return (
    <>
      <Lamp3D v={v} />
      <div style={{ position: 'absolute', top: 190, left: 80, right: 80, opacity: 1 - end }}>
        <div style={{ fontFamily: F.display, fontWeight: 700, fontSize: 230, lineHeight: 0.9, color: C.hl }}>×{curvas}</div>
        <div style={{ fontFamily: F.body, fontWeight: 500, fontSize: 50, lineHeight: 1.25, color: C.ink, marginTop: 10 }}>Repite la misma curva {DESIGN.nCur} veces y arma la lámpara.</div>
      </div>
      <div style={{ position: 'absolute', top: 200, left: 80, right: 80, opacity: end, transform: `translateY(${(1 - end) * 24}px)` }}>
        <div style={{ fontFamily: F.mono, fontSize: 30, letterSpacing: '0.12em', color: C.brass }}>DISEÑADOR ROSETA</div>
        <div style={{ fontFamily: F.display, fontWeight: 700, fontSize: 132, lineHeight: 0.92, color: C.ink, textTransform: 'uppercase', marginTop: 14 }}>Una pieza,<br />48 veces</div>
        <div style={{ fontFamily: F.mono, fontSize: 36, color: C.ink, marginTop: 26 }}>R {fmt(cur.R)} · {fmt(deg(cur.Th))}° · varilla Ø6</div>
        <div style={{ fontFamily: F.body, fontSize: 40, color: C.muted, marginTop: 14, lineHeight: 1.3 }}>Plantilla 1:1, medidas y pasos en el Diseñador Roseta.</div>
      </div>
    </>
  );
};
