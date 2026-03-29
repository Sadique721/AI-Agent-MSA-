import requests
from bs4 import BeautifulSoup

class Internet:
    def __init__(self):
        self.is_online = self.check_connection()

    def check_connection(self):
        try:
            requests.get("http://1.1.1.1", timeout=2)
            return True
        except:
            return False

    def search_and_summarize(self, query):
        if not self.is_online:
            return "No internet connection."
        # Use a local search engine like Searx or simply fetch from a trusted site
        # For demo, we'll do a simple DuckDuckGo search (not offline)
        url = f"https://html.duckduckgo.com/html/?q={query}"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        results = soup.find_all('a', class_='result__a')
        summaries = [r.get_text() for r in results[:5]]
        return "\n".join(summaries)
