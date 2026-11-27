# Sync stage 2: the first pairing, with consent (batch 23 item 122)

Written 27 November 2026 from:
- decision 0089: one main, members push to Review, over a private network
- decision 0100: stage 1's change log and `travels`
- decision 0140: the household's sharing choice for every list and detail, read on Lane A's branch, not yet on `main`

These are the screens a household sees the first time it pairs two computers. Words in **bold** are exact. Main
is User 1's computer ("Kitchen PC" in the examples); the member is User 2's laptop ("User 2's laptop"). The private
network (Tailscale or WireGuard) is assumed to be set up already; its own setup is out of scope here.

## The rules these screens keep

1. **Two people say yes, each on their own computer.** Main's person agrees to what main sends. The member's person
   agrees to receive it and to their changes going to main's Review. Neither can agree for the other.
2. **What travels is shown before the first copy, in household words**, built from the 0140 choices as they are
   at that moment. Private things that would travel are listed first and need their own tick.
3. **Nothing moves until both have said yes and the codes match.** Cancelling at any step leaves both computers
   as they were.
4. **A fresh yes is needed** whenever more starts to travel (listed below). Less never needs a yes.
5. **Stopping is always one button, on either computer**, and says what happens to the copy.

## On main: Settings → Other computers

**Empty state:**

> **Other computers**
> No other computer gets anything from this one yet.
> Pairing lets another computer in your household have a copy of your lists. Changes made there come back to your
> **Review** page, and nothing is added here until you accept it.
> [ **Pair a computer** ]
> Before you pair: your computers need the same private network (Tailscale or WireGuard). **How to set that up**

**Step 1 of 4: name it**

> **Pair a computer: what is it called?**
> A name you will recognise on Review, like "User 2's laptop".
> Name [________]
> [ **Next** ] [ Cancel ]

**Step 2 of 4: what it will get.** Built from Settings → What your other computers get (0140), grouped:

> **What User 2's laptop will get**
> These follow your sharing choices. You can change them now or at any time; less always takes effect at once.
>
> **Private things that will go to it** (tick to agree to each)
> ☐ **Medicine doses: who was given which medicine and when, and the amounts.**
> ☐ **Medical details: allergies, conditions, medicines, care and mobility needs, diet.** Access instructions stay here.
> ☐ (any other private list or detail the household chose to share, each on its own line)
>
> **Lists that will go to it** (17): People, Who to call, Household stock, Places, Vehicles, Things to do's routines …
> [ Show all 17 ]
>
> **Kept on this computer** (6): Money back, What you paid, Codes and access details (always), Registration or plate
> number, Bills' amounts and references, Private notes. [ Show all ]
>
> [ **Change what it gets** ] (opens What your other computers get, and comes back here)
> [ **Next** ] (enabled only when every private line above is ticked or changed to "Keep it here")
> Each private line also has **Keep it here instead**, which changes that 0140 choice at once.

This is the household's consent for the defaults that today start Shared (item 115 found doses and medical details
start Shared with nobody asked). Nothing private travels on a default alone.

**Step 3 of 4: the pairing code**

> **Type this on User 2's laptop**
> In Dashboard Plus on that computer: Settings → Other computers → **Join a household**.
> Pairing code: **TULIP-RIVER-42-OCEAN** (good for 10 minutes, once)
> Waiting for User 2's laptop … [ Cancel ]

**Step 4 of 4: check both screens show the same words**

> **Do both screens show these four words?**
> **lantern · meadow · copper · violin**
> Look at User 2's laptop. If the words are different, press **They are different**: someone else may be trying to
> join.
> [ **They match, start sharing** ] [ **They are different** ]

**Done:**

> **Paired with User 2's laptop.** It is getting its first copy now (about 2 minutes for this household).
> Changes made there will come to your Review page, marked **From User 2's laptop**.
> [ Back to Other computers ]

## On the member: Settings → Other computers → Join a household

> **Join a household**
> This computer will get a copy of another Dashboard Plus household's lists. Your changes go to that household's
> Review page, and someone there accepts or rejects each one.
> **This computer's own records:** this computer has 3 records of its own. Joining keeps them only on this computer,
> as a separate household you can still open; they are not sent. (A computer with no records has no question.)
> Pairing code [________]
> [ **Next** ]

> **Kitchen PC wants to share with this computer.** Here is what will arrive:
> **Private things:** Medicine doses (who, which medicine, when, amounts); Medical details (allergies, conditions,
> medicines, care and mobility needs, diet).
> **17 lists:** People, Who to call, … [ Show all ]
> **Not coming:** money back, prices, codes, registration numbers, bills' amounts.
> Anyone who uses this computer will be able to see what arrives. Keep this computer locked.
> ☐ **I agree to keep this household's information on this computer.**
> [ **Next** ] [ Cancel ]

> **Do both screens show these four words?** **lantern · meadow · copper · violin**
> [ **They match** ] [ **They are different** ]

> **Joined Kitchen PC's household.** Your changes go to Kitchen PC's Review. Private details show "kept on Kitchen PC"
> where they are not shared.

## Changes that need a fresh yes

| Change | Who is asked | Words |
|---|---|---|
| Main shares a private list or detail it did not share before (0140's "Start sharing these private things?") | main's person, then the member's on its next sync | Member: **"Kitchen PC now also shares Money back: that money came back, for which Stock in, and when. Accept on this computer?"** [Accept] [Not on this computer] |
| A module is switched on whose defaults would share private things | main's person, at switch-on | **"Turning on Medicine doses would share doses with User 2's laptop. Share them, or keep them here?"** |
| A new member pairs | both people, all four steps | as above; earlier members are not asked |
| The member's code changes (a reinstall, a new computer) | both | the whole pairing again; the old pairing is stopped |
| Main is restored from a backup | main's person | **"This copy was restored. Sharing is paused until you choose Catch up User 2's laptop."** (0089) |
| A sharing choice becomes less | nobody | it takes effect at once; the member's next sync says **"Kitchen PC stopped sharing Notes. Earlier copies on this computer stay until you remove them: [Remove them]."** |

The member saying **Not on this computer** keeps that list off the member: its lines are skipped there, and main
is told **"User 2's laptop chose not to keep Money back."**

## Stopping

**On main**, each paired computer has **Stop sharing with User 2's laptop**:

> **Stop sharing with User 2's laptop?**
> It gets nothing more from this computer, and its changes are no longer accepted here. What it already has stays
> on it: Dashboard Plus cannot take a copy back from another computer. Suggestions from it still waiting on Review
> stay there for you to accept or reject.
> [ **Stop sharing** ] [ Cancel ]

**On the member**, **Leave this household**:

> **Leave Kitchen PC's household?**
> This computer stops getting updates. Changes not sent yet (2) will not be sent.
> ( ) **Keep a read-only copy here** · ( ) **Remove the household's records from this computer** (a backup is
> made first, and kept for 30 days)
> [ **Leave** ] [ Cancel ]

## Checks

1. Cancelling at any step on either computer leaves no pairing, no key and no change log reset.
2. Step 2's **Next** stays disabled until each private line is ticked or kept here; "Keep it here instead" changes
   the 0140 choice and the list updates.
3. With the codes different, **They are different** stops both sides and records the attempt in history.
4. A pairing code works once, for 10 minutes, and only on the private network address.
5. The first copy contains exactly what step 2 listed: compare a snapshot with the 0140 rules at the moment of
   agreement.
6. A private list shared later reaches the member only after the member accepts it.
7. Stopping on main refuses that member's next push with **"Kitchen PC has stopped sharing with this computer."**
8. Leaving on the member with "Remove" makes a backup first and removes only that household's records.
9. Every screen fits 320px. The four words are readable aloud: screen readers say each word, not "lantern dot
   meadow".
10. No screen names a medicine, amount or other private value: only kinds of information.

## What the core must add

- A member key kind and pairing exchange (0089), a one-use pairing code, and a short four-word fingerprint of both keys.
- A **consent record** per pairing: who agreed, when, and the exact 0140 rules agreed to. Later loosening compares
  against it to know what needs a fresh yes.
- Per-member **"Not on this computer"** choices, so a member can refuse a list main shares.
- Stop and leave actions, with a backup before removing.
- 0140 on `main`, with the defaults for doses and medical details turned into "asked at pairing" (item 115).
