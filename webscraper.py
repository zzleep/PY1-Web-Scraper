# Import required libraries
import pandas as pd  # For data manipulation and CSV operations
import os  # For file and path operations
from selenium import webdriver  # For browser automation
from selenium.webdriver.common.by import By  # For locating elements
from selenium.webdriver.chrome.service import Service  # For ChromeDriver service
from selenium.webdriver.support.ui import WebDriverWait  # For explicit waits
from selenium.webdriver.support import expected_conditions as EC  # For wait conditions
from concurrent.futures import ThreadPoolExecutor, as_completed  # For parallel execution
import time  # For delays and timing
from random import uniform  # For randomizing delays
import json  # For caching and data storage

# Configuration dictionary for scraper settings
CONFIG = {
    "chromedriver_path": "path/to/chromedriver",  # Path to your ChromeDriver executable
    "output_csv": "github_projects.csv",  # Output CSV file for scraped data
    "cache_file": "scrape_cache.json",  # Cache file to store progress and avoid duplicates
    "max_workers": 6,  # Number of parallel threads for scraping
    "min_delay": 1.0,  # Minimum delay (in seconds) between requests to avoid detection
    "max_delay": 3.0,  # Maximum delay (in seconds) to randomize request intervals
    "headless": True,  # Run Chrome in headless mode (no GUI)
    "proxies": [  # List of proxies to rotate for anonymity (add your proxies if needed)
        # 'http://proxy1:port',
        # 'http://proxy2:port'
    ],
    # List of user agents to rotate for each request
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
                new_projects = future.result()  # Get the result from the completed thread (list of new projects)
                if new_projects:
                    cache['projects'].extend(new_projects)  # Add new projects to the cache
                    # Save incremental progress to cache file after each batch
                    save_cache(cache)
            except Exception as e:
                print(f"Thread error for {url}: {e}")  # Log any thread-specific errors

    # Create a DataFrame from all collected projects for easy data manipulation and export
    df = pd.DataFrame(cache['projects'])

    # If the output CSV already exists, merge new data with existing data and remove duplicates
    if os.path.exists(CONFIG['output_csv']):
        existing_df = pd.read_csv(CONFIG['output_csv'])  # Load existing data
        df = pd.concat([existing_df, df]).drop_duplicates(subset=['URL'], keep='last')  # Merge and deduplicate

    df.to_csv(CONFIG['output_csv'], index=False)  # Save the final DataFrame to CSV

    # Print summary statistics for the scraping session
    print(f"\nScraping completed in {time.time()-start_time:.2f} seconds")
    print(f"Total projects: {len(df)}")
    print(f"New projects added: {len([p for p in cache['projects'] if p['URL'] not in cache['scraped_urls']])}")
    print(f"Data saved to {CONFIG['output_csv']}")

# Entry point for the script; ensures main() only runs when script is executed directly
if __name__ == "__main__":
    main()