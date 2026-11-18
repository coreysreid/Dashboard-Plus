# Count what is in this batch

These are proposed screen words for a **made-up Kidney beans** batch. The actual batch is 3 tins at **Kitchen › Pantry › Shelf 3**, use by **20/05/27**. Its item also has 10 tins in another batch, so the item shows 13 tins before this correction. Dates follow the household's selected display order. Checked against the shipped Stock labels and decision 0053 on **18 November 2026**.

**Entry point:** On the batch record, **Count this batch**. Do not put a count form on the item total: a total cannot tell which date or place changed. If the household opens a saved batch's **How many** field for a stocktake, lead to this flow rather than silently editing its count.

**Count form:**

> **Count this batch**  
> Kidney beans · Kitchen › Pantry › Shelf 3 · Use by 20/05/27  
> **Recorded here: 3 tins**  
> **You counted** [ 5 ] tins  
> Count only this batch. If the tins are in another place or have another use-by date, open that batch or add a new one.  
> [Review count] [Cancel]

**Review before save:**

> **Update this batch?**  
> You counted **5 tins**; **3 tins** are recorded here.  
> This adds **2 tins** as a **stocktake correction**.  
> Kidney beans will show **15 tins** across its two batches.  
> The correction will appear in **Stock in and out** and in this batch's history. It is not a purchase.  
> [Save correction] [Go back]

After saving: **“Count updated. This batch has 5 tins; Kidney beans has 15 tins across 2 batches. Stocktake correction: +2 tins, 18/11/26.”** On a US household the date is **11/18/26**. The batch and item links remain in view. Do not say that 2 tins were bought or that both batches were counted.

For a lower count, for example **1 counted; 3 recorded**, the review says **“This removes 2 tins as a stocktake correction. It does not say they were used or thrown away.”** The movement displays **−2 tins**. A zero count remains a zero batch in history and stops its use-by warning and print row. If the count equals the recorded amount, show **“This batch already shows 3 tins. No correction was saved.”** A blank, negative, nonnumber or impossible unit amount gets a field error without changing either count.

If the count changed in another window between form and review/save, refuse the old confirmation: **“This batch now shows 4 tins, so the count you reviewed is out of date. Check it again before saving.”** Show the current batch and item totals. A double click on Save must create one correction, not two.
