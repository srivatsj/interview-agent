import { useEffect, useRef, useState, useCallback } from "react";

// Message format for sending to backend
export interface WebSocketMessage {
  mime_type: "text/plain" | "audio/pcm" | "audio/webm" | "image/png";
  data: string; // Text content or base64-encoded data
}

// Event part structure matching working ADK sample
export interface EventPart {
  type: "text" | "audio/pcm" | "function_call" | "function_response";
  data: unknown;
}

// Transcription data structure
export interface TranscriptionData {
  text: string;
  is_final: boolean;
}

// Structured message format received from backend (matching working ADK sample)
export interface StructuredAgentEvent {
  author: string;
  is_partial: boolean;
  turn_complete: boolean;
  interrupted: boolean;
  parts: EventPart[];
  input_transcription?: TranscriptionData | null;
  output_transcription?: TranscriptionData | null;
}

export interface UseWebSocketOptions {
  url: string;
  onMessage?: (event: StructuredAgentEvent) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  autoConnect?: boolean;
}

export function useWebSocket({
  url,
  onMessage,
  onConnect,
  onDisconnect,
  onError,
  autoConnect = true,
}: UseWebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const maxReconnectAttempts = 5;
  const reconnectDelay = 2000;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        setIsConnected(true);
        setConnectionError(null);
        setReconnectAttempts(0);
        onConnect?.();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as StructuredAgentEvent;
          onMessage?.(data);
        } catch (error) {
          console.error("Failed to parse WebSocket message:", error);
        }
      };

      ws.onerror = (event) => {
        console.error("WebSocket error:", event);
        setConnectionError("WebSocket connection error");
        onError?.(event);
      };

      ws.onclose = () => {
        setIsConnected(false);
        wsRef.current = null;
        onDisconnect?.();

        // Auto-reconnect with exponential backoff
        if (autoConnect && reconnectAttempts < maxReconnectAttempts) {
          const delay = reconnectDelay * Math.pow(2, reconnectAttempts);
          reconnectTimeoutRef.current = setTimeout(() => {
            setReconnectAttempts((prev) => prev + 1);
            connect();
          }, delay);
        }
      };

      wsRef.current = ws;
    } catch {
      setConnectionError("Failed to create WebSocket connection");
    }
  }, [
    url,
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    autoConnect,
    reconnectAttempts,
    connect,
  ]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
  }, []);

  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return false;
    }

    try {
      const json = JSON.stringify(message);
      wsRef.current.send(json);
      return true;
    } catch (error) {
      console.error("Failed to send WebSocket message:", error);
      return false;
    }
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    // Don't disconnect on cleanup to avoid issues with React Strict Mode remounts
    // Users should manually call disconnect() when needed
    // return () => {
    //   disconnect();
    // };
  }, [autoConnect, connect]);

  return {
    isConnected,
    connectionError,
    connect,
    disconnect,
    sendMessage,
    reconnectAttempts,
  };
}
