'use client';

import { Excalidraw } from '@excalidraw/excalidraw';
import '@excalidraw/excalidraw/index.css';

export default function ExcalidrawWrapper() {
  return (
    <div style={{ height: '100%', width: '100%' }}>
      <Excalidraw
        theme="light"
        initialData={{
          appState: {
            viewBackgroundColor: '#ffffff',
          },
        }}
      />
    </div>
  );
}
