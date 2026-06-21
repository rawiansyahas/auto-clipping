"""
Transcribes a clip with word-level timestamps using faster-whisper
(runs locally on CPU, no API key needed).
"""
from faster_whisper import WhisperModel

import config

_model = None


def _get_model():
    global _model
    if _model is None:
        print(f"[whisper] loading model '{config.WHISPER_MODEL_SIZE}' (first call only)...")
        _model = WhisperModel(
            config.WHISPER_MODEL_SIZE,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE_TYPE,
        )
    return _model


def transcribe_words(audio_path: str):
    """
    Returns a flat list of {word, start, end} dicts with timestamps
    relative to the start of audio_path.
    """
    model = _get_model()
    segments, _info = model.transcribe(
        audio_path,
        word_timestamps=True,
        vad_filter=True,  # skips silence, helps avoid hallucinated words
    )

    words = []
    for seg in segments:
        if not seg.words:
            continue
        for w in seg.words:
            text = w.word.strip()
            if text:
                words.append({"word": text, "start": w.start, "end": w.end})
    return words
