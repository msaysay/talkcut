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

const PAUSE = /[的了是在和就也要把被而与或及对给]/;
const EXIT_FRAMES = 6;

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

const latest = (items: Caption[], key: "start" | "end") => {
  let best: Caption | undefined;
  for (const item of items) {
    if (!best || item[key] >= best[key]) best = item;
  }
  return best;
};

const breakAt = (text: string, perLine: number) => {
  const target = Math.min(text.length - 1, Math.max(1, perLine));
  const start = Math.max(1, Math.floor(target * 0.55));
  for (let index = target; index >= start; index -= 1) {
    if (PAUSE.test(text[index - 1] ?? "")) return index;
  }
  return target;
};

/** One line up to 18 characters, otherwise two complete lines. Never append an ellipsis. */
const fitLines = (text: string, fontSize: number, maxWidth: number, minScale: number, charsPerLine: number) => {
  const per = Math.max(4, charsPerLine);
  const lines = text.length <= per
    ? [text]
    : [text.slice(0, breakAt(text, Math.min(per, text.length - 1))), text.slice(breakAt(text, Math.min(per, text.length - 1)))].filter((line) => line.length > 0);
  const widest = Math.max(1, ...lines.map((line) => line.length));
  const fitted = Math.floor(maxWidth / (widest * 1.02));
  const floor = Math.max(28, Math.round(fontSize * minScale));
  const size = Math.max(floor, Math.min(fontSize, fitted || fontSize));
  return {lines: lines.slice(0, 2), size};
};

const NumberRoll: React.FC<{value: number; progress: number}> = ({value, progress}) => {
  const shown = Math.round(interpolate(progress, [0, 1], [0, value], {extrapolateRight: "clamp"}));
  return <span style={{fontFamily: "TC Number, sans-serif"}}>{shown}</span>;
};

const SliceDigit: React.FC<{text: string; progress: number}> = ({text, progress}) => {
  const slices = 6;
  return (
    <span style={{display: "inline-grid", fontFamily: "TC Number, sans-serif", verticalAlign: "baseline"}}>
      {Array.from({length: slices}, (_, index) => {
        const from = index % 2 === 0 ? -22 : 22;
        const start = index * 0.06;
        const x = interpolate(progress, [start, Math.min(1, start + 0.55)], [from, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        const top = (index / slices) * 100;
        const bottom = ((slices - index - 1) / slices) * 100;
        return (
          <span key={index} style={{gridArea: "1 / 1", transform: `translateX(${x}px)`, clipPath: `inset(${top}% 0 ${bottom}% 0)`}}>
            {text}
          </span>
        );
      })}
    </span>
  );
};

const lineBody = (
  line: string,
  digit: string | undefined,
  roll: boolean,
  slash: boolean,
  progress: number,
  keyword: string | undefined,
  color: string,
) => {
  const token = keyword && line.includes(keyword) ? keyword : undefined;
  if (token && digit && token === digit && (roll || slash)) {
    const at = line.indexOf(digit);
    return (
      <>
        {line.slice(0, at)}
        <span style={{color}}>
          {slash ? <SliceDigit text={digit} progress={progress} /> : <NumberRoll value={Number(digit)} progress={progress} />}
        </span>
        {line.slice(at + digit.length)}
      </>
    );
  }
  if (token) {
    const at = line.indexOf(token);
    return (
      <>
        {line.slice(0, at)}
        <span style={{color}}>{token}</span>
        {line.slice(at + token.length)}
      </>
    );
  }
  if (!digit || !line.includes(digit) || (!roll && !slash)) return line;
  const at = line.indexOf(digit);
  return (
    <>
      {line.slice(0, at)}
      {slash ? <SliceDigit text={digit} progress={progress} /> : <NumberRoll value={Number(digit)} progress={progress} />}
      {line.slice(at + digit.length)}
    </>
  );
};

export const CaptionLayer: React.FC<{props: MotionProps; layout: string}> = ({props, layout}) => {
  const frame = useCurrentFrame();
  const {width, height, fps} = useVideoConfig();
  const time = frame / fps;
  const active = latest(
    props.captions.filter((item) => time >= item.start && time < item.end),
    "start",
  );
  const exitWindow = EXIT_FRAMES / fps;
  const leaving = active
    ? undefined
    : latest(
        props.captions.filter((item) => time >= item.end && time - item.end < exitWindow),
        "end",
      );
  const caption = active ?? leaving;
  if (!caption) return null;
  const local = active ? frame - Math.round(caption.start * fps) : Math.round((caption.end - caption.start) * fps);
  const fadeIn = interpolate(local, [0, 4], [0, 1], {extrapolateLeft: "clamp", extrapolateRight: "clamp"});
  const fadeOut = leaving
    ? interpolate(time - caption.end, [0, exitWindow], [1, 0], {extrapolateLeft: "clamp", extrapolateRight: "clamp"})
    : 1;
  const fade = fadeIn * fadeOut;
  const scale = height / (width > height ? 1080 : 1920);
  const tight = props.theme.motion === "settle" || props.theme.motion === "slash" || props.theme.motion === "morph";
  const margins = marginsOf(props.theme);
  const segment = (props.segments ?? []).find((item) => time >= item.start && time < item.end);
  const anchor = segment?.captionAnchor ?? "bottom";
  const bandCenter = props.theme.caption.bandCenter;
  const useBand = anchor === "bottom" && typeof bandCenter === "number";
  const bottom = Math.max((props.theme.caption.bottom / 1920) * height, margins.douyinBottom * height);
  const left = props.theme.caption.side * (width / 1080);
  const right = Math.max(props.theme.caption.side * (width / 1080), margins.douyinRight * width);
  const padX = tight ? 18 : 26;
  const maxWidth = Math.max(160, width - left - right - padX * 2);
  const minScale = props.theme.caption.minScale ?? 0.9;
  const spoken = caption.displayText || caption.text;
  const fitted = fitLines(spoken, sizeFor(props, caption.emphasis, scale), maxWidth, minScale, props.theme.caption.charsPerLine ?? 18);
  const effects = caption.effects ?? [];
  const rise = tight ? interpolate(local, [0, 6], [10, 0], {extrapolateLeft: "clamp", extrapolateRight: "clamp"}) : 0;
  const digit = caption.keywords.find((item) => /^\d+$/.test(item));
  const keyword = caption.keywords.find((item) => item && spoken.includes(item));
  const slashNumber = props.theme.motion === "slash" && Boolean(digit);
  const roll = !slashNumber && Boolean(digit) && (caption.emphasis === "number" || effects.includes("number-roll"));
  const progress = Math.min(1, local / (fps * (slashNumber ? 0.35 : 0.45)));
  const hookSlash = !slashNumber && (caption.emphasis === "hook" || effects.includes("slash-in"));
  const slash = hookSlash ? interpolate(local, [0, 6], [100, 0], {extrapolateRight: "clamp"}) : 0;
  const bar = layout === "h4" || effects.includes("lower-third");
  return (
    <div
      style={{
        position: "absolute",
        left,
        right,
        bottom: !useBand && anchor === "bottom" ? bottom : undefined,
        top: useBand ? `${bandCenter * 100}%` : anchor === "middle" ? height * 0.22 : anchor === "top" ? height * 0.08 : undefined,
        opacity: fade,
        display: "flex",
        justifyContent: "center",
        transform: useBand ? `translateY(calc(-50% + ${rise}px))` : `translateY(${rise}px)`,
        overflow: "visible",
      }}
    >
      <div
        style={{
          width: bar ? "100%" : "fit-content",
          maxWidth: "100%",
          background: props.theme.colors.pill,
          borderRadius: bar ? 0 : tight ? 12 : 18,
          padding: bar ? "14px 22px" : tight ? "12px 18px" : "18px 26px",
          textAlign: "center",
          clipPath: slash ? `inset(0 ${slash}% 0 0)` : undefined,
          boxShadow: caption.emphasis === "gold" ? `inset 0 -5px 0 ${props.theme.colors.accent}` : undefined,
          overflow: "visible",
        }}
      >
        <div
          style={{
            position: "relative",
            fontFamily: familyFor(caption),
            fontSize: fitted.size,
            fontWeight: 700,
            lineHeight: 1.22,
            letterSpacing: tight ? "0.03em" : 0,
            whiteSpace: "pre-line",
            textOverflow: "clip",
            overflow: "visible",
            color: props.theme.colors.ink,
            WebkitTextStroke: `2px ${props.theme.colors.stroke}`,
            paintOrder: "stroke fill",
          }}
        >
          <span style={{position: "relative", zIndex: 1}}>
            {fitted.lines.map((line, index) => {
              const earlier = fitted.lines.slice(0, index).some((item) => keyword && item.includes(keyword));
              return (
                <React.Fragment key={`${line}-${index}`}>
                  {index > 0 ? "\n" : null}
                  {lineBody(line, digit, roll, Boolean(slashNumber), progress, earlier ? undefined : keyword, props.theme.colors.accent)}
                </React.Fragment>
              );
            })}
          </span>
        </div>
      </div>
    </div>
  );
};
