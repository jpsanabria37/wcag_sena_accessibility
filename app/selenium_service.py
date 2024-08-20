from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from axe_selenium_python import Axe
from urllib.parse import urlparse
import os
import uuid


class SeleniumService:
    def __init__(self, driver_path):
        self.driver_path = driver_path
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')

    def analyze_url(self, url):
        service = Service(executable_path=self.driver_path)
        driver = webdriver.Chrome(service=service, options=self.chrome_options)

        try:
            driver.get(url)
            axe = Axe(driver)
            axe.inject()
            results = axe.run()

            domain = urlparse(url).netloc
            unique_id = str(uuid.uuid4())
            filename = f"{domain}_{unique_id}_accessibility_results.json"
            results_path = os.path.join('./results', filename)

            return results, domain, unique_id, results_path
        finally:
            driver.quit()
