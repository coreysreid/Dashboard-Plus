# Getting started with Dashboard Plus

Dashboard Plus is a notebook for your household: people to call, things you keep, where they are, and what needs attention. It runs on **Windows 10 or 11** from a folder on your computer or a USB stick. This is an early test version. Keep another copy of anything important while you get used to it. Your records stay in its `data` folder, which is **not encrypted**; keep that folder or USB stick somewhere private.

## Download and open it

1. Open the project's [builds page](https://github.com/coreysreid/Dashboard-Plus/actions). Until the first release is published, choose the newest run on `main` with a green tick. Under **Artifacts**, download **dashboard-plus-windows**. GitHub asks you to sign in. Inside that download is a file named `Dashboard-Plus-<version>-windows.zip`.
2. Right-click that zip, choose **Extract All…**, then **Extract**. Put the extracted **Dashboard Plus** folder in Documents or on your USB stick. Work from the extracted folder, not from inside the zip.
3. Double-click **Open Dashboard**. Keep the small black window open while you use it. Your browser should show the Welcome page. [See the first screen](../../../docs/screenshots/smith/01-welcome.png).

If Windows shows **“Windows protected your PC”** and **“Unknown publisher”**, check that you downloaded the zip from this project's GitHub page. Choose **More info**, check that the file is **Open Dashboard.bat**, then choose **Run anyway**. This warning can appear because the program is not signed with a paid certificate. If it also appears for **Save and exit Dashboard**, check the name in the same way. The [README's Windows section](../../../README.md#using-it-on-windows) has the current instructions.

## Your first ten minutes

1. On **Welcome**, enter the names of the people who live here. Add pets if you have them. Choose your country, state or region, kind of home, and number of storeys. Check any situation you want to think about later, choose **People** and **Household stock**, then choose **Finish setup**. You can change these choices in **Settings**. [See an example setup](../../../docs/screenshots/smith/02-setup-answered.png).
2. On **Home**, follow **Start here**. Open **People** and add one person you would call, with a phone number. In **Who to call**, give that person a role such as Emergency contact and a call order. This makes the printed sheet useful. [See the Home page](../../../docs/screenshots/smith/03-first-home.png) and [Who to call](../../../docs/screenshots/smith/07-who-to-call.png).
3. Add a few **Places** you recognise: perhaps Kitchen, then Pantry **inside** Kitchen. You can stop there or add Shelf 3 inside Pantry. A place then reads **Kitchen › Pantry › Shelf 3** wherever you choose it. [See Places](../../../docs/screenshots/smith/11-places.png).
4. Open **Stock items** and add four things you actually have, perhaps rice, tinned tomatoes, drinking water and batteries. Start typing a name and choose a matching suggestion, or keep your own name. Enter **Amount on hand**, its unit, **Keep at least**, and a place if you know it. The list suggests a kind and unit, but check them against what is in your home. [See the add form](../../../docs/screenshots/smith/12b-adding-stock.png).

For water, enter the **total litres**, not the number of bottles. The **Safe to drink** box decides whether those litres count on the Home card. Check it for every water item; untick it for water kept for washing or flushing, or for appliance water. The estimate is a starting point and shows its own daily basis; use your local authority's advice for your household. [See the water card](../../../docs/screenshots/smith/04-home.png) and [how the estimate is worked out](../../../docs/screenshots/smith/19-needs-attention.png).

## Your first stocktake and later shopping

To do a stocktake, go to **Stock items**, choose **Add**, type the first letters of a good and pick it from the short list. If you already have that item, open it and correct its **Amount on hand**. If it is new, save the name you chose. Add its place and optional **Use by** date from the package. **Save and add another** keeps you on the add form. Look at [Stock items](../../../docs/screenshots/smith/12-stock.png) and [one item's page](../../../docs/screenshots/smith/13-stock-item.png).

After shopping, use **Stock in and out** for an item you already record. Use the find box to choose it, choose **Bought or added**, enter how many in the item's own unit, and save. Its amount updates. If you cannot find it, the form offers a way to add a new Stock item first. Use the same page for things used, expired or thrown away. [See Stock in](../../../docs/screenshots/smith/14-stock-in.png). Today, an item has one Use by date; separate dates for different batches are planned, so check the package dates yourself.

## Print a sheet to keep handy

From **Home**, choose **Print: Emergency sheet (fridge copy)**. Check the names and phone numbers on the preview, then use your browser's **Print** command. Keep the paper where your household can find it. The separate **Emergency sheet with private medical details** includes sensitive details; print and share it only when you intend to. Reprint a sheet after a contact or other important detail changes. [See the fridge copy](../../../docs/screenshots/smith/09-emergency-sheet.png).

## Save, exit and update

Choose **Save and exit** at the top of the page, then **Save and exit now**. Wait for the **Saved and closed** message before unplugging a USB stick. The program makes a final backup when it closes. You can also use **Save and exit Dashboard** in the folder. [See the close screen](../../../docs/screenshots/smith/22-close.png) and [the final message](../../../docs/screenshots/smith/23-closed.png).

Your records live in the **`data` folder inside Dashboard Plus**. Backups are also kept in `data\backups` and, if you chose the extra copy, on this computer under `%LOCALAPPDATA%\Dashboard Plus\backups`. You can see backup status under **Settings**. Keep your own copy of the folder before a major change; do not put someone else's private `data` folder in a shared copy.

To update, **Save and exit** first. Download and extract the newer Windows zip, then replace the program files in your existing **Dashboard Plus** folder **while keeping your existing `data` folder**. Do not replace or delete `data`. The next start makes a backup before changing stored records. The [project README](../../../README.md#where-your-data-is) has the current update steps.

If a page reports a problem, use **Save a report** and read it before sharing it. It may contain technical details about your household's records. [Report a problem](https://github.com/coreysreid/Dashboard-Plus/issues) without including names, numbers or private details.
