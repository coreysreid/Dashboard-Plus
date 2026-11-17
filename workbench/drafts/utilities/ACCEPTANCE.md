# Utilities and accounts checks

Checked **2026-11-17**. Test with invented providers and numbers only.

1. A new household sees **“Add one household service and who to contact about a fault.”**
2. A provider and fault contact are saved as People rows. Updating a fault phone there updates the service's opened view; no duplicate phone field is kept in Utilities.
3. A service without a household meter, such as internet, can be saved with Meter blank. Electricity, water and gas examples name a meter also recorded in Home layout. At promotion, the name becomes an exact record link and shows its full place path.
4. The Home layout Our home sheet lists the meter and full place path. After the core adds a meter link, moving the meter's parent place updates that path without retyping the Utility service.
5. Account number and notes are private. They are hidden in the default list and absent from the Utility contacts and Our home sheets; helpers without sensitive permission cannot read them.
6. A missing fault contact produces the specific Worth filling in question. A linked fault contact with no phone produces the phone question; a contact with a phone does not.
7. The Utility contacts printout includes the actual fault phone, not just a linked contact name, once the core supports linked fields in sheets. Until then the sheet must say to use the People contact and must not present itself as a complete outage reference.
8. Deleting a linked contact clears the service link and asks for review. After meter linking is added, deleting a meter also asks for review and never displays a stale place. Removing a place that contains a meter is refused or requires reassignment.
9. Export and backup include private account numbers under existing household protections, but a general emergency-sheet bundle excludes them. Print never reveals them by default.
10. No provider phone or outage instruction is preloaded for a real household. The household confirms its provider, line and meter location from its own records before using the sheet.
