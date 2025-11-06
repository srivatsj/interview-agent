'use client';

import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Video, VideoOff } from 'lucide-react';
import { useWebcam } from '@/modules/interview/common/hooks/use-webcam';
import { authClient } from '@/lib/auth-client';

export function CandidateVideo() {
  const { videoRef, isEnabled, error, toggleVideo } = useWebcam();
  const { data: session } = authClient.useSession();

  const getFirstName = (name?: string) => {
    if (!name) return 'Candidate';
    return name.split(' ')[0];
  };

  return (
    <div className="relative aspect-video bg-slate-900 rounded-lg overflow-hidden">
      {/* Video stream */}
      {!error ? (
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="absolute inset-0 w-full h-full object-cover"
        />
      ) : (
        <div className="absolute inset-0 flex items-center justify-center">
          <Avatar className="h-24 w-24">
            <AvatarFallback className="bg-slate-700 text-white text-2xl">
              {getFirstName(session?.user?.name).slice(0, 2).toUpperCase()}
            </AvatarFallback>
          </Avatar>
        </div>
      )}

      {/* Controls overlay */}
      <div className="absolute bottom-3 left-3 flex gap-2">
        <button
          onClick={toggleVideo}
          className="p-2 rounded-full bg-slate-800/80 hover:bg-slate-700 text-white"
        >
          {isEnabled ? <Video className="h-4 w-4" /> : <VideoOff className="h-4 w-4" />}
        </button>
      </div>

      {/* Label */}
      <div className="absolute top-3 left-3">
        <span className="text-xs bg-slate-800/80 text-white px-2 py-1 rounded">
          {getFirstName(session?.user?.name)}
        </span>
      </div>
    </div>
  );
}
