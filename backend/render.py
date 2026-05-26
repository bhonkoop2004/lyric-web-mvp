from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import random
import whisper

FPS = 24

FONT_SIZE = 72
LINE_HEIGHT = 90

MAX_WORDS = 7
MAX_CHARS = 34

SHADOW_OFFSET = 4
PARTICLE_COUNT = 25

WHISPER_MODEL = None

try:
    font = ImageFont.truetype(
        "C:/Windows/Fonts/arialbd.ttf",
        FONT_SIZE
    )
except:
    font = ImageFont.load_default()


# =========================================================
# VIDEO FORMAT SIZES
# =========================================================

def get_video_size(video_format):

    if video_format == "tiktok":
        return 1080, 1920

    if video_format == "square":
        return 1080, 1080

    return 1280, 720


# =========================================================
# WHISPER MODEL
# =========================================================

def get_whisper_model():

    global WHISPER_MODEL

    if WHISPER_MODEL is None:

        print("Loading Whisper model...")

        WHISPER_MODEL = whisper.load_model("base")

    return WHISPER_MODEL


# =========================================================
# TRANSCRIBE AUDIO
# =========================================================

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

    words = []

    for segment in result.get("segments", []):

        for w in segment.get("words", []):

            word_text = w.get("word", "").strip()

            if not word_text:
                continue

            words.append({
                "word": word_text,
                "start": float(w["start"]),
                "end": float(w["end"])
            })

    return words


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

    for i, w in enumerate(lyrics):

        dur = w["end"] - w["start"]

        if dur < 0.22:

            w["end"] += 0.08

            if i < len(lyrics) - 1:

                nxt = lyrics[i + 1]["start"]

                if w["end"] > nxt:
                    w["end"] = nxt - 0.01

    # =====================================================
    # SPLIT SENTENCES
    # =====================================================

    def split_sentences(words):

        sentences = []

        current = []
        chars = 0

        for i, w in enumerate(words):

            current.append(w)

            chars += len(w["word"]) + 1

            is_last = i == len(words) - 1

            gap = (
                words[i + 1]["start"] - w["end"]
                if not is_last else 0
            )

            should_split = False

            if len(current) >= MAX_WORDS:
                should_split = True

            elif chars >= MAX_CHARS:
                should_split = True

            elif gap > 0.45:
                should_split = True

            elif is_last:
                should_split = True

            if should_split:

                sentences.append(current)

                current = []
                chars = 0

        return sentences

    sentences = split_sentences(lyrics)

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

    def color(progress):

        return (
            lerp(255, 255, progress),
            lerp(255, 60, progress),
            lerp(255, 180, progress)
        )

    # =====================================================
    # FRAME FUNCTION
    # =====================================================

    def make_frame(t):

        frame = static_bg.copy()

        # =================================================
        # PARTICLES
        # =================================================

        particle_layer = Image.new(
            "RGBA",
            (W, H),
            (0, 0, 0, 0)
        )

        pd = ImageDraw.Draw(particle_layer)

        for p in particles:

            py = (
                p["y"] - t * p["speed"] * 8
            ) % H

            pd.ellipse(
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

        # =================================================
        # LYRICS
        # =================================================

        for sentence in sentences:

            start = sentence[0]["start"]
            end = sentence[-1]["end"]

            if not (start <= t <= end):
                continue

            lines = []

            current = []

            words_per_line = 3 if video_format == "tiktok" else 4

            for w in sentence:

                current.append(w)

                if len(current) >= words_per_line:

                    lines.append(current)

                    current = []

            if current:
                lines.append(current)

            total_h = len(lines) * LINE_HEIGHT

            y0 = (H - total_h) // 2

            if video_format == "tiktok":
                y0 = int(H * 0.48) - total_h // 2

            positions = []

            for li, line in enumerate(lines):

                txt = " ".join(
                    [w["word"] for w in line]
                )

                bbox = draw.textbbox(
                    (0, 0),
                    txt,
                    font=font
                )

                tw = bbox[2] - bbox[0]

                x = (W - tw) // 2

                y = y0 + li * LINE_HEIGHT

                for w in line:

                    positions.append((x, y))

                    bbox = draw.textbbox(
                        (0, 0),
                        w["word"] + " ",
                        font=font
                    )

                    x += bbox[2] - bbox[0]

            active = -1

            for i, w in enumerate(sentence):

                if w["start"] <= t <= w["end"]:

                    active = i
                    break

            for i, w in enumerate(sentence):

                x, y = positions[i]

                txt = w["word"] + " "

                progress = 1 if i == active else 0

                c = color(progress)

                # shadow
                draw.text(
                    (
                        x + SHADOW_OFFSET,
                        y + SHADOW_OFFSET
                    ),
                    txt,
                    font=font,
                    fill=(0, 0, 0)
                )

                # main text
                draw.text(
                    (x, y),
                    txt,
                    font=font,
                    fill=c
                )

        return np.array(frame.convert("RGB"))

    # =====================================================
    # CREATE VIDEO
    # =====================================================

    video = VideoClip(
        make_frame,
        duration=audio.duration
    )

    video = video.set_audio(audio)

    # =====================================================
    # EXPORT
    # =====================================================

    video.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        threads=4
    )

    return output_path