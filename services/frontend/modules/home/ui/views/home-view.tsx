"use client";

import { Brain, Star, ArrowRight, Play } from "lucide-react";
import Link from "next/link";
import { authClient } from "@/lib/auth-client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

// Mock data - replace with real data from your backend
const companies = [
  {
    id: "google",
    name: "Google",
    logo: "G",
    bgColor: "bg-blue-500",
    avgScore: 8.5,
    completedCount: 3,
    available: true,
    isPremium: true,
  },
  {
    id: "meta",
    name: "Meta",
    logo: "M",
    bgColor: "bg-blue-600",
    avgScore: 7.8,
    completedCount: 1,
    available: true,
    isPremium: true,
  },
  {
    id: "free",
    name: "Free Practice",
    logo: "✓",
    bgColor: "bg-primary",
    avgScore: 8.0,
    completedCount: 8,
    available: true,
    isPremium: false,
    directLink: "/interview/demo-123/system-design",
  },
  {
    id: "amazon",
    name: "Amazon",
    logo: "A",
    bgColor: "bg-orange-500",
    avgScore: 0,
    completedCount: 0,
    available: false,
    isPremium: true,
  },
];

const recentInterviews = [
  {
    id: "1",
    company: "Google",
    type: "System Design",
    status: "completed",
    completedAt: "2 hours ago",
    score: 8.5,
    strengths: ["Architecture", "APIs", "Scalability"],
    improvements: ["Capacity planning", "Load balancing"],
  },
  {
    id: "3",
    company: "Free Practice",
    type: "System Design",
    status: "completed",
    completedAt: "Yesterday",
    score: 7.0,
    strengths: ["Data modeling", "API design"],
    improvements: ["Caching strategies", "CDN usage"],
  },
];

export const HomeView = () => {
  const { data: session } = authClient.useSession();

  const getFirstName = (name?: string) => {
    if (!name) return "there";
    return name.split(" ")[0];
  };

  return (
    <div className="space-y-6">
      {/* Greeting */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">
          Hi {getFirstName(session?.user?.name)}! Ready to practice? 🚀
        </h1>
        <p className="text-muted-foreground">
          Choose your company and start preparing for your dream interview
        </p>
      </div>

      {/* Company Cards */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Choose Your Company</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {companies.map((company) => (
            <Card
              key={company.id}
              className={`relative overflow-hidden transition-all duration-300 ${
                !company.available && "opacity-60"
              }
              hover:shadow-xl hover:border-primary hover:bg-gradient-to-br hover:from-primary/5 hover:to-primary/10 hover:-translate-y-1`}
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <Avatar className={`size-12 ${company.bgColor}`}>
                    <AvatarFallback className="bg-transparent text-white text-lg font-bold">
                      {company.logo}
                    </AvatarFallback>
                  </Avatar>
                  {company.isPremium && company.available && (
                    <Badge variant="secondary" className="text-xs">
                      Premium
                    </Badge>
                  )}
                  {!company.available && (
                    <Badge variant="outline" className="text-xs">
                      Coming Soon
                    </Badge>
                  )}
                </div>
                <CardTitle className="mt-4">{company.name}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {company.available && company.completedCount > 0 && (
                  <>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Avg Score</span>
                      <span className="font-semibold">{company.avgScore}/10</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Completed</span>
                      <span className="font-semibold">{company.completedCount}</span>
                    </div>
                    <Button
                      className="w-full btn-gradient text-white"
                      size="sm"
                      asChild
                    >
                      <Link href={company.directLink || `/interview/new?company=${company.id}`}>
                        <Play className="mr-2 size-4" />
                        Start Interview
                      </Link>
                    </Button>
                  </>
                )}
                {company.available && company.completedCount === 0 && (
                  <Button
                    className="w-full btn-gradient text-white"
                    size="sm"
                    asChild
                  >
                    <Link href={`/interview/new?company=${company.id}`}>
                      <Play className="mr-2 size-4" />
                      Get Started
                    </Link>
                  </Button>
                )}
                {!company.available && (
                  <Button className="w-full" variant="secondary" size="sm" disabled>
                    Not Available
                  </Button>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
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

        <div className="space-y-4">
          {recentInterviews.map((interview) => (
            <Card key={interview.id} className="transition-all hover:shadow-xl border-2 hover:border-primary/20">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <CardTitle className="text-lg">
                      {interview.company} • {interview.type}
                    </CardTitle>
                    <CardDescription>
                      {interview.status === "completed"
                        ? `Completed ${interview.completedAt}`
                        : `Started ${interview.startedAt}`}
                    </CardDescription>
                  </div>
                  {interview.status === "completed" ? (
                    <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                      ✓ Completed
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                      In Progress
                    </Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {interview.status === "completed" && interview.score && (
                  <>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Score</span>
                      <div className="flex items-center gap-2">
                        <span className="text-lg font-bold">{interview.score}/10</span>
                        {interview.score >= 8 ? (
                          <Star className="size-5 fill-yellow-400 text-yellow-400" />
                        ) : interview.score >= 7 ? (
                          <Star className="size-5 fill-yellow-200 text-yellow-400" />
                        ) : (
                          <Star className="size-5 text-gray-300" />
                        )}
                      </div>
                    </div>

                    {interview.strengths && interview.strengths.length > 0 && (
                      <div className="space-y-2">
                        <span className="text-sm font-medium text-green-700">
                          Strong Areas:
                        </span>
                        <div className="flex flex-wrap gap-2">
                          {interview.strengths.map((strength, idx) => (
                            <Badge
                              key={idx}
                              variant="secondary"
                              className="bg-green-50 text-green-700"
                            >
                              {strength}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {interview.improvements && interview.improvements.length > 0 && (
                      <div className="space-y-2">
                        <span className="text-sm font-medium text-orange-700">
                          Areas to Improve:
                        </span>
                        <div className="flex flex-wrap gap-2">
                          {interview.improvements.map((improvement, idx) => (
                            <Badge
                              key={idx}
                              variant="secondary"
                              className="bg-orange-50 text-orange-700"
                            >
                              {improvement}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" asChild className="flex-1">
                        <Link href={`/interviews/${interview.id}`}>View Details</Link>
                      </Button>
                      <Button size="sm" asChild className="flex-1 btn-gradient text-white">
                        <Link href={`/interview/new?company=${interview.company.toLowerCase()}`}>
                          Practice Again
                          <ArrowRight className="ml-2 size-4" />
                        </Link>
                      </Button>
                    </div>
                  </>
                )}

                {interview.status === "in_progress" && interview.currentPhase && (
                  <>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium">Progress</span>
                        <span className="text-muted-foreground">
                          Phase {interview.currentPhase} of {interview.totalPhases}
                        </span>
                      </div>
                      <Progress
                        value={(interview.currentPhase / interview.totalPhases) * 100}
                        className="h-2"
                      />
                    </div>

                    <Button size="sm" className="w-full btn-gradient text-white" asChild>
                      <Link href={`/interviews/${interview.id}/resume`}>
                        Resume Interview
                        <ArrowRight className="ml-2 size-4" />
                      </Link>
                    </Button>
                  </>
                )}
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
              <Link href="/interview/new">
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
