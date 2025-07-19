from fastapi import (
  APIRouter,
  WebSocket,
  WebSocketDisconnect,
)

router = APIRouter(tags=["websockets"])


@router.websocket("/ws/{task_id}")
async def websocket_post_status(
  websocket: WebSocket,
  task_id: str,
):
  try:
    # Ожидаем, пока соединение не будет закрыто клиентом или сервером
    await websocket.receive_text()

  except WebSocketDisconnect:
    print(f"Клиент {task_id} отключился.")
