import { useEffect, useRef, useState, useCallback } from "react";

// Message format for sending to backend
export interface WebSocketMessage {
  mime_type: "text/plain" | "audio/pcm" | "audio/webm" | "image/png" | "confirmation_response";
  data: string; // Text content or base64-encoded data
}

// Event part in agent response
interface EventPart {
  type: "audio/pcm" | "text" | "function_call" | "function_response";
  data: unknown;
}

// Session state from backend
export interface SessionState {
  pending_confirmation?: {
    id: string;
    company: string;
    interview_type: string;
    price: number;
  };
  routing_decision?: {
    company: string;
    interview_type: string;
    confidence: number;
  };
  interview_phase?: string;
  interview_id?: string;
  session_key?: string;
  [key: string]: unknown;
}

// Agent event from orchestrator
export interface StructuredAgentEvent {
  is_partial: boolean;
  turn_complete: boolean;
  interrupted: boolean;
  parts: EventPart[];
  state?: SessionState; // Session state included in every message
}

// State update notification (sent before tool blocks)
export interface StateUpdateMessage {
  type: "state_update";
  state: SessionState;
}

// Union type for all possible WebSocket messages
export type WebSocketIncomingMessage = StructuredAgentEvent | StateUpdateMessage;

export interface UseWebSocketOptions {
  url: string;
  onMessage?: (event: StructuredAgentEvent) => void;
  onStateUpdate?: (state: SessionState) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  autoConnect?: boolean;
}

export function useWebSocket({
  url,
  onMessage,
  onStateUpdate,
  onConnect,
  onDisconnect,
  onError,
  autoConnect = true,
}: UseWebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const connectRef = useRef<(() => void) | null>(null);

  const maxReconnectAttempts = 5;
  const reconnectDelay = 2000;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    // Don't try to connect with empty/invalid URL
    if (!url || url === "") {
      console.warn("⚠️ Cannot connect: URL is empty");
      return;
    }

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        setIsConnected(true);
        setConnectionError(null);
        reconnectAttemptsRef.current = 0;
        onConnect?.();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WebSocketIncomingMessage;

          // Handle state_update notification (sent before tool blocks)
          if ("type" in data && data.type === "state_update") {
            onStateUpdate?.(data.state);
            return;
          }

          // Handle regular structured agent events
          const structuredEvent = data as StructuredAgentEvent;

          // Check for state in regular events too (backup)
          if (structuredEvent.state) {
            onStateUpdate?.(structuredEvent.state);
          }

          onMessage?.(structuredEvent);
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
        if (autoConnect && reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = reconnectDelay * Math.pow(2, reconnectAttemptsRef.current);
          reconnectAttemptsRef.current += 1;
          reconnectTimeoutRef.current = setTimeout(() => {
            connectRef.current?.();
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
    onStateUpdate,
    onConnect,
    onDisconnect,
    onError,
    autoConnect,
  ]);

  // Store the latest connect function in a ref
  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

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
      // Defer connection to avoid synchronous setState in effect
      const timer = setTimeout(() => {
        connect();
      }, 0);
      return () => clearTimeout(timer);
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
  };
}
