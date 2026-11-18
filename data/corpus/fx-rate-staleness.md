# FX Rate Staleness

Foreign exchange rates are refreshed every sixty seconds from the rates service and cached
locally. A rate older than one hundred and twenty seconds is considered stale and is not
used for a new quote; the request fails with `FX_RATE_STALE` rather than quoting an old
rate.

The rate applied to a payment is the rate quoted at booking, not the rate at settlement,
and the quote id is stored on the payment. This is the single most common source of
apparent amount mismatches in reconciliation: the ledger and the statement can differ
because the rate moved between the two points in time, and that is correct behaviour
rather than a defect.

Quotes expire after five minutes. A payment submitted with an expired quote is rejected
and the client must re-quote, because honouring an expired quote transfers market risk to
the bank.

During a rates service outage, no fallback to a previous day's rate is permitted. Cross
currency payments queue until rates are available, and same-currency payments are
unaffected.
