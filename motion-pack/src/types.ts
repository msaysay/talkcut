export type Emphasis = "hook" | "body" | "number" | "gold" | "cta" | "list";

export type Caption = {
  text: string;
  start: number;
  end: number;
  emphasis: Emphasis;
  keywords: string[];
};

export type FaceBox = {x: number; y: number; w: number; h: number};

export type LayoutSegment = {
  layout: string;
  start: number;
  end: number;
  title: string;
  body: string;
  caption: string;
  captionAnchor: "top" | "middle" | "bottom";
  face: FaceBox | null;
};

export type Theme = {
  id: string;
  compositionId: string;
  coverCompositionId?: string;
  name: string;
  motion: "fade" | "beat-punch";
  fps: number;
  width: number;
  height: number;
  colors: {
    ink: string;
    accent: string;
    pill: string;
    stroke: string;
    badge: string;
  };
  caption: {
    bottom: number;
    side: number;
    bodySize: number;
    hookSize: number;
    numberSize: number;
    goldSize: number;
    ctaSize: number;
    listSize: number;
  };
  music: {
    speechVolume: number;
    gapVolume: number;
    ctaVolume: number;
  };
  maxColors: number;
  frames?: {vertical: {width: number; height: number}; landscape: {width: number; height: number}};
  platformMargins?: {douyinBottom: number; douyinRight: number; maskMinBottomPx: number; pipPx: number};
  fontRoles?: Record<string, string>;
};

export type MotionProps = {
  durationInFrames: number;
  fps: number;
  width?: number;
  height?: number;
  orientation?: "vertical" | "landscape";
  videoFile: string;
  musicFile: string | null;
  fontFile: string;
  fontFiles?: Record<string, string>;
  captions: Caption[];
  beats: number[];
  nameplate: {text: string; start: number; end: number} | null;
  theme: Theme;
  title: string;
  segments?: LayoutSegment[];
  personFile?: string | null;
  personFrom?: number;
};
