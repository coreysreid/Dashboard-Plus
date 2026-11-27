# Practice: restore a backup onto a new computer (batch 23 item 123)

Written and run 27 November 2026 against Lane A's branch at `eeb6eac` (restore is on `main`: Settings → Restore
from a backup, `/settings/backups`). The run used a throwaway "new computer" data folder and a backup copied from
the invented Smith household. It shows what works **today** and where the words or screens would confuse a
household. Do this practice once a year, or before replacing a computer, with the old computer still working.

## What you need

- The old computer still working, or a USB stick or drive holding a backup file.
- The new computer, with Dashboard Plus downloaded but **not yet set up** (do not answer the setup questions).
- 20 minutes.

## Windows

1. **On the old computer**, press **Save and exit**. It makes a closing backup.
2. Open the `Dashboard Plus` folder, then `data`, then `backups`. Find the newest file, named like
   `close-2026-11-27-....db` or `daily-2026-11-27.db`. Copy it to the USB stick. **Do not rename it.**
   Alternatively, copy the whole `Dashboard Plus` folder (program and data together) to the stick. That is the
   simplest move: on the new computer you open the copied folder and you are done (skip to step 8).
3. **On the new computer**, unzip Dashboard Plus (see the read-me, including "Windows protected your PC").
4. Open the new `Dashboard Plus` folder, then `data`. If there is no `backups` folder inside `data`, double-click
   **Open Dashboard** once and close it again with **Save and exit**, without answering the setup questions.
   (Today the folder is only made when the program first runs.)
5. Copy the backup file from the stick into `Dashboard Plus\data\backups`.
6. Double-click **Open Dashboard**. It shows **Welcome to Dashboard Plus** and the setup questions. **Do not answer
   them.** In the browser's address bar, change the end of the address to `/settings/backups` and press Enter.
7. Under **Your backups**, find the copy, press **Look** and check **What is in it** against what you expect (for
   example People 14, Stock items 28). Press **Restore this backup**.
8. The page says **"Done. You are now using the records from the backup made …"**. Press **Keep the restored
   records** once you have checked (below), or **Undo restore**.

## Mac (preview build)

Steps 1 and 5 differ: the data is not next to the app. It is in your account's
`~/Library/Application Support/Dashboard Plus`. In Finder, choose **Go → Go to Folder…** and paste that path.
The backups are in its `backups` folder. On the new Mac, open the app once and quit it with **Save and exit**,
then copy the backup into the same folder and carry on from step 6.

## Check afterwards (about 5 minutes)

1. **Home:** the household's name and the drinking water days look the same as on the old computer.
2. **People:** the count matches, and one person's phone number is right.
3. **Private details:** open one person's Important details and press **Show**. The detail is there, because
   private details are in the backup.
4. **Needs attention and Things to do:** the same tasks are due.
5. **Settings:** country and region are right. Time zone: if the new computer is in another time zone, check the
   household's time zone in Settings.
6. **Settings, Helpers:** helper keys are **not** in a backup ("Helper keys are not part of a backup"). Make new
   keys for any assistant you use.
7. **Settings, backups:** the **second copy** setting came from the old computer. Check it is how you want it on
   this one.
8. Print the emergency sheet and compare it with the old one.
9. Only then press **Keep the restored records**. Keep the stick and the old computer's folder for a month.

## Where today's words or screens would confuse a household, worst first

1. **No way in from the setup page.** A new computer opens on **Welcome to Dashboard Plus** with setup questions,
   and nothing says "Already using Dashboard Plus on another computer? Restore a backup". The household must type
   `/settings/backups` into the address bar. **Suggested:** a first line on the setup page: **"Moving from another
   computer? Restore a backup instead"**, linking to `/settings/backups`, with the words: **"Put the backup file in
   this folder first: <the data folder's backups folder, shown in full>."**
2. **A renamed copy is invisible.** Only the program's own names are listed (`restore.NAME`). A file downloaded
   twice (`daily-2026-11-27 (1).db`) or renamed "Smith backup.db" does not appear, with no message. The drill
   copied `daily-2026-11-27 (1).db` next to the original, and only one Daily row showed. **Suggested:** list any
   `.db` file in the backups folder, checked as usual, with the words **"This file has been renamed; it is shown
   because it is in the backups folder."** Or add **Restore from a file…** (an upload box) on the backups page.
3. **"Made" is the time the file was copied.** The drill's copy, made at 15:38, showed **"27 Nov 2026 at 16:44"**,
   because "Made" is the file's modified time. Downloads and some copy tools reset that time, so a household may
   pick the wrong copy. **Suggested:** read the time from inside the backup (its last change) and say **"Last
   change in it: 27 Nov 2026 at 15:38 · copied here 27 Nov 16:44"**.
4. **"0 (different)" on every row.** On a new computer, "What is in it" compares with an empty household, so every
   row says **"0 (different)"**. **Suggested:** when the current household is empty, drop the Now column and say
   **"This computer has no records yet, so restoring adds everything below."**
5. **No backups folder until the first run.** Step 4 exists only because `data\backups` is made at the first run.
   **Suggested:** the restore page names the folder in full, makes it if missing, and offers **Open this folder**.
6. **Mac's second copy goes to a Linux-style folder.** `backups.default_extra_dir` returns
   `~/.local/share/dashboard-plus/backups` on a Mac (only Windows has its own case). A Mac household looking in
   Library will not find the second copy. **Suggested:** `~/Library/Application Support/Dashboard Plus/second-copy`
   or similar, and say the real folder on the backups page.
7. **Helper keys and the second-copy setting.** The page says helper keys are not part of a backup, which is right.
   It does not say that settings such as the second copy come across. **Suggested:** **"Your settings come from the
   backup too (country, backups, sharing choices). Check them in Settings."**

## What worked in the drill

The backup was listed and **Check passed**. **Look** showed every list's count, and **Restore this backup** worked
before setup. Home then showed the Smith household. **Undo restore** and **Keep the restored records** were offered
with clear words ("Your records from before were kept as a backup called "Before a restore"").

## Limits

Run on Linux with Lane A's code. Windows Explorer and Finder were not used, so steps 2, 4 and 5 are written from
the README and the code. On a real Windows or Mac computer User 1 should check them once.
