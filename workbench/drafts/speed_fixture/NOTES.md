# Large household speed fixture

Created 17 November and rechecked 18 November 2026. [large_household.toml](large_household.toml) is entirely invented. It has no real names, phone numbers, addresses, email addresses, account details or credentials. Every name begins **Example** or **Level**. The dates are artificial and must not be used as household guidance.

| Records | Count | Shape |
|---|---:|---|
| People | 60 | Example Resident 001–060; all named in setup. |
| Pets | 10 | Example Pet 01–10; all named in setup. |
| Places | 600 | 20 top level, 40 at depth 2, 80 at depth 3, 160 at depth 4, 300 at depth 5. Names are globally unique so the example loader resolves parent links without guessing. |
| Stock items | 2,000 | Example supply 0001–2000, spread across the 300 deepest places; amount 20 packs, minimum 5. |
| Stock batches | 2,000 after load | The current core creates one batch per new item from its starting amount, place and use-by date. No duplicate batch rows in the input. |
| Stock movements | 3,600 | 1,800 one-pack uses and 1,800 one-pack purchases, alternating by month across 36 months, 1 Dec 2023–17 Nov 2026; each item has enough starting stock. |

Load into a **new empty temporary folder** with:

```bash
PYTHONPATH=src python tools/load_example.py workbench/drafts/speed_fixture/large_household.toml --data /tmp/dashboard-plus-large-example
```

This calls the shipped example loader by path, with normal module validation and record creation. It is a performance fixture; never load it into a household's real folder. The loader on main `95c8754` reported **6,270 input records loaded** into an empty temporary folder. Read-only SQL checks found 60 People, 10 Pets, 600 Places, 2,000 Stock items, 2,000 resulting batches and 3,600 movements; a recursive parent query reached depth 5 and visited all 600 places. The movement date range covers 36 distinct months. The file includes no Medical rows; the Medical module remains off for this fixture.

Useful speed measurements after loading: startup and Home render; Stock list open/search/sort; five-part place path rendering and search by middle segment; Stock item open; first/last page of 3,600 movements; and a printed supplies sheet. Measure these separately on the same machine and record elapsed time, browser and app revision. The fixture tests volume and depth, not realistic item distribution, receipt parsing or attachment size. Source: the current [example loader](../../../tools/load_example.py), [Stock schema](../../../modules/stock/tables.toml) and this generated synthetic file, checked 18 November 2026.
