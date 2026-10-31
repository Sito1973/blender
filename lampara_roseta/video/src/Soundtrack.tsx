import React from 'react';
import { Audio, Sequence, interpolate, staticFile } from 'remotion';
import audio from '../public/audio/audio.json';
import { T_DOBLAR, T_HORMA, T_REV } from './scenes';

const FPS = 30;
const WS = 810; // inicio del taller (pasos 2 a 5)

// Tramos (en frames) donde habla la voz: ahí los efectos bajan para que se entienda.
const VOICE = audio.voz.map((v) => [Math.round(v.inicio * FPS) - 4, Math.round((v.inicio + v.duracion) * FPS) + 4]);
const DUCK = 0.5;
const duck = (g: number) => (VOICE.some(([a, b]) => g >= a && g <= b) ? DUCK : 1);

// Entrada y salida cortas para evitar chasquidos
const env = (f: number, dur: number, fade = 3) =>
  interpolate(f, [0, fade, Math.max(fade + 1, dur - 6), dur], [0, 1, 1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

const len = (file: string) => Math.ceil((audio.efectos.find((e) => e.archivo === `audio/${file}.mp3`)?.duracion ?? 1) * FPS);

type Fx = { file: string; at: number; vol: number; dur?: number };
const FX: Fx[] = [
  // apertura y la pieza
  { file: 'sfx_intro', at: 0, vol: 0.6 },
  { file: 'sfx_trans', at: 146, vol: 0.75 },
  { file: 'sfx_brillo', at: 164, vol: 0.5 },                   // la varilla se ilumina
  { file: 'sfx_whoosh', at: 208, vol: 1.0 },                   // sale del domo y se acuesta
  // medidas: un pop por cada cota
  ...[410, 432, 460, 486, 520].map((at) => ({ file: 'sfx_pop', at, vol: 0.32 })),
  // paso 1: cortar
  { file: 'sfx_trans', at: 626, vol: 0.75 },
  { file: 'sfx_golpe', at: 632, vol: 1.0 },
  { file: 'sfx_cortes', at: 668, vol: 0.63 },
  // paso 2: trazar
  { file: 'sfx_trans', at: 806, vol: 0.75 },
  { file: 'sfx_golpe', at: WS + 2, vol: 1.0 },
  { file: 'sfx_clavo', at: WS + 18, vol: 1.0 },
  { file: 'sfx_lapiz', at: WS + 30, vol: 1.0 },
  { file: 'sfx_check', at: WS + 152, vol: 0.8 },
  // paso 3: horma
  { file: 'sfx_golpe', at: WS + T_HORMA + 2, vol: 1.0 },
  { file: 'sfx_sierra', at: WS + T_HORMA + 24, vol: 0.63 },
  { file: 'sfx_tornillo', at: WS + T_HORMA + 110, vol: 0.56 },
  // paso 4: doblar
  { file: 'sfx_golpe', at: WS + T_DOBLAR + 2, vol: 1.0 },
  { file: 'sfx_doblar', at: WS + T_DOBLAR + 28, vol: 1.0 },
  { file: 'sfx_soltar', at: WS + T_DOBLAR + 136, vol: 1.0 },
  { file: 'sfx_check', at: WS + T_DOBLAR + 168, vol: 0.8 },
  // paso 5: recortar y revisar
  { file: 'sfx_golpe', at: WS + T_REV + 2, vol: 1.0 },
  { file: 'sfx_cortes', at: WS + T_REV + 26, vol: 0.63, dur: 32 },
  ...[80, 96, 112].map((d) => ({ file: 'sfx_check', at: WS + T_REV + d, vol: 0.8 })),
  // armar y cierre
  { file: 'sfx_trans', at: 1616, vol: 0.75 },
  { file: 'sfx_armar', at: 1626, vol: 1.0 },
  { file: 'sfx_contador', at: 1628, vol: 0.6 },
  { file: 'sfx_final', at: 1736, vol: 0.9 },
];

const AMB_FROM = 140, AMB_TO = 1800, AMB_VOL = 0.08;

export const Soundtrack: React.FC = () => (
  <>
    {audio.voz.map((v) => {
      const from = Math.round(v.inicio * FPS), dur = Math.ceil(v.duracion * FPS) + 4;
      return (
        <Sequence key={v.archivo} from={from} durationInFrames={dur} layout="none">
          <Audio src={staticFile(v.archivo)} volume={(f) => env(f, dur)} />
        </Sequence>
      );
    })}
    {FX.map((fx, i) => {
      const dur = fx.dur ?? len(fx.file);
      return (
        <Sequence key={i} from={fx.at} durationInFrames={dur} layout="none">
          <Audio src={staticFile(`audio/${fx.file}.mp3`)} volume={(f) => fx.vol * env(f, dur) * duck(fx.at + f)} />
        </Sequence>
      );
    })}
    {/* ambiente de taller en bucle, muy bajo, para que no queden silencios muertos */}
    <Sequence from={AMB_FROM} durationInFrames={AMB_TO - AMB_FROM} layout="none">
      <Audio src={staticFile('audio/sfx_ambiente.mp3')} loop volume={(f) => AMB_VOL * env(f, AMB_TO - AMB_FROM, 30) * (duck(AMB_FROM + f) === 1 ? 1 : 0.7)} />
    </Sequence>
  </>
);
