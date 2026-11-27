# Pet food in the cupboard (batch 23 item 120)

Written 27 November 2026 against `main` at `2d9fca8`: Pet feeding's Food given (0110), Stock batches and
movements (`stock.movements.adjusts`), bars (0124), Bring in (0137) and the Review groups (0097, 0105). Today a
feeding has free-text **Food** ("Example dry dog food") and an amount in g, ml, pouch, scoop or piece. A bag of the
same food in Stock is a separate item. Nothing joins them, so Needs attention never learns that the dog food is
running out from the feedings.

## The household's choice

The link is **off** until the household turns it on, food by food. On a pet-food Stock item's page (category Pet
supplies):

> **Use this up when food is put out?**
> When someone records food put out for a pet as this food, take the same amount off this item.
> Food put out is not food eaten: what the pet leaves is still taken off. Use a stocktake to put the count right.
> ( ) No, I will record Stock out myself (usual) · ( ) Yes, for feedings recorded from today
> Unit used for feedings: **g** (this item counts in **kg**: 1,000 g = 1 kg)

**Units.** The one conversion allowed is the household's own stated one, typed once on this choice: "this item
counts in bags; one bag is 2,000 g". The app never converts on its own (0111). If a feeding's unit is not the one
stated (a pouch fed from a bag of kibble), nothing is taken off, and the feeding says why.

**From today only.** Turning it on never reaches back to earlier feedings. The choice's history line says
**"From 27/11/26, feedings of Example dry dog food take from this item."**

## What a feeding does

A feeding is linked when its **Food** is chosen from linked Stock items. The feeding form's Food field offers
them first: **"Example dry dog food · from Stock (2.4 kg left)"**. Free text still works and takes nothing off.

Saving a linked feeding of 120 g, on the bag that counts in kg with 1,000 g = 1 kg, adds **one Stock out** of
0.12 kg, reason **used**, on the feeding's own day, with the note **"Food put out for Rex (120 g)"**. Both are written
in one transaction, the movement pointing at the feeding (a new optional link `serving` on movements), so:

| Person does | Stock does |
|---|---|
| Edits the feeding's amount to 150 g | the same movement becomes 0.15 kg; one history line each |
| Deletes the feeding | its movement is deleted with it; Undo restores both |
| Changes the Food to free text | the movement is deleted; the feeding says **"No longer taken from Stock."** |
| Records a treat (kind = treat) of a linked food | taken off like any feeding |
| Feeds two pets from one scoop | two feedings, two movements; the household writes each pet's share |

**After saving**, the notice says: **"Saved: 120 g put out for Rex. 0.12 kg taken off Example dry dog food (2.28 kg
left)."** If the item would go below zero: **"Saved. Example dry dog food would go below zero, so nothing was taken
off: count the bag in Stock."** The feeding is still saved.

## Words that must never appear

- "eaten", "ate", "consumed" for food put out (0110).
- "Rex used 0.12 kg" (the household used it, putting it out).
- A daily "Rex ate 240 g" bar. The bars stay **"Food put out"**, never Stock's "Used".

Stock's own movement list may say **"Used · 0.12 kg · Food put out for Rex (120 g)"**.

## Double-count traps, and what stops each

| Trap | What would go wrong | What stops it |
|---|---|---|
| 1. The household also records Stock out "used" for the same food | taken off twice | On a linked item, a manual "used" movement asks: **"Feedings already take this off. Record this as well? Only if this was used for something else."** |
| 2. Bring in earlier feedings (0137) | weeks of old feedings take today's bag to zero | Bring-in never takes from Stock. Its check page says: **"Brought-in feedings are not taken off Stock."** |
| 3. A helper suggests feedings | taken off when accepted, while the household also counts | Accepting a helper's feeding takes off like a person's. Review shows, under the row: **"Accepting takes 0.12 kg off Example dry dog food."** |
| 4. A possible repeat (the 30-minute repeat question) | both copies take off | The repeat question names Stock: **"…Keeping both takes the amount off Stock twice."** |
| 5. A stocktake after feedings | the count is right but earlier "used" lines look wrong | A stocktake records the difference only (counted_less or counted_more), as today. The feedings' movements stay. |
| 6. Buying a new bag | the feedings take from the old batch | Use takes from the batch with the earliest use-by, as Stock's adjusts already do. The feeding never picks a batch. |
| 7. Turning the link off | earlier movements disappear, or the count jumps | Turning off affects only new feedings. Earlier movements stay, and the history says **"From 03/12/26, feedings no longer take from this item."** |
| 8. A unit that is not the stated one | a pouch taken off a kg bag as 1 kg | Nothing is taken off, and the feeding says **"Not taken from Stock: this food is fed in g."** |
| 9. Leftovers thrown away | thrown away again as Stock out | Stock's "thrown_away" on a linked item asks the same question as trap 1. |
| 10. Food put out read as eaten in a chart | a correlation (batch 24 item 132) treats Stock use as eating | Movements created by feedings keep their `serving` link; charts of eating are never offered. |

## Needs attention

Once linked, Needs attention can say **"Example dry dog food: about 9 days left at the last 14 days' feedings"**. The
estimate comes only from linked feedings in the stated unit and is labelled **"an estimate from food put out"**. It is
shown only when there are 7 or more days of linked feedings. Otherwise it stays "2.4 kg left, keep at least 3 kg",
as today.

## Checks

1. Off by default: a feeding of a food that matches a Stock item's name takes nothing off.
2. Turning it on adds nothing for earlier feedings.
3. A linked 120 g feeding on a kg bag (1,000 g = 1 kg) adds one 0.12 kg "used" movement on the same day, with the note.
4. Editing, deleting and undoing the feeding moves the movement with it, with one history line each.
5. A pouch feeding of a kg bag takes nothing off and says why.
6. A manual Stock out "used" on a linked item asks the trap-1 question.
7. Bring in earlier feedings never creates movements, and says so.
8. Accepting a helper's feeding shows the Stock line on Review before accepting.
9. Going below zero saves the feeding, takes nothing off, and says to count the bag.
10. No page says "eaten" or "ate" for a feeding (search the HTML).
11. The 14-day estimate is hidden with fewer than 7 days of linked feedings.
12. Turning it off keeps earlier movements and stops new ones.

## What the core must add

- **An "uses up" link between two modules' records**, declared in `tables.toml` without naming a module: a dated
  amount in one list creates one movement in a list with `adjusts`, in one transaction. It is chosen per target
  record, with the household's stated conversion.
- **The `serving` back-link** on Stock movements, kept with the movement when edited, deleted or undone.
- **The trap-1 and trap-9 question** on manual movements of a linked item.
- **Review and repeat-question words** that name the Stock effect.
- Pet feeding's **Food** field offering linked Stock items first.
