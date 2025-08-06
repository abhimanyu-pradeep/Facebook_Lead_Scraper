from openai import OpenAI
from tenacity import retry, wait_random_exponential, stop_after_attempt
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from readability import Document
import requests
import logging
load_dotenv()

client = OpenAI()  # Uses OPENAI_API_KEY from environment automatically

SYSTEM_PROMPT = """You are a lead classification assistant for B2B data enrichment.
Your task is to classify each company description into **one** of the following categories:

- Edutech
- Pharma and Healthcare
- Ecommerce
- IT and Tech
- Logistics
- Professional Services
- Other

Only return the category name. Do not explain."""

@retry(wait=wait_random_exponential(min=1, max=5), stop=stop_after_attempt(3))
def classify(desc):
    response = client.chat.completions.create(
        model="gpt-4-1106-preview",
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": desc},
        ]
    )
    return response.choices[0].message.content.strip()

SYSTEM_PROMPT_SUMMARIZE = """You are a lead enrichment assistant.
Given the following company website content, provide a concise 1-2 sentence summary of what the company does if the summary of the website is given. Focus on identifying their primary business activity and target audience. Avoid vague descriptions or generic statements. Be specific and to the point."""


SYSTEM_PROMPT_INSIGHT = """You are a B2B sales strategist helping sell WhatsApp automation and CRM solutions.
Given the following company summary if there exists one, suggest 1 specific and actionable insight about how WhatsApp automation could benefit this business. Focus on use cases such as customer support, lead generation, follow-ups, campaign automation, or booking workflows. Be relevant and practical.Keep the insights to maximum 3 sentences."""

@retry(wait=wait_random_exponential(min=1, max=5), stop=stop_after_attempt(3))
def summarize_website(content: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4-1106-preview",
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_SUMMARIZE},
            {"role": "user", "content": content},
        ]
    )
    return response.choices[0].message.content.strip()

@retry(wait=wait_random_exponential(min=1, max=5), stop=stop_after_attempt(3))
def generate_sales_insight(summary: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4-1106-preview",
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_INSIGHT},
            {"role": "user", "content": summary},
        ]
    )
    return response.choices[0].message.content.strip()

def fetch_website_text(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, timeout=10, headers=headers)
        doc = Document(res.text)
        html = doc.summary()
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n")
        return text.strip()[:5000]  # Cap to 5000 chars
    except Exception as e:
        logging.warning(f"Error fetching website: {e}")
        return ""

def enrich_lead(description: str, website_url: str = None):
    result = {
        "website_summary": "",
        "sales_insight": ""
    }

    if website_url:
        if not website_url.startswith("http"):
            website_url = "https://" + website_url
        content = fetch_website_text(website_url)
        if content:
            summary = summarize_website(content)
            result["website_summary"] = summary
            result["sales_insight"] = generate_sales_insight(summary)
    
    return result

if __name__ == "__main__":
    while True:
        description = input("Enter the desc :")
        print(f"class === {classify(description)}")
