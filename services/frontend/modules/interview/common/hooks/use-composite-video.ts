import { useRef, useCallback, useEffect, useState } from "react";

interface CompositeVideoOptions {
  canvasStream: MediaStream | null;
  webcamStream: MediaStream | null;
  layout?: "picture-in-picture" | "side-by-side";
}

/**
 * Composites multiple video streams into a single video stream
 * This allows recording both canvas and webcam in a single video
 */
export function useCompositeVideo({
  canvasStream,
  webcamStream,
  layout = "picture-in-picture",
}: CompositeVideoOptions) {
  const [compositeStream, setCompositeStream] = useState<MediaStream | null>(
    null,
  );
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const canvasVideoRef = useRef<HTMLVideoElement | null>(null);
  const webcamVideoRef = useRef<HTMLVideoElement | null>(null);

  const stopCompositing = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }

    if (canvasVideoRef.current) {
      canvasVideoRef.current.srcObject = null;
    }
    if (webcamVideoRef.current) {
      webcamVideoRef.current.srcObject = null;
    }
  }, []);

  useEffect(() => {
    if (!canvasStream && !webcamStream) {
      stopCompositing();
      setCompositeStream(null);
      return;
    }

    if (!canvasStream || !webcamStream) {
      return;
    }

    console.log("🎬 Creating composite video (canvas + webcam)...");

    // Create hidden video elements to play the streams
    const canvasVideo = document.createElement("video");
    const webcamVideo = document.createElement("video");
    canvasVideo.autoplay = true;
    canvasVideo.muted = true;
    webcamVideo.autoplay = true;
    webcamVideo.muted = true;

    canvasVideoRef.current = canvasVideo;
    webcamVideoRef.current = webcamVideo;

    // Create composite canvas
    const compositeCanvas = document.createElement("canvas");
    canvasRef.current = compositeCanvas;

    // Set canvas size based on layout
    if (layout === "picture-in-picture") {
      // Use canvas stream dimensions as base
      compositeCanvas.width = 1920;
      compositeCanvas.height = 1080;
    } else {
      compositeCanvas.width = 1920;
      compositeCanvas.height = 1080;
    }

    const ctx = compositeCanvas.getContext("2d");
    if (!ctx) {
      console.error("Failed to get 2D context");
      return;
    }

    // Set video sources and play
    if (canvasStream) {
      canvasVideo.srcObject = canvasStream;
      canvasVideo.play().catch((err) => console.error("Canvas video play error:", err));
    }
    if (webcamStream) {
      webcamVideo.srcObject = webcamStream;
      webcamVideo.play().catch((err) => console.error("Webcam video play error:", err));
    }

    // Wait for videos to be ready
    const startCompositing = () => {
      console.log("✅ Starting video compositing (30 FPS)...");

      const draw = () => {
        if (!ctx || !canvasRef.current) return;

        // Clear canvas with white background
        ctx.fillStyle = "#FFFFFF";
        ctx.fillRect(0, 0, compositeCanvas.width, compositeCanvas.height);

        // Draw canvas video (main view)
        if (canvasVideo.readyState >= canvasVideo.HAVE_CURRENT_DATA) {
          try {
            ctx.drawImage(
              canvasVideo,
              0,
              0,
              compositeCanvas.width,
              compositeCanvas.height,
            );
          } catch (err) {
            console.error("Error drawing canvas video:", err);
          }
        }

        // Draw webcam (picture-in-picture in bottom-right)
        if (
          webcamVideo.readyState >= webcamVideo.HAVE_CURRENT_DATA &&
          layout === "picture-in-picture"
        ) {
          const pipWidth = 320;
          const pipHeight = 240;
          const padding = 20;
          const x = compositeCanvas.width - pipWidth - padding;
          const y = compositeCanvas.height - pipHeight - padding;

          try {
            // Draw border/shadow for depth
            ctx.fillStyle = "rgba(0, 0, 0, 0.3)";
            ctx.fillRect(x - 2, y - 2, pipWidth + 4, pipHeight + 4);

            // Draw webcam
            ctx.drawImage(webcamVideo, x, y, pipWidth, pipHeight);

            // Draw subtle border around webcam
            ctx.strokeStyle = "rgba(255, 255, 255, 0.8)";
            ctx.lineWidth = 2;
            ctx.strokeRect(x, y, pipWidth, pipHeight);
          } catch (err) {
            console.error("Error drawing webcam video:", err);
          }
        }

        animationFrameRef.current = requestAnimationFrame(draw);
      };

      draw();

      // Capture stream from composite canvas
      const stream = compositeCanvas.captureStream(30);
      console.log(
        "✅ Composite video stream created:",
        stream.getVideoTracks().length,
        "video tracks",
      );
      setCompositeStream(stream);
    };

    // Wait for both videos to be ready
    let canvasReady = false;
    let webcamReady = false;

    const checkReady = () => {
      if (
        (!canvasStream || canvasReady) &&
        (!webcamStream || webcamReady)
      ) {
        startCompositing();
      }
    };

    if (canvasStream) {
      canvasVideo.onloadeddata = () => {
        canvasReady = true;
        console.log("Canvas video loaded");
        checkReady();
      };
    } else {
      canvasReady = true;
    }

    if (webcamStream) {
      webcamVideo.onloadeddata = () => {
        webcamReady = true;
        checkReady();
      };

      // Also try onloadedmetadata as backup
      webcamVideo.onloadedmetadata = () => {
        if (!webcamReady) {
          webcamReady = true;
          checkReady();
        }
      };
    } else {
      webcamReady = true;
    }

    // Fallback timeout - increased to 5 seconds
    setTimeout(() => {
      if (!compositeStream) {
        console.warn("⚠️ Video timeout - starting composite anyway");
        startCompositing();
      }
    }, 5000);

    return () => {
      stopCompositing();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canvasStream, webcamStream, layout, stopCompositing]);

  return compositeStream;
}
