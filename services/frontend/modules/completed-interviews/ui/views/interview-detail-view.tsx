"use client";

import { InterviewDetail } from "@/modules/completed-interviews/actions";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  Calendar,
  Clock,
  ArrowLeft,
  MessageSquare,
  FileText,
  PenTool,
  DollarSign,
  Play,
  Brain,
  User,
  Bot,
} from "lucide-react";
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

  const formatPrice = (cents: number | null | undefined) => {
    if (!cents) return "N/A";
    const dollars = cents / 100;
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(dollars);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild className="-ml-2 text-muted-foreground hover:text-foreground">
              <Link href="/interviews">
                <ArrowLeft className="mr-2 size-4" />
                Back to List
              </Link>
            </Button>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">
            {interview.company || "Practice"} <span className="text-muted-foreground font-normal">•</span> {interview.role || "Software Engineer"}
          </h1>
          <div className="flex flex-wrap gap-4 text-sm text-muted-foreground items-center">
            <Badge variant="secondary" className="rounded-md">
              {interview.interviewType === "system_design"
                ? "System Design"
                : interview.interviewType === "coding"
                  ? "Coding"
                  : "Interview"}
            </Badge>
            <span className="text-xs">•</span>
            <span>{interview.level || "Senior"}</span>
            <span className="text-xs">•</span>
            <div className="flex items-center gap-1.5">
              <Calendar className="size-3.5" />
              <span>{formatDate(interview.completedAt)}</span>
            </div>
            <span className="text-xs">•</span>
            <div className="flex items-center gap-1.5">
              <Clock className="size-3.5" />
              <span>{formatDuration(interview.durationSeconds)}</span>
            </div>
            {interview.payment && (
              <>
                <span className="text-xs">•</span>
                <div className="flex items-center gap-1.5">
                  <DollarSign className="size-3.5" />
                  <span>{formatPrice(interview.payment.amountCents)}</span>
                  {interview.payment.status !== "completed" && (
                    <Badge variant="outline" className="text-xs border-amber-200 text-amber-700 bg-amber-50 ml-1">
                      {interview.payment.status}
                    </Badge>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
        <Badge
          variant="outline"
          className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20 px-3 py-1 text-sm font-medium self-start md:self-center"
        >
          Completed
        </Badge>
      </div>

      {/* Tabs Layout */}
      <Tabs defaultValue="feedback" className="w-full">
        <TabsList className="w-full justify-start h-auto p-1 bg-muted/40 space-x-2 rounded-xl mb-6">
          <TabsTrigger
            value="feedback"
            className="gap-2 rounded-lg px-4 py-2.5 font-medium text-muted-foreground data-[state=active]:bg-white dark:data-[state=active]:bg-slate-800 data-[state=active]:text-primary data-[state=active]:shadow-sm transition-all"
          >
            <MessageSquare className="size-4" />
            Feedback
          </TabsTrigger>
          <TabsTrigger
            value="artifacts"
            className="gap-2 rounded-lg px-4 py-2.5 font-medium text-muted-foreground data-[state=active]:bg-white dark:data-[state=active]:bg-slate-800 data-[state=active]:text-primary data-[state=active]:shadow-sm transition-all"
          >
            <PenTool className="size-4" />
            Artifacts
          </TabsTrigger>
          <TabsTrigger
            value="transcription"
            className="gap-2 rounded-lg px-4 py-2.5 font-medium text-muted-foreground data-[state=active]:bg-white dark:data-[state=active]:bg-slate-800 data-[state=active]:text-primary data-[state=active]:shadow-sm transition-all"
          >
            <FileText className="size-4" />
            Transcription
          </TabsTrigger>
        </TabsList>

        {/* Feedback Tab */}
        <TabsContent value="feedback" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[500px]">
            {/* Video Recording */}
            {interview.videoUrl && (
              <Card className="overflow-hidden border-border/50 shadow-sm h-full flex flex-col">
                <CardHeader className="bg-muted/30 border-b border-border/50 pb-4 flex-shrink-0">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <div className="size-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                      <Play className="size-4" />
                    </div>
                    Recording
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-0 flex-1 bg-black relative">
                  <video
                    src={interview.videoUrl}
                    controls
                    className="absolute inset-0 w-full h-full object-contain"
                    preload="metadata"
                  >
                    Your browser does not support the video tag.
                  </video>
                </CardContent>
              </Card>
            )}

            {/* Feedback Section */}
            <Card className="border-border/50 shadow-sm h-full flex flex-col">
              <CardHeader className="bg-muted/30 border-b border-border/50 pb-4 flex-shrink-0">
                <CardTitle className="text-lg flex items-center gap-2">
                  <div className="size-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                    <MessageSquare className="size-4" />
                  </div>
                  Analysis
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6 flex items-center justify-center flex-1">
                <div className="text-center max-w-xs mx-auto space-y-4">
                  <div className="size-16 rounded-full bg-muted flex items-center justify-center mx-auto">
                    <Brain className="size-8 text-muted-foreground/50" />
                  </div>
                  <div className="space-y-2">
                    <h3 className="text-lg font-medium">AI Analysis in Progress</h3>
                    <p className="text-sm text-muted-foreground">
                      Our agents are analyzing your performance. Detailed feedback will appear here shortly.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Artifacts Tab */}
        <TabsContent value="artifacts">
          {/* Canvas State */}
          {interview.canvasState ? (
            <Card className="overflow-hidden border-border/50 shadow-sm">
              <CardHeader className="bg-muted/30 border-b border-border/50 pb-4">
                <CardTitle className="text-lg flex items-center gap-2">
                  <div className="size-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                    <PenTool className="size-4" />
                  </div>
                  Whiteboard
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="h-[700px] w-full">
                  <DynamicReadonlyExcalidraw
                    elements={interview.canvasState.elements}
                    appState={interview.canvasState.appState}
                  />
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card className="border-dashed">
              <CardContent className="pt-6">
                <div className="text-center py-12 text-muted-foreground space-y-3">
                  <PenTool className="size-12 mx-auto opacity-20" />
                  <p>No whiteboard artifacts for this session.</p>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Transcription Tab */}
        <TabsContent value="transcription">
          <Card className="overflow-hidden border-border/50 shadow-sm">
            <CardHeader className="bg-muted/30 border-b border-border/50 pb-4">
              <CardTitle className="text-lg flex items-center gap-2">
                <div className="size-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                  <FileText className="size-4" />
                </div>
                Transcript
                <Badge variant="secondary" className="ml-2 text-xs font-normal">
                  {interview.transcriptions.length} messages
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {interview.transcriptions.length === 0 ? (
                <div className="text-center py-24 text-muted-foreground space-y-4">
                  <div className="size-16 rounded-full bg-muted flex items-center justify-center mx-auto">
                    <FileText className="size-8 text-muted-foreground/40" />
                  </div>
                  <p>No transcription available.</p>
                </div>
              ) : (
                <div className="flex flex-col gap-6 p-6 max-h-[800px] overflow-y-auto bg-slate-50/50 dark:bg-black/20">
                  {interview.transcriptions.map((trans, index) => {
                    const isUser = trans.role === "user";
                    return (
                      <div
                        key={`${trans.event_id}-${index}`}
                        className={`flex gap-4 ${isUser ? "flex-row-reverse" : "flex-row"} animate-in slide-in-from-bottom-2 fade-in duration-300`}
                        style={{ animationDelay: `${index * 50}ms` }}
                      >
                        {/* Avatar */}
                        <div className={`flex-shrink-0 size-8 rounded-full flex items-center justify-center shadow-sm ${isUser
                          ? "bg-gradient-to-br from-primary to-primary/80 text-primary-foreground"
                          : "bg-white dark:bg-slate-800 border border-border"
                          }`}>
                          {isUser ? (
                            <User className="size-4" />
                          ) : (
                            <Bot className="size-4 text-primary" />
                          )}
                        </div>

                        {/* Message Bubble */}
                        <div className={`flex flex-col max-w-[80%] ${isUser ? "items-end" : "items-start"}`}>
                          <div className="flex items-center gap-2 mb-1 px-1">
                            <span className="text-xs font-medium text-muted-foreground">
                              {isUser ? "You" : "Interviewer"}
                            </span>
                            <span className="text-[10px] text-muted-foreground/60">
                              {new Date(trans.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          </div>
                          <div
                            className={`rounded-2xl px-5 py-3 text-sm shadow-sm leading-relaxed ${isUser
                              ? "bg-gradient-to-br from-primary to-primary/90 text-primary-foreground rounded-tr-sm shadow-md"
                              : "bg-white dark:bg-slate-800 border border-border/50 text-foreground rounded-tl-sm"
                              }`}
                          >
                            <p className="whitespace-pre-wrap">{trans.content_text}</p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};
