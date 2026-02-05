# main.py
import time
from datetime import datetime

from brain.local_llm import LocalLLM
from brain.prompts import JARVIS_SYSTEM_PROMPT
from brain.memory import load_memory, update_memory, save_memory
from brain.mood import get_mood
from brain.planner import plan_action

from voice.stt import listen_and_transcribe
from voice.tts import speak, is_speaking, get_last_speech_end_time, wait_until_finished

from agents import browser_agent, windows_agent

def main():
    # ---- INIT ----
    llm = LocalLLM(model_name="phi3")
    system_prompt = JARVIS_SYSTEM_PROMPT.strip()
    memory = load_memory()
    
    print("🟢 Echo is alive. Say 'exit' to quit.\n")
    print("Voice: Edge TTS (en-US-AriaNeural)\n")
    
    while True:
        try:
            # ---- WAIT FOR TTS TO FINISH ----
            wait_until_finished()
            
            # Wait additional time after speech
            last_end = get_last_speech_end_time()
            current_time = time.time()
            
            if last_end > 0:
                time_since_speech = current_time - last_end
                if time_since_speech < 0.8:  # Wait at least 0.8 seconds after speech
                    wait_time = 0.8 - time_since_speech
                    time.sleep(wait_time)
            
            # ---- LISTEN ----
            print("\n" + "="*50)
            print("🎤 READY - SPEAK NOW")
            print("="*50)
            
            user_input = listen_and_transcribe()
            
            if not user_input:
                time.sleep(0.3)
                continue
            
            user_input = user_input.strip()
            print(f"\n👤 You: {user_input}")
            
            # ---- EXIT ----
            if user_input.lower() in {"exit", "quit", "stop", "goodbye"}:
                speak("Goodbye Boss. See you next time.")
                wait_until_finished()
                break
            
            # ---- PLAN ACTION ----
            plan = plan_action(user_input)
            
            if plan.get("agent") == "browser":
                if plan.get("action") == "youtube":
                    browser_agent.play_youtube(plan.get("query", ""))
                    speak("Playing on YouTube.")
                    wait_until_finished()
                    time.sleep(1)
                    continue
                
                if plan.get("action") == "open_url":
                    browser_agent.open_url(plan.get("url", ""))
                    speak("Opening browser.")
                    wait_until_finished()
                    time.sleep(1)
                    continue
            
            if plan.get("agent") == "windows":
                try:
                    windows_agent.open_app(plan.get("app", ""))
                    speak(f"Opening {plan.get('app')}.")
                except Exception as e:
                    print(f"Error opening app: {e}")
                    speak("I couldn't open that application.")
                wait_until_finished()
                time.sleep(1)
                continue
            
            # ---- MEMORY ----
            update_memory(memory, user_input)
            save_memory(memory)
            
            # ---- MOOD + TIME ----
            mood = get_mood()
            hour = datetime.now().hour
            
            time_of_day = (
                "late night" if hour < 6 else
                "morning" if hour < 12 else
                "afternoon" if hour < 18 else
                "evening"
            )
            
            # ---- PROMPT ----
            prompt = f"""
{system_prompt}

Mood: {mood}
Time: {time_of_day}
Memory: {memory}

User: {user_input}
Echo:
""".strip()
            
            # ---- GENERATE ----
            print("\n🤖 Echo: ", end="", flush=True)
            response = llm.generate(prompt)
            print(response)
            
            # ---- SPEAK ----
            speak(response)
            
            # Wait for speech to start
            time.sleep(0.1)
            
        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user.")
            speak("Goodbye!")
            wait_until_finished()
            break
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()