'use client';

import { Clock, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export function InterviewHeader() {
  return (
    <div className="h-16 border-b bg-gradient-to-r from-[hsl(180,50%,35%)] to-[hsl(180,55%,25%)] px-6 flex items-center justify-between">
      {/* Left: Interview info */}
      <div className="flex items-center gap-4">
        <div>
          <h1 className="text-lg font-semibold text-white">
            System Design Interview
          </h1>
          <p className="text-sm text-white/80">URL Shortening Service</p>
        </div>
        <Badge variant="secondary" className="bg-white/20 text-white border-white/30">
          Design Phase
        </Badge>
      </div>

      {/* Right: Timer and controls */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-white/90">
          <Clock className="h-4 w-4" />
          <span className="text-sm font-mono">42:18</span>
        </div>
        <Button variant="ghost" size="icon" className="text-white hover:bg-white/10">
          <Settings className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
