"""기능 5: 코드 진행 → MIDI → WAV 렌더링

pretty_midi로 코드 진행을 MIDI로 변환하고,
pyfluidsynth + FluidR3_GM.sf2 SoundFont로 WAV를 생성한다.
각 코드 사이에 짧은 간격(silence)을 둔다.
"""

from __future__ import annotations

import wave
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pretty_midi
from music21 import harmony

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output"
DEFAULT_SOUNDFONT = PROJECT_ROOT / "soundfonts" / "FluidR3_GM.sf2"

# 렌더링 파라미터
CHORD_DURATION_SEC = 1.5      # 각 코드 지속시간
GAP_SEC = 0.3                 # 코드 사이 간격
SAMPLE_RATE = 44100
PROGRAM_NUMBER = 24           # GM Acoustic Guitar (nylon)
DEFAULT_VELOCITY = 90


def _chord_to_midi_pitches(symbol: str) -> List[int]:
    """코드 심볼 문자열에서 MIDI 노트 번호 리스트 추출."""
    try:
        cs = harmony.ChordSymbol(symbol)
    except Exception:
        return []
    return [int(p.midi) for p in cs.pitches]


def build_midi(chords: List[str]) -> pretty_midi.PrettyMIDI:
    """코드 진행으로부터 PrettyMIDI 객체 생성."""
    pm = pretty_midi.PrettyMIDI()
    inst = pretty_midi.Instrument(program=PROGRAM_NUMBER)

    cursor = 0.0
    for symbol in chords:
        pitches = _chord_to_midi_pitches(symbol)
        if not pitches:
            cursor += CHORD_DURATION_SEC + GAP_SEC
            continue
        start = cursor
        end = cursor + CHORD_DURATION_SEC
        for p in pitches:
            inst.notes.append(
                pretty_midi.Note(
                    velocity=DEFAULT_VELOCITY,
                    pitch=p,
                    start=start,
                    end=end,
                )
            )
        cursor = end + GAP_SEC

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


def _write_wav(path: Path, audio: np.ndarray, sample_rate: int) -> None:
    """float32 모노 신호를 16-bit PCM WAV로 저장."""
    # 클리핑 방지 후 int16 변환
    peak = float(np.max(np.abs(audio))) if audio.size else 1.0
    if peak > 1.0:
        audio = audio / peak
    pcm = (audio * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def render_audio(
    chords: List[str],
    output_basename: str = "arranged",
    soundfont_path: Path | str = DEFAULT_SOUNDFONT,
) -> Path:
    """코드 진행을 WAV 파일로 저장하고 경로 반환."""
    if not chords:
        raise ValueError("코드 진행이 비어 있습니다.")

    sf_path = Path(soundfont_path)
    if not sf_path.exists():
        raise FileNotFoundError(f"SoundFont를 찾을 수 없습니다: {sf_path}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pm = build_midi(chords)

    # MIDI 파일도 함께 저장 (디버깅/재사용 용도)
    midi_path = OUTPUT_DIR / f"{output_basename}.mid"
    pm.write(str(midi_path))

    audio, sr = _render_with_fluidsynth(pm, sf_path)
    wav_path = OUTPUT_DIR / f"{output_basename}.wav"
    _write_wav(wav_path, audio, sr)
    return wav_path
