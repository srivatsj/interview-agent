'use client';

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';
import { InterviewHeader } from '@/modules/interview/common/ui/components/interview-header';
import { VideoPanel } from '@/modules/interview/common/ui/components/video-panel';
import { ExcalidrawCanvas } from '../components/excalidraw-canvas';
import { useTimer } from '@/modules/interview/common/hooks/use-timer';
import { useWebSocket, type StructuredAgentEvent } from '@/modules/interview/common/hooks/use-websocket';
import { useAudioWorkletRecorder } from '@/modules/interview/common/hooks/use-audio-worklet-recorder';
import { useAudioWorkletPlayer } from '@/modules/interview/common/hooks/use-audio-worklet-player';
import type { ExcalidrawImperativeAPI } from '@excalidraw/excalidraw/types';

export function SystemDesignInterview() {
  // const [excalidrawAPI, setExcalidrawAPI] = useState<ExcalidrawImperativeAPI | null>(null);
  const [userId] = useState(() => Date.now());
  const hasConnectedRef = useRef(false);
  const hasInitializedAudioRef = useRef(false);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const isConnectedRef = useRef(false);

  const { formattedTime } = useTimer();

  // Initialize AudioWorklet player
  const { initializePlayer, playAudio, flush } = useAudioWorkletPlayer();

  // WebSocket connection - CRITICAL: is_audio=true for audio mode
  const websocketUrl = useMemo(
    () => `ws://localhost:8000/ws/${userId}?is_audio=true`,
    [userId]
  );

  // Handle incoming structured messages from WebSocket
  const handleWebSocketMessage = useCallback(
    (event: StructuredAgentEvent) => {
      // Handle interruption - flush audio player
      if (event.interrupted) {
        flush();
        return;
      }

      // Handle turn completion
      if (event.turn_complete) {
        return;
      }

      // Process all parts in the event
      for (const part of event.parts) {
        if (part.type === 'audio/pcm') {
          // Play PCM audio using AudioWorklet
          playAudio(part.data);
        }
      }
    },
    [playAudio, flush]
  );

  // WebSocket configuration
  const { isConnected, sendMessage, connect } = useWebSocket({
    url: websocketUrl,
    onMessage: handleWebSocketMessage,
    onConnect: () => {
      isConnectedRef.current = true;
      // Initialize audio after successful connection
      initializeAudio();
    },
    onDisconnect: () => {
      isConnectedRef.current = false;
    },
    onError: (error) => console.error('WebSocket error:', error),
    autoConnect: false,
  });

  // Send audio data to WebSocket (PCM format)
  const handleAudioData = useCallback(
    (base64Data: string) => {
      if (!isConnectedRef.current) {
        return;
      }

      sendMessage({
        mime_type: 'audio/pcm',
        data: base64Data,
      });
    },
    [sendMessage]
  );

  // Handle speech start (for barge-in)
  const handleSpeechStart = useCallback(() => {
    flush();
  }, [flush]);

  // Setup AudioWorklet recorder
  const { startRecording, stopRecording } = useAudioWorkletRecorder({
    onAudioData: handleAudioData,
    onSpeechStart: handleSpeechStart,
  });

  // Initialize audio (player and recorder)
  const initializeAudio = useCallback(async () => {
    if (hasInitializedAudioRef.current) return;

    try {
      // Initialize audio player
      await initializePlayer();

      // Get microphone stream
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: false,
      });

      mediaStreamRef.current = stream;

      // Start AudioWorklet recorder
      await startRecording(stream);

      hasInitializedAudioRef.current = true;
    } catch (error) {
      console.error('Failed to initialize audio:', error);
    }
  }, [initializePlayer, startRecording]);

  // Initiate connection when component mounts (only once)
  useEffect(() => {
    if (!hasConnectedRef.current) {
      hasConnectedRef.current = true;
      connect();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      }
      stopRecording();
    };
  }, [stopRecording]);

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden">
      <InterviewHeader elapsedTime={formattedTime} />

      {!isConnected && (
        <div className="absolute top-20 left-1/2 -translate-x-1/2 bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-2 rounded-lg shadow-lg z-50">
          Connecting to interview server...
        </div>
      )}

      <ResizablePanelGroup direction="horizontal" className="flex-1 overflow-hidden">
        <ResizablePanel defaultSize={70} minSize={50} className="overflow-hidden">
          <ExcalidrawCanvas />
        </ResizablePanel>

        <ResizableHandle className="w-1 bg-slate-200 hover:bg-slate-300" />

        <ResizablePanel defaultSize={30} minSize={20} maxSize={40} className="overflow-hidden">
          <VideoPanel />
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
}
