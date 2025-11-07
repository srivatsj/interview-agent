'use client';

import { Excalidraw } from '@excalidraw/excalidraw';
import '@excalidraw/excalidraw/index.css';
import type { ExcalidrawImperativeAPI } from '@excalidraw/excalidraw/types';

interface ExcalidrawWrapperProps {
  onInit?: (api: ExcalidrawImperativeAPI) => void;
}

export default function ExcalidrawWrapper({ onInit }: ExcalidrawWrapperProps) {
  return (
    <div style={{ height: '100%', width: '100%' }}>
      <Excalidraw
        theme="light"
        initialData={{
          appState: {
            viewBackgroundColor: '#ffffff',
          },
        }}
        excalidrawAPI={onInit}
      />
    </div>
  );
}
