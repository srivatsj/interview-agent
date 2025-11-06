import { useEffect, useCallback, useState } from 'react';
import { exportToBlob } from '@excalidraw/excalidraw';
import type { ExcalidrawImperativeAPI } from '@excalidraw/excalidraw/types/types';

interface Screenshot {
  blob: Blob;
  timestamp: number;
}

export function useCanvasScreenshot(
  excalidrawAPI: ExcalidrawImperativeAPI | null,
  intervalMs: number = 10000
) {
  const [screenshots, setScreenshots] = useState<Screenshot[]>([]);

  const captureScreenshot = useCallback(async () => {
    if (!excalidrawAPI) return;

    try {
      const elements = excalidrawAPI.getSceneElements();
      const appState = excalidrawAPI.getAppState();
      const files = excalidrawAPI.getFiles();

      const blob = await exportToBlob({
        elements,
        appState,
        files,
      });

      const screenshot: Screenshot = {
        blob,
        timestamp: Date.now(),
      };

      setScreenshots((prev) => [...prev, screenshot]);
    } catch (error) {
      console.error('Failed to capture screenshot:', error);
    }
  }, [excalidrawAPI]);

  useEffect(() => {
    if (!excalidrawAPI) return;

    const interval = setInterval(captureScreenshot, intervalMs);
    return () => clearInterval(interval);
  }, [excalidrawAPI, intervalMs, captureScreenshot]);

  const clearScreenshots = useCallback(() => {
    setScreenshots([]);
  }, []);

  return {
    screenshots,
    captureScreenshot,
    clearScreenshots,
  };
}
