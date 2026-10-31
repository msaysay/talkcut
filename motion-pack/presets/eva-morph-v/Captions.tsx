import React from "react";
import {TalkingHead} from "../../src/TalkingHead";
import type {MotionProps, Theme} from "../../src/types";
import theme from "./preset.json";

/** 全屏人脸收到右下圆角窗，落在底部安全区之上。字幕用 displayText，不改源句。 */
export const EvaMorphV: React.FC<MotionProps> = (props) => {
  return <TalkingHead {...props} theme={theme as Theme} />;
};
