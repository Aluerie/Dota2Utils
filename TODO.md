# 📝 TODO

## ⏰ ItemBuilds on a schedule

Add `uv run ItemBuilds schedule` to register a Windows Task Scheduler job, so guides stay fresh without running the tool by hand.

- Run daily and/or at logon. Make the frequency an option, e.g. `--daily` / `--at-logon`.
- The task runs `uv run ItemBuilds` in the repo folder. Use the full path to `uv.exe`, because the Task Scheduler `PATH` is minimal.
- Use `schtasks /Create ... /F`, so running the command again updates the task instead of failing.
- Add `uv run ItemBuilds unschedule` to remove the task.
- Logs: the task has no console, so also write loguru output to a rotating file, e.g. `ItemBuilds/.temp/logs/`, to show what a background run did.
- The old `ItemBuilds-D2PT-Scrape/create_scheduled_task.bat` (deleted, still in git history) did this with a `.bat` file and screenshots of the Task Scheduler UI. Look there for the settings that worked.

## 🧠 Ability and talent stats in the guides

Put the popular skill order and talent picks into each hero guide as **hover text only**, not as the guide's suggested build, so Dota doesn't push those choices when leveling up.

- Where: the guide's `ItemTooltips` section (already in our guides, currently empty). Attach the text to an item that's always in the guide, e.g. a Tango in "Consumables": hovering it shows the stats.
- What to show, e.g.:
  - Skill order for the first levels: `Q W Q E Q R ...`
  - Talents per level with pick rates: `10: +20 Attack Speed (62%) / +200 Health (38%)`
- Data sources: D2PT (check if its hero pages have an ability/talent endpoint like `item-overview`), else Stratz (`heroStats` has ability and talent stats, and we already have a token and client).
- First check that Dota really shows `ItemTooltips` text in the guide UI, how long it can be, and whether line breaks work.
- Leave the guide's own ability build (`AbilityBuild`, if any) untouched.
