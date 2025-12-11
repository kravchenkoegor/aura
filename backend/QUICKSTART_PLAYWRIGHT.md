# Quick Start: Playwright Instagram Scraper

## Installation (Local Development)

```bash
# Install Python dependencies
cd /Users/egor/Documents/projects/aura/backend
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

## Installation (Docker)

```bash
# Build with Playwright support
docker-compose build

# Start services
docker-compose up -d
```

## Usage

The scraper is automatically used by the Instagram download worker. No code changes needed!

### Test the Implementation

1. Start the worker:
```bash
python -m app.workers.instagram_download_worker
```

2. Submit a task to Redis (or use your API endpoint)

3. Check logs for:
```
INFO: Browser initialized
INFO: Navigating to https://www.instagram.com/p/...
INFO: Found 3 image elements
INFO: Successfully scraped 1 images from [shortcode]
```

## Troubleshooting

### Browser Not Found
```bash
playwright install chromium
```

### Permission Issues
```bash
# Check Playwright cache directory
ls -la ~/.cache/ms-playwright

# Fix permissions if needed
chmod -R 755 ~/.cache/ms-playwright
```

### Import Error
```bash
# Verify Playwright is installed
pip show playwright

# Reinstall if needed
pip install --force-reinstall playwright==1.49.0
```

### Timeout Errors
Instagram may be rate-limiting. Wait a few minutes and try again.

## Architecture

```
Worker receives URL
    ↓
Extract shortcode
    ↓
Check if post exists in DB
    ↓
[NEW] Playwright scraper
    ├─ Launch browser (reused)
    ├─ Navigate to Instagram
    ├─ Close modals
    ├─ Extract images from DOM
    └─ Extract username & caption
    ↓
Save to database
    ↓
Publish status to Redis
```

## Performance

- First scrape: ~5-8 seconds (browser launch)
- Subsequent scrapes: ~2-4 seconds (reused browser)
- Memory: ~150-200MB per browser instance

## Files Changed

1. `app/service/playwright_scraper.py` - NEW scraper service
2. `app/workers/instagram_download_worker.py` - Updated import
3. `requirements.txt` - Added playwright==1.49.0
4. `Dockerfile` - Added Playwright installation

## Rollback

To revert to instaloader:

```python
# In instagram_download_worker.py, change line 33:
from app.service.instagram import download_instagram_post

# And line 155:
post_data = await asyncio.to_thread(download_instagram_post, shortcode=post_id)
```

## Support

- See `MIGRATION_PLAYWRIGHT.md` for detailed guide
- See `IMPLEMENTATION_SUMMARY.md` for complete technical details
- Check worker logs for debugging: `tail -f worker.log`
