# brain/state.py

class AssistantState:
    def __init__(self):
        self.active = True
        self.listening = True
        self.speaking = False

state = AssistantState()

