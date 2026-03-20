# A2 Database Backup and Restore SOP

## Backup Policy

- Full backup schedule: every day at `02:30` (Asia/Shanghai).
- Incremental backup interval: every `30 minutes`.
- Binlog archive interval: every `5 minutes`.

## Retention

- Full backups retained for `35 days`.
- Incremental backups retained for `7 days`.
- Binlog retained for `14 days`.

## Recovery Objectives

- Core order database `RPO`: `15 minutes`.
- Core order database `RTO`: `45 minutes`.
- Non-core analytics database `RTO`: `4 hours`.

## Restore Drill and Verification

- Restore drill frequency: `quarterly`.
- Drill completion report due: within `2 business days`.
- Post-restore checks must include:
- row count verification
- checksum verification
- critical query latency check
