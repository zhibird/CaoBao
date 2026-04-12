# SQLite Backup And Future Migration Notes

This upgrade does not migrate historical SQLite data into PostgreSQL. The SQLite database should now be treated as a historical snapshot, not the active runtime database.

## Current policy
- PostgreSQL is the primary database for application runtime.
- SQLite should be kept as a backup or inspection artifact.
- Prefer storing the backup outside the repository so it does not get committed by accident.
- Prefer a dated filename such as `CaiBao_backup_2026-04-12.db`.

## Recommended backup workflow
1. Locate the current SQLite file you want to preserve.
2. Copy it to a backup directory outside the repo.
3. Mark the copied file read-only.
4. Record where the backup lives and what date it represents.

Example PowerShell flow:

```powershell
$backupDir = "D:\backups\CaiBao"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
Copy-Item -LiteralPath "D:\work\CaiBao\CaiBao.db" -Destination "$backupDir\CaiBao_backup_2026-04-12.db"
(Get-Item "$backupDir\CaiBao_backup_2026-04-12.db").IsReadOnly = $true
```

Adjust the source path if your legacy SQLite file lives somewhere else.

## How to inspect legacy SQLite data safely
- Best option: open the backup with a SQLite browser or ad hoc query tool.
- If you need to point the app at SQLite for local debugging, do it only in a non-Docker local run.
- Do not aim the app at your read-only archival backup. Copy the backup to a disposable debug file first.

Example local override:

```env
DATABASE_URL=sqlite:///C:/Users/your-name/AppData/Local/CaiBao/CaiBao.db
DB_LEGACY_INIT_ENABLED=true
```

## What a later full migration should include
1. Keep a frozen SQLite backup before any import attempt.
2. Provision PostgreSQL and run `alembic upgrade head`.
3. Write a one-off import script that maps legacy SQLite rows into the PostgreSQL schema.
4. Validate row counts, primary/foreign key integrity, timestamps, booleans, and nullable fields.
5. Smoke test the application against the imported PostgreSQL data.
6. Keep the original SQLite snapshot available for rollback and audit.

## Decision boundary
Do the full migration only when one of these becomes true:
- Existing chat or memory history has real demo value.
- The imported dataset is needed for a public or interview-facing environment.
- Database migration itself becomes part of the project story you want to showcase.
