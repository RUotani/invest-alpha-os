# Sample Output Regeneration Contract

Date: 2026-06-05

## Decision

Add `sample-output-regeneration-contract` as a source-only CLI that lists allowed sample regeneration commands and their
expected markers without executing them.

## Rationale

Sample regeneration should be reproducible, but the safe boundary must stay explicit. The contract records stdout-only
or read-only commands and forbidden actions so future operators do not confuse sample regeneration with report artifact
write, workflow dispatch, provider access, cache write, actual import, raw input parsing, email send, or trading action.

## Boundary

- contract output only
- no command execution by the contract
- no workflow change
- no manual workflow_dispatch
- no live HTTP / market-data live fetch
- no cache write / actual import / manual import
- no broker API / raw Excel direct parsing
- no env/secret display
- no trading action / real email send

## Follow-Up

Use this contract as the reference before refreshing sample output files or reports-private sample artifacts under a
future explicitly approved sample refresh task.
