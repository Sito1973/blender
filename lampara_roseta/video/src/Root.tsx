import React from 'react';
import { Composition, staticFile } from 'remotion';
import { loadFont } from '@remotion/fonts';
import { DURATION, FPS, Video } from './Video';

const FONTS: [string, string, string][] = [
  ['Barlow Condensed', 'BarlowCondensed-500.woff2', '500'],
  ['Barlow Condensed', 'BarlowCondensed-600.woff2', '600'],
  ['Barlow Condensed', 'BarlowCondensed-700.woff2', '700'],
  ['Barlow', 'Barlow-400.woff2', '400'],
  ['Barlow', 'Barlow-500.woff2', '500'],
  ['Barlow', 'Barlow-600.woff2', '600'],
  ['Barlow', 'Barlow-700.woff2', '700'],
  ['IBM Plex Mono', 'IBMPlexMono-400.woff2', '400'],
  ['IBM Plex Mono', 'IBMPlexMono-500.woff2', '500'],
  ['IBM Plex Mono', 'IBMPlexMono-600.woff2', '600'],
];
FONTS.forEach(([family, file, weight]) => loadFont({ family, url: staticFile(`fonts/${file}`), weight, format: 'woff2' }));

export const RemotionRoot: React.FC = () => (
  <Composition id="VarillaRoseta" component={Video} durationInFrames={DURATION} fps={FPS} width={1080} height={1920} />
);
