'use client';

import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Bot } from 'lucide-react';

export function AIAvatar() {
  return (
    <div className="relative aspect-video bg-gradient-to-br from-[hsl(180,50%,35%)] to-[hsl(180,55%,25%)] rounded-lg overflow-hidden">
      {/* AI Avatar */}
      <div className="absolute inset-0 flex items-center justify-center">
        <Avatar className="h-24 w-24">
          <AvatarFallback className="bg-[hsl(180,60%,45%)] text-white text-2xl">
            <Bot className="h-12 w-12" />
          </AvatarFallback>
        </Avatar>
      </div>

      {/* Speaking indicator */}
      <div className="absolute bottom-3 left-3">
        <div className="flex gap-1 items-center bg-slate-900/60 px-2 py-1 rounded">
          <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-xs text-white">Listening</span>
        </div>
      </div>

      {/* Label */}
      <div className="absolute top-3 left-3">
        <span className="text-xs bg-slate-900/60 text-white px-2 py-1 rounded">
          AI Interviewer
        </span>
      </div>
    </div>
  );
}
