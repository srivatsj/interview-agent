"use server";

import Stripe from "stripe";
import { db } from "@/db";
import { userPaymentMethods } from "@/db/schema/payments";
import { eq } from "drizzle-orm";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: "2025-11-17.clover",
});

export interface PaymentSetupResult {
  clientSecret: string;
  stripeCustomerId: string;
}

export interface SavePaymentMethodResult {
  success: boolean;
  card: {
    brand: string | undefined;
    last4: string | undefined;
    expMonth: number | undefined;
    expYear: number | undefined;
  };
}

/**
 * Initialize Stripe customer and create SetupIntent for payment method collection
 */
export async function setupPaymentMethod(
  userId: string
): Promise<PaymentSetupResult> {
  if (!userId) {
    throw new Error("userId is required");
  }

  console.log(`🔐 Setting up Stripe customer for user: ${userId}`);

  // Check if customer already exists
  const existing = await db
    .select()
    .from(userPaymentMethods)
    .where(eq(userPaymentMethods.userId, userId))
    .limit(1);

  if (existing.length > 0) {
    console.log(
      `✅ Existing Stripe customer found: ${existing[0].stripeCustomerId}`
    );

    // Create SetupIntent for existing customer
    const setupIntent = await stripe.setupIntents.create({
      customer: existing[0].stripeCustomerId,
      payment_method_types: ["card"],
    });

    return {
      clientSecret: setupIntent.client_secret!,
      stripeCustomerId: existing[0].stripeCustomerId,
    };
  }

  // Create new Stripe customer
  console.log("💳 Creating new Stripe customer...");
  const customer = await stripe.customers.create({
    metadata: { userId },
  });

  console.log(`✅ Stripe customer created: ${customer.id}`);

  // Store in database
  await db.insert(userPaymentMethods).values({
    userId,
    stripeCustomerId: customer.id,
  });

  console.log("💾 Saved to database");

  // Create SetupIntent
  const setupIntent = await stripe.setupIntents.create({
    customer: customer.id,
    payment_method_types: ["card"],
  });

  return {
    clientSecret: setupIntent.client_secret!,
    stripeCustomerId: customer.id,
  };
}

/**
 * Save payment method details after Stripe confirmation
 */
export async function savePaymentMethod(
  userId: string,
  paymentMethodId: string
): Promise<SavePaymentMethodResult> {
  if (!userId || !paymentMethodId) {
    throw new Error("userId and paymentMethodId are required");
  }

  console.log(`💳 Saving payment method for user: ${userId}`);

  // Get user's Stripe customer ID
  const userPayment = await db
    .select()
    .from(userPaymentMethods)
    .where(eq(userPaymentMethods.userId, userId))
    .limit(1);

  if (userPayment.length === 0) {
    throw new Error("User payment setup not found");
  }

  // Get payment method details from Stripe
  const paymentMethod = await stripe.paymentMethods.retrieve(paymentMethodId);

  console.log(
    `✅ Payment method retrieved: ${paymentMethod.card?.brand} ` +
      `ending in ${paymentMethod.card?.last4}`
  );

  // Update database with payment method details
  await db
    .update(userPaymentMethods)
    .set({
      defaultPaymentMethodId: paymentMethodId,
      cardLast4: paymentMethod.card?.last4 || null,
      cardBrand: paymentMethod.card?.brand || null,
      cardExpMonth: paymentMethod.card?.exp_month || null,
      cardExpYear: paymentMethod.card?.exp_year || null,
      updatedAt: new Date(),
    })
    .where(eq(userPaymentMethods.userId, userId));

  console.log("💾 Payment method saved to database");

  return {
    success: true,
    card: {
      brand: paymentMethod.card?.brand,
      last4: paymentMethod.card?.last4,
      expMonth: paymentMethod.card?.exp_month,
      expYear: paymentMethod.card?.exp_year,
    },
  };
}
