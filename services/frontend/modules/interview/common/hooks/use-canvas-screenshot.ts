import { useEffect, useCallback, useState } from "react";
import type { ExcalidrawImperativeAPI } from "@excalidraw/excalidraw/types";

interface Screenshot {
  blob: Blob;
  timestamp: number;
}

export interface UseCanvasScreenshotOptions {
  onScreenshot?: (screenshot: Screenshot) => void;
  intervalMs?: number;
}

export function useCanvasScreenshot(
  excalidrawAPI: ExcalidrawImperativeAPI | null,
  { onScreenshot, intervalMs = 30000 }: UseCanvasScreenshotOptions = {},
) {
  const [screenshots, setScreenshots] = useState<Screenshot[]>([]);

  const captureScreenshot = useCallback(async () => {
    if (!excalidrawAPI) return;

    try {
      // Dynamic import to avoid SSR issues with window object
      const { exportToBlob } = await import("@excalidraw/excalidraw");

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
      onScreenshot?.(screenshot); // Call callback if provided
    } catch (error) {
      console.error("Failed to capture screenshot:", error);
    }
  }, [excalidrawAPI, onScreenshot]);

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
