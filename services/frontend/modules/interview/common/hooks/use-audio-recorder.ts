import { useState, useRef, useCallback } from 'react';

interface AudioChunk {
  blob: Blob;
  timestamp: number;
}

export interface UseAudioRecorderOptions {
  onChunk?: (chunk: AudioChunk) => void;
  chunkInterval?: number;
}

export function useAudioRecorder({ onChunk, chunkInterval = 5000 }: UseAudioRecorderOptions = {}) {
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
          onChunk?.(chunk); // Call callback if provided
        }
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start(chunkInterval);
      setIsRecording(true);
    } catch (error) {
      console.error('Failed to start audio recording:', error);
    }
  }, [onChunk, chunkInterval]);

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
