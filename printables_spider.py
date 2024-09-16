import time
import random
from playwright.sync_api import sync_playwright, TimeoutError

class PrintablesSpider:
    BASE_DELAY = 3  # Base delay in seconds
    MAX_JITTER = 2  # Maximum jitter in seconds
    BACKOFF_FACTOR = 2  # Factor for exponential backoff
    MAX_RETRIES = 3  # Maximum number of retries
    THINK_TIME_CHANCE = 0.1  # 10% chance of a longer pause
    THINK_TIME_RANGE = (30, 120)  # Range for think time in seconds

    def __init__(self, model_id, user_agent):
        self.model_id = model_id
        self.url = f'https://www.printables.com/model/{model_id}'
        self.user_agent = user_agent
        self.data = {}
        self.consecutive_requests = 0

    def get_delay(self):
        delay = self.BASE_DELAY + (self.consecutive_requests * 0.5)
        jitter = random.uniform(0, self.MAX_JITTER)
        return delay + jitter

    def run(self):
        for attempt in range(self.MAX_RETRIES):
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=False)
                    context = browser.new_context(
                        user_agent=self.user_agent,
                        ignore_https_errors=True
                    )
                    page = context.new_page()

                    page.goto(self.url)
                    page.wait_for_load_state('networkidle')

                    # Check for the "top secret printer" message
                    secret_message = page.query_selector("p:has-text(\"We're sorry, but this page belongs to our top secret printer coming in the distant future.\")")
                    if secret_message:
                        #print(f"Skipping model {self.model_id} due to top secret printer message")
                        return None

                    # Wait for the specific h1 element to be visible
                    page.wait_for_selector('h1.model-name')

                    # Get the text content of the h1 element (model name)
                    self.data['model_name'] = page.inner_text('h1.model-name')

                    # Get the text content of the description
                    description_selector = 'div.user-inserted'
                    if page.is_visible(description_selector):
                        self.data['description'] = page.inner_text(description_selector)
                    else:
                        self.data['description'] = ""

                    # Get the download link URL
                    download_link = page.get_attribute('a.download-btn', 'href')
                    self.data['download_link'] = f'https://www.printables.com{download_link}'

                    # Get the URL of the first image
                    self.data['first_image_url'] = page.get_attribute('li.splide__slide.is-active img', 'src')

                    #print(f'Successfully extracted data for model {self.model_id}')
                    self.consecutive_requests += 1

                    # Chance of a longer "think time" pause
                    if random.random() < self.THINK_TIME_CHANCE:
                        think_time = random.uniform(*self.THINK_TIME_RANGE)
                        #print(f"Taking a longer pause of {think_time:.2f} seconds")
                        time.sleep(think_time)
                        self.consecutive_requests = 0  # Reset consecutive requests after think time
                    else:
                        delay = self.get_delay()
                        #print(f"Waiting for {delay:.2f} seconds before next request")
                        time.sleep(delay)

                    return self.data

            except TimeoutError:
                print(f'A timeout occurred while trying to navigate or find elements for model {self.model_id}')
            except Exception as e:
                print(f'An error occurred for model {self.model_id}: {str(e)}')

            if attempt < self.MAX_RETRIES - 1:
                backoff_time = (self.BACKOFF_FACTOR ** attempt) * self.BASE_DELAY
                print(f"Retrying in {backoff_time:.2f} seconds...")
                time.sleep(backoff_time)
            else:
                print(f"Failed to scrape model {self.model_id} after {self.MAX_RETRIES} attempts")

        self.consecutive_requests = 0  # Reset consecutive requests after all retries fail
        return None