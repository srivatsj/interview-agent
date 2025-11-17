import { auth } from "@/lib/auth";
import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { getCompletedInterviews } from "@/modules/completed-interviews/actions";
import { CompletedInterviewsListView } from "@/modules/completed-interviews/ui/views/completed-interviews-list-view";

const Page = async () => {
  const session = await auth.api.getSession({
    headers: await headers(),
  });

  if (!session) {
    redirect("/sign-in");
  }

  const interviews = await getCompletedInterviews();

  return <CompletedInterviewsListView interviews={interviews} />;
};

export default Page;
