import React from "react";
import {TalkingHead} from "../../src/TalkingHead";
import type {MotionProps, Theme} from "../../src/types";
import theme from "./preset.json";

/** 数字从左右切片砍入并锁住。配乐仍然只在用户传入时叠加，并压在人声下面。 */
export const OpusPunch: React.FC<MotionProps> = (props) => {
  return <TalkingHead {...props} theme={theme as Theme} />;
};
