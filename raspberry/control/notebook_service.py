"""Dedicated Care Notebook API service.

This process deliberately exposes only the restricted notebook routes.  The
full Control Service remains on its own port for the desktop application and
IT Admin tooling.
"""

from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app import (
    APP_VERSION,
    NotebookChangeRequestPayload,
    notebook_change_requests as notebook_change_requests_handler,
    notebook_create_change_request as notebook_create_change_request_handler,
    notebook_document as notebook_document_handler,
    notebook_health as notebook_health_handler,
    notebook_image as notebook_image_handler,
    notebook_resident as notebook_resident_handler,
    notebook_residents as notebook_residents_handler,
)


app = FastAPI(
    title="Whisperwood Care Notebook API",
    version=APP_VERSION,
    description="Restricted resident read and approval-request service.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Whisperwood-Notebook-Key"],
)


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "notebook",
        "version": APP_VERSION,
    }


@app.get("/notebook/health")
def notebook_health(request: Request):
    return notebook_health_handler(request)


@app.get("/notebook/residents")
def notebook_residents(request: Request, since: Optional[str] = None, limit: int = 500):
    return notebook_residents_handler(request, since=since, limit=limit)


@app.get("/notebook/residents/{resident_id}")
def notebook_resident(resident_id: int, request: Request):
    return notebook_resident_handler(resident_id, request)


@app.get("/notebook/residents/{resident_id}/document")
def notebook_document(resident_id: int, request: Request):
    return notebook_document_handler(resident_id, request)


@app.get("/notebook/residents/{resident_id}/image")
def notebook_image(resident_id: int, request: Request):
    return notebook_image_handler(resident_id, request)


@app.get("/notebook/change-requests")
def notebook_change_requests(request: Request, status: Optional[str] = None, limit: int = 100):
    return notebook_change_requests_handler(request, status=status, limit=limit)


@app.post("/notebook/change-requests")
def notebook_create_change_request(payload: NotebookChangeRequestPayload, request: Request):
    return notebook_create_change_request_handler(payload, request)
