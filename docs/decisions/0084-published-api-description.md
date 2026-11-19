# 0084. A published, tested description of the helper API

- **Status:** Accepted
- **Date:** 2026-11-19
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
The helper API now has an official, written description (an OpenAPI 3.1 file) that a helper's author can read to
know exactly what to send and what comes back. The program serves it to helpers at `GET /api/v1/openapi.json`,
and a test fails if the description and the real routes ever drift apart.

## What we chose
- One file, `src/dashboard/web/openapi-v1.json`, written to match the real routes in `web/api.py`, including the
  hardening of decision 0074 and the review queue limit of decision 0085. All examples are invented.
- `GET /api/v1/openapi.json` sends that file unchanged. It is read-only (other methods are refused) and goes through
  the same door as every other helper route: it needs the helper key, a request from a web page (an `Origin`
  header) is refused, and the reply is never cached.
- `tests/test_api_contract.py` checks that every route under `/api/v1/` is in the file with the same methods and
  the file lists no others; that every error code the code can send is in the file and the file lists no code the
  code never sends; that every example fits its schema; and that real replies from a test app for every GET route,
  the suggestion route and each refusal fit the documented shape. A small checker in the test (required keys, types,
  lists, no undocumented keys) does this, so no new dependency is added.
- This file replaces Lane B's earlier draft in `workbench/drafts/agent_api/` as the source of truth. The draft was
  written before the code existed; it is left alone as history.

## Why it needs the key
- Nothing in the file is household data, so the choice is about the door, not secrecy. Putting it behind the key keeps
  the rule simple and true: **nothing under `/api/v1/` answers without a key**, so there is no exception for a web page
  or another program on this computer to find, and no second set of rules to get wrong.
- A helper that was not given the key has no use for it. A person who wants to read the description can open the
  file in the repository.
- Cost of the other choice: an open route would be the only unauthenticated thing under `/api/v1/`, a reason to
  loosen the guard in `only_this_computer`, and it would tell anything on this computer that Dashboard Plus is
  running and which version of the API it speaks.

## What else we considered
- **Serve it without a key** so a helper could discover the API first. Rejected for the reasons above. A helper is
  configured by a person who has the key and the repository.
- **Write the description from the code** (generate it from routes). Rejected: the replies are built by hand, so
  generation would need decorators on every route and would still miss the wording and examples. A hand-written file
  held to the code by a test is simpler.
- **Add a schema-validation library** to the tests. Rejected: we use a tiny part of JSON Schema, and the rule is few
  dependencies.

## What this costs us (the downsides)
- Whoever changes a route, a reply field or an error code must also edit the JSON file, by hand. The test fails and
  says what is missing, but it is extra work on every API change.
- The checker is deliberately small. It covers required keys, types, lists, allowed values and undocumented keys. It
  does not check string patterns, number ranges or the `values` inside a record (those depend on each household's
  modules and are described by `GET /tables`).
- The file is about 70 KB of JSON because shared error replies are written out where they are used.
- The `servers` entry cannot name the port, which changes at every start.

## How hard it is to undo
Easy. Delete the file, the route and the test. Nothing else depends on them.

## We should revisit this if
- A helper's author asks to learn about the API before they have a key.
- The file and the code drift apart in ways the test does not see.
- The API grows enough routes that generating the file becomes cheaper than keeping it by hand.
