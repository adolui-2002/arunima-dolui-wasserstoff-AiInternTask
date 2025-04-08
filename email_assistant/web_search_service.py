"""
Web search service for gathering information.
"""
import requests
from bs4 import BeautifulSoup

SEARCH_API_KEY="Your_api_key"
SEARCH_ENGINE_ID="Your_search_engine_id"
class WebSearchService:
    def __init__(self):
        self.api_key = SEARCH_API_KEY
        self.engine_id = SEARCH_ENGINE_ID
        self.base_url = "https://www.googleapis.com/customsearch/v1"

    def search(self, query, num_results):
        """Perform a web search using Google Custom Search API."""
        params = {
            'key': self.api_key,
            'cx': self.engine_id,
            'q': query,
            'num': num_results
        }

        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            results = response.json()

            if 'items' not in results:
                return []

            return [{
                'title': item['title'],
                'link': item['link'],
                'snippet': item['snippet']
            } for item in results['items']]

        except requests.RequestException as e:
            print(f"Error performing web search: {e}")
            return []

    def extract_content(self, url):
        """Extract main content from a webpage."""
        try:
            response = requests.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text content
            text = soup.get_text()

            # Break into lines and remove leading/trailing space
            lines = (line.strip() for line in text.splitlines())

            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))

            # Drop blank lines
            text = ' '.join(chunk for chunk in chunks if chunk)

            return text

        except requests.RequestException as e:
            print(f"Error extracting content: {e}")
            return None

    def search_and_summarize(self, questions) -> str:
        """Search for information and summarize the results."""
        max_results = 3  # Adjust as needed

        results = self.search(questions, num_results=max_results)

        if not results:
                return "No relevant information found."

        summary = f"Here's what I found about '{questions}':\n\n"
        txt = ""
        for i, result in enumerate(results, 1):
            summary += f"{i}. {result['title']}\n"
            summary += f"   {result['snippet']}\n\n"

                # Extract and summarize content if needed
            if len(result['snippet']) < 100:  # If snippet is too short
                content = self.extract_content(result['link'])
                if content:
                    summary += f"   Additional details: {content[:200]}...\n\n"
            txt += summary
            print(summary)
        return txt
