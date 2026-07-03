import memory_store


class RememberTool:
    name = "remember"
    description = (
        "Save a fact about the user for future conversations "
        "(only when the user asks to remember something)"
    )
    side_effect = True
    parameter_spec = {
        "fact": {
            "type": "string",
            "description": "The fact to remember, e.g. 'The user's dog is named Biscuit'",
        }
    }

    def execute(self, fact: str = "") -> str:
        return memory_store.add(fact)
