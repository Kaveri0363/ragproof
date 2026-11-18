# pacs.008 Message Validation

Every inbound pacs.008 credit transfer is validated in three stages before it reaches the
payment engine. Stage one is XSD validation against ISO 20022 PSDP v1.4.5. Stage two is
business rule validation: the debtor and creditor agent BICs must be present and eleven
characters, the settlement amount must be positive, and `IntrBkSttlmDt` must be within
five business days of the message timestamp. Stage three is duplicate detection against
the `EndToEndId` window described in the duplicate-detection runbook.

A message failing XSD validation is rejected immediately with a pacs.002 status report
carrying reason code `FF01` and never enters the retry pipeline. Business rule failures
produce reason code `AM05` for duplicates, `AC03` for an invalid creditor account, and
`DT01` for a settlement date outside the permitted window.

Validation failures are logged to the `payments.validation.rejected` topic with the
original message id, the failing rule id, and the field path that failed. Do not
re-submit a rejected message by hand: the correct action is to ask the sending
institution for a corrected message with a new `MsgId`. Manual resubmission of the same
`MsgId` will be caught by duplicate detection and rejected with `AM05`, which looks like
a platform bug during incident review but is expected behaviour.
