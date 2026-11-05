# Demo video script

Target 2:30, limit 3:00. Voice-over in English. No third-party music.

**Accuracy / security gate:** This script currently demonstrates the **offline fake-PayPal mode** only. For the hackathon submission, show separately that the application really works with **PayPal sandbox and an AI tool**, or revise the video to include a visible genuine sandbox read/draft/send sequence. Do not present simulated failures/payments as provider-verified. The current unauthenticated app must remain **localhost-only**, not publicly hosted or tunneled. Do not record secrets or real customer data.

**0:00 – 0:20 · The problem**
"Small businesses spend hours chasing late invoices and guessing when cash will arrive. Invoice Steward is an AI agent that does the chasing and the forecasting, but never sends anything without you."

**0:20 – 0:50 · Forecast**
Show the headline with what is owed and what is at risk. Point at the chart and its range bars. "It learns how each customer really pays and simulates thousands of outcomes. This invoice, two months late, has under a 50% chance of being paid within 30 days."

**0:50 – 1:25 · Reminders**
Click *Remind my late customers*. Cards appear. "Each card shows exactly what will be sent." Click *Send reminder* on one: the stamp lands. "Ask again and it won't spam: there is a cooldown."

**1:25 – 1:55 · New invoice**
Click *Invoice Alba for a logo refresh*. Show the card, then click *Send invoice*.

**1:55 – 2:30 · Safety**
Open *Simulate a PayPal problem* and choose *PayPal sends it, but the answer is lost*. Prepare another invoice and send it. The card says it could not confirm the outcome. Click *Check PayPal*: done, and there is only one invoice. "The agent has no send tool, what you review is what is sent, and uncertain outcomes are verified, never blindly retried."

**2:30 – 2:45 · Close**
"Built on the PayPal Invoicing API and Claude. Open source, MIT."
