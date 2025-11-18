import { useState, useCallback } from "react";
import type {
  SessionState,
  WebSocketMessage,
} from "@/modules/interview/common/hooks/use-websocket";

export interface ConfirmationRequest {
  id: string;
  company: string;
  interview_type: string;
  price: number;
}

export interface UseConfirmationOptions {
  sendMessage?: (message: WebSocketMessage) => boolean;
}

/**
 * Hook to handle payment confirmation requests from the agent.
 *
 * NEW FLOW (Blocking Tool Approach):
 * 1. Backend tool sets state.pending_confirmation and sends notification
 * 2. Tool blocks waiting for user response
 * 3. Frontend detects pending_confirmation in state
 * 4. Shows payment dialog
 * 5. User clicks approve/decline
 * 6. Frontend sends confirmation_response
 * 7. Tool unblocks and continues
 */
export function useConfirmation({ sendMessage }: UseConfirmationOptions) {
  const [confirmationRequest, setConfirmationRequest] = useState<ConfirmationRequest | null>(null);
  const [isConfirmationOpen, setIsConfirmationOpen] = useState(false);

  /**
   * Handle session state updates to detect confirmation requests.
   * Called when state_update message received or state changes in regular events.
   */
  const handleStateUpdate = useCallback((state: SessionState) => {
    // Check for pending payment confirmation
    if (state.pending_confirmation) {
      const { id, company, interview_type, price } = state.pending_confirmation;

      setConfirmationRequest({
        id,
        company,
        interview_type,
        price,
      });
      setIsConfirmationOpen(true);
    } else if (confirmationRequest && !state.pending_confirmation) {
      // Confirmation was cleared (completed or timed out)
      setIsConfirmationOpen(false);
      setConfirmationRequest(null);
    }
  }, [confirmationRequest]);

  /**
   * Send confirmation response to agent.
   * Uses new confirmation_response mime type format.
   */
  const sendConfirmationResponse = useCallback((approved: boolean) => {
    if (!confirmationRequest || !sendMessage) return;

    const responseData = {
      confirmation_id: confirmationRequest.id,
      approved,
    };

    const success = sendMessage({
      mime_type: "confirmation_response",
      data: JSON.stringify(responseData),
    });

    if (success) {
      setIsConfirmationOpen(false);
      setConfirmationRequest(null);
    } else {
      console.error("❌ Failed to send confirmation response");
    }
  }, [confirmationRequest, sendMessage]);

  const handleApprove = useCallback(() => {
    sendConfirmationResponse(true);
  }, [sendConfirmationResponse]);

  const handleDecline = useCallback(() => {
    sendConfirmationResponse(false);
  }, [sendConfirmationResponse]);

  return {
    confirmationRequest,
    isConfirmationOpen,
    handleStateUpdate, // NEW: Call this with session state updates
    handleApprove,
    handleDecline,
  };
}
