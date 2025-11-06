'use client';

import { CandidateVideo } from './candidate-video';
import { AIAvatar } from './ai-avatar';
import { Button } from '@/components/ui/button';
import { PhoneOff } from 'lucide-react';

export function VideoPanel() {
  return (
    <div className="h-full flex flex-col bg-slate-50 border-l">
      {/* Video feeds */}
      <div className="p-4 space-y-4">
        <CandidateVideo />
        <AIAvatar />
      </div>

      {/* Controls */}
      <div className="p-4 border-t bg-white">
        <Button variant="destructive" className="w-full" size="lg">
          <PhoneOff className="mr-2 h-4 w-4" />
          End Interview
        </Button>
      </div>
    </div>
  );
}
