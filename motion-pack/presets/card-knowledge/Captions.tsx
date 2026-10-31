import React from "react";
import {TalkingHead} from "../../src/TalkingHead";
import type {MotionProps, Theme} from "../../src/types";
import theme from "./preset.json";

/** 深色知识卡。字幕按抖音安全区放在画面中下，默认一行，最多两行且不截断。 */
export const CardKnowledge: React.FC<MotionProps> = (props) => {
  return <TalkingHead {...props} theme={theme as Theme} />;
};
