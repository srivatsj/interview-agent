import { useState, useCallback } from "react";

interface Toast {
  title?: string;
  description?: string;
  variant?: "default" | "destructive";
}

export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback((toast: Toast) => {
    // Simple console-based toast for now (can be enhanced with UI later)
    if (toast.variant === "destructive") {
      console.error(`[Toast] ${toast.title}: ${toast.description}`);
    } else {
      console.log(`[Toast] ${toast.title}: ${toast.description}`);
    }

    setToasts((prev) => [...prev, toast]);

    // Auto-dismiss after 3 seconds
    setTimeout(() => {
      setToasts((prev) => prev.slice(1));
    }, 3000);
  }, []);

  return { toast, toasts };
}
