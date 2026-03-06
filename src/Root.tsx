import React from "react";
import { Composition } from "remotion";
import { Interview } from "./Interview";
import subData from "../sub.json";

const FPS = 30;

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="interview"
      component={Interview}
      durationInFrames={subData.duration * FPS}
      fps={FPS}
      width={1080}
      height={1080}
    />
  );
};
