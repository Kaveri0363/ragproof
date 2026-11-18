# Duplicate Payment Detection

Duplicates are detected on the tuple of debtor account, creditor account, amount,
currency and `EndToEndId` within a rolling seventy-two hour window. The window is stored
in Redis with a TTL, and a cache miss falls back to a database query against the
`payment_dedupe` table so that a Redis outage degrades latency rather than correctness.

A detected duplicate is rejected with ISO reason code `AM05` and an alert is raised only
if the same tuple is seen more than three times in one hour, which usually indicates a
sender-side retry loop rather than a genuine double payment.

The seventy-two hour window is deliberate: shorter windows missed weekend resubmissions,
and longer windows caused false positives for legitimate recurring payments made on the
same day of consecutive months. Changing the window requires sign-off from payments
product, not just engineering, because it changes customer-visible rejection behaviour.

Genuine duplicates that reach settlement are corrected by a reversal, never by deleting
the payment record. The audit trail must show both the original and the reversal.
