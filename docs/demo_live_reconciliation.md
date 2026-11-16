# Demo and Live Reconciliation Checkpoint

Date: November 15, 2026

## Read-only baseline

- Live Control Service was checked at `100.101.133.66` and returned healthy service and database responses.
- Demo Control Service was checked at `192.168.2.37` and `100.108.80.111` and returned HTTP 200 health responses.
- Before this demo update, live/source Control Service was `0.6.8` and demo Control Service was `0.6.7`.
- The local desktop source is on `main` at `2.1.22`.
- The demo download site was serving `demo-v2.2.12`; this remains a separate demo release line.

## Demo-only reconciliation

This branch brings the demo Control Service to `0.6.9` from the current source baseline and adds the Care Notebook API. It does not deploy to the live Raspberry Pi and does not change live resident data.

The database change is additive only:

- creates `notebook_api_tokens` if it does not exist;
- does not drop, truncate, recreate, or rewrite resident tables;
- stores notebook tokens as hashes;
- stores notebook notes through the existing `resident_change_requests` table;
- uses the existing Approvals page for nurse-admin decisions.

The demo deployment keeps a timestamped backup of the previous Control Service source before restart. If the demo needs to be reverted, restore that backup and restart `whisperwood-control`; no resident table rollback is required.

## Live protection

The live Pi must not be updated from this branch until the demo API contract, permissions, approval behavior, and display forwarding have been tested and signed off. The live API key and resident database are not included in the notebook client.
