# Reconciliation Breaks

The end-of-day reconciliation compares the internal ledger against the scheme statement
and reports any difference as a break. Breaks are classified as timing, amount, missing
or unexpected.

Timing breaks are the most common and usually self-resolve: a payment settled after the
statement snapshot appears on the next day's statement. A timing break older than two
business days is escalated as a genuine break.

Amount breaks are never self-resolving and always indicate either a rounding defect or an
FX rate applied at a different time than expected. Check the FX staleness runbook before
raising a defect, because most amount breaks in the last year were caused by a rate
refreshed between quote and settlement.

Missing breaks — present in the ledger, absent from the statement — are investigated by
querying the scheme reference in the ledger and confirming with the scheme gateway logs
that the message was actually transmitted. Unexpected breaks, present on the statement but
absent from the ledger, are the most serious and always page the on-call, because they can
indicate a settled payment the platform has no record of.

The reconciliation job runs at 22:30 local time and takes about forty minutes.
