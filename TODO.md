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