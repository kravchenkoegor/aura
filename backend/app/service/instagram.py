from typing import NamedTuple
from urllib.parse import urlparse

import instaloader

from app.models import Image


class PostSidecarNode(NamedTuple):
  """
  Custom PostSidecarNode to handle sidecar media extraction.
  This is a workaround for the fact that Instaloader's PostSidecarNode
  does not expose the display_url directly.
  """

  display_url: str
  width: int
  height: int


L = instaloader.Instaloader(quiet=True, compress_json=False)


def get_sidecar_nodes(post_data: instaloader.Post) -> list[PostSidecarNode]:
  edges = post_data._node.get("edge_sidecar_to_children", {}).get("edges", [])

  if not edges:
    raise ValueError("Post does not contain sidecar media.")

  nodes = []

  for _, edge in enumerate(edges):
    node = edge["node"]
    is_video = node["is_video"]

    if is_video:
      continue  # Skip video nodes

    dimensions = node["dimensions"]
    display_url = node["display_url"]

    nodes.append(
      PostSidecarNode(
        display_url=display_url,
        width=dimensions["width"],
        height=dimensions["height"],
      )
    )

  return nodes


def extract_filename_from_url(url: str) -> str:
  path = urlparse(url).path
  filename = path.split("/")[-1]

  if not filename:
    raise ValueError("Could not extract filename from URL.")

  return filename


def download_instagram_post(shortcode: str):
  """
  Imports an Instagram post from a URL.

  1. Fetches metadata and media from Instagram.
  2. Creates a new Author if they don't exist.
  3. Creates a new Post record.
  4. Creates new Image records for all images in the post.
  """

  try:
    post_data = instaloader.Post.from_shortcode(
      L.context,
      shortcode,
    )

    L.download_post(post_data, shortcode)

  except instaloader.exceptions.InstaloaderException as e:
    raise ValueError(f'Could not fetch post "{shortcode}". Error: {e}')

  if post_data.is_video:
    raise ValueError(
      f'Post "{shortcode}" is a video, not an image post. '
      "Video posts are not supported."
    )

  description = post_data.caption or ""
  taken_at = post_data.date_utc

  images_to_add = []

  is_carousel = post_data.typename == "GraphSidecar"

  if is_carousel:
    nodes = get_sidecar_nodes(post_data)

    for i, node in enumerate(nodes):
      images_to_add.append(
        Image(
          post_id=shortcode,
          storage_key=node.display_url,
          height=node.height,
          width=node.width,
          is_primary=(i == 0),
        )
      )
  else:  # Single image
    dimensions = post_data._node["dimensions"]

    images_to_add.append(
      Image(
        post_id=shortcode,
        storage_key=post_data.url,
        height=dimensions["height"],
        width=dimensions["width"],
        is_primary=True,
      )
    )

  # TODO: create class
  return {
    "owner_username": post_data.owner_username,
    "id": shortcode,
    "description": description,
    "taken_at": taken_at,
    "images": images_to_add,
  }
