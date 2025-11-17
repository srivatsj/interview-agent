"use client";

import { CompletedInterview } from "@/modules/completed-interviews/actions";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Calendar, Clock, Video } from "lucide-react";
import Link from "next/link";

interface CompletedInterviewsListViewProps {
  interviews: CompletedInterview[];
}

export const CompletedInterviewsListView = ({
  interviews,
}: CompletedInterviewsListViewProps) => {
  const formatDuration = (seconds: number | null) => {
    if (!seconds) return "N/A";
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  const formatDate = (date: Date | null) => {
    if (!date) return "N/A";
    return new Date(date).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Completed Interviews</h1>
          <p className="text-muted-foreground mt-2">
            Review your past interviews and track your progress
          </p>
        </div>
        <Button asChild>
          <Link href="/">Back to Home</Link>
        </Button>
      </div>

      {interviews.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Video className="mb-4 size-12 text-muted-foreground/50" />
            <h3 className="mb-2 text-lg font-semibold">
              No completed interviews yet
            </h3>
            <p className="text-muted-foreground mb-4 text-center">
              Complete an interview to see it here
            </p>
            <Button asChild>
              <Link href="/interview-session/new">Start Your First Interview</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {interviews.map((interview) => (
            <Card
              key={interview.id}
              className="transition-all hover:shadow-lg hover:border-primary/20"
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="space-y-2">
                    <CardTitle className="text-xl">
                      {interview.company || "Practice"} •{" "}
                      {interview.role || "Software Engineer"}
                    </CardTitle>
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
              </CardHeader>
              <CardContent>
                <div className="flex gap-2">
                  <Button asChild className="flex-1">
                    <Link href={`/interviews/${interview.id}`}>
                      View Details
                    </Link>
                  </Button>
                  {interview.videoUrl && (
                    <Button variant="outline" asChild>
                      <a
                        href={interview.videoUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <Video className="mr-2 size-4" />
                        Watch Recording
                      </a>
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};
