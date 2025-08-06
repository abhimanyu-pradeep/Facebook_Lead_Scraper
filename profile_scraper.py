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

from classifier_llm import classify
from classifier_llm import enrich_lead

ALL_LEADS_CSV = "all_leads.csv"
ALL_LEADS_XLSX = "all_leads.xlsx"

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
            browser = p.firefox.launch(headless=True, proxy={"server": self.proxy} if self.proxy else None)
            context = browser.new_context()
            page = context.new_page()

            try:
                self.logger.debug(f"Navigating to {self.link} with proxy {self.proxy or 'None'}")
                self.log_list.put(f"Navigating to {self.link} with proxy {self.proxy or 'None'}")
                page.goto(self.link, timeout=30000)
                page.wait_for_selector("body", timeout=10000)
                self._close_login_popup(page)

                intro_info = self._extract_intro_section_info(page)

                title = (page.title()).replace(" | Facebook", "").strip()
                followers = self._fetch_followers_count(page)
                website = intro_info["websites"]
                email = intro_info["emails"]
                phone_number =intro_info["phone_numbers"]
                address=intro_info["address"]
                intro_desc=intro_info["intro_description"]
                whatsapp_numbers=intro_info["whatsapp_numbers"]

                category = classify(intro_desc if intro_desc else title)
                if intro_desc:
                    enrichment=enrich_lead(intro_desc,website)
                    website_summary=enrichment["website_summary"]
                    sales_insight=enrichment["sales_insight"]
                else:
                    website_summary=""
                    sales_insight=""

                if phone_number and email and website and whatsapp_numbers:
                    grade = "A"
                elif (phone_number or whatsapp_numbers) and (email or website):
                    grade = "B"
                elif phone_number or whatsapp_numbers:
                    grade = "C"
                elif email and website:
                    grade = "D"
                elif email or website:
                    grade = "E"
                else:
                    grade = "F"
                
                data = {
                    "Business_Name": title,
                    "category":category,
                    "facebook_url": self.link,
                    "phone_numbers": phone_number,
                    "whatsapp_numbers":whatsapp_numbers,
                    "emails": email,
                    "websites": website,
                    "address":address,
                    "intro_desc":intro_desc,
                    "followers": followers,
                    "grade":grade,
                    "website_summary":website_summary,
                    "sales_insight":sales_insight
                }

                self.logger.info(f"Scraped data: {data}")
                self.log_list.put(f"Scraped data: {data}")
                
                return data if grade != "F" else None

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

    def _extract_intro_section_info(self,page):
        #phones, emails, websites = set(), set(), set()
        icons_map = {
            "phone": "Dc7-7AgwkwS.png",
            "whatsapp": "lnfZfe30sq0.png",
            "email": "2PIcyqpptfD.png",
            "website": "BQdeC67wT9z.png",
            "address": "8k_Y-oVxbuU.png"
        }
        info = {"phone_numbers": "", 
                "whatsapp_numbers": "",
                "emails": "",
                "websites": "", 
                "grade": "",
                "address": "", 
                "intro_description": ""}
        try:
            elements = page.query_selector_all("div[class*='x1ja2u2z']")
            self.logger.debug(f"Found {len(elements)} intro section span elements.")
            self.log_list.put(f"Found {len(elements)} intro section span elements.")

            for i, el in enumerate(elements):
                try:
                    img_tag = el.query_selector("img")
                    if not img_tag:
                        continue
                    src = img_tag.get_attribute("src")
                    next_div = elements[i + 1]

                    if icons_map["phone"] in src:
                        info["phone_numbers"] = next_div.inner_text().strip()

                    elif icons_map["whatsapp"] in src:
                        info["whatsapp_numbers"] = next_div.inner_text().strip()

                    elif icons_map["email"] in src:
                        info["emails"] = next_div.inner_text().strip()

                    elif icons_map["website"] in src:
                        try:
                            a = next_div.query_selector("a")
                            if a:
                                info["websites"] = a.inner_text().strip()
                            else:
                                info["websites"] = next_div.inner_text().strip()
                        except:
                            info["websites"] = next_div.inner_text().strip()

                    elif icons_map["address"] in src:
                        info["address"] = next_div.inner_text().strip()

                except Exception:
                    continue

            try:
                intro_desc_elem = page.query_selector("div[class*='x2b8uid'] span")
                if intro_desc_elem:
                    info["intro_description"] = intro_desc_elem.inner_text().strip()
            except Exception as e:
                self.logger.warning(f"Intro description fallback failed: {e}")
        except Exception as e:
            self.logger.warning(f"Intro section scraping issue: {e}")
            self.log_list.put(f"Intro section scraping issue: {e}")
        return info
    
def process_csv_and_scrape(data_directory:str,logger,log_list):
    # Read input CSV with pandas
    try:
        df_input = pd.read_csv(f"{data_directory}/links.csv")
    except pd.errors.EmptyDataError:
        logger.info(f"There are no new links scraped so ending session.")
        log_list.put(f"There are no new links scraped so ending session.")
        exit()

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

    if len(output_data)!=0:

    # Create DataFrame from scraped output
        df_output = pd.DataFrame(output_data)

        df_output_final=pd.DataFrame(output_data)
        df_output.sort_values(by="grade", inplace=True)

        filtered_columns = ['Business_Name', 'category', 'phone_numbers','whatsapp_numbers', 'emails', 'websites','address', 'grade',"website_summary","sales_insight"]
        available_columns = [col for col in filtered_columns if col in df_output_final.columns]
        df_filtered=df_output_final[available_columns]
        # Write to output CSV
        df_filtered.to_csv(f"{data_directory}/leads_final.csv", index=False, encoding='utf-8')
        df_output.to_csv(f"{data_directory}/leads.csv", index=False, encoding='utf-8')
        df_output.to_excel(f"{data_directory}/leads.xlsx", index=False)
        df_filtered.to_excel(f"{data_directory}/leads_final.xlsx", index=False)

        if os.path.exists(ALL_LEADS_CSV):
            try:
                all_leads = pd.read_csv(ALL_LEADS_CSV)
                combined_df = pd.concat([all_leads, df_output]).drop_duplicates(subset=["facebook_url"])
            except:
                combined_df = df_output
        combined_df.to_csv(ALL_LEADS_CSV, index=False)
        combined_df.to_excel(ALL_LEADS_XLSX, index=False)

        logger.info(f"Done .... Scraped {len(df_output)} leads.")
        log_list.put(f"Done .... Scraped {len(df_output)} leads.")
    else:
        logger.info(f"No Quality Leads found:( ")
        log_list.put(f"No Quality Leads found:( ")