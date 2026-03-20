# B1 Release Gates and Canary Rules

## Mandatory Gates Before Production

- PRD and release scope approved by Product Manager.
- Automated test coverage must be at least `85%`.
- Open `P0/P1` bugs must be `0`.
- Service latency `p95` must stay below `250ms`.
- Security scan high-risk findings must be `0`.

## Approval Model

- Final production release requires joint sign-off from:
- `Tech Lead`
- `Product Manager`

## Canary Strategy

- Start with `10%` traffic canary.
- Canary observation window: at least `30 minutes`.
- Rollback trigger during canary:
- error rate over `2%` for `10 minutes`
- or latency increase over `40%` versus baseline
