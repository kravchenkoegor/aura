import asyncio
import contextlib
import json  # <<< Добавляем импорт json
import logging
import uuid
from typing import Any, Dict

from fastapi import (
  APIRouter,
  WebSocket,
  WebSocketDisconnect,
)
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websockets"])


async def _forward_redis_stream(
  redis: Redis,
  stream_name: str,
  websocket: WebSocket,
  start_id: str,
  extra_payload: Dict[str, Any] | None = None,
) -> None:
  """
  Читает Redis Stream и отправляет сообщения в WebSocket,
  пока не получит финальный статус ('done', 'failed', 'skipped').
  """
  last_id = start_id

  while True:
    try:
      resp = await redis.xread({stream_name: last_id}, block=15_000, count=50)
    except Exception as exc:
      logger.exception("Redis XREAD failed: %s", exc)
      await asyncio.sleep(1)
      continue

    if not resp:
      continue

    _, messages = resp[0]

    for msg_id, fields in messages:
      last_id = msg_id

      payload = {}
      if extra_payload:
        payload.update(extra_payload)

      # Декодируем поля, которые воркер отправил как JSON-строки
      for key, value in fields.items():
        if isinstance(value, str) and (value.startswith("{") or value.startswith("[")):
          try:
            payload[key] = json.loads(value)

          except json.JSONDecodeError:
            payload[key] = value  # Оставляем как есть, если не JSON

        else:
          payload[key] = value

      await websocket.send_json(payload)

      status = fields.get("status")
      if extra_payload and status in ("done", "failed", "skipped"):
        logger.info(
          "Final status '%s' received for task %s. Terminating stream listener.",
          status,
          extra_payload.get("task_id"),
        )
        return


@router.websocket("/ws/{task_id}")
async def websocket_post_status(
  websocket: WebSocket,
  task_id: str,
):
  """
  Отправляет обновления статуса задачи из Redis Stream клиенту.
  Соединение закрывается после получения финального статуса.
  """

  try:
    _ = uuid.UUID(task_id)

  except ValueError:
    logger.warning(
      "WebSocket connection attempt with invalid task_id format: %s", task_id
    )
    return

  await websocket.accept()

  stream_name = f"task:{task_id}:updates"
  redis_client = websocket.app.state.redis_client

  try:
    await _forward_redis_stream(
      redis=redis_client,
      stream_name=stream_name,
      websocket=websocket,
      start_id="$",  # Начинаем только с новых сообщений
      extra_payload={"task_id": task_id},
    )

  except WebSocketDisconnect:
    logger.info("Client for task %s disconnected prematurely.", task_id)

  except Exception as exc:
    logger.exception("WebSocket error for task %s: %s", task_id, exc)

  finally:
    logger.info("Closing WebSocket connection for task %s.", task_id)

    with contextlib.suppress(Exception):
      await websocket.close(code=1000)
