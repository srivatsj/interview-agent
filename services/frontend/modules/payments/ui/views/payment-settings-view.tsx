"use client";

import { useState, useEffect } from "react";
import { loadStripe } from "@stripe/stripe-js";
import {
  Elements,
  PaymentElement,
  useStripe,
  useElements,
} from "@stripe/react-stripe-js";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { setupPaymentMethod, savePaymentMethod } from "../../actions";

const stripePromise = loadStripe(
  process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!
);

interface PaymentSetupFormProps {
  userId: string;
}

function PaymentSetupForm({ userId }: PaymentSetupFormProps) {
  const stripe = useStripe();
  const elements = useElements();
  const { toast } = useToast();
  const [isProcessing, setIsProcessing] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!stripe || !elements) {
      return;
    }

    setIsProcessing(true);

    try {
      console.log("💳 Confirming payment setup...");

      // Confirm the SetupIntent
      const { error, setupIntent } = await stripe.confirmSetup({
        elements,
        redirect: "if_required",
      });

      if (error) {
        console.error("❌ Setup error:", error);
        toast({
          variant: "destructive",
          title: "Payment Setup Failed",
          description: error.message,
        });
        return;
      }

      if (setupIntent?.payment_method) {
        console.log("✅ Payment method added:", setupIntent.payment_method);

        // Save payment method to database via server action
        const result = await savePaymentMethod(
          userId,
          setupIntent.payment_method as string
        );

        console.log("💾 Payment method saved:", result);

        toast({
          title: "Success!",
          description: `Payment method added: ${result.card.brand} ending in ${result.card.last4}`,
        });

        // Refresh page to show updated card
        window.location.reload();
      }
    } catch (error) {
      console.error("❌ Error:", error);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to save payment method. Please try again.",
      });
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <PaymentElement />
      <Button type="submit" disabled={!stripe || isProcessing} className="w-full">
        {isProcessing ? "Processing..." : "Save Payment Method"}
      </Button>
    </form>
  );
}

interface PaymentSettingsViewProps {
  userId: string;
}

export function PaymentSettingsView({ userId }: PaymentSettingsViewProps) {
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    async function initializePaymentSetup() {
      try {
        console.log("🔐 Initializing payment setup...");

        // Call server action to setup payment
        const result = await setupPaymentMethod(userId);

        console.log("✅ Client secret received");
        setClientSecret(result.clientSecret);
      } catch (error) {
        console.error("❌ Setup error:", error);
        toast({
          variant: "destructive",
          title: "Setup Failed",
          description: "Failed to initialize payment setup. Please try again.",
        });
      } finally {
        setIsLoading(false);
      }
    }

    initializePaymentSetup();
  }, [userId, toast]);

  return (
    <div className="container max-w-2xl py-8">
      <Card>
        <CardHeader>
          <CardTitle>Payment Method</CardTitle>
          <CardDescription>
            Add a payment method to purchase premium interview sessions
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <div className="text-muted-foreground">Loading...</div>
            </div>
          ) : clientSecret ? (
            <Elements
              stripe={stripePromise}
              options={{
                clientSecret,
                appearance: { theme: "stripe" },
              }}
            >
              <PaymentSetupForm userId={userId} />
            </Elements>
          ) : (
            <div className="text-center text-muted-foreground py-8">
              Failed to load payment setup
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
