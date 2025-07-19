from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
import httpx

router = APIRouter(prefix='/proxy', tags=['proxy'])


@router.get("/{url:path}")
async def proxy_image(url: str, request: Request):
  """
  Proxies image requests to avoid CORS issues. It reconstructs the target
  URL from the request path and query parameters.
  Example: /proxy/https://example.com/image.jpg?param=value
  """
  # FastAPI's path converter turns "://" into ":/", so we fix it back.
  if url.startswith("http:/") and not url.startswith("http://"):
    url = "http://" + url[6:]
  elif url.startswith("https:/") and not url.startswith("https://"):
    url = "https://" + url[7:]

  if request.query_params:
    url += "?" + str(request.query_params)

  client = httpx.AsyncClient()
  try:
    # client.stream() returns an async context manager, not an awaitable.
    # We must manually enter it to get the response object.
    stream_context = client.stream("GET", url)
    response = await stream_context.__aenter__()
    response.raise_for_status()

    async def stream_body_and_close_resources():
      try:
        async for chunk in response.aiter_bytes():
          yield chunk
      finally:
        # Manually exit the context manager to close the response and stream.
        await stream_context.__aexit__(None, None, None)
        await client.aclose()

    return StreamingResponse(
        stream_body_and_close_resources(),
        media_type=response.headers.get(
            "content-type", "image/jpeg"),
        headers={"Access-Control-Allow-Origin": "*"},
    )
  except httpx.HTTPStatusError as e:
    await client.aclose()
    raise HTTPException(status_code=e.response.status_code,
                        detail="Upstream image not found or failed.")
  except httpx.RequestError:
    await client.aclose()
    raise HTTPException(
        status_code=502, detail="Could not connect to the upstream server.")
  except Exception:
    await client.aclose()
    raise
