# Sanctions Screening Holds

Every payment is screened against the consolidated sanctions list before settlement. A
name match above the configured similarity threshold of eighty-five percent places the
payment on hold with status `SCREENING_HOLD` and creates a case in the compliance
workqueue.

Held payments are not rejected and must not be cancelled by engineering. Only a
compliance analyst may release or block a held payment; engineering's role is limited to
confirming that the hold was applied correctly and that the case reached the workqueue.

The screening service has a hard timeout of one and a half seconds. On timeout the
payment fails closed — it is held rather than allowed through — because settling an
unscreened payment is a regulatory breach while a delayed payment is a service issue.
This is the one place in the platform where availability is deliberately traded for
compliance.

Screening decisions and the list version used are written to the immutable audit log and
retained for seven years. If the screening service is degraded, escalate to the
compliance duty officer as well as the technology on-call, because a sustained screening
outage requires a regulatory notification if it exceeds four hours.
