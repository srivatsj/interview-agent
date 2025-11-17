import { auth } from "@/lib/auth";
import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { getInterviewById } from "@/modules/completed-interviews/actions";
import { InterviewDetailView } from "@/modules/completed-interviews/ui/views/interview-detail-view";

interface PageProps {
  params: Promise<{ interviewId: string }>;
}

const Page = async ({ params }: PageProps) => {
  const session = await auth.api.getSession({
    headers: await headers(),
  });

  if (!session) {
    redirect("/sign-in");
  }

  const { interviewId } = await params;
  const interview = await getInterviewById(interviewId, session.user.id);

  if (!interview) {
    redirect("/interviews");
  }

  return <InterviewDetailView interview={interview} />;
};

export default Page;
