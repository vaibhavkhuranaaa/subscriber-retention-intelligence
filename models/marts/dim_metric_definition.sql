select * from (values
    ('active_subscribers', 'Subscribers with a reconstructed valid membership on the history cutoff.', 'subscriber at cutoff', 'higher', 'Reconstructed from ordered transactions; not source-reported.'),
    ('gross_receipts', 'Sum of actual amount paid in source currency.', 'subscription transaction', 'context', 'Not recognized revenue, MRR, ARR, or accounting treatment.'),
    ('observed_renewal_rate', 'Label-eligible subscribers not observed as churned inside the challenge renewal window divided by eligible subscribers.', 'label window', 'higher', 'Observed challenge outcome; not intervention uplift.'),
    ('observed_churn_rate', 'Label-eligible subscribers observed as churned inside the challenge renewal window divided by eligible subscribers.', 'label window', 'lower', 'Challenge-compatible 30-day renewal-gap definition.'),
    ('cancellation_event_rate', 'Cancellation-marked transactions divided by subscription transactions through the cutoff.', 'subscription transaction', 'lower', 'Event rate, not unique-subscriber rate.'),
    ('listening_active_days', 'Subscriber-days with recorded listening inside the declared lookback window.', 'subscriber-day', 'context', 'Absence means no source listening row, not proven inactivity.')
) as definitions(metric_id, definition, grain, direction, limitation)
