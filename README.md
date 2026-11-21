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

**See it first:** [`docs/EXAMPLES.md`](docs/EXAMPLES.md) shows three made-up
households (a family with pets in Australia, three generations in the United
States, one person in the United Kingdom) at every stage, from the first start
to saving and exiting.

**Status: an early test version of the first release (M1).** It works, but it
is new: keep a copy of anything important somewhere else too. See
[`docs/ROADMAP.md`](docs/ROADMAP.md) for what comes next.

## What it does today

- **People:** who lives here, family, neighbours, the doctor and the vet; *Who
  to call*, in order; important details such as allergies, hidden on screen
  until you choose to show them.
- **A one-page emergency sheet** to print and put on the fridge. It needs no
  internet. A second version also lists the medical details.
- **Set up my home:** one page, offered after the welcome questions and always
  on Home and in Settings, to add your rooms and areas, the storage spots inside
  them (Kitchen › Pantry › Shelf 3), and which rooms connect, through a door,
  an open doorway, stairs or a door to outside.
- **Household stock:** what you have, where it is kept, how many to keep at
  least, and when it expires. Record what comes in and goes out (bought, used,
  expired, thrown away, given away) and the count updates itself.
- **Needs attention:** what is running low, what expires soon, about how many
  days of water you have for the people (and pets) in the house, and details
  worth filling in, such as an emergency contact with no phone number.
- **Things to do:** Today, This week, This month and This year (and No date
  yet) in one place, from the dates you already recorded: Home care and Garden
  jobs, alarm and kit checks, pet treatments, vehicle dates, document reviews,
  things lent out, and **Routines**, your own repeating tasks such as watering
  the pot plants or putting the bins out. Each task is finished the same way
  as on its own page (Home care's Mark done, Garden's Mark done, or Open record
  to update). Something late shows once, as "Due since", never as a pile of
  missed days or a streak; a repeat only ever offers the next date, and Undo
  puts a tick back straight after. Weeks start on the day you choose in Settings.
- **Have you thought about…?** (Readiness) 49 calm questions about fire,
  flood, storms, heat, power cuts, medical needs and leaving home quickly, each
  with the official page it came from and the date that page was checked. Only
  the questions that fit what you told Settings are asked (storeys, the things
  that can happen where you live, pets, mobility needs). Answer Yes, Not
  relevant or Not yet, or open Tell me more. When one of your records may
  already answer a question (a first aid kit with its place, an emergency
  contact with a phone number) it is offered for you to confirm, never
  answered for you; if that record changes, the question comes back. Home
  shows at most two at a time, and the count says how many you have looked
  at, never whether you are "safe".
- **Helpers (early):** give an assistant, such as an AI program, a key in
  Settings so it can look at the parts of your records you choose and suggest
  new ones. Nothing is added until you accept it on the Review page. Private
  details are never shared with helpers. A helper reading a receipt can show
  the line and price each row came from (for checking only, never saved), and
  can send a new Stock item with its first Stock in as one group: accepting
  the Stock in adds the item too, rejecting the item rejects both. A new Stock
  item can also arrive as one suggestion with its amount on hand, unit, use-by
  date and place, just like your own Add form: accepting it adds the item and
  its first batch together. Review says each Stock in plainly ("Add 1 pack
  of Red lentils on 20/11/26") and, after Accept all, what was added. A
  receipt line the helper could not match waits on Review with **Choose
  item** (pick one of your Stock items or make a new one, then confirm the
  amount and date) and **Skip line**, which you can undo until **Finish
  receipt review**. If a receipt looks like one already sent, by a helper or
  a spreadsheet import, Review says so and waits until you choose **Reject
  this copy** or **Keep this as another purchase**.
- **Starting message for your assistant:** each helper in Settings, Helpers
  has a message to copy into the assistant's chat. It lists the lists that
  helper may use, their fields, what is private, how stock amounts work and
  today's limits. It holds no records, private details or key. The assistant
  can read the same guide itself (the `dashboard_how_to_help` tool).
- **Connect an AI assistant:** assistant apps that support MCP can use a
  helper through the connector that comes with Dashboard Plus
  (`python -m dashboard.connector`). Settings, Helpers shows the settings to
  paste in. The key is a password, and an online assistant sees what the
  helper reads. Before sending the key, the connector checks that the address
  really is your Dashboard Plus, so an old address cannot catch it. The
  settings point to a small address file in the Dashboard Plus folder, so you
  paste them once and an ordinary restart needs no new copy. If a key was lost
  or may have been seen, **Make a new key** replaces it and keeps the helper's
  name, access and Review history.
- **Import from a spreadsheet:** bring rows from a CSV file into any list
  (Settings). You see which rows are ready and what is wrong with the rest
  before anything is sent, and nothing is added until you accept it on the
  Review page.
- **Automatic backups**, every day and every time you close it safely, and
  **Restore from a backup** in Settings: check a backup and compare it with
  now, put it back, and undo that if it was the wrong one.

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

Windows may ask again for *Save and exit Dashboard*; answer the same way. To
stop these questions for good, before unzipping, right-click the zip, choose
*Properties*, tick **Unblock** at the bottom and click *OK*. Only do this for a
zip you downloaded from this project's GitHub page.

Dashboard Plus listens only on this computer (the address starts with
`127.0.0.1`), so no other device can open it.

### Closing it

Click **Save and exit** at the top of the page, or double-click `Save and exit
Dashboard` in the folder. It makes a backup and finishes writing before it stops.
**Always do this before unplugging a USB stick.**

### Where your data is

- Your records are in the `data` folder inside `Dashboard Plus`. **This folder
  is not encrypted:** anyone who has the folder (or the USB stick) can read it.
  Keep the stick somewhere safe.
- Backups are kept in two places: `data\backups`, and on the computer itself in
  `%LOCALAPPDATA%\Dashboard Plus\backups` (paste that into the File Explorer
  address bar to open it). The last 14 daily backups and 10 closing backups
  are kept.
- To **go back to a backup**, open Settings, then *Restore from a backup*. Your
  records as they are now are copied first, so *Undo restore* can put them
  back. Helper keys are not part of a backup.
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

## On a Mac (preview, not signed yet)

There is an early **test build** for Macs. It is not yet signed or checked
("notarised") by Apple, so macOS will warn you before it opens. Use it only if
you are helping to test; a signed version comes later. It has only been built
and checked automatically on GitHub's Apple silicon Macs, not yet tried by a
person on a real Mac. You need macOS 11 (Big Sur) or later and a Mac with
Apple silicon; an Intel version is not built yet.

**Check your Mac first.** Choose **Apple menu, About This Mac**. Continue only
if **Chip** begins with M1, M2, M3 or a later Apple chip and your macOS version
is 11 or later. If it says **Processor: Intel**, this preview download is not
for your Mac.

1. **Get the zip.** Sign in to GitHub. Open the
   [Actions page](https://github.com/coreysreid/Dashboard-Plus/actions), choose
   the newest completed run whose branch is **main** and whose result is a green
   tick. Under *Artifacts*, download **dashboard-plus-macos-arm64-unsigned**.
   Finder now has an outer ZIP; open it, then open the
   `Dashboard-Plus-<version>-macos-arm64-unsigned.zip` inside it. If the
   artifact is missing or has expired, stop and ask for a new main build.
2. **Drag `Dashboard Plus.app` into your Applications folder.**
3. **Double-click Dashboard Plus.** The first time, macOS says it could not
   verify that Dashboard Plus is free of malware. Click **Done** (not *Move to
   Bin*). Then open **System Settings**, choose **Privacy & Security**, scroll
   down to the message about Dashboard Plus and click **Open Anyway**, then
   confirm with your password or Touch ID. You may need to allow each new
   unsigned preview build separately. If the warning or button is different
   from these steps, stop and tell us your macOS version and the words on
   screen. Do not turn off Mac security checks. On macOS 14 or earlier you can
   instead Control-click the app, choose **Open**, then **Open** again.
4. Your browser shows the dashboard. Answer the setup questions as on Windows.

There is no separate app window or Dock icon: after opening the app, look for a
new Dashboard Plus page in your browser. If it is not visible after about 20
seconds, bring your browser to the front and check its tabs. If you closed only
the tab, open the app once to bring the page back. To stop Dashboard Plus
itself, click **Save and exit** on that page and wait for **Saved and closed**.
If a failure alert appears, note its words (without personal details) for the
Issues page.

**Where your data is:** in this Mac account's Application Support folder,
separate from the app: `Library/Application Support/Dashboard Plus` inside your
home folder (in Finder, choose *Go*, *Go to Folder…* and paste
`~/Library/Application Support/Dashboard Plus`). Someone with access to this Mac
account or its backups may be able to read it. Replacing the app does not erase
it.

**To update:** choose **Save and exit** and wait for **Saved and closed**.
Download and unzip the new preview, then drag its **Dashboard Plus** app into
Applications; if Finder asks, choose **Replace**. Open it, follow any new
unsigned-app warning, and check that your existing records are still there. Do
not delete the Application Support folder during an update.

**To remove the app:** delete only **Dashboard Plus** from Applications. Delete
the record and backup folders only if you deliberately want to erase your local
copies, after checking any backup you want to keep. They are two separate
folders:

- `~/Library/Application Support/Dashboard Plus` (your records)
- `~/.local/share/dashboard-plus` (the second backup copy)

## About the project

Start with the documents in `docs/`:

- [`docs/VISION.md`](docs/VISION.md): what this is, who it is for, what it will never be
- [`docs/CORE.md`](docs/CORE.md): the one-page v1 promise
- [`docs/ROADMAP.md`](docs/ROADMAP.md): the milestones and what comes first
- [`docs/JOURNEYS.md`](docs/JOURNEYS.md): short stories of real use
- [`docs/DESIGN.md`](docs/DESIGN.md): how it is built
- [`docs/INFLUENCES.md`](docs/INFLUENCES.md): the ideas we build on, and their authors

## Licence

Dashboard Plus is free software: you can share it and change it under the
terms of the GNU Affero General Public License, version 3 or (at your choice)
any later version. See [`LICENSE`](LICENSE). Copyright (C) 2026 Corey Reid.

In plain words: use it at home freely. If you share a changed copy, or run a
changed copy for other people over a network, you must share your changes
under the same licence. It comes with no warranty (decision 0065).

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

On Linux, running from the project folder as above is the way to use it for
now. The portable folder is Windows only; Macs have their own app, built with
`python tools/build_macos.py` on a Mac (unsigned for now, decision 0096).

GitHub runs the same checks on Windows, Linux and macOS for every change. Start at
[`INDEX.md`](INDEX.md) and follow the index in each folder. See
[`AGENTS.md`](AGENTS.md) for the working rules.
