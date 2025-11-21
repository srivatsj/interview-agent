"use client";

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { InterviewHeader } from "@/modules/interview/common/ui/components/interview-header";
import { VideoPanel } from "@/modules/interview/common/ui/components/video-panel";
import { ExcalidrawCanvas } from "@/modules/interview/system-design/ui/components/excalidraw-canvas";
import { CodeEditorCanvas } from "@/modules/interview/coding/ui/components/code-editor-canvas";
import { useTimer } from "@/modules/interview/common/hooks/use-timer";
import {
  useWebSocket,
  type StructuredAgentEvent,
  type WebSocketMessage,
} from "@/modules/interview/common/hooks/use-websocket";
import { useConfirmation } from "@/modules/interview/common/ui/views/use-confirmation";
import { ConfirmationDialog } from "@/modules/interview/common/ui/components/confirmation-dialog";
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
import type { editor } from "monaco-editor";
import { updateInterview, getInterviewWithCanvas } from "@/modules/interview/actions";
import { authClient } from "@/lib/auth-client";
import { Layout, Code } from "lucide-react";

export function UnifiedInterview() {
  const router = useRouter();
  const params = useParams();
  const [excalidrawAPI, setExcalidrawAPI] = useState<ExcalidrawImperativeAPI | null>(null);
  const [editorInstance, setEditorInstance] = useState<editor.IStandaloneCodeEditor | null>(null);
  const [isEndingInterview, setIsEndingInterview] = useState(false);
  const [webcamStream, setWebcamStream] = useState<MediaStream | null>(null);
  const [activeTab, setActiveTab] = useState<string>("whiteboard");
  const [initialCode, setInitialCode] = useState<string | undefined>(undefined);
  const [language, setLanguage] = useState<string>("javascript");
  const [isReadOnly, setIsReadOnly] = useState(false);

  // Get interview ID from URL params
  const interviewId = params.interviewId as string;
  const hasConnectedRef = useRef(false);
  const hasInitializedAudioRef = useRef(false);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const isConnectedRef = useRef(false);

  // Get authenticated user for session persistence
  const { data: session } = authClient.useSession();
  const userId = session?.user?.id || interviewId;

  const { formattedTime } = useTimer();

  // Initialize AudioWorklet player
  const { initializePlayer, playAudio, flush, getAudioStream } = useAudioWorkletPlayer();

  // WebSocket connection
  const websocketUrl = useMemo(
    () => `ws://localhost:8000/ws/${userId}?interview_id=${interviewId}&is_audio=true`,
    [userId, interviewId],
  );

  // Handle incoming structured messages from WebSocket
  const handleBaseAgentEvent = useCallback(
    (event: StructuredAgentEvent) => {
      if (event.interrupted) {
        flush();
        return;
      }

      if (event.turn_complete) {
        return;
      }

      for (const part of event.parts) {
        if (part.type === "audio/pcm" && typeof part.data === "string") {
          playAudio(part.data);
        }
      }
    },
    [playAudio, flush],
  );

  // WebSocket sendMessage ref for confirmation hook
  const sendMessageRef = useRef<((message: WebSocketMessage) => boolean) | null>(null);

  // Confirmation hook
  const {
    confirmationRequest,
    isConfirmationOpen,
    handleStateUpdate,
    handleApprove,
    handleDecline,
  } = useConfirmation({
    sendMessage: sendMessageRef.current || undefined,
  });

  // WebSocket configuration
  const { isConnected, sendMessage, connect, disconnect } = useWebSocket({
    url: websocketUrl,
    onMessage: handleBaseAgentEvent,
    onStateUpdate: handleStateUpdate,
    onConnect: () => {
      isConnectedRef.current = true;
      initializeAudio();
    },
    onDisconnect: () => {
      isConnectedRef.current = false;
    },
    onError: (error) => console.error("WebSocket error:", error),
    autoConnect: false,
  });

  useEffect(() => {
    sendMessageRef.current = sendMessage;
  }, [sendMessage]);

  // Send audio data to WebSocket
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

  // Handle speech start
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

  // Composite video stream
  const compositeVideoStream = useCompositeVideo({
    canvasStream,
    webcamStream,
    layout: "picture-in-picture",
  });

  const mixedStreamRef = useRef<MediaStream | null>(null);

  // Canvas screenshot hook
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

  useCanvasScreenshot(excalidrawAPI, {
    onScreenshot: handleCanvasScreenshot,
    intervalMs: 30000,
  });

  // Handle ending interview
  const handleEndInterview = useCallback(async () => {
    setIsEndingInterview(true);

    try {
      console.log("🔌 Disconnecting WebSocket...");
      disconnect();

      const recordingBlob = await stopScreenRecording();

      if (recordingBlob) {
        await uploadRecording(interviewId, recordingBlob);
      }

      // Save both canvas states
      const canvasStateData: {
        elements: unknown[];
        appState?: Record<string, unknown>;
      } = {
        elements: [],
        appState: {},
      };

      // Save Excalidraw state
      if (excalidrawAPI) {
        try {
          const elements = [...excalidrawAPI.getSceneElements()];
          const appState = excalidrawAPI.getAppState();
          canvasStateData.elements.push({
            type: "excalidraw",
            elements,
          });
          if (!canvasStateData.appState) canvasStateData.appState = {};
          canvasStateData.appState.excalidraw = appState;
        } catch (error) {
          console.error("Failed to save excalidraw state:", error);
        }
      }

      // Save code editor state
      if (editorInstance) {
        try {
          const code = editorInstance.getValue();
          const editorLanguage = editorInstance.getModel()?.getLanguageId() || "javascript";
          canvasStateData.elements.push({
            type: "code",
            code,
            language: editorLanguage,
          });
          if (!canvasStateData.appState) canvasStateData.appState = {};
          canvasStateData.appState.codeLanguage = editorLanguage;
        } catch (error) {
          console.error("Failed to save code state:", error);
        }
      }

      // Update interview with canvas state
      await updateInterview({
        interviewId,
        canvasState: canvasStateData,
      });

      // Cleanup resources
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      }
      if (webcamStream) {
        webcamStream.getTracks().forEach((track) => track.stop());
      }
      stopRecording();
      cleanupMixer();
      cleanupRecorder();

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
    excalidrawAPI,
    editorInstance,
    stopRecording,
    cleanupMixer,
    cleanupRecorder,
    router,
    webcamStream,
  ]);

  // Initialize audio
  const initializeAudio = useCallback(async () => {
    if (hasInitializedAudioRef.current) return;

    try {
      await initializePlayer();

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: "user",
        },
      });

      mediaStreamRef.current = stream;
      setWebcamStream(stream);

      await startRecording(stream);

      const agentAudioStream = getAudioStream();

      const mixedStream = await createMixedStream(
        stream,
        agentAudioStream || undefined,
      );
      mixedStreamRef.current = mixedStream;

      hasInitializedAudioRef.current = true;
    } catch {
      console.error("Failed to initialize audio");
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

  // Initialize interview
  useEffect(() => {
    let mounted = true;

    const initializeInterview = async () => {
      if (!mounted) return;

      if (!interviewId) {
        console.error("❌ No interview ID provided");
        router.push("/");
        return;
      }

      const interviewData = await getInterviewWithCanvas(interviewId);
      if (!interviewData) {
        console.error(`❌ Interview not found: ${interviewId}`);
        alert("Invalid interview ID. Please start a new interview.");
        router.push("/");
        return;
      }

      const isCompleted = interviewData.status === "completed";
      setIsReadOnly(isCompleted);

      // Load saved states if available
      if (interviewData.canvasState) {
        const elements = interviewData.canvasState.elements as Array<{
          type: string;
          code?: string;
          language?: string;
          elements?: unknown[];
        }>;

        const codeElement = elements.find((el) => el.type === "code");
        if (codeElement && codeElement.code) {
          setInitialCode(codeElement.code);
          setLanguage(codeElement.language || "javascript");
        }
      }

      if (!isCompleted && !hasConnectedRef.current && mounted) {
        hasConnectedRef.current = true;
        connect();
      }
    };

    initializeInterview();

    return () => {
      mounted = false;
      if (hasConnectedRef.current) {
        disconnect();
        hasConnectedRef.current = false;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

      <ConfirmationDialog
        open={isConfirmationOpen}
        request={confirmationRequest}
        onApprove={handleApprove}
        onDecline={handleDecline}
      />

      <ResizablePanelGroup
        direction="horizontal"
        className="flex-1 overflow-hidden"
      >
        <ResizablePanel
          defaultSize={70}
          minSize={50}
          className="overflow-hidden"
        >
          <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
            <TabsList className="w-full justify-start h-auto p-1 bg-secondary/20 rounded-none border-b flex-shrink-0">
              <TabsTrigger
                value="whiteboard"
                className="gap-2 rounded-md px-4 py-2 font-medium text-muted-foreground data-[state=active]:bg-secondary data-[state=active]:text-secondary-foreground data-[state=active]:shadow-sm"
              >
                <Layout className="size-4" />
                Whiteboard
              </TabsTrigger>
              <TabsTrigger
                value="code"
                className="gap-2 rounded-md px-4 py-2 font-medium text-muted-foreground data-[state=active]:bg-secondary data-[state=active]:text-secondary-foreground data-[state=active]:shadow-sm"
              >
                <Code className="size-4" />
                Code Editor
              </TabsTrigger>
            </TabsList>

            <div className="flex-1 relative">
              <TabsContent value="whiteboard" className="absolute inset-0 m-0 p-0" forceMount>
                <div className={activeTab !== "whiteboard" ? "hidden" : "h-full w-full"}>
                  <ExcalidrawCanvas onExcalidrawAPIInit={setExcalidrawAPI} />
                </div>
              </TabsContent>

              <TabsContent value="code" className="absolute inset-0 m-0 p-0" forceMount>
                <div className={activeTab !== "code" ? "hidden" : "h-full w-full"}>
                  <CodeEditorCanvas
                    onEditorInit={setEditorInstance}
                    initialCode={initialCode}
                    language={language}
                    readOnly={isReadOnly}
                  />
                </div>
              </TabsContent>
            </div>
          </Tabs>
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
