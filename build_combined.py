#!/usr/bin/env python3
"""Build combined notebook - reads individual notebooks, deduplicates, generates Full Pipeline.

Usage:
    python build_combined.py
    # Then commit notebooks/ROTBOTS_Full_Pipeline.ipynb
"""
import json, re
from pathlib import Path

NOTEBOOK_ORDER = [
    "01_Archive_Scraper.ipynb", "02_Script_Writer.ipynb", "03_Effects_and_Log.ipynb",
    "04_The_Voice.ipynb", "05_Generate.ipynb", "07_Subtitles.ipynb", "06_Assemble.ipynb",
]
NB_NAMES = {
    "01_Archive_Scraper.ipynb": "🎬 Part 1: Archive Scraper (Optional Found Footage)",
    "02_Script_Writer.ipynb": "📥 Part 2: Script Writer (Sources → Essay → Prompts)",
    "03_Effects_and_Log.ipynb": "🎨 Part 3: Effects & Chain Log",
    "04_The_Voice.ipynb": "🎙️ Part 4: The Voice (TTS Narration)",
    "05_Generate.ipynb": "🎥 Part 5: Video Generator",
    "07_Subtitles.ipynb": "📝 Part 6: Subtitles (Optional)",
    "06_Assemble.ipynb": "🎞️ Part 7: Assemble (Final Video)",
}

def mc(src): return {"cell_type":"markdown","metadata":{},"source":[src]}
def cc(src): return {"cell_type":"code","metadata":{},"source":[src],"execution_count":None,"outputs":[]}

def should_skip(cell):
    src = ''.join(cell.get('source',[]))
    if 'drive.mount(' in src and 'BASE_DIR' in src: return True
    if '# SELECT SESSION' in src or ('sessions = sorted([d.name for d in BASE_DIR' in src): return True
    if ("GROQ_API_KEY = ''" in src or "FAL_API_KEY = ''" in src) and '# API KEY' in src: return True
    if "FAL_API_KEY = ''" in src and 'fal.ai key' in src and len(src) < 300: return True
    if src.strip() in ["print('✅ Setup complete')", "print('✅ Setup')", "print('✅ Helpers loaded')"]: return True
    if cell.get('cell_type') == 'markdown':
        if re.match(r'^#\s+[🤖🎬🎙🎥📝🎞].*ROTBOTS', src.strip()): return True
        if 'ROTBOTS Workshop' in src and 'LI-MA' in src and len(src) < 300: return True
    return False

cells = []
cells.append(mc("# 🤖 ROTBOTS — Full Pipeline\n## Topic → Finished Video in One Notebook\n\n---\n\nRun every cell top to bottom. All 7 pipeline stages in one place.\n\n**You don't need to understand the code.** Just fill in inputs and press ▶️ Play.\n\n---"))
cells.append(cc("# ============================================================\n# SETUP — Run this cell once!\n# ============================================================\n!pip install -q requests beautifulsoup4 pymupdf edge-tts fal-client yt-dlp faster-whisper\n\nimport json, re, random, os, time, subprocess, shutil\nfrom pathlib import Path\nfrom IPython.display import display, Markdown, HTML, Audio, Video\n\nfrom google.colab import drive\ndrive.mount('/content/drive')\n\nBASE_DIR = Path('/content/drive/MyDrive/rotbots_workshop')\nBASE_DIR.mkdir(parents=True, exist_ok=True)\nTEMP = Path('/content/temp_work'); TEMP.mkdir(exist_ok=True)\n\nprint('✅ All dependencies installed')\nprint(f'📁 Workspace: {BASE_DIR}')"))
cells.append(cc("# ============================================================\n# API KEYS — Paste both keys here\n# ============================================================\n\nGROQ_API_KEY = ''     # Free: https://console.groq.com/keys\nFAL_API_KEY = ''      # Video gen: https://fal.ai/dashboard/keys\n\n# LLM Settings\nLLM_MODEL = 'llama-3.3-70b-versatile'\nLLM_TEMPERATURE = 0.8\nLLM_MAX_TOKENS = 4096\nGROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'\n\nif FAL_API_KEY: os.environ['FAL_KEY'] = FAL_API_KEY\n\nif not GROQ_API_KEY: print('⚠️  Paste Groq key!')\nelif not GROQ_API_KEY.startswith('gsk_'): print('⚠️  Key should start with gsk_')\nelse: print(f'✅ Groq: {LLM_MODEL}')\nif FAL_API_KEY: print('✅ fal.ai ready')\nelse: print('⚠️  fal.ai key needed for video generation')"))

for nb_file in NOTEBOOK_ORDER:
    nb_path = Path('notebooks') / nb_file
    if not nb_path.exists(): continue
    with open(nb_path) as f: nb = json.load(f)
    name = NB_NAMES.get(nb_file, nb_file)
    cells.append(mc(f"\n---\n---\n# {name}\n"))
    for cell in nb.get('cells', []):
        if should_skip(cell): continue
        cells.append(cell)

notebook = {
    "nbformat": 4, "nbformat_minor": 0,
    "metadata": {"colab":{"provenance":[],"toc_visible":True},"kernelspec":{"name":"python3","display_name":"Python 3"},"language_info":{"name":"python"}},
    "cells": cells
}
out = Path('notebooks/ROTBOTS_Full_Pipeline.ipynb')
with open(out, 'w') as f: json.dump(notebook, f, indent=1)
print(f"✅ {out}: {len(cells)} cells")
