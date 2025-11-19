import requests
import json

from cryptography.hazmat.decrepit.ciphers.algorithms import SEED

TEMPERATURE = 1
TOP_K = 1
TOP_P = 0.01
SEED = 42


PORT = 8001
MODEL_NAME = "Mistral"
API_URL = f"http://localhost:{PORT}/chat"
NPS_TEXT = """
During the last quarter, our team introduced a customer feedback program targeting common pain points in our product. 
Quarterly surveys revealed a steady increase in satisfaction, culminating in an NPS of 49 by the end of the period. 
The executive team noted that these improvements would serve as a foundation for future innovation and competitive differentiation.
"""

master_prompt = f"""
You are an AI classifier.  
Your task: Given a piece of text referencing Net Promoter Score (NPS), classify the mention into one of these categories:  
1. “Score reporting” — when the text discloses the company’s NPS value.  
2. “Improvement initiatives” — when the text describes efforts or plans to raise or improve NPS.  
3. “Benchmarking / competition” — when the text compares the NPS to peers, industry averages, or competitive context.  
4. “General statements” — when the text highlights the strategic importance or general commentary about NPS but does not disclose a value, plan or comparison.

Instructions:  
- Read the text carefully.  
- Choose exactly one category label (from the four) that best fits.  
- Respond **only** with the category label (one of: Score reporting; Improvement initiatives; Benchmarking / competition; General statements).  
- Then, optionally (on a new line) provide a short explanation (1 sentence) of why you chose that label.

Here is the text:  
“{NPS_TEXT}”
"""

payload = {
    "message": master_prompt,
    "model": MODEL_NAME,
    "temperature": TEMPERATURE,
    "top_p": TOP_P,
    "top_k": TOP_K,
    "seed": SEED,
}

response = requests.post(API_URL, json=payload)

print(f"Status code: {response.status_code}")
print(f"Response: {response.text.replace('\\n', '\n')}")