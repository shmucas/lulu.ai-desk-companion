import httpx


class JokeTool:
    name = "tell_joke"
    description = "Get a random clean joke"
    parameter_spec = {}

    def execute(self) -> str:
        try:
            resp = httpx.get(
                "https://icanhazdadjoke.com/",
                headers={"Accept": "application/json"},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json().get("joke", "I couldn't think of a joke.")
        except Exception as e:
            return f"Could not fetch a joke: {e}"
