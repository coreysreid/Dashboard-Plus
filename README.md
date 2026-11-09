# Dashboard Plus

**Look after what your household has.**
Know what you have, where it is, and when it's running out.

A free, portable, local-first "CRM for a home". Track the pantry and when to
reorder, the weekly shopping, emergency water, the tools and screws you have
stacked away, your pets, and anything else you care about: an art project, an electronics
hobby, Lego sets you flip, a wine collection. See it in charts, and
get gentle questions that help you understand *why* numbers change. The habit
of looking after what you have is what makes a home resilient.

Everything stays on your own computer. Nothing is sent anywhere unless you
switch on an optional outside source.

**Status: an early test version of the first release (M1).** It works, but it
is new: keep a copy of anything important somewhere else too. See
[`docs/ROADMAP.md`](docs/ROADMAP.md) for what comes next.

## What it does today

- **People:** who lives here, family, neighbours, the doctor and the vet; *Who
  to call*, in order; important details such as allergies, hidden on screen
  until you choose to show them.
- **A one-page emergency sheet** to print and put on the fridge. It needs no
  internet. A second version also lists the medical details.
- **Household stock:** what you have, where it is kept, how many to keep at
  least, and when it expires. Record what comes in and goes out (bought, used,
  expired, thrown away, given away) and the count updates itself.
- **Needs attention:** what is running low, what expires soon, about how many
  days of water you have for the people (and pets) in the house, and details
  worth filling in, such as an emergency contact with no phone number.
- **Automatic backups**, every day and every time you close it safely.

## Using it on Windows

You need Windows 10 or 11. Nothing is installed, no administrator rights are
needed, and no settings on the computer are changed. It runs happily from a
USB stick.

1. **Get the zip.** Until the first release is published, the latest build is
   on the [Actions page](https://github.com/coreysreid/Dashboard-Plus/actions):
   open the newest run on `main` with a green tick and download
   **dashboard-plus-windows** under *Artifacts* (you need to be signed in to
   GitHub). Inside is `Dashboard-Plus-<version>-windows.zip`.
2. **Unzip it** where you want it to live: your Documents folder or a USB stick.
   Right-click the zip, choose *Extract All…*, then *Extract*. You get a folder
   called `Dashboard Plus`.
3. **Double-click `Open Dashboard`.** A small black window opens (leave it
   open while you use the dashboard) and your browser shows the dashboard.
4. **Answer the setup questions:** who lives here, your country and type of
   home, and what you want to track. You can change these later in *Settings*.

### "Windows protected your PC"

The first time, Windows will probably show a blue box saying **"Windows
protected your PC"** and **"Unknown publisher"**. This is because Dashboard Plus
is free and not signed with a paid certificate, not because anything is wrong
with it. To carry on:

1. Click **More info**.
2. Check the file is `Open Dashboard.bat`, then click **Run anyway**.

Windows may ask again for *Close Dashboard safely*; answer the same way. To
stop these questions for good, before unzipping, right-click the zip, choose
*Properties*, tick **Unblock** at the bottom and click *OK*. Only do this for a
zip you downloaded from this project's GitHub page.

Dashboard Plus listens only on this computer (the address starts with
`127.0.0.1`), so no other device can open it.

### Closing it

Click **Close safely** at the top of the page, or double-click `Close Dashboard
safely` in the folder. It makes a backup and finishes writing before it stops.
**Always do this before unplugging a USB stick.**

### Where your data is

- Your records are in the `data` folder inside `Dashboard Plus`. **This folder
  is not encrypted:** anyone who has the folder (or the USB stick) can read it.
  Keep the stick somewhere safe.
- Backups are kept in two places: `data\backups`, and on the computer itself in
  `%LOCALAPPDATA%\Dashboard Plus\backups` (paste that into the File Explorer
  address bar to open it). The last 14 daily backups and 10 closing backups
  are kept.
- To **update**, close the dashboard, then replace everything in the
  `Dashboard Plus` folder **except the `data` folder**. The next start backs up
  your data before changing anything.
- To **start a fresh copy** for someone else, copy the folder without its
  `data` folder; they get their own setup questions.

### If something goes wrong

Error pages explain the problem in plain words and offer **Save a report**,
which writes a file in the `data\reports` folder. It holds technical details
about the problem; read it before sharing it with anyone. Report problems on the
[Issues page](https://github.com/coreysreid/Dashboard-Plus/issues), and never
include real names, phone numbers or other personal details.

## About the project

Start with the documents in `docs/`:

- [`docs/VISION.md`](docs/VISION.md): what this is, who it is for, what it will never be
- [`docs/CORE.md`](docs/CORE.md): the one-page v1 promise
- [`docs/ROADMAP.md`](docs/ROADMAP.md): the milestones and what comes first
- [`docs/JOURNEYS.md`](docs/JOURNEYS.md): short stories of real use
- [`docs/DESIGN.md`](docs/DESIGN.md): how it is built
- [`docs/INFLUENCES.md`](docs/INFLUENCES.md): the ideas we build on, and their authors

## Licence

MIT. Copyright (c) 2026 Corey Reid. See [`LICENSE`](LICENSE).

## For contributors

The checks need only Python. The program and its tests need a few pinned
libraries, installed with their checksums verified. From the project folder:

```bash
python tools/check_all.py            # every check below, with one command
python tools/check_privacy.py        # nothing personal may be committed
python tools/check_indexes.py        # every folder has a current INDEX.md
python tools/make_project_map.py     # regenerate PROJECT_MAP.md
pip install --require-hashes -r requirements.lock
PYTHONPATH=src python -m unittest discover -s tests
PYTHONPATH=src python -m dashboard --data <a folder outside this project>   # opens the dashboard in your browser
python tools/make_migration.py <module> --name <what_changed>   # after editing a module's tables.toml
```

On Mac or Linux, running from the project folder as above is the way to use it
for now; the portable folder is Windows only.

GitHub runs the same checks on Windows and Linux for every change. Start at
[`INDEX.md`](INDEX.md) and follow the index in each folder. See
[`AGENTS.md`](AGENTS.md) for the working rules.
