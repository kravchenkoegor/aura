import asyncio
import json
import logging
import os
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from dotenv import load_dotenv
from redis.asyncio import Redis, from_url
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import async_engine
from app.data.author import (
  create_author,
  get_author_by_id,
)
from app.data.image import (
  create_images,
  get_primary_image_by_post_id,
)
from app.data.post import update_post
from app.data.task import update_task
from app.schemas import (
  PostUpdate,
  TaskStatus,
  TaskUpdate,
)
from app.service.instagram import download_instagram_post
from app.utils.instagram import extract_shortcode_from_url

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s %(levelname)s: %(message)s",
)

REDIS_STREAM = os.getenv("REDIS_STREAM", "tasks:instagram_download:stream")
CONSUMER_GROUP = os.getenv("REDIS_CONSUMER_GROUP", "instagram_download_group")
CONSUMER_NAME = os.getenv("REDIS_CONSUMER_NAME", "worker-1")
BATCH_SIZE = int(os.getenv("REDIS_BATCH_SIZE", "5"))
IDLE_TIMEOUT_MS = int(os.getenv("REDIS_BLOCK_MS", "10000"))


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
  """
  Публикует обновление статуса задачи в её персональный Redis Stream.
  """

  stream_name = f"task:{task_id}:updates"

  final_payload = {}
  for key, value in payload.items():
    if isinstance(value, (dict, list)):
      final_payload[key] = json.dumps(value, cls=CustomJSONEncoder)
    else:
      final_payload[key] = str(value)

  try:
    await redis_client.xadd(stream_name, final_payload)
    logger.info(
      f"Published update to {stream_name}: {final_payload.get('status', 'no_status')}"
    )

  except Exception as e:
    logger.error(f"Failed to publish update to {stream_name}: {e}")


async def handle_message(
  session: AsyncSession,
  redis_client: Redis,
  message: dict,
) -> Optional[List[dict]]:
  task_id = message.get("task_id")
  url = message.get("url")
  if not task_id or not url:
    logger.warning("Invalid message: %s", message)
    return

  task_id = str(task_id)
  url = str(url)

  await _publish_task_update(
    redis_client,
    task_id,
    {
      "status": TaskStatus.in_progress.value,
      "detail": "Starting download...",
    },
  )

  logger.info(f"Received task {task_id} to download post: {url}")

  start = time.monotonic()
  started_at = datetime.now(timezone.utc)

  try:
    post_id = extract_shortcode_from_url(url)
    existing_image = await get_primary_image_by_post_id(
      session=session,
      post_id=post_id,
    )

    if existing_image:
      logger.info(f"Post {post_id} already downloaded. Skipping.")

      await _publish_task_update(
        redis_client,
        task_id,
        {
          "status": TaskStatus.skipped.value,
          "detail": f"Post {post_id} already exists.",
        },
      )

      await update_task(
        session=session,
        task_id=task_id,
        task_update=TaskUpdate(
          status=TaskStatus.skipped,
          started_at=started_at,
          ended_at=datetime.now(timezone.utc),
          duration=timedelta(seconds=time.monotonic() - start),
        ),
      )
      await session.commit()
      return

    post_data = await asyncio.to_thread(download_instagram_post, shortcode=post_id)
    images_to_add = post_data["images"]
    username = post_data["owner_username"]

    author_id = await get_author_by_id(session=session, author_id=username)
    if not author_id:
      author_id = await create_author(session=session, username=username)

    await update_post(
      session=session,
      post_id=post_data["id"],
      post_update=PostUpdate(
        author_id=author_id,
        description=post_data["description"],
        taken_at=post_data["taken_at"],
      ),
    )

    images = await create_images(session=session, images=images_to_add)
    await session.flush()
    images_dicts = [image.model_dump(mode="json") for image in images]

    await _publish_task_update(
      redis_client,
      task_id,
      {
        "status": TaskStatus.done.value,
        "result": images_dicts,
      },
    )

    await update_task(
      session=session,
      task_id=task_id,
      task_update=TaskUpdate(
        status=TaskStatus.done,
        started_at=started_at,
        ended_at=datetime.now(timezone.utc),
        duration=timedelta(seconds=time.monotonic() - start),
      ),
    )
    await session.commit()
    return images_dicts

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
      task_update=TaskUpdate(
        status=TaskStatus.failed,
        error_message=str(e),
        started_at=started_at,
        ended_at=datetime.now(timezone.utc),
        duration=timedelta(seconds=time.monotonic() - start),
      ),
    )
    await session.commit()


async def _process_entry(redis_client: Redis, entry_id: str, data: dict):
  """Обработка одной записи из Stream."""

  try:
    # Этот код для парсинга JSON можно упростить, если вы всегда знаете,
    # что полезная нагрузка лежит в одном поле, например, 'data'.
    # Для универсальности оставим как есть.
    payload = {
      k: json.loads(v) if isinstance(
        v, str) and v.startswith(("{", "[")) else v
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
      # Здесь можно добавить логику graceful shutdown, например, дождаться завершения текущих задач
      break
    except Exception:
      logger.exception("Error in worker loop")
      await asyncio.sleep(2)


if __name__ == "__main__":
  try:
    concurrency = int(os.getenv("WORKER_CONCURRENCY", "3"))
    asyncio.run(start_worker(concurrency))

  except KeyboardInterrupt:
    print("Worker stopped by user.")
