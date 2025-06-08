# GitHub Project Web Scraper

This project provides a Python-based web scraper designed to collect information about GitHub projects. The scraper is highly configurable, supports headless browsing, proxy rotation, user-agent spoofing, and includes caching to avoid redundant requests. It is optimized for performance and can be run in parallel using multiple workers.

## Features
- Scrapes GitHub project data efficiently
- Headless Chrome browser automation
- Proxy and user-agent rotation for anonymity
- Configurable delays to avoid rate limiting
- Caching to prevent duplicate scraping
- Outputs results to CSV

## Prerequisites
- **Python 3.7+**
- **Google Chrome** (latest version recommended)
- **ChromeDriver** (matching your Chrome version)

## Requirements
Install the following Python packages:

```
pip install selenium
```

If you plan to use proxies, ensure you have access to working HTTP proxies.

## Setup
1. **Clone this repository** or copy the `webscraper.py` file to your project directory.
2. **Download ChromeDriver** from [here](https://sites.google.com/chromium.org/driver/) and place it on your system. Update the `chromedriver_path` in the `CONFIG` dictionary in `webscraper.py` to the correct path.
3. (Optional) Add your proxy addresses and user agents to the `CONFIG` dictionary as needed.

## Usage
Run the scraper with:

```
python webscraper.py
```

The results will be saved to `github_projects.csv` and the cache will be stored in `scrape_cache.json`.

## Configuration
Edit the `CONFIG` dictionary at the top of `webscraper.py` to:
- Set the path to your ChromeDriver
- Adjust output file names
- Set the number of parallel workers
- Configure delays, proxies, and user agents

## Notes
- Make sure your ChromeDriver version matches your installed Chrome browser version.
- Respect GitHub's robots.txt and terms of service when scraping.
- Excessive scraping may result in your IP being rate-limited or blocked.

## License
This project is for educational purposes only. Use responsibly.

