'use client';

import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Mic, MicOff, Video, VideoOff } from 'lucide-react';

export function CandidateVideo() {
  return (
    <div className="relative aspect-video bg-slate-900 rounded-lg overflow-hidden">
      {/* Video placeholder */}
      <div className="absolute inset-0 flex items-center justify-center">
        <Avatar className="h-24 w-24">
          <AvatarFallback className="bg-slate-700 text-white text-2xl">
            You
          </AvatarFallback>
        </Avatar>
      </div>

      {/* Controls overlay */}
      <div className="absolute bottom-3 left-3 flex gap-2">
        <button className="p-2 rounded-full bg-slate-800/80 hover:bg-slate-700 text-white">
          <Mic className="h-4 w-4" />
        </button>
        <button className="p-2 rounded-full bg-slate-800/80 hover:bg-slate-700 text-white">
          <Video className="h-4 w-4" />
        </button>
      </div>

      {/* Label */}
      <div className="absolute top-3 left-3">
        <span className="text-xs bg-slate-800/80 text-white px-2 py-1 rounded">
          Candidate
        </span>
      </div>
    </div>
  );
}
