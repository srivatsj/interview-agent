import { useRef, useCallback } from "react";

/**
 * Hook to mix candidate microphone audio with agent playback audio
 * for recording purposes.
 */
export function useAudioMixer() {
  const audioContextRef = useRef<AudioContext | null>(null);
  const destinationRef = useRef<MediaStreamAudioDestinationNode | null>(null);
  const micSourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const agentSourceRef = useRef<MediaStreamAudioSourceNode | null>(null);

  /**
   * Initialize the audio mixer and return a mixed MediaStream
   * @param candidateMicStream - The candidate's microphone stream
   * @param agentAudioStream - The agent's audio playback stream (if available)
   * @returns Mixed audio stream containing both candidate and agent audio
   */
  const createMixedStream = useCallback(
    async (
      candidateMicStream: MediaStream,
      agentAudioStream?: MediaStream,
    ): Promise<MediaStream> => {
      try {
        // Create audio context if it doesn't exist
        if (!audioContextRef.current) {
          audioContextRef.current = new AudioContext();
        }
        const audioCtx = audioContextRef.current;

        if (audioCtx.state === "suspended") {
          await audioCtx.resume();
        }

        // Create destination for mixed audio
        destinationRef.current = audioCtx.createMediaStreamDestination();

        // Connect candidate microphone
        micSourceRef.current =
          audioCtx.createMediaStreamSource(candidateMicStream);
        micSourceRef.current.connect(destinationRef.current);
        console.log("🎙️ Audio Mixer: Connected candidate microphone");

        // Connect agent audio if available
        if (agentAudioStream) {
          agentSourceRef.current =
            audioCtx.createMediaStreamSource(agentAudioStream);
          agentSourceRef.current.connect(destinationRef.current);
          console.log("🔊 Audio Mixer: Connected agent audio");
        }

        console.log("✅ Audio Mixer: Mixed stream created");
        return destinationRef.current.stream;
      } catch (error) {
        console.error("Failed to create mixed audio stream:", error);
        throw error;
      }
    },
    [],
  );

  /**
   * Add or update the agent audio source
   * Call this when agent starts speaking
   */
  const addAgentAudio = useCallback((agentAudioStream: MediaStream) => {
    if (!audioContextRef.current || !destinationRef.current) {
      console.warn("Audio mixer not initialized");
      return;
    }

    // Disconnect existing agent source if any
    if (agentSourceRef.current) {
      agentSourceRef.current.disconnect();
    }

    // Connect new agent audio
    agentSourceRef.current =
      audioContextRef.current.createMediaStreamSource(agentAudioStream);
    agentSourceRef.current.connect(destinationRef.current);
    console.log("🔊 Audio Mixer: Agent audio source updated");
  }, []);

  /**
   * Clean up audio mixer resources
   */
  const cleanup = useCallback(() => {
    if (micSourceRef.current) {
      micSourceRef.current.disconnect();
      micSourceRef.current = null;
    }

    if (agentSourceRef.current) {
      agentSourceRef.current.disconnect();
      agentSourceRef.current = null;
    }

    if (destinationRef.current) {
      destinationRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    console.log("🧹 Audio Mixer: Cleaned up");
  }, []);

  return {
    createMixedStream,
    addAgentAudio,
    cleanup,
  };
}
