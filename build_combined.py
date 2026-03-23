#!/usr/bin/env python3
"""Build ROTBOTS_Full_Pipeline.ipynb from all 9 individual notebooks.

Strategy: Skip ALL setup/session/API cells from individual notebooks.
Instead, inject bridging cells that define missing variables from
the in-memory pipeline state.
"""
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

PIP_PACKAGES = 'requests beautifulsoup4 pymupdf edge-tts fal-client yt-dlp faster-whisper'


def should_skip(cell):
    """Skip setup, session-loading, API key, and pip install cells."""
    if cell['cell_type'] != 'code':
        return False
    src = '\n'.join(cell.get('source', []) if isinstance(cell.get('source'), list)
                    else [cell.get('source', '')])

    # Always skip pip installs
    if src.strip().startswith('!pip install'):
        return True

    # Skip cells that are primarily boilerplate (setup, session loading, API keys)
    skip_markers = [
        "drive.mount(",
        'BASE_DIR = Path',
        'BASE_DIR.mkdir',
        'sessions = sorted',
        'SESSION_NAME = sessions',
        'SESSION_DIR = BASE_DIR',
        'for i,s in enumerate(sessions)',
        'if not sessions',
        "GROQ_API_KEY = ''",
        "FAL_API_KEY = ''",
        "FAL_API_KEY=''",
        "print('[OK] Setup')",
        "print('[OK] Setup complete')",
    ]
    for marker in skip_markers:
        if marker in src:
            return True

    # Skip session-loading cells that read video_plan.json from disk
    if 'video_plan.json' in src and ('json.load' in src or 'sessions' in src):
        return True

    return False


def make_code_cell(source_lines):
    return {
        'cell_type': 'code', 'metadata': {},
        'source': source_lines,
        'execution_count': None, 'outputs': []
    }


def make_md_cell(source_lines):
    return {'cell_type': 'markdown', 'metadata': {}, 'source': source_lines}


def build():
    nb_dir = Path('notebooks')
    cells = []

    # ── Header ──
    cells.append(make_md_cell([
        '# ROTBOTS -- Full Pipeline\n',
        '## Topic -> Video in One Notebook\n',
        '\n',
        '---\n',
        '\n',
        'All 9 pipeline stages in one place. Run cells top to bottom.\n',
        '\n',
        '> Every cell is an automated decision. What does the machine choose?\n',
        '\n',
        '---'
    ]))

    # ── Combined Setup (all imports, drive mount, helpers) ──
    cells.append(make_code_cell([
        f'# SETUP (all dependencies)\n',
        f'!pip install -q {PIP_PACKAGES}\n',
        '\n',
        'import json, re, random, requests, subprocess, shutil, os, time as _time, threading\n',
        'import edge_tts, fal_client\n',
        'from pathlib import Path\n',
        'from bs4 import BeautifulSoup\n',
        'from IPython.display import display, Markdown, HTML, Audio, Video\n',
        'from google.colab import drive, files\n',
        '\n',
        "drive.mount('/content/drive')\n",
        "BASE_DIR = Path('/content/drive/MyDrive/rotbots_workshop')\n",
        'BASE_DIR.mkdir(parents=True, exist_ok=True)\n',
        "TEMP = Path('/content/temp_assembly'); TEMP.mkdir(exist_ok=True)\n",
        '\n',
        '# Progress helpers\n',
        "def progress_bar(c,t,l='',w=30):\n",
        "    p=c/t if t>0 else 0; f=int(w*p)\n",
        "    return f'<div style=\"font-family:monospace;font-size:14px;padding:2px 0;\">{\"#\"*f}{\"-\"*(w-f)} {c}/{t} {l} ({p:.0%})</div>'\n",
        "def progress_html(title,c,t,l='',d='',color='#4ecca3'):\n",
        '    return f\'<div style="background:#1a1a2e;padding:12px;border-radius:8px;color:#eaeaea;font-family:monospace;"><div style="font-size:16px;font-weight:bold;color:{color};">{title}</div>{progress_bar(c,t,l)}\' + (f\'<div style="color:#a0a0a0;font-size:12px;margin-top:4px;">{d}</div>\' if d else \'\') + \'</div>\'\n',
        '\n',
        "print('[OK] All dependencies ready')\n",
    ]))

    # ── API Keys ──
    cells.append(make_md_cell([
        '---\n',
        '# >>> YOUR INPUT: API Keys\n',
        '\n',
        'Paste your API keys below. Both are free to get.\n',
        '\n',
        '| Service | What for | Get it here |\n',
        '|---------|----------|-------------|\n',
        '| **Groq** | LLM (text generation) | https://console.groq.com/keys |\n',
        '| **fal.ai** | Video generation | https://fal.ai/dashboard/keys |\n',
    ]))
    cells.append(make_code_cell([
        '# =============================================\n',
        '#   PASTE YOUR API KEYS HERE\n',
        '# =============================================\n',
        '\n',
        "GROQ_API_KEY = ''   # <-- paste your Groq key here\n",
        "FAL_API_KEY  = ''   # <-- paste your fal.ai key here\n",
        '\n',
        '# =============================================\n',
        '\n',
        "if GROQ_API_KEY: print('[OK] Groq API key set')\n",
        "else: print('[!] GROQ_API_KEY is empty -- paste it above!')\n",
        "if FAL_API_KEY: os.environ['FAL_KEY']=FAL_API_KEY; print('[OK] fal.ai API key set')\n",
        "else: print('[!] FAL_API_KEY is empty -- paste it above!')\n",
    ]))

    # ── Bridging cells injected BEFORE specific notebook sections ──
    # Each value is a LIST of cells (markdown + code)
    BRIDGING = {
        # 01_Video_Plan uses the section divider as its header (no extra bridging needed)
        '02_Script_Writer.ipynb': [make_code_cell([
            '# BRIDGE: Script Writer needs these from Video Plan\n',
            "TARGET_VIDEO_LENGTH = TOTAL_VIDEO_LENGTH\n",
            "TOTAL_NARRATION_WORDS = int(CONTENT_LENGTH * 2.5)\n",
        ])],
        '03_Archive_Scraper.ipynb': [
            make_md_cell([
                '---\n',
                '# >>> YOUR INPUT: Archive Sources (optional)\n',
                '\n',
                'Add archive.org URLs below if you set ARCHIVE_RATIO > 0.\n',
                'Skip this if you only use AI-generated video.\n',
            ]),
        ],
        '04_Upload_Footage.ipynb': [make_code_cell([
            '# BRIDGE: Upload needs these variables\n',
            "UPLOADS_DIR = SESSION_DIR / 'uploads'; UPLOADS_DIR.mkdir(exist_ok=True)\n",
            "needed = plan.get('num_upload_scenes', 0) if 'plan' in dir() else NUM_UPLOAD_SCENES\n",
            "upload_clips = []\n",
        ])],
        '06_The_Voice.ipynb': [make_code_cell([
            '# BRIDGE: Voice needs audio dir\n',
            "AUDIO_DIR = SESSION_DIR / 'audio'; AUDIO_DIR.mkdir(exist_ok=True)\n",
        ])],
        '07_Generate.ipynb': [make_code_cell([
            '# BRIDGE: Generate needs video dir + fal key\n',
            "VIDEOS_DIR = SESSION_DIR / 'videos'; VIDEOS_DIR.mkdir(exist_ok=True)\n",
            "if FAL_API_KEY and not os.environ.get('FAL_KEY'): os.environ['FAL_KEY'] = FAL_API_KEY\n",
        ])],
        '08_Subtitles.ipynb': [make_code_cell([
            '# BRIDGE: Subtitles -- skip if disabled\n',
            "AUDIO_DIR = SESSION_DIR / 'audio'\n",
            "if not ENABLE_SUBTITLES:\n",
            "    print('Subtitles disabled, skipping.')\n",
        ])],
        '09_Assemble.ipynb': [make_code_cell([
            '# BRIDGE: Assemble needs all pipeline state\n',
            "VIDEOS_DIR = SESSION_DIR / 'videos'\n",
            "AUDIO_DIR = SESSION_DIR / 'audio'\n",
            "narration_file = AUDIO_DIR / 'narration_full.mp3'\n",
            "has_narration_file = narration_file.exists()\n",
            "sub_file = SESSION_DIR / 'subtitles.ass'\n",
            "ENABLE_NARRATION = True\n",
            '\n',
            "# Load storyboard from disk (built by Script Writer)\n",
            "with open(SESSION_DIR / 'storyboard.json') as f: storyboard = json.load(f)\n",
            '\n',
            "# Load prompts for effects map\n",
            "prompts_data = []\n",
            "if (SESSION_DIR / 'prompts.json').exists():\n",
            "    with open(SESSION_DIR / 'prompts.json') as f: prompts_data = json.load(f)\n",
            "effects_map = {int(p['scene']): p for p in prompts_data if p.get('ffmpeg_effects')}\n",
            '\n',
            "# Load clips\n",
            "archive_clips = []\n",
            "if (SESSION_DIR / 'archive_clips.json').exists():\n",
            "    with open(SESSION_DIR / 'archive_clips.json') as f: archive_clips = json.load(f).get('clips', [])\n",
            "upload_clips_data = []\n",
            "if (SESSION_DIR / 'upload_clips.json').exists():\n",
            "    with open(SESSION_DIR / 'upload_clips.json') as f: upload_clips_data = json.load(f).get('clips', [])\n",
            "# Use upload_clips_data if upload_clips not in memory\n",
            "if not upload_clips: upload_clips = upload_clips_data\n",
            '\n',
            "# Load essay for credits\n",
            "essay = None\n",
            "if (SESSION_DIR / 'essay_script.json').exists():\n",
            "    with open(SESSION_DIR / 'essay_script.json') as f: essay = json.load(f)\n",
            '\n',
            "# Scene counts for summary\n",
            "ai_count = sum(1 for s in storyboard if s['scene_type'] == 'ai_generated')\n",
            "arc_count = sum(1 for s in storyboard if s['scene_type'] == 'archive')\n",
            "upl_count = sum(1 for s in storyboard if s['scene_type'] == 'upload')\n",
            '\n',
            "print(f'[OK] Assembly ready: {len(storyboard)} scenes ({ai_count} AI + {arc_count} archive + {upl_count} upload)')\n",
            "print(f'  Narration: {\"narration_full.mp3\" if has_narration_file else \"none\"}')\n",
            "print(f'  Subtitles: {\"yes\" if sub_file.exists() else \"no\"}')\n",
            "print(f'  Effects: {len(effects_map)}')\n",
        ])],
    }

    # ── Process each notebook ──
    for nb_name in NOTEBOOKS:
        nb_path = nb_dir / nb_name
        if not nb_path.exists():
            print(f'  SKIP {nb_name} (not found)')
            continue

        with open(nb_path) as f:
            notebook = json.load(f)

        # Section divider (with input instructions for user-facing sections)
        num = nb_name.split('_')[0]
        title = nb_name.replace('.ipynb', '').replace('_', ' ').lstrip('0123456789 ')
        if nb_name == '01_Video_Plan.ipynb':
            cells.append(make_md_cell([
                '\n---\n\n',
                f'# >>> YOUR INPUT: {title}\n',
                '\n',
                'Configure your video below. Change **TOPIC**, **SOURCES**, and settings.\n',
                '\n',
                '**SOURCES** can be: website URLs, PDF links, or raw text.\n',
            ]))
        else:
            cells.append(make_md_cell([f'\n---\n\n# == {num}: {title}\n']))

        # Inject bridging cells if needed
        if nb_name in BRIDGING:
            for bridging_cell in BRIDGING[nb_name]:
                cells.append(bridging_cell)

        # Add cells (skip boilerplate)
        added = 0
        for cell in notebook.get('cells', []):
            if should_skip(cell):
                continue
            cells.append(cell)
            added += 1

        print(f'  {nb_name}: {added} cells')

    # ── Footer ──
    cells.append(make_md_cell([
        '\n---\n\n# Pipeline Complete\n',
        '\n',
        'Every step: automated decisions. What does that mean?\n',
        '\n',
        '---\n',
        '*ROTBOTS -- LI-MA TDA 2026, Amsterdam*'
    ]))

    # ── Build notebook JSON ──
    combined = {
        'nbformat': 4, 'nbformat_minor': 0,
        'metadata': {
            'colab': {'provenance': [], 'toc_visible': True},
            'kernelspec': {'name': 'python3', 'display_name': 'Python 3'},
            'language_info': {'name': 'python'}
        },
        'cells': cells
    }

    # ── Strip any remaining emoji from the output ──
    raw = json.dumps(combined, ensure_ascii=True)
    combined = json.loads(raw)

    out = nb_dir / 'ROTBOTS_Full_Pipeline.ipynb'
    with open(out, 'w') as f:
        json.dump(combined, f, ensure_ascii=True)

    size = out.stat().st_size
    print(f'\n[OK] {out}: {len(cells)} cells, {size/1024:.0f}KB')


if __name__ == '__main__':
    build()
