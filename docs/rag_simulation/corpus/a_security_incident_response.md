# A4 Security Incident Response Playbook

## Detection and Trigger

- Suspicious login trigger: `5` failed attempts in `10 minutes` for one account.
- Credential stuffing trigger: failure rate above `20%` in a `15-minute` window.
- Token leak severity default: `P1`.

## Containment SLA

- Leaked token revocation SLA: `30 minutes`.
- Force password reset for high-risk accounts: within `2 hours`.
- Block malicious IP ranges: within `15 minutes` after confirmation.

## Notification and Compliance

- Legal/compliance notification SLA: `24 hours`.
- Customer communication starts after legal review is approved.
- Forensic evidence retention period: `180 days`.

## Post-Incident

- Security postmortem draft: within `24 hours`.
- Final report with action owners: within `5 business days`.
