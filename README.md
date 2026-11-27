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
- **Our way-out sketch:** your rooms drawn as boxes, floor by floor, with lines
  for the ways between them, doors to outside and your outside meeting place,
  plus the same facts as a list. It marks what still needs checking, prints on
  as many numbered pages as it needs, and always says it is a practice aid, not
  a certified or safe route. Codes and private details never appear on it.
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
  puts a tick (or a press of Mark done or Mark returned) back straight after.
  Weeks start on the day you choose in Settings.
- **The first charts:** *What is counted* on Home's water card shows each
  water item behind the days of drinking water, as a bar with its litres, and
  every item left out with the reason (not safe to drink, or not in litres).
  A pet's page shows its recorded weights as dots by date, and you can choose
  the pet and the dates. Each chart has a table with the same values, prints,
  and works with a keyboard or screen reader. They show what was written down,
  never a health or safety verdict.
- **Pet feeding log:** each time you put food in a pet's bowl, refill it or
  give a treat, from the pet's page with **Add food** (a phone-sized form that
  fills in the time now and, for you to check, your last choices). An amount is
  food *put out*, not food eaten. Home says, for each pet, "Rex · 2 feedings
  recorded today · 240 g put out", and the day's page adds up only matching
  units ("120 g and 1 pouch put out"; a scoop is never turned into grams) and
  says when an entry has no amount. A day with no entry says "No feeding entry
  recorded today", never that a pet was not fed. Days follow your household's
  own time zone. A **Pet feeding log** sheet prints every entry for the last 14
  days (or dates you choose) with each day's totals, or says the range is too
  long and offers shorter ones. A helper may suggest feedings; one that looks
  like an entry already there, or like another waiting, is marked **Possible
  repeat feeding entry** on Review with **Accept as another feeding** and
  **Reject this copy**.
- **Calendars and trends:** a pet's page shows a **Feeding calendar**: the
  month as a grid where each day with a feeding shows ● and how many, and
  Previous month and Next month. **Things to do** has a **Calendar** tab for
  Routines: ✓ Done and – Skipped on the day it happened, and each routine's
  next date once, ○ Due or ◇ Planned. Every mark has its own symbol as well
  as a colour, there is a legend, and the same days are listed in words. A
  blank day only means nothing was recorded; nothing is ever called missed.
  A pet's weights can be shown for the last 3 months, the last year or all
  dates, with "Since the reading before: up 0.3 kg, from 4.4 kg to 4.7 kg" in
  words and a line between readings, on a scale that still starts at zero.
  The **Calendar** tab now shows every dated list together: Home care's work
  done and Do again by dates, Garden jobs marked done and their due dates,
  each vehicle's registration, insurance and service dates, and each bill or
  policy's check date, each paper's review or renewal date, first aid kit
  checks, smoke alarm tests and the day a lent thing is due back, with each line in words starting with its list
  ("Home care · Clear the gutters: Job done"). **Show: All / Home care /
  Vegetable garden / ...** links keep one list at a time. A bill's amount and
  any private detail are never on a calendar.
  Earlier times show too: each earlier day a vehicle service, an alarm test,
  a return or a garden job was recorded as done stays on its day, read from
  the record's own history, marked "(an earlier time, from its history)". A
  date typed back to fix it or changed again the same day never counts, and
  an undone Mark done never shows. A date cleared a day or more after it was
  typed (a thing lent again) stays as a done day, and an old Mark done with a
  Done on typed later counts once, on the typed day. If one of these earlier
  days is wrong, **Not a done day — remove from the calendar** under its line
  takes it off (and off Jobs done per month), with **Undo**; the record's
  history keeps a line for it, with **Put back on the calendar**.
- **Bars over time:** a pet's page shows **Food put out per day** (or per
  week or month), in one unit at a time, such as grams or pouches, never added
  together or converted; a routine's page shows **Times done per month**; a
  person's page shows **Doses recorded per week**, every medicine together,
  with each medicine's own bars only after **Show**; until then the chart says
  "this person" and its chooser lists people by number. Every bar has its value in
  words and the same values are in a table; a day, week or month with nothing
  written down says "nothing recorded", never "missed", and this week or month
  is striped and says "so far".
  Garden jobs now keep a **Done on** date (Mark done fills in today; older
  jobs keep no date, never a guessed one), and the Garden calendar and list
  link to **Jobs done per month**: every job together, one count for each day
  a job was done.
- **What you paid and Spent per month:** when you save a bought Stock in, or
  later, you can type what you paid and say whether it is the total or the
  price for each one, in your household's currency (chosen in Settings). A
  receipt price a helper read stays on Review for checking and is never saved
  by itself. **Spent per month** (on Household stock) counts your Stock ins;
  **Show** adds up the prices, overall and for each category, one currency at
  a time. A Stock in without a price is counted, never read as zero, and the
  page says it covers only prices that were typed in. Prices stay on this
  computer and are never on lists, sheets, the export or a helper's screen.
- **Money back and a price on Review:** on a Stock in with a price, **Record
  money back** saves a refund tied to it, in the same currency and never more
  than was paid unless you tick that it is. **Spent per month** says it in
  words and in its table ("3.80 AUD spent, less 3.00 refunded") and never
  draws a negative bar. A refund never changes the stock; if the goods went
  back, you also record a Stock out with the reason **Returned to the shop**.
  On Review, a bought Stock in has **Save a price with this Stock in?**: you
  type the price (the paper's is shown beside it for checking and never
  filled in) and it is saved when you press Accept. A Stock in's page also
  shows its worked-out **Line total** after **Show**.
- **What happened, newest first:** a pet's page and a person's page end with
  one list of everything recorded for them, under month headings: each
  weigh-in with the change since the one before ("up 0.3 kg since 2 Oct"),
  each vet visit and treatment given, feedings as one line a day ("3 feedings
  recorded on Tue 24 Nov · 240 g put out"), and doses as one line a day that
  says only how many until **Show** names each medicine. Every kind has its
  own symbol beside its words, and **Earlier** goes back a page.
  A vehicle's page lists its odometer readings ("up 1,240 km since 2 Oct",
  only between readings in the same unit, never converted) and service
  estimates (never an amount); a Home care job's page lists the work done; a
  routine's page lists each time it was done or skipped. After **Show**, a
  dose reads in the medicine's own words, with no id.
- **Medicine doses:** each dose of medicine given to a person, from **Record a
  dose** on their page: the medicine is chosen from that person's own
  medication details (People → Important details), with the time now and, for
  you to check, the last medicine and who gave it filled in; an amount is
  optional and never copied from an earlier dose. The person's page says "1
  dose entry recorded today" and the times, nothing more; **Dose history**
  shows each medicine and amount only after **Show details**. The same
  medicine for the same person within two hours asks first, with **Keep this
  as another dose**. Doses are never on Home, a printed sheet, the
  spreadsheet export or visible to a helper, and nothing ever says a dose was
  missed. People only: pets keep their treatments in Pets. A **Dose
  calendar** on the person's page shows the month with ● and how many doses
  on each day, never which medicine or how much; **Show** on the calendar
  lists each day's doses. The list of every dose and each dose's own page say
  only "Private history — press Show to see it." until **Show** is pressed
  (a button, never a link), and so does any list marked private.
- **Vehicle running log:** what each vehicle's odometer showed and when, as
  dots on the vehicle's page ("Last recorded: 48,500 km on 20/11/26"), in the
  km or miles you choose in Settings and never converted. A reading lower than
  the last one, or in another unit, asks **Go back** or **Save as entered**
  first. A service's page lists its dealer, independent or other quotes with
  their dates; the amounts and what each covers stay private behind **Show
  estimated cost and scope**. They are estimates, not a bill or a
  recommendation, and the service date you typed stays the only reminder.
- **Bills and insurance:** each bill or policy with who provides it (from
  People), how often it comes and the next date you want to check it, and
  optionally a vehicle or a place. Thirty days before, Needs attention and
  Things to do say "bill check due", "policy check due" or "vehicle insurance
  review or renewal due"; nothing works out the next date and nothing says a
  bill was paid or cover is active. The amount, what it covers, the reference
  and notes stay private on this computer. If Vehicles already reminds you
  about car insurance, nothing moves until you choose **Keep reminders in
  Vehicles** or **Review and move to Bills**, one policy at a time, with
  **Transfer back** to undo; each policy keeps one reminder.
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
- **Think it through** (Readiness) eight calm practice runs, one question at
  a time: water behind a bathroom wall, a bedroom fire at night, a kitchen
  fire, a break-in at 2 am, the car stopping far from home, three days without
  power, a regional tap-water warning and a cyclone forecast (where cyclones
  are ticked in Settings). Each step shows the records that may help, such as
  your water shut-off and its place, or says exactly what is not recorded yet
  with a link to add it. Your own words stay private on this computer: never
  exported, sent or shown to a helper. Stop part-way and continue later, or
  save the practice with the date you choose to look again. Every drill first
  says to phone the emergency service if anyone is in danger (000, 911 or 999
  by country, otherwise your local number) and lists its sources with the date
  each was checked; it never says your home is safe.
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
  today's limits. It gives one invented example for each list with its own ways
  of working (pet weigh-ins, feedings, odometer readings, a routine's times, Garden
  jobs) and says what is never for a helper (medicines, prices, money back, codes:
  you type those in yourself), and that units and times follow your own day. It
  holds no records, private details or key. The assistant
  can read the same guide itself (the `dashboard_how_to_help` tool). While
  moving records in, Review warns when a new item's amount and a Stock in for
  it would count twice, and when a suggestion's text holds a private detail
  you already keep; a helper that names a place instead of picking it is told
  the exact matches and to ask you.
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
- **Bring in earlier entries:** weigh-ins, food given, medicine doses and
  odometer readings you kept in an old spreadsheet can be added in one go
  from that list's page, with every row shown first and one **Undo** for the
  whole lot. See [Bringing in your old tracker](#bringing-in-your-old-tracker).
- **What your other computers get:** in Settings, every list and each of its
  details says whether it will be **Shared with your other computers** or kept
  **Only on this computer** (and, for a list with private details, **Shared,
  but not the amount**). Everything starts as it always was; Money back starts
  on this computer only, and codes and access details are never shared.
  Keeping something here happens at once; starting to share something private
  asks first, says what will start going, and has **Undo**. Nothing is sent
  yet: this decides what your computers get once they can be paired.
- **Automatic backups**, every day and every time you close it safely, and
  **Restore from a backup** in Settings: check a backup and compare it with
  now, put it back, and undo that if it was the wrong one.

## Bringing in your old tracker

If you kept pets' weights, feedings or medicine doses in a spreadsheet before,
you do not have to type them again:

1. Add the pets and people first, and for doses each person's medicines
   (People, Important details, kind Medication). Nothing new is made from the
   file: a name has to match one you already have, or you choose it.
2. In your spreadsheet, choose Save As, then "CSV UTF-8". A heading row such as
   `Pet, Date, Weight` or `Date, Time, Given to, Medicine, Amount, Unit` works.
   Dates your usual way or as 2026-02-13; times like 8:00 am or 20:00, in the
   date column or their own. Weights in kg (nothing is converted).
3. Open the list (for example Weigh-ins or Medicine doses) and press **Bring in
   earlier entries**. For doses press **Show** first, when nobody else is
   looking: the next pages show the medicines and amounts.
4. Choose the file, check the matches, then look over every row: rows to fix,
   names to choose, and possible repeats (the same pet or person at the same
   time as an entry already there), which are skipped unless you tick
   **Add anyway**.
5. Press **Bring in**. The next page has **Undo** if anything looks wrong.

The file is read on this computer only. It is never saved and never sent
anywhere, and helpers can never use this.

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
any later version. See [`LICENSE`](LICENSE). Copyright (C) 2026 the Dashboard Plus contributors.

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
