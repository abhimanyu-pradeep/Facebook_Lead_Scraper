# scraper.py

import pandas as pd
import os
from playwright.sync_api import sync_playwright

# === Configuration ===
COUNTRY_CODE = "IN"
SCRAPED_PAGES_CSV = "all_links.csv"
SCROLL_DELAY_MS = 3000

# === Phase 1: Scrape Page Links with Continuous Scrolling ===
def scrape_meta_ads_page_links(search_keyword, country, start_date_min=None, start_date_max=None, existing_links=None):
    if existing_links is None:
        existing_links = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        search_query = search_keyword.replace(" ", "%20")
        search_url = f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country={country}&q={search_query}"

        if start_date_min:
            search_url += f"&start_date[min]={start_date_min}"
        if start_date_max:
            search_url += f"&start_date[max]={start_date_max}"

        page.goto(search_url)

        print("Waiting for page to load...")
        page.wait_for_timeout(5000)

        advertiser_links = set()
        advertiser_data = []
        count = 0
        skipped = 0

        previous_height = 0
        scroll_round = 0
        while True:
            scroll_round += 1
            print(f"[Scroll {scroll_round}] Collecting page links...")
            link_elements = page.locator("a[href^='https://www.facebook.com/']").all()
            for link_element in link_elements:
                href = link_element.get_attribute("href")
                classes = link_element.get_attribute("class")
                name = link_element.inner_text().strip()
                if href and classes and "xt0psk2" in classes:
                    clean_href = href.split("?")[0]
                    if clean_href not in advertiser_links and clean_href not in existing_links:
                        advertiser_links.add(clean_href)
                        advertiser_data.append({"Page Name": name, "Page Link": clean_href})
                        count += 1
                        print(f"[{count}] New link: {clean_href} | Name: {name}")
                    elif clean_href in existing_links:
                        skipped += 1
            page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            page.wait_for_timeout(SCROLL_DELAY_MS)
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == previous_height:
                print("Reached end of page.")
                break
            previous_height = new_height

        print(f"Skipped {skipped} already-known links.")
        browser.close()
        return advertiser_data

# === Wrapper Function ===
def run_scrape_page_links(search_keyword, data_directory, start_date_min=None, start_date_max=None):
    print("Starting Phase 1: Scrape Facebook Page Links...")

    # Load existing links
    if os.path.exists(SCRAPED_PAGES_CSV):
        existing_df = pd.read_csv(SCRAPED_PAGES_CSV)
        existing_links = set(existing_df["Page Link"].dropna().unique())
        print(f"Loaded {len(existing_links)} existing links from {SCRAPED_PAGES_CSV}.")
    else:
        existing_df = pd.DataFrame()
        existing_links = set()
        print("No existing CSV found — starting fresh.")

    # Run scraper
    links_data = scrape_meta_ads_page_links(
        search_keyword,
        COUNTRY_CODE,
        start_date_min,
        start_date_max,
        existing_links
    )
    print(f"Scraped {len(links_data)} new unique page links.")

    if links_data:
        new_df = pd.DataFrame(links_data)

        # Save new links to file
        new_links_csv = f"{data_directory}/links.csv"
        new_links_xlsx = f"{data_directory}/links.xlsx"
        new_df.to_csv(new_links_csv, index=False)
        new_df.to_excel(new_links_xlsx, index=False)
        print(f"New links saved to {new_links_xlsx}.")

        # Update master file
        if not existing_df.empty:
            combined_df = pd.concat([existing_df, new_df]).drop_duplicates(subset=["Page Link"])
        else:
            combined_df = new_df
        combined_df.to_csv(SCRAPED_PAGES_CSV, index=False)
        print(f"Updated {SCRAPED_PAGES_CSV} with new links.")
    else:
        print("No new links to add.")

# === Prompt Entry Point ===
if __name__ == "__main__":
    search_keyword = input("Enter search keyword (e.g. 'Whatsapp Kerala'): ").strip()
    start_date_min = input("Enter start date min (YYYY-MM-DD) [press Enter to skip]: ").strip() or None
    start_date_max = input("Enter start date max (YYYY-MM-DD) [press Enter to skip]: ").strip() or None

    run_scrape_page_links(search_keyword, start_date_min, start_date_max, data_directory= "test_data")