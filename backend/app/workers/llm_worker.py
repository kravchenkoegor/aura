import asyncio
import json
import logging
import os
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict
from uuid import UUID

import httpx
from dotenv import load_dotenv
from redis.asyncio import Redis, from_url
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import async_engine
from app.data.task import update_task
from app.schemas import TaskStatus, TaskUpdate
from app.service.compliment_service import ComplimentService
from app.service.gemini_service.gemini_service import GeminiService
from app.service.image_service import ImageService

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s %(levelname)s: %(message)s",
)

REDIS_STREAM = os.getenv(
  "REDIS_STREAM_COMPLIMENTS",
  "tasks:compliment_generation:stream",
)
CONSUMER_GROUP = os.getenv(
  "REDIS_CONSUMER_GROUP_COMPLIMENTS",
  "compliment_generation_group",
)
CONSUMER_NAME = os.getenv("REDIS_CONSUMER_NAME_COMPLIMENTS", "worker-compliments-1")
BATCH_SIZE = int(os.getenv("REDIS_BATCH_SIZE_COMPLIMENTS", "5"))
IDLE_TIMEOUT_MS = int(os.getenv("REDIS_BLOCK_MS_COMPLIMENTS", "10000"))


class CustomJSONEncoder(json.JSONEncoder):
  def default(self, o):
    if isinstance(o, UUID):
      return str(o)

    if isinstance(o, (datetime, date)):
      return o.isoformat()

    return json.JSONEncoder.default(self, o)


async def _publish_task_update(
  redis_client: Redis,
  task_id: str,
  payload: Dict[str, Any],
):
  stream_name = f"task:{task_id}:updates"
  final_payload = {
    k: json.dumps(v, cls=CustomJSONEncoder) if isinstance(v, (dict, list)) else str(v)
    for k, v in payload.items()
  }
  try:
    await redis_client.xadd(stream_name, final_payload)

    status = final_payload.get("status", "no_status")
    logger.info(f"Published update to {stream_name}: {status}")

  except Exception as e:
    logger.error(f"Failed to publish update to {stream_name}: {e}")


async def handle_message(
  session: AsyncSession,
  redis_client: Redis,
  message: dict,
):
  task_id = message.get("task_id")
  post_id = message.get("post_id")
  user_id = message.get("user_id")

  if not task_id or not post_id or not user_id:
    logger.warning("Invalid message: %s", message)
    return

  await _publish_task_update(
    redis_client,
    task_id,
    {
      "status": TaskStatus.in_progress.value,
      "detail": "Starting compliment generation...",
    },
  )

  logger.info(f"Received task {task_id} to generate compliments for post: {post_id}")

  start = time.monotonic()
  started_at = datetime.now(timezone.utc)

  try:
    image_service = ImageService(session)
    gemini_service = GeminiService(session)
    compliment_service = ComplimentService(session)

    image = await image_service.get_primary_image_by_post_id(
      post_id=post_id,
      user_id=user_id,
    )
    if not image:
      raise ValueError(f"No primary image found for post ID {post_id}")

    async with httpx.AsyncClient() as client:
      http_response = await client.get(image.storage_key)
      http_response.raise_for_status()
      image_bytes = http_response.content

    (
      generation_metadata,
      candidates_data,
    ) = await gemini_service.create_chat(image_bytes=image_bytes)

    await compliment_service.create_compliments(
      image_id=image.id,
      generation_metadata_id=generation_metadata.id,
      candidates=candidates_data,
    )

    await _publish_task_update(
      redis_client,
      task_id,
      {
        "status": TaskStatus.done.value,
        "result": "Compliments created successfully",
      },
    )

    await update_task(
      session=session,
      task_id=task_id,
      user_id=user_id,
      task_update=TaskUpdate(
        status=TaskStatus.done,
        started_at=started_at,
        ended_at=datetime.now(timezone.utc),
        duration=timedelta(seconds=time.monotonic() - start),
      ),
    )
    await session.commit()

  except Exception as e:
    logger.exception(f"Error processing task {task_id}: {e}")

    await _publish_task_update(
      redis_client,
      task_id,
      {
        "status": TaskStatus.failed.value,
        "error": str(e),
      },
    )

    await update_task(
      session=session,
      task_id=task_id,
      user_id=user_id,
      task_update=TaskUpdate(
        status=TaskStatus.failed,
        error_message=str(e),
        started_at=started_at,
        ended_at=datetime.now(timezone.utc),
        duration=timedelta(seconds=time.monotonic() - start),
      ),
    )

    await session.commit()


async def _process_entry(
  redis_client: Redis,
  entry_id: str,
  data: dict,
):
  try:
    payload = {
      k: json.loads(v) if isinstance(v, str) and v.startswith(("{", "[")) else v
      for k, v in data.items()
    }

    async with AsyncSession(async_engine) as session:
      await handle_message(session, redis_client, payload)

    await redis_client.xack(REDIS_STREAM, CONSUMER_GROUP, entry_id)
    logger.info(f"ACK: {entry_id}")

  except Exception:
    logger.exception(f"Failed to process entry {entry_id}")


async def start_worker(concurrency: int = 3):
  redis_url = os.getenv("REDIS_URL")

  if not redis_url:
    logger.warning("REDIS_URL is not set!")
    return

  redis_client = from_url(redis_url, decode_responses=True)

  try:
    await redis_client.xgroup_create(
      name=REDIS_STREAM,
      groupname=CONSUMER_GROUP,
      id="0",
      mkstream=True,
    )
    logger.info(f"Created consumer group {CONSUMER_GROUP}")

  except Exception as e:
    if "BUSYGROUP" in str(e):
      logger.info(f"Consumer group {CONSUMER_GROUP} already exists.")

    else:
      raise

  sem = asyncio.Semaphore(concurrency)
  logger.info(f"Worker started: concurrency={concurrency}")

  async def handle_entry(entry_id, data):
    async with sem:
      await _process_entry(redis_client, entry_id, data)

  while True:
    try:
      entries = await redis_client.xreadgroup(
        groupname=CONSUMER_GROUP,
        consumername=CONSUMER_NAME,
        streams={REDIS_STREAM: ">"},
        count=BATCH_SIZE,
        block=IDLE_TIMEOUT_MS,
      )

      if not entries:
        continue

      tasks = []

      for _, msgs in entries:
        for entry_id, data in msgs:
          task = asyncio.create_task(handle_entry(entry_id, data))
          tasks.append(task)

    except asyncio.CancelledError:
      logger.info("Worker cancelled.")
      break

    except Exception:
      logger.exception("Error in worker loop")
      await asyncio.sleep(2)


if __name__ == "__main__":
  try:
    concurrency = int(os.getenv("WORKER_CONCURRENCY_COMPLIMENTS", "3"))
    asyncio.run(start_worker(concurrency))

  except KeyboardInterrupt:
    print("Worker stopped by user.")
