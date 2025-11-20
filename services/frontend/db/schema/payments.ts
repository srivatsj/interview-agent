import { uuid, text, timestamp, integer, jsonb } from "drizzle-orm/pg-core";
import { product } from "./namespaces";
import { interviews } from "./interviews";

export const userPaymentMethods = product.table("user_payment_methods", {
  id: uuid("id").defaultRandom().primaryKey(),
  userId: text("user_id").notNull().unique(),

  // Stripe IDs (safe to store per Stripe best practices)
  stripeCustomerId: text("stripe_customer_id").notNull().unique(),
  defaultPaymentMethodId: text("default_payment_method_id"),

  // Optional: Cache safe metadata from Stripe (for UI display)
  cardLast4: text("card_last4"),
  cardBrand: text("card_brand"), // "visa", "mastercard", etc.
  cardExpMonth: integer("card_exp_month"),
  cardExpYear: integer("card_exp_year"),

  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

export const ap2Transactions = product.table("ap2_transactions", {
  id: uuid("id").defaultRandom().primaryKey(),
  userId: text("user_id").notNull(),
  interviewId: uuid("interview_id").references(() => interviews.id),

  amountCents: integer("amount_cents").notNull(),

  // Stripe reference (store ID only, not full charge object)
  stripeChargeId: text("stripe_charge_id").notNull().unique(),

  // AP2 protocol data (CartMandate and PaymentMandate structures)
  cartMandate: jsonb("cart_mandate"),
  paymentMandate: jsonb("payment_mandate"),

  status: text("status").notNull().default("completed"), // "completed", "failed", "refunded"
  createdAt: timestamp("created_at").defaultNow().notNull(),
});
