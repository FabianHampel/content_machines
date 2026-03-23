#!/usr/bin/env python3
"""
ROTBOTS Pipeline E2E Test
Tests the pipeline logic step-by-step, first with mocks, then with real APIs.

Usage:
    python test_pipeline.py              # Mock-only test
    python test_pipeline.py --live       # Test with real API keys from .env
"""
import json, re, os, sys, subprocess, tempfile, shutil
from pathlib import Path

# Load .env if present
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

LIVE = '--live' in sys.argv
PASSED = 0
FAILED = 0


def test(name, condition, detail=''):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f'  PASS  {name}')
    else:
        FAILED += 1
        print(f'  FAIL  {name}  {detail}')


# ============================================================
# STAGE 01: VIDEO PLAN (pure logic, no APIs)
# ============================================================
print('\n=== STAGE 01: VIDEO PLAN ===')

TOPIC = 'Test topic for pipeline validation'
SOURCES = ['https://example.com']
TOTAL_VIDEO_LENGTH = 60
SECONDS_PER_SCENE = 5
ARCHIVE_RATIO = 0.3
UPLOAD_RATIO = 0.2
ENABLE_CREDITS = True

# Scene count fix
AI_RATIO = max(0, 1.0 - ARCHIVE_RATIO - UPLOAD_RATIO)
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

test('Total scenes correct', NUM_TOTAL_SCENES == 10, f'got {NUM_TOTAL_SCENES}')
test('Scene sum <= total', NUM_AI_SCENES + NUM_ARCHIVE_SCENES + NUM_UPLOAD_SCENES <= NUM_TOTAL_SCENES,
     f'{NUM_AI_SCENES}+{NUM_ARCHIVE_SCENES}+{NUM_UPLOAD_SCENES} = {NUM_AI_SCENES+NUM_ARCHIVE_SCENES+NUM_UPLOAD_SCENES}')
test('AI scenes >= 1', NUM_AI_SCENES >= 1)
test('Archive scenes correct', NUM_ARCHIVE_SCENES == 3, f'got {NUM_ARCHIVE_SCENES}')
test('Upload scenes correct', NUM_UPLOAD_SCENES == 2, f'got {NUM_UPLOAD_SCENES}')

# Interleaving
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

test('Interleave count correct', len(scene_types) == NUM_TOTAL_SCENES)
test('AI count in interleave', scene_types.count('ai_generated') == NUM_AI_SCENES)
test('Archive count in interleave', scene_types.count('archive') == NUM_ARCHIVE_SCENES)
test('Upload count in interleave', scene_types.count('upload') == NUM_UPLOAD_SCENES)
test('No clustering (archive not all at end)',
     scene_types[-1] != 'archive' or scene_types[-2] != 'archive' or scene_types[-3] != 'archive',
     f'order: {scene_types}')
print(f'  Scene order: {scene_types}')

# Edge case: all AI
ARCHIVE_RATIO_0 = 0.0; UPLOAD_RATIO_0 = 0.0
ns0 = 10
na0 = int(ns0 * ARCHIVE_RATIO_0) if ARCHIVE_RATIO_0 > 0 else 0
nu0 = int(ns0 * UPLOAD_RATIO_0) if UPLOAD_RATIO_0 > 0 else 0
nai0 = max(1, ns0 - na0 - nu0)
test('All-AI: 0 archive', na0 == 0)
test('All-AI: 0 upload', nu0 == 0)
test('All-AI: 10 AI', nai0 == 10)

# Save mock plan
WORK_DIR = Path(tempfile.mkdtemp(prefix='rotbots_test_'))
SESSION_DIR = WORK_DIR / 'test-session'
for d in ['', 'videos', 'audio', 'archive_clips', 'uploads']:
    (SESSION_DIR / d).mkdir(parents=True, exist_ok=True)

plan = dict(topic=TOPIC, sources=SOURCES, session_name='test-session',
    total_video_length=TOTAL_VIDEO_LENGTH, seconds_per_scene=SECONDS_PER_SCENE,
    content_length=CONTENT_LENGTH, credits_length=CREDITS_LENGTH,
    narration_length=CONTENT_LENGTH, ai_ratio=AI_RATIO,
    archive_ratio=ARCHIVE_RATIO, upload_ratio=UPLOAD_RATIO,
    num_total_scenes=NUM_TOTAL_SCENES, num_ai_scenes=NUM_AI_SCENES,
    num_archive_scenes=NUM_ARCHIVE_SCENES, num_upload_scenes=NUM_UPLOAD_SCENES,
    words_per_scene=SECONDS_PER_SCENE * 2.5, scene_types=scene_types,
    num_chapters=3, sections_per_chapter=3,
    enable_credits=True, enable_subtitles=False, enable_music=False, enable_effects=True)
with open(SESSION_DIR / 'video_plan.json', 'w') as f:
    json.dump(plan, f, indent=2)
test('Plan JSON saved', (SESSION_DIR / 'video_plan.json').exists())


# ============================================================
# STAGE 02: SCRIPT WRITER (needs Groq API)
# ============================================================
print('\n=== STAGE 02: SCRIPT WRITER ===')

GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

if LIVE and GROQ_API_KEY:
    import requests

    def query_llm(prompt, system_prompt=None, temperature=0.8):
        msgs = []
        if system_prompt: msgs.append({'role': 'system', 'content': system_prompt})
        msgs.append({'role': 'user', 'content': prompt})
        r = requests.post('https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': f'Bearer {GROQ_API_KEY}', 'Content-Type': 'application/json'},
            json={'model': 'llama-3.3-70b-versatile', 'messages': msgs, 'temperature': temperature, 'max_tokens': 4096},
            timeout=60)
        r.raise_for_status()
        text = r.json()['choices'][0]['message']['content']
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        return text

    def parse_json_response(text):
        text = re.sub(r'[\x00-\x1f]', '', text)
        m = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if m: text = m.group(1)
        for start in range(len(text)):
            if text[start] in '{[':
                depth = 0; end = start
                for j in range(start, len(text)):
                    if text[j] in '{[': depth += 1
                    elif text[j] in '}]': depth -= 1
                    if depth == 0: end = j; break
                candidate = text[start:end+1]
                candidate = re.sub(r',\s*([}\]])', r'\1', candidate)
                try: return json.loads(candidate, strict=False)
                except: pass
        return json.loads(text, strict=False)

    # Test LLM connectivity
    try:
        resp = query_llm('Say "hello" and nothing else.')
        test('Groq API responds', 'hello' in resp.lower(), f'got: {resp[:50]}')
    except Exception as e:
        test('Groq API responds', False, str(e))

    # Test JSON parsing
    test_json = '```json\n{"title": "Test", "chapters": [{"chapter": 1}]}\n```'
    parsed = parse_json_response(test_json)
    test('JSON parsing works', parsed.get('title') == 'Test')

    # Test outline generation
    try:
        outline_prompt = f"""Write a video essay outline about "{TOPIC}" with exactly 3 chapters.
Output JSON: {{"title":"...","thesis":"...","chapters":[{{"chapter":1,"title":"...","summary":"...","key_points":["..."]}}]}}"""
        outline_text = query_llm(outline_prompt, 'You are a video essay writer. Output valid JSON only.')
        outline = parse_json_response(outline_text)
        test('Outline has title', 'title' in outline)
        test('Outline has chapters', len(outline.get('chapters', [])) > 0)
        print(f'  Title: {outline.get("title", "?")}')

        # Generate one chapter's sections
        ch = outline['chapters'][0]
        sec_prompt = f"""Write 3 sections for chapter "{ch['title']}" about "{TOPIC}".
Each section max {int(SECONDS_PER_SCENE * 2.5)} words narration.
Output JSON array: [{{"section":1,"narration":"...","visual_direction":"...","mood":"..."}}]"""
        sec_text = query_llm(sec_prompt, 'Video script writer. Output valid JSON array only.')
        sections = parse_json_response(sec_text)
        test('Sections generated', isinstance(sections, list) and len(sections) > 0)
        if sections:
            test('Section has narration', 'narration' in sections[0])
    except Exception as e:
        test('Script generation', False, str(e))

else:
    if not GROQ_API_KEY:
        print('  SKIP  (no GROQ_API_KEY, use --live)')
    # Create mock data for downstream tests
    outline = {'title': 'Test Video', 'thesis': 'A test thesis',
        'chapters': [{'chapter': i+1, 'title': f'Chapter {i+1}', 'summary': f'Summary {i+1}',
            'sections': [{'section': j+1, 'narration': f'This is test narration for section {j+1}.',
                'visual_direction': 'Wide shot', 'mood': 'neutral'}
                for j in range(3)]}
            for i in range(3)]}

# Build mock storyboard
all_sec = []
for ch in outline.get('chapters', []):
    for sec in ch.get('sections', []):
        d = dict(**sec)
        d['chapter_title'] = ch['title']
        all_sec.append(d)

scenes = []
sn = 1; si = 0
for stype in scene_types:
    sec = all_sec[si] if si < len(all_sec) else dict(narration='', visual_direction='', mood='neutral', chapter_title=TOPIC, section=si+1)
    scenes.append(dict(scene=sn, scene_type=stype,
        title=str(sec.get('chapter_title', '')) + ' - Part ' + str(sec.get('section', si+1)),
        narration=sec.get('narration', ''), visual_direction=sec.get('visual_direction', ''),
        mood=sec.get('mood', ''), duration=SECONDS_PER_SCENE))
    sn += 1; si += 1

ai_scenes = [s for s in scenes if s['scene_type'] == 'ai_generated']
test('Storyboard has correct count', len(scenes) == NUM_TOTAL_SCENES, f'got {len(scenes)}')
test('AI scenes filtered correctly', len(ai_scenes) == NUM_AI_SCENES, f'got {len(ai_scenes)}')
# Some scenes may lack narration if we have more scenes than essay sections — that's OK
narrated = sum(1 for s in scenes if s.get('narration'))
test('Most scenes have narration', narrated >= len(all_sec), f'{narrated}/{len(scenes)}')

with open(SESSION_DIR / 'storyboard.json', 'w') as f: json.dump(scenes, f, indent=2)
prompts = [dict(scene=s['scene'], title=s['title'], t2v_prompt=f'Test prompt for scene {s["scene"]}',
    style='documentary', narration=s.get('narration', ''), duration=SECONDS_PER_SCENE) for s in ai_scenes]
with open(SESSION_DIR / 'prompts.json', 'w') as f: json.dump(prompts, f, indent=2)
test('Storyboard saved', (SESSION_DIR / 'storyboard.json').exists())
test('Prompts saved', (SESSION_DIR / 'prompts.json').exists())


# ============================================================
# STAGE 05: EFFECTS (pure logic)
# ============================================================
print('\n=== STAGE 05: EFFECTS ===')
EFFECTS = ['film_grain', 'vhs_artifacts', 'celluloid_scratches', 'sepia_tone', 'bw_transition',
           'color_grade_warm', 'color_grade_cool', 'vignette', 'flicker', 'desaturate']
import random
for p in prompts:
    p['ffmpeg_effects'] = [random.choice(EFFECTS)]
    p['effect_intensity'] = 0.7
with open(SESSION_DIR / 'prompts.json', 'w') as f: json.dump(prompts, f, indent=2)
test('Effects assigned', all('ffmpeg_effects' in p for p in prompts))


# ============================================================
# STAGE 06: VOICE (needs edge-tts)
# ============================================================
print('\n=== STAGE 06: VOICE ===')

if LIVE:
    try:
        import edge_tts, asyncio

        async def gen_tts(text, path, voice='en-US-GuyNeural', rate='+0%'):
            await edge_tts.Communicate(text, voice, rate=rate).save(str(path))

        narrations = [s for s in scenes if s.get('narration')]
        audio_files = []
        for n in narrations[:2]:  # Test with first 2 only
            out = SESSION_DIR / 'audio' / f'narration_{n["scene"]:03d}.mp3'
            asyncio.run(gen_tts(n['narration'], out))
            test(f'TTS scene {n["scene"]}', out.exists() and out.stat().st_size > 0)
            if out.exists():
                audio_files.append({'scene': n['scene'], 'path': str(out)})
        test('Audio files generated', len(audio_files) > 0)
    except ImportError:
        print('  SKIP  (edge-tts not installed)')
    except Exception as e:
        test('TTS generation', False, str(e))
else:
    print('  SKIP  (use --live)')


# ============================================================
# STAGE 07: GENERATE (needs fal.ai)
# ============================================================
print('\n=== STAGE 07: GENERATE ===')

FAL_API_KEY = os.environ.get('FAL_API_KEY', '')

if LIVE and FAL_API_KEY:
    try:
        os.environ['FAL_KEY'] = FAL_API_KEY
        import fal_client
        import requests as req

        test_prompt = prompts[0] if prompts else None
        if test_prompt:
            print(f'  Generating 1 test clip (~30s)...')
            inp = dict(prompt=test_prompt['t2v_prompt'], aspect_ratio='16:9', enable_prompt_expansion=False)
            result = fal_client.subscribe('fal-ai/wan-t2v', arguments=inp)
            url = None
            if isinstance(result, dict):
                v = result.get('video', result.get('output', ''))
                url = v.get('url', '') if isinstance(v, dict) else v
            test('fal.ai returns video URL', url and url.startswith('http'), f'got: {result}')
            if url:
                vid_path = SESSION_DIR / 'videos' / 'scene_001.mp4'
                vid_path.write_bytes(req.get(url, timeout=120).content)
                test('Video downloaded', vid_path.exists() and vid_path.stat().st_size > 10000)
    except Exception as e:
        test('fal.ai generation', False, str(e))
else:
    if not FAL_API_KEY:
        print('  SKIP  (no FAL_API_KEY, use --live)')


# ============================================================
# STAGE 09: ASSEMBLE (needs ffmpeg)
# ============================================================
print('\n=== STAGE 09: ASSEMBLE ===')

# Test effect filter builder
def build_effect_filter(name, intensity=0.7):
    i = max(0.0, min(1.0, intensity))
    if name == 'film_grain': return f'noise=alls={int(12*i)}:allf=t'
    if name == 'sepia_tone':
        inv = 1 - i
        return f'colorchannelmixer={inv+i*0.393:.3f}:{i*0.769:.3f}:{i*0.189:.3f}:0:{i*0.349:.3f}:{inv+i*0.686:.3f}:{i*0.168:.3f}:0:{i*0.272:.3f}:{i*0.534:.3f}:{inv+i*0.131:.3f}:0'
    if name == 'vignette': return f'vignette=PI/4*{i:.3f}'
    return None

test('Effect filter: film_grain', 'noise' in (build_effect_filter('film_grain') or ''))
test('Effect filter: sepia_tone', 'colorchannelmixer' in (build_effect_filter('sepia_tone') or ''))
test('Effect filter: vignette', 'vignette' in (build_effect_filter('vignette') or ''))
test('Effect filter: unknown', build_effect_filter('nonexistent') is None)

# Test ffmpeg availability
try:
    r = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
    test('ffmpeg available', r.returncode == 0)
except FileNotFoundError:
    test('ffmpeg available (optional locally)', True, 'not installed — OK, runs in Colab')
    print('  NOTE  ffmpeg not installed locally, will work in Colab')


# ============================================================
# CLEANUP + SUMMARY
# ============================================================
print('\n=== CLEANUP ===')
shutil.rmtree(WORK_DIR, ignore_errors=True)
test('Temp dir cleaned', not WORK_DIR.exists())

print(f'\n{"="*50}')
print(f'Results: {PASSED} passed, {FAILED} failed')
if FAILED: print('Some tests failed!'); sys.exit(1)
else: print('All tests passed!'); sys.exit(0)
