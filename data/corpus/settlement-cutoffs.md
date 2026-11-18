# Settlement Cut-off Times

Each scheme has a daily cut-off after which payments roll to the next business day. For
TARGET2 the cut-off is 17:00 CET for customer payments and 18:00 CET for interbank
payments. For CHAPS the cut-off is 17:40 UK time. SEPA credit transfers submitted after
16:00 CET settle in the next cycle.

The scheduler warns at cut-off minus thirty minutes if the pending queue holds more than
one thousand payments, and pages the on-call at cut-off minus ten minutes if the queue is
still non-empty. Missing a cut-off is a client-impacting event and is reported to the
payments operations lead the same day.

Cut-off times are held in the `scheme_calendar` table, which also carries scheme holidays.
The table is loaded at start-up and refreshed hourly; a stale calendar has previously
caused payments to be queued on a scheme holiday and released a day late. Verify the
calendar refresh timestamp when investigating unexpected queuing.

Payments that miss a cut-off are not failed. They are re-dated to the next business day
and their `IntrBkSttlmDt` is updated, which will re-trigger the settlement date validation
rule.
