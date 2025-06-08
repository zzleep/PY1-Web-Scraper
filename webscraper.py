import pandas as pd
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from random import uniform
import json

# Configuration
CONFIG = {
    "chromedriver_path": "path/to/chromedriver",  # Update with your chromedriver path
    "output_csv": "github_projects.csv",
    "cache_file": "scrape_cache.json",
    "max_workers": 6,  # Optimal for most systems
    "min_delay": 1.0,  # Minimum delay between requests (seconds)
    "max_delay": 3.0,  # Maximum delay to avoid rate limiting
    "headless": True,
    "proxies": [  # Rotate through these if needed
        # 'http://proxy1:port',
        # 'http://proxy2:port'
    ],
    # User agents to rotate through
    "user_agents": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
    ]
}

def setup_driver(proxy=None, user_agent=None):
    """Initialize Chrome WebDriver with advanced options"""
    options = webdriver.ChromeOptions()

    if CONFIG['headless']:
        options.add_argument("--headless")
    options.add_argument("--incognito")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")

    if proxy:
        options.add_argument(f'--proxy-server={proxy}')
    if user_agent:
        options.add_argument(f'--user-agent={user_agent}')

    # Additional performance optimizations
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")

    service = Service(executable_path=CONFIG['chromedriver_path'])
    driver = webdriver.Chrome(service=service, options=options)

    # Set timeouts
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(5)

    return driver

def load_cache():
    """Load previously scraped data from cache"""
    if os.path.exists(CONFIG['cache_file']):
        with open(CONFIG['cache_file'], 'r') as f:
            return json.load(f)
    return {"scraped_urls": {}, "projects": []}

def save_cache(cache):
    """Save scraped data to cache"""
    with open(CONFIG['cache_file'], 'w') as f:
        json.dump(cache, f)

def scrape_page(url, cache):
    """Scrape individual page with retry logic"""
    # Skip already scraped URLs
    if url in cache['scraped_urls']:
        return []

    # Random delay to avoid detection
    time.sleep(uniform(CONFIG['min_delay'], CONFIG['max_delay']))

    # Rotate proxies/user-agents if available
    proxy = CONFIG['proxies'][len(cache['scraped_urls']) % len(CONFIG['proxies'])] if CONFIG['proxies'] else None
    user_agent = CONFIG['user_agents'][len(cache['scraped_urls']) % len(CONFIG['user_agents'])]

    driver = setup_driver(proxy, user_agent)
    page_data = []

    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//h1[@class='h3 lh-condensed']"))
        )

        projects = driver.find_elements(By.XPATH, "//h1[@class='h3 lh-condensed']")

        for proj in projects:
            try:
                name = proj.text
                url = proj.find_element(By.XPATH, ".//a").get_attribute('href')

                # Only add new projects
                if url not in cache['scraped_urls']:
                    page_data.append({
                        'Project Name': name,
                        'URL': url,
                        'Timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                    cache['scraped_urls'][url] = True

            except Exception as e:
                print(f"Error processing project: {e}")

        return page_data

    except Exception as e:
        print(f"Error scraping {url}: {str(e)[:100]}...")
        return []
    finally:
        driver.quit()

def main():
    start_time = time.time()
    cache = load_cache()

    # Main URL and pagination discovery
    main_url = "https://github.com/collections/machine-learning"
    page_links = [main_url]

    # Discover additional pages (if any)
    discovery_driver = setup_driver()
    try:
        discovery_driver.get(main_url)
        pages = discovery_driver.find_elements(By.XPATH, "//a[contains(@class,'paginate')]")
        page_links += [p.get_attribute('href') for p in pages if p.get_attribute('href') not in cache['scraped_urls']]
    except Exception as e:
        print(f"Pagination discovery failed: {e}")
    finally:
        discovery_driver.quit()

    # Parallel scraping with progress tracking
    print(f"Scraping {len(page_links)} pages with {CONFIG['max_workers']} workers...")

    with ThreadPoolExecutor(max_workers=CONFIG['max_workers']) as executor:
        futures = {executor.submit(scrape_page, url, cache): url for url in page_links}

        for future in as_completed(futures):
            url = futures[future]
            try:
                new_projects = future.result()
                if new_projects:
                    cache['projects'].extend(new_projects)
                    # Save incremental progress
                    save_cache(cache)
            except Exception as e:
                print(f"Thread error for {url}: {e}")

    # Create DataFrame and save
    df = pd.DataFrame(cache['projects'])

    # Merge with existing data if file exists
    if os.path.exists(CONFIG['output_csv']):
        existing_df = pd.read_csv(CONFIG['output_csv'])
        df = pd.concat([existing_df, df]).drop_duplicates(subset=['URL'], keep='last')

    df.to_csv(CONFIG['output_csv'], index=False)

    print(f"\nScraping completed in {time.time()-start_time:.2f} seconds")
    print(f"Total projects: {len(df)}")
    print(f"New projects added: {len([p for p in cache['projects'] if p['URL'] not in cache['scraped_urls']])}")
    print(f"Data saved to {CONFIG['output_csv']}")

if __name__ == "__main__":
    main()