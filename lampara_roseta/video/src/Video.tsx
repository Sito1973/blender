import React from 'react';
import { AbsoluteFill, Sequence, useCurrentFrame } from 'remotion';
import { SHOP, fmt, DESIGN } from './geometry';
import { CheckList, S1Title, S2OnePiece, S3Measures, S4Cut, S9Assemble, T_DOBLAR, T_END, T_HORMA, T_REV, Workshop } from './scenes';
import { Background, C, Scene, StepHeader, StepsBar } from './ui';
import { Soundtrack } from './Soundtrack';

export const FPS = 30;
export const DURATION = 1800;

const WS = 810; // inicio del taller (pasos 2 a 5)

const StepsBarAnim: React.FC = () => {
  const f = useCurrentFrame();
  const step = f < 180 ? 1 : f < 180 + T_HORMA ? 2 : f < 180 + T_DOBLAR ? 3 : f < 180 + T_REV ? 4 : 5;
  return <StepsBar current={step} />;
};

export const Video: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: C.bg }}>
    <Background />
    <Sequence from={0} durationInFrames={150}><Scene dur={150} fadeIn={8} fadeOut={12}><S1Title /></Scene></Sequence>
    <Sequence from={150} durationInFrames={240}><Scene dur={240} fadeIn={12} fadeOut={0}><S2OnePiece /></Scene></Sequence>
    <Sequence from={390} durationInFrames={240}><Scene dur={240} fadeIn={0} fadeOut={12}><S3Measures /></Scene></Sequence>
    <Sequence from={630} durationInFrames={180}><Scene dur={180} fadeIn={12} fadeOut={12}><S4Cut /></Scene></Sequence>
    <Sequence from={WS} durationInFrames={T_END}><Scene dur={T_END} fadeIn={0} fadeOut={14}><Workshop /></Scene></Sequence>
    <Sequence from={WS + T_TRAZ_START} durationInFrames={T_HORMA}>
      <Scene dur={T_HORMA}><StepHeader n={2} title="Trazar el arco" caption={`Clavo en el centro y cordel de ${fmt(DESIGN.cur.R)} mm.`} caption2="La punta del lápiz dibuja el eje de la varilla." c2From={40} /></Scene>
    </Sequence>
    <Sequence from={WS + T_HORMA} durationInFrames={T_DOBLAR - T_HORMA}>
      <Scene dur={T_DOBLAR - T_HORMA}><StepHeader n={3} title="Hacer la horma" caption={`Corta un arco de ${fmt(SHOP.form, 0)} mm de radio.`} caption2="Más cerrado que la pieza: el acero se abre un poco al soltarlo." c2From={120} /></Scene>
    </Sequence>
    <Sequence from={WS + T_DOBLAR} durationInFrames={T_REV - T_DOBLAR}>
      <Scene dur={T_REV - T_DOBLAR}><StepHeader n={4} title="Doblar" caption="Prensa la punta y dobla de a poco contra la horma." caption2="Al soltarla, se abre justo hasta el trazo." c2From={140} /></Scene>
    </Sequence>
    <Sequence from={WS + T_REV} durationInFrames={T_END - T_REV}>
      <Scene dur={T_END - T_REV} fadeOut={14}><StepHeader n={5} title="Recortar y revisar" caption="Corta las puntas sobrantes sobre las marcas." caption2="Una galga con 3 topes revisa cada pieza." c2From={62} /></Scene>
    </Sequence>
    <Sequence from={WS + T_REV} durationInFrames={T_END - T_REV}><Scene dur={T_END - T_REV} fadeIn={0} fadeOut={14}><CheckList /></Scene></Sequence>
    <Sequence from={630} durationInFrames={990}><Scene dur={990} fadeIn={12} fadeOut={14}><StepsBarAnim /></Scene></Sequence>
    <Sequence from={1620} durationInFrames={180}><Scene dur={180} fadeIn={14} fadeOut={10}><S9Assemble /></Scene></Sequence>
    <Soundtrack />
  </AbsoluteFill>
);

const T_TRAZ_START = 0;
