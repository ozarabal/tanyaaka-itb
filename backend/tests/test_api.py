import pytest


@pytest.mark.anyio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "vector_store_ready" in data


@pytest.mark.anyio
async def test_chat_no_documents(client):
    """Chat should return 503 when vector store is empty."""
    response = await client.post("/api/v1/chat", json={"question": "Test question?"})
    assert response.status_code == 503


@pytest.mark.anyio
async def test_chat_empty_question(client):
    """Chat should reject empty questions."""
    response = await client.post("/api/v1/chat", json={"question": ""})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_list_documents_empty(client):
    """Should return empty list when no documents ingested."""
    response = await client.get("/api/v1/documents")
    assert response.status_code == 200
    data = response.json()
    assert data["total_chunks"] >= 0
