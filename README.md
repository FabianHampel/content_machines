# 🤖 ROTBOTS — Content Machines

**"Anatomy of a Content Machine"**

An AI-powered video content pipeline: Topic in → finished video out.

## 📓 Notebooks

| # | Notebook | Description | Open in Colab |
|---|----------|-------------|---------------|
| 0 | Setup | Google Drive connection (shared workspace) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/00_Setup.ipynb) |
| 2 | Script Writer | Sources → Essay → Storyboard → T2V Prompts | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/02_Script_Writer.ipynb) |
| 4 | The Voice | Text-to-Speech narration (Edge-TTS, free) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/04_The_Voice.ipynb) |
| 5 | Video Generator | T2V Prompts → AI Video Clips + Found Footage | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/05_Generate.ipynb) |
| 6 | Assemble | FFmpeg: Videos + Audio → Final Video | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/06_Assemble.ipynb) |

## 🔄 Pipeline Flow

```
02_Script_Writer  →  prompts.json + essay_script.json  (on Google Drive)
       ↓
04_The_Voice      →  narration audio files              (on Google Drive)
       ↓
05_Generate       →  video clips                        (on Google Drive)
       ↓
06_Assemble       →  final_video.mp4                    (on Google Drive)
```

All notebooks share a workspace on Google Drive (`My Drive/rotbots_workshop/`).

## 🛠️ Requirements

- Google Account (for Colab + Drive)
- Groq API Key (free): https://console.groq.com/keys
- fal.ai API Key (for video generation): https://fal.ai/dashboard/keys
- Edge-TTS is free, no key needed
- FFmpeg is pre-installed on Colab
