import { useEffect, useRef, useState } from "react";
import type { ExcalidrawImperativeAPI } from "@excalidraw/excalidraw/types";

/**
 * Captures a video stream from the Excalidraw canvas
 * This allows recording the canvas without screen sharing prompts
 */
export function useCanvasStream(excalidrawAPI: ExcalidrawImperativeAPI | null) {
  const [canvasStream, setCanvasStream] = useState<MediaStream | null>(null);
  const retryCountRef = useRef(0);

  useEffect(() => {
    if (!excalidrawAPI) return;

    const attemptCapture = () => {
      try {
        // Try multiple selectors
        const selectors = [
          ".excalidraw__canvas canvas",
          "canvas.excalidraw",
          ".excalidraw canvas",
          'canvas[class*="excalidraw"]',
        ];

        let canvas: HTMLCanvasElement | null = null;
        for (const selector of selectors) {
          canvas = document.querySelector(selector) as HTMLCanvasElement;
          if (canvas) break;
        }

        if (!canvas) {
          // Retry up to 5 times
          if (retryCountRef.current < 5) {
            retryCountRef.current++;
            setTimeout(attemptCapture, 1000);
          } else {
            console.error("❌ Canvas element not found after 5 attempts");
          }
          return;
        }

        // Capture stream from canvas at 30 FPS
        const stream = canvas.captureStream(30);

        if (!stream || stream.getVideoTracks().length === 0) {
          console.error("❌ Canvas stream has no video tracks");
          return;
        }

        const videoTrack = stream.getVideoTracks()[0];
        const settings = videoTrack.getSettings();
        console.log(
          `🎨 Canvas stream ready: ${settings.width}x${settings.height} @ ${settings.frameRate}fps`,
        );

        setCanvasStream(stream);
      } catch (error) {
        console.error("Failed to capture canvas stream:", error);

        // Retry on error
        if (retryCountRef.current < 5) {
          retryCountRef.current++;
          setTimeout(attemptCapture, 1000);
        }
      }
    };

    // Initial delay to let Excalidraw render
    const timer = setTimeout(attemptCapture, 1500);

    return () => {
      clearTimeout(timer);
      retryCountRef.current = 0;
    };
  }, [excalidrawAPI]);

  return canvasStream;
}
