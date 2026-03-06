import React from "react";
import { AbsoluteFill, Audio, Img, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont } from "@remotion/google-fonts/NotoSansSC";
import subData from "../sub.json";

const { fontFamily } = loadFont("normal", {
  weights: ["700"],
  ignoreTooManyRequestsWarning: true,
});

interface SubtitleEntry {
  start: number;
  end: number;
  text: string;
}

const SPEAKERS = Object.keys(subData.speakers);
const SUBTITLES: Record<string, SubtitleEntry[]> = subData.speakers;
const ANNOTATIONS: SubtitleEntry[] = subData.annotations;

const SPEAKER_CONFIG: Record<string, { image: string; bgColor: string }> = {
  [SPEAKERS[0]]: { image: `${SPEAKERS[0]}.jpeg`, bgColor: "#1a1a1a" },
  [SPEAKERS[1]]: { image: `${SPEAKERS[1]}.jpeg`, bgColor: "#2a2a2a" },
};

const textShadow = [
  "-2px -2px 0 #000",
  "2px -2px 0 #000",
  "-2px 2px 0 #000",
  "2px 2px 0 #000",
  "0 -2px 0 #000",
  "0 2px 0 #000",
  "-2px 0 0 #000",
  "2px 0 0 #000",
].join(", ");

function getCurrentSubtitle(entries: SubtitleEntry[], timeSec: number): string | null {
  for (const entry of entries) {
    if (timeSec >= entry.start && timeSec < entry.end) {
      return entry.text;
    }
  }
  return null;
}

const SpeakerHalf: React.FC<{
  speaker: string;
  image: string;
  timeSec: number;
  bgColor: string;
}> = ({ speaker, image, timeSec, bgColor }) => {
  const subtitle = getCurrentSubtitle(SUBTITLES[speaker], timeSec);

  return (
    <div
      style={{
        width: 1080,
        height: 540,
        backgroundColor: bgColor,
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
        padding: "0 30px",
        boxSizing: "border-box",
      }}
    >
      <Img
        src={staticFile(image)}
        style={{
          width: 200,
          height: 200,
          objectFit: "cover",
          borderRadius: 12,
          flexShrink: 0,
        }}
      />
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "flex-start",
          paddingLeft: 30,
          minWidth: 0,
        }}
      >
        {subtitle && (
          <div
            style={{
              fontFamily,
              fontSize: 40,
              fontWeight: 700,
              color: "white",
              textShadow,
              lineHeight: 1.4,
              wordBreak: "break-word",
            }}
          >
            {subtitle}
          </div>
        )}
      </div>
    </div>
  );
};

export const Interview: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const timeSec = frame / fps;
  const annotation = getCurrentSubtitle(ANNOTATIONS, timeSec);

  return (
    <AbsoluteFill style={{ backgroundColor: "#1a1a1a" }}>
      <SpeakerHalf
        speaker={SPEAKERS[0]}
        image={SPEAKER_CONFIG[SPEAKERS[0]].image}
        timeSec={timeSec}
        bgColor={SPEAKER_CONFIG[SPEAKERS[0]].bgColor}
      />
      <div
        style={{
          width: 1080,
          height: 4,
          backgroundColor: "#444444",
          flexShrink: 0,
        }}
      />
      <SpeakerHalf
        speaker={SPEAKERS[1]}
        image={SPEAKER_CONFIG[SPEAKERS[1]].image}
        timeSec={timeSec}
        bgColor={SPEAKER_CONFIG[SPEAKERS[1]].bgColor}
      />
      {annotation && (
        <div
          style={{
            position: "absolute",
            top: 540,
            left: 0,
            width: 1080,
            display: "flex",
            justifyContent: "center",
            transform: "translateY(-50%)",
          }}
        >
          <div
            style={{
              fontFamily,
              fontSize: 28,
              fontWeight: 700,
              color: "rgba(255, 255, 255, 0.8)",
              textShadow,
              lineHeight: 1.4,
              textAlign: "center",
              padding: "4px 16px",
            }}
          >
            {annotation}
          </div>
        </div>
      )}
      <Audio src={staticFile("audio.mp3")} />
    </AbsoluteFill>
  );
};
