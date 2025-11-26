import { NextRequest, NextResponse } from "next/server";
import { db } from "@/db";
import { userPaymentMethods } from "@/db/schema/payments";
import { eq } from "drizzle-orm";
import type { PaymentToken } from "@/lib/ap2/types";

export async function POST(request: NextRequest) {
  try {
    const { user_id } = await request.json();

    if (!user_id) {
      return NextResponse.json({ error: "user_id is required" }, { status: 400 });
    }

    console.log(`🔐 Getting payment token for user: ${user_id}`);

    // Get user's payment method
    const userPayment = await db
      .select()
      .from(userPaymentMethods)
      .where(eq(userPaymentMethods.userId, user_id))
      .limit(1);

    if (userPayment.length === 0 || !userPayment[0].defaultPaymentMethodId) {
      console.error(`❌ No payment method found for user: ${user_id}`);
      return NextResponse.json(
        { error: "No payment method found. Please add a payment method first." },
        { status: 404 }
      );
    }

    const paymentMethodId = userPayment[0].defaultPaymentMethodId;
    console.log(`✅ Payment method found: ${paymentMethodId}`);

    // Return AP2-compliant payment token (encrypted reference to payment method)
    // In production, this should be encrypted/signed
    const frontendUrl = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

    const token: PaymentToken = {
      payment_method_id: paymentMethodId,
      stripe_customer_id: userPayment[0].stripeCustomerId,
      issued_at: new Date().toISOString(),
      credentials_provider_url: `${frontendUrl}/api/payments`, // AP2 spec requirement
    };

    return NextResponse.json({ token });
  } catch (error) {
    console.error("❌ Error getting payment token:", error);
    return NextResponse.json(
      { error: "Failed to get payment token" },
      { status: 500 }
    );
  }
}
