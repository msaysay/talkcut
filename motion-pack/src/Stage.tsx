import React from "react";
import {OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig} from "remotion";
import type {FaceBox, LayoutSegment, Theme} from "./types";

type Margins = {douyinBottom: number; douyinRight: number; maskMinBottomPx: number; pipPx: number};

const DEFAULT_MARGINS: Margins = {douyinBottom: 0.14, douyinRight: 0.12, maskMinBottomPx: 140, pipPx: 380};

export const marginsOf = (theme: Theme): Margins => ({...DEFAULT_MARGINS, ...theme.platformMargins});

const VideoFill: React.FC<{file: string; radius?: number}> = ({file, radius = 0}) => (
  <OffthreadVideo
    src={staticFile(file)}
    style={{width: "100%", height: "100%", objectFit: "cover", borderRadius: radius}}
  />
);

const Card: React.FC<{title: string; body: string; theme: Theme; note?: string}> = ({title, body, theme, note}) => (
  <div style={{color: theme.colors.ink, padding: "6% 7%"}}>
    <div style={{fontFamily: "TC Cover, TC Hook, TC Body, TC Fallback, sans-serif", fontSize: "0.9em", letterSpacing: 2, color: theme.colors.accent}}>
      {title}
    </div>
    {body ? (
      <div style={{fontFamily: "TC Hook, TC Body, TC Fallback, sans-serif", fontSize: "1.7em", fontWeight: 700, lineHeight: 1.25, marginTop: "0.35em"}}>
        {body}
      </div>
    ) : null}
    {note ? (
      <div style={{fontFamily: "TC Note, TC Fallback, sans-serif", fontSize: "1.05em", marginTop: "0.8em", color: theme.colors.accent}}>
        {note}
      </div>
    ) : null}
  </div>
);

const lerp = (from: number, to: number, amount: number) => from + (to - from) * amount;

export const Stage: React.FC<{
  videoFile: string;
  personFile?: string | null;
  personFrom?: number;
  segment: LayoutSegment | null;
  theme: Theme;
  fontSize: number;
}> = ({videoFile, personFile, personFrom = 0, segment, theme, fontSize}) => {
  const {width, height, fps} = useVideoConfig();
  const frame = useCurrentFrame();
  const time = frame / fps;
  const margins = marginsOf(theme);
  const layout = segment?.layout ?? "full";
  const progress = segment ? Math.min(1, Math.max(0, (time - segment.start) / Math.max(0.01, segment.end - segment.start))) : 1;
  const face = segment?.face ?? null;
  const graphic = (
    <Card title={segment?.title ?? ""} body={segment?.body ?? ""} theme={theme} note={layout === "v2" ? "先看这点" : undefined} />
  );

  if (layout === "v2") {
    const size = Math.min(width, height) * 0.28;
    return (
      <div style={{fontSize}}>
        <div style={{position: "absolute", inset: 0, background: "#14181c"}}>{graphic}</div>
        <div style={{position: "absolute", left: width * 0.06, top: height * 0.08, width: size, height: size, borderRadius: size, overflow: "hidden", border: `4px solid ${theme.colors.ink}`}}>
          <VideoFill file={videoFile} />
        </div>
      </div>
    );
  }

  if (layout === "v3") {
    const amount = interpolate(progress, [0, 0.55], [0, 1], {extrapolateLeft: "clamp", extrapolateRight: "clamp"});
    const boxW = width * 0.42;
    const boxH = height * 0.28;
    const minBottom = Math.max(margins.maskMinBottomPx, margins.douyinBottom * height);
    const endLeft = width - margins.douyinRight * width - boxW;
    const endTop = height - minBottom - boxH;
    const left = lerp(0, endLeft, amount);
    const top = lerp(0, endTop, amount);
    const boxWidth = lerp(width, boxW, amount);
    const boxHeight = lerp(height, boxH, amount);
    const radius = lerp(0, Math.min(boxW, boxH) * 0.18, amount);
    return (
      <div style={{fontSize}}>
        <div style={{position: "absolute", inset: 0, background: "#101114"}}>{graphic}</div>
        <div style={{position: "absolute", left, top, width: boxWidth, height: boxHeight, borderRadius: radius, overflow: "hidden"}}>
          <VideoFill file={videoFile} />
        </div>
      </div>
    );
  }

  if (layout === "v4") {
    return (
      <div style={{fontSize}}>
        <div style={{position: "absolute", left: 0, right: 0, top: 0, height: height * 0.46, background: "#14181c"}}>{graphic}</div>
        <div style={{position: "absolute", left: 0, right: 0, top: height * 0.46, bottom: 0}}>
          <VideoFill file={videoFile} />
        </div>
      </div>
    );
  }

  if (layout === "v5") {
    const from = Math.round(personFrom * fps);
    return (
      <div style={{fontSize}}>
        <div style={{position: "absolute", inset: 0, background: "#1a140c", display: "flex", alignItems: "center", justifyContent: "center", padding: "12%"}}>
          <div style={{fontFamily: "TC Gold, TC Fallback, serif", fontSize: "2.4em", fontWeight: 700, textAlign: "center", color: theme.colors.ink, lineHeight: 1.2}}>
            {segment?.caption}
          </div>
        </div>
        {personFile ? (
          <>
            <OffthreadVideo src={staticFile(videoFile)} style={{position: "absolute", width: 1, height: 1, opacity: 0}} />
            <Sequence from={from} durationInFrames={Math.max(1, Math.round(((segment?.end ?? 1) - (segment?.start ?? 0)) * fps))}>
              <OffthreadVideo muted src={staticFile(personFile)} style={{width: "100%", height: "100%", objectFit: "cover"}} />
            </Sequence>
          </>
        ) : (
          <VideoFill file={videoFile} />
        )}
      </div>
    );
  }

  if (layout === "v6") {
    const band = height * 0.34;
    const top = height * 0.3;
    return (
      <div style={{fontSize}}>
        <div style={{position: "absolute", inset: 0, background: "#101114"}}>{graphic}</div>
        <div style={{position: "absolute", left: width * 0.04, right: width * margins.douyinRight, top, height: band, overflow: "hidden", borderRadius: 18}}>
          <VideoFill file={videoFile} />
        </div>
      </div>
    );
  }

  if (layout === "h1" || layout === "h2") {
    const column = layout === "h1" ? width / 3 : width * 0.38;
    return (
      <div style={{fontSize}}>
        <div style={{position: "absolute", left: 0, top: 0, bottom: 0, width: column}}>
          <VideoFill file={videoFile} />
        </div>
        <div style={{position: "absolute", left: column, top: 0, right: 0, bottom: margins.douyinBottom * height, background: "#14181c"}}>
          {graphic}
        </div>
      </div>
    );
  }

  if (layout === "h3") {
    const pip = margins.pipPx * (width / 1920);
    return (
      <div style={{fontSize}}>
        <div style={{position: "absolute", inset: 0, background: "#14181c"}}>{graphic}</div>
        <div
          style={{
            position: "absolute",
            width: pip,
            height: pip * 0.72,
            right: margins.douyinRight * width,
            bottom: Math.max(margins.maskMinBottomPx, margins.douyinBottom * height),
            borderRadius: 24,
            overflow: "hidden",
            border: `3px solid ${theme.colors.ink}`,
          }}
        >
          <VideoFill file={videoFile} />
        </div>
      </div>
    );
  }

  if (layout === "h5") {
    const scale = interpolate(progress, [0, 1], [1, 1.12], {extrapolateRight: "clamp"});
    const origin = faceOrigin(face);
    return (
      <div style={{position: "absolute", inset: 0, transform: `scale(${scale})`, transformOrigin: origin}}>
        <VideoFill file={videoFile} />
      </div>
    );
  }

  const titleTop = face ? Math.max(0.03, face.y - 0.11) * height : height * 0.04;
  return (
    <div style={{position: "absolute", inset: 0}}>
      <VideoFill file={videoFile} />
      {layout === "v1" && segment?.title ? (
        <div
          style={{
            position: "absolute",
            left: width * 0.06,
            right: width * margins.douyinRight,
            top: titleTop,
            padding: "14px 18px",
            background: theme.colors.pill,
            color: theme.colors.ink,
            fontFamily: "TC Cover, TC Hook, TC Fallback, sans-serif",
            fontSize: fontSize * 1.15,
          }}
        >
          {segment.title}
        </div>
      ) : null}
    </div>
  );
};

const faceOrigin = (face: FaceBox | null) => {
  if (!face) return "50% 40%";
  return `${(face.x + face.w / 2) * 100}% ${(face.y + face.h / 2) * 100}%`;
};
