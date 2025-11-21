import dynamic from 'next/dynamic';
import type { ExcalidrawImperativeAPI } from '@excalidraw/excalidraw/types';

const ExcalidrawWrapper = dynamic(
  () => import('./excalidraw-wrapper'),
  { ssr: false }
);

interface ExcalidrawCanvasProps {
  onExcalidrawAPIInit?: (api: ExcalidrawImperativeAPI) => void;
}

export function ExcalidrawCanvas({ onExcalidrawAPIInit }: ExcalidrawCanvasProps) {
  return (
    <div className="h-full w-full">
      <ExcalidrawWrapper onInit={onExcalidrawAPIInit} />
    </div>
  );
}
