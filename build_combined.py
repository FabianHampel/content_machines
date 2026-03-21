#!/usr/bin/env python3
"""Build combined ROTBOTS notebook from individual notebooks.

Reads all individual notebooks in pipeline order, deduplicates setup cells,
removes session-select cells, and produces a single ROTBOTS_Full_Pipeline.ipynb.

Usage:
    python build_combined.py

Markers in notebook cells (in source comments):
    # @SKIP_IN_COMBINED   — Cell is dropped entirely (e.g. session select, duplicate setup)
    # @SETUP              — Cell is collected into the shared setup section (deduplicated)
    # @API_KEY            — API key cell, collected into shared setup

Cells without markers are included as-is.
"""

import json
import copy
from pathlib import Path

# Pipeline order
NOTEBOOK_ORDER = [
    "01_Archive_Scraper.ipynb",
    "02_Script_Writer.ipynb",
    "03_Effects_and_Log.ipynb",
    "04_The_Voice.ipynb",
    "05_Generate.ipynb",
    "07_Subtitles.ipynb",
    "06_Assemble.ipynb",
]

NOTEBOOKS_DIR = Path("notebooks")
OUTPUT_PATH = Path("notebooks/ROTBOTS_Full_Pipeline.ipynb")


def cell_has_marker(cell, marker):
    """Check if any source line contains the marker."""
    src = cell.get("source", [])
    text = "".join(src) if isinstance(src, list) else src
    return marker in text


def cell_contains_any(cell, patterns):
    """Check if cell source contains any of the given patterns."""
    src = cell.get("source", [])
    text = "".join(src) if isinstance(src, list) else src
    return any(p in text for p in patterns)


def is_setup_cell(cell):
    """Auto-detect setup/boilerplate cells even without markers."""
    if cell.get("cell_type") != "code":
        return False
    return cell_contains_any(cell, [
        "drive.mount(",
        "BASE_DIR = Path(",
        "from google.colab import drive",
    ])


def is_session_select_cell(cell):
    """Auto-detect session selection cells."""
    if cell.get("cell_type") != "code":
        return False
    return cell_contains_any(cell, [
        "# SELECT SESSION",
        "sessions = sorted([d.name for d in BASE_DIR",
        "SESSION_NAME = sessions[-1]",
    ])


def is_pip_install(cell):
    """Check if cell is primarily a pip install."""
    if cell.get("cell_type") != "code":
        return False
    src = "".join(cell.get("source", []))
    lines = [l.strip() for l in src.split("\n") if l.strip() and not l.strip().startswith("#")]
    return all(l.startswith("!pip") or l.startswith("import") or l.startswith("from ") or l.startswith("print") for l in lines)


def extract_pip_packages(cell):
    """Extract pip package names from install cells."""
    src = "".join(cell.get("source", []))
    packages = set()
    for line in src.split("\n"):
        if "!pip install" in line:
            parts = line.split("!pip install")[1].strip().split()
            for p in parts:
                if not p.startswith("-"):
                    packages.add(p)
    return packages


def extract_imports(cell):
    """Extract import lines from a cell."""
    src = "".join(cell.get("source", []))
    imports = []
    for line in src.split("\n"):
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            if stripped not in imports:
                imports.append(stripped)
    return imports


def make_markdown_cell(source):
    """Create a markdown cell."""
    if isinstance(source, str):
        source = [source]
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source
    }


def make_code_cell(source):
    """Create a code cell."""
    if isinstance(source, str):
        source = [source]
    return {
        "cell_type": "code",
        "metadata": {},
        "source": source,
        "execution_count": None,
        "outputs": []
    }


def build_combined():
    """Build the combined notebook."""
    
    # Collect all cells from all notebooks
    all_pip_packages = set()
    all_imports = set()
    content_cells = []  # (notebook_name, cell) tuples
    
    for nb_file in NOTEBOOK_ORDER:
        nb_path = NOTEBOOKS_DIR / nb_file
        if not nb_path.exists():
            print(f"  WARNING: {nb_path} not found, skipping")
            continue
        
        with open(nb_path) as f:
            nb = json.load(f)
        
        print(f"  Processing {nb_file}: {len(nb.get('cells', []))} cells")
        
        for cell in nb.get("cells", []):
            # Skip cells with explicit marker
            if cell_has_marker(cell, "@SKIP_IN_COMBINED"):
                continue
            
            # Skip session select cells (auto-detected)
            if is_session_select_cell(cell):
                continue
            
            # Skip setup/drive mount cells (will be unified)
            if is_setup_cell(cell):
                continue
            
            # Collect pip packages but skip the install cell itself
            if cell.get("cell_type") == "code" and cell_contains_any(cell, ["!pip install"]):
                all_pip_packages.update(extract_pip_packages(cell))
                # Also collect imports from this cell
                for imp in extract_imports(cell):
                    all_imports.add(imp)
                continue
            
            # Collect imports from code cells
            if cell.get("cell_type") == "code":
                for imp in extract_imports(cell):
                    all_imports.add(imp)
            
            content_cells.append((nb_file, cell))
    
    # Build the combined notebook
    cells = []
    
    # Header
    cells.append(make_markdown_cell(
        "# \ud83e\udd16 ROTBOTS \u2014 Full Pipeline\n"
        "## From Topic to Finished Video in One Notebook\n"
        "\n"
        "---\n"
        "\n"
        "This notebook runs the **entire** ROTBOTS content machine pipeline:\n"
        "\n"
        "1. \ud83c\udfac Archive Scraper (optional found footage)\n"
        "2. \ud83d\udce5 Feed the Machine (scrape + summarize sources)\n"
        "3. \u270d\ufe0f Script Writer (essay + storyboard + T2V prompts)\n"
        "4. \ud83c\udfa8 Effects & Chain Log (FFmpeg effects + AI decision log)\n"
        "5. \ud83c\udf99\ufe0f The Voice (TTS narration)\n"
        "6. \ud83c\udfa5 Video Generator (AI video clips)\n"
        "7. \ud83d\udcdd Subtitles (TikTok-style, optional)\n"
        "8. \ud83c\udf9e\ufe0f Assemble (combine everything into final video)\n"
        "\n"
        "**Just fill in your inputs and press \u25b6\ufe0f Play on each cell, top to bottom.**\n"
        "\n"
        "---"
    ))
    
    # Unified setup cell
    pip_list = " ".join(sorted(all_pip_packages - {"requests", "-q", "-Q"}))
    cells.append(make_code_cell(
        "# ============================================================\n"
        "# SETUP \u2014 Run this cell first!\n"
        "# ============================================================\n"
        f"!pip install -q {pip_list}\n"
        "\n"
        "import json, re, random, os, time, subprocess, shutil\n"
        "from pathlib import Path\n"
        "from IPython.display import display, Markdown, HTML, Audio, Video\n"
        "\n"
        "from google.colab import drive\n"
        "drive.mount('/content/drive')\n"
        "\n"
        "BASE_DIR = Path('/content/drive/MyDrive/rotbots_workshop')\n"
        "BASE_DIR.mkdir(parents=True, exist_ok=True)\n"
        "TEMP = Path('/content/temp_work'); TEMP.mkdir(exist_ok=True)\n"
        "\n"
        "print('\u2705 All dependencies installed')\n"
        "print(f'\ud83d\udcc1 Workspace: {BASE_DIR}')"
    ))
    
    # API keys cell
    cells.append(make_code_cell(
        "# ============================================================\n"
        "# API KEYS \u2014 Paste your keys here\n"
        "# ============================================================\n"
        "\n"
        "GROQ_API_KEY = ''     # Free: https://console.groq.com/keys\n"
        "FAL_API_KEY = ''      # https://fal.ai/dashboard/keys\n"
        "\n"
        "# LLM Settings\n"
        "LLM_MODEL = 'llama-3.3-70b-versatile'\n"
        "LLM_TEMPERATURE = 0.8\n"
        "LLM_MAX_TOKENS = 4096\n"
        "GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'\n"
        "\n"
        "if FAL_API_KEY: os.environ['FAL_KEY'] = FAL_API_KEY\n"
        "\n"
        "# Validate\n"
        "if not GROQ_API_KEY: print('\u26a0\ufe0f  Paste Groq key above!')\n"
        "elif not GROQ_API_KEY.startswith('gsk_'): print('\u26a0\ufe0f  Groq key should start with gsk_')\n"
        "else: print(f'\u2705 Groq: {LLM_MODEL}')\n"
        "if FAL_API_KEY: print('\u2705 fal.ai configured')\n"
        "else: print('\u26a0\ufe0f  fal.ai key needed for video generation')"
    ))
    
    # Add content cells with section dividers
    current_notebook = None
    
    # Notebook display names
    nb_names = {
        "01_Archive_Scraper.ipynb": "\ud83c\udfac Archive Scraper (Optional)",
        "02_Script_Writer.ipynb": "\ud83d\udce5 Script Writer",
        "03_Effects_and_Log.ipynb": "\ud83c\udfa8 Effects & Chain Log",
        "04_The_Voice.ipynb": "\ud83c\udf99\ufe0f The Voice",
        "05_Generate.ipynb": "\ud83c\udfa5 Video Generator",
        "07_Subtitles.ipynb": "\ud83d\udcdd Subtitles (Optional)",
        "06_Assemble.ipynb": "\ud83c\udf9e\ufe0f Assemble",
    }
    
    for nb_file, cell in content_cells:
        # Add section divider when switching notebooks
        if nb_file != current_notebook:
            current_notebook = nb_file
            name = nb_names.get(nb_file, nb_file)
            cells.append(make_markdown_cell(
                f"\n---\n---\n# {name}\n\n"
                f"*From `{nb_file}`*\n"
            ))
        
        # Skip cells that are just "Setup complete" prints or redundant headers
        src = "".join(cell.get("source", []))
        if cell.get("cell_type") == "code" and src.strip() in ["print('\u2705 Setup complete')", "print('\u2705 Setup')", "print('\u2705 Helpers loaded')"]:
            continue
        
        # Skip title markdown cells from individual notebooks (we have our own header)
        if cell.get("cell_type") == "markdown":
            if src.strip().startswith("# \ud83e\udd16 ROTBOTS") or src.strip().startswith("# \ud83c\udfac ROTBOTS") or src.strip().startswith("# \ud83c\udf99\ufe0f ROTBOTS") or src.strip().startswith("# \ud83c\udfa5 ROTBOTS") or src.strip().startswith("# \ud83d\udcdd ROTBOTS") or src.strip().startswith("# \ud83c\udf9e\ufe0f ROTBOTS"):
                continue
            # Skip "Next steps" / footer cells
            if "ROTBOTS Workshop" in src and "LI-MA" in src and len(src) < 200:
                continue
        
        # Skip API key cells from individual notebooks (we have unified one)
        if cell.get("cell_type") == "code" and cell_contains_any(cell, ["GROQ_API_KEY = ''", "FAL_API_KEY = ''", "# API KEY"]):
            if not cell_contains_any(cell, ["@KEEP_IN_COMBINED"]):
                continue
        
        cells.append(cell)
    
    # Build notebook
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 0,
        "metadata": {
            "colab": {"provenance": [], "toc_visible": True},
            "kernelspec": {"name": "python3", "display_name": "Python 3"},
            "language_info": {"name": "python"}
        },
        "cells": cells
    }
    
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(notebook, f, indent=1)
    
    print(f"\n\u2705 Combined notebook: {OUTPUT_PATH}")
    print(f"   {len(cells)} cells from {len(NOTEBOOK_ORDER)} notebooks")
    print(f"   Pip packages: {pip_list}")


if __name__ == "__main__":
    build_combined()
