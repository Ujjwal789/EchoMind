from ollama import chat


class LocalLLM:
    def __init__(self, model_name="phi3"):
        self.model_name = model_name

    def generate(self, prompt: str) -> str:
        """
        Blocking full response (safe, stable)
        """
        response = ""

        for chunk in chat(
            model=self.model_name,
            messages=[
                {"role": "user", "content": prompt}
            ],
            stream=True,
            options={
                "num_thread": 8,
                "num_ctx": 2048,
            }
        ):
            token = chunk["message"]["content"]
            response += token

        return response