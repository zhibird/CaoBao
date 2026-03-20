# B3 Incident Rollback Flow

## Decision and Ownership

- Rollback decision is made by:
- `Incident Commander`
- `Release Owner`
- If canary error rate exceeds `2%` for `10 minutes`, execute rollback within `5 minutes`.

## Rollback Steps

1. Stop rollout and freeze new deploy jobs.
2. Switch traffic to previous stable version.
3. Drain or replay impacted async queues.
4. Verify key SLOs return to baseline within `15 minutes`.

## Communication

- Incident status page update cadence: every `10 minutes`.
- Internal incident channel summary after rollback: within `15 minutes`.

## Mandatory Records

- Create rollback incident ticket with:
- trigger metric
- rollback start/end time
- owner and verifier
