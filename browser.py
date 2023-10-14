from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import asyncio
from bs4 import BeautifulSoup
import os
import time
import logging

# Initialize logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class Browser:
    def __init__(self, user_agent=None):
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run Chrome in headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        #ublock_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uBlock')
        #chrome_options.add_argument(f"--load-extension={ublock_path}")
        if user_agent:
            chrome_options.add_argument(f"user-agent={user_agent}")
        self.driver = webdriver.Chrome(options=chrome_options)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def get_dynamic_soup(self, base_url, wait_time=4, scroll=True):
        try:
            self.driver.get(base_url)
            
            # Wait for a fixed amount of time
            time.sleep(wait_time)
            
            # Scroll down to load dynamic content (optional)
            if scroll:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            dynamic_content = self.driver.page_source
            dynamic_soup = BeautifulSoup(dynamic_content, 'html.parser')
            return dynamic_soup
        except WebDriverException as e:
            logger.error(f"Failed to fetch dynamic content: {e}")
            return None
    
    def get_video_src(self, base_url, wait_time=4):
        try:
            self.driver.get(base_url)
            
            # Wait for a fixed amount of time
            time.sleep(wait_time)
            
            video_element = driver.find_element_by_tag_name('video')
            media = video_element.get_attribute('src')

            return media
        except WebDriverException as e:
            logger.error(f"Failed to fetch dynamic content: {e}")
            return None

    async def extract_video_file_link(self, url):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._extract_video_file_link, url)

    def _extract_video_file_link(self, url):
        try:
            logger.debug(f"Processing URL: {url}")

            # Navigate to the URL using Selenium
            self.driver.get(url)
            wait = WebDriverWait(self.driver, 10)

            # Wait for the video element to load
            video_elements = wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, 'video')))

            # Filter out video elements based on conditions (if needed)
            for video_element in video_elements:
                src = video_element.get_attribute('src')
                if src and src.lower().endswith(('.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv')):
                    logger.debug(f"Video URL found in HTML: {src}")
                    return src

            logger.debug(f"No video URL found for: {url}")
            return None

        except Exception as e:
            logger.error(f"An error occurred while processing {url}: {e}")
            return None

    async def get_video_url_array(self, arr):
        tasks = [self.extract_video_file_link(url) for url in arr]
        return [url for url in await asyncio.gather(*tasks) if url]

    def close(self):
        self.driver.close()  # Close the current window.
        self.driver.quit()  # Quit the driver and close every associated window.

# Usage example
if __name__ == "__main__":
    with Browser() as browser:
        video_urls = browser.get_video_url_array(["https://example.com/video1", "https://example.com/video2"])
        print(video_urls)
