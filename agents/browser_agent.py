import webbrowser
import urllib.parse


def open_url(url: str):
    webbrowser.open(url)


def play_youtube(query: str):
    q = urllib.parse.quote(query)
    url = f"https://www.youtube.com/results?search_query={q}"
    webbrowser.open(url)
