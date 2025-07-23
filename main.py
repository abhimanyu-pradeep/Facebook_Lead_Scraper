import pandas as pd 
from playwright.sync_api import sync_playwright
from datetime import datetime as dt
import os
import streamlit as st
import threading
import zipfile

from profile_scraper import process_csv_and_scrape, setup_logger
from ad_scraper import run_scrape_page_links

from datetime import date
import time
import queue



def run_session():
    global folder_name
    now = dt.now()
    timestamp = now.strftime("%d-%m-%y | %H:%M")
    folder_name = f"data/session_{timestamp}"
    os.makedirs(folder_name, exist_ok=True)
    logger = setup_logger(f"{folder_name}/scraper.log")

    run_scrape_page_links(search_keyword=search_keyword, start_date_min=start_date,
                           start_date_max=end_date, data_directory= folder_name,logger = logger,log_list = log_lines)
    
    links_path = os.path.join(folder_name,"links.csv")

    total_links = len(pd.read_csv(links_path))

    process_csv_and_scrape(data_directory=folder_name,logger=logger,log_list=log_lines)


st.set_page_config(page_title="Meta Ads Library Search", layout="centered")

st.title("Search Through Facebook Pages")

with st.sidebar:
    # Inputs
    search_keyword = st.text_input("Enter text query")
    start_date = st.date_input("Start Date", date.today())
    end_date = st.date_input("End Date", date.today())
    start_button = st.button("Search")

    pie_placeholder = st.empty()
    pie_legend = st.empty()

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
        height: 80px;
        overflow-y: scroll;
        border-radius: 6px;
        border: 1px solid #333;
    ">
    {log_html}
    </div>
    """
    log_placeholder.markdown(styled_log_box, unsafe_allow_html=True)

if start_button:
    if not search_keyword:
        st.warning("Please enter a query.")
    else:
        log_lines = queue.Queue()
        threading.Thread(target=run_session,daemon=True).start()
        while True:
            logs_to_render = []
            try:
                logs_to_render.append(log_lines.get_nowait())
                render_logs(logs_to_render)
            except queue.Empty:
                pass
            if not threading.active_count() > 1:  # Only one background thread running
                render_logs(["Done ... ",])
                break
            time.sleep(0.6)
        
        csv_path = os.path.join(folder_name,"leads.csv")
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)

            st.subheader("Generated Leads Preview")
            st.dataframe(df.head(n = 10))

            if "grade" in df.columns:
                grade_counts = df["grade"].value_counts()
                pie_placeholder.pyplot(
                    grade_counts.plot.pie(autopct="%1.1f%%", figsize=(4, 4), title="Grade Distribution").figure
                )
                pie_legend.markdown(
                    "**Legend:**\n\n"
                    "- Grade A: Has Phone, Email, Website\n"
                    "- Grade B: Has Phone and one of Email, Website\n"
                    "- Grade C: Has Phone only\n"
                    "- Grade D: Has only Email and Website\n"
                    "- Grade E: Has either of Email or Website\n"
                ) 

        else:
            df = pd.read_csv(csv_path) 

            # ---- Zip & Download ----
            zip_path = os.path.join(f"{folder_name}", "session_output.zip")
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for file in os.listdir(f"{folder_name}"):
                    file_path = os.path.join(f"{folder_name}", file)
                    zipf.write(file_path, arcname=file)

            with open(zip_path, "rb") as f:
                st.download_button(
                    label="📦 Download Session ZIP",
                    data=f,
                    file_name="session_output.zip",
                    mime="application/zip"
                )      


