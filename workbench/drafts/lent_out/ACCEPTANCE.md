# Things lent out checks

Checked **2026-11-17**. Use invented people and loans.

1. A new household sees **“Add a tool or other thing when you lend it to someone.”**
2. Add a loan for an existing Stock item. The link is shown, but the Stock quantity does not silently change; the household can log a separate Stock movement if needed.
3. Add a loan for an untracked item by name without creating a Stock item. The borrower must be a saved People contact.
4. A loan needs a lent date and a due-back date. An impossible locally typed date is refused with the household's date format hint.
5. The open-loans list shows what, who and when due. A returned loan remains in history but is absent from the **Things still lent out** sheet.
6. Marking a loan returned sets `status = returned` and `returned_on` together. A returned date before the lent date is refused. Reopening a mistaken return restores an open state without deleting the history.
7. A due date tomorrow, today and yesterday reads **“due tomorrow,” “due today,”** and **“overdue since …”** only for still-out loans. A returned loan never appears overdue.
8. If the borrower has no phone, Worth filling in asks for one only while the loan is out; the question links to that People record and appears once per borrower.
9. Deleting a borrower while a loan exists is refused or requires a safe reassignment. If a linked Stock item is deleted, the loan's typed name and history remain.
10. Printed and exported open-loan lists are household copies. They omit private notes, do not send a reminder to the borrower, and reflect edits and returns.
