'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';
import { InterviewHeader } from '@/modules/interview/common/ui/components/interview-header';
import { VideoPanel } from '@/modules/interview/common/ui/components/video-panel';
import { ExcalidrawCanvas } from '../components/excalidraw-canvas';
import { useTimer } from '@/modules/interview/common/hooks/use-timer';
import { useAudioRecorder } from '@/modules/interview/common/hooks/use-audio-recorder';
import { useAudioPlayer } from '@/modules/interview/common/hooks/use-audio-player';
import { useCanvasScreenshot } from '@/modules/interview/common/hooks/use-canvas-screenshot';
import { useWebSocket, type ADKEvent } from '@/modules/interview/common/hooks/use-websocket';
import type { ExcalidrawImperativeAPI } from '@excalidraw/excalidraw/types';

// Helper to convert Blob to base64
async function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64 = reader.result as string;
      // Remove data:...;base64, prefix
      const base64Data = base64.split(',')[1];
      resolve(base64Data);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

export function SystemDesignInterview() {
  const [excalidrawAPI, setExcalidrawAPI] = useState<ExcalidrawImperativeAPI | null>(null);
  const [userId] = useState(() => `user-${Date.now()}`);
  const [sessionId] = useState(() => `session-${Date.now()}`);

  const { formattedTime } = useTimer();
  const { playAudio } = useAudioPlayer();

  // WebSocket connection
  const websocketUrl = useMemo(
    () =>
      `ws://localhost:8080/run_live?app_name=interview_orchestrator&user_id=${userId}&session_id=${sessionId}`,
    [userId, sessionId]
  );

  // Handle incoming messages from WebSocket
  const handleWebSocketMessage = useCallback(
    (event: ADKEvent) => {
      console.log('Received event type:', event.type);

      // Handle AI audio responses
      if (event.content?.parts) {
        for (const part of event.content.parts) {
          // Check for inline audio data
          if (part.inline_data?.mime_type?.startsWith('audio/')) {
            const audioData = part.inline_data.data;
            // Convert base64 to blob URL for playback
            const audioBlob = new Blob(
              [Uint8Array.from(atob(audioData), (c) => c.charCodeAt(0))],
              { type: part.inline_data.mime_type }
            );
            const audioUrl = URL.createObjectURL(audioBlob);
            playAudio(audioUrl);
          }

          // Log text responses
          if (part.text) {
            console.log('AI:', part.text);
          }
        }
      }
    },
    [playAudio]
  );

  const { isConnected, sendMessage } = useWebSocket({
    url: websocketUrl,
    onMessage: handleWebSocketMessage,
    onConnect: () => console.log('✓ Connected to interview orchestrator'),
    onDisconnect: () => console.log('Disconnected from interview orchestrator'),
    onError: (error) => console.error('WebSocket error:', error),
    autoConnect: true,
  });

  // Send audio chunks to WebSocket
  const handleAudioChunk = useCallback(
    async (chunk: { blob: Blob; timestamp: number }) => {
      if (!isConnected) return;

      try {
        const base64Data = await blobToBase64(chunk.blob);
        sendMessage({
          blob: {
            mime_type: 'audio/webm',
            data: base64Data,
          },
        });
      } catch (error) {
        console.error('Failed to send audio chunk:', error);
      }
    },
    [isConnected, sendMessage]
  );

  // Send screenshots to WebSocket
  const handleScreenshot = useCallback(
    async (screenshot: { blob: Blob; timestamp: number }) => {
      if (!isConnected) return;

      try {
        const base64Data = await blobToBase64(screenshot.blob);
        sendMessage({
          blob: {
            mime_type: 'image/png',
            data: base64Data,
          },
        });
      } catch (error) {
        console.error('Failed to send screenshot:', error);
      }
    },
    [isConnected, sendMessage]
  );

  // Setup audio recorder with WebSocket callback
  const { isRecording, startRecording } = useAudioRecorder({
    onChunk: handleAudioChunk,
    chunkInterval: 5000,
  });

  // Setup screenshot capture with WebSocket callback
  useCanvasScreenshot(excalidrawAPI, {
    onScreenshot: handleScreenshot,
    intervalMs: 10000,
  });

  // Start audio recording when connected
  useEffect(() => {
    if (isConnected && !isRecording) {
      startRecording();
    }
  }, [isConnected, isRecording, startRecording]);

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
          <ExcalidrawCanvas onExcalidrawAPIInit={setExcalidrawAPI} />
        </ResizablePanel>

        <ResizableHandle className="w-1 bg-slate-200 hover:bg-slate-300" />

        <ResizablePanel defaultSize={30} minSize={20} maxSize={40} className="overflow-hidden">
          <VideoPanel />
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
}
