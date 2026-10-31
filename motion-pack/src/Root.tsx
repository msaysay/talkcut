import React from "react";
import { AbsoluteFill, Composition, useCurrentFrame } from "remotion";

const Placeholder: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#141414",
        color: "#f4f1ea",
        fontFamily: "sans-serif",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div style={{ fontSize: 72, fontWeight: 700 }}>TalkCut</div>
      <div style={{ marginTop: 16, fontSize: 28, opacity: 0.75 }}>
        motion-pack stub · frame {frame}
      </div>
    </AbsoluteFill>
  );
};

/** Vertical 9:16 placeholder. Real caption and BGM presets replace this composition. */
export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="TalkCutPlaceholder"
      component={Placeholder}
      durationInFrames={90}
      fps={30}
      width={1080}
      height={1920}
    />
  );
};
