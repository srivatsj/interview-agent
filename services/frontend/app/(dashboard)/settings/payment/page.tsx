import { auth } from "@/lib/auth";
import { PaymentSettingsView } from "@/modules/payments/ui/views/payment-settings-view";
import { headers } from "next/headers";
import { redirect } from "next/navigation";

const Page = async () => {
  const session = await auth.api.getSession({
    headers: await headers(),
  });

  if (!session?.user?.id) {
    redirect("/sign-in");
  }

  return <PaymentSettingsView userId={session.user.id} />;
};

export default Page;
