# 🤖 ROTBOTS — Content Machines

**"Anatomy of a Content Machine"** — Workshop for LI-MA TDA 2026, Amsterdam

AI video pipeline: Topic in → finished video out.

## 🚀 Quick Start — All-in-One Notebook

Run the entire pipeline in a single notebook:

[![Open Full Pipeline in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/ROTBOTS_Full_Pipeline.ipynb)

## 📓 Individual Notebooks

Or run each step separately:

| # | Notebook | What it does | Colab |
|---|----------|-------------|-------|
| 1 | Archive Scraper | Download & segment Internet Archive videos as found footage | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/01_Archive_Scraper.ipynb) |
| 2 | Script Writer | Sources → Essay → Storyboard → T2V Prompts | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/02_Script_Writer.ipynb) |
| 3 | Effects & Log | Assign FFmpeg effects per scene + view AI decision chain | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/03_Effects_and_Log.ipynb) |
| 4 | The Voice | Text-to-Speech narration (Edge-TTS, free) | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/04_The_Voice.ipynb) |
| 5 | Video Generator | T2V Prompts → AI Video Clips | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/05_Generate.ipynb) |
| 7 | Subtitles | TikTok-style word-by-word subtitles (5 styles) | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/07_Subtitles.ipynb) |
| 6 | Assemble | FFmpeg: Videos + Effects + Audio + Music + Subs + Credits → Final | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/06_Assemble.ipynb) |

## 🔄 Pipeline

```
01_Archive_Scraper  →  archive clips (optional found footage)
        ↓
02_Script_Writer    →  prompts.json + essay_script.json
        ↓
03_Effects_and_Log  →  effects assigned + chain_report.html
        ↓
04_The_Voice        →  narration audio
        ↓
05_Generate         →  AI video clips (+ optional archive footage)
        ↓
07_Subtitles        →  subtitles.ass (optional)
        ↓
06_Assemble         →  final_video.mp4
                       (effects + narration + music + subs + credits)
```

## 📂 Sessions

Each run creates a named folder on Google Drive (auto-named from topic):

```
rotbots_workshop/
├── ai-generated-art/
│   ├── session_info.json
│   ├── summaries.json, essay_script.json, prompts.json
│   ├── storyboard.json, archive_clips.json
│   ├── subtitles.ass, chain_log.json, chain_report.html
│   ├── videos/, audio/, archive_clips/
│   └── final_video.mp4
├── climate-change/
└── my-custom-session/
```

## 🎬 Assembly Toggles

```python
ENABLE_NARRATION = True      # Voice-over
ENABLE_MUSIC = False         # AI-generated (fal.ai) or uploaded MP3
ENABLE_SUBTITLES = False     # TikTok-style (5 styles, random mix)
ENABLE_CREDITS = True        # Rolling credits with sources
# Effects auto-detected from prompts.json (set in 03_Effects_and_Log)
```

## 🎨 FFmpeg Effects (10 from original ROTBOTS)

`film_grain` · `vhs_artifacts` · `celluloid_scratches` · `sepia_tone` · `bw_transition` · `color_grade_warm` · `color_grade_cool` · `vignette` · `flicker` · `desaturate`

## 🔧 Building the Combined Notebook

The Full Pipeline notebook is auto-generated from the individual notebooks:

```bash
python build_combined.py   # generates notebooks/ROTBOTS_Full_Pipeline.ipynb
```

Run this after editing any individual notebook to keep the combined version in sync.

## 🛠️ Requirements

- Google Account (Colab + Drive)
- **Groq API Key** (free): https://console.groq.com/keys
- **fal.ai API Key** (video + optional music): https://fal.ai/dashboard/keys
- Edge-TTS, Whisper, FFmpeg, yt-dlp: all free, run on Colab
