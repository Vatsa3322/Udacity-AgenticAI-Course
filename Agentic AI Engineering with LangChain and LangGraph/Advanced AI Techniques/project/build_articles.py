"""Generates data/external/cultpass_articles.jsonl (4 original + 11 new = 15 articles).
Run once from the project root:  python build_articles.py"""
import json

A = []
def add(title, content, tags): A.append({"title": title, "content": content, "tags": tags})

# ---- original 4 ----
add("How to Reserve a Spot for an Event",
"""If a user asks how to reserve an event:

- Guide them to the CultPass app
- Instruct them to browse the experience catalog and tap 'Reserve'
- If it's a premium or limited event, check if reservation confirmation is required via email
- Remind them to arrive at least 15 minutes early with their QR code visible

**Suggested phrasing:**
"You can reserve an experience by opening the CultPass app, selecting your desired event, and tapping 'Reserve'. Be sure to arrive 15 minutes early with your QR code ready.\"""",
"reservation, events, booking, attendance")
add("What's Included in a CultPass Subscription",
"""Each user is entitled to 4 cultural experiences per month, which may include:
- Art exhibitions
- Museum entries
- Music concerts
- Film screenings and more

Some premium experiences may require an additional fee (visible in the app).

**Suggested phrasing:**
"Your CultPass subscription includes 4 curated experiences each month. You can choose from museums, concerts, film events and more. Premium events may have an extra cost, which is shown during reservation.\"""",
"subscription, benefits, pricing, access")
add("How to Cancel or Pause a Subscription",
"""Users can manage their subscription via the app > 'My Account' > 'Manage Plan'.

- Cancel: Effective at the end of the billing cycle
- Pause: Preserves user data, resumes automatically when reactivated
- Do NOT offer refunds unless approved by support lead

**Suggested phrasing:**
"You can cancel or pause your subscription at any time via the 'My Account' section in the CultPass app. Cancelation takes effect at the end of your billing cycle.\"""",
"cancelation, pause, subscription, billing")
add("How to Handle Login Issues?",
"""Most login issues are resolved with password reset:

- Ask the user to tap 'Forgot Password' on the login screen
- Ensure they are using the correct registered email
- If they did not receive the reset email, check spam folder or retry after 10 minutes
- For persistent login issues, escalate to human support

**Suggested phrasing:**
"Try tapping 'Forgot Password' on the login screen. Make sure you're using the email associated with your account. If the email doesn't arrive, check spam or try again in a few minutes.\"""",
"login, password, access, escalation")

# ---- 11 new (billing, technical, account management, policy, accessibility ...) ----
add("Refund and Billing Dispute Policy",
"""Refunds are NOT issued by the support bot.

- Monthly fees are non-refundable once the billing cycle has started
- Exceptions (duplicate charge, charge after confirmed cancellation) must be approved by the support lead
- Never promise a refund; collect the charge date and amount and escalate to human support

**Suggested phrasing:**
"I understand your concern about this charge. Refund requests are reviewed by our support team, so I'll pass your details to them and they'll follow up.\"""",
"billing, refund, charge, dispute, escalation")
add("Accepted Payment Methods and Failed Payments",
"""CultPass accepts major credit/debit cards and Pix (Brazil).

- Update the payment method in the app > 'My Account' > 'Payment'
- A failed payment is retried automatically after 3 days; the subscription stays active for a 5-day grace period
- Common causes: expired card, insufficient funds, bank blocking international charges
- If the card is valid and the payment keeps failing, escalate to human support

**Suggested phrasing:**
"Your payment may have failed because of an expired card or a bank restriction. You can update your payment method under 'My Account' > 'Payment', and we'll retry automatically.\"""",
"billing, payment, card, pix, failed payment")
add("Basic vs Premium Tiers and Premium Experiences",
"""CultPass has two tiers: Basic and Premium.

- Basic: access to standard experiences
- Premium: access to standard AND premium experiences (e.g. exclusive tours, limited-capacity events)
- Basic members who try to reserve a premium experience are asked to upgrade
- Upgrade via app > 'My Account' > 'Manage Plan'; the new tier applies immediately and is billed pro-rata

**Suggested phrasing:**
"Premium experiences are available on the Premium tier. You can upgrade anytime under 'My Account' > 'Manage Plan'.\"""",
"premium, tier, upgrade, subscription, experiences")
add("QR Code Not Working at Check-in",
"""If the QR code does not scan at the venue:

- Increase screen brightness and remove screen protectors/glare
- Make sure the reservation shows status 'Reserved' in the app (not 'Pending' or 'Cancelled')
- Refresh the 'My Reservations' tab or log out and in again
- Venue staff can look up the reservation by the customer's name and email
- If still failing, escalate to human support

**Suggested phrasing:**
"Please raise your screen brightness and refresh 'My Reservations'. If the code still won't scan, show your name and email to the venue staff, who can check you in manually.\"""",
"qr code, check-in, attendance, reservation, troubleshooting")
add("App Crashes, Freezes or Won't Load",
"""Technical troubleshooting steps for the CultPass app:

- Update to the latest app version from the App Store / Google Play
- Force-close and reopen the app; restart the phone
- Check internet connection; try Wi-Fi vs mobile data
- Clear cache (Android) or reinstall the app (reservations are stored in the cloud and will not be lost)
- If it persists, escalate with device model, OS version and app version

**Suggested phrasing:**
"Please update the app, restart it and check your connection. Reinstalling is safe since your reservations are stored in your account.\"""",
"technical, app, crash, bug, troubleshooting")
add("How to Delete Your Account and Data Privacy",
"""Account deletion and privacy requests:

- Delete via app > 'My Account' > 'Privacy' > 'Delete Account'
- Active subscriptions must be cancelled first; deletion is permanent after a 14-day recovery window
- CultPass follows LGPD/GDPR: users may request a copy of their data or its removal
- Data export requests are handled by human support (allow up to 15 days)

**Suggested phrasing:**
"You can delete your account in 'My Account' > 'Privacy'. Please cancel any active subscription first. Deletion becomes permanent after 14 days.\"""",
"account, delete, privacy, lgpd, gdpr, data")
add("Event Cancelled or Rescheduled by the Venue",
"""When a partner venue cancels or reschedules an experience:

- Customers are notified by push notification and email
- Cancelled events return the credit to the monthly quota automatically
- For a reschedule, the reservation moves to the new date; the customer can cancel it if the new date does not suit them
- Do not promise compensation beyond the quota credit

**Suggested phrasing:**
"If a venue cancels, the credit returns to your monthly quota automatically. If it is rescheduled, you can keep the new date or cancel and choose another experience.\"""",
"events, cancelled, rescheduled, quota, venue")
add("Blocked or Suspended Accounts",
"""An account may be blocked for policy violations (e.g. repeated no-shows, ticket resale, payment fraud).

- Blocked users cannot reserve experiences or change their plan
- Support agents must NOT reveal internal fraud details
- Never unblock an account; ask the user to wait for a human review and escalate to human support

**Suggested phrasing:**
"Your account is currently under review, so some actions are unavailable. I've asked our support team to look into it.\"""",
"blocked, suspended, account, policy, escalation")
add("No-Show and Reservation Cancellation Policy",
"""Cancelling a reservation:

- Cancel from app > 'My Reservations' at least 12 hours before the event to get the credit back
- Late cancellations and no-shows consume the monthly credit
- Three no-shows within 60 days may lead to temporary suspension

**Suggested phrasing:**
"You can cancel from 'My Reservations' up to 12 hours before the event to keep your credit. Later cancellations or no-shows use one credit.\"""",
"cancel reservation, no-show, quota, policy")
add("Accessibility and Special Assistance at Experiences",
"""CultPass encourages inclusive access:

- Each experience page lists accessibility info (wheelchair access, audio description, sign language)
- Users can add an accessibility note when reserving so the venue can prepare
- For needs not listed, escalate to human support, which contacts the venue directly

**Suggested phrasing:**
"Each experience lists its accessibility details. You can add a note when you reserve, and our team can contact the venue for specific needs.\"""",
"accessibility, inclusion, special needs, venue")
add("Changing Your Email, Name or Profile Details",
"""Profile updates:

- Name and phone: app > 'My Account' > 'Profile'
- Changing the login email requires verification via a code sent to the NEW address
- If the user no longer has access to the old email, escalate to human support for identity verification

**Suggested phrasing:**
"You can update your profile in 'My Account' > 'Profile'. To change your login email we'll send a verification code to the new address.\"""",
"account, profile, email, update, verification")

with open("data/external/cultpass_articles.jsonl", "w", encoding="utf-8") as f:
    for a in A:
        f.write(json.dumps(a, ensure_ascii=False) + "\n")
print(f"Wrote {len(A)} articles")
