import requests
from bs4 import BeautifulSoup
import urllib.parse

class WebAgent:
    def __init__(self):
        self.headers = {"User-Agent": "Mozilla/5.0 (MSA AI Browser)"}

    def search(self, query: str):
        url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        try:
            response = requests.get(url, headers=self.headers, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                results = []
                for a in soup.find_all('a', class_='result__snippet', limit=3):
                    results.append(a.text)
                if results:
                    return "\n".join(results)
                return "No snippet results found."
            return "Failed to fetch response."
        except Exception as e:
            return f"Error connecting to internet: {str(e)}"

agent = WebAgent()
