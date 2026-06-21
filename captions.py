"""
Turns word-level transcript timestamps into a TikTok-style "pop-on"
ASS subtitle file: short bursts of 1-3 words, bold, centered, with
an outline for readability over any background.
"""
import config


def _group_words(words, max_words):
    """Groups consecutive words into chunks of up to max_words each."""
    groups = []
    current = []
    for w in words:
        current.append(w)
        if len(current) >= max_words:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def _format_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _ass_header(width, height):
    font_name = config.CAPTION_FONT.replace("-", " ")
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Pop,{font_name},{config.CAPTION_FONT_SIZE},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,{config.CAPTION_OUTLINE_WIDTH},0,2,40,40,{int((1 - config.CAPTION_POSITION_Y_RATIO) * height)},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def build_caption_ass(words: list, out_path: str, width: int, height: int):
    """
    Writes an .ass file with pop-on caption groups timed to the words.
    Returns the path, or None if there were no words to caption.
    """
    if not words:
        return None

    groups = _group_words(words, config.CAPTION_MAX_WORDS_PER_CHUNK)

    lines = [_ass_header(width, height)]
    for group in groups:
        start = group[0]["start"]
        end = group[-1]["end"]
        text = " ".join(w["word"] for w in group).upper()
        # escape ASS special characters
        text = text.replace("{", "(").replace("}", ")")
        lines.append(
            f"Dialogue: 0,{_format_ass_time(start)},{_format_ass_time(end)},Pop,,0,0,0,,{text}"
        )

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return out_path
