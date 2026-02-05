# agents/windows_agent.py
import subprocess
import os

APP_PATHS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "chrome_x86": r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "edge": "msedge",
}


def open_app(app_name: str):
    app_name = app_name.lower().strip()

    # ---- Chrome special handling ----
    if app_name == "chrome":
        if os.path.exists(APP_PATHS["chrome"]):
            subprocess.Popen(APP_PATHS["chrome"])
            return
        elif os.path.exists(APP_PATHS["chrome_x86"]):
            subprocess.Popen(APP_PATHS["chrome_x86"])
            return
        else:
            raise FileNotFoundError("Chrome is not installed")

    # ---- Other apps ----
    if app_name in APP_PATHS:
        subprocess.Popen(APP_PATHS[app_name])
    else:
        raise FileNotFoundError(f"Unknown app: {app_name}")
