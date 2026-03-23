#!/usr/bin/env python3
"""Build ROTBOTS_Full_Pipeline.ipynb from all 9 individual notebooks."""
import json
from pathlib import Path

NOTEBOOKS = [
    '01_Video_Plan.ipynb',
    '02_Script_Writer.ipynb',
    '03_Archive_Scraper.ipynb',
    '04_Upload_Footage.ipynb',
    '05_Effects_and_Log.ipynb',
    '06_The_Voice.ipynb',
    '07_Generate.ipynb',
    '08_Subtitles.ipynb',
    '09_Assemble.ipynb',
]

SKIP_PATTERNS = [
    "drive.mount('/content/drive')",
    "drive.mount(\"/content/drive\")",
    'BASE_DIR = Path',
    'BASE_DIR.mkdir',
    'sessions = sorted',
    'SESSION_NAME = sessions',
    'SESSION_DIR = BASE_DIR',
    'video_plan.json',
    'session_info.json',
    'for i,s in enumerate(sessions)',
    'if not sessions',
    "print('\u2705 Setup')",
    "print('\u2705 Setup complete')",
]

PIP_PACKAGES = 'requests beautifulsoup4 pymupdf edge-tts fal-client yt-dlp faster-whisper'

def should_skip(cell):
    if cell['cell_type'] != 'code': return False
    src = '\n'.join(cell.get('source', []) if isinstance(cell.get('source'), list) else [cell.get('source', '')])
    # Skip pip installs (we do one combined)
    if src.strip().startswith('!pip install'): return True
    # Skip drive mount / session select boilerplate
    for pat in SKIP_PATTERNS:
        if pat in src and len(src.strip().split('\n')) <= 8: return True
    return False

def build():
    nb_dir = Path('notebooks')
    cells = []
    
    # Header
    cells.append({'cell_type':'markdown','metadata':{},'source':[
        '# \ud83e\udd16 ROTBOTS \u2014 Full Pipeline\n',
        '## Topic \u2192 Video in One Notebook\n',
        '\n',
        '---\n',
        '\n',
        'All 9 pipeline stages in one place. Run cells top to bottom.\n',
        '\n',
        '> **\ud83e\udd14** Every cell is an automated decision. What does the machine choose?\n',
        '\n',
        '---'
    ]})
    
    # Combined setup
    cells.append({'cell_type':'code','metadata':{},'source':[
        f'# SETUP (all dependencies)\n',
        f'!pip install -q {PIP_PACKAGES}\n',
        'import json, re, random, requests, subprocess, shutil, os, time as _time, threading, edge_tts\n',
        'from pathlib import Path\n',
        'from bs4 import BeautifulSoup\n',
        'from IPython.display import display, Markdown, HTML, Audio, Video\n',
        '\n',
        'from google.colab import drive\n',
        "drive.mount('/content/drive')\n",
        "BASE_DIR = Path('/content/drive/MyDrive/rotbots_workshop')\n",
        'BASE_DIR.mkdir(parents=True, exist_ok=True)\n',
        "TEMP = Path('/content/temp_assembly'); TEMP.mkdir(exist_ok=True)\n",
        '\n',
        '# Progress helpers\n',
        'def progress_bar(c,t,l=\'\',w=30):\n',
        '    p=c/t if t>0 else 0;f=int(w*p);return f\'<div style="font-family:monospace;font-size:14px;padding:2px 0;">{"\u2588"*f}{"\u2591"*(w-f)} {c}/{t} {l} ({p:.0%})</div>\'\n',
        'def progress_html(title,c,t,l=\'\',d=\'\',color=\'#4ecca3\'):\n',
        '    return f\'<div style="background:#1a1a2e;padding:12px;border-radius:8px;color:#eaeaea;font-family:monospace;"><div style="font-size:16px;font-weight:bold;color:{color};">{title}</div>{progress_bar(c,t,l)}\' + (f\'<div style="color:#a0a0a0;font-size:12px;margin-top:4px;">{d}</div>\' if d else \'\') + \'</div>\'\n',
        '\n',
        "print('\u2705 All dependencies ready')\n",
    ],'execution_count':None,'outputs':[]})
    
    # API Keys
    cells.append({'cell_type':'code','metadata':{},'source':[
        '# API KEYS\n',
        "GROQ_API_KEY = ''   # Free: https://console.groq.com/keys\n",
        "FAL_API_KEY = ''    # Video: https://fal.ai/dashboard/keys\n",
        '\n',
        "if GROQ_API_KEY: print('\u2705 Groq')\n",
        "else: print('\u26a0\ufe0f Paste GROQ_API_KEY above')\n",
        "if FAL_API_KEY: os.environ['FAL_KEY']=FAL_API_KEY; print('\u2705 fal.ai')\n",
        "else: print('\u26a0\ufe0f Paste FAL_API_KEY above')\n",
    ],'execution_count':None,'outputs':[]})
    
    # Process each notebook
    for nb_name in NOTEBOOKS:
        nb_path = nb_dir / nb_name
        if not nb_path.exists():
            print(f'  SKIP {nb_name} (not found)')
            continue
        
        with open(nb_path) as f:
            notebook = json.load(f)
        
        # Section divider
        num = nb_name.split('_')[0]
        title = nb_name.replace('.ipynb','').replace('_',' ').lstrip('0123456789 ')
        cells.append({'cell_type':'markdown','metadata':{},'source':[
            f'\n---\n\n# \u2501\u2501 {num}: {title}\n'
        ]})
        
        # Add cells (skip boilerplate)
        added = 0
        for cell in notebook.get('cells', []):
            if should_skip(cell):
                continue
            cells.append(cell)
            added += 1
        
        print(f'  {nb_name}: {added} cells added')
    
    # Footer
    cells.append({'cell_type':'markdown','metadata':{},'source':[
        '\n---\n\n# \ud83c\udfc1 Pipeline Complete\n',
        '\n',
        'Every step: automated decisions. What does that mean?\n',
        '\n',
        '---\n',
        '*ROTBOTS \u2014 LI-MA TDA 2026, Amsterdam*'
    ]})
    
    # Build notebook
    combined = {
        'nbformat': 4, 'nbformat_minor': 0,
        'metadata': {
            'colab': {'provenance': [], 'toc_visible': True},
            'kernelspec': {'name': 'python3', 'display_name': 'Python 3'},
            'language_info': {'name': 'python'}
        },
        'cells': cells
    }
    
    out = nb_dir / 'ROTBOTS_Full_Pipeline.ipynb'
    with open(out, 'w') as f:
        json.dump(combined, f)
    
    size = out.stat().st_size
    print(f'\n\u2705 {out}: {len(cells)} cells, {size/1024:.0f}KB')
    if size > 70000:
        print(f'\u26a0\ufe0f File is {size/1024:.0f}KB - may exceed GitHub API limit (use git push)')

if __name__ == '__main__':
    build()
