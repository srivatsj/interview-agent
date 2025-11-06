import { useState, useEffect, useRef } from 'react';

export function useWebcam() {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [isEnabled, setIsEnabled] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    let currentStream: MediaStream | null = null;

    const startWebcam = async () => {
      try {
        const mediaStream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false,
        });

        currentStream = mediaStream;
        setStream(mediaStream);

        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream;
        }
      } catch (err) {
        setError('Failed to access webcam');
        console.error('Webcam error:', err);
      }
    };

    startWebcam();

    return () => {
      if (currentStream) {
        currentStream.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  const toggleVideo = () => {
    if (stream) {
      stream.getVideoTracks().forEach((track) => {
        track.enabled = !track.enabled;
      });
      setIsEnabled(!isEnabled);
    }
  };

  return {
    videoRef,
    stream,
    isEnabled,
    error,
    toggleVideo,
  };
}
