# B2 Change Calendar and Freeze Policy

## Regular Change Windows

- Standard production change windows:
- Tuesday `14:00-17:00` (Asia/Shanghai)
- Thursday `14:00-17:00` (Asia/Shanghai)

## Freeze Windows

- Month-end freeze: last `2` calendar days of each month.
- Shopping festival freeze: `11-10` to `11-12`.
- Spring Festival freeze dates are published each year by SRE PMO.

## Emergency Change Rules

- Emergency change is allowed during freeze only if both are true:
- business impact is `P1` or above
- on-call director approves
- SRE must stay online during full execution and verification.

## Communication Rules

- Regular changes require stakeholder notice at least `24 hours` in advance.
- Batch data migration is allowed only in `01:00-05:00`.
