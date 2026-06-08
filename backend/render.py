import os
import random
import numpy as np
import whisper

from moviepy.editor import AudioFileClip
from moviepy.video.VideoClip import VideoClip

from PIL import Image, ImageDraw, ImageFont, ImageFilter

FPS = 24

FONT_SIZE = 60
LINE_HEIGHT = 80

MAX_WORDS = 14
MAX_CHARS = 80

SHADOW_OFFSET = 5
PARTICLE_COUNT = 25

WHISPER_MODEL = None


def load_font(size, font_style="bold"):
    if font_style == "clean":
        possible_fonts = [
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/Arial.ttf",
        ]

        wanted_names = [
            "LiberationSans-Regular.ttf",
            "DejaVuSans.ttf",
            "Arial.ttf"
        ]

    elif font_style == "cinematic":
        possible_fonts = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ]

        wanted_names = [
            "DejaVuSansCondensed-Bold.ttf",
            "DejaVuSans-Bold.ttf",
            "LiberationSans-Bold.ttf",
            "arialbd.ttf"
        ]

    else:
        possible_fonts = [
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/Arial.ttf",
        ]

        wanted_names = [
            "LiberationSans-Bold.ttf",
            "DejaVuSans-Bold.ttf",
            "arialbd.ttf",
            "Arial.ttf"
        ]

    for font_path in possible_fonts:
        if os.path.exists(font_path):
            print("Using font:", font_path)
            return ImageFont.truetype(font_path, size)

    search_dirs = [
        "/usr/share/fonts",
        "/nix/store"
    ]

    for search_dir in search_dirs:
        if os.path.exists(search_dir):
            for root, dirs, files in os.walk(search_dir):
                for file in files:
                    if file in wanted_names:
                        font_path = os.path.join(root, file)
                        print("Using discovered font:", font_path)
                        return ImageFont.truetype(font_path, size)

    print("WARNING: fallback tiny font used")
    return ImageFont.load_default()


def get_video_size(video_format):
    if video_format == "tiktok":
        return 1080, 1920

    if video_format == "square":
        return 1080, 1080

    return 1280, 720


def get_active_color(lyric_color):
    colors = {
        "pink": (255, 60, 180),
        "yellow": (255, 220, 70),
        "blue": (80, 170, 255),
        "green": (90, 255, 150),
        "white": (255, 255, 255)
    }

    return colors.get(
        lyric_color,
        (255, 60, 180)
    )


def get_whisper_model():
    global WHISPER_MODEL

    if WHISPER_MODEL is None:
        print("Loading Whisper model...")
        WHISPER_MODEL = whisper.load_model("medium")

    return WHISPER_MODEL


def transcribe_audio(audio_path):
    model = get_whisper_model()

    print("Transcribing lyrics automatically...")

    result = model.transcribe(
        audio_path,
        task="transcribe",
        word_timestamps=True,
        fp16=False,
        temperature=0,
        condition_on_previous_text=True,
        compression_ratio_threshold=2.4,
        logprob_threshold=-1.0,
        no_speech_threshold=0.6,
        initial_prompt=(
            "These are song lyrics. "
            "Transcribe exactly what is sung. "
            "Do not translate. "
            "Keep repeated words and slang."
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

    print("Total lyric words:", len(words))

    return words


def build_lyrics_from_text(
    lyrics_text,
    audio_duration,
    timing_words=None
):
    raw_words = lyrics_text.replace("\n", " ").split()

    words = []

    if not raw_words:
        return words

    if timing_words and len(timing_words) > 0:
        for i, word in enumerate(raw_words):
            if i < len(timing_words):
                start = timing_words[i]["start"]
                end = timing_words[i]["end"]

            else:
                previous_end = (
                    words[-1]["end"]
                    if words else 0
                )

                start = previous_end
                end = start + 0.35

            words.append({
                "word": word,
                "start": float(start),
                "end": float(end)
            })

        return words

    usable_duration = max(audio_duration - 0.5, 1)

    word_duration = (
        usable_duration /
        len(raw_words)
    )

    for i, word in enumerate(raw_words):
        start = i * word_duration
        end = start + word_duration * 0.9

        words.append({
            "word": word,
            "start": float(start),
            "end": float(end)
        })

    return words


def split_sentences(words):
    sentences = []
    current = []
    chars = 0

    min_words = 6

    connectors = [
        "and",
        "but",
        "or",
        "so",
        "cause",
        "because",
        "that",
        "when",
        "where",
        "with",
        "to",
        "of",
        "in",
        "on",
        "for",
        "the",
        "a"
    ]

    for i, w in enumerate(words):
        current.append(w)
        chars += len(w["word"]) + 1

        is_last = i == len(words) - 1

        gap = (
            words[i + 1]["start"] - w["end"]
            if not is_last else 0
        )

        word_text = w["word"].strip()

        next_word = (
            words[i + 1]["word"].lower().strip(".,!?;:")
            if not is_last else ""
        )

        should_split = False

        if is_last:
            should_split = True

        elif (
            word_text.endswith((".", "!", "?"))
            and len(current) >= min_words
        ):
            should_split = True

        elif (
            gap > 1.25
            and len(current) >= min_words
        ):
            should_split = True

        elif (
            len(current) >= MAX_WORDS
            or chars >= MAX_CHARS
        ):
            should_split = True

        if should_split and next_word in connectors:
            should_split = False

        if should_split:
            sentences.append(current)
            current = []
            chars = 0

    return sentences


def render_video(
    audio_path,
    bg_path,
    output_path,
    video_format="youtube",
    lyric_language="auto",
    lyric_color="pink",
    font_style="bold",
    lyrics_text="",
    text_position="center"
):
    W, H = get_video_size(video_format)

    active_color = get_active_color(lyric_color)
    selected_font = load_font(FONT_SIZE, font_style)

    audio = AudioFileClip(audio_path)

    if lyrics_text.strip():
        print("Using pasted lyrics text with Whisper timing.")

        timing_words = transcribe_audio(
            audio_path
        )

        lyrics = build_lyrics_from_text(
            lyrics_text,
            audio.duration,
            timing_words
        )

    else:
        lyrics = transcribe_audio(
            audio_path
        )

    bg_original = Image.open(bg_path).convert("RGB")

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

    for i, w in enumerate(lyrics):
        dur = w["end"] - w["start"]

        if dur < 0.25:
            w["end"] = w["start"] + 0.25

        if i < len(lyrics) - 1:
            next_start = lyrics[i + 1]["start"]

            if w["end"] > next_start:
                w["end"] = next_start - 0.02

    sentences = split_sentences(lyrics)

    random.seed(10)

    particles = []

    for _ in range(PARTICLE_COUNT):
        particles.append({
            "x": random.randint(0, W),
            "y": random.randint(0, H),
            "speed": random.uniform(0.5, 1.5),
            "size": random.randint(1, 2)
        })

    def make_frame(t):
        frame = static_bg.copy()

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

        for sentence in sentences:
            start = sentence[0]["start"]
            end = sentence[-1]["end"]

            fade_time = 0.45

            sentence_duration = max(
                end - start,
                0.01
            )

            safe_fade = min(
                fade_time,
                sentence_duration / 3
            )

            visible_start = start - safe_fade
            visible_end = end + safe_fade

            if not (visible_start <= t <= visible_end):
                continue

            if t < start:
                sentence_alpha = (
                    t - visible_start
                ) / safe_fade

            elif t > end:
                sentence_alpha = (
                    visible_end - t
                ) / safe_fade

            else:
                sentence_alpha = 1

            sentence_alpha = max(
                0,
                min(sentence_alpha, 1)
            )

            lines = []
            current = []

            words_per_line = 5 if video_format == "tiktok" else 7

            for w in sentence:
                current.append(w)

                if len(current) >= words_per_line:
                    lines.append(current)
                    current = []

            if current:
                lines.append(current)

            total_h = len(lines) * LINE_HEIGHT

            if text_position == "bottom":
                if video_format == "tiktok":
                    y0 = int(H * 0.72) - total_h // 2
                else:
                    y0 = int(H * 0.74) - total_h // 2

            else:
                y0 = (H - total_h) // 2

                if video_format == "tiktok":
                    y0 = int(H * 0.48) - total_h // 2

            for li, line in enumerate(lines):
                txt = " ".join(
                    [w["word"] for w in line]
                )

                bbox = draw.textbbox(
                    (0, 0),
                    txt,
                    font=selected_font
                )

                tw = bbox[2] - bbox[0]

                x = (W - tw) // 2
                y = y0 + li * LINE_HEIGHT

                shadow_alpha = int(220 * sentence_alpha)
                text_alpha = int(255 * sentence_alpha)

                draw.text(
                    (
                        x + SHADOW_OFFSET,
                        y + SHADOW_OFFSET
                    ),
                    txt,
                    font=selected_font,
                    fill=(0, 0, 0, shadow_alpha)
                )

                draw.text(
                    (x, y),
                    txt,
                    font=selected_font,
                    fill=(
                        active_color[0],
                        active_color[1],
                        active_color[2],
                        text_alpha
                    )
                )

        return np.array(frame.convert("RGB"))

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