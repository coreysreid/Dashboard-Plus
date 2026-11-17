# When a copy or computer is lost

Household guide draft, 17 November 2026. **The Backups and export screens described here are planned, not shipped.** The current app saves verified daily and close copies, and Settings shows the latest backup result. A future household restore must follow [the restore flow](FLOW.md) before these steps can be published as in-app instructions. If the app cannot open, use a trusted computer helper; keep all surviving drives and folders until a copy has been inspected. Examples below are made up.

## The USB stick is lost

1. Keep the computer and any other backup drive safe. Open **Settings → Backups** on the computer and read the last successful computer-side copy time. A last attempt marked failed is not a usable copy.
2. If the missing stick held the active data folder, do not create a new empty household over the old folder name. In the planned **Backups and export** screen, choose a good computer-side copy and **Check this backup**. Check the household name, date, included modules and record counts.
3. Choose **Restore into a new folder** on a drive you control. Compare its last change and record counts with any current folder, then **Open restored copy** before **Use restored copy from now on**. Keep the old folder and the pre-switch snapshot.
4. A lost unencrypted stick may reveal private household details to whoever finds it. Treat phone numbers, medical notes and home locations on that stick as exposed; decide which account credentials or contact details need changing. The app cannot remotely erase a lost stick.

## The computer died

1. Keep the original data drive and any separate backup drive. Do not format either. On a replacement computer, install a compatible Dashboard Plus version and connect the drive with the most recent good copy. A backup from a newer app version may require updating the app first.
2. In the planned **Backups and export** screen, select **Check this backup**. The preview must say whether its database and any attachments are present, pass integrity checks, and show the copy date and version. If one copy fails, try the other physical copy.
3. **Restore into a new folder**, inspect records and an emergency sheet, and then **Use restored copy from now on**. Keep the source drive unchanged. The other computer's daily backup may be older than the lost computer's last work; the comparison must say so.
4. If the computer held the only copy, a household screen cannot recover it. Ask a qualified repair or recovery service before writing to that disk; the product must not promise recovery.

## A record was deleted by mistake

1. Open the record's **Recently deleted** area and use **Restore it** if it is still there. Check linked rows and the history. This is a record action, distinct from restoring the whole household.
2. If the record cannot be restored there, inspect a backup from before the deletion. Restore that backup **into a new folder** and open it to find the old record. The old backup is a snapshot: switching the whole household to it could lose later changes.
3. Compare the old record with the current household. Copy or re-enter the needed facts in the current folder, with the household's approval. Keep both folders until the result is checked. The planned restore does **not** merge records automatically.

## A backup will not open

1. Stop retrying against the same file and do not overwrite it. Check whether the USB is connected, the file is complete, and the app can read it. “Missing”, “Damaged” and “Cannot open” need different messages.
2. In **Check this backup**, read the integrity and version reason. A damaged or unsupported copy must not offer **Restore**. Try the other physical copy, including a computer-side copy with the same date.
3. If no copy passes checks, preserve the current data folder and all backup files. A computer helper may inspect copies read-only. Do not run migrations against the only copy or turn a failed backup into the active household.
4. Once a good copy is found, restore to a **new folder**, inspect it, then choose whether to switch. A partial restore must say “Restore did not finish. Your current records were not changed.”

## Before choosing a copy

Use the newest **verified** copy that contains the records you need, not merely the newest filename. Read its household, timestamp with time zone, version, included attachments and counts. Current records stay in place while previewing. Switching makes a snapshot of the current folder; **Undo this restore** switches back but does not merge edits made after the switch. Keep the prior folder and snapshot until satisfied. An **Export everything** folder is readable data, not a restorable app backup; it contains private details and should be kept private.

Source and limits: [Dashboard Plus restore/export design](FLOW.md) and [acceptance checks](ACCEPTANCE.md), checked 17 November 2026; [SQLite backup API](https://www.sqlite.org/backup.html), checked 17 November 2026. The current backup service copies the database and verifies SQLite integrity, but it has no household restore, switch, attachment bundle or export screen; see [core needs](NOTES.md). The lost-stick privacy step is a precaution based on the current unencrypted data design, not a claim that the app can assess exposure.
