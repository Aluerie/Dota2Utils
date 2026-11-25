# 📝 TODO

## ⏰ ItemBuilds on a schedule

Add `uv run ItemBuilds schedule` to register a Windows Task Scheduler job, so guides stay fresh without running the tool by hand.

- Run daily and/or at logon. Make the frequency an option, e.g. `--daily` / `--at-logon`.
- The task runs `uv run ItemBuilds` in the repo folder. Use the full path to `uv.exe`, because the Task Scheduler `PATH` is minimal.
- Use `schtasks /Create ... /F`, so running the command again updates the task instead of failing.
- Add `uv run ItemBuilds unschedule` to remove the task.
- Logs: the task has no console, so also write loguru output to a rotating file, e.g. `ItemBuilds/.temp/logs/`, to show what a background run did.
- The old `ItemBuilds-D2PT-Scrape/create_scheduled_task.bat` (deleted, still in git history) did this with a `.bat` file and screenshots of the Task Scheduler UI. Look there for the settings that worked.
