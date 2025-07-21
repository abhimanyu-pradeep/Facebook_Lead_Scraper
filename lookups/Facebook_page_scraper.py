from __future__ import annotations

import csv
import re
import random
import time
import os
from typing import Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium import webdriver
import colorlog
import logging

def setup_logger():
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        "%(log_color)s[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        }
    ))
    logger = colorlog.getLogger("facebook_scraper")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger

logger = setup_logger()

def get_random_proxy():
    proxy_list = [
        # Add actual proxy URLs or leave blank for direct connection:
        # "http://username:password@proxy1.example.com:8000",
        # "http://username:password@proxy2.example.com:8000"
    ]
    return random.choice(proxy_list) if proxy_list else None

class FacebookPageInfoScraper:
    def __init__(self, link, proxy: Optional[str] = None):
        self.link = link
        self.proxy = proxy
        self.driver = self._init_driver()

    def _init_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")

        if self.proxy:
            options.add_argument(f"--proxy-server={self.proxy}")

        logger.debug(f"Launching Chrome for: {self.link} | Proxy: {self.proxy or 'None'}")
        driver = webdriver.Chrome(options=options)
        return driver

    def scrape(self):
        try:
            self.driver.get(self.link)
            logger.info(f"Page loaded: {self.link}")

            self._wait_for_element(By.TAG_NAME, "body")

            self._close_login_popup()

            data = {
                "page_name": self._fetch_page_name(),
                "facebook_url": self.link,
                "phone_numbers": "",
                "emails": "",
                "websites": "",
                "followers": self._fetch_followers_count(),
            }

            contact_info = self._extract_intro_section_info()
            data.update(contact_info)

            logger.info(f"Scraped data: {data}")
            return data
        except Exception as e:
            logger.error(f"Error scraping {self.link}: {e}")
            return None
        finally:
            self.driver.quit()
            logger.debug("Browser session closed.\n")

    def _wait_for_element(self, by_method, identifier, timeout=10):
        WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by_method, identifier))
        )

    def _close_login_popup(self):
        try:
            logger.debug("Checking for login popup...")
            close_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@aria-label='Close']"))
            )
            close_btn.click()
            logger.info("Login popup closed.")
            time.sleep(1)
        except TimeoutException:
            logger.debug("No login popup detected.")

    def _fetch_page_name(self) -> str:
        try:
            title = self.driver.title
            return title.replace(" | Facebook", "").strip()
        except Exception:
            return ""

    def _fetch_followers_count(self) -> str:
        try:
            spans = self.driver.find_elements(By.TAG_NAME, 'span')
            for span in spans:
                if "followers" in span.text.lower():
                    return span.text.strip()
            return ""
        except Exception:
            return ""

    def _extract_intro_section_info(self):
        phones, emails, websites = set(), set(), set()

        try:
            elements = self.driver.find_elements(By.XPATH, "//span[contains(@class,'x193iq5w') and @dir='auto']")

            logger.debug(f"Found {len(elements)} intro section span elements.")

            for el in elements:
                try:
                    text = el.text.strip()

                    if re.fullmatch(r"[\d\s]{5,}", text):
                        phones.add(text)

                    if re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text):
                        emails.add(text)

                    if re.fullmatch(r"(?!.*facebook\.com)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text):
                        websites.add(text)

                except StaleElementReferenceException:
                    continue

        except Exception as e:
            logger.warning(f"Intro section scraping issue: {e}")

        return {
            "phone_numbers": ", ".join(phones),
            "emails": ", ".join(emails),
            "websites": ", ".join(websites)
        }

def process_csv_and_scrape(input_csv, output_csv):
    with open(input_csv, newline='', encoding='utf-8') as infile:
        reader = list(csv.DictReader(infile))

    fieldnames = ['page_name', 'facebook_url', 'phone_numbers', 'emails', 'websites', 'followers']

    with open(output_csv, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            url = row.get('Page Link', '').strip()
            if not url:
                continue

            logger.info(f"Scraping URL: {url}")

            proxy = get_random_proxy()

            scraper = FacebookPageInfoScraper(url, proxy)
            scraped_data = scraper.scrape()

            if scraped_data:
                writer.writerow(scraped_data)

if __name__ == "__main__":
    input_file = "scraped_updated_links_21_07.csv"
    output_file = "scraped_facebook_pages_2_21_07.csv"

    if not os.path.exists(input_file):
        logger.error(f"Input file '{input_file}' not found.")
    else:
        process_csv_and_scrape(input_file, output_file)
        logger.info("Scraping process completed.")
