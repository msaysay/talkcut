import React from "react";
import {Composition} from "remotion";
import {CoverStill} from "../presets/cover/Cover";
import {CleanKnowledge} from "../presets/clean-knowledge/Captions";
import {GoldLine} from "../presets/gold-line/Captions";
import {OpusClean} from "../presets/opus-clean/Captions";
import {OpusPunch} from "../presets/opus-punch/Captions";
import {CardKnowledge} from "../presets/card-knowledge/Captions";
import {EvaMorphV} from "../presets/eva-morph-v/Captions";
import opusClean from "../presets/opus-clean/preset.json";
import opusPunch from "../presets/opus-punch/preset.json";
import cardKnowledge from "../presets/card-knowledge/preset.json";
import evaMorph from "../presets/eva-morph-v/preset.json";
import type {MotionProps} from "./types";
import clean from "../presets/clean-knowledge/preset.json";

const fallback: MotionProps = {
  durationInFrames: 90,
  fps: 30,
  videoFile: "video.mp4",
  musicFile: null,
  fontFile: "fonts/cjk.ttf",
  captions: [{text: "先把三秒说清", start: 0, end: 2.4, emphasis: "hook", keywords: ["三"]}],
  beats: [0, 0.6, 1.2],
  nameplate: null,
  theme: clean as MotionProps["theme"],
  title: "先把三秒说清",
};

const duration = ({props}: {props: MotionProps}) => ({
  durationInFrames: Math.max(1, Math.round(props.durationInFrames)),
  width: props.width || props.theme.width || 1080,
  height: props.height || props.theme.height || 1920,
  fps: props.fps || 30,
});

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="clean-knowledge"
        component={CleanKnowledge}
        durationInFrames={90}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={fallback}
        calculateMetadata={duration}
      />
      <Composition
        id="gold-line"
        component={GoldLine}
        durationInFrames={90}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={fallback}
        calculateMetadata={duration}
      />
      <Composition
        id="opus-clean"
        component={OpusClean}
        durationInFrames={90}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{...fallback, theme: opusClean as MotionProps["theme"]}}
        calculateMetadata={duration}
      />
      <Composition
        id="opus-punch"
        component={OpusPunch}
        durationInFrames={90}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{...fallback, theme: opusPunch as MotionProps["theme"]}}
        calculateMetadata={duration}
      />
      <Composition
        id="card-knowledge"
        component={CardKnowledge}
        durationInFrames={90}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{...fallback, theme: cardKnowledge as MotionProps["theme"]}}
        calculateMetadata={duration}
      />
      <Composition
        id="eva-morph-v"
        component={EvaMorphV}
        durationInFrames={90}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{...fallback, theme: evaMorph as MotionProps["theme"]}}
        calculateMetadata={duration}
      />
      <Composition
        id="cover-still"
        component={CoverStill}
        durationInFrames={1}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={fallback}
        calculateMetadata={({props}) => ({
          durationInFrames: 1,
          width: props.width || props.theme.width || 1080,
          height: props.height || props.theme.height || 1920,
        })}
      />
    </>
  );
};
