# 0099. Utilities and accounts is switched on, built from the second agent's draft

- **Status:** Accepted
- **Date:** 2026-11-21
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
A household can now keep a short list of its services (electricity, gas,
water, internet, phone): who provides each one, who to contact about a fault,
and, if the service has a meter, which meter in Our home it is. You choose the
provider and the fault contact from your People, so a phone number is typed once,
in People. A printed Utility contacts page shows each fault contact's phone and
reminds you to check it with your provider. The account reference and private
notes stay hidden until you press Show, and they are never printed, listed or
exported. Nothing is filled in for you: no provider, number, outage step, payment
step or meter reading.

## What we chose
- A new module, `modules/utilities/`, built on Lane B's draft
  (`workbench/drafts/utilities/`, now removed; its notes, acceptance checks and
  example rows are in git history). One list, Services. It needs People and
  Home layout. The draft's one migration is unchanged and a test checks that it
  still matches `tables.toml`.
- **The meter is an exact row.** The Meter column links to `home_layout.meters`
  by its stored ID. The picker offers only existing meters; typed text is refused.
  A service with no meter (internet, phone) leaves it blank. Where the meter is
  comes from that meter's own Place, so moving a Place updates Our home and
  nothing is retyped in Utilities. There is no second places table.
- **Deleting clears, never strands.** Deleting a People contact or a meter clears
  that link on the service; the service stays and the gap question returns. A
  Place that holds a meter still cannot be deleted (Home layout's own rule).
- **The sheet prints the People phone.** Utility contacts shows service, kind,
  provider, fault contact, `fault_contact.phone` and meter, using the linked
  phone feature of decision 0072. Its intro says to check the number with the
  provider. It is a snapshot of People, not a verified outage number.
- **Account reference and notes are private.** Both are hidden until Show and are
  left off lists, the sheet, Our home, Needs attention, the spreadsheet export and
  the helper reading API. The household backup keeps them. Tests plant a made-up
  reference and note and search every one of those places. The form asks for no
  password, login code or card detail and says to leave them out.
- **Two gap questions.** "Who would you contact about a fault with {name}? Add a
  People contact if you have one." and "What is the fault-line number for {name}?
  Add it to the People contact." Adding the contact or the phone clears them.
- **Provider and fault contact are ordinary People rows.** No People roles were
  added, so they are reachable from the service and the People list but not
  grouped under Who to call.
- **Example households:** Smith (Home electricity, linked to its existing
  Electricity meter in the Garage), Garcia (Apartment electricity, with a new
  Apartment electricity meter in the Hall closet) and Taylor (Flat water, with a
  new Flat water meter in the Kitchen cupboard). The draft listed the meter rows
  after the service; here each meter is loaded first so the loader can link it.
  Phone numbers use fiction-reserved ranges and account references begin DEMO-.
- Tests: `tests/test_module_utilities.py` covers each of Lane B's 12 checks that
  a computer can run, including that the private reference never appears on a
  sheet, in a list, on a page, in Needs attention, in any export file or to a
  helper before it is shown. Reading a screen at 320 pixels and printing on A4
  and Letter are checked in the browser check and screenshots.
- No core file was changed.

## Why we chose it
- A utility is a contact plus a place: keeping the phone in People and the place
  in Home layout means each fact is corrected in one spot.
- A real link, not a copied name, means a renamed or moved meter cannot leave a
  service pointing at the wrong thing.
- Making the account reference private from the start avoids a field that
  looks safe and is not.

## What else we considered
- **Typing the meter name as free text.** Easier to enter but it drifts out of
  step with Our home. Refused.
- **Making Home layout optional.** The module contract has no optional
  dependencies. A household with only internet still needs Home layout switched
  on. Looser rules need core design first.
- **A utility role in People, grouped under Who to call.** A product choice for
  later; not needed to print the sheet.
- **Showing the full place path beside the meter on the list.** Needs a core
  linked-record label that includes the linked Place's path. Not done here.

## What this costs us (the downsides)
- A household with no meter still must have Home layout switched on.
- The Utilities list and picker show the meter's name only, not its full place
  path; the path is on Our home.
- The printed phone is whatever People holds. If it is out of date, the sheet is.
- The provider and fault contact are not grouped in Who to call.
- The account reference is private from lists and exports but is stored as
  ordinary text in the database and in every backup.
- A household with a service whose meter is deleted must choose a new meter itself.

## How hard it is to undo
Easy. Switch the module off in Settings (records are kept) or remove the folder.
No other module or core file changed. The only edits outside the module are the
example files, the screenshot stages, tests and documents.

## We should revisit this if
- Households want the place path or a utility role in Who to call.
- A household without any meter finds the Home layout requirement a nuisance.
- Households put passwords or card details in the notes despite the warning.
