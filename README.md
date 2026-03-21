# 🤖 ROTBOTS — Content Machines

**"Anatomy of a Content Machine"**

AI video pipeline: Topic in → finished video out.

## 📓 Notebooks

| # | Notebook | Description | Colab |
|---|----------|-------------|-------|
| 2 | Script Writer | Sources → Essay → Storyboard → T2V Prompts | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/02_Script_Writer.ipynb) |
| 4 | The Voice | Text-to-Speech narration (Edge-TTS, free) | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/04_The_Voice.ipynb) |
| 5 | Video Generator | T2V Prompts → AI Video Clips + Found Footage | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/05_Generate.ipynb) |
| 7 | Subtitles | TikTok-style word-by-word subtitles (Whisper) | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/07_Subtitles.ipynb) |
| 6 | Assemble | FFmpeg: Videos + Audio + Music + Subs + Credits → Final | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/06_Assemble.ipynb) |

## 🔄 Pipeline

```
02_Script_Writer  →  prompts.json + essay_script.json
       ↓
04_The_Voice      →  narration audio
       ↓
05_Generate       →  video clips
       ↓
07_Subtitles      →  subtitles.ass (optional)
       ↓
06_Assemble       →  final_video.mp4
                     (+ optional music, subtitles, credits)
```

## 📂 Session System

Each run creates a named session folder on Google Drive:

```
rotbots_workshop/
├── ai-generated-art/         ← auto-named from topic
│   ├── session_info.json
│   ├── summaries.json
│   ├── essay_script.json
│   ├── prompts.json
│   ├── subtitles.ass
│   ├── videos/
│   ├── audio/
│   └── final_video.mp4
├── climate-change/
└── my-custom-name/
```

## 🎬 Assembly Options

The Assembly notebook has toggles for all optional features:

```python
ENABLE_NARRATION = True      # Voice-over
ENABLE_MUSIC = False         # Background music (AI generate or upload)
ENABLE_SUBTITLES = False     # TikTok-style word-by-word subs
ENABLE_CREDITS = True        # Rolling credits with source attribution
```

## 🛠️ Requirements

- Google Account (Colab + Drive)
- **Groq API Key** (free): https://console.groq.com/keys
- **fal.ai API Key** (video + optional music): https://fal.ai/dashboard/keys
- Edge-TTS: free, no key
- Whisper (subtitles): runs on Colab CPU, no key
- FFmpeg: pre-installed on Colab
