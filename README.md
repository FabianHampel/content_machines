# ROTBOTS -- Content Machines

**"Anatomy of a Content Machine"** -- Workshop for LI-MA TDA 2026, Amsterdam

AI video pipeline: Topic in, finished video out.

## Quick Start

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FabianHampel/content_machines/blob/main/notebooks/ROTBOTS_Full_Pipeline.ipynb)

1. Open the notebook in Colab
2. Paste your API keys (Groq + fal.ai)
3. Set your topic, sources, and video settings
4. Run all cells top to bottom
5. Watch your video

## Pipeline

```
YOUR INPUT          Topic, sources, video length, content mix
    |
Script Writer       Scrape sources -> essay narration -> storyboard -> T2V prompts
    |
Media Collection    Archive.org clips (optional) + uploaded clips (optional)
    |
Effects             Random FFmpeg effects on AI scenes
    |
Voice               Single narration from full essay (Edge-TTS)
    |
AI Video            Generate video clips from prompts (fal.ai)
    |
Subtitles           Word-by-word subtitles from narration (Whisper)
    |
Assembly            Normalize -> credits -> concat -> audio -> subtitles -> final_video.mp4
```

## Settings

```python
TOPIC = 'Your topic here'
SOURCES = ['https://en.wikipedia.org/wiki/...']   # websites, PDFs, or raw text
TOTAL_VIDEO_LENGTH = 60       # seconds
ARCHIVE_RATIO = 0.0           # 0.0-1.0 archive.org footage
UPLOAD_RATIO  = 0.0           # 0.0-1.0 your own clips
ENABLE_CREDITS   = True
ENABLE_SUBTITLES = True
ENABLE_EFFECTS   = True
```

Scene types are automatically interleaved:
```
AI -> AI -> archive -> AI -> upload -> archive -> AI -> upload -> AI
```

## FFmpeg Effects

`film_grain` `vhs_artifacts` `celluloid_scratches` `sepia_tone` `bw_transition` `color_grade_warm` `color_grade_cool` `vignette` `flicker` `desaturate`

## Requirements

- Google Account (Colab + Drive)
- **Groq API Key** (free): https://console.groq.com/keys
- **fal.ai API Key** (video generation): https://fal.ai/dashboard/keys
- Edge-TTS, Whisper, FFmpeg, yt-dlp: all free, installed automatically in Colab
