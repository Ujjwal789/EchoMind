# brain/planner.py
def plan_action(user_input: str):
    text = user_input.lower()

    if "chrome" in text:
        return {"agent": "windows", "app": "chrome"}

    if "notepad" in text:
        return {"agent": "windows", "app": "notepad"}

    if "youtube" in text:
        query = text.replace("play", "").replace("on youtube", "").strip()
        return {
            "agent": "browser",
            "action": "youtube",
            "query": query
        }

    return {"agent": "llm"}
