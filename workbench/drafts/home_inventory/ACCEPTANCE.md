# Claim-list checks

Checked **2026-11-17**. Test only with invented households and serials.

1. A new household sees **“Add one belonging, starting with a room you know well.”** No value or coverage is inferred.
2. A belonging can link to a nested Stock place. Its opened record and claim list show the full path, not only the last shelf name.
3. Leaving the room blank shows the specific Worth filling in question, not an insurance warning. Deleting a room that still holds a belonging is refused or requires a safe reassignment.
4. Two laptops with different serial numbers remain separate rows even if they are in the same room. A blank serial is allowed.
5. The default list omits serial and private notes. The opened record limits display of sensitive fields to the household's chosen view; helpers without sensitive permission cannot read them.
6. The claim sheet groups or sorts by full room path, includes serial, paid amount and evidence locations, and warns that it is a sensitive copy. It is opened only by an explicit household Print action.
7. An item with no paid amount shows blank, not zero. The sheet never labels a paid amount as current value, replacement cost or insurer payment.
8. A changed room or corrected cost appears in a fresh sheet and export. Printing does not modify the inventory.
9. The sheet works locally and prints legibly on paper; page breaks do not orphan an item name from its serial or room. A generated PDF is treated as sensitive data.
10. Export and backup include the inventory under the household's existing privacy and encryption rules. An ordinary emergency or helper sheet does not silently include it.
