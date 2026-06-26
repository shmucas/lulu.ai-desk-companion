class WebSearchTool:
    name = "web_search"
    description = "Search the web for current news, facts, or events"
    parameter_spec = {"query": {"type": "string", "description": "Search query"}}

    def execute(self, query: str = "") -> str:
        try:
            from duckduckgo_search import DDGS
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=3):
                    results.append(f"- {r.get('title', '')}: {r.get('body', '')}")
            return "\n".join(results) if results else "No results found."
        except Exception as e:
            return f"Search failed: {e}"
