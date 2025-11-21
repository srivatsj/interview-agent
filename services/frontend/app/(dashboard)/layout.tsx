"use client";

import { Brain, LayoutDashboard, Play, BookOpen, BarChart3, Clock } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { authClient } from "@/lib/auth-client";
import { useRouter } from "next/navigation";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarSeparator,
  SidebarInset,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const menuItems = {
  start: [
    {
      title: "START",
      icon: Play,
      url: "/dashboard",
      badge: null,
      isActive: true,
    },
  ],
  myPrep: [
    {
      title: "Interviews",
      icon: BookOpen,
      url: "/interviews",
      badge: null,
    },
    {
      title: "Notes",
      icon: BookOpen,
      url: "/notes",
      badge: null,
    },
  ],
  insights: [
    {
      title: "Overview",
      icon: LayoutDashboard,
      url: "/insights",
      badge: null,
    },
    {
      title: "By Company",
      icon: BarChart3,
      url: "/insights/company",
      badge: null,
    },
    {
      title: "By Type",
      icon: BarChart3,
      url: "/insights/type",
      badge: null,
    },
  ],
};

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { data: session } = authClient.useSession();

  const handleSignOut = () => {
    authClient.signOut({
      fetchOptions: {
        onSuccess: () => router.push("/sign-in"),
      },
    });
  };

  const getInitials = (name?: string) => {
    if (!name) return "U";
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <SidebarProvider defaultOpen>
      <Sidebar collapsible="icon" className="border-r border-border/50 bg-sidebar">
        <SidebarHeader className="pb-4 pt-4">
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton size="lg" asChild className="hover:bg-transparent">
                <Link href="/dashboard">
                  <div className="bg-gradient-to-br from-primary to-purple-600 text-primary-foreground flex aspect-square size-10 items-center justify-center rounded-xl shadow-lg shadow-primary/20">
                    <Brain className="size-6" />
                  </div>
                  <div className="grid flex-1 text-left text-sm leading-tight ml-2">
                    <span className="truncate font-bold text-lg tracking-tight">InterviewOS</span>
                    <span className="truncate text-xs text-muted-foreground font-medium">
                      AI Interview Prep
                    </span>
                  </div>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarHeader>

        <SidebarContent className="px-2">
          {/* START Section */}
          <SidebarGroup>
            <SidebarGroupLabel className="text-xs font-bold uppercase tracking-wider text-muted-foreground/70 mb-2">
              Start
            </SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {menuItems.start.map((item) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton
                      asChild
                      isActive={pathname === item.url}
                      tooltip={item.title}
                      className={`
                        transition-all duration-200 font-medium
                        ${pathname === item.url
                          ? "bg-primary text-primary-foreground shadow-md shadow-primary/20 hover:bg-primary/90 hover:text-primary-foreground"
                          : "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground text-muted-foreground"}
                      `}
                    >
                      <Link href={item.url}>
                        <item.icon className={pathname === item.url ? "text-primary-foreground" : "text-muted-foreground"} />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>

          <SidebarSeparator className="my-4 opacity-50" />

          {/* MY PREP Section */}
          <SidebarGroup>
            <SidebarGroupLabel className="text-xs font-bold uppercase tracking-wider text-muted-foreground/70 mb-2">
              My Prep
            </SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {menuItems.myPrep.map((item) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton
                      asChild
                      isActive={pathname === item.url}
                      tooltip={item.title}
                      className="text-muted-foreground hover:text-foreground transition-colors"
                    >
                      <Link href={item.url}>
                        <item.icon />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>

          <SidebarSeparator className="my-4 opacity-50" />

          {/* INSIGHTS Section */}
          <SidebarGroup>
            <SidebarGroupLabel className="text-xs font-bold uppercase tracking-wider text-muted-foreground/70 mb-2">
              Insights
            </SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {menuItems.insights.map((item) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton
                      asChild
                      isActive={pathname === item.url}
                      tooltip={item.title}
                      className="text-muted-foreground hover:text-foreground transition-colors"
                    >
                      <Link href={item.url}>
                        <item.icon />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>

          <div className="mt-auto p-2">
            {/* Stats Widget */}
            <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-violet-500/10 via-purple-500/10 to-fuchsia-500/10 border border-purple-500/20 p-4">
              <div className="absolute top-0 right-0 -mt-4 -mr-4 h-24 w-24 rounded-full bg-purple-500/20 blur-2xl" />
              <h4 className="relative text-xs font-bold uppercase tracking-wider text-purple-600 dark:text-purple-400 mb-3">
                Your Stats
              </h4>
              <div className="relative space-y-3">
                <div className="flex items-center gap-2 text-sm text-foreground/80">
                  <Clock className="size-4 text-purple-500" />
                  <span className="font-medium">9.5 hrs</span>
                  <span className="text-xs text-muted-foreground ml-auto">Practice</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-foreground/80">
                  <BarChart3 className="size-4 text-fuchsia-500" />
                  <span className="font-medium">12</span>
                  <span className="text-xs text-muted-foreground ml-auto">Completed</span>
                </div>
                <div className="pt-2 border-t border-purple-500/10">
                  <span className="text-xs font-medium text-green-600 dark:text-green-400 flex items-center gap-1">
                    📈 +15% this week
                  </span>
                </div>
              </div>
            </div>
          </div>

        </SidebarContent>

        <SidebarFooter className="p-4">
          <SidebarMenu>
            <SidebarMenuItem>
              <DropdownMenu>
                <DropdownMenuTrigger asChild suppressHydrationWarning>
                  <SidebarMenuButton
                    size="lg"
                    className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground hover:bg-sidebar-accent/50 transition-colors"
                    suppressHydrationWarning
                  >
                    <Avatar className="size-9 rounded-xl border border-border/50">
                      <AvatarImage
                        src={session?.user?.image || undefined}
                        alt={session?.user?.name || ""}
                      />
                      <AvatarFallback className="rounded-xl bg-gradient-to-br from-primary/10 to-purple-500/10 text-primary font-medium">
                        {getInitials(session?.user?.name)}
                      </AvatarFallback>
                    </Avatar>
                    <div className="grid flex-1 text-left text-sm leading-tight ml-1">
                      <span className="truncate font-semibold text-foreground">
                        {session?.user?.name || "User"}
                      </span>
                      <span className="text-muted-foreground truncate text-xs">
                        {session?.user?.email || "user@example.com"}
                      </span>
                    </div>
                  </SidebarMenuButton>
                </DropdownMenuTrigger>
                <DropdownMenuContent
                  className="w-56 rounded-xl border-border/50 shadow-xl bg-background/95 backdrop-blur-sm"
                  align="end"
                  side="top"
                  sideOffset={8}
                >
                  <DropdownMenuLabel className="text-muted-foreground">My Account</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem asChild className="cursor-pointer focus:bg-primary/10 focus:text-primary">
                    <Link href="/profile">Profile</Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild className="cursor-pointer focus:bg-primary/10 focus:text-primary">
                    <Link href="/settings">Settings</Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild className="cursor-pointer focus:bg-primary/10 focus:text-primary">
                    <Link href="/settings/payment">Payment Settings</Link>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleSignOut} className="text-red-600 focus:bg-red-50 focus:text-red-700 dark:focus:bg-red-950/50 dark:focus:text-red-400 cursor-pointer">
                    Sign Out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarFooter>
      </Sidebar>

      <SidebarInset className="bg-background">
        <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center gap-2 border-b border-border/40 bg-background/80 px-6 backdrop-blur-xl transition-all">
          <SidebarTrigger className="-ml-2 text-muted-foreground hover:text-foreground" />
          <div className="flex flex-1 items-center justify-between">
            <h1 className="text-lg font-semibold tracking-tight text-foreground/90">Dashboard</h1>
          </div>
        </header>
        <div className="flex flex-1 flex-col gap-6 p-6 max-w-7xl mx-auto w-full animate-in-fade">
          {children}
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
