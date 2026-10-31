import React from "react";
import {TalkingHead} from "../../src/TalkingHead";
import type {MotionProps, Theme} from "../../src/types";
import theme from "./preset.json";

/** 紧凑知识口播：字幕两行内完整落下，字体角色分开，配乐只在传入时压低。 */
export const OpusClean: React.FC<MotionProps> = (props) => {
  return <TalkingHead {...props} theme={theme as Theme} />;
};
