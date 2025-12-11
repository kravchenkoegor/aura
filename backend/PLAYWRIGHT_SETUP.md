# Playwright Setup Instructions

This project uses Playwright for Instagram scraping. After installing the Python dependencies, you need to install the Playwright browser binaries.

## Installation Steps

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright browsers:
```bash
playwright install chromium
```

Or install all browsers:
```bash
playwright install
```

3. For production/Docker environments, you may need to install system dependencies:
```bash
playwright install-deps chromium
```

## Docker Setup

If running in Docker, add these commands to your Dockerfile after installing Python dependencies:

```dockerfile
RUN pip install -r requirements.txt
RUN playwright install chromium
RUN playwright install-deps chromium
```

## Troubleshooting

- If you encounter permission errors, make sure the user has write access to the Playwright cache directory
- For headless environments (CI/CD, Docker), ensure all system dependencies are installed with `playwright install-deps`
- The scraper uses Chromium by default for better compatibility and lighter footprint

## Browser Reuse

The implementation reuses a single browser instance across multiple scraping requests for better performance. The browser is automatically initialized on first use and can be manually closed if needed.
