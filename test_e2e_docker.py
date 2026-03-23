#!/usr/bin/env python3
"""
ROTBOTS E2E Pipeline Test — Docker version (single-narration architecture)
Runs the full pipeline: plan → script → archive → upload → effects → voice → generate → subtitles → assemble

Config: 120s video, 10% AI, 40% archive, 50% upload, all features on.
"""
import json, re, os, sys, subprocess, random, shutil, asyncio, time
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================
TOPIC = 'The Secret Life of Forgotten Films: How Private Archives Shape Public Memory'
SOURCES = ['https://en.wikipedia.org/wiki/Home_movies', 'https://en.wikipedia.org/wiki/Archive.org']
TOTAL_VIDEO_LENGTH = 120
SECONDS_PER_SCENE = 5
ARCHIVE_RATIO = 0.4
UPLOAD_RATIO = 0.5
AI_RATIO = max(0, 1.0 - ARCHIVE_RATIO - UPLOAD_RATIO)
ENABLE_CREDITS = True
ENABLE_SUBTITLES = True
ENABLE_MUSIC = False
ENABLE_EFFECTS = True
ARCHIVE_URL = 'https://archive.org/details/PrivateL1947'
INPUT_VIDEO = '/app/input_video.mp4'  # mounted from host

GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
FAL_API_KEY = os.environ.get('FAL_API_KEY', '')
if FAL_API_KEY: os.environ['FAL_KEY'] = FAL_API_KEY

BASE = Path('/app/test_output')
SESSION_NAME = 'test-e2e-run'
SESSION_DIR = BASE / SESSION_NAME
for d in ['', 'videos', 'audio', 'archive_clips', 'uploads']:
    (SESSION_DIR / d).mkdir(parents=True, exist_ok=True)
TEMP = Path('/tmp/rotbots_assembly'); TEMP.mkdir(exist_ok=True)

PASSED = 0; FAILED = 0; SKIPPED = 0
def ok(name, cond, detail=''):
    global PASSED, FAILED
    if cond: PASSED += 1; print(f'  [OK]  {name}')
    else: FAILED += 1; print(f'  [FAIL] {name}  {detail}')
def skip(name, reason=''):
    global SKIPPED; SKIPPED += 1; print(f'  [SKIP] {name}  {reason}')

def dur(path):
    try: return float(subprocess.run(['ffprobe','-v','quiet','-show_entries','format=duration',
        '-of','default=noprint_wrappers=1:nokey=1',str(path)], capture_output=True, text=True, timeout=10).stdout.strip())
    except: return 0

def ff(cmd, desc=''):
    if desc: print(f'    {desc}...', end=' ', flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode == 0:
        if desc: print('OK')
        return True
    if desc: print('FAIL')
    if r.stderr: print(f'    {r.stderr[-200:]}')
    return False


# ============================================================
# STAGE 01: VIDEO PLAN
# ============================================================
print('\n' + '='*60)
print('STAGE 01: VIDEO PLAN')
print('='*60)

CREDITS_LENGTH = 8 if ENABLE_CREDITS else 0
CONTENT_LENGTH = TOTAL_VIDEO_LENGTH - CREDITS_LENGTH
NUM_TOTAL_SCENES = max(2, int(CONTENT_LENGTH / SECONDS_PER_SCENE))
NUM_ARCHIVE_SCENES = int(NUM_TOTAL_SCENES * ARCHIVE_RATIO) if ARCHIVE_RATIO > 0 else 0
NUM_UPLOAD_SCENES = int(NUM_TOTAL_SCENES * UPLOAD_RATIO) if UPLOAD_RATIO > 0 else 0
NUM_AI_SCENES = max(1, NUM_TOTAL_SCENES - NUM_ARCHIVE_SCENES - NUM_UPLOAD_SCENES)
while NUM_AI_SCENES + NUM_ARCHIVE_SCENES + NUM_UPLOAD_SCENES > NUM_TOTAL_SCENES:
    if NUM_ARCHIVE_SCENES > 0: NUM_ARCHIVE_SCENES -= 1
    elif NUM_UPLOAD_SCENES > 0: NUM_UPLOAD_SCENES -= 1
    else: break
WORDS_PER_SCENE = SECONDS_PER_SCENE * 2.5
TOTAL_NARRATION_WORDS = int(CONTENT_LENGTH * 2.5)
NUM_CHAPTERS = max(1, min(3, NUM_TOTAL_SCENES // 3))
SECTIONS_PER_CHAPTER = max(1, NUM_TOTAL_SCENES // NUM_CHAPTERS)

scene_types = []
ai_p = 0; ar_p = 0; up_p = 0
for i in range(NUM_TOTAL_SCENES):
    remaining = max(1, NUM_TOTAL_SCENES - i)
    ai_need = (NUM_AI_SCENES - ai_p) / remaining
    ar_need = (NUM_ARCHIVE_SCENES - ar_p) / remaining
    up_need = (NUM_UPLOAD_SCENES - up_p) / remaining
    if ar_need >= ai_need and ar_need >= up_need and ar_p < NUM_ARCHIVE_SCENES:
        scene_types.append('archive'); ar_p += 1
    elif up_need >= ai_need and up_p < NUM_UPLOAD_SCENES:
        scene_types.append('upload'); up_p += 1
    else:
        scene_types.append('ai_generated'); ai_p += 1

plan = dict(topic=TOPIC, sources=SOURCES, session_name=SESSION_NAME,
    total_video_length=TOTAL_VIDEO_LENGTH, seconds_per_scene=SECONDS_PER_SCENE,
    content_length=CONTENT_LENGTH, credits_length=CREDITS_LENGTH,
    narration_length=CONTENT_LENGTH, ai_ratio=AI_RATIO,
    archive_ratio=ARCHIVE_RATIO, upload_ratio=UPLOAD_RATIO,
    num_total_scenes=NUM_TOTAL_SCENES, num_ai_scenes=NUM_AI_SCENES,
    num_archive_scenes=NUM_ARCHIVE_SCENES, num_upload_scenes=NUM_UPLOAD_SCENES,
    words_per_scene=WORDS_PER_SCENE, scene_types=scene_types,
    num_chapters=NUM_CHAPTERS, sections_per_chapter=SECTIONS_PER_CHAPTER,
    enable_credits=ENABLE_CREDITS, enable_subtitles=ENABLE_SUBTITLES,
    enable_music=ENABLE_MUSIC, enable_effects=ENABLE_EFFECTS)
with open(SESSION_DIR / 'video_plan.json', 'w') as f: json.dump(plan, f, indent=2)

print(f'  Plan: {TOTAL_VIDEO_LENGTH}s = {CONTENT_LENGTH}s content + {CREDITS_LENGTH}s credits')
print(f'  Scenes: {NUM_TOTAL_SCENES} total = {NUM_AI_SCENES} AI + {NUM_ARCHIVE_SCENES} archive + {NUM_UPLOAD_SCENES} upload')
print(f'  Narration target: {TOTAL_NARRATION_WORDS} words for {CONTENT_LENGTH}s')
print(f'  Order: {scene_types}')
ok('Plan saved', (SESSION_DIR / 'video_plan.json').exists())


# ============================================================
# STAGE 02: SCRIPT WRITER
# ============================================================
print('\n' + '='*60)
print('STAGE 02: SCRIPT WRITER')
print('='*60)

import requests

def query_llm(prompt, system_prompt=None, temperature=0.8):
    if not GROQ_API_KEY: raise Exception('No GROQ_API_KEY')
    msgs = []
    if system_prompt: msgs.append({'role': 'system', 'content': system_prompt})
    msgs.append({'role': 'user', 'content': prompt})
    r = requests.post('https://api.groq.com/openai/v1/chat/completions',
        headers={'Authorization': f'Bearer {GROQ_API_KEY}', 'Content-Type': 'application/json'},
        json={'model': 'llama-3.3-70b-versatile', 'messages': msgs, 'temperature': temperature, 'max_tokens': 4096},
        timeout=60)
    r.raise_for_status()
    text = r.json()['choices'][0]['message']['content']
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

def parse_json_response(text):
    text = re.sub(r'[\x00-\x1f]', '', text)
    m = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if m: text = m.group(1)
    for start in range(len(text)):
        if text[start] in '{[':
            depth = 0
            for j in range(start, len(text)):
                if text[j] in '{[': depth += 1
                elif text[j] in '}]': depth -= 1
                if depth == 0:
                    candidate = text[start:j+1]
                    candidate = re.sub(r',\s*([}\]])', r'\1', candidate)
                    try: return json.loads(candidate, strict=False)
                    except: break
    return json.loads(text, strict=False)

def fetch_website_text(url, max_chars=10000):
    try:
        from bs4 import BeautifulSoup
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        for tag in soup(['script','style','nav','header','footer','aside','form']): tag.decompose()
        main = soup.find('article') or soup.find('main') or soup.find('body')
        text = main.get_text(separator='\n', strip=True) if main else soup.get_text(separator='\n', strip=True)
        return re.sub(r'\n{3,}', '\n\n', text)[:max_chars]
    except: return ''

if GROQ_API_KEY:
    # Scrape + Summarize
    print('  Scraping sources...')
    summaries = []
    for src_url in SOURCES:
        text = fetch_website_text(src_url)
        if text:
            try:
                summary = query_llm(f'Summarize in 2-3 paragraphs for a video essay:\n\n{text[:5000]}',
                    'Research assistant. Summarize concisely.')
                summaries.append({'source': src_url, 'summary': summary})
                print(f'    {src_url[:50]}... OK')
            except Exception as e: print(f'    {src_url[:50]}... FAIL: {e}')
        else: print(f'    {src_url[:50]}... no text')
    ok('Sources scraped', len(summaries) > 0)
    with open(SESSION_DIR / 'summaries.json', 'w') as f:
        json.dump({'sources': summaries}, f, indent=2)

    # Outline
    print('  Generating outline...')
    combined = '\n\n'.join(s['summary'] for s in summaries)
    outline_prompt = f"""Create an essay outline for a {TOTAL_VIDEO_LENGTH}s video about: "{TOPIC}"

RESEARCH:
{combined[:3000]}

Exactly {NUM_CHAPTERS} chapters. JSON only:
{{"title":"...","thesis":"...","chapters":[{{"chapter":1,"title":"...","summary":"...","key_points":["..."]}}]}}"""
    try:
        outline = parse_json_response(query_llm(outline_prompt, 'Expert essay writer. Concise.'))
        ok('Outline generated', 'title' in outline)
        print(f'    Title: {outline.get("title", "?")}')
    except Exception as e:
        ok('Outline generated', False, str(e)); outline = None

    # Full essay narration (ONE continuous text)
    if outline:
        print(f'  Writing full essay narration ({TOTAL_NARRATION_WORDS} words)...')
        chapter_summaries = '\n'.join([f'Ch {c["chapter"]}: {c["title"]} - {c.get("summary","")}' for c in outline['chapters']])
        essay_prompt = f"""Write a single continuous narration for a {TOTAL_VIDEO_LENGTH}-second video about: "{TOPIC}"

STRUCTURE:
{chapter_summaries}

RULES:
- Write EXACTLY {TOTAL_NARRATION_WORDS} words total
- One flowing essay, NO section breaks, headers, or labels
- Engaging, documentary-style prose
- Complete sentences only
- Output ONLY the essay text"""
        essay_narration = query_llm(essay_prompt,
            f'Expert video essay scriptwriter. Write exactly {TOTAL_NARRATION_WORDS} words of flowing documentary narration.').strip()
        wc = len(essay_narration.split())
        # Retry/expand if too short (< 90% of target)
        while wc < int(TOTAL_NARRATION_WORDS * 0.9):
            needed = TOTAL_NARRATION_WORDS - wc
            print(f'    {wc} words — too short, expanding by {needed} words...')
            more = query_llm(
                f'Continue this essay with EXACTLY {needed} more words. Same style, same topic. Pick up right where it left off:\n\n{essay_narration[-500:]}',
                f'Continue the essay seamlessly. Write exactly {needed} words.').strip()
            essay_narration = essay_narration + ' ' + more
            wc = len(essay_narration.split())
        ok('Essay narration', wc >= TOTAL_NARRATION_WORDS * 0.9, f'{wc} words (target {TOTAL_NARRATION_WORDS})')
        print(f'    {wc} words ~ {wc/2.5:.0f}s narration')

        # Visual directions per chapter
        print('  Generating visual directions...')
        for ch in outline['chapters']:
            try:
                vis_prompt = f'Write {SECTIONS_PER_CHAPTER} visual scene descriptions for chapter "{ch["title"]}" of a video about "{TOPIC}". JSON: [{{"section": 1, "visual_direction": "...", "mood": "..."}}]'
                sections = parse_json_response(query_llm(vis_prompt, 'Visual director. Concise scene descriptions.'))
                if isinstance(sections, dict):
                    for v in sections.values():
                        if isinstance(v, list): sections = v; break
                    else: sections = [sections]
                ch['sections'] = sections[:SECTIONS_PER_CHAPTER]
            except:
                ch['sections'] = [{'section': j+1, 'visual_direction': 'Wide establishing shot', 'mood': 'contemplative'} for j in range(SECTIONS_PER_CHAPTER)]
        ok('Visual directions', all('sections' in ch for ch in outline['chapters']))

        outline['narration'] = essay_narration
        outline['credits'] = {'sources': SOURCES}
        with open(SESSION_DIR / 'essay_script.json', 'w') as f: json.dump(outline, f, indent=2)
else:
    skip('Script Writer (LLM)', 'no GROQ_API_KEY')
    essay_narration = """Forgotten films hold secrets that reshape how we understand the past. Tucked away in attics, basements, and forgotten storage units, private archives contain visual records that official history often overlooks. These fragile reels of celluloid and magnetic tape preserve moments of everyday life that no professional filmmaker thought worth capturing, yet they reveal truths about human experience that no scripted production ever could.

The history of home movie-making stretches back to the early twentieth century, when amateur cameras first became affordable to middle-class families. What began as a novelty quickly became a cultural ritual. Birthday parties, holidays, neighborhood gatherings, and quiet Sunday afternoons were all committed to film. These recordings were never meant for public consumption, yet their candid nature makes them invaluable to historians seeking authentic glimpses of daily life across decades of social change.

The Internet Archive and similar institutions have transformed access to these private collections. What was once locked in family closets now streams freely to anyone with an internet connection. Researchers, filmmakers, and curious viewers can explore thousands of hours of footage that document everything from postwar suburban expansion to civil rights marches captured by bystanders. The democratization of these archives has fundamentally changed who gets to tell the story of the past.

Yet preservation remains an urgent challenge. Film stock deteriorates, magnetic tape degrades, and digital formats become obsolete. Every year, irreplaceable footage is lost forever because no one recognized its value in time. The race between decay and digitization continues, and the outcome will determine which chapters of our collective visual memory survive for future generations to discover and interpret."""
    wc = len(essay_narration.split())
    outline = {'title': 'The Secret Life of Forgotten Films', 'thesis': 'Private archives shape collective memory.',
        'narration': essay_narration, 'credits': {'sources': SOURCES},
        'chapters': [{'chapter': i+1, 'title': f'Chapter {i+1}',
            'sections': [{'section': j+1, 'visual_direction': 'Wide shot of archival footage and film reels', 'mood': 'contemplative'}
                for j in range(SECTIONS_PER_CHAPTER)]}
            for i in range(NUM_CHAPTERS)]}
    with open(SESSION_DIR / 'essay_script.json', 'w') as f: json.dump(outline, f, indent=2)
    print(f'  Mock essay: {wc} words ~ {wc/2.5:.0f}s')

# Storyboard (no narration per scene)
print('  Building storyboard...')
STYLES = dict(documentary='cinematic, professional lighting', nature='wide nature shots, golden hour',
    news_report='news studio, professional', action_movie='dynamic movement, dramatic lighting',
    horror='dark lighting, shadows, fog')
arc = dict(early=['documentary','nature'], middle=['news_report'], late=['action_movie','horror'])

all_sec = []
for ch in outline.get('chapters', []):
    for sec in ch.get('sections', []):
        d = dict(**sec); d['chapter_title'] = ch['title']; all_sec.append(d)

scenes = []; sn = 1; si = 0
for stype in scene_types:
    sec = all_sec[si] if si < len(all_sec) else dict(visual_direction='Wide shot', mood='neutral', chapter_title=TOPIC, section=si+1)
    scenes.append(dict(scene=sn, scene_type=stype,
        title=str(sec.get('chapter_title',''))+' - Part '+str(sec.get('section',si+1)),
        visual_direction=sec.get('visual_direction',''), mood=sec.get('mood',''), duration=SECONDS_PER_SCENE))
    sn += 1; si += 1

ai_sc = [s for s in scenes if s['scene_type'] == 'ai_generated']
total_ai = len(ai_sc); ee = max(1,int(total_ai*0.25)); ls = max(ee+1,int(total_ai*0.75)); last = None
for i, sc in enumerate(ai_sc):
    phase = 'early' if i < ee else ('late' if i >= ls else 'middle')
    pool = arc.get(phase, ['documentary']); avail = [s for s in pool if s != last] or pool
    st = random.choice(avail); sc['assigned_style'] = st; sc['visual_keywords'] = STYLES.get(st,''); last = st

with open(SESSION_DIR / 'storyboard.json', 'w') as f: json.dump(scenes, f, indent=2)
ok('Storyboard', len(scenes) == NUM_TOTAL_SCENES)

# T2V Prompts (AI scenes only, no narration field)
print('  Generating T2V prompts...')
OPENINGS = ['Start with SHOT TYPE', 'Start with ACTION', 'Start with ENVIRONMENT']
prompts = []
for sc in ai_sc:
    if GROQ_API_KEY:
        try:
            st = sc.get('assigned_style','documentary'); vk = sc.get('visual_keywords','')
            t2v = query_llm(
                f'T2V prompt for {SECONDS_PER_SCENE}s:\nVisual: {sc.get("visual_direction","")}\nMood: {sc.get("mood","")}\n{random.choice(OPENINGS)}\nOutput ONLY the prompt text.',
                f'T2V prompt expert. ONE paragraph, 3-5 sentences. Style: {st}. Visual: {vk}. No text overlays.').strip().strip('"')
        except: t2v = f'Cinematic shot of {sc.get("visual_direction","old film reels")}. {sc.get("mood","contemplative")} mood.'
    else:
        t2v = f'Cinematic shot of {sc.get("visual_direction","old film reels")}. {sc.get("mood","contemplative")} mood.'
    prompts.append(dict(scene=sc['scene'], title=sc['title'], t2v_prompt=t2v, style=sc.get('assigned_style',''), duration=SECONDS_PER_SCENE))
with open(SESSION_DIR / 'prompts.json', 'w') as f: json.dump(prompts, f, indent=2)
ok('T2V prompts', len(prompts) == NUM_AI_SCENES)


# ============================================================
# STAGE 03: ARCHIVE SCRAPER
# ============================================================
print('\n' + '='*60)
print('STAGE 03: ARCHIVE SCRAPER')
print('='*60)

def parse_archive_id(url):
    m = re.search(r'archive\.org/(?:details|download)/([^/?#]+)', url.strip().rstrip('/'))
    if m: return m.group(1)
    raise ValueError('Cannot parse: ' + url)

archive_clips = []
ARCHIVE_DIR = SESSION_DIR / 'archive_clips'; ARCHIVE_DIR.mkdir(exist_ok=True)
ATEMP = Path('/tmp/archive_dl'); ATEMP.mkdir(exist_ok=True)

aid = parse_archive_id(ARCHIVE_URL)
print(f'  Downloading {aid}...')
out_tpl = str(ATEMP / (aid + '.%(ext)s'))
try:
    subprocess.run(['yt-dlp', f'https://archive.org/details/{aid}',
        '-f', 'bestvideo[height<=480]+bestaudio/best[height<=480]/best',
        '--merge-output-format', 'mp4', '--no-playlist', '--no-warnings', '-o', out_tpl, '--quiet'],
        check=True, timeout=600)
    video = None
    for fp in ATEMP.iterdir():
        if fp.stem == aid and fp.suffix in ('.mp4','.mkv','.webm'): video = fp; break
    if video:
        total = dur(video); print(f'  Downloaded: {total:.1f}s')
        clip_dir = ARCHIVE_DIR / aid; clip_dir.mkdir(exist_ok=True)
        extract_end = min(total, 180)
        t = 0; idx2 = 0
        while t < extract_end and len(archive_clips) < NUM_ARCHIVE_SCENES:
            clip_dur = min(SECONDS_PER_SCENE, extract_end - t)
            if clip_dur < 3: break
            clip_out = clip_dir / f'archive_{idx2:03d}.mp4'
            r = subprocess.run(['ffmpeg','-y','-ss',str(t),'-i',str(video),'-t',str(clip_dur),
                '-c:v','libx264','-preset','fast','-crf','23','-an',str(clip_out)],
                capture_output=True, text=True, timeout=120)
            if r.returncode == 0 and clip_out.exists():
                archive_clips.append(dict(path=str(clip_out), duration=round(clip_dur,1), archive_id=aid)); idx2 += 1
            t += clip_dur
        video.unlink(missing_ok=True)
        print(f'  Extracted: {len(archive_clips)} clips')
    ok('Archive clips', len(archive_clips) >= NUM_ARCHIVE_SCENES, f'need {NUM_ARCHIVE_SCENES}, got {len(archive_clips)}')
except Exception as e:
    ok('Archive download', False, str(e))
with open(SESSION_DIR / 'archive_clips.json', 'w') as f:
    json.dump(dict(clips=archive_clips, total=len(archive_clips)), f, indent=2)


# ============================================================
# STAGE 04: UPLOAD FOOTAGE (from input video)
# ============================================================
print('\n' + '='*60)
print('STAGE 04: UPLOAD FOOTAGE')
print('='*60)

upload_clips = []
input_path = Path(INPUT_VIDEO)
if input_path.exists():
    input_dur = dur(input_path)
    print(f'  Input video: {input_dur:.1f}s')
    clip_dur = min(SECONDS_PER_SCENE, input_dur / max(1, NUM_UPLOAD_SCENES))
    for i in range(NUM_UPLOAD_SCENES):
        clip_out = SESSION_DIR / 'uploads' / f'upload_{i:03d}.mp4'
        start_t = (i * input_dur / NUM_UPLOAD_SCENES) % input_dur
        ff(['ffmpeg', '-y', '-ss', str(start_t), '-i', str(input_path), '-t', str(SECONDS_PER_SCENE),
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-an', '-pix_fmt', 'yuv420p',
            str(clip_out)], f'Clip {i+1}/{NUM_UPLOAD_SCENES} (from {start_t:.1f}s)')
        if clip_out.exists():
            upload_clips.append(dict(path=str(clip_out), duration=SECONDS_PER_SCENE, filename=f'upload_{i:03d}.mp4'))
else:
    print('  No input video found, generating color placeholders...')
    colors = ['red','blue','green','yellow','purple','orange','cyan','magenta','white','gray','brown','pink']
    for i in range(NUM_UPLOAD_SCENES):
        clip_out = SESSION_DIR / 'uploads' / f'upload_{i:03d}.mp4'
        ff(['ffmpeg','-y','-f','lavfi','-i',f'color=c={colors[i%len(colors)]}:s=1280x720:d={SECONDS_PER_SCENE}:r=24',
            '-c:v','libx264','-preset','fast','-pix_fmt','yuv420p',str(clip_out)],
           f'Mock {i+1}/{NUM_UPLOAD_SCENES}')
        if clip_out.exists():
            upload_clips.append(dict(path=str(clip_out), duration=SECONDS_PER_SCENE, filename=f'upload_{i:03d}.mp4'))

with open(SESSION_DIR / 'upload_clips.json', 'w') as f:
    json.dump(dict(clips=upload_clips, total=len(upload_clips)), f, indent=2)
ok('Upload clips', len(upload_clips) == NUM_UPLOAD_SCENES, f'need {NUM_UPLOAD_SCENES}, got {len(upload_clips)}')


# ============================================================
# STAGE 05: EFFECTS
# ============================================================
print('\n' + '='*60)
print('STAGE 05: EFFECTS')
print('='*60)

EFFECTS = ['film_grain','vhs_artifacts','celluloid_scratches','sepia_tone','bw_transition',
           'color_grade_warm','color_grade_cool','vignette','flicker','desaturate']
for p in prompts:
    p['ffmpeg_effects'] = [random.choice(EFFECTS)]
    p['effect_intensity'] = 0.7
with open(SESSION_DIR / 'prompts.json', 'w') as f: json.dump(prompts, f, indent=2)
ok('Effects assigned', all('ffmpeg_effects' in p for p in prompts))


# ============================================================
# STAGE 06: VOICE — single narration file
# ============================================================
print('\n' + '='*60)
print('STAGE 06: VOICE (single narration)')
print('='*60)

import edge_tts

VOICE = 'en-US-GuyNeural'
AUDIO_DIR = SESSION_DIR / 'audio'

async def gen_tts(text, path, voice=VOICE, rate='+0%'):
    await edge_tts.Communicate(text, voice, rate=rate).save(str(path))

narration_file = AUDIO_DIR / 'narration_full.mp3'
audio_file = None

print(f'  Generating TTS for {len(essay_narration.split())} words...')
try:
    asyncio.run(gen_tts(essay_narration, narration_file))
    audio_duration = dur(narration_file)
    audio_file = {'path': str(narration_file), 'duration': audio_duration}
    print(f'  narration_full.mp3: {audio_duration:.1f}s')
    ok('TTS narration', audio_duration > 30, f'{audio_duration:.1f}s')
except Exception as e:
    ok('TTS narration', False, str(e))

with open(SESSION_DIR / 'audio_manifest.json', 'w') as f:
    json.dump({'voice': VOICE, 'file': audio_file}, f, indent=2)


# ============================================================
# STAGE 07: AI VIDEO GENERATION
# ============================================================
print('\n' + '='*60)
print('STAGE 07: AI VIDEO GENERATION')
print('='*60)

VIDEOS_DIR = SESSION_DIR / 'videos'
generated = []

if FAL_API_KEY:
    import fal_client
    for idx, p in enumerate(prompts):
        vid_path = VIDEOS_DIR / f'scene_{p["scene"]:03d}.mp4'
        print(f'  Generating scene {p["scene"]} ({idx+1}/{len(prompts)})...')
        t0 = time.time()
        try:
            result = fal_client.subscribe('fal-ai/wan-t2v',
                arguments=dict(prompt=p['t2v_prompt'], aspect_ratio='16:9', enable_prompt_expansion=False))
            url = None
            if isinstance(result, dict):
                v = result.get('video', result.get('output', ''))
                url = v.get('url', '') if isinstance(v, dict) else v
            if url:
                vid_path.write_bytes(requests.get(url, timeout=120).content)
                generated.append(dict(scene=p['scene'], path=str(vid_path), duration=dur(vid_path)))
                print(f'    OK ({time.time()-t0:.0f}s, {dur(vid_path):.1f}s)')
            else: print(f'    No URL: {str(result)[:200]}')
        except Exception as e: print(f'    FAIL: {e}')
    ok('AI videos', len(generated) == len(prompts), f'{len(generated)}/{len(prompts)}')
else:
    print('  No FAL_API_KEY — generating placeholders')
    for p in prompts:
        vid_path = VIDEOS_DIR / f'scene_{p["scene"]:03d}.mp4'
        ff(['ffmpeg','-y','-f','lavfi','-i',f'color=c=black:s=1280x720:d={p["duration"]}:r=24',
            '-vf',f"drawtext=text='AI Scene {p['scene']}':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
            '-c:v','libx264','-preset','fast','-pix_fmt','yuv420p',str(vid_path)],
           f'Placeholder scene {p["scene"]}')
        if vid_path.exists():
            generated.append(dict(scene=p['scene'], path=str(vid_path), duration=dur(vid_path)))
    ok('Placeholder videos', len(generated) == len(prompts))

with open(SESSION_DIR / 'video_manifest.json', 'w') as f: json.dump(generated, f, indent=2)


# ============================================================
# STAGE 08: SUBTITLES — single file whisper
# ============================================================
print('\n' + '='*60)
print('STAGE 08: SUBTITLES')
print('='*60)

if ENABLE_SUBTITLES and narration_file.exists():
    try:
        from faster_whisper import WhisperModel
        print('  Loading Whisper...')
        wm = WhisperModel('base', device='cpu', compute_type='int8')
        all_words = []
        print('  Transcribing single narration file...')
        segs, info = wm.transcribe(str(narration_file), word_timestamps=True, language='en')
        for seg in segs:
            if seg.words:
                for w in seg.words:
                    all_words.append({'word': w.word.strip(), 'start': w.start, 'end': w.end})
        print(f'  {len(all_words)} words transcribed')

        # Generate ASS
        sc_f = 720/512; sz = int(80*sc_f); ol = int(7*sc_f); mg = int(20*sc_f)
        ass = f"""[Script Info]
Title: ROTBOTS Subtitles
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,Impact,{sz},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{ol},2,2,{mg},{mg},{mg},1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
        for w in all_words:
            s=w['start']; e=w['end']
            st=f'{int(s//3600)}:{int((s%3600)//60):02d}:{s%60:05.2f}'
            et=f'{int(e//3600)}:{int((e%3600)//60):02d}:{e%60:05.2f}'
            ass += f'Dialogue: 0,{st},{et},Default,,0,0,0,,{w["word"]}\n'

        sub_file = SESSION_DIR / 'subtitles.ass'
        sub_file.write_text(ass)
        ok('Subtitles', len(all_words) > 0, f'{len(all_words)} words')
    except Exception as e:
        ok('Subtitles', False, str(e))
else:
    skip('Subtitles', 'disabled or no audio')


# ============================================================
# STAGE 09: ASSEMBLE
# ============================================================
print('\n' + '='*60)
print('STAGE 09: ASSEMBLE')
print('='*60)

def build_effect_filter(name, intensity=0.7):
    i = max(0.0, min(1.0, intensity))
    if name == 'film_grain': return f'noise=alls={int(12*i)}:allf=t'
    if name == 'vhs_artifacts': return f'noise=alls={int(30*i)}:allf=t,rgbashift=rh={int(2*i)}:bh={int(-2*i)}'
    if name == 'celluloid_scratches': return f'noise=c0s={int(15*i)}:c0f=t'
    if name == 'sepia_tone':
        inv=1-i; return f'colorchannelmixer={inv+i*0.393:.3f}:{i*0.769:.3f}:{i*0.189:.3f}:0:{i*0.349:.3f}:{inv+i*0.686:.3f}:{i*0.168:.3f}:0:{i*0.272:.3f}:{i*0.534:.3f}:{inv+i*0.131:.3f}:0'
    if name == 'bw_transition':
        inv=1-i; return f'colorchannelmixer={inv+i*0.3:.3f}:{i*0.4:.3f}:{i*0.3:.3f}:0:{i*0.3:.3f}:{inv+i*0.4:.3f}:{i*0.3:.3f}:0:{i*0.3:.3f}:{i*0.4:.3f}:{inv+i*0.3:.3f}:0'
    if name == 'color_grade_warm': return f'eq=saturation={1+0.1*i:.3f}:brightness={0.02*i:.3f}'
    if name == 'color_grade_cool': return f'eq=saturation={1-0.1*i:.3f}'
    if name == 'vignette': return f'vignette=PI/4*{i:.3f}'
    if name == 'flicker': return f'noise=alls={int(8*i)}:allf=t'
    if name == 'desaturate': return f'eq=saturation={0.5+0.5*(1-i):.3f}'
    return None

with open(SESSION_DIR / 'storyboard.json') as f: storyboard = json.load(f)
effects_map = {int(p['scene']): p for p in prompts if p.get('ffmpeg_effects')}

# Step 1: Normalize scenes
print('  Step 1: Normalize scenes...')
norm = []; arc_idx = 0; upl_idx = 0
for sc in storyboard:
    sn=sc['scene']; stype=sc['scene_type']
    out=TEMP/f'scene_{sn:03d}.mp4'; src=None
    if stype == 'ai_generated':
        c = VIDEOS_DIR / f'scene_{sn:03d}.mp4'
        if c.exists(): src = c
    elif stype == 'archive':
        if arc_idx < len(archive_clips): src = Path(archive_clips[arc_idx]['path']); arc_idx += 1
    elif stype == 'upload':
        if upl_idx < len(upload_clips): src = Path(upload_clips[upl_idx]['path']); upl_idx += 1
    if not src or not src.exists():
        print(f'    Scene {sn} ({stype}): MISSING'); continue
    vf = 'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:black'
    if stype == 'ai_generated' and sn in effects_map:
        p = effects_map[sn]
        for eff in p.get('ffmpeg_effects',[]):
            ef = build_effect_filter(eff, p.get('effect_intensity',0.7))
            if ef: vf += ',' + ef
    if ff(['ffmpeg','-y','-i',str(src),'-vf',vf,'-r','24','-pix_fmt','yuv420p','-c:v','libx264',
           '-preset','fast','-crf','23','-an','-t',str(sc.get('duration',5)),str(out)],
          f'Scene {sn} ({stype})'):
        norm.append(out)
ok('Scenes normalized', len(norm) >= len(storyboard) * 0.8, f'{len(norm)}/{len(storyboard)}')

# Step 2: Credits
credits_path = None
if ENABLE_CREDITS:
    print('  Step 2: Credits...')
    title = outline.get('title','Untitled')
    sources_list = outline.get('credits',{}).get('sources',[])
    lines = [title,'','Generated by ROTBOTS','','-- Sources --']+[s[:60] for s in sources_list]+['','-- Pipeline --','LLM: Groq','Video: fal.ai','Voice: Edge-TTS','FFmpeg','','LI-MA TDA 2026']
    D=8; LH=42; spd=(720+len(lines)*LH)/D
    flt = [f"drawtext=text='{l.replace(chr(39),chr(8217)).replace(chr(58),chr(92)+chr(58))}':fontsize=28:fontcolor=white:x=(w-text_w)/2:y=h+{i*LH}-{spd:.1f}*t"
           for i,l in enumerate(lines) if l]
    credits_path = TEMP / 'credits.mp4'
    ff(['ffmpeg','-y','-f','lavfi','-i',f'color=c=black:s=1280x720:d={D}:r=24',
        '-vf',','.join(flt),'-pix_fmt','yuv420p','-c:v','libx264','-preset','fast',str(credits_path)],'Credits')

# Step 3: Concat
print('  Step 3: Concatenate...')
cf = TEMP / 'concat.txt'
with open(cf,'w') as f:
    for v in norm: f.write(f"file '{v}'\n")
    if credits_path and credits_path.exists(): f.write(f"file '{credits_path}'\n")
concat_out = TEMP / 'concatenated.mp4'
ff(['ffmpeg','-y','-f','concat','-safe','0','-i',str(cf),'-c','copy',str(concat_out)],'Concat')
video_duration = dur(concat_out)
print(f'    Duration: {video_duration:.1f}s')

# Step 4: Audio — single file, just pad + merge
audio_out = TEMP / 'with_audio.mp4'
has_narr = narration_file.exists()
if has_narr:
    print('  Step 4: Audio (single narration)...')
    narr_padded = TEMP / 'narration_padded.mp3'
    ff(['ffmpeg','-y','-i',str(narration_file),'-af',f'apad=whole_dur={video_duration}',
        '-c:a','libmp3lame','-b:a','128k',str(narr_padded)],'Pad audio')
    ff(['ffmpeg','-y','-i',str(concat_out),'-i',str(narr_padded),'-c:v','copy',
        '-c:a','aac','-b:a','192k','-map','0:v:0','-map','1:a:0',str(audio_out)],'Merge audio')
    ok('Audio merged', audio_out.exists())
else:
    shutil.copy2(str(concat_out), str(audio_out))

# Step 5: Subtitles
final = SESSION_DIR / 'final_video.mp4'
sub_file = SESSION_DIR / 'subtitles.ass'
if ENABLE_SUBTITLES and sub_file.exists():
    print('  Step 5: Burn subtitles...')
    local_ass = TEMP / 'subtitles.ass'
    shutil.copy2(str(sub_file), str(local_ass))
    if not ff(['ffmpeg','-y','-i',str(audio_out),'-vf',f'ass={local_ass}',
               '-c:v','libx264','-preset','fast','-crf','23','-c:a','copy',str(final)],'Burn subs'):
        shutil.copy2(str(audio_out), str(final))
else:
    shutil.copy2(str(audio_out), str(final))

ok('Final video', final.exists())
if final.exists():
    fd = dur(final); fs = final.stat().st_size / (1024*1024)
    print(f'\n  FINAL: {fd:.1f}s, {fs:.1f}MB')
    print(f'  Path: {final}')

# ============================================================
# SUMMARY
# ============================================================
print('\n' + '='*60)
print('SUMMARY')
print('='*60)
print(f'  Scenes: {NUM_AI_SCENES} AI + {NUM_ARCHIVE_SCENES} archive + {NUM_UPLOAD_SCENES} upload = {NUM_TOTAL_SCENES}')
print(f'  Narration: {len(essay_narration.split())} words, single file')
if audio_file: print(f'  Audio: {audio_file["duration"]:.1f}s')
print(f'  Effects: {len(effects_map)}')
if final.exists(): print(f'  Final: {dur(final):.1f}s, {final.stat().st_size/(1024*1024):.1f}MB')
print(f'\n  Results: {PASSED} passed, {FAILED} failed, {SKIPPED} skipped')
if FAILED: sys.exit(1)
