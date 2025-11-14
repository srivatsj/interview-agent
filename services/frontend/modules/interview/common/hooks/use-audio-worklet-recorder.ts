import { useRef, useCallback } from "react";
import { arrayBufferToBase64 } from "../utils/audio-utils";

const RECORDER_WORKLET_PATH = "/audio-recorder-worklet.js";

interface AudioWorkletRecorderOptions {
  onAudioData: (base64Data: string) => void;
  onSpeechStart?: () => void;
}

export function useAudioWorkletRecorder({
  onAudioData,
  onSpeechStart,
}: AudioWorkletRecorderOptions) {
  const audioContextRef = useRef<AudioContext | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);

  const startRecording = useCallback(
    async (stream: MediaStream) => {
      try {
        // Create audio context with 16kHz sample rate (required for Gemini Live API)
        const recorderContextOptions = { sampleRate: 16000 };

        const audioTracks = stream.getAudioTracks();
        if (audioTracks.length === 0) {
          console.warn(
            "No audio tracks found in the stream. Skipping audio recording setup.",
          );
          return;
        }

        if (!audioContextRef.current) {
          audioContextRef.current = new AudioContext(recorderContextOptions);
        }
        const audioCtx = audioContextRef.current;

        if (audioCtx.state === "suspended") {
          await audioCtx.resume();
        }

        // Load the AudioWorklet module
        try {
          await audioCtx.audioWorklet.addModule(RECORDER_WORKLET_PATH);
        } catch (e) {
          console.error("Error adding audio recorder worklet module", e);
          return;
        }

        // Create worklet node
        const micSourceNode = audioCtx.createMediaStreamSource(stream);
        const workletNode = new AudioWorkletNode(
          audioCtx,
          "audio-recorder-processor",
        );

        // Handle messages from worklet
        let audioChunkCount = 0;
        workletNode.port.onmessage = (event) => {
          if (event.data.type === "audio_data") {
            const pcmDataBuffer = event.data.buffer;
            const base64Data = arrayBufferToBase64(pcmDataBuffer);
            audioChunkCount++;
            // Only log every 100th chunk to reduce noise
            if (audioChunkCount % 100 === 0) {
              console.log("🎙️ Recorder: Sent", audioChunkCount, "audio chunks");
            }
            onAudioData(base64Data);
          } else if (event.data.type === "speech_start") {
            console.log("🎙️ Recorder: Speech detected!");
            onSpeechStart?.();
          }
        };

        micSourceNode.connect(workletNode);
        workletNodeRef.current = workletNode;
        mediaStreamRef.current = stream;

        console.log("Audio recorder worklet setup complete.");
      } catch (error) {
        console.error("Failed to setup audio recorder worklet:", error);
      }
    },
    [onAudioData, onSpeechStart],
  );

  const stopRecording = useCallback(() => {
    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }

    console.log("Audio recorder stopped.");
  }, []);

  return {
    startRecording,
    stopRecording,
  };
}
