"use client";

import { InterviewDetail } from "@/modules/completed-interviews/actions";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Calendar, Clock, ArrowLeft } from "lucide-react";
import Link from "next/link";
import dynamic from "next/dynamic";

// Dynamically import the readonly Excalidraw to avoid SSR issues
const DynamicReadonlyExcalidraw = dynamic(
  () =>
    import("../components/readonly-excalidraw").then(
      (mod) => mod.ReadonlyExcalidraw,
    ),
  { ssr: false },
);

interface InterviewDetailViewProps {
  interview: InterviewDetail;
}

export const InterviewDetailView = ({
  interview,
}: InterviewDetailViewProps) => {
  const formatDuration = (seconds: number | null) => {
    if (!seconds) return "N/A";
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  const formatDate = (date: Date | null) => {
    if (!date) return "N/A";
    return new Date(date).toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/interviews">
                <ArrowLeft className="mr-2 size-4" />
                Back to List
              </Link>
            </Button>
          </div>
          <h1 className="text-3xl font-bold">
            {interview.company || "Practice"} •{" "}
            {interview.role || "Software Engineer"}
          </h1>
          <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
            <div>
              {interview.interviewType === "system_design"
                ? "System Design"
                : interview.interviewType === "coding"
                  ? "Coding"
                  : "Interview"}{" "}
              • {interview.level || "Senior"}
            </div>
            <div className="flex items-center gap-1">
              <Calendar className="size-4" />
              <span>{formatDate(interview.completedAt)}</span>
            </div>
            <div className="flex items-center gap-1">
              <Clock className="size-4" />
              <span>{formatDuration(interview.durationSeconds)}</span>
            </div>
          </div>
        </div>
        <Badge
          variant="outline"
          className="bg-green-50 text-green-700 border-green-200"
        >
          Completed
        </Badge>
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column - Video & Canvas */}
        <div className="space-y-6">
          {/* Video Recording */}
          {interview.videoUrl && (
            <Card className="border-primary/20">
              <CardHeader className="bg-gradient-to-r from-primary/5 to-primary/10">
                <CardTitle className="text-lg">Interview Recording</CardTitle>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="w-full aspect-video bg-black rounded-lg overflow-hidden">
                  <video
                    src={interview.videoUrl}
                    controls
                    className="w-full h-full"
                    preload="metadata"
                  >
                    Your browser does not support the video tag.
                  </video>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Canvas State */}
          {interview.canvasState && (
            <Card className="border-primary/20">
              <CardHeader className="bg-gradient-to-r from-primary/5 to-primary/10">
                <CardTitle className="text-lg">Design Canvas</CardTitle>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="h-[500px]">
                  <DynamicReadonlyExcalidraw
                    elements={interview.canvasState.elements}
                    appState={interview.canvasState.appState}
                  />
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Column - Transcription */}
        <div>
          <Card className="border-primary/20 h-full">
            <CardHeader className="bg-gradient-to-r from-primary/5 to-primary/10 sticky top-0 z-10">
              <CardTitle className="text-lg">
                Interview Transcript ({interview.transcriptions.length}{" "}
                messages)
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6">
              {interview.transcriptions.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <p>No transcription available for this interview.</p>
                </div>
              ) : (
                <div className="space-y-3 max-h-[calc(100vh-12rem)] overflow-y-auto pr-2">
                  {interview.transcriptions.map((trans, index) => (
                    <div
                      key={`${trans.event_id}-${index}`}
                      className={`border rounded-lg p-3 ${
                        trans.role === "user"
                          ? "bg-blue-50 border-blue-200"
                          : "bg-green-50 border-green-200"
                      }`}
                    >
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-2 py-1 text-xs font-semibold rounded ${
                              trans.role === "user"
                                ? "bg-blue-200 text-blue-800"
                                : "bg-green-200 text-green-800"
                            }`}
                          >
                            {trans.role === "user" ? "You" : "Interviewer"}
                          </span>
                          <span className="text-xs text-gray-500">
                            {trans.author}
                          </span>
                        </div>
                        <span className="text-xs text-gray-500">
                          {new Date(trans.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      <p className="text-sm text-gray-800 whitespace-pre-wrap">
                        {trans.content_text}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};
