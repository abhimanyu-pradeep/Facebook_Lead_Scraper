from __future__ import annotations

import pandas as pd
import re
import random
import time
import os
import asyncio
from typing import Optional
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import colorlog
import logging


def setup_logger(log_file="scraper.log"):
    logger = colorlog.getLogger("facebook_scraper")
    logger.setLevel(logging.DEBUG)

    # Avoid adding multiple handlers if this gets called multiple times
    if not logger.hasHandlers():
        # Console Handler with Color
        console_handler = colorlog.StreamHandler()
        console_handler.setFormatter(colorlog.ColoredFormatter(
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

        # File Handler (no color)
        file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(
            "[%(asctime)s] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        ))

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger


def get_random_proxy():
    proxy_list = [
        # Add actual proxy URLs or leave blank for direct connection
    ]
    return random.choice(proxy_list) if proxy_list else None


class FacebookPageInfoScraper:
    def __init__(self, link: str, logger, log_list, proxy: Optional[str] = None):
        self.link = link
        self.proxy = proxy
        self.logger = logger
        self.log_list = log_list

    def scrape(self):
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=False, proxy={"server": self.proxy} if self.proxy else None)
            context = browser.new_context()
            page = context.new_page()

            try:
                self.logger.debug(f"Navigating to {self.link} with proxy {self.proxy or 'None'}")
                self.log_list.put(f"Navigating to {self.link} with proxy {self.proxy or 'None'}")
                page.goto(self.link, timeout=30000)
                page.wait_for_selector("body", timeout=10000)
                self._close_login_popup(page)

                title = (page.title()).replace(" | Facebook", "").strip()
                followers = self._fetch_followers_count(page)
                contact_info = self._extract_intro_section_info(page)

                data = {
                    "page_name": title,
                    "facebook_url": self.link,
                    "phone_numbers": contact_info.get("phones", ""),
                    "emails": contact_info.get("emails", ""),
                    "websites": contact_info.get("websites", ""),
                    "followers": followers
                }

                self.logger.info(f"Scraped data: {data}")
                self.log_list.put(f"Scraped data: {data}")
                return data

            except Exception as e:
                self.logger.error(f"Error scraping {self.link}: {e}")
                self.log_list.put(f"Error scraping {self.link}: {e}")
                return None
            finally:
                browser.close()

    def _close_login_popup(self, page):
        try:
            self.logger.debug("Checking for login popup...")
            self.log_list.put("Checking for login popup...")
            close_btn = page.wait_for_selector("div[aria-label='Close']", timeout=5000)
            close_btn.click()
            self.logger.info("Login popup closed.")
            self.log_list.put("Login popup closed.")
            page.wait_for_timeout(1000)
        except PlaywrightTimeoutError:
            self.logger.debug("No login popup detected.")
            self.log_list.put("No login popup detected.")

    def _fetch_followers_count(self, page) -> str:
        spans = page.query_selector_all("span")
        for span in spans:
            text = (span.inner_text()).lower()
            if "followers" in text:
                return text.strip()
        return ""

    def _extract_intro_section_info(self, page):
        phones, emails, websites = set(), set(), set()
        try:
            elements = page.query_selector_all("span.x193iq5w[dir='auto']")
            self.logger.debug(f"Found {len(elements)} intro section span elements.")
            self.log_list.put(f"Found {len(elements)} intro section span elements.")

            for el in elements:
                text = (el.inner_text()).strip()

                if re.fullmatch(r"[\d\s]{7,}", text):
                    phones.add(text)

                if re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text):
                    emails.add(text)

                if re.fullmatch(r"(?!.*facebook\.com)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text):
                    websites.add(text)

        except Exception as e:
            self.logger.warning(f"Intro section scraping issue: {e}")
            self.log_list.put(f"Intro section scraping issue: {e}")

        return {
            "phones": ", ".join(phones),
            "emails": ", ".join(emails),
            "websites": ", ".join(websites)
        }


# async def process_csv_and_scrape(input_csv, output_csv):
#     with open(input_csv, newline='', encoding='utf-8') as infile:
#         reader = list(csv.DictReader(infile))

#     fieldnames = ['page_name', 'facebook_url', 'phone_numbers', 'emails', 'websites', 'followers']

#     with open(output_csv, 'w', newline='', encoding='utf-8') as outfile:
#         writer = csv.DictWriter(outfile, fieldnames=fieldnames)
#         writer.writeheader()

#         for row in reader:
#             url = row.get('Page Link', '').strip()
#             if not url:
#                 continue

#             logger.info(f"Scraping URL: {url}")
#             proxy = get_random_proxy()

#             scraper = FacebookPageInfoScraper(url, proxy)
#             scraped_data = await scraper.scrape()

#             if scraped_data:
#                 writer.writerow(scraped_data)

def process_csv_and_scrape(data_directory:str,logger,log_list):
    # Read input CSV with pandas
    df_input = pd.read_csv(f"{data_directory}/links.csv")

    # Define output structure
    output_data = []

    for _, row in df_input.iterrows():
        url = str(row.get('Page Link', '')).strip()
        if not url:
            continue

        logger.info(f"Scraping URL: {url}")
        log_list.put(f"Scraping URL: {url}")
        proxy = get_random_proxy()

        scraper = FacebookPageInfoScraper(link=url, proxy = proxy,logger=logger,log_list=log_list)
        scraped_data = scraper.scrape()

        if scraped_data:
            output_data.append(scraped_data)

    # Create DataFrame from scraped output
    df_output = pd.DataFrame(output_data, columns=[
        'page_name', 'facebook_url', 'phone_numbers',
        'emails', 'websites', 'followers'
    ])

    # Write to output CSV
    df_output.to_csv(f"{data_directory}/leads.csv", index=False, encoding='utf-8')
    df_output.to_excel(f"{data_directory}/leads.xlsx", index=False)

    logger.info(f"Done .... Scraped {len(df_output)} leads.")
    log_list.put(f"Done .... Scraped {len(df_output)} leads.")


if __name__ == "__main__":
    input_file = "scraped_updated_links_21_07.csv"
    output_file = "scraped_facebook_pages_2_21_07.csv"

    logger=setup_logger()
    if not os.path.exists(input_file):
        logger.error(f"Input file '{input_file}' not found.")
    else:
        asyncio.run(process_csv_and_scrape(input_file, output_file))
        logger.info("Scraping process completed.")
