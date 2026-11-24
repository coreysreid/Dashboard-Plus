# Sharing with your household: three options (a design, not built)

Written 18 November 2026 for User 1's question: "how can I also configure it so
my partner can see the same database? I'd love to have a sync option, key word
is option. The app should clearly display that it's in isolation mode or
online. And use best practices."

Nothing here is built. The decision record is
[0081](../decisions/0081-household-sharing-options.md); it waits for User 1 to
choose. Every name, device and address below is made up: "User 1's desktop",
"Sam's laptop", "Sam's phone", `192.168.1.20`.

## 0. The short version

| | A. Take turns through a shared folder | B. One "home base" computer, others use a browser | C. Every device keeps a copy and they sync |
|---|---|---|---|
| In one line | The records live in a folder OneDrive, Dropbox or Syncthing copies between your computers. One person has them open at a time. | One computer at home runs Dashboard Plus. Others open it in a browser on home Wi-Fi, with their own password. | Each computer has its own records and swaps changes with the others directly. Both can edit, even apart. |
| Works on a phone | No | **Yes** | No |
| Both edit at the same time | No (one at a time) | Yes | Yes, conflicts shown on Review |
| Works when apart (one person travelling) | Yes, one at a time | No (home Wi-Fi only) | Yes |
| Opens a door into your computer | No | **Yes**, on home Wi-Fi only, while switched on | Only if it talks directly; not if it uses a shared folder (see C) |
| Records pass through a company | Yes with OneDrive or Dropbox; no with Syncthing | No | No |
| New programs we must add (dependencies) | None | Probably one, for HTTPS certificates | Probably one, and a large rewrite |
| Size of the change | **Medium** | **Large** | **Very large** |
| Way back to "this computer only" | Stop sharing in Settings; easy | Switch off; instant | Unpair; each copy carries on alone |

**Recommendation (section 6):** build **A first**, using Syncthing where the
household can, because it keeps the rule "the program listens on this computer
only" and needs no new dependency. Build **B instead of A if Sam mainly uses a
phone.** Keep **C for later**, and only if taking turns turns out to be a real
nuisance; much of A's work (device names, the shared folder, conflict pages) is
reused by C.

Whatever is chosen, **the default stays "On this computer only"**, sharing is
a switch in Settings, and every page says which mode it is in (section 5).

## 1. What we have today, and why sharing is a rule change

- The program listens on `127.0.0.1` only (decision 0011, DESIGN section 12).
  Pages need the launch-link cookie, a page token on every save, and a matching
  `Host` and `Origin` (`web/app.py`, `only_this_computer`). Helpers use the
  separate `/api/v1/` door with a key, from this computer only (0067, 0074).
- The data is one SQLite file, `dashboard.db`, in `journal_mode=DELETE` with
  `synchronous=FULL` (decision 0009, `core/db.py`). Every web request opens and
  closes its own connection through a gate, so a restore can hold the file
  alone (0079).
- Backups are checked copies made with SQLite's backup function, in the data
  folder and a second folder on the computer (0006, 0036, `core/backups.py`).
  Restore checks copies read-only and swaps in a prepared file (0079).
- Every change is in the history (`core__audit`) with an actor such as
  `person`. It does not say which person or which computer, because today there
  is only one of each.
- Private details are sent to the screen only when asked (0059) and never to
  helpers (0067). Helper key fingerprints live in `data/secrets/`, outside the
  database and outside backups (0066).
- The footer of every page says "Runs on this computer only. Nothing is sent
  anywhere." The data folder is not encrypted; an optional passphrase is
  researched (`workbench/research/data_folder_passphrase.md`) but not built.

Every option breaks one of these promises on purpose: A sends the records to a
folder another computer reads (and, with OneDrive or Dropbox, to a company); B
lets other devices on the home network talk to the program; C does both or one
of them. So **any option needs User 1's OK** under "the privacy and security
rules" in `docs/WORKSTREAMS.md`, and a fresh security review before it ships.

## 2. Option A: take turns through a shared folder

### How it works for the household
1. User 1 opens **Settings → Sharing → Share through a folder**. The page
   explains the one-at-a-time rule and asks for a folder that OneDrive, Dropbox
   or Syncthing keeps in step between your computers (for example a folder
   called `Dashboard Plus household` inside OneDrive).
2. Dashboard Plus makes a checked copy of the records into that folder, with a
   small note saying which copy is newest. User 1's own data folder, backups and
   helper keys stay where they are.
3. On Sam's laptop, Sam installs Dashboard Plus, chooses **Join a shared
   household folder**, picks the same folder and types a name for the laptop.
4. Whoever opens Dashboard Plus first "takes" the records. The other computer
   sees: "User 1's desktop has the records open (since 7:40 pm). You can look at
   the copy from 7:40 pm, but not change it, until User 1 closes."
5. **Save and exit** puts the records back into the shared folder and hands
   them back. A few seconds to a few minutes later (depending on the cloud
   service) Sam's laptop sees the newer copy and can take it.

### The rule that makes it safe: never open the database in the shared folder
SQLite's own documentation says plainly that the file locking it relies on is
unreliable on network filesystems, and that two computers writing one database
file over a network share can corrupt it ("How To Corrupt An SQLite Database
File", sqlite.org/howtocorrupt.html, section on broken locking; "Appropriate
Uses For SQLite", sqlite.org/whentouse.html; and I believe a newer page,
"SQLite Over a Network", sqlite.org/useovernet.html, which I am not certain of
the exact title of). OneDrive and Dropbox are not even network filesystems: they
watch the folder and upload whole files whenever they change, with no idea
where a SQLite transaction starts or ends, and SQLite's journal file next to it
would be uploaded too. So:

- **Check out:** on opening, Dashboard Plus checks the shared copy, then copies
  it into the local data folder with SQLite's backup function. All work happens
  on the local copy, exactly as today (USB-safe settings, gate, backups).
- **Check in:** on Save and exit (and, optionally, every few minutes while open
  as a safety copy), it writes a checked copy to the shared folder under a
  temporary name (`household.db.partial`, like `db.backup_to` already does)
  and renames it into place. The cloud service only ever sees whole, finished
  files. No journal file is ever in the shared folder.

### The files in the shared folder
| File | Written by | What it holds |
|---|---|---|
| `household.db` | whoever checks in | the records |
| `household.json` | whoever checks in, after `household.db` | a "generation" number (1, 2, 3 …), the file's size and fingerprint (SHA-256), app and module versions, which device checked in and when |
| `lease.json` | whoever has the records open | the device name and person, when it was taken, when it was last renewed, when it expires, and the generation it took |
| `aside/` | any device | copies set aside after a clash (see below), never opened automatically |

No private details are in the JSON files; device names are chosen by the
household. `data/secrets/` (helper keys), the log, the running-state file and
backups are never put in the shared folder.

### The lease ("who has it open")
- Taking: the device writes `lease.json` naming itself, with an expiry 15
  minutes ahead, and renews it every 5 minutes while open. Closing removes it.
- Refusal: if a lease from another device has not expired, the records open
  **read-only** with the message above. Read-only uses the shared copy checked
  out as a look-only copy; no save buttons.
- **The lease is a polite sign on the door, not a lock.** Cloud folders take
  seconds to minutes to pass a file along, so two computers opened within the
  same minute could both see "nobody has it". The real protection is the
  generation number:
- **Check-in rule:** a device may only replace `household.db` if
  `household.json` still shows the generation it checked out. If someone else
  has checked in since, the device does not overwrite; it puts its own copy in
  `aside/` as `household from Sam's laptop 2026-11-18 2040.db` and says so:
  "User 1's desktop saved newer records while this laptop had them open. Your
  changes from this session are kept separately. Open them on Review to copy
  anything across." Nothing is merged automatically in option A.
- **Stale leases** (the other computer crashed, went to sleep, or lost
  internet): after the lease expires, the page offers **Take over**, with
  words that say what will happen: "Sam's laptop opened the records at 3:00 pm
  and has not been heard from since 3:10 pm. If you take over, anything Sam
  changes on that laptop after 3:10 pm will be kept separately, not lost."
  Taking over raises the generation, so a laptop that comes back later is
  caught by the check-in rule.
- Clocks: lease times are compared using the time written by the holder and
  the time the file arrived; a computer whose clock is far off (more than a few
  minutes from the file times) gets a warning rather than a silent take-over.
  (Not certain how reliably cloud services keep file times; to test.)

### Partial uploads and "conflicted copies"
- **Half-arrived files:** before using `household.db`, check its size and
  SHA-256 against `household.json`, then `PRAGMA integrity_check`, opened
  read-only (as restore does, 0079). If they do not match, the newest copy is
  still arriving: "The copy from Sam's laptop has not finished arriving. Try
  again in a minute." Never open, check out or overwrite a file that does not
  match.
- **Conflicted copies:** when two computers change the same file before the
  service has passed it along, the service keeps both under new names. From
  memory (check each before relying on it): Dropbox uses `household (Sam's
  conflicted copy 2026-11-18).db`; Syncthing uses
  `household.sync-conflict-20261118-204000-ABCDEFG.db`; OneDrive adds the
  computer's name, such as `household-SAMS-LAPTOP.db` (least sure of this
  one). On every open, Dashboard Plus looks for any file in the shared folder
  whose name starts with `household` and is not one of its own, and shows:
  "There are 2 extra copies of the records in the shared folder, probably made
  by OneDrive when two computers saved at once. Nothing was lost. Look at
  them." Looking reuses the restore preview (read-only, record counts then and
  now). They are never opened for writing or deleted without a click.

### Security and privacy
- **What leaves the computer:** the whole records file, private details
  included, goes to the shared folder. With OneDrive or Dropbox that means a
  copy sits on the company's servers and in its version history (often kept
  for weeks after deletion). With **Syncthing** it goes only to your own
  devices, directly or through a relay that cannot read it (Syncthing encrypts
  between devices with TLS and identifies devices by their certificate
  fingerprint, the "device ID"; this is from its documentation as I remember
  it).
- **In transit:** the cloud service's own encryption (HTTPS for OneDrive and
  Dropbox; TLS for Syncthing). We add nothing.
- **At rest:** the shared copy is as unencrypted as the data folder is today.
  The company can technically read it; anyone who gets into the cloud account
  can download it. Encrypting the shared copy needs the optional passphrase
  work (M3) and, because Python's standard library has no general encryption,
  a new dependency. Until then the Sharing page must say: "The shared copy is
  not encrypted. OneDrive or Dropbox can read it, as can anyone who signs in to
  that account."
- **Logins:** none needed in the app: each person uses their own computer and
  account. The history should start naming the device and person
  (`person:Sam on Sam's laptop`) so "who changed this?" still has an answer.
- **Home Wi-Fi attacker:** nothing new. The program still listens on this
  computer only.
- **Shared links:** share the folder with Sam's own account, never "anyone
  with the link". The page says so.
- **The footer** changes from "Nothing is sent anywhere" to "Records are
  shared through a folder with Sam's laptop." Telling the truth here is the
  point.

### What changes in the code (medium)
- New `core/shared_folder.py`: lease, generation note, check-out, check-in,
  extra-copy scan, set-aside copies. Uses only the standard library and the
  existing `db.backup_to`, `integrity_ok` and the restore preview.
- Start-up and Save and exit: check out first, check in last; read-only mode
  when another device holds the lease (a new "look only" flag the pages
  honour: no save buttons, every POST refused).
- Settings → Sharing page; Review shows set-aside copies; the mode indicator.
- History: add device name to the actor. Settings: a device name.
- Tests: two fake "computers" pointing at one folder, slow and half-written
  arrivals, conflicted-copy names, expired leases, take-over, clock skew.
- No new dependency. No change to the web server's listening rules.

### Turning it off, and getting back to isolation
**Settings → Sharing → Stop sharing on this computer**: checks in a last time,
gives up the lease, and from then on uses only the local data folder. The
shared folder is left alone; the page says "The shared copy is still in your
OneDrive folder. Delete it there if you no longer want it, and empty
OneDrive's recycle bin." **Pause sharing** keeps the settings but opens the
local copy only, and warns that changes made while paused will come back as a
set-aside copy if the other computer also changed things.

### Best practices that apply
- Treat cloud folders as file copiers, not databases: one writer, whole files,
  write-then-rename (SQLite docs above).
- Verify before use (size, fingerprint, integrity check), as decision 0079
  already does for backups.
- Never lose a side: on doubt, set aside, do not overwrite.

## 3. Option B: one "home base" computer, others use a browser

### How it works for the household
1. User 1 picks a computer that is usually on at home (the "home base"), opens
   **Settings → Sharing → Let others at home use Dashboard Plus**, and confirms
   the home network ("You are on the network called HomeNet. Only devices on
   this network can connect.").
2. User 1 makes an account for Sam: a name and a password Sam chooses on the
   spot (at least 8 characters; no rules about symbols).
3. The page shows the address, for example `https://192.168.1.20:8765`, and a
   pairing code, `482 913`, valid for 5 minutes.
4. On Sam's phone, Sam types the address. The browser warns that the
   connection's certificate is not from a known authority (see HTTPS below).
   After checking, Sam continues, types the pairing code, then Sam's name and
   password. The phone is now an **allowed device**, listed in Settings with a
   **Remove** button.
5. Sam uses the same pages as User 1. Two people can save at the same time.
6. When the home base closes, sleeps, or leaves the home network, the others
   see "Dashboard Plus on User 1's desktop is not available right now."

### Listening beyond this computer, only when switched on
- Off by default. When on, the server listens on `127.0.0.1` **and** the one
  home-network address chosen, never on every address (`0.0.0.0`), on a fixed
  port the household keeps (so bookmarks work).
- Only on a network Windows calls "Private", never "Public". If the computer
  joins a different network, sharing switches itself off and says why.
- **Windows firewall:** the first time, Windows asks whether to allow the
  program on private networks. I believe allowing it may need an administrator
  on some computers, which clashes with "no admin rights needed"; to test on a
  clean Windows computer before promising anything.
- **Auto-off:** at Save and exit; when the network changes; optionally after a
  set time ("Stop sharing at midnight"). Question for User 1: when Dashboard Plus
  opens next time, does sharing come back on by itself? Suggested answer: yes,
  but only on the same home network, and the home base's own screen says so.
- The helper door (`/api/v1/`), safe close (`/api/shutdown`) and the pages for
  Sharing, Helpers, Backups, Restore, Export, Import and modules answer **only
  on the home base's own screen** (`127.0.0.1`), never to another device.

### Per-person accounts, passwords and sessions
- **Passwords:** stored only as a slow, salted hash. OWASP's Password Storage
  Cheat Sheet prefers Argon2id; Python's standard library has scrypt
  (`hashlib.scrypt`), which OWASP also lists, with parameters it gives as at
  least N=2^17, r=8, p=1 (from memory; check the current sheet). scrypt avoids
  a new dependency. Following NIST SP 800-63B (as I recall it): at least 8
  characters, allow long passphrases, no forced symbols or regular changes,
  refuse very common passwords. Hashes live in `data/secrets/`, like helper key
  fingerprints (0066), so a restored backup can never bring back a removed
  account's password.
- **Sessions:** after signing in, a random 256-bit session id in a cookie that
  is `Secure`, `HttpOnly`, `SameSite=Strict` and, with HTTPS, named with the
  `__Host-` prefix. A new id at every sign-in (OWASP Session Management Cheat
  Sheet). Signed out after 30 minutes of no use on other devices (User 1 to
  choose); **Sign out** on every page. Removing a device or account ends its
  sessions at once.
- **Allowed devices:** a device must be paired once with a pairing code shown
  on the home base (single use, 5 minutes, 6 digits). The device then holds a
  long random device token, kept as a fingerprint in `data/secrets/`. A device
  that is not paired cannot even reach the sign-in form.
- **Private details:** each account has "May see private details" (allergies,
  medicines, access codes). Off by default for new accounts; User 1 decides for
  Sam. Showing one is recorded in the history as who, when and which detail,
  never the value.
- **History:** every change records the account, for example `person:Sam`.
- **Two people editing one record:** today the last save wins silently. With
  two people this needs a check: "Sam changed this record after you opened it.
  Here is what Sam saved." (compare the record's `updated_at` when saving).

### HTTPS on a home network
- **Plain HTTP is not acceptable** for this: anyone else on the Wi-Fi (a
  guest, a smart TV or camera with a security hole) could read every page,
  including private details once shown, and copy the session cookie to act as
  Sam. Browsers also refuse `Secure` cookies without HTTPS.
- **Self-signed certificate with a fingerprint check:** the home base makes its
  own certificate once. Every browser warns on first visit, because no public
  authority vouches for a home computer. The honest protection is for Sam to
  compare a short fingerprint shown on the home base with the one the browser
  shows in the certificate details. That is fiddly on phones, and training
  people to click past warnings is itself a risk. The pairing code does not
  fix this: it proves the device to the home base, not the home base to the
  device.
- **Better but harder:** a home "certificate authority" installed on each
  device, so browsers trust the home base without warnings. Phones make this a
  multi-step settings task (on iPhones, installing a profile and then trusting
  it separately, as I remember). Probably too much for most households.
- **Code cost:** Waitress, our web server, does not speak HTTPS by itself (as
  far as I know), and Python's standard library cannot make a certificate. So B
  needs either a new dependency (likely the `cryptography` package to make the
  certificate, plus a way to serve HTTPS) or a different server piece. That is
  its own decision, and AGENTS.md says to ask before adding a dependency.

### Request rules (CSRF, Host, Origin, limits)
- **Host:** allowed names become exactly `127.0.0.1:<port>`,
  `localhost:<port>` and `<home address>:<port>`. Anything else is refused,
  as today (protects against DNS rebinding).
- **Origin:** every save must come with an `Origin` matching one of those
  exactly, or none at all from older browsers plus a valid page token.
- **Page token:** one per session instead of one per start (OWASP CSRF
  Prevention Cheat Sheet: synchroniser token plus `SameSite` and Origin
  checks).
- **Rate limits:** sign-in and pairing attempts: after 5 failures for one
  account or one device in 15 minutes, wait 15 minutes; pairing codes die after
  3 wrong tries (OWASP Authentication Cheat Sheet). The page limit per minute
  from 0074 applies per session too.
- The existing headers stay: `Cache-Control: no-store`, `X-Frame-Options:
  DENY`, `nosniff`, `Referrer-Policy: same-origin`.

### What an attacker on home Wi-Fi could do
- With B **off**: nothing new; the program does not listen on the network.
- With B **on, HTTPS and fingerprint checked**: see that something answers on
  the port; try pairing codes and passwords, slowed by the limits; nothing more
  without a password and a paired device.
- With B on and the warning clicked past without checking: someone already
  inside the network could pretend to be the home base on the first visit and
  collect Sam's password. This is the weakest point of B.
- Advice on the page: use a separate guest network for visitors and smart
  devices if the router offers one.

### What can go wrong
- Home base off or asleep: nobody else can use the records. No offline use.
- The home address changes (routers hand them out): bookmarks break. Show the
  current address on the home base; a fixed address in the router helps. A
  name such as `dashboard.local` needs another dependency (zeroconf); later.
- SQLite is happy here: one program, one file, short transactions with a busy
  timeout. This is the arrangement SQLite recommends (one process owns the
  file) rather than several computers sharing it.
- A restore on the home base signs everyone out and says why.

### What changes in the code (large)
- Server: listen on a chosen address and fixed port; HTTPS; switch on and off
  while running.
- Accounts, password hashing, pairing, device list, sessions, sign-in and
  sign-out pages, per-account private-details permission.
- `only_this_computer` grows into "this computer, or a signed-in paired
  device", with the local-only pages listed above. A full security review.
- History records the account; the edit-clash check.
- Likely one new dependency (certificates and HTTPS), needing its own record.
- Tests: two devices, wrong Host, wrong Origin, stolen cookie on another
  device, expired pairing code, rate limits, network change, local-only pages
  refused from the network.

### Turning it off, and getting back to isolation
The switch on the Sharing page, or Save and exit: the server stops listening
on the network at once and every other device's session ends. Accounts and
paired devices are kept but do nothing until sharing is switched back on.
**Remove all devices and accounts** forgets them. The home base itself never
needs an account; it always works as today.

## 4. Option C: every device keeps its own copy, and they sync

### How it works for the household
1. User 1 opens **Settings → Sharing → Sync with another computer** and gets a
   pairing code. Sam enters it on Sam's laptop. The two now trust each other.
2. Each computer keeps its own full records and works alone, at home or away.
3. Whenever they can reach each other (or the shared folder, see below),
   each sends the changes the other has not seen. Usually nobody notices.
4. If both changed the **same detail** of the same record, Dashboard Plus keeps
   one for now and puts both on Review: "User 1 set Rice, minimum to 4 and Sam
   set it to 6, at about the same time. Kept 6 for now. Keep 6 / Use 4."

### Merge rules
- **Records need world-wide ids.** Today each table numbers its rows 1, 2, 3
  (`id INTEGER PRIMARY KEY`); two computers would both make "item 7". Every row
  needs a second, random id that links and the change log use. This touches
  every table, link and module migration.
- **The change log:** each saved change becomes an entry: which device, a
  counter, a time, table, record id, field, new value, and who. The existing
  history (`core__audit`) is close but records whole rows, not fields.
- **Ordinary details (names, dates, notes):** "last writer wins" per field,
  ordered by a hybrid logical clock (wall time plus a counter, so a computer
  with a wrong clock cannot jump ahead forever; Kulkarni and others, 2014,
  "Logical Physical Clocks"). To tell "changed one after the other" from
  "changed at the same time", each field also carries a version vector (one
  counter per device; the idea from Fidge and Mattern, 1988, used by Syncthing
  per file). Same-time changes to one field go to Review instead of being
  silently decided.
- **CRDTs** (conflict-free replicated data types; Shapiro and others, 2011)
  give rules that always merge the same way on every device. A last-writer-wins
  register per field is one of them; a grow-only set is another. Full CRDT
  libraries for text and lists (Automerge, Yjs) or for SQLite (cr-sqlite, a
  native extension; I am not sure how well maintained it is now) exist, but
  each is a sizeable dependency. Field-level last-writer-wins plus Review for
  clashes is enough for household records and easy to explain.
- **Stock in and out merges naturally** if each movement is a record that is
  only ever added (a grow-only set): User 1's "used 2 tins" and Sam's "bought 6"
  both arrive, and each device works the count out from all movements. But
  today saving a movement also **changes the item's count** directly
  (DESIGN 5.3). Under sync the count must be worked out, never copied, or it
  would be counted twice. **Stocktake corrections** (0070) save the difference
  from the count at that moment; two stocktakes on two devices at once would
  both add their difference. They need to become "counted 12 at 7:40 pm", with
  a Review item when two counts clash.
- **Deletions** keep a marker (the program already deletes softly with
  `deleted_at`). "Sam deleted a record User 1 just changed" goes to Review.
- **Rules a merge can break:** a required link to a record deleted elsewhere,
  a "not before" date order (0075), a choice list a module removed. Each goes
  to Review; nothing is dropped.

### Moving the changes, without a company server
- **Option C1, through a shared folder (recommended if C is built):** each
  device writes only its own files (`changes from Sam's laptop 000123.log`),
  never anyone else's. Because no file ever has two writers, cloud
  "conflicted copies" cannot happen, and there is no listening port at all.
  Syncthing or a cloud folder does the moving; option A's folder settings are
  reused.
- **Option C2, directly on home Wi-Fi:** each device listens for its peers,
  with mutual TLS and certificates pinned during pairing (the pairing code
  authenticates the first exchange of fingerprints, much as Syncthing's device
  IDs do). This brings back B's listening and certificate costs, so it is worse
  for us than C1.

### Different app versions
- Each change carries the module and its database-step number. A device
  refuses to apply changes from a newer version, keeps them waiting, and says
  "Sam's laptop has a newer Dashboard Plus. Update this computer to keep
  syncing." The indicator shows "Sharing paused".
- Older changes arriving at a newer device are upgraded as the database steps
  were, which means every future migration that renames or reshapes a column
  must also say how to upgrade log entries. That is a permanent cost on every
  module, including households' own modules.
- A module switched on in one copy only: its changes are kept but not applied
  until it is switched on.
- **Restore** becomes hard: putting back an old backup on one device must not
  "undo" everyone. A restore would either be local only (that device leaves the
  sync and is paired again) or a reset that fetches everything from the
  others. To design if C is chosen.

### Security and privacy
- **What leaves:** changes, private details included unless the household
  chooses otherwise per part (for example "do not sync Medical").
- **In transit and at rest:** with C1, as option A (Syncthing best; cloud
  companies can read). Encrypting log files ourselves needs a dependency
  (the standard library has no encryption). With C2, TLS between pinned
  devices.
- **Logins:** none in the app; each person on their own computer. Devices are
  paired and can be unpaired; an unpaired device's later changes are refused.
- **Home Wi-Fi attacker:** nothing new with C1; with C2 as B, minus browsers.

### What can go wrong
- A wrong merge rule quietly loses a change. This is why every same-time clash
  goes to Review and why the log is kept.
- Phones cannot run Dashboard Plus, so C does not help a partner who uses a
  phone.
- A device unused for months returns with old changes: they merge by the rules;
  clashes go to Review.
- SQLite: fine, each device has its own file; only log files travel.

### What changes in the code (very large)
World-wide ids for every row and link, a field-level change log, clocks,
merge engine, worked-out stock counts, new stocktake rule, Review for clashes,
version rules for every migration, pairing, restore redesign, and many tests
(two and three devices, offline for weeks, every clash type). It touches
nearly every part of the core and every module that changes a count.

### Turning it off
**Unpair** on either computer: from then on each copy carries on alone with
everything it had. Nothing is deleted; set-aside clashes stay on Review.

## 5. The mode indicator on every page

### Where
In the top bar on every page, immediately after "Dashboard Plus" and before
"Needs attention": a small rounded label with an icon and words, linking to
Settings → Sharing. On narrow screens it wraps onto its own line under the
name; it is never hidden behind a menu. The footer sentence repeats the same
mode in full, replacing "Runs on this computer only. Nothing is sent anywhere."
only when sharing is on. Printed sheets show it in small print too ("Printed
from User 1's desktop, shared with Sam's laptop").

### Exact words
| Mode | Label | Footer and Sharing page |
|---|---|---|
| Default, no sharing set up | **On this computer only** | Runs on this computer only. Nothing is sent anywhere. |
| A, you have the records | **Shared folder · open here** | Open on User 1's desktop. Sam's laptop can look but not change until you choose Save and exit. Shared through your OneDrive folder. |
| A, another computer has them | **Look only · Sam's laptop has them open** | Sam's laptop has had the records open since 7:40 pm. You are looking at the copy from 7:40 pm. |
| B, home base | **Sharing on home Wi-Fi with 2 devices** (or **with 1 device**, or **Sharing on home Wi-Fi · nobody connected**) | Other devices on HomeNet can use Dashboard Plus with their own password. Switch off |
| B, another device | **Using User 1's desktop · signed in as Sam** | You are using Dashboard Plus on User 1's desktop over home Wi-Fi. Sign out |
| C, in step | **Syncing with Sam's laptop, last synced 2 minutes ago** | Changes from both computers are swapped through your Syncthing folder. |
| C, out of touch | **Syncing with Sam's laptop, last synced yesterday at 6:40 pm** | Sam's laptop has not been in touch since yesterday at 6:40 pm. Your changes are saved here and will be sent when it is. |
| C, clashes | **Syncing with Sam's laptop · 2 changes need a look** (links to Review) | |
| Any, chosen pause | **Sharing paused** | Sharing is set up but paused. Records stay on this computer only until you turn it back on. |
| Any, a problem | **Sharing stopped: the shared folder can't be found** (or **…: Sam's laptop has a newer version**) | The plain reason and what to do. |

Times use the household's date setting (0052). "2 minutes ago" updates at
most once a minute.

### Colours (checked for contrast)
Each label has its own text and background colour in light and dark mode,
plus a 1-pixel border, and always an icon and words, so colour is never the
only signal (WCAG 2.1, 1.4.1). Ratios below were computed with the WCAG
formula; text needs at least 4.5 to 1 (1.4.3), borders 3 to 1 (1.4.11).

| Label | Light text on background | Ratio | Dark text on background | Ratio |
|---|---|---|---|---|
| On this computer only (house icon) | `#1f4d36` on `#e8f3ec` | 8.5 | `#bfe6d0` on `#1f3328` | 9.9 |
| Sharing on home Wi-Fi / Shared folder (two people icon) | `#6b4200` on `#fff1cc`, border `#9a6a00` (4.7 on white) | 7.8 | `#ffd98a` on `#3a2e12`, border `#d9a63a` (7.1) | 9.8 |
| Syncing (two arrows icon) | `#1d4f91` on `#e6effa` | 7.0 | `#b9d4f5` on `#1a2a40` | 9.5 |
| Sharing paused (pause icon) | `#3d4440` on `#ececE6` | 8.4 | `#d5dad6` on `#2c312d` | 9.4 |
| Problem (warning icon) | existing `--bad` `#a3361f` on `--bad-bg` `#fbeee9` | 6.0 | `#f0a08a` on `#3a221c` | 7.1 |

Amber for "shared" is deliberate: it is not an alarm, but it is different from
the calm green of "this computer only", so a glance tells the two apart.

### Behaviour
- **The default is isolation.** A new install, a new data folder and a copy
  moved to another computer all start "On this computer only". Sharing starts
  only from the Sharing page, after a page that explains what will leave the
  computer and asks to confirm.
- After a restore (0079), sharing is paused and the household is asked
  whether to carry on sharing.
- A second shortcut, **Open Dashboard (this computer only)**, opens with
  sharing paused for that session, whatever the setting.
- For screen readers, the label is a link named "Sharing status: …". A change
  of mode (not the minute counter) is announced politely (`role="status"`).

## 6. Recommendation

**Stage 1: option A, with Syncthing recommended and OneDrive or Dropbox
allowed with a clear warning.** Reasons, in order:
1. It keeps the strongest rule we have: the program still listens on this
   computer only, so nothing on the home network can reach it.
2. It needs no new dependency and no passwords to look after.
3. It is honest about SQLite: one computer writes at a time, on its own local
   copy, and only finished, checked files travel.
4. It works when one person is away, which B does not.
5. Its parts (device names in the history, the shared-folder settings,
   set-aside copies on Review, the mode indicator) are the first half of C1.

**Instead, choose B first if Sam mainly uses a phone,** or if you both want the
records open at the same time at home. It is the only option that serves a
phone, but it opens a door on the home network and needs HTTPS, accounts and a
dependency decision.

**Stage 3, only if needed: option C1** (sync through the same folder), if
taking turns turns out to be a real nuisance. It is the most convenient and by
far the largest and riskiest change, and it puts a lasting cost on every future
module change.

Before any of it ships: User 1's OK on the rule change (decision 0081), a
security review like 0055's, and a test on two real Windows computers with the
chosen cloud folder.

## 7. Questions for User 1

1. Who should see the records: just you and Sam, or anyone else (children, a
   carer, a house-sitter)? Should anyone see only some parts?
2. Which devices: Windows computers, a Mac, phones (iPhone or Android)?
3. **Does Sam mainly use a phone?** (If yes, B first.)
4. Will you both want to change things at the same time, or is "one at a time"
   fine?
5. Is one computer usually switched on at home?
6. Do you already use OneDrive, Dropbox or Google Drive, and would you be happy
   to try Syncthing (free, no company holds the records)?
7. Should Sam see private details (allergies, medicines, access codes)?
8. When Dashboard Plus opens, should sharing come back on by itself?
9. Do you still run it from a USB stick? (A shared folder lives on a computer;
   the stick would then hold a copy, not the shared records.)
10. Do you need it away from home? (None of these options reach a phone outside
    the home; that would need a service such as a VPN, which is a bigger step.)

## 8. Sources (from memory; check before quoting)
- SQLite: "How To Corrupt An SQLite Database File" (sqlite.org/howtocorrupt.html),
  "Appropriate Uses For SQLite" (sqlite.org/whentouse.html), the backup API
  (sqlite.org/backup.html), and a page on using SQLite over a network
  (I believe sqlite.org/useovernet.html; unsure of title and address).
- OWASP Cheat Sheet Series: Password Storage, Authentication, Session
  Management, Cross-Site Request Forgery Prevention. Parameter numbers quoted
  above are from memory and may have changed.
- NIST SP 800-63B, Digital Identity Guidelines (memorised secrets section).
- WCAG 2.1: 1.4.1 Use of Color, 1.4.3 Contrast (Minimum), 1.4.11 Non-text
  Contrast.
- Syncthing documentation: device IDs, the Block Exchange Protocol, and its
  `.sync-conflict-` file names.
- M. Kleppmann, A. Wiggins, P. van Hardenberg, M. McGranaghan, "Local-first
  software: you own your data, in spite of the cloud" (Ink & Switch, 2019).
- M. Shapiro, N. Preguiça, C. Baquero, M. Zawirski, "Conflict-free Replicated
  Data Types" (2011).
- S. Kulkarni and others, "Logical Physical Clocks and Consistent Snapshots in
  Globally Distributed Databases" (2014), hybrid logical clocks.
- C. Fidge and F. Mattern (1988), vector clocks; L. Lamport, "Time, Clocks, and
  the Ordering of Events in a Distributed System" (1978).
- Dropbox and OneDrive help pages on conflicted copies (file name patterns
  above are from memory; OneDrive's is the least certain).
