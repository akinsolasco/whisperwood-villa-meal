# Care Notebook API

This is a restricted API for a remote care notebook or large-screen interface. It is separate from the main Control API key and does not provide database, SSH, device, firmware, or IT Admin access.

## Access Model

Use the dedicated notebook service port `8095` for private testing or an outbound HTTPS tunnel for a production URL. Add only TCP `8095` to the approved Tailscale group. Do not grant that group TCP `7000`, and do not port-forward PostgreSQL, SSH, Operation Manager, or the full Control Service.

The notebook key is sent as either:

```http
X-Whisperwood-Notebook-Key: wwnb_...
```

or:

```http
Authorization: Bearer wwnb_...
```

Raw notebook keys are returned only when created and are stored as hashes. A key can be expired or revoked without changing resident data.

## Admin Token Management

These routes require the existing Control Service key and should only be called by IT Admin tooling or a controlled setup script:

```text
POST /notebook/tokens
GET  /notebook/tokens
POST /notebook/tokens/{id}/revoke
```

Example token creation payload:

```json
{
  "label": "care-notebook-demo",
  "scopes": [
    "residents:read",
    "attachments:read",
    "change_requests:create",
    "change_requests:read_own"
  ],
  "expires_in_days": 30
}
```

Available scopes:

- `residents:read`: read active resident display information and incremental changes.
- `attachments:read`: retrieve attached source documents and resident images through protected routes.
- `change_requests:create`: submit notes or proposed changes for approval.
- `change_requests:read_own`: read the status of requests submitted by that notebook.
- `change_requests:read_all`: optional wider request visibility for a trusted review client.

## Resident Read Routes

```text
GET /notebook/health
GET /notebook/residents
GET /notebook/residents/{resident_id}
GET /notebook/residents/{resident_id}/document
GET /notebook/residents/{resident_id}/image
```

Use `GET /notebook/residents?since=<updated_at>` for incremental refresh. The response deliberately omits server filesystem paths.

## Notes and Approval

```text
POST /notebook/change-requests
GET  /notebook/change-requests
```

Example note submission:

```json
{
  "resident_id": 26,
  "comment": "Resident asked for assistance during breakfast.",
  "proposed_payload": {},
  "client_note_id": "tablet-2026-001"
}
```

Structured proposed changes can be submitted in `proposed_payload`, but the request is always created with `PENDING` status. The existing desktop Approvals page is the decision point. Only an authorized nurse administrator can approve or reject it.

When approved, the Control Service:

1. applies only allow-listed resident fields;
2. creates a resident audit record with before and after values;
3. records the approving user and review note; and
4. forwards the approved resident payload to the paired e-paper display.

If the display is offline, the resident approval remains recorded and the response reports that display forwarding needs a retry. It must not be presented as successfully delivered to the device.

## Data Safety

The notebook is not allowed to update residents directly. Voice or AI output must first become a pending change request. Keep the notebook API behind user authentication and a scoped token, and use local or approved transcription processing for resident information.
