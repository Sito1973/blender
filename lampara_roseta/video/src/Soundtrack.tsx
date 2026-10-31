import React from 'react';
import { Audio, Sequence, interpolate, staticFile } from 'remotion';
import audio from '../public/audio/audio.json';
import { T_DOBLAR, T_HORMA, T_REV } from './scenes';

const FPS = 30;
const WS = 810; // inicio del taller (pasos 2 a 5)

// Volumen con entrada y salida cortas para evitar chasquidos
const env = (v: number, dur: number) => (f: number) =>
  interpolate(f, [0, 3, Math.max(4, dur - 6), dur], [0, v, v, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

type Fx = { file: string; at: number; vol: number; dur?: number };
const len = (file: string) => Math.ceil((audio.efectos.find((e) => e.archivo === `audio/${file}.mp3`)?.duracion ?? 1) * FPS);

const FX: Fx[] = [
  { file: 'sfx_whoosh', at: 150 + 58, vol: 0.5 },                 // la varilla sale del domo
  { file: 'sfx_cortes', at: 630 + 38, vol: 0.28 },                // paso 1: cortes
  { file: 'sfx_lapiz', at: WS + 30, vol: 0.32 },                  // paso 2: trazar con cordel
  { file: 'sfx_check', at: WS + 152, vol: 0.45 },                 // cuerda comprobada
  { file: 'sfx_sierra', at: WS + T_HORMA + 24, vol: 0.3 },        // paso 3: cortar la horma
  { file: 'sfx_doblar', at: WS + T_DOBLAR + 28, vol: 0.38 },      // paso 4: doblar
  { file: 'sfx_soltar', at: WS + T_DOBLAR + 136, vol: 0.5 },      // soltar la prensa
  { file: 'sfx_check', at: WS + T_DOBLAR + 168, vol: 0.45 },      // coincide con el trazo
  { file: 'sfx_cortes', at: WS + T_REV + 26, vol: 0.28, dur: 32 },// paso 5: recortar puntas
  { file: 'sfx_check', at: WS + T_REV + 80, vol: 0.4 },           // cuerda
  { file: 'sfx_check', at: WS + T_REV + 96, vol: 0.4 },           // flecha
  { file: 'sfx_check', at: WS + T_REV + 112, vol: 0.4 },          // plana
  { file: 'sfx_armar', at: 1620 + 6, vol: 0.38 },                 // armar la lámpara
];

export const Soundtrack: React.FC = () => (
  <>
    {audio.voz.map((v) => {
      const from = Math.round(v.inicio * FPS), dur = Math.ceil(v.duracion * FPS) + 4;
      return (
        <Sequence key={v.archivo} from={from} durationInFrames={dur} layout="none">
          <Audio src={staticFile(v.archivo)} volume={env(1, dur)} />
        </Sequence>
      );
    })}
    {FX.map((fx, i) => {
      const dur = fx.dur ?? len(fx.file);
      return (
        <Sequence key={i} from={fx.at} durationInFrames={dur} layout="none">
          <Audio src={staticFile(`audio/${fx.file}.mp3`)} volume={env(fx.vol, dur)} />
        </Sequence>
      );
    })}
  </>
);
