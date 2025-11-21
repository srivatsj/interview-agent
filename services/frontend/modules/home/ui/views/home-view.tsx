"use client";

import { Brain, ArrowRight, Play, Code, Layout, Sparkles } from "lucide-react";
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
    <div className="space-y-8 pb-8">
      {/* Hero / Greeting */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-primary/90 via-primary to-purple-600 p-8 text-white shadow-xl shadow-primary/20">
        <div className="absolute top-0 right-0 -mt-16 -mr-16 h-64 w-64 rounded-full bg-white/10 blur-3xl" />
        <div className="absolute bottom-0 left-0 -mb-16 -ml-16 h-64 w-64 rounded-full bg-purple-500/20 blur-3xl" />

        <div className="relative z-10 flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-primary-foreground/80">
              <Sparkles className="size-5" />
              <span className="text-sm font-medium uppercase tracking-wider">Welcome Back</span>
            </div>
            <h1 className="text-3xl font-bold tracking-tight md:text-4xl lg:text-5xl">
              Hi, {getFirstName(session?.user?.name)}!
            </h1>
            <p className="max-w-xl text-lg text-primary-foreground/90">
              Ready to ace your next technical interview? Choose a track below to get started.
            </p>
          </div>
          <Button asChild size="lg" className="bg-white text-primary hover:bg-white/90 border-0 shadow-lg hover:shadow-xl transition-all duration-300 font-semibold h-12 px-8 rounded-xl">
            <Link href="/interview-session/new">
              <Play className="mr-2 size-5" />
              Start New Session
            </Link>
          </Button>
        </div>
      </div>

      {/* Quick Start Tracks */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card className="group relative overflow-hidden border-border/50 bg-card/50 hover:bg-card/80 transition-all duration-300 hover:shadow-lg hover:-translate-y-1 cursor-pointer">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-cyan-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
          <CardHeader>
            <div className="mb-4 flex size-12 items-center justify-center rounded-2xl bg-blue-500/10 text-blue-600 dark:text-blue-400 group-hover:scale-110 transition-transform duration-300">
              <Layout className="size-6" />
            </div>
            <CardTitle className="text-xl">System Design</CardTitle>
            <CardDescription>
              Architect scalable distributed systems. Practice with Google & Meta specific feedback.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" className="w-full group-hover:bg-blue-500 group-hover:text-white group-hover:border-blue-500 transition-all" asChild>
              <Link href="/interview-session/new?type=system-design">
                Start Practice <ArrowRight className="ml-2 size-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card className="group relative overflow-hidden border-border/50 bg-card/50 hover:bg-card/80 transition-all duration-300 hover:shadow-lg hover:-translate-y-1 cursor-pointer">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-green-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
          <CardHeader>
            <div className="mb-4 flex size-12 items-center justify-center rounded-2xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 group-hover:scale-110 transition-transform duration-300">
              <Code className="size-6" />
            </div>
            <CardTitle className="text-xl">Coding Interview</CardTitle>
            <CardDescription>
              Solve algorithmic problems with real-time execution and complexity analysis.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" className="w-full group-hover:bg-emerald-500 group-hover:text-white group-hover:border-emerald-500 transition-all" asChild>
              <Link href="/interview-session/new?type=coding">
                Start Practice <ArrowRight className="ml-2 size-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <div className="space-y-4">
        <div className="flex items-center justify-between px-1">
          <h2 className="text-xl font-semibold tracking-tight">Recent Activity</h2>
          <Button variant="ghost" size="sm" asChild className="text-muted-foreground hover:text-primary">
            <Link href="/interviews">
              View All History
              <ArrowRight className="ml-2 size-4" />
            </Link>
          </Button>
        </div>

        <div className="space-y-3">
          {recentInterviews.map((interview) => (
            <Card
              key={interview.id}
              className="group border-border/50 bg-card/50 hover:bg-card hover:border-primary/20 transition-all duration-300 hover:shadow-md"
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4">
                    <div className={`mt-1 flex size-10 items-center justify-center rounded-lg border ${interview.interviewType === 'system_design'
                        ? 'bg-blue-500/10 border-blue-500/20 text-blue-600'
                        : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-600'
                      }`}>
                      {interview.interviewType === 'system_design' ? <Layout className="size-5" /> : <Code className="size-5" />}
                    </div>
                    <div className="space-y-1">
                      <CardTitle className="text-base font-semibold group-hover:text-primary transition-colors">
                        {interview.company || "Practice Session"}
                      </CardTitle>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span className="font-medium text-foreground/80">{interview.role || "Software Engineer"}</span>
                        <span>•</span>
                        <span>{interview.level || "Senior"}</span>
                        <span>•</span>
                        <span>{formatDate(interview.completedAt)}</span>
                      </div>
                    </div>
                  </div>
                  <Badge
                    variant="outline"
                    className="bg-green-500/10 text-green-600 border-green-500/20 dark:bg-green-500/20 dark:text-green-400"
                  >
                    Completed
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-end">
                  <Button
                    variant="ghost"
                    size="sm"
                    asChild
                    className="opacity-0 group-hover:opacity-100 transition-opacity -translate-x-2 group-hover:translate-x-0 duration-300"
                  >
                    <Link href={`/interviews/${interview.id}`}>
                      View Details
                      <ArrowRight className="ml-2 size-4" />
                    </Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Empty State if no interviews */}
      {recentInterviews.length === 0 && (
        <Card className="border-dashed border-2 bg-muted/30">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <div className="mb-6 flex size-20 items-center justify-center rounded-full bg-primary/10">
              <Brain className="size-10 text-primary" />
            </div>
            <h3 className="mb-2 text-xl font-semibold">No interviews yet</h3>
            <p className="text-muted-foreground mb-8 max-w-sm">
              Your journey to your dream job starts here. Launch your first mock interview to begin tracking your progress.
            </p>
            <Button asChild size="lg" className="bg-gradient-to-r from-primary to-purple-600 text-white hover:opacity-90 shadow-lg shadow-primary/25">
              <Link href="/interview-session/new">
                <Play className="mr-2 size-5" />
                Start Your First Interview
              </Link>
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
