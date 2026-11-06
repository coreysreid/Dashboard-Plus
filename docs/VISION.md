# Vision

**Look after what your household has.**  
Know what you have, where it is, and when it's running out.

## The idea in one paragraph

Most households already track things in notebooks, spreadsheets, phone photos
and memory, and most of it is out of date when it is needed. Dashboard Plus is
a single place on your own computer where you define what you want to track,
enter it (or let a helper enter it for you), see it in charts, and get gentle
questions that help you understand *why* numbers change.

Think of it as Salesforce for a home: people and pets (CRM), household stock
and storage (a small warehouse system), things that could go wrong (risk),
jobs in progress (projects), a pile of unsorted photos, notes and receipts
(inbox), and later, money (finance). You decide which of these you use.

## The heart of it: looking after what you have

The reason this exists is **stewardship**: looking after what your household
has by knowing what it is, where it is, and whether it is enough, *before* you
need it. The result is **resilience**: when something goes wrong, you are
already covered, instead of counting shelves in a crisis.

Concretely, a household can:

- **Keep the pantry stocked.** Track staples, set a minimum for each, and see
  at a glance what is running low so reordering is a habit, not a surprise.
  Record the weekly shopping receipt (type it, or drop in a photo and approve
  what was read) so stock goes up when shopping comes home.
- **Know the emergency water supply.** Many countries now advise households to
  hold at least three days of water and basics. Say how many people and pets
  live here, and see in plain words: "You have about 2 days of water. You need
  roughly 12 more litres for 3 days." Stored water and food show their expiry
  dates so they get rotated.
- **Know the tools and hardware.** Which screws, fixings and fuses you have and
  do not have, before the shop is shut. Where the ladder, the generator or the
  spare torch batteries are stacked away.
- **Spot trouble early.** A water bottle past its date, a medication running
  out, a pet's food intake changing: the same watching-and-asking loop below
  applies to all of it.
- **Survive its own failures.** The records are yours, backed up automatically,
  exportable in plain files, and work with no internet. A tracker that is down
  when you need it is not resilient.

## Built for what people care about

Stock and supplies are where the product starts, but the tool is built to
adapt. One household tracks an art project, another an electronics hobby, a
third the Lego sets they buy and resell, a fourth a wine collection, a fifth
the medication log for an ageing cat. Each of those matters a great deal to
someone, and none of them matters to everyone. That is exactly why the product
is modular: nobody has to carry modules they don't use, and nobody's interest
is treated as a side-show.

Every module we ship is built seriously, with real fields, real checks and the
same question loop. Some are broad (Household stock, Pets) and some are
compact (Wine), and the compact ones show how little it takes to add a topic
of your own.


## What makes it different

Storing data and drawing charts are solved problems. The value here is a loop
that connects numbers to meaning, which we call the **question loop**:

1. **Notice.** A number changed. "Food eaten went up 30% from June."
2. **Look.** Search your own notes, events and other modules near that date for
   anything that might explain it.
3. **Ask.** "Your notes say a new job started on 3 June. Is that related?"
   with *Yes / No / Not sure*.
4. **Remember.** Your answer is saved as a note attached to the date. Charts
   show it, and later averages can take it into account.

The computer proposes. The person confirms. The software never claims to know
a cause; it only ever asks. The same principle governs data that arrives from
outside: anything entered by an assistant or imported from a file waits in a
review queue until a person approves it.

## Who it is for

- A household member who is not technical and will never edit a config file.
- Someone who wants to keep their data private and on their own machine.
- Someone who may hand the whole thing to a family member on a USB stick.
- A hobbyist who wants to add a new topic (say, a vegetable garden) by writing
  a short text file, or by asking an AI assistant to write it from a sentence.

## Principles

1. **Local first.** Your data lives in a folder you own. No account, no cloud.
2. **Ask, don't assert.** Every automated finding is a question or a
   suggestion. Words like "associated with" are allowed; "caused by" is not.
3. **A small, finished core and many modules.** The core is meant to become
   stable and stop changing. New topics are modules.
4. **No lock-in.** One click exports everything as CSV and plain files.
5. **Honest numbers.** Statistics show how many days they rest on, refuse to
   speak with too little data, and correct for looking at many things at once.
6. **Outlives its maintainer.** Few dependencies, a stable file format
   (SQLite), failure-tolerant outside sources, and documents written for a
   newcomer, and a short `INDEX.md` in every folder so a person or an AI
   assistant can skim the project and only go deeper where needed. If the
   original author disappears, someone else can pick it up.
7. **Safe by default.** Listens on this computer only. Declarative modules
   cannot run code. Code modules say clearly that they can.
8. **Nothing personal in the public repository.** Ever.
9. **Look after what you have.** The product earns its place by telling a
   household what it has, what is running low and what is about to expire, with
   no internet and no account. That habit of stewardship is what builds
   resilience.
10. **Every technical decision has a written reason.** Choices are recorded
   in `docs/decisions/` with their downsides and the sign that they were
   wrong, so any of them can be judged and reversed later.

## What ships first

A core plus six modules: **Household stock** (pantry, emergency water, tools
and hardware, shopping receipts), **Pets**, **Wine collection** (a compact
module), Graphing, Analysis and an API connector. Household stock, Pets and
Wine are deliberately made from files alone, to prove the core can build real
features from a description. If it cannot, the design
is wrong and we change the core.

## Non-goals

These are choices, not omissions. Requests for them will be politely declined.

- **Multi-user cloud hosting.** There is no server to sign in to.
- **Mobile apps.** The program runs on a computer. A phone browser on the same
  home network is not supported either, because it listens on this computer
  only.
- **Real-time sync across devices.** One data folder, one computer at a time.
  Moving it means copying the folder.
- **Replacing a bank's or doctor's system.** It is a notebook with charts, not
  a medical record or accounting system of record.
- **Anything that needs your data to leave your computer.** Optional outside
  sources may fetch public information (weather, exchange rates). They do not
  upload your records.

## Later (not v1)

Rules and workflows ("if weight drops 10% in a month, flag it"), a finance
model, project management, forecasting, and Home Assistant integration.
