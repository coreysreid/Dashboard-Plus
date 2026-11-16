# Medical readiness promotion checks

Use only the invented Smith, Garcia and Taylor rows in `example.toml`. These checks describe record handling, not medical advice. Checked against the shipped module contracts 17 November 2026.

1. **Loads and starts.** Medical loads beside People, Stock and Pets with no module problems. Generated migrations match `tables.toml`; enabling Medical does not alter existing People or Stock records.
2. **First step.** A household with no kits sees “Add a first aid kit and where to find it.” Kit checks and training have their own empty messages. No empty-state text claims the household is prepared or requires training.
3. **Smith's kit.** Once the example loader supports history tables without a text column, import the Smith example block. `Car first aid kit` links to Stock place `Car › Car boot`; Jane Smith is a valid People link. The kit sheet shows the full path and omits the check note.
4. **Garcia's kit.** Import the Garcia example block. `Apartment first aid kit` resolves to `Hallway › Hall closet`; the next check in 20 days appears as a **due** check reminder, not “expired”. Carlos Garcia's renewal in 40 days remains a training record, with no invented medical interval.
5. **Taylor's missing date.** Import the Taylor block. `Small first aid kit` has no `next_check`; Worth filling in asks “When do you plan to check Small first aid kit again?” It does not appear as a due or overdue check until a person chooses a date. A previous check remains visible as history.
6. **No automatic claims.** Logging a check does not update Stock quantities or assert that missing supplies were replaced. It also does not silently fill the kit's current next-check date; the two fields are distinct until a future atomic Complete check flow exists.
7. **Training dates.** A person enters a certificate's renewal date. Needs attention uses **due** wording within the 30-day watch window and **overdue** afterward. Blank renewal dates produce no invented due date. Private People medical details never print on the First aid at home sheet.
8. **Gaps and place changes.** A recorded kit without a place asks “Where is [kit] kept?” Moving Car boot under another parent updates the kit's visible full path without changing its link ID. A deleted place holding a kit is refused by the link restriction.
9. **Migration to shared places.** If Lane A later promotes Home layout's shared places, move Medical kit links with a verified old/new ID map, preserve the three example paths, and roll back completely on failure. Back up first.
