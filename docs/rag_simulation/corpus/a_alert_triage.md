# A1 Alert Triage Runbook

## Severity and SLA

- `P1`: Core transaction unavailable, impact over 30% active users.
- `P1` first response SLA: `5 minutes`.
- `P1` war room start SLA: `10 minutes`.
- `P2`: Core feature degraded, impact 5% to 30% users.
- `P2` first response SLA: `15 minutes`.
- `P3`: Non-core feature issue with workaround.
- `P3` mitigation plan SLA: `4 hours`.

## First 10 Minutes Checklist

1. Confirm alert validity and record first seen timestamp.
2. Check recent deploys/config/database migrations in the last 30 minutes.
3. Assign three roles:
- `Incident Commander (IC)`
- `Technical Owner`
- `Comms Owner`
4. Post first incident update to status channel within `10 minutes`.

## Update Cadence

- `P1`: update every `10 minutes`.
- `P2`: update every `20 minutes`.
- `P3`: update every `60 minutes`.

## Mandatory Incident Fields

- `incident_id`
- `service_name`
- `impact_scope`
- `owner`
- `next_update_at`
