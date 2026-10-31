export type Emphasis = "hook" | "body" | "number" | "gold" | "cta" | "list";

export type Caption = {
  text: string;
  start: number;
  end: number;
  emphasis: Emphasis;
  keywords: string[];
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
};

export type MotionProps = {
  durationInFrames: number;
  fps: number;
  videoFile: string;
  musicFile: string | null;
  fontFile: string;
  captions: Caption[];
  beats: number[];
  nameplate: {text: string; start: number; end: number} | null;
  theme: Theme;
  title: string;
};
