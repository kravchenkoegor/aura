import asyncio
import logging
from typing import Optional
from urllib.parse import urlparse

from playwright.async_api import Browser, Page, async_playwright

from app.models import Image

logger = logging.getLogger(__name__)


class ScrapedPostResult:
  """Result of scraping an Instagram post."""

  def __init__(
    self,
    success: bool,
    images: Optional[list[Image]] = None,
    owner_username: Optional[str] = None,
    description: Optional[str] = None,
    taken_at: Optional[str] = None,
    error: Optional[str] = None,
  ):
    self.success = success
    self.images = images or []
    self.owner_username = owner_username
    self.description = description
    self.taken_at = taken_at
    self.error = error


class PlaywrightScraperService:
  """Service for scraping Instagram posts using Playwright."""

  def __init__(self):
    self.browser: Optional[Browser] = None
    self._playwright = None
    self._lock = asyncio.Lock()

  async def _init_browser(self) -> None:
    """Initialize the browser if not already initialized."""
    async with self._lock:
      if not self.browser:
        self._playwright = await async_playwright().start()
        self.browser = await self._playwright.chromium.launch(
          headless=True,
          args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--disable-gpu",
          ],
        )
        logger.info("Browser initialized")

  async def close_browser(self) -> None:
    """Close the browser and cleanup resources."""
    async with self._lock:
      if self.browser:
        await self.browser.close()
        self.browser = None
        logger.info("Browser closed")
      if self._playwright:
        await self._playwright.stop()
        self._playwright = None

  async def scrape_instagram_post(self, url: str, shortcode: str) -> ScrapedPostResult:
    """
    Scrape an Instagram post using Playwright.

    Args:
        url: The Instagram post URL
        shortcode: The post shortcode (used as post_id)

    Returns:
        ScrapedPostResult with images and metadata
    """
    page: Optional[Page] = None

    try:
      await self._init_browser()

      if not self.browser:
        raise Exception("Failed to initialize browser")

      # Create new page with a realistic user agent
      page = await self.browser.new_page(
        user_agent=(
          "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
          "AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/120.0.0.0 Safari/537.36"
        )
      )

      logger.info(f"Navigating to {url}")
      await page.goto(url, wait_until="networkidle", timeout=30000)

      # Wait a bit for page to fully load
      await page.wait_for_timeout(2000)

      # Close any modals/dialogs that might appear
      try:
        # Try to close "Log in" modal
        close_button = page.locator('svg[aria-label="Close"]').first
        if await close_button.is_visible(timeout=3000):
          await close_button.click()
          logger.info("Closed modal")
          await page.wait_for_timeout(1000)
      except Exception as e:
        logger.debug(f"No modal to close or modal close failed: {e}")

      # Extract images from the post
      images_data = await self._extract_images(page, shortcode)

      if not images_data:
        return ScrapedPostResult(
          success=False,
          error="No images found on the page",
        )

      # Extract metadata
      owner_username = await self._extract_username(page)
      description = await self._extract_description(page)
      taken_at = None  # Instagram doesn't expose exact timestamp easily

      logger.info(f"Successfully scraped {len(images_data)} images from {shortcode}")

      return ScrapedPostResult(
        success=True,
        images=images_data,
        owner_username=owner_username,
        description=description,
        taken_at=taken_at,
      )

    except Exception as error:
      logger.exception(f"Error scraping Instagram post {shortcode}: {error}")
      return ScrapedPostResult(
        success=False,
        error=str(error),
      )

    finally:
      if page:
        await page.close()

  async def _extract_images(self, page: Page, post_id: str) -> list[Image]:
    """
    Extract all images from the Instagram post page.

    Args:
        page: The Playwright page
        post_id: The post shortcode

    Returns:
        List of Image objects with storage_key, width, height
    """
    images = []

    try:
      # Wait for images to load
      await page.wait_for_selector("article img", timeout=10000)

      # Get all image elements within the article (post content)
      img_elements = await page.locator("article img").all()

      logger.info(f"Found {len(img_elements)} image elements")

      for idx, img_element in enumerate(img_elements):
        try:
          # Get image URL
          img_url = await img_element.get_attribute("src")

          if not img_url:
            logger.warning(f"Image {idx} has no src attribute")
            continue

          # Skip profile pictures and other small images
          # Instagram post images have specific characteristics
          if "profile" in img_url.lower() or "avatar" in img_url.lower():
            logger.debug(f"Skipping profile/avatar image: {img_url}")
            continue

          # Get natural dimensions
          width = await img_element.evaluate("el => el.naturalWidth")
          height = await img_element.evaluate("el => el.naturalHeight")

          # Skip very small images (likely not post content)
          if width < 100 or height < 100:
            logger.debug(f"Skipping small image {idx}: {width}x{height}")
            continue

          # Create Image object
          # storage_key is the Instagram CDN URL - same as current implementation
          image = Image(
            post_id=post_id,
            storage_key=img_url,
            width=int(width),
            height=int(height),
            is_primary=(idx == 0),
          )

          images.append(image)
          logger.info(f"Extracted image {idx}: {width}x{height} from {img_url[:100]}")

        except Exception as e:
          logger.warning(f"Failed to extract image {idx}: {e}")
          continue

    except Exception as e:
      logger.error(f"Error extracting images: {e}")

    return images

  async def _extract_username(self, page: Page) -> Optional[str]:
    """Extract the post owner's username."""
    try:
      # Try multiple selectors for username
      username_selectors = [
        'a[href*="/"][role="link"]',
        "header a",
        'a[href^="/"]',
      ]

      for selector in username_selectors:
        try:
          username_element = page.locator(selector).first
          if await username_element.is_visible(timeout=2000):
            href = await username_element.get_attribute("href")
            if href:
              # Extract username from href like "/username/"
              username = href.strip("/").split("/")[0]
              if username and not username.startswith("http"):
                logger.info(f"Extracted username: {username}")
                return username
        except Exception:
          continue

      logger.warning("Could not extract username")
      return None

    except Exception as e:
      logger.warning(f"Error extracting username: {e}")
      return None

  async def _extract_description(self, page: Page) -> Optional[str]:
    """Extract the post description/caption."""
    try:
      # Try to find the caption text
      caption_selectors = [
        "h1",  # Instagram often uses h1 for captions
        'article div[role="button"] span',
        "article span",
      ]

      for selector in caption_selectors:
        try:
          caption_elements = await page.locator(selector).all()
          for element in caption_elements:
            text = await element.text_content()
            if text and len(text.strip()) > 10:  # Reasonable caption length
              logger.info(f"Extracted description: {text[:100]}...")
              return text.strip()
        except Exception:
          continue

      logger.warning("Could not extract description")
      return None

    except Exception as e:
      logger.warning(f"Error extracting description: {e}")
      return None


# Global instance to reuse browser across multiple requests
_scraper_instance: Optional[PlaywrightScraperService] = None


async def get_scraper_instance() -> PlaywrightScraperService:
  """Get or create the global scraper instance."""
  global _scraper_instance
  if _scraper_instance is None:
    _scraper_instance = PlaywrightScraperService()
  return _scraper_instance


async def scrape_instagram_post_with_playwright(url: str, shortcode: str) -> dict:
  """
  Convenience function to scrape an Instagram post.
  Returns data in the same format as the instaloader implementation.

  Args:
      url: The Instagram post URL
      shortcode: The post shortcode

  Returns:
      dict with keys: owner_username, id, description, taken_at, images
  """
  scraper = await get_scraper_instance()
  result = await scraper.scrape_instagram_post(url, shortcode)

  if not result.success:
    raise ValueError(f"Failed to scrape post: {result.error}")

  return {
    "owner_username": result.owner_username or "unknown",
    "id": shortcode,
    "description": result.description or "",
    "taken_at": result.taken_at,
    "images": result.images,
  }
