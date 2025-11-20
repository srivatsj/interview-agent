import { NextRequest, NextResponse } from "next/server";
import Stripe from "stripe";
import { db } from "@/db";
import { ap2Transactions } from "@/db/schema/payments";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: "2025-11-17.clover",
});

export async function POST(request: NextRequest) {
  try {
    const { payment_mandate } = await request.json();

    if (!payment_mandate) {
      return NextResponse.json(
        { error: "payment_mandate is required" },
        { status: 400 }
      );
    }

    console.log(`💳 Processing payment mandate: ${payment_mandate.payment_mandate_id}`);

    // Extract payment details
    const paymentToken = payment_mandate.payment_response?.details?.token;
    const userId = payment_mandate.payment_response?.details?.user_id;
    const interviewId = payment_mandate.payment_response?.details?.interview_id;
    const totalAmount = payment_mandate.payment_details_total;

    if (!paymentToken || !userId || !totalAmount) {
      console.error("❌ Missing required payment details");
      return NextResponse.json(
        { error: "Invalid payment mandate" },
        { status: 400 }
      );
    }

    // Verify cart hash (optional but recommended)
    const cartMandateId = payment_mandate.cart_mandate_id;
    const expectedHash = payment_mandate.cart_hash;
    console.log(`🔐 Verifying cart hash: ${expectedHash.substring(0, 8)}...`);

    // Get payment method from token
    const paymentMethodId = paymentToken.payment_method_id;
    const stripeCustomerId = paymentToken.stripe_customer_id;

    console.log(`💰 Charging ${totalAmount.currency} ${totalAmount.value} to customer ${stripeCustomerId}`);

    // Create and confirm PaymentIntent
    const paymentIntent = await stripe.paymentIntents.create({
      amount: Math.round(totalAmount.value * 100), // Convert to cents
      currency: totalAmount.currency.toLowerCase(),
      customer: stripeCustomerId,
      payment_method: paymentMethodId,
      confirm: true,
      off_session: true, // Allow charging saved card without user present
      metadata: {
        user_id: userId,
        interview_id: interviewId || "",
        cart_mandate_id: cartMandateId,
        payment_mandate_id: payment_mandate.payment_mandate_id,
      },
    });

    if (paymentIntent.status !== "succeeded") {
      console.error(`❌ Payment failed: ${paymentIntent.status}`);
      return NextResponse.json({
        payment_receipt: {
          payment_id: paymentIntent.id,
          payment_status: {
            status: "failed",
            error: `Payment status: ${paymentIntent.status}`,
          },
        },
      });
    }

    console.log(`✅ Payment succeeded: ${paymentIntent.id}`);

    // Store transaction in database
    await db.insert(ap2Transactions).values({
      userId,
      interviewId: interviewId || null,
      amountCents: Math.round(totalAmount.value * 100),
      stripeChargeId: paymentIntent.id,
      cartMandate: payment_mandate,
      paymentMandate: payment_mandate,
      status: "completed",
    });

    console.log("💾 Transaction stored in database");

    // Return payment receipt
    const receipt = {
      payment_receipt: {
        payment_id: paymentIntent.id,
        payment_mandate_id: payment_mandate.payment_mandate_id,
        cart_mandate_id: cartMandateId,
        amount: totalAmount,
        payment_status: {
          status: "success",
          timestamp: new Date().toISOString(),
        },
        merchant_agent: payment_mandate.merchant_agent,
      },
    };

    return NextResponse.json(receipt);
  } catch (error: unknown) {
    console.error("❌ Error executing payment:", error);

    // Handle specific Stripe errors
    if (
      error &&
      typeof error === "object" &&
      "type" in error &&
      error.type === "StripeCardError"
    ) {
      return NextResponse.json({
        payment_receipt: {
          payment_id: "",
          payment_status: {
            status: "failed",
            error: "message" in error ? String(error.message) : "Card error",
          },
        },
      });
    }

    return NextResponse.json(
      { error: "Failed to execute payment" },
      { status: 500 }
    );
  }
}
