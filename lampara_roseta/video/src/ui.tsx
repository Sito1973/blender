import React from 'react';
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from 'remotion';

// Paleta y tipografía del Diseñador Roseta (tema oscuro del visor)
export const C = {
  bg: '#0e1013',
  bg2: '#1a1d22',
  ink: '#ece6da',
  muted: '#a29d94',
  line: 'rgba(236,230,218,0.16)',
  brass: '#dcab58',
  rod: '#d0ac72',
  rodDark: '#9c7a46',
  hl: '#ff8a4f',
  cota: '#ff7366',
  eje: '#74aaec',
  ok: '#72cf8f',
  board: '#7a5a39',
  boardEdge: '#9b7650',
  form: '#4f3a24',
  pencil: '#3a2a19',
};
export const F = {
  display: '"Barlow Condensed", "Arial Narrow", sans-serif',
  body: 'Barlow, "Segoe UI", sans-serif',
  mono: '"IBM Plex Mono", monospace',
};

export const W = 1080;
export const H = 1920;

const EASE = Easing.bezier(0.45, 0, 0.2, 1);
export const prog = (f: number, a: number, b: number, easing = EASE) =>
  interpolate(f, [a, b], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing });
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

export const Background: React.FC = () => (
  <AbsoluteFill style={{ background: `radial-gradient(120% 80% at 50% 45%, ${C.bg2} 0%, ${C.bg} 70%)` }} />
);

// Escena con entrada y salida suaves
export const Scene: React.FC<{ dur: number; fadeIn?: number; fadeOut?: number; children: React.ReactNode }> = ({ dur, fadeIn = 10, fadeOut = 10, children }) => {
  const f = useCurrentFrame();
  const a = fadeIn ? prog(f, 0, fadeIn) : 1;
  const b = fadeOut ? 1 - prog(f, dur - fadeOut, dur) : 1;
  return <AbsoluteFill style={{ opacity: Math.min(a, b) }}>{children}</AbsoluteFill>;
};

// Texto que entra subiendo y sale desvaneciéndose
export const Reveal: React.FC<{ from: number; to?: number; style?: React.CSSProperties; children: React.ReactNode; rise?: number }> = ({ from, to, style, children, rise = 26 }) => {
  const f = useCurrentFrame();
  const inn = prog(f, from, from + 14);
  const out = to === undefined ? 0 : prog(f, to - 10, to);
  return (
    <div style={{ position: 'absolute', opacity: inn * (1 - out), transform: `translateY(${(1 - inn) * rise}px)`, ...style }}>
      {children}
    </div>
  );
};

export const StepHeader: React.FC<{ n: number; title: string; caption: string; caption2?: string; c2From?: number }> = ({ n, title, caption, caption2, c2From = 60 }) => {
  const f = useCurrentFrame();
  const pop = prog(f, 0, 16, Easing.out(Easing.back(1.6)));
  return (
    <>
      <div style={{ position: 'absolute', top: 150, left: 80, right: 80, display: 'flex', alignItems: 'center', gap: 30 }}>
        <div style={{
          width: 128, height: 128, flex: 'none', borderRadius: 64, border: `6px solid ${C.brass}`, color: C.brass,
          fontFamily: F.display, fontWeight: 700, fontSize: 88, display: 'flex', alignItems: 'center', justifyContent: 'center',
          transform: `scale(${0.6 + 0.4 * pop})`, opacity: pop,
        }}>{n}</div>
        <div style={{ fontFamily: F.display, fontWeight: 700, fontSize: title.length > 12 ? 86 : 104, lineHeight: 0.95, color: C.ink, textTransform: 'uppercase', letterSpacing: '0.02em', opacity: prog(f, 4, 18), transform: `translateX(${(1 - prog(f, 4, 18)) * 30}px)` }}>{title}</div>
      </div>
      <Reveal from={10} style={{ top: 330, left: 80, right: 80, fontFamily: F.body, fontWeight: 500, fontSize: 50, lineHeight: 1.22, color: C.ink }}>{caption}</Reveal>
      {caption2 ? <Reveal from={c2From} style={{ top: 470, left: 80, right: 80, fontFamily: F.body, fontWeight: 400, fontSize: 42, lineHeight: 1.25, color: C.muted }}>{caption2}</Reveal> : null}
    </>
  );
};

const STEPS = ['Cortar', 'Trazar', 'Horma', 'Doblar', 'Revisar'];
export const StepsBar: React.FC<{ current: number }> = ({ current }) => (
  <div style={{ position: 'absolute', left: 60, right: 60, bottom: 110, display: 'flex', gap: 12 }}>
    {STEPS.map((s, i) => {
      const on = i + 1 === current, done = i + 1 < current;
      return (
        <div key={s} style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'center' }}>
          <div style={{ height: 8, width: '100%', borderRadius: 4, background: on ? C.brass : done ? 'rgba(220,171,88,0.45)' : C.line }} />
          <div style={{ fontFamily: F.mono, fontSize: 25, color: on ? C.brass : C.muted, fontWeight: on ? 600 : 400 }}>{i + 1} {s}</div>
        </div>
      );
    })}
  </div>
);

export const Check: React.FC<{ x: number; y: number; size?: number; t: number; color?: string }> = ({ x, y, size = 46, t, color = C.ok }) => (
  <g transform={`translate(${x} ${y}) scale(${size / 46})`} opacity={t}>
    <circle cx={0} cy={0} r={23} fill={color} />
    <path d="M-11 0 L-3 8 L12 -9" fill="none" stroke={C.bg} strokeWidth={6} strokeLinecap="round" strokeLinejoin="round" pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - t} />
  </g>
);
