# Interview Agent - Pending Features

## Fix UX and UI using Gemini 3.0
## Smotthen Interview Conversation Flow
## Design Interview flow with Remote Agents
## Canvas Screenshots to Remote Agents
## Interview Feedback System

## Paymeny veriifcaiton

Yes, Google Agent should verify payment.

  Currently, it only signs the cart JWT (creating mandate) but doesn't verify payment completion before conducting the interview.

  Security gap:
  - No verification that payment was actually completed before conduct_interview skill runs
  - Anyone could call the interview skill directly without paying

  Best practice:
  - Verify JWT signature when receiving payment mandate (check cart wasn't tampered)
  - Store payment proof/receipt in session state
  - In conduct_interview skill: check if session has valid payment_proof before proceeding
  - ADK supports session-based authorization - you can gate tool execution on payment status

  Simple fix: Add payment verification check at start of conduct_interview tool - reject if no valid payment receipt in
  session/context.

Also, check frontend payment apis follwo ap2 specs

Based on my analysis of your AP2 implementation against the official spec, here's what I found:

  ✅ What's Correct:

  1. Google agent (payment_tools.py): Uses proper AP2 types (CartMandate, CartContents, PaymentRequest)
  2. Orchestrator (payment_flow.py): Uses AP2 types for PaymentMandate creation
  3. A2A communication: Properly uses DataPart/TextPart in artifacts
  4. Payment flow sequence: Orchestrator → Get token → Create mandate → Charge → Receipt

  ❌ AP2 Spec Violations:

  Critical Issues:

  1. Frontend APIs don't use AP2 types - Both /api/payments/get-token and /api/payments/execute use plain JSON instead of
  importing/validating AP2 types
  2. Wrong DataPart keys in A2A messages:
    - Should be: "ap2.mandates.CartMandate" (spec line 154)
    - Currently: "cart_mandate"
    - Should be: "ap2.mandates.PaymentMandate" (spec line 254)
    - Currently: "payment_mandate"
  3. Missing PaymentMandate.user_authorization - Spec requires cryptographic user signature (line 282 in a2a-extension.md)
  4. Payment token incomplete - Token should include credentials_provider_url for proper AP2 flow (merchant needs to contact CP for
  credentials per spec line 294)

  Pattern Deviations:

  5. No transaction challenge flow - AP2 spec shows OTP/step-up authentication pattern
  (merchant_payment_processor_agent/tools.py:105-133)
  6. Cart signature verification incomplete - Frontend computes hash but doesn't verify JWT signature
  7. PaymentReceipt structure - Missing payment_method_details field expected by spec

  Recommendation:

  The backend (orchestrator + Google agent) follows AP2 well, but frontend needs to adopt AP2 types and use proper A2A data keys to be
  fully spec-compliant.