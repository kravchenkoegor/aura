# Migration Guide: Instaloader to Playwright

This document describes the migration from `instaloader` to `Playwright` for Instagram scraping.

## Changes Made

### 1. New Service: `app/service/playwright_scraper.py`

Created a new Playwright-based scraper service that:
- Uses async/await for better performance
- Handles Instagram's anti-bot measures with realistic browser behavior
- Extracts images directly from the DOM
- Manages browser lifecycle efficiently with a reusable browser instance
- Returns data in the same format as the old instaloader implementation

Key features:
- **Browser reuse**: Single browser instance shared across requests for better performance
- **Anti-bot measures**: Realistic user agent, proper timeouts, modal handling
- **Robust image extraction**: Multiple fallback selectors to handle Instagram's changing DOM
- **Resource cleanup**: Proper page closing after each scrape
- **Error handling**: Comprehensive error logging and graceful degradation

### 2. Updated Worker: `app/workers/instagram_download_worker.py`

Changed from:
```python
from app.service.instagram import download_instagram_post
post_data = await asyncio.to_thread(download_instagram_post, shortcode=post_id)
```

To:
```python
from app.service.playwright_scraper import scrape_instagram_post_with_playwright
post_data = await scrape_instagram_post_with_playwright(url=url, shortcode=post_id)
```

The worker's error handling and task update logic remains unchanged.

### 3. Dependencies: `requirements.txt`

Added:
```
playwright==1.49.0
```

### 4. Docker Configuration: `Dockerfile`

Added Playwright installation in the builder stage:
```dockerfile
RUN playwright install chromium
RUN playwright install-deps chromium
```

And system dependencies in the final stage with browser cache copying.

## Why Playwright?

### Advantages over Instaloader:
1. **More reliable**: Directly scrapes the webpage like a real browser
2. **Better anti-bot evasion**: Uses real browser rendering
3. **More control**: Can handle dynamic content, modals, and authentication flows
4. **Future-proof**: Easier to adapt to Instagram UI changes
5. **Native async**: Better integration with the async worker architecture

### Disadvantages:
1. **Heavier**: Requires browser binaries (~200MB for Chromium)
2. **Slower**: Browser startup overhead (mitigated by browser reuse)
3. **More dependencies**: System libraries required for browser execution

## Data Format Compatibility

The new implementation maintains 100% compatibility with the existing data format:

```python
{
    "owner_username": str,      # Username of post owner
    "id": str,                  # Post shortcode
    "description": str,         # Post caption
    "taken_at": Optional[datetime],  # Post timestamp (may be None)
    "images": list[Image],      # List of Image objects
}
```

Each `Image` object contains:
- `post_id`: The post shortcode
- `storage_key`: The Instagram CDN URL (direct image URL)
- `width`: Image width in pixels
- `height`: Image height in pixels
- `is_primary`: Boolean marking the first image in carousels

## Installation

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright browsers:
```bash
playwright install chromium
```

### Docker

The Dockerfile has been updated to automatically install Playwright and Chromium. Just rebuild:
```bash
docker-compose build
```

## Rollback Plan

If you need to rollback to instaloader:

1. Restore the import in `instagram_download_worker.py`:
```python
from app.service.instagram import download_instagram_post
post_data = await asyncio.to_thread(download_instagram_post, shortcode=post_id)
```

2. Remove playwright from `requirements.txt`

3. Revert the Dockerfile changes

The old `app/service/instagram.py` file is still present and functional.

## Testing

To test the new implementation:

1. Ensure Playwright browsers are installed
2. Run the worker: `python -m app.workers.instagram_download_worker`
3. Submit an Instagram post URL to the Redis stream
4. Check logs for successful scraping and image extraction

Example test URLs:
- Single image post: `https://www.instagram.com/p/[shortcode]/`
- Carousel post: `https://www.instagram.com/p/[shortcode]/` (multiple images)

## Performance Considerations

### Browser Lifecycle
- The browser instance is created on first use and reused for subsequent requests
- Each scrape operation opens a new page in the existing browser
- Pages are properly closed after each operation to prevent memory leaks

### Optimization Tips
1. The browser is launched in headless mode by default
2. GPU acceleration is disabled to reduce resource usage
3. Dev tools and unnecessary features are disabled
4. Consider adjusting timeouts based on your network conditions

### Memory Usage
- Chromium: ~100-200MB
- Each page: ~10-50MB (automatically cleaned up)
- Monitor memory usage in production and adjust concurrency accordingly

## Troubleshooting

### "Browser not found" Error
Run: `playwright install chromium`

### Permission Errors
Ensure the application has write access to the Playwright cache directory (usually `~/.cache/ms-playwright`)

### Timeout Errors
- Instagram may be rate-limiting or blocking
- Try increasing timeouts in the scraper service
- Consider adding delays between requests

### Empty Results
- Instagram's HTML structure may have changed
- Check browser logs by setting `headless=False` temporarily
- Update selectors in the `_extract_images()` method

## Future Enhancements

Potential improvements:
1. Add support for video posts
2. Implement cookie-based authentication for private accounts
3. Add retry logic with exponential backoff
4. Implement distributed browser instances for higher throughput
5. Cache scraped results to reduce redundant requests
6. Add metrics/monitoring for scraping success rates
