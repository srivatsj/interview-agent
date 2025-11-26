/**
 * TypeScript types for Agent Payments Protocol (AP2)
 * Mirrors Python types from ap2 package
 */

// AP2 Data Keys (constants matching Python PAYMENT_RECEIPT_DATA_KEY, etc.)
export const AP2_KEYS = {
  CART_MANDATE: "ap2.mandates.CartMandate",
  PAYMENT_MANDATE: "ap2.mandates.PaymentMandate",
  PAYMENT_RECEIPT: "ap2.PaymentReceipt",
} as const;

// Payment Request Types (W3C Payment Request API based)

export interface PaymentCurrencyAmount {
  currency: string;
  value: number;
}

export interface PaymentItem {
  label: string;
  amount: PaymentCurrencyAmount;
}

export interface PaymentMethodData {
  supported_methods: string;
}

export interface PaymentDetailsInit {
  id: string;
  total: PaymentItem;
  display_items?: PaymentItem[];
}

export interface PaymentRequest {
  method_data: PaymentMethodData[];
  details: PaymentDetailsInit;
}

export interface PaymentResponse {
  request_id: string;
  method_name: string;
  details: Record<string, any>;
  shipping_address?: any;
  payer_email?: string;
}

// Cart Mandate Types

export interface CartContents {
  id: string;
  user_cart_confirmation_required: boolean;
  payment_request: PaymentRequest;
  cart_expiry: string; // ISO 8601 datetime
  merchant_name: string;
}

export interface CartMandate {
  contents: CartContents;
  merchant_authorization: string; // JWT
}

// Payment Mandate Types

export interface PaymentMandateContents {
  payment_mandate_id: string;
  timestamp?: string; // ISO 8601 datetime
  payment_details_id: string;
  payment_details_total: PaymentItem;
  payment_response: PaymentResponse;
  merchant_agent: string;
}

export interface PaymentMandate {
  payment_mandate_contents: PaymentMandateContents;
  user_authorization?: string; // JWT with user's digital signature
}

// Payment Receipt Types

export interface PaymentStatusSuccess {
  merchant_confirmation_id: string;
  psp_confirmation_id?: string;
  network_confirmation_id?: string;
}

export interface PaymentStatusError {
  error_message: string;
}

export interface PaymentStatusFailure {
  failure_message: string;
}

export type PaymentStatus =
  | { status: "success"; details: PaymentStatusSuccess }
  | { status: "error"; details: PaymentStatusError }
  | { status: "failed"; details: PaymentStatusFailure };

export interface PaymentReceipt {
  payment_mandate_id: string;
  timestamp: string; // ISO 8601 datetime
  payment_id: string;
  amount: PaymentCurrencyAmount;
  payment_status: PaymentStatus;
  payment_method_details?: Record<string, any>;
}

// Payment Token (Credentials Provider)

export interface PaymentToken {
  payment_method_id: string;
  stripe_customer_id: string;
  issued_at: string; // ISO 8601 datetime
  credentials_provider_url?: string; // AP2 spec requirement
}

// Type Guards

export function isSuccessStatus(status: PaymentStatus): status is Extract<PaymentStatus, { status: "success" }> {
  return status.status === "success";
}

export function isErrorStatus(status: PaymentStatus): status is Extract<PaymentStatus, { status: "error" }> {
  return status.status === "error";
}

export function isFailureStatus(status: PaymentStatus): status is Extract<PaymentStatus, { status: "failed" }> {
  return status.status === "failed";
}

// Validation Helper

export function validatePaymentReceipt(data: any): data is PaymentReceipt {
  return (
    data &&
    typeof data.payment_id === "string" &&
    typeof data.payment_mandate_id === "string" &&
    data.amount &&
    typeof data.amount.currency === "string" &&
    typeof data.amount.value === "number" &&
    data.payment_status &&
    typeof data.payment_status.status === "string"
  );
}
