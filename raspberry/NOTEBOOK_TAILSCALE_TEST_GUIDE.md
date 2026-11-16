# Demo Care Notebook Test Guide

This guide is for the demo Raspberry Pi only. The current route is private to the approved Tailscale tailnet.

## 1. Give the tester network access

The tester must:

1. Install Tailscale on the laptop or tablet.
2. Sign in with the Tailscale account invited to the approved tailnet.
3. Confirm the Tailscale client is connected.
4. Do not give the tester Raspberry Pi SSH credentials, PostgreSQL credentials, or the main Control Service key.

The demo address is:

```text
100.108.80.111
```

The notebook API is on its dedicated port `8095` through the Tailscale network.
The tester does not need access to the main Control Service port `7000`:

```text
http://100.108.80.111:8095
```

## 2. Confirm the route

On Windows PowerShell:

```powershell
tailscale ping 100.108.80.111
Test-NetConnection 100.108.80.111 -Port 8095
```

The TCP test should report `TcpTestSucceeded : True`.

## 3. Set the notebook key without saving it in the project

Open PowerShell and set the values only for the current terminal window:

```powershell
$env:NOTEBOOK_API_BASE_URL = "http://100.108.80.111:8095"
$env:NOTEBOOK_API_KEY = "PASTE_THE_NOTEBOOK_KEY_HERE"
```

The key is the separate `wwnb_...` key created for the notebook. Never use the main `X-Whisperwood-Key` control key.

## 4. Run the read-only test

From the project folder:

```powershell
python scripts/test_notebook_api.py
```

The test checks:

- notebook health;
- resident list access;
- submitted-request status access; and
- that the notebook key is blocked from the unrestricted `/residents` endpoint.

## 5. Submit a test note

Only run this after choosing a demo resident. It creates a real pending approval request, so the nurse admin must reject it after confirming the test.

Replace `<resident-id>` with an ID returned by the read-only resident test:

```powershell
python scripts/test_notebook_api.py --submit-note --resident-id <resident-id> --comment "Notebook voice-note test; reject after review."
```

The request should appear in the desktop application's existing **Approvals** section as `PENDING`.

## 6. Verify the approval workflow

The nurse admin should:

1. Open **Approvals**.
2. Select the notebook request.
3. Review the note and proposed fields.
4. Add a decision note.
5. Reject the smoke-test request, or approve a deliberate test request.

For a deliberately approved structured change, the backend records the before/after audit and attempts to send the approved resident payload to the paired e-paper display.

## 7. Access and safety boundaries

The notebook key can read approved resident display information, read attachments, submit change requests, and see the status of requests created by that notebook. It cannot access SSH, PostgreSQL, firmware, pairing, IT Admin, or the unrestricted resident API.

The key expires after one year and can be revoked by IT Admin tooling through the protected token-management endpoint. The external tester should only receive the Tailscale invitation and notebook key.
