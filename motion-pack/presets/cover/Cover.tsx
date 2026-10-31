import React from "react";
import {AbsoluteFill, staticFile} from "remotion";
import type {MotionProps} from "../../src/types";

/** 竖屏封面静帧。标题在安全区上沿，不替代第 3 段的字幕动效。 */
export const CoverStill: React.FC<MotionProps> = (props) => {
  const theme = props.theme;
  const font = `"TalkCut CJK", "Droid Sans Fallback", sans-serif`;
  return (
    <AbsoluteFill style={{backgroundColor: "#14120f", fontFamily: font, color: theme.colors.ink}}>
      <style>
        {`@font-face { font-family: "TalkCut CJK"; src: url("${staticFile(props.fontFile)}") format("truetype"); }`}
      </style>
      <div style={{position: "absolute", left: 72, right: 72, top: 180}}>
        <div style={{fontSize: 36, letterSpacing: 4, color: theme.colors.accent, marginBottom: 28}}>口播</div>
        <div
          style={{
            fontSize: 84,
            fontWeight: 700,
            lineHeight: 1.2,
            WebkitTextStroke: `3px ${theme.colors.stroke}`,
            paintOrder: "stroke fill",
          }}
        >
          {props.title}
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          left: 72,
          right: 72,
          bottom: 220,
          height: 8,
          background: theme.colors.accent,
        }}
      />
    </AbsoluteFill>
  );
};
