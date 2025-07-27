import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_task_requires_authentication(client: AsyncClient):
  """Test that creating a task requires authentication."""

  response = await client.post(
    "/tasks/",
    json={"url": "https://www.instagram.com/p/ABC123/"},
  )
  assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_task_with_authentication(
  client: AsyncClient,
  normal_user_token_headers: dict,
):
  """Test that authenticated users can create tasks."""

  response = await client.post(
    "/tasks/",
    headers=normal_user_token_headers,
    json={"url": "https://www.instagram.com/p/ABC123/"},
  )
  assert response.status_code == 202

  data = response.json()
  assert "id" in data
  assert "user_id" in data


@pytest.mark.asyncio
async def test_get_task_requires_authentication(client: AsyncClient):
  """Test that getting a task requires authentication."""

  response = await client.get("/tasks/123e4567-e89b-12d3-a456-426614174000")
  assert response.status_code == 401


@pytest.mark.asyncio
async def test_user_cannot_access_other_user_task(
  client: AsyncClient,
  normal_user_token_headers: dict,
  other_user_task_id: str,
):
  """Test that users cannot access tasks created by other users."""

  response = await client.get(
    f"/tasks/{other_user_task_id}",
    headers=normal_user_token_headers,
  )
  assert response.status_code == 403


@pytest.mark.asyncio
async def test_superuser_can_access_all_tasks(
  client: AsyncClient,
  superuser_token_headers: dict,
  any_user_task_id: str,
):
  """Test that superusers can access any task."""

  response = await client.get(
    f"/tasks/{any_user_task_id}",
    headers=superuser_token_headers,
  )
  assert response.status_code == 200
