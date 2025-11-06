'use client';

import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';
import { InterviewHeader } from '@/modules/interview/common/ui/components/interview-header';
import { VideoPanel } from '@/modules/interview/common/ui/components/video-panel';
import { ExcalidrawCanvas } from '../components/excalidraw-canvas';
import { useTimer } from '@/modules/interview/common/hooks/use-timer';

export function SystemDesignInterview() {
  const { formattedTime } = useTimer();

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden">
      <InterviewHeader elapsedTime={formattedTime} />

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
