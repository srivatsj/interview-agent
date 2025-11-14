import { useState, useRef, useCallback } from "react";

export interface ScreenRecorderOptions {
  mimeType?: string;
  videoBitsPerSecond?: number;
}

export function useScreenRecorder(options?: ScreenRecorderOptions) {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingBlob, setRecordingBlob] = useState<Blob | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const screenStreamRef = useRef<MediaStream | null>(null);

  /**
   * Start recording with canvas stream, webcam, and audio
   * @param audioStream - Mixed audio stream (candidate + agent)
   * @param canvasStream - Canvas video stream (Excalidraw)
   * @param webcamStream - Webcam video stream (candidate face)
   * @returns Promise that resolves when recording starts
   */
  const startRecording = useCallback(
    async (
      audioStream?: MediaStream,
      canvasStream?: MediaStream,
      webcamStream?: MediaStream,
    ) => {
      try {
        console.log("🎥 Starting recording with:");
        console.log("  - Audio tracks:", audioStream?.getAudioTracks().length || 0);
        console.log("  - Canvas video tracks:", canvasStream?.getVideoTracks().length || 0);
        console.log("  - Webcam video tracks:", webcamStream?.getVideoTracks().length || 0);

        // Collect all video and audio tracks
        const tracks: MediaStreamTrack[] = [];

        // Add canvas video if provided
        if (canvasStream) {
          const canvasTracks = canvasStream.getVideoTracks();
          tracks.push(...canvasTracks);
          console.log("  ✓ Canvas video added");
        }

        // Add webcam video if provided
        if (webcamStream) {
          const webcamTracks = webcamStream.getVideoTracks();
          tracks.push(...webcamTracks);
          console.log("  ✓ Webcam video added");
        }

        // Add mixed audio if provided
        if (audioStream) {
          const audioTracks = audioStream.getAudioTracks();
          tracks.push(...audioTracks);
          console.log("  ✓ Mixed audio added");
        }

        if (tracks.length === 0) {
          throw new Error("No tracks available for recording");
        }

        console.log(`📹 Total tracks for recording: ${tracks.length}`);
        const combinedStream = new MediaStream(tracks);

        // Create MediaRecorder
        const mimeType = options?.mimeType || "video/webm;codecs=vp9,opus";
        const mediaRecorder = new MediaRecorder(combinedStream, {
          mimeType,
          videoBitsPerSecond: options?.videoBitsPerSecond || 2500000, // 2.5 Mbps
        });

        // Reset chunks
        chunksRef.current = [];

        // Collect data chunks
        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            chunksRef.current.push(event.data);
          }
        };

        // Handle recording stop
        mediaRecorder.onstop = () => {
          const blob = new Blob(chunksRef.current, { type: mimeType });
          setRecordingBlob(blob);
        };

        // Handle errors
        mediaRecorder.onerror = (event) => {
          console.error("Recording error:", event);
        };

        // Start recording (capture every 1 second)
        mediaRecorder.start(1000);
        mediaRecorderRef.current = mediaRecorder;
        setIsRecording(true);
      } catch (error) {
        console.error("Failed to start screen recording:", error);
        throw error;
      }
    },
    [options?.mimeType, options?.videoBitsPerSecond],
  );

  /**
   * Stop the screen recording
   * @returns Promise that resolves with the recording blob
   */
  const stopRecording = useCallback(async (): Promise<Blob | null> => {
    return new Promise((resolve) => {
      if (!mediaRecorderRef.current) {
        resolve(null);
        return;
      }

      const mediaRecorder = mediaRecorderRef.current;

      // Wait for onstop to fire, then resolve with blob
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, {
          type: mediaRecorder.mimeType,
        });
        setRecordingBlob(blob);
        setIsRecording(false);

        // Stop screen stream tracks
        if (screenStreamRef.current) {
          screenStreamRef.current.getTracks().forEach((track) => track.stop());
          screenStreamRef.current = null;
        }

        resolve(blob);
      };

      if (mediaRecorder.state === "recording") {
        mediaRecorder.stop();
      } else {
        // Already stopped
        resolve(recordingBlob);
      }

      mediaRecorderRef.current = null;
    });
  }, [recordingBlob]);

  /**
   * Clean up resources
   */
  const cleanup = useCallback(() => {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state === "recording"
    ) {
      mediaRecorderRef.current.stop();
    }

    if (screenStreamRef.current) {
      screenStreamRef.current.getTracks().forEach((track) => track.stop());
      screenStreamRef.current = null;
    }

    chunksRef.current = [];
    setRecordingBlob(null);
    setIsRecording(false);
  }, []);

  return {
    isRecording,
    recordingBlob,
    startRecording,
    stopRecording,
    cleanup,
  };
}
