from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import random
import whisper

# =========================================================
# CONFIG
# =========================================================

FPS = 24

FONT_SIZE = 72
LINE_HEIGHT = 90

MAX_WORDS = 7
MAX_CHARS = 34

SHADOW_OFFSET = 4
PARTICLE_COUNT = 25

WHISPER_MODEL = None

# =========================================================
# FONT
# =========================================================

try:
    font = ImageFont.truetype(
        "C:/Windows/Fonts/arialbd.ttf",
        FONT_SIZE
    )
except:
    font = ImageFont.load_default()


# =========================================================
# VIDEO SIZE
# =========================================================

def get_video_size(video_format):

    if video_format == "tiktok":
        return 1080, 1920

    if video_format == "square":
        return 1080, 1080

    return 1280, 720


# =========================================================
# WHISPER
# =========================================================

def get_whisper_model():

    global WHISPER_MODEL

    if WHISPER_MODEL is None:

        print("Loading Whisper model...")

        WHISPER_MODEL = whisper.load_model("base")

    return WHISPER_MODEL


def transcribe_audio(audio_path):

    model = get_whisper_model()

    print("Transcribing lyrics automatically...")

    result = model.transcribe(
        audio_path,
        language="nl",
        task="transcribe",
        word_timestamps=True,
        fp16=False,
        initial_prompt=(
            "Dit is een Nederlands rapnummer met straattaal, slang en jongerentaal. "
            "Transcribeer letterlijk wat er gezegd wordt. "
            "Vertaal niets naar Engels of Duits. "
            "Behoud Nederlandse straattaal zoals: bro, broer, mattie, do, doekoe, "
            "osso, skeer, fissa, kaulo, kanker, wollah, sahbi, niffo, strijder, "
            "drerrie, pokoe, barkie, stack, stacks, money, cash, gang, vibe, baddie. "
            "Gebruik de originele woorden zoals gezongen."
        )
    )

    lyrics = []

    for segment in result.get("segments", []):

        word_items = segment.get("words", [])

        # normal working mode: Whisper gives real word timestamps
        if word_items:

            for item in word_items:

                word_text = item.get("word", "").strip()

                if not word_text:
                    continue

                lyrics.append({
                    "word": word_text,
                    "start": float(item["start"]),
                    "end": float(item["end"])
                })

        # safety fallback: if Railway/Whisper gives only segment text
        else:

            text = segment.get("text", "").strip()

            if not text:
                continue

            raw_words = text.split()

            if not raw_words:
                continue

            start = float(segment.get("start", 0))
            end = float(segment.get("end", start + 1))

            total_duration = max(0.1, end - start)
            word_duration = total_duration / len(raw_words)

            for i, word in enumerate(raw_words):

                lyrics.append({
                    "word": word,
                    "start": start + i * word_duration,
                    "end": start + (i + 1) * word_duration
                })

    print("Total lyric words:", len(lyrics))

    return lyrics


# =========================================================
# MAIN RENDER FUNCTION
# =========================================================

def render_video(
    audio_path,
    bg_path,
    output_path,
    video_format="youtube",
    lyric_language="auto"
):

    W, H = get_video_size(video_format)

    audio = AudioFileClip(audio_path)

    lyrics = transcribe_audio(audio_path)

    if len(lyrics) == 0:

        print("WARNING: No lyrics found.")

        lyrics = [{
            "word": "Lyrics unavailable",
            "start": 0,
            "end": min(5, audio.duration)
        }]

    bg_original = Image.open(bg_path).convert("RGB")

    # =====================================================
    # PRE-RENDER STATIC BACKGROUND
    # =====================================================

    base = bg_original.resize((W, H)).convert("RGBA")

    blur = bg_original.resize((W, H)).filter(
        ImageFilter.GaussianBlur(10)
    ).convert("RGBA")

    static_bg = Image.blend(base, blur, 0.15)

    overlay = Image.new(
        "RGBA",
        (W, H),
        (0, 0, 0, 60)
    )

    static_bg = Image.alpha_composite(
        static_bg,
        overlay
    )

    # =====================================================
    # TIMING FIX
    # =====================================================

    for i, word in enumerate(lyrics):

        word_duration = word["end"] - word["start"]

        if word_duration < 0.22:

            word["end"] += 0.08

            if i < len(lyrics) - 1:

                next_start = lyrics[i + 1]["start"]

                if word["end"] > next_start:
                    word["end"] = next_start - 0.01

    # =====================================================
    # SMART SENTENCE SPLIT
    # =====================================================

    def smart_split(words):

        sentences = []

        current = []
        current_chars = 0

        for i, item in enumerate(words):

            word = item.get("word", "")

            if not word:
                continue

            current.append(item)
            current_chars += len(word) + 1

            is_last = i == len(words) - 1

            if not is_last:
                gap = words[i + 1]["start"] - item["end"]
            else:
                gap = 0

            should_split = False

            if word.endswith((".", "!", "?")):
                should_split = True

            elif gap > 0.45:
                should_split = True

            elif len(current) >= MAX_WORDS:
                should_split = True

            elif current_chars >= MAX_CHARS:
                should_split = True

            elif is_last:
                should_split = True

            if should_split:

                sentences.append(current)

                current = []
                current_chars = 0

        return sentences

    sentences = smart_split(lyrics)

    # =====================================================
    # PARTICLES
    # =====================================================

    random.seed(10)

    particles = []

    for _ in range(PARTICLE_COUNT):

        particles.append({
            "x": random.randint(0, W),
            "y": random.randint(0, H),
            "speed": random.uniform(0.5, 1.5),
            "size": random.randint(1, 2)
        })

    # =====================================================
    # COLORS
    # =====================================================

    def lerp(a, b, t):
        return int(a + (b - a) * t)

    def smooth_color(progress):

        white = (255, 255, 255)
        pink = (255, 60, 180)

        return (
            lerp(white[0], pink[0], progress),
            lerp(white[1], pink[1], progress),
            lerp(white[2], pink[2], progress)
        )

    # =====================================================
    # FRAME FUNCTION
    # =====================================================

    def make_frame(t):

        frame = static_bg.copy()

        # -------------------------------------------------
        # PARTICLES
        # -------------------------------------------------

        particle_layer = Image.new(
            "RGBA",
            (W, H),
            (0, 0, 0, 0)
        )

        particle_draw = ImageDraw.Draw(particle_layer)

        for p in particles:

            py = (
                p["y"] - t * p["speed"] * 8
            ) % H

            particle_draw.ellipse(
                (
                    p["x"],
                    py,
                    p["x"] + p["size"],
                    py + p["size"]
                ),
                fill=(255, 255, 255, 20)
            )

        particle_layer = particle_layer.filter(
            ImageFilter.GaussianBlur(1)
        )

        frame = Image.alpha_composite(
            frame,
            particle_layer
        )

        draw = ImageDraw.Draw(frame)

        # -------------------------------------------------
        # LYRICS
        # -------------------------------------------------

        for sentence in sentences:

            start = sentence[0]["start"]
            end = sentence[-1]["end"]

            if not (start <= t <= end):
                continue

            lines = []
            current_line = []

            words_per_line = 3 if video_format == "tiktok" else 4

            for word in sentence:

                current_line.append(word)

                if len(current_line) >= words_per_line:

                    lines.append(current_line)

                    current_line = []

            if current_line:
                lines.append(current_line)

            total_height = len(lines) * LINE_HEIGHT

            y_start = (H - total_height) // 2

            if video_format == "tiktok":
                y_start = int(H * 0.48) - total_height // 2

            positions = []

            # layout
            for li, line in enumerate(lines):

                line_text = " ".join(
                    [w["word"] for w in line]
                )

                bbox = draw.textbbox(
                    (0, 0),
                    line_text,
                    font=font
                )

                text_width = bbox[2] - bbox[0]

                x = (W - text_width) // 2
                y = y_start + li * LINE_HEIGHT

                for word in line:

                    positions.append((x, y))

                    bbox = draw.textbbox(
                        (0, 0),
                        word["word"] + " ",
                        font=font
                    )

                    x += bbox[2] - bbox[0]

            active_word = -1

            for i, word in enumerate(sentence):

                if word["start"] <= t <= word["end"]:

                    active_word = i
                    break

            for i, word in enumerate(sentence):

                x, y = positions[i]

                text = word["word"] + " "

                progress = 1 if i == active_word else 0

                color = smooth_color(progress)

                # text shadow
                draw.text(
                    (
                        x + SHADOW_OFFSET,
                        y + SHADOW_OFFSET
                    ),
                    text,
                    font=font,
                    fill=(0, 0, 0)
                )

                # main text
                draw.text(
                    (x, y),
                    text,
                    font=font,
                    fill=color
                )

        return np.array(frame.convert("RGB"))

    # =====================================================
    # EXPORT
    # =====================================================

    video = VideoClip(
        make_frame,
        duration=audio.duration
    )

    video = video.set_audio(audio)

    video.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        threads=4
    )

    return output_path