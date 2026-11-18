# Ten household jobs for an API helper

The [machine-readable examples](helper-jobs.json) give an exact HTTP method, route, request body, illustrative JSON response, Review words and after-decision result for **ten jobs**. Checked **18 November 2026** against the [Agent API v1 plan](../../../docs/plans/agent-api-v1.md), shipped module schemas and the fictional Smith, Garcia and Taylor example TOMLs. Seven jobs suggest a new row; three only read Needs attention. The skeleton is still in Lane A's draft PR, so these are **contract examples**, not captured live API responses. The `/attention` envelope and `/batches` details are provisional until `api.py` merges.

| # | Household job | Helper grant in example | Human result |
|---:|---|---|---|
| 1 | Smith: paper receipt → 2 tins of Kidney beans in a new dated Garage batch | Stock | Accept adds one Bought or added movement and raises the item from 13 to 15 tins. |
| 2 | Garcia: Luna's paper weigh-in → 4.3 kg entry | Pets, People | Accept adds one dated weight; no health conclusion. |
| 3 | Taylor: “What's running low?” → AA batteries 2, minimum 4 | Stock | Read only; Review stays empty. |
| 4 | Smith: Home insurance policy review date | Documents, People, Stock | Read only; the household-entered 14 Dec date is repeated, not treated as a legal renewal rule. |
| 5 | Garcia: Air conditioner filter Work done note | Home care, People, Stock | Accept adds history; it does not advance the job's next date. |
| 6 | Taylor: proposed car tyre check | Vehicles, People, Stock | Reject leaves the service list unchanged. |
| 7 | Smith: Car first aid kit check | Medical, Stock | Accept adds a check; it does not change Stock or the kit's current check date. |
| 8 | Garcia: generic appliance warranty pointer | Documents, Stock | Accept adds a document at Hallway › Hall closet, without any document number. |
| 9 | Taylor: water basis, 12 drinkable litres and one excluded distilled litre | Stock | Read only; the helper cannot flip the Safe to drink answer. |
| 10 | Taylor: Example blue box inside Outside › Bike shed | Stock | Accept adds one Place with the full nested path. |

**How to read each example:** `look_up_first` shows the GET requests a helper should use to resolve the fixture's IDs. The listed IDs were verified after loading each example into a new temporary folder; a real helper must resolve IDs in the current household rather than copy the sample numbers. `request` is the helper call. `response` is the proposed 201 or 200 result. For a POST, `review` gives exact displayed words and the person's decision, then `after_review_request` and `after_review_response` show the helper's batch status. Proposed `batch_id` and proposal IDs are illustrative; the record IDs after Accept match the fresh examples plus one new row. A rejected proposal has no record ID. For the three GET jobs, `review` explicitly stays unchanged.

A receipt is interpreted outside the API: v1 has no receipt image upload or parser. V1 can only **add** suggestions; it cannot change an existing item, document, date, stock minimum or private field. It never accepts its own suggestion. Values in `why` and Review are untrusted helper text, so the screen must escape them and show the verified helper identity. The examples deliberately grant linked modules when a GET could include linked records; [item 48](ABUSE_CASES.md) calls out unresolved cross-module ID leakage and validation. No real keys, names or documents are included.

I validated the seven POST `table`/`values` pairs against the current `Records.create` contracts in separate temporary copies of the three example households; all seven were accepted by the core's normal create path. That verifies field types and links only. It does **not** verify helper authentication, staging, Review, API response envelopes or the draft PR. After the skeleton merges, replay the JSON requests against a local invented household and replace any provisional response shape with captured behavior. [OPENAPI_NOTES.md](OPENAPI_NOTES.md) lists the contract sync points.
