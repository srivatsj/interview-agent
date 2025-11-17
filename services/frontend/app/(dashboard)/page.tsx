import { auth } from "@/lib/auth";
import { HomeView } from "@/modules/home/ui/views/home-view";
import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { getRecentInterviews } from "@/modules/home/actions";

const Page = async () => {
  const session = await auth.api.getSession({
    headers: await headers(),
  });

  if (!session) {
    redirect("/sign-in");
  }

  // Get 3 most recent completed interviews for home page
  const recentInterviews = await getRecentInterviews();

  return <HomeView recentInterviews={recentInterviews} />;
};

export default Page;
