'use client';

import { useState, useEffect } from 'react';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';
import { InterviewHeader } from '@/modules/interview/common/ui/components/interview-header';
import { VideoPanel } from '@/modules/interview/common/ui/components/video-panel';
import { ExcalidrawCanvas } from '../components/excalidraw-canvas';
import { useTimer } from '@/modules/interview/common/hooks/use-timer';
import { useAudioRecorder } from '@/modules/interview/common/hooks/use-audio-recorder';
import { useAudioPlayer } from '@/modules/interview/common/hooks/use-audio-player';
import { useCanvasScreenshot } from '@/modules/interview/common/hooks/use-canvas-screenshot';
import type { ExcalidrawImperativeAPI } from '@excalidraw/excalidraw/types/types';

export function SystemDesignInterview() {
  const [excalidrawAPI, setExcalidrawAPI] = useState<ExcalidrawImperativeAPI | null>(null);

  const { formattedTime } = useTimer();
  const { isRecording, chunks: audioChunks, startRecording } = useAudioRecorder();
  const { isPlaying, playAudio } = useAudioPlayer();
  const { screenshots } = useCanvasScreenshot(excalidrawAPI, 10000);

  // Start audio recording on mount
  useEffect(() => {
    startRecording();
  }, [startRecording]);

  // Log data for debugging (no API calls yet)
  useEffect(() => {
    if (audioChunks.length > 0) {
      console.log(`Captured ${audioChunks.length} audio chunks`);
    }
  }, [audioChunks]);

  useEffect(() => {
    if (screenshots.length > 0) {
      console.log(`Captured ${screenshots.length} screenshots`);

      // Debug: Expose to window for manual inspection
      if (typeof window !== 'undefined') {
        (window as any).__INTERVIEW_SCREENSHOTS__ = screenshots;
        console.log('💡 To download latest screenshot, run: window.downloadLatestScreenshot()');
      }
    }
  }, [screenshots]);

  // Debug helper to download screenshots
  useEffect(() => {
    if (typeof window !== 'undefined') {
      (window as any).downloadLatestScreenshot = () => {
        if (screenshots.length === 0) {
          console.log('No screenshots captured yet');
          return;
        }
        const latest = screenshots[screenshots.length - 1];
        const url = URL.createObjectURL(latest.blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `screenshot-${latest.timestamp}.png`;
        a.click();
        URL.revokeObjectURL(url);
        console.log('Downloaded latest screenshot!');
      };
    }
  }, [screenshots]);

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden">
      <InterviewHeader elapsedTime={formattedTime} />

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
