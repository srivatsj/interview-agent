import { useState, useRef, useCallback } from 'react';

interface AudioChunk {
  blob: Blob;
  timestamp: number;
}

export function useAudioRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [chunks, setChunks] = useState<AudioChunk[]>([]);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm',
      });

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          const chunk: AudioChunk = {
            blob: event.data,
            timestamp: Date.now(),
          };
          setChunks((prev) => [...prev, chunk]);
        }
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start(5000); // Capture chunks every 5 seconds
      setIsRecording(true);
    } catch (error) {
      console.error('Failed to start audio recording:', error);
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      streamRef.current?.getTracks().forEach((track) => track.stop());
      setIsRecording(false);
    }
  }, [isRecording]);

  const clearChunks = useCallback(() => {
    setChunks([]);
  }, []);

  return {
    isRecording,
    chunks,
    startRecording,
    stopRecording,
    clearChunks,
  };
}
