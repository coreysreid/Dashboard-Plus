# New screens: exact wording replacements

Checked **19 November 2026** against `src/dashboard/web/templates/{count,review,helpers,helper_key,helper_connect}.html`, `src/dashboard/web/{count,review,helper_settings,pages}.py`, `modules/lent_out/{tables,labels}.toml` and the stocktake action in `src/dashboard/core/records.py`. The table lists **only replacements** after reviewing the labels, help lines and messages on Count this batch, Review, Settings → Helpers and Mark returned. These are wording proposals; shipped files are unchanged.

| Screen and source | Current words | Replace with |
|---|---|---|
| Count this batch · `count.html` review heading | `Update this batch?` | `Save this stocktake correction?` |
| Count this batch · `count.html` removal explanation | `It does not say they were used or thrown away.` | `This does not record use or waste.` |
| Count this batch · `count.html` review back link | `Go back` | `Change count` |
| Count this batch · `count.html` completion heading | `Count updated` | `Stocktake correction saved` |
| Mark returned · `modules/lent_out/tables.toml` completion message | `Marked as returned today. If it came back on another day, change Returned on below.` | `Marked returned today. If it came back on another day, change Returned on below.` |
| Review · `review.html` heading | `Review suggestions` | `Review` |
| Review · `review.html` empty state | `No suggestions to review.` | `Nothing is waiting on Review.` |
| Review · `review.py` already-decided result | `That suggestion had already been decided.` | `This row was already accepted or rejected.` |
| Review · `review.py` nothing-to-decide result | `Nothing was waiting to be decided.` | `Nothing is waiting on Review.` |
| Review · `review.py` batch-reject result | `Rejected {n} suggestion(s). Nothing was added.` | `Rejected {n} row(s). Nothing was added.` (keep the existing singular/plural logic) |
| Review · `review.py` batch-accept result | `Added {n}.` | `Added {n} record(s).` (singular/plural by `n`) |
| Settings → Helpers · `helpers.html` introduction | `Private details are never shared with helpers.` | `Fields marked private are never shared with helpers. Ordinary names and notes in the parts you tick can be read.` |
| Settings → Helpers · `helper_settings.py` access summary | `May look and suggest` | `May look and suggest new records` |
| Settings → Helpers · `helper_connect.html` setup help | `Some AI assistant apps can use a helper through a small connector that comes with Dashboard Plus (it uses a standard called MCP). Paste these settings where your assistant's app lists its MCP servers, then replace YOUR-KEY-HERE with the helper's key.` | `If your AI assistant desktop app can run local MCP servers, copy these settings into its MCP server settings. Replace YOUR-KEY-HERE in DASHBOARD_PLUS_KEY with the key shown above. Do not paste the key into a chat.` (keep the current code styling on `YOUR-KEY-HERE`) |
| Settings → Helpers · `helper_key.html` key warning, Look and suggest branch | `look at and suggest records for` | `look at records and suggest new records for` |

