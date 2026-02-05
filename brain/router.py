# brain/router.py
from brain.local_llm import generate as local_generate
# from brain.cloud_llm import generate as cloud_generate  # optional

USE_LOCAL = True

def route(prompt, system_prompt=None):
    if USE_LOCAL:
        return local_generate(prompt, system_prompt)
    else:
        return cloud_generate(prompt, system_prompt)
