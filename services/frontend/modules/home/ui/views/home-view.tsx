"use client";

import { Brain, ArrowRight, Play } from "lucide-react";
import Link from "next/link";
import { authClient } from "@/lib/auth-client";
import type { RecentInterview } from "@/modules/home/actions";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface HomeViewProps {
  recentInterviews: RecentInterview[];
}

export const HomeView = ({ recentInterviews }: HomeViewProps) => {
  const { data: session } = authClient.useSession();

  const getFirstName = (name?: string) => {
    if (!name) return "there";
    return name.split(" ")[0];
  };

  const formatDate = (date: Date | null) => {
    if (!date) return "N/A";
    const now = new Date();
    const diff = now.getTime() - new Date(date).getTime();
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (hours < 1) return "Just now";
    if (hours < 24) return `${hours} hour${hours > 1 ? "s" : ""} ago`;
    if (days === 1) return "Yesterday";
    if (days < 7) return `${days} days ago`;

    return new Date(date).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
  };

  return (
    <div className="space-y-6">
      {/* Greeting */}
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold">
            Hi {getFirstName(session?.user?.name)}! Ready to practice? 🚀
          </h1>
          <p className="text-muted-foreground">
            Start a new interview or review your recent activity
          </p>
        </div>
        <Button asChild className="btn-gradient text-white">
          <Link href="/interview-session/new">
            <Play className="mr-2 size-4" />
            Start Interview
          </Link>
        </Button>
      </div>

      {/* Recent Activity */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Recent Activity</h2>
          <Button variant="ghost" size="sm" asChild>
            <Link href="/interviews">
              View All
              <ArrowRight className="ml-2 size-4" />
            </Link>
          </Button>
        </div>

        <div className="space-y-3">
          {recentInterviews.map((interview) => (
            <Card
              key={interview.id}
              className="transition-all hover:shadow-md hover:border-primary/20"
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <CardTitle className="text-base">
                      {interview.company || "Practice"} •{" "}
                      {interview.role || "Software Engineer"}
                    </CardTitle>
                    <CardDescription className="text-xs">
                      {interview.interviewType === "system_design"
                        ? "System Design"
                        : interview.interviewType === "coding"
                          ? "Coding"
                          : "Interview"}{" "}
                      • {interview.level || "Senior"} • Completed{" "}
                      {formatDate(interview.completedAt)}
                    </CardDescription>
                  </div>
                  <Badge
                    variant="outline"
                    className="bg-green-50 text-green-700 border-green-200"
                  >
                    ✓ Completed
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <Button
                  variant="outline"
                  size="sm"
                  asChild
                  className="w-full"
                >
                  <Link href={`/interviews/${interview.id}`}>
                    View Details
                    <ArrowRight className="ml-2 size-4" />
                  </Link>
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Empty State if no interviews */}
      {recentInterviews.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Brain className="mb-4 size-12 text-muted-foreground/50" />
            <h3 className="mb-2 text-lg font-semibold">No interviews yet</h3>
            <p className="text-muted-foreground mb-4 text-center">
              Start your first mock interview to begin tracking your progress
            </p>
            <Button asChild className="btn-gradient text-white">
              <Link href="/interview-session/new">
                <Play className="mr-2 size-4" />
                Start Your First Interview
              </Link>
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
