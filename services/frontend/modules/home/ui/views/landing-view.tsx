"use client";

import { Brain, ArrowRight, Code, Layout, Mic, Zap, CheckCircle2, Play } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export const LandingView = () => {
    return (
        <div className="flex min-h-screen flex-col bg-background text-foreground selection:bg-primary/20 selection:text-primary">
            {/* Navbar */}
            <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/80 backdrop-blur-xl">
                <div className="container mx-auto flex h-16 items-center justify-between px-4 md:px-6">
                    <div className="flex items-center gap-2">
                        <div className="flex size-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-purple-600 text-white shadow-lg shadow-primary/20">
                            <Brain className="size-5" />
                        </div>
                        <span className="text-lg font-bold tracking-tight">InterviewOS</span>
                    </div>
                    <nav className="flex items-center gap-4">
                        <Link href="/sign-in" className="text-sm font-medium text-muted-foreground hover:text-primary transition-colors">
                            Sign In
                        </Link>
                        <Button asChild className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-lg shadow-primary/20 transition-all hover:-translate-y-0.5">
                            <Link href="/sign-up">
                                Get Started <ArrowRight className="ml-2 size-4" />
                            </Link>
                        </Button>
                    </nav>
                </div>
            </header>

            <main className="flex-1">
                {/* Hero Section */}
                <section className="relative overflow-hidden pt-24 pb-32 md:pt-32 md:pb-48">
                    <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/20 via-background to-background" />
                    <div className="absolute top-0 right-0 -mt-20 -mr-20 h-96 w-96 rounded-full bg-purple-500/20 blur-3xl" />
                    <div className="absolute bottom-0 left-0 -mb-20 -ml-20 h-96 w-96 rounded-full bg-blue-500/20 blur-3xl" />

                    <div className="container mx-auto px-4 md:px-6 text-center">
                        <div className="inline-flex items-center rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-sm font-medium text-primary mb-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                            <Zap className="mr-2 size-3.5 fill-primary" />
                            AI-Powered Technical Interviews
                        </div>
                        <h1 className="mx-auto max-w-4xl text-5xl font-bold tracking-tight md:text-7xl bg-clip-text text-transparent bg-gradient-to-b from-foreground to-foreground/70 mb-6 animate-in fade-in slide-in-from-bottom-6 duration-700 delay-100">
                            Master Your Next <br />
                            <span className="text-primary">Technical Interview</span>
                        </h1>
                        <p className="mx-auto max-w-2xl text-xl text-muted-foreground mb-10 animate-in fade-in slide-in-from-bottom-8 duration-700 delay-200">
                            Practice system design and coding interviews with AI agents from top tech companies. Get real-time feedback and improve faster.
                        </p>
                        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-in fade-in slide-in-from-bottom-10 duration-700 delay-300">
                            <Button asChild size="lg" className="h-12 px-8 text-base bg-gradient-to-r from-primary to-purple-600 hover:opacity-90 transition-all shadow-xl shadow-primary/25">
                                <Link href="/sign-up">
                                    Start Practicing Now
                                    <Play className="ml-2 size-4 fill-current" />
                                </Link>
                            </Button>
                            <Button asChild variant="outline" size="lg" className="h-12 px-8 text-base border-primary/20 hover:bg-primary/5 hover:text-primary transition-colors">
                                <Link href="#features">
                                    Learn More
                                </Link>
                            </Button>
                        </div>
                    </div>
                </section>

                {/* Features Section */}
                <section id="features" className="py-24 bg-muted/30">
                    <div className="container mx-auto px-4 md:px-6">
                        <div className="text-center mb-16">
                            <h2 className="text-3xl font-bold tracking-tight md:text-4xl mb-4">Everything you need to succeed</h2>
                            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                                Comprehensive preparation tools designed to mimic real-world interview scenarios at top tech companies.
                            </p>
                        </div>

                        <div className="grid gap-8 md:grid-cols-3">
                            <div className="group relative overflow-hidden rounded-2xl border border-border/50 bg-background p-8 hover:shadow-xl hover:shadow-primary/5 transition-all duration-300 hover:-translate-y-1">
                                <div className="mb-6 inline-flex size-12 items-center justify-center rounded-xl bg-blue-500/10 text-blue-600 group-hover:scale-110 transition-transform duration-300">
                                    <Layout className="size-6" />
                                </div>
                                <h3 className="text-xl font-bold mb-3">System Design</h3>
                                <p className="text-muted-foreground leading-relaxed">
                                    Design scalable architectures with an interactive whiteboard. Get feedback on trade-offs, bottlenecks, and data models.
                                </p>
                            </div>

                            <div className="group relative overflow-hidden rounded-2xl border border-border/50 bg-background p-8 hover:shadow-xl hover:shadow-primary/5 transition-all duration-300 hover:-translate-y-1">
                                <div className="mb-6 inline-flex size-12 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-600 group-hover:scale-110 transition-transform duration-300">
                                    <Code className="size-6" />
                                </div>
                                <h3 className="text-xl font-bold mb-3">Coding Challenges</h3>
                                <p className="text-muted-foreground leading-relaxed">
                                    Solve algorithmic problems in a real IDE environment. Receive hints and complexity analysis from your AI interviewer.
                                </p>
                            </div>

                            <div className="group relative overflow-hidden rounded-2xl border border-border/50 bg-background p-8 hover:shadow-xl hover:shadow-primary/5 transition-all duration-300 hover:-translate-y-1">
                                <div className="mb-6 inline-flex size-12 items-center justify-center rounded-xl bg-purple-500/10 text-purple-600 group-hover:scale-110 transition-transform duration-300">
                                    <Mic className="size-6" />
                                </div>
                                <h3 className="text-xl font-bold mb-3">Voice Interaction</h3>
                                <p className="text-muted-foreground leading-relaxed">
                                    Experience natural conversations with ultra-low latency voice AI. Practice your communication and behavioral skills.
                                </p>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Companies Section */}
                <section className="py-24 border-t border-border/40">
                    <div className="container mx-auto px-4 md:px-6">
                        <div className="grid gap-12 lg:grid-cols-2 items-center">
                            <div className="space-y-8">
                                <h2 className="text-3xl font-bold tracking-tight md:text-4xl">
                                    Tailored feedback for <br />
                                    <span className="text-primary">Top Tech Companies</span>
                                </h2>
                                <p className="text-lg text-muted-foreground">
                                    Our AI agents are trained on specific evaluation rubrics from major tech companies. Whether you're aiming for Google, Meta, or Amazon, we've got you covered.
                                </p>
                                <ul className="space-y-4">
                                    {[
                                        "Company-specific evaluation criteria",
                                        "Role-based difficulty levels (L3 - L7)",
                                        "Detailed performance reports",
                                        "Actionable improvement tips"
                                    ].map((item) => (
                                        <li key={item} className="flex items-center gap-3">
                                            <CheckCircle2 className="size-5 text-green-500" />
                                            <span className="font-medium">{item}</span>
                                        </li>
                                    ))}
                                </ul>
                                <Button asChild size="lg" className="mt-4 bg-primary text-primary-foreground hover:bg-primary/90">
                                    <Link href="/sign-up">
                                        Start Free Trial
                                    </Link>
                                </Button>
                            </div>
                            <div className="relative mx-auto w-full max-w-md lg:max-w-full">
                                <div className="absolute inset-0 bg-gradient-to-tr from-primary/20 to-purple-500/20 blur-3xl -z-10" />
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-4 translate-y-8">
                                        <div className="rounded-2xl border border-border/50 bg-background/50 p-6 backdrop-blur-sm shadow-lg">
                                            <div className="h-8 w-24 bg-foreground/10 rounded mb-4" />
                                            <div className="space-y-2">
                                                <div className="h-2 w-full bg-foreground/5 rounded" />
                                                <div className="h-2 w-2/3 bg-foreground/5 rounded" />
                                            </div>
                                        </div>
                                        <div className="rounded-2xl border border-border/50 bg-background/50 p-6 backdrop-blur-sm shadow-lg">
                                            <div className="h-8 w-24 bg-foreground/10 rounded mb-4" />
                                            <div className="space-y-2">
                                                <div className="h-2 w-full bg-foreground/5 rounded" />
                                                <div className="h-2 w-2/3 bg-foreground/5 rounded" />
                                            </div>
                                        </div>
                                    </div>
                                    <div className="space-y-4">
                                        <div className="rounded-2xl border border-border/50 bg-background/50 p-6 backdrop-blur-sm shadow-lg">
                                            <div className="h-8 w-24 bg-foreground/10 rounded mb-4" />
                                            <div className="space-y-2">
                                                <div className="h-2 w-full bg-foreground/5 rounded" />
                                                <div className="h-2 w-2/3 bg-foreground/5 rounded" />
                                            </div>
                                        </div>
                                        <div className="rounded-2xl border border-border/50 bg-background/50 p-6 backdrop-blur-sm shadow-lg">
                                            <div className="h-8 w-24 bg-foreground/10 rounded mb-4" />
                                            <div className="space-y-2">
                                                <div className="h-2 w-full bg-foreground/5 rounded" />
                                                <div className="h-2 w-2/3 bg-foreground/5 rounded" />
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>
            </main>

            {/* Footer */}
            <footer className="border-t border-border/40 bg-muted/20 py-12">
                <div className="container mx-auto px-4 md:px-6 flex flex-col md:flex-row items-center justify-between gap-6">
                    <div className="flex items-center gap-2">
                        <Brain className="size-5 text-muted-foreground" />
                        <span className="text-sm font-semibold text-muted-foreground">InterviewOS</span>
                    </div>
                    <p className="text-sm text-muted-foreground">
                        © {new Date().getFullYear()} InterviewOS. All rights reserved.
                    </p>
                    <div className="flex gap-6">
                        <Link href="#" className="text-sm text-muted-foreground hover:text-primary transition-colors">Privacy</Link>
                        <Link href="#" className="text-sm text-muted-foreground hover:text-primary transition-colors">Terms</Link>
                        <Link href="#" className="text-sm text-muted-foreground hover:text-primary transition-colors">Contact</Link>
                    </div>
                </div>
            </footer>
        </div>
    );
};
