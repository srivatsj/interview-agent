"use client";

import { CandidateVideo } from "@/modules/interview/common/ui/components/candidate-video";
import { AIAvatar } from "@/modules/interview/common/ui/components/ai-avatar";

export function VideoPanel() {
  return (
    <div className="h-full flex flex-col bg-slate-50 border-l">
      {/* Video feeds */}
      <div className="p-4 space-y-4">
        <CandidateVideo />
        <AIAvatar />
      </div>
    </div>
  );
}
