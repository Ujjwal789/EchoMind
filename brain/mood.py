from datetime import datetime

def get_mood():
    hour = datetime.now().hour

    if 6 <= hour < 10:
        return "sleepy"
    elif 10 <= hour < 16:
        return "focused"
    elif 16 <= hour < 21:
        return "playful"
    else:
        return "tired"
