import pandas as pd 
from playwright.sync_api import sync_playwright
from datetime import datetime as dt
import os
import streamlit as st

from profile_scraper import process_csv_and_scrape, setup_logger
from ad_scraper import run_scrape_page_links

from datetime import date
import time

st.set_page_config(page_title="Search App", layout="centered")

st.title("Search Interface")

# Inputs
search_keyword = st.text_input("Enter text query")
start_date = st.date_input("Start Date", date.today())
end_date = st.date_input("End Date", date.today())

# Placeholder for logs
log_placeholder = st.empty()

# Define custom scrollable log container
def render_logs(log_lines):
    log_html = "<br>".join(log_lines).replace(" ", "&nbsp;")
    styled_log_box = f"""
    <div style="
        background-color: #000;
        color: #0f0;
        padding: 10px;
        font-family: monospace;
        font-size: 14px;
        height: 300px;
        overflow-y: scroll;
        border-radius: 6px;
        border: 1px solid #333;
    ">
    {log_html}
    </div>
    """
    log_placeholder.markdown(styled_log_box, unsafe_allow_html=True)

if st.button("Start Search"):
    if not search_keyword:
        st.warning("Please enter a query.")
    else:
        print(start_date,end_date)
        # Simulate log streaming
        log_lines = []
        for i in range(10):
            log_line = f"[{i}] Searching '{search_keyword}' from {start_date} to {end_date}..."
            log_lines.append(log_line)
            render_logs(log_lines)
            time.sleep(0.8)

        log_lines.append("✅ Search completed.")
        render_logs(log_lines)


def run_session():
    now = dt.now()
    timestamp = now.strftime("%d-%m-%y | %H:%M")
    folder_name = f"session_{timestamp}"
    os.makedirs(folder_name, exist_ok=True)
    logger = setup_logger(f"{folder_name}/scraper.log")

    run_scrape_page_links(search_keyword=search_keyword, start_date_min=start_date,
                           start_date_max=end_date, data_directory= folder_name)
    
    process_csv_and_scrape(data_directory=folder_name,logger=logger)