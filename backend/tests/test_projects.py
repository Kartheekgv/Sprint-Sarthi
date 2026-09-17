import io

import pytest
from openpyxl import Workbook


@pytest.mark.asyncio
async def test_create_project_and_upload_pdf(client):
    created = await client.post("/api/v1/projects", json={"name": "Payments Modernization", "description": "Migrate safely"})
    assert created.status_code == 201
    project = created.json()
    assert project["status"] == "draft"
    assert created.headers["x-request-id"]

    uploaded = await client.post(
        f"/api/v1/projects/{project['id']}/documents",
        files={"file": ("../architecture.pdf", io.BytesIO(b"%PDF-1.7 sample"), "application/pdf")},
    )
    assert uploaded.status_code == 201
    document = uploaded.json()
    assert document["document_code"] == "DOC-001"
    assert document["original_name"] == "architecture.pdf"
    assert document["sha256"]
    assert document["status"] == "uploaded"


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_file(client):
    created = await client.post("/api/v1/projects", json={"name": "Secure Project"})
    response = await client.post(
        f"/api/v1/projects/{created.json()['id']}/documents",
        files={"file": ("payload.exe", b"not allowed", "application/octet-stream")},
    )
    assert response.status_code == 415


@pytest.mark.asyncio
async def test_upload_requires_existing_project(client):
    response = await client.post(
        "/api/v1/projects/00000000-0000-0000-0000-000000000000/documents",
        files={"file": ("architecture.pdf", b"%PDF", "application/pdf")},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_process_document_extracts_xlsx_content(client):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Requirements"
    sheet.append(["ID", "Requirement"])
    sheet.append(["REQ-1", "Users can approve the final export"])
    content = io.BytesIO()
    workbook.save(content)
    content.seek(0)

    created = await client.post("/api/v1/projects", json={"name": "Analysis Project"})
    uploaded = await client.post(
        f"/api/v1/projects/{created.json()['id']}/documents",
        files={"file": ("requirements.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    processed = await client.post(f"/api/v1/documents/{uploaded.json()['id']}/process")

    assert processed.status_code == 201
    assert processed.json()["status"] == "completed"
    assert processed.json()["progress"] == 100

    chunks = await client.get(f"/api/v1/documents/{uploaded.json()['id']}/chunks")
    assert chunks.status_code == 200
    first_chunk = chunks.json()[0]
    assert first_chunk["document_id"] == "DOC-001"
    assert first_chunk["chunk_id"] == "CHUNK-001"
    assert first_chunk["token_count"] > 0
    assert "Users can approve" in first_chunk["content"]


@pytest.mark.asyncio
async def test_process_markdown_preserves_headings(client):
    created = await client.post("/api/v1/projects", json={"name": "Markdown Project"})
    uploaded = await client.post(
        f"/api/v1/projects/{created.json()['id']}/documents",
        files={"file": ("requirements.md", b"# Authentication\nAdministrators approve access requests.", "text/markdown")},
    )
    assert uploaded.status_code == 201
    processed = await client.post(f"/api/v1/documents/{uploaded.json()['id']}/process")
    assert processed.status_code == 201
    chunks = (await client.get(f"/api/v1/documents/{uploaded.json()['id']}/chunks")).json()
    assert chunks[0]["section_heading"] == "Authentication"
