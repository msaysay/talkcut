import React from "react";
import {interpolate, useCurrentFrame, useVideoConfig} from "remotion";
import type {Caption, MotionProps} from "./types";
import {marginsOf} from "./Stage";

const FONT_STACK: Record<string, string> = {
  hook: "TC Hook, TC Cover, TC Body, TC Fallback, sans-serif",
  cover: "TC Cover, TC Hook, TC Fallback, sans-serif",
  gold: "TC Gold, TC Fallback, serif",
  number: "TC Number, TC Hook, TC Fallback, sans-serif",
  note: "TC Note, TC Fallback, sans-serif",
  body: "TC Body, TC Fallback, sans-serif",
};

const familyFor = (caption: Caption) => {
  if (caption.font && FONT_STACK[caption.font]) return FONT_STACK[caption.font];
  if (caption.emphasis === "gold") return FONT_STACK.gold;
  if (caption.emphasis === "number") return FONT_STACK.number;
  if (caption.emphasis === "hook" || caption.emphasis === "cta") return FONT_STACK.hook;
  return FONT_STACK.body;
};

const sizeFor = (props: MotionProps, emphasis: Caption["emphasis"], scale: number) => {
  const box = props.theme.caption;
  const base =
    emphasis === "hook" ? box.hookSize :
    emphasis === "number" ? box.numberSize :
    emphasis === "gold" ? box.goldSize :
    emphasis === "cta" ? box.ctaSize :
    emphasis === "list" ? box.listSize :
    box.bodySize;
  return Math.round(base * scale);
};

const revealCount = (text: string, local: number, fps: number) => {
  const framesPerChar = Math.max(1, Math.round(fps / 18));
  return Math.min(text.length, Math.floor(local / framesPerChar) + 1);
};

const NumberRoll: React.FC<{value: number; progress: number}> = ({value, progress}) => {
  const shown = Math.round(interpolate(progress, [0, 1], [0, value], {extrapolateRight: "clamp"}));
  return <span style={{fontFamily: "TC Number, sans-serif"}}>{shown}</span>;
};

export const CaptionLayer: React.FC<{props: MotionProps; layout: string}> = ({props, layout}) => {
  const frame = useCurrentFrame();
  const {width, height, fps} = useVideoConfig();
  const time = frame / fps;
  const caption = props.captions.find((item) => time >= item.start && time < item.end);
  if (!caption) return null;
  const local = frame - Math.round(caption.start * fps);
  const fade = interpolate(local, [0, 5], [0, 1], {extrapolateLeft: "clamp", extrapolateRight: "clamp"});
  const scale = height / (width > height ? 1080 : 1920);
  const size = sizeFor(props, caption.emphasis, scale);
  const margins = marginsOf(props.theme);
  const segment = (props.segments ?? []).find((item) => time >= item.start && time < item.end);
  const anchor = segment?.captionAnchor ?? "bottom";
  const bottom = Math.max((props.theme.caption.bottom / 1920) * height, margins.douyinBottom * height);
  const right = margins.douyinRight * width;
  const shown = caption.text.slice(0, revealCount(caption.text, local, fps));
  const effects = caption.effects ?? [];
  const slash = caption.emphasis === "hook" || effects.includes("slash-in") ? interpolate(local, [0, 8], [100, 0], {extrapolateRight: "clamp"}) : 0;
  const highlight = interpolate(local, [4, 12], [0, 1], {extrapolateLeft: "clamp", extrapolateRight: "clamp"});
  const digit = caption.keywords.find((item) => /^\d+$/.test(item));
  const roll = Boolean(digit) && (caption.emphasis === "number" || effects.includes("number-roll"));
  const body = roll && digit ? (
    <>
      {shown.split(digit)[0]}
      <NumberRoll value={Number(digit)} progress={Math.min(1, local / (fps * 0.55))} />
      {shown.includes(digit) ? shown.split(digit).slice(1).join(digit) : ""}
    </>
  ) : (
    shown
  );
  const bar = layout === "h4" || effects.includes("lower-third");
  return (
    <div
      style={{
        position: "absolute",
        left: props.theme.caption.side * (width / 1080),
        right: Math.max(props.theme.caption.side * (width / 1080), right),
        bottom: anchor === "bottom" ? bottom : undefined,
        top: anchor === "middle" ? height * 0.22 : anchor === "top" ? height * 0.08 : undefined,
        opacity: fade,
        display: "flex",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          width: bar ? "100%" : undefined,
          background: props.theme.colors.pill,
          borderRadius: bar ? 0 : 18,
          padding: bar ? "18px 28px" : "18px 26px",
          textAlign: "center",
          clipPath: slash ? `inset(0 ${slash}% 0 0)` : undefined,
          boxShadow: caption.emphasis === "gold" ? `inset 0 -6px 0 ${props.theme.colors.accent}` : undefined,
        }}
      >
        <div
          style={{
            position: "relative",
            fontFamily: familyFor(caption),
            fontSize: size,
            fontWeight: 700,
            lineHeight: 1.2,
            color: props.theme.colors.ink,
            WebkitTextStroke: `2px ${props.theme.colors.stroke}`,
            paintOrder: "stroke fill",
          }}
        >
          {caption.keywords.filter((item) => !/^\d+$/.test(item)).map((word) => (
            <span
              key={word}
              style={{
                position: "absolute",
                left: "8%",
                right: "8%",
                bottom: "0.05em",
                height: "0.38em",
                background: props.theme.colors.accent,
                opacity: 0.85,
                transform: `scaleX(${highlight})`,
                transformOrigin: "left center",
                zIndex: 0,
              }}
            />
          ))}
          <span style={{position: "relative", zIndex: 1}}>{body}</span>
        </div>
      </div>
    </div>
  );
};
