import dynamic from 'next/dynamic';
import type { ExcalidrawImperativeAPI } from '@excalidraw/excalidraw/types/types';

const ExcalidrawWrapper = dynamic(
  () => import('./excalidraw-wrapper'),
  { ssr: false }
);

interface ExcalidrawCanvasProps {
  onExcalidrawAPIInit?: (api: ExcalidrawImperativeAPI) => void;
}

export function ExcalidrawCanvas({ onExcalidrawAPIInit }: ExcalidrawCanvasProps) {
  return (
    <div style={{ height: '100%', width: '100%' }}>
      <ExcalidrawWrapper onInit={onExcalidrawAPIInit} />
    </div>
  );
}
