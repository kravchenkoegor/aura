import re


def extract_shortcode_from_url(url: str) -> str:
  '''Extracts the shortcode from various Instagram post URL formats.'''

  match = re.search(r'/(p|reel|tv)/([^/]+)', url)
  if not match:
    raise ValueError('Invalid or unsupported Instagram post URL format.')

  return match.group(2)
