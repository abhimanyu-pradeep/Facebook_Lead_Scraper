from openai import OpenAI
from tenacity import retry, wait_random_exponential, stop_after_attempt
from dotenv import load_dotenv

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


if __name__ == "__main__":
    while True:
        description = input("Enter the desc :")
        print(f"class === {classify(description)}")
