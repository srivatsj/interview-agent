import { auth } from "@/lib/auth";
import { LandingView } from "@/modules/home/ui/views/landing-view";
import { headers } from "next/headers";
import { redirect } from "next/navigation";

export default async function Page() {
    const session = await auth.api.getSession({
        headers: await headers(),
    });

    if (session) {
        redirect("/dashboard");
    }

    return <LandingView />;
}
