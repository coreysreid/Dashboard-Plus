# Remove or erase a private detail

Proposed household words, checked against the shipped Delete/Restore and private Show screens on **18 November 2026**. The example is an invented People Important detail for **Example Person**. The actual saved value stays hidden on this screen until the household chooses Show; do not put it in a confirmation URL, notification, log or page title.

**Entry:** On the Important detail record, beside the normal edit controls:

> **Remove from dashboard** — Hide this record from current lists and sheets. You can restore it later. Its earlier values may remain in history and backups.  
> **Erase this private detail** — Remove this field's saved value from this data folder, its history and the backup copies this app can reach. You cannot restore the erased value from this folder. Other copies may still have it.

Choose **Remove from dashboard** for a reversible action. Its existing button/confirmation should say: **“Remove this record from the dashboard? You can restore it later. Older values may remain in history and backups.”** Buttons: **Remove from dashboard**, **Cancel**. The current generic “Delete this record? It can be restored later” is too broad when a private value is present.

**Erase review:**

> **Erase this private detail?**  
> This will clear the saved [field label] for Example Person from this data folder, its change history and the backup copies Dashboard Plus can reach. It will keep the nonprivate record and a redacted history entry.  
> **Main backup folder:** [found / unavailable]  
> **Second backup folder:** [found / switched off / unavailable]  
> Copies you made elsewhere, exports, printouts, sync history and copies on another computer are outside this app's reach. The app cannot promise to erase them.  
> **After erasing, you cannot bring this detail back from this folder. Save it elsewhere first if you need it.**  
> [Erase private detail] [Cancel]

The final button requires a fresh local confirmation, not a `?erase=1` link or a stale open tab. Keep the private value out of the review page. If a required backup folder is unavailable, do not offer a completed-erasure claim: **“We could not reach the second backup folder. Reconnect it and try again, or remove the record from the dashboard for now.”** Do not quietly switch off that backup to proceed.

**Result:** Only after current data, history and reachable app backups have been checked: **“This private detail was erased from this data folder and the Dashboard Plus backups we could reach. Copies outside this app may still have it.”** Show the time and the backup locations checked, without the old value. There is no Undo button for the erased value. **Cancel** on the review screen is the way back; **Remove from dashboard** remains a reversible alternative.

If erasure was interrupted: **“Erasure is not finished. Do not restore an older backup yet. Reconnect the backup folder or try again; the app will check each copy before saying it is done.”** Do not show the success message until all managed copies are accounted for. Importing an older external backup later must warn that the detail may return and require a recheck before that backup becomes active.
