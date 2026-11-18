# Canary Release and Rollback

Deployments to the payments service go out as a canary receiving five percent of traffic
for fifteen minutes, then twenty-five percent for fifteen minutes, then full rollout. The
canary is automatically rolled back if the error rate exceeds one percent or p99 latency
exceeds eight hundred milliseconds during either window.

Automatic rollback reverts the deployment but does not revert database migrations. All
migrations must therefore be backwards compatible with the previous application version;
this is why the expand-and-contract pattern is mandatory for column changes.

Rollback of a payments release does not undo payments already processed by the canary.
If a defect caused incorrect processing, rolling back stops the bleeding but a separate
remediation is always required for the affected payments.

Releases are frozen from 16:00 local time on the day before a scheme holiday and for the
whole of the last business day of the month, when settlement volumes peak. An exception
requires approval from the payments engineering lead.
