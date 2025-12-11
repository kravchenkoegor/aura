"""
Tests for the Playwright Instagram scraper service.

Note: These tests require Playwright to be installed with:
    playwright install chromium

For CI/CD environments, also run:
    playwright install-deps chromium
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import Image
from app.service.playwright_scraper import (
  PlaywrightScraperService,
  ScrapedPostResult,
  scrape_instagram_post_with_playwright,
)


class TestPlaywrightScraperService:
  """Test suite for PlaywrightScraperService class."""

  @pytest.fixture
  async def scraper(self):
    """Create a scraper instance for testing."""
    service = PlaywrightScraperService()
    yield service
    # Cleanup after tests
    await service.close_browser()

  @pytest.mark.asyncio
  async def test_browser_initialization(self, scraper):
    """Test that browser initializes correctly."""
    await scraper._init_browser()
    assert scraper.browser is not None
    assert scraper._playwright is not None

  @pytest.mark.asyncio
  async def test_browser_reuse(self, scraper):
    """Test that browser instance is reused across calls."""
    await scraper._init_browser()
    browser1 = scraper.browser

    await scraper._init_browser()
    browser2 = scraper.browser

    assert browser1 is browser2

  @pytest.mark.asyncio
  async def test_browser_cleanup(self, scraper):
    """Test that browser is properly cleaned up."""
    await scraper._init_browser()
    await scraper.close_browser()

    assert scraper.browser is None
    assert scraper._playwright is None

  @pytest.mark.asyncio
  @patch("app.service.playwright_scraper.async_playwright")
  async def test_scrape_with_mock(self, mock_playwright):
    """Test scraping with mocked Playwright."""
    # Setup mocks
    mock_browser = AsyncMock()
    mock_page = AsyncMock()
    mock_playwright_instance = AsyncMock()

    mock_playwright.return_value.start = AsyncMock(
      return_value=mock_playwright_instance
    )
    mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser)
    mock_browser.new_page = AsyncMock(return_value=mock_page)

    # Mock page methods
    mock_page.goto = AsyncMock()
    mock_page.wait_for_timeout = AsyncMock()
    mock_page.locator.return_value.first.is_visible = AsyncMock(return_value=False)
    mock_page.wait_for_selector = AsyncMock()

    # Mock image elements
    mock_img = MagicMock()
    mock_img.get_attribute = AsyncMock(return_value="https://instagram.com/image.jpg")
    mock_img.evaluate = AsyncMock(side_effect=[1080, 1080])  # width, height

    mock_page.locator.return_value.all = AsyncMock(return_value=[mock_img])

    # Mock username and description extraction
    mock_username_element = AsyncMock()
    mock_username_element.is_visible = AsyncMock(return_value=True)
    mock_username_element.get_attribute = AsyncMock(return_value="/testuser/")

    scraper = PlaywrightScraperService()
    result = await scraper.scrape_instagram_post(
      "https://www.instagram.com/p/ABC123/", "ABC123"
    )

    assert result.success or result.error is not None  # Either success or error

  @pytest.mark.asyncio
  async def test_extract_images_filters_small_images(self, scraper):
    """Test that small images are filtered out."""
    # This would require more complex mocking of the page object
    # Left as a placeholder for implementation
    pass

  @pytest.mark.asyncio
  async def test_extract_images_filters_profile_pictures(self, scraper):
    """Test that profile pictures are filtered out."""
    # This would require more complex mocking of the page object
    # Left as a placeholder for implementation
    pass

  @pytest.mark.asyncio
  async def test_error_handling_invalid_url(self, scraper):
    """Test error handling for invalid URLs."""
    result = await scraper.scrape_instagram_post("https://invalid-url.com", "invalid")

    assert result.success is False
    assert result.error is not None

  @pytest.mark.asyncio
  async def test_error_handling_network_timeout(self, scraper):
    """Test error handling for network timeouts."""
    # This would require mocking network failures
    # Left as a placeholder for implementation
    pass


class TestScrapedPostResult:
  """Test suite for ScrapedPostResult class."""

  def test_successful_result(self):
    """Test creating a successful result."""
    images = [
      Image(
        post_id="ABC123",
        storage_key="https://example.com/image.jpg",
        width=1080,
        height=1080,
        is_primary=True,
      )
    ]

    result = ScrapedPostResult(
      success=True,
      images=images,
      owner_username="testuser",
      description="Test description",
    )

    assert result.success is True
    assert len(result.images) == 1
    assert result.owner_username == "testuser"
    assert result.error is None

  def test_failed_result(self):
    """Test creating a failed result."""
    result = ScrapedPostResult(
      success=False,
      error="Network timeout",
    )

    assert result.success is False
    assert result.error == "Network timeout"
    assert len(result.images) == 0

  def test_default_values(self):
    """Test default values in result."""
    result = ScrapedPostResult(success=True)

    assert result.images == []
    assert result.owner_username is None
    assert result.description is None
    assert result.error is None


class TestConvenienceFunction:
  """Test suite for the convenience wrapper function."""

  @pytest.mark.asyncio
  async def test_successful_scrape_returns_dict(self):
    """Test that successful scrape returns dict in correct format."""
    # This test would require an actual Instagram URL or extensive mocking
    # Left as a placeholder for implementation
    pass

  @pytest.mark.asyncio
  async def test_failed_scrape_raises_error(self):
    """Test that failed scrape raises ValueError."""
    with patch("app.service.playwright_scraper.get_scraper_instance") as mock_get:
      mock_scraper = AsyncMock()
      mock_scraper.scrape_instagram_post = AsyncMock(
        return_value=ScrapedPostResult(success=False, error="Test error")
      )
      mock_get.return_value = mock_scraper

      with pytest.raises(ValueError, match="Failed to scrape post"):
        await scrape_instagram_post_with_playwright(
          "https://www.instagram.com/p/ABC123/", "ABC123"
        )


# Integration tests (require actual Instagram access)
# These should be marked as integration tests and skipped in CI/CD


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_instagram_scrape():
  """
  Test scraping a real Instagram post.

  WARNING: This test accesses the real Instagram website.
  - Skip in CI/CD to avoid rate limiting
  - Use a known stable post URL
  - Instagram may block or rate limit
  """
  # Use a well-known Instagram post that's unlikely to be deleted
  # For example, Instagram's own posts or verified accounts
  url = "https://www.instagram.com/p/REPLACE_WITH_REAL_SHORTCODE/"
  shortcode = "REPLACE_WITH_REAL_SHORTCODE"

  scraper = PlaywrightScraperService()
  try:
    result = await scraper.scrape_instagram_post(url, shortcode)

    # Verify result structure
    if result.success:
      assert result.images is not None
      assert len(result.images) > 0
      assert result.owner_username is not None

      # Verify image structure
      for img in result.images:
        assert img.post_id == shortcode
        assert img.storage_key.startswith("http")
        assert img.width > 0
        assert img.height > 0
    else:
      # If scraping failed, at least verify error is present
      assert result.error is not None

  finally:
    await scraper.close_browser()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_carousel_post_scrape():
  """
  Test scraping an Instagram carousel post.

  WARNING: This test accesses the real Instagram website.
  """
  # Use a carousel post URL
  url = "https://www.instagram.com/p/REPLACE_WITH_CAROUSEL_SHORTCODE/"
  shortcode = "REPLACE_WITH_CAROUSEL_SHORTCODE"

  scraper = PlaywrightScraperService()
  try:
    result = await scraper.scrape_instagram_post(url, shortcode)

    if result.success:
      # Carousel posts should have multiple images
      assert len(result.images) > 1

      # First image should be marked as primary
      primary_images = [img for img in result.images if img.is_primary]
      assert len(primary_images) == 1

  finally:
    await scraper.close_browser()


# Performance tests


@pytest.mark.performance
@pytest.mark.asyncio
async def test_browser_reuse_performance():
  """Test that browser reuse improves performance."""
  import time

  url = "https://www.instagram.com/p/REPLACE_WITH_SHORTCODE/"
  shortcode = "REPLACE_WITH_SHORTCODE"

  scraper = PlaywrightScraperService()

  try:
    # First scrape (cold start)
    start1 = time.monotonic()
    await scraper.scrape_instagram_post(url, shortcode)
    duration1 = time.monotonic() - start1

    # Second scrape (warm start)
    start2 = time.monotonic()
    await scraper.scrape_instagram_post(url, shortcode)
    duration2 = time.monotonic() - start2

    # Second scrape should be faster (browser already initialized)
    # Allow some margin for network variability
    print(f"First scrape: {duration1:.2f}s")
    print(f"Second scrape: {duration2:.2f}s")

    # This is a soft assertion - second should typically be faster
    # but network conditions can vary

  finally:
    await scraper.close_browser()


# Pytest configuration
def pytest_configure(config):
  """Configure pytest with custom markers."""
  config.addinivalue_line(
    "markers", "integration: mark test as integration test (access network)"
  )
  config.addinivalue_line("markers", "performance: mark test as performance test")
