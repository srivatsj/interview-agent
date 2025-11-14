import { useRef, useCallback } from "react";
import { base64ToArrayBuffer } from "../utils/audio-utils";

const PLAYER_WORKLET_PATH = "/audio-player-worklet.js";

export function useAudioWorkletPlayer() {
  const audioContextRef = useRef<AudioContext | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const streamDestinationRef = useRef<MediaStreamAudioDestinationNode | null>(
    null,
  );

  const initializePlayer = useCallback(async () => {
    try {
      // Create audio context with 24kHz sample rate (Gemini Live API output)
      const playerContextOptions = { sampleRate: 24000 };

      if (!audioContextRef.current) {
        audioContextRef.current = new AudioContext(playerContextOptions);
      }
      const audioCtx = audioContextRef.current;

      if (audioCtx.state === "suspended") {
        await audioCtx.resume();
      }

      // Load the AudioWorklet module
      try {
        await audioCtx.audioWorklet.addModule(PLAYER_WORKLET_PATH);
        const playerNode = new AudioWorkletNode(
          audioCtx,
          "audio-player-processor",
        );

        // Connect to both speakers AND stream destination for recording
        playerNode.connect(audioCtx.destination); // For playback

        // Create stream destination for recording AI audio
        streamDestinationRef.current = audioCtx.createMediaStreamDestination();
        playerNode.connect(streamDestinationRef.current); // For recording

        workletNodeRef.current = playerNode;
      } catch (error) {
        console.error("Error setting up audio player worklet:", error);
      }
    } catch (error) {
      console.error("Failed to initialize audio player:", error);
    }
  }, []);

  const playAudio = useCallback((base64Data: string) => {
    if (!workletNodeRef.current) {
      console.warn("Audio player not initialized");
      return;
    }

    try {
      const audioDataBytes = base64ToArrayBuffer(base64Data);
      const int16Array = new Int16Array(audioDataBytes);

      // Send audio data to worklet
      workletNodeRef.current.port.postMessage(
        { type: "audio_data", buffer: int16Array.buffer },
        [int16Array.buffer],
      );
    } catch (error) {
      console.error("Failed to play audio:", error);
    }
  }, []);

  const flush = useCallback(() => {
    if (workletNodeRef.current) {
      workletNodeRef.current.port.postMessage({ type: "flush" });
    }
  }, []);

  const stopPlayer = useCallback(() => {
    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    streamDestinationRef.current = null;
  }, []);

  const getAudioStream = useCallback((): MediaStream | null => {
    return streamDestinationRef.current?.stream || null;
  }, []);

  return {
    initializePlayer,
    playAudio,
    flush,
    stopPlayer,
    getAudioStream,
  };
}
