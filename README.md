# 🤖 ROTBOTS — Content Machines

**"Anatomy of a Content Machine"** — Workshop for LI-MA TDA 2026, Amsterdam

AI video pipeline: Topic in → finished video out.

## 🚀 Quick Start — All-in-One

[![Open Full Pipeline in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/ROTBOTS_Full_Pipeline.ipynb)

## 📓 Individual Notebooks

| # | Notebook | What it does | Colab |
|---|----------|-------------|-------|
| 01 | Video Plan | Configure length, content mix, features | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/01_Video_Plan.ipynb) |
| 02 | Script Writer | Sources → Essay → Mixed Storyboard → T2V Prompts | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/02_Script_Writer.ipynb) |
| 03 | Archive Scraper | Download & segment archive.org videos (optional) | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/03_Archive_Scraper.ipynb) |
| 04 | Upload Footage | Upload own video clips (optional) | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/04_Upload_Footage.ipynb) |
| 05 | Effects & Log | FFmpeg effects per scene + AI decision chain | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/05_Effects_and_Log.ipynb) |
| 06 | The Voice | TTS narration for ALL scenes (free Edge-TTS) | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/06_The_Voice.ipynb) |
| 07 | AI Video | Generate AI video clips (fal.ai) | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/07_Generate.ipynb) |
| 08 | Subtitles | TikTok-style word-by-word (5 styles, optional) | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/08_Subtitles.ipynb) |
| 09 | Assemble | Interleave AI + archive + uploads → final video | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/09_Assemble.ipynb) |

## 🔄 Pipeline

```
01_Video_Plan       →  video_plan.json (length, mix ratios, features)
        ↓
02_Script_Writer    →  essay + storyboard (interleaved scene types)
        ↓
03_Archive_Scraper  →  archive clips (if ARCHIVE_RATIO > 0)
04_Upload_Footage   →  uploaded clips (if UPLOAD_RATIO > 0)
        ↓
05_Effects_and_Log  →  FFmpeg effects + chain log
        ↓
06_The_Voice        →  narration for ALL scenes
        ↓
07_Generate         →  AI video clips (only ai_generated scenes)
        ↓
08_Subtitles        →  subtitles.ass (optional)
        ↓
09_Assemble         →  final_video.mp4
```

## 🎬 Video Plan (01)

```python
TOTAL_VIDEO_LENGTH = 60     # Total video in seconds
ARCHIVE_RATIO = 0.3         # 30% archive.org footage
UPLOAD_RATIO = 0.0          # 0% self-uploaded
# Remainder = 70% AI-generated

ENABLE_CREDITS = True
ENABLE_SUBTITLES = False
ENABLE_MUSIC = False
ENABLE_EFFECTS = True
```

Scene order is automatically interleaved:
```
🤖 → 🤖 → 🏛️ → 🤖 → 🤖 → 🏛️ → 🤖 → 🤖 → 🏛️ → 🤖
```

## 🎨 FFmpeg Effects

`film_grain` · `vhs_artifacts` · `celluloid_scratches` · `sepia_tone` · `bw_transition` · `color_grade_warm` · `color_grade_cool` · `vignette` · `flicker` · `desaturate`

## 🛠️ Requirements

- Google Account (Colab + Drive)
- **Groq API Key** (free): https://console.groq.com/keys
- **fal.ai API Key** (video): https://fal.ai/dashboard/keys
- Edge-TTS, Whisper, FFmpeg, yt-dlp: all free, run on Colab

## 🔧 Build Combined Notebook

```bash
python build_combined.py   # generates ROTBOTS_Full_Pipeline.ipynb
```
