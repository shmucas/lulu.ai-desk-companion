"""
Persistent memory - a small JSON file of facts about the user.

Facts are injected into both LLM system prompts each turn and survive
backend restarts. Capped so the tiny models never drown in context.
"""
import json
import os
import threading

_PATH = os.path.join(os.path.dirname(__file__), "lulu_memory.json")
_MAX_FACTS = 50
_lock = threading.Lock()


def facts() -> list[str]:
    try:
        with open(_PATH) as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def add(fact: str) -> str:
    fact = " ".join(fact.split()).strip()
    if not fact:
        return "Nothing to remember."
    with _lock:
        current = facts()
        if any(f.lower() == fact.lower() for f in current):
            return f"Already remembered: {fact}"
        current.append(fact)
        current = current[-_MAX_FACTS:]
        tmp = _PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(current, f, indent=2)
        os.replace(tmp, _PATH)
    return f"Remembered: {fact}"
