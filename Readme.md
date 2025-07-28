# 🕸️ Facebook Lead Scraper (Dockerized)

This tool scrapes lead information from the Meta Ad Library using Playwright and displays a Streamlit-based UI for configuration and status monitoring.

---

## 🐳 Dockerized Setup

The app runs entirely in Docker, so no local dependency hell.

### ✅ Prerequisites

- Docker installed on your machine

---

## 🛠️ Build the Docker Image

Make sure you create the directories and the files said below:

- **data** - For storing the output files
- **archives** - For creating the .zip files for download

Run this from the root of your project:

```bash
#Build the image
docker build -t lead_generator .

#Run the container with the volumes mounted for retrieving the data
docker run -p 8501:8501 -v "$PWD/all_links.csv":/app/all_links.csv -v \
"$PWD/all_leads.xlsx":/app/all_leads.xlsx \
-v "$PWD/all_leads.csv":/app/all_leads.csv \
-v "$PWD/data":/app/data \
-v "$PWD/archive":/app/archive
streamlit_app
```

For Windows users:

```bash
#Build the image
docker build -t lead_generator .

#Run the container with the volumes mounted for retrieving the data
docker run -p 8501:8501 `
  -v "${PWD}/all_links.csv:/app/all_links.csv" `
  -v "${PWD}/all_leads.xlsx:/app/all_leads.xlsx" `
  -v "${PWD}/all_leads.csv:/app/all_leads.csv" `
  -v "${PWD}/data:/app/data" `
  -v "${PWD}/archive:/app/archive" `
  streamlit_app
