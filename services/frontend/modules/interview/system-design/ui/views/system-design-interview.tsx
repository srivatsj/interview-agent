"use client";

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { InterviewHeader } from "@/modules/interview/common/ui/components/interview-header";
import { VideoPanel } from "@/modules/interview/common/ui/components/video-panel";
import { ExcalidrawCanvas } from "../components/excalidraw-canvas";
import { useTimer } from "@/modules/interview/common/hooks/use-timer";
import {
  useWebSocket,
  type StructuredAgentEvent,
} from "@/modules/interview/common/hooks/use-websocket";
import { useAudioWorkletRecorder } from "@/modules/interview/common/hooks/use-audio-worklet-recorder";
import { useAudioWorkletPlayer } from "@/modules/interview/common/hooks/use-audio-worklet-player";
import { useAudioMixer } from "@/modules/interview/common/hooks/use-audio-mixer";
import { useScreenRecorder } from "@/modules/interview/common/hooks/use-screen-recorder";
import { useRecordingUpload } from "@/modules/interview/common/hooks/use-recording-upload";
import { useCanvasScreenshot } from "@/modules/interview/common/hooks/use-canvas-screenshot";
import { useCanvasStream } from "@/modules/interview/common/hooks/use-canvas-stream";
import { useCompositeVideo } from "@/modules/interview/common/hooks/use-composite-video";
import { useRouter, useParams } from "next/navigation";
import type { ExcalidrawImperativeAPI } from "@excalidraw/excalidraw/types";
import { validateInterviewExists } from "@/modules/interview/actions";
import { authClient } from "@/lib/auth-client";

export function SystemDesignInterview() {
  const router = useRouter();
  const params = useParams();
  const [excalidrawAPI, setExcalidrawAPI] =
    useState<ExcalidrawImperativeAPI | null>(null);
  const [isEndingInterview, setIsEndingInterview] = useState(false);
  const [webcamStream, setWebcamStream] = useState<MediaStream | null>(null);

  // Get interview ID from URL params
  const interviewId = params.interviewId as string;
  const hasConnectedRef = useRef(false);
  const hasInitializedAudioRef = useRef(false);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const isConnectedRef = useRef(false);

  // Get authenticated user for session persistence
  const { data: session } = authClient.useSession();
  const userId = session?.user?.id || interviewId; // Fallback to interviewId if no auth

  const { formattedTime } = useTimer();

  // Initialize AudioWorklet player
  const { initializePlayer, playAudio, flush, getAudioStream } =
    useAudioWorkletPlayer();

  // WebSocket connection - CRITICAL: is_audio=true for audio mode
  // Pass both user_id and interview_id for session management
  const websocketUrl = useMemo(
    () => `ws://localhost:8000/ws/${userId}?interview_id=${interviewId}&is_audio=true`,
    [userId, interviewId],
  );

  // Handle incoming structured messages from WebSocket
  const handleWebSocketMessage = useCallback(
    (event: StructuredAgentEvent) => {
      // Handle interruption - flush audio player
      if (event.interrupted) {
        flush();
        return;
      }

      // Handle turn completion
      if (event.turn_complete) {
        return;
      }

      // Process all parts in the event
      for (const part of event.parts) {
        if (part.type === "audio/pcm" && typeof part.data === "string") {
          // Play PCM audio using AudioWorklet
          playAudio(part.data);
        }
      }
    },
    [playAudio, flush],
  );

  // WebSocket configuration
  const { isConnected, sendMessage, connect, disconnect } = useWebSocket({
    url: websocketUrl,
    onMessage: handleWebSocketMessage,
    onConnect: () => {
      isConnectedRef.current = true;
      // Initialize audio after successful connection
      initializeAudio();
    },
    onDisconnect: () => {
      isConnectedRef.current = false;
    },
    onError: (error) => console.error("WebSocket error:", error),
    autoConnect: false,
  });

  // Send audio data to WebSocket (PCM format)
  const handleAudioData = useCallback(
    (base64Data: string) => {
      if (!isConnectedRef.current) {
        return;
      }

      sendMessage({
        mime_type: "audio/pcm",
        data: base64Data,
      });
    },
    [sendMessage],
  );

  // Handle speech start (for barge-in)
  const handleSpeechStart = useCallback(() => {
    flush();
  }, [flush]);

  // Setup AudioWorklet recorder
  const { startRecording, stopRecording } = useAudioWorkletRecorder({
    onAudioData: handleAudioData,
    onSpeechStart: handleSpeechStart,
  });

  // Recording hooks
  const { createMixedStream, cleanup: cleanupMixer } = useAudioMixer();
  const {
    isRecording,
    startRecording: startScreenRecording,
    stopRecording: stopScreenRecording,
    cleanup: cleanupRecorder,
  } = useScreenRecorder();
  const { uploadRecording } = useRecordingUpload();

  // Canvas stream for recording
  const canvasStream = useCanvasStream(excalidrawAPI);

  // Composite video stream (canvas + webcam picture-in-picture)
  const compositeVideoStream = useCompositeVideo({
    canvasStream,
    webcamStream,
    layout: "picture-in-picture",
  });

  const mixedStreamRef = useRef<MediaStream | null>(null);

  // Canvas screenshot hook - sends screenshots to orchestrator every 30s
  const blobToBase64 = useCallback((blob: Blob): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64 = (reader.result as string).split(",")[1];
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }, []);

  const handleCanvasScreenshot = useCallback(
    async (screenshot: { blob: Blob; timestamp: number }) => {
      if (!isConnectedRef.current) return;

      try {
        const base64 = await blobToBase64(screenshot.blob);
        sendMessage({
          mime_type: "image/png",
          data: base64,
        });
      } catch (error) {
        console.error("Failed to send canvas screenshot:", error);
      }
    },
    [blobToBase64, sendMessage],
  );

  // Initialize canvas screenshot hook (30s interval by default)
  useCanvasScreenshot(excalidrawAPI, {
    onScreenshot: handleCanvasScreenshot,
    intervalMs: 30000, // 30 seconds
  });

  // Handle ending interview - CRITICAL: Must complete upload before navigation
  const handleEndInterview = useCallback(async () => {
    setIsEndingInterview(true);

    try {
      // 1. Disconnect WebSocket - backend auto-syncs to database on disconnect
      console.log("🔌 Disconnecting WebSocket (backend will auto-sync session to DB)...");
      disconnect();

      // 2. Stop screen recording and get blob
      const recordingBlob = await stopScreenRecording();

      if (recordingBlob) {
        // 3. Upload recording - WAIT for completion
        await uploadRecording(interviewId, recordingBlob);
      }

      // 4. Cleanup audio/video resources
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      }
      if (webcamStream) {
        webcamStream.getTracks().forEach((track) => track.stop());
      }
      stopRecording();
      cleanupMixer();
      cleanupRecorder();

      // 5. Navigate to home AFTER upload completes
      router.push("/");
    } catch (error) {
      console.error("Failed to end interview:", error);
      alert("Failed to save recording. Please try again.");
      setIsEndingInterview(false);
    }
  }, [
    interviewId,
    disconnect,
    stopScreenRecording,
    uploadRecording,
    stopRecording,
    cleanupMixer,
    cleanupRecorder,
    router,
    webcamStream,
  ]);

  // Initialize audio (player and recorder)
  const initializeAudio = useCallback(async () => {
    if (hasInitializedAudioRef.current) return;

    try {
      // Initialize audio player first
      await initializePlayer();

      // Get microphone AND webcam stream (both audio and video)
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: "user",
        },
      });

      mediaStreamRef.current = stream;
      setWebcamStream(stream); // Set webcam stream for composite video

      // Start AudioWorklet recorder (uses audio tracks only)
      await startRecording(stream);

      // Get AI audio stream from player
      const agentAudioStream = getAudioStream();

      // Create mixed audio stream for recording (candidate mic + agent audio)
      const mixedStream = await createMixedStream(
        stream,
        agentAudioStream || undefined,
      );
      mixedStreamRef.current = mixedStream;

      hasInitializedAudioRef.current = true;
    } catch (error) {
      console.error("Failed to initialize audio:", error);
    }
  }, [
    initializePlayer,
    startRecording,
    createMixedStream,
    getAudioStream,
  ]);

  // Start recording once composite video is ready
  useEffect(() => {
    if (!hasInitializedAudioRef.current) return;
    if (isRecording) return;
    if (!compositeVideoStream) return;
    if (!mixedStreamRef.current) {
      console.error("⚠️ Mixed audio stream not ready");
      return;
    }

    console.log("🎬 Starting screen recording...");

    const startRecordingAsync = async () => {
      try {
        await startScreenRecording(
          mixedStreamRef.current || undefined,
          compositeVideoStream,
        );
        console.log("✅ Recording started successfully");
      } catch (error) {
        console.error("❌ Failed to start recording:", error);
      }
    };

    startRecordingAsync();
  }, [compositeVideoStream, isRecording, startScreenRecording]);

  // Initiate connection when component mounts - EXACTLY like original pattern
  useEffect(() => {
    let mounted = true;

    const initializeInterview = async () => {
      if (!mounted) return;

      if (!interviewId) {
        console.error("❌ No interview ID provided");
        router.push("/");
        return;
      }

      // Validate interview exists in database
      const exists = await validateInterviewExists(interviewId);
      if (!exists) {
        console.error(`❌ Interview not found: ${interviewId}`);
        alert("Invalid interview ID. Please start a new interview.");
        router.push("/");
        return;
      }

      if (!hasConnectedRef.current && mounted) {
        hasConnectedRef.current = true;
        connect();
      }
    };

    initializeInterview();

    return () => {
      mounted = false;
      // Prevent duplicate connections on remount
      if (hasConnectedRef.current) {
        disconnect();
        hasConnectedRef.current = false;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // ✅ EMPTY DEPS - exactly like original!

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden">
      <InterviewHeader
        elapsedTime={formattedTime}
        onEndInterview={handleEndInterview}
        isEndingInterview={isEndingInterview}
      />

      {!isConnected && (
        <div className="absolute top-20 left-1/2 -translate-x-1/2 bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-2 rounded-lg shadow-lg z-50">
          Connecting to interview server...
        </div>
      )}

      {isEndingInterview && (
        <div className="absolute top-20 left-1/2 -translate-x-1/2 bg-blue-100 border border-blue-400 text-blue-700 px-6 py-3 rounded-lg shadow-lg z-50">
          <div className="flex items-center gap-3">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-700"></div>
            <div>
              <div className="font-semibold">Ending Interview...</div>
              <div className="text-sm">Saving recording, please wait</div>
            </div>
          </div>
        </div>
      )}

      <ResizablePanelGroup
        direction="horizontal"
        className="flex-1 overflow-hidden"
      >
        <ResizablePanel
          defaultSize={70}
          minSize={50}
          className="overflow-hidden"
        >
          <ExcalidrawCanvas onExcalidrawAPIInit={setExcalidrawAPI} />
        </ResizablePanel>

        <ResizableHandle className="w-1 bg-slate-200 hover:bg-slate-300" />

        <ResizablePanel
          defaultSize={30}
          minSize={20}
          maxSize={40}
          className="overflow-hidden"
        >
          <VideoPanel />
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
}
