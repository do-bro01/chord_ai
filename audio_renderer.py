"""기능 5: 코드 진행 → MIDI → WAV 렌더링

PRD v2 MVP는 피아노 1트랙 sustain.
한 마디 = 한 코드, 마디 길이는 BPM + 박자에서 계산.

세 가지 진입점:
  - build_midi(chords, bpm, beats_per_bar) → PrettyMIDI 객체
  - render_to_bytes(chords, ...) → WAV bytes (preview용, 파일 저장 안 함)
  - render_audio(chords, output_basename, ...) → output/에 .mid + .wav 저장 (CLI/export 호환)
"""

from __future__ import annotations

import io
import wave
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pretty_midi
from music21 import harmony

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output"
DEFAULT_SOUNDFONT = PROJECT_ROOT / "soundfonts" / "FluidR3_GM.sf2"

# GM Acoustic Grand Piano (PRD v2 MVP)
PIANO_PROGRAM = 0
SAMPLE_RATE = 44100
DEFAULT_VELOCITY = 90
DEFAULT_BPM = 100
DEFAULT_BEATS_PER_BAR = 4


def _chord_to_midi_pitches(symbol: str) -> List[int]:
    """코드 심볼 문자열에서 MIDI 노트 번호 리스트 추출."""
    try:
        cs = harmony.ChordSymbol(symbol)
    except Exception:
        return []
    return [int(p.midi) for p in cs.pitches]


def _bar_duration_sec(bpm: int, beats_per_bar: int) -> float:
    return (60.0 / bpm) * beats_per_bar


def build_midi(
    chords: List[str],
    bpm: int = DEFAULT_BPM,
    beats_per_bar: int = DEFAULT_BEATS_PER_BAR,
    program: int = PIANO_PROGRAM,
) -> pretty_midi.PrettyMIDI:
    """코드 진행으로부터 PrettyMIDI 객체 생성.

    한 마디 = 한 코드, sustain. 코드 사이 gap 없음.
    파싱 실패한 코드는 한 마디만큼 휴지.
    """
    bar_dur = _bar_duration_sec(bpm, beats_per_bar)
    pm = pretty_midi.PrettyMIDI(initial_tempo=float(bpm))
    inst = pretty_midi.Instrument(program=program)

    cursor = 0.0
    for symbol in chords:
        pitches = _chord_to_midi_pitches(symbol)
        if pitches:
            for p in pitches:
                inst.notes.append(
                    pretty_midi.Note(
                        velocity=DEFAULT_VELOCITY,
                        pitch=p,
                        start=cursor,
                        end=cursor + bar_dur,
                    )
                )
        cursor += bar_dur

    pm.instruments.append(inst)
    return pm


def _render_with_fluidsynth(
    pm: pretty_midi.PrettyMIDI,
    soundfont_path: Path,
    sample_rate: int = SAMPLE_RATE,
) -> Tuple[np.ndarray, int]:
    """pretty_midi의 fluidsynth 백엔드로 오디오 생성. (mono float32)"""
    audio = pm.fluidsynth(fs=sample_rate, sf2_path=str(soundfont_path))
    return audio.astype(np.float32), sample_rate


def _audio_to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    """float32 모노 신호를 16-bit PCM WAV bytes로 인코딩."""
    peak = float(np.max(np.abs(audio))) if audio.size else 1.0
    if peak > 1.0:
        audio = audio / peak
    pcm = (audio * 32767.0).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


def _write_wav(path: Path, audio: np.ndarray, sample_rate: int) -> None:
    path.write_bytes(_audio_to_wav_bytes(audio, sample_rate))


def render_to_bytes(
    chords: List[str],
    bpm: int = DEFAULT_BPM,
    beats_per_bar: int = DEFAULT_BEATS_PER_BAR,
    soundfont_path: Path | str = DEFAULT_SOUNDFONT,
) -> bytes:
    """코드 진행 → WAV bytes (in-memory). preview API용.

    파일을 디스크에 남기지 않고 즉시 재생 가능한 WAV 바이트만 반환.
    """
    if not chords:
        raise ValueError("코드 진행이 비어 있습니다.")
    sf_path = Path(soundfont_path)
    if not sf_path.exists():
        raise FileNotFoundError(f"SoundFont를 찾을 수 없습니다: {sf_path}")

    pm = build_midi(chords, bpm=bpm, beats_per_bar=beats_per_bar)
    audio, sr = _render_with_fluidsynth(pm, sf_path)
    return _audio_to_wav_bytes(audio, sr)


def render_audio(
    chords: List[str],
    output_basename: str = "arranged",
    soundfont_path: Path | str = DEFAULT_SOUNDFONT,
    bpm: int = DEFAULT_BPM,
    beats_per_bar: int = DEFAULT_BEATS_PER_BAR,
) -> Path:
    """코드 진행을 output/<basename>.mid + .wav로 저장하고 WAV 경로 반환.

    CLI(main.py)와 export 흐름 양쪽에서 사용.
    """
    if not chords:
        raise ValueError("코드 진행이 비어 있습니다.")

    sf_path = Path(soundfont_path)
    if not sf_path.exists():
        raise FileNotFoundError(f"SoundFont를 찾을 수 없습니다: {sf_path}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pm = build_midi(chords, bpm=bpm, beats_per_bar=beats_per_bar)

    midi_path = OUTPUT_DIR / f"{output_basename}.mid"
    pm.write(str(midi_path))

    audio, sr = _render_with_fluidsynth(pm, sf_path)
    wav_path = OUTPUT_DIR / f"{output_basename}.wav"
    _write_wav(wav_path, audio, sr)
    return wav_path
