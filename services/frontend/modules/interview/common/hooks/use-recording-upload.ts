import { useState, useCallback } from "react";

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

export function useRecordingUpload() {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);

  /**
   * Upload recording blob to server
   * @param interviewId - Interview ID
   * @param recordingBlob - Recording blob to upload
   * @returns Promise that resolves with the uploaded video URL
   */
  const uploadRecording = useCallback(
    async (interviewId: string, recordingBlob: Blob): Promise<string> => {
      setIsUploading(true);
      setError(null);
      setUploadProgress({
        loaded: 0,
        total: recordingBlob.size,
        percentage: 0,
      });

      try {
        // Create form data
        const formData = new FormData();
        formData.append("recording", recordingBlob, `${interviewId}.webm`);

        // Upload with progress tracking
        const response = await fetch(
          `/api/interviews/${interviewId}/upload-recording`,
          {
            method: "POST",
            body: formData,
          },
        );

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || "Upload failed");
        }

        const data = await response.json();

        console.log("✅ Upload complete:", data.url);
        setUploadProgress({
          loaded: recordingBlob.size,
          total: recordingBlob.size,
          percentage: 100,
        });
        setIsUploading(false);

        return data.url;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Upload failed";
        console.error("Upload error:", errorMessage);
        setError(errorMessage);
        setIsUploading(false);
        throw err;
      }
    },
    [],
  );

  /**
   * Reset upload state
   */
  const reset = useCallback(() => {
    setIsUploading(false);
    setUploadProgress(null);
    setError(null);
  }, []);

  return {
    uploadRecording,
    isUploading,
    uploadProgress,
    error,
    reset,
  };
}
