# Enhanced Living Care Notebook Client

This is a small Windows demonstration client for the restricted Whisperwood
Notebook API. It is intended as a starting point for a large-screen or voice
notebook project.

The packaged client uses standard Windows Tkinter rather than Qt, so the team
does not need to install Python, PyQt, or a separate Qt runtime.

## What it can do

- connect to the dedicated notebook API using a scoped `wwnb_...` key;
- search and select active residents;
- refresh the resident list automatically every five seconds while connected;
- show approved resident display fields, safety-review state, and attachment names;
- submit an observation or note for nurse/admin approval; and
- show the status of notes created by this notebook.

It cannot directly edit resident records, approve requests, access the main
Control Service, access the database, or access Raspberry Pi administration.

## Run the packaged demo

1. Extract `EnhancedLivingCareNotebook-demo-v0.1.0.zip`.
2. Start `EnhancedLivingCareNotebook.exe` (client v0.1.2).
3. Confirm the notebook API address supplied by the project owner.
4. Paste the separate notebook API key into the API key field.
5. Select **Connect**, then select a resident.
6. Enter a test note and select **Send for approval**.

The note appears in the main application's existing **Approvals** page as
`PENDING`. It must be approved or rejected there; the notebook client does not
change resident information by itself.

## API boundary

The client uses the dedicated notebook service only:

```text
GET  /notebook/health
GET  /notebook/residents
GET  /notebook/residents/{id}
GET  /notebook/change-requests
POST /notebook/change-requests
```

The API key is a secret. Do not place it in source code, email it with the
executable, or reuse the main Control Service key. The current demo address is
`https://consistent-gilbert-graphs-adjacent.trycloudflare.com`. It is a
temporary Cloudflare Quick Tunnel address and may change if the tunnel is
restarted.
