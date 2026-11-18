# On-call and Escalation

The payments rota runs a primary and a secondary on-call, each on a weekly shift starting
Wednesday at 10:00. The primary acknowledges within five minutes; if unacknowledged after
ten minutes the page automatically escalates to the secondary, and after a further fifteen
minutes to the engineering manager.

Severity one is defined as payments not settling, client funds at risk, or a regulatory
breach. Severity one requires an incident channel, an incident commander who is not the
person debugging, and a status update every thirty minutes. Severity two is degraded
performance without settlement impact and does not require an incident commander.

Anyone may declare a severity one incident. Declaring one and downgrading later is
explicitly encouraged; the review process treats a fast declaration as a good outcome
even when the incident proves minor.

Post-incident reviews are held within five business days and are blameless. The review
must produce actions with named owners and dates. An action without an owner is not an
action.
