import React from "react";
import {TalkingHead} from "../../src/TalkingHead";
import type {MotionProps, Theme} from "../../src/types";
import theme from "./preset.json";

/** 干净知识口播：下三分之一字幕，淡入，数字用强调色，人声时配乐压低。 */
export const CleanKnowledge: React.FC<MotionProps> = (props) => {
  return <TalkingHead {...props} theme={theme as Theme} />;
};
