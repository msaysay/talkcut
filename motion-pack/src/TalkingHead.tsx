import React from "react";
import {AbsoluteFill, Audio, staticFile, useCurrentFrame, useVideoConfig} from "remotion";
import {CaptionLayer} from "./CaptionLayer";
import {Stage} from "./Stage";
import type {MotionProps} from "./types";

export const musicVolumeAt = (time: number, props: MotionProps): number => {
  const theme = props.theme.music;
  const active = props.captions.find((caption) => time >= caption.start && time < caption.end);
  if (!active) return theme.gapVolume;
  if (active.emphasis === "cta") return theme.ctaVolume;
  return theme.speechVolume;
};

const fontFace = (family: string, file: string | undefined) =>
  file ? `@font-face { font-family: "${family}"; src: url("${staticFile(file)}") format("truetype"); }` : "";

export const TalkingHead: React.FC<MotionProps> = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const time = frame / (props.fps || fps);
  const theme = props.theme;
  const files = props.fontFiles ?? {};
  const nearestBeat = props.beats.reduce(
    (best, beat) => (Math.abs(beat - time) < Math.abs(best - time) ? beat : best),
    props.beats[0] ?? -10,
  );
  const beatDistance = Math.abs(time - nearestBeat);
  const segment = (props.segments ?? []).find((item) => time >= item.start && time < item.end) ?? null;
  const layout = segment?.layout ?? (props.orientation === "landscape" ? "h4" : "full");
  const nameplate = props.nameplate && time >= props.nameplate.start && time < props.nameplate.end ? props.nameplate : null;
  const fontCss = [
    fontFace("TC Body", files.body),
    fontFace("TC Hook", files.hook),
    fontFace("TC Cover", files.cover),
    fontFace("TC Gold", files.gold),
    fontFace("TC Number", files.number),
    fontFace("TC Note", files.note),
    fontFace("TC Fallback", files.fallback ?? props.fontFile),
  ].join("\n");

  return (
    <AbsoluteFill style={{backgroundColor: "#101114", fontFamily: "TC Body, TC Fallback, sans-serif"}}>
      <style>{fontCss}</style>
      <Stage
        videoFile={props.videoFile}
        personFile={props.personFile}
        personFrom={props.personFrom}
        segment={segment}
        theme={theme}
        fontSize={props.orientation === "landscape" ? 28 : 36}
      />
      {props.musicFile ? <Audio src={staticFile(props.musicFile)} volume={(f) => musicVolumeAt(f / (props.fps || fps), props)} /> : null}
      {theme.motion === "beat-punch" && beatDistance < 0.1 ? (
        <div style={{position: "absolute", top: 0, left: 0, right: 0, height: 14, background: theme.colors.accent, opacity: 1 - beatDistance / 0.1}} />
      ) : null}
      {nameplate ? (
        <div
          style={{
            position: "absolute",
            left: "6%",
            top: "46%",
            maxWidth: "36%",
            padding: "12px 18px",
            borderRadius: 12,
            background: theme.colors.pill,
            color: theme.colors.ink,
            fontFamily: "TC Body, TC Fallback, sans-serif",
            fontSize: 28,
          }}
        >
          {nameplate.text}
        </div>
      ) : null}
      <CaptionLayer props={props} layout={layout} />
    </AbsoluteFill>
  );
};
