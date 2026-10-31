import React from "react";
import {AbsoluteFill, Audio, OffthreadVideo, interpolate, staticFile, useCurrentFrame} from "remotion";
import type {Caption, MotionProps, Theme} from "./types";

const sizeFor = (theme: Theme, emphasis: Caption["emphasis"]): number => {
  const box = theme.caption;
  if (emphasis === "hook") return box.hookSize;
  if (emphasis === "number") return box.numberSize;
  if (emphasis === "gold") return box.goldSize;
  if (emphasis === "cta") return box.ctaSize;
  if (emphasis === "list") return box.listSize;
  return box.bodySize;
};

const wrapChars = (text: string, size: number, maxWidth: number): string[] => {
  const perLine = Math.max(6, Math.floor(maxWidth / size));
  const lines: string[] = [];
  for (let index = 0; index < text.length; index += perLine) {
    lines.push(text.slice(index, index + perLine));
  }
  return lines.slice(0, 3);
};

const RichLine: React.FC<{text: string; keywords: string[]; color: string; accent: string}> = ({
  text,
  keywords,
  color,
  accent,
}) => {
  if (keywords.length === 0) {
    return <span style={{color}}>{text}</span>;
  }
  const pattern = new RegExp(`(${keywords.map((item) => item.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "g");
  const parts = text.split(pattern).filter((part) => part.length > 0);
  return (
    <>
      {parts.map((part, index) =>
        keywords.includes(part) ? (
          <span key={`${part}-${index}`} style={{color: accent, fontSize: "1.18em"}}>
            {part}
          </span>
        ) : (
          <span key={`${part}-${index}`} style={{color}}>
            {part}
          </span>
        ),
      )}
    </>
  );
};

export const musicVolumeAt = (time: number, props: MotionProps): number => {
  const theme = props.theme.music;
  const active = props.captions.find((caption) => time >= caption.start && time < caption.end);
  if (!active) return theme.gapVolume;
  if (active.emphasis === "cta") return theme.ctaVolume;
  return theme.speechVolume;
};

const activeCaption = (time: number, captions: Caption[]): Caption | null =>
  captions.find((caption) => time >= caption.start && time < caption.end) ?? null;

export const TalkingHead: React.FC<MotionProps> = (props) => {
  const frame = useCurrentFrame();
  const time = frame / props.fps;
  const theme = props.theme;
  const caption = activeCaption(time, props.captions);
  const local = caption ? frame - Math.round(caption.start * props.fps) : 0;
  const fade = caption ? interpolate(local, [0, 6], [0, 1], {extrapolateRight: "clamp", extrapolateLeft: "clamp"}) : 0;
  const nearestBeat = props.beats.reduce((best, beat) => (Math.abs(beat - time) < Math.abs(best - time) ? beat : best), props.beats[0] ?? -10);
  const beatDistance = Math.abs(time - nearestBeat);
  const punch =
    theme.motion === "beat-punch" && beatDistance < 0.12 ? 1 + (1 - beatDistance / 0.12) * 0.14 : 1;
  const font = `"TalkCut CJK", "Droid Sans Fallback", sans-serif`;
  const nameplate = props.nameplate && time >= props.nameplate.start && time < props.nameplate.end ? props.nameplate : null;

  return (
    <AbsoluteFill style={{backgroundColor: "#101114", fontFamily: font}}>
      <style>
        {`@font-face { font-family: "TalkCut CJK"; src: url("${staticFile(props.fontFile)}") format("truetype"); }`}
      </style>
      {props.videoFile ? (
        <OffthreadVideo
          src={staticFile(props.videoFile)}
          style={{width: "100%", height: "100%", objectFit: "cover"}}
        />
      ) : null}
      {props.musicFile ? <Audio src={staticFile(props.musicFile)} volume={(f) => musicVolumeAt(f / props.fps, props)} /> : null}
      {theme.motion === "beat-punch" && beatDistance < 0.1 ? (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: 18,
            background: theme.colors.accent,
            opacity: 1 - beatDistance / 0.1,
          }}
        />
      ) : null}
      {nameplate ? (
        <div
          style={{
            position: "absolute",
            left: 64,
            top: "46%",
            maxWidth: 420,
            padding: "16px 22px",
            borderRadius: 12,
            background: theme.colors.pill,
            color: theme.colors.ink,
            fontSize: 32,
            lineHeight: 1.25,
          }}
        >
          {nameplate.text}
        </div>
      ) : null}
      {caption ? (
        <div
          style={{
            position: "absolute",
            left: theme.caption.side,
            right: theme.caption.side,
            bottom: theme.caption.bottom,
            opacity: fade,
            transform: `scale(${punch})`,
            transformOrigin: "center bottom",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              alignItems: "flex-end",
              gap: 18,
            }}
          >
            {caption.emphasis === "list" ? (
              <div
                style={{
                  width: 72,
                  height: 72,
                  borderRadius: 36,
                  background: theme.colors.badge,
                  color: "#1a1a1a",
                  fontSize: 36,
                  fontWeight: 700,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {caption.text.slice(0, 1)}
              </div>
            ) : null}
            <div
              style={{
                background: theme.colors.pill,
                borderRadius: 18,
                padding: "22px 28px",
                maxWidth: 920,
                textAlign: "center",
                boxShadow: caption.emphasis === "gold" ? `inset 0 -8px 0 ${theme.colors.accent}` : undefined,
              }}
            >
              {wrapChars(caption.text, sizeFor(theme, caption.emphasis), 860).map((line, lineIndex) => (
                <div
                  key={`${lineIndex}-${line}`}
                  style={{
                    fontSize: sizeFor(theme, caption.emphasis),
                    fontWeight: 700,
                    lineHeight: 1.22,
                    letterSpacing: 1,
                    WebkitTextStroke: `2px ${theme.colors.stroke}`,
                    paintOrder: "stroke fill",
                  }}
                >
                  <RichLine text={line} keywords={caption.keywords} color={theme.colors.ink} accent={theme.colors.accent} />
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
