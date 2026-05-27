from datetime import datetime


class TimeTool:
    name = "get_time"
    description = "Get the current date and time"
    parameter_spec = {}

    def execute(self) -> str:
        now = datetime.now()
        return now.strftime("%A, %B %d, %Y at %I:%M %p")
