"""chordino(vamp) 기반 코드 추출 — autochord 대안/보조 인식기.

설치 전제:
  - vamp Python 바인딩 + nnls-chroma:chordino 플러그인 (이미 깔려있음)
  - librosa, soundfile (audio_analysis와 공유)

특징:
  - usehartesyntax=1 로 maj7/min7/7/sus4/dim/aug 등 확장 라벨 출력
  - tuningmode=0 (global) 로 곡 전체 튜닝 보정
  - autochord와 동일하게 demucs harmonic stem을 입력으로 받아 노이즈 제거 후 분석
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List, Tuple

log = logging.getLogger("chord_ai.chordino")

# Harte 표기 → 일반 표기 매핑
# 예: 'C:maj' → 'C', 'A:min7' → 'Am7', 'D:7' → 'D7', 'C/E' → 'C/E'
_HARTE_QUALITY_MAP = {
    "maj": "",
    "min": "m",
    "7": "7",
    "maj7": "maj7",
    "min7": "m7",
    "minmaj7": "mMaj7",
    "dim": "dim",
    "dim7": "dim7",
    "hdim7": "m7b5",
    "aug": "aug",
    "sus4": "sus4",
    "sus2": "sus2",
    "9": "9",
    "maj9": "maj9",
    "min9": "m9",
    "11": "11",
    "13": "13",
    "6": "6",
    "min6": "m6",
}


def _normalize_label(label: str) -> str:
    """chordino 라벨을 일반 표기로 정규화.

    chordino가 토하는 라벨 예시:
      - 'N'                   → '' (no chord)
      - 'C'                    → 'C' (simple syntax)
      - 'C:maj'                → 'C' (harte syntax)
      - 'A:min'                → 'Am'
      - 'D:7'                  → 'D7'
      - 'C:maj/E'              → 'C/E' (slash with bass)
      - 'F#:min7'              → 'F#m7'
    """
    if not label or label == "N" or label == "X":
        return ""

    # 슬래시(베이스 명시) 분리
    bass = ""
    if "/" in label:
        label, bass = label.split("/", 1)

    if ":" not in label:
        # simple syntax — 그대로 사용
        chord = label
    else:
        root, quality = label.split(":", 1)
        suffix = _HARTE_QUALITY_MAP.get(quality, quality)
        chord = f"{root}{suffix}"

    if bass:
        chord = f"{chord}/{bass}"
    return chord


def _load_audio_mono(path: Path, sr: int = 44100):
    """mono float32 오디오 로드. chordino는 mono 입력을 받음."""
    import librosa
    y, _sr = librosa.load(str(path), sr=sr, mono=True)
    return y, sr


def _load_audio_from_demucs(audio_path: Path, sr: int = 44100):
    """demucs로 분리한 harmonic stem(bass+other)을 mono로 변환해서 반환.

    audio_analysis._separate_harmonic을 재사용하되, chordino 입력을 위해
    mono + 원하는 sample rate로 맞춰준다.
    """
    import numpy as np
    import librosa
    from audio_analysis import _separate_harmonic

    waveform, demucs_sr = _separate_harmonic(audio_path)
    # waveform: torch tensor (channels, samples)
    arr = waveform.numpy()
    # mono down-mix
    mono = arr.mean(axis=0)
    # sample rate 변환
    if demucs_sr != sr:
        mono = librosa.resample(mono, orig_sr=demucs_sr, target_sr=sr)
    return mono.astype("float32"), sr


def analyze_with_timing(
    path: str | Path,
    *,
    use_demucs_stem: bool = True,
    use_harte_syntax: bool = True,
    rollon: float = 1.0,
    tuningmode: int = 0,
) -> List[Tuple[float, float, str]]:
    """chordino로 코드 진행 추출.

    Args:
        path: 오디오 파일 경로
        use_demucs_stem: True면 demucs로 보컬·드럼 제거 후 분석. False면 원본.
        use_harte_syntax: True면 maj7/min7 등 확장 라벨 (권장)
        rollon: 베이스 노이즈 제거 임계값 0~5 (%). 1.0 권장.
        tuningmode: 0=global, 1=local

    Returns:
        [(start_sec, end_sec, chord), ...] — autochord와 같은 형식.
        chordino는 시작 시간만 출력하므로 다음 segment 시작을 현재 segment 끝으로 사용.
    """
    import numpy as np
    import vamp

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)

    if use_demucs_stem:
        log.info("demucs harmonic stem 추출 중...")
        audio, sr = _load_audio_from_demucs(p)
    else:
        audio, sr = _load_audio_mono(p)

    log.info("chordino 호출 (sr=%d, samples=%d)", sr, len(audio))
    params = {
        "usehartesyntax": 1.0 if use_harte_syntax else 0.0,
        "rollon": float(rollon),
        "tuningmode": float(tuningmode),
    }
    result = vamp.collect(
        audio, sr, "nnls-chroma:chordino", output="simplechord", parameters=params
    )

    # result 형식: {'list': [{'timestamp': ..., 'label': '...', 'values': array(...)}]}
    if "list" not in result:
        raise RuntimeError(f"chordino 출력 형식 예상과 다름: keys={list(result.keys())}")

    raw = result["list"]
    # 시작 시간 + 라벨 추출
    starts: List[float] = []
    labels: List[str] = []
    for item in raw:
        ts = item.get("timestamp")
        # ts는 RealTime 또는 Fraction 형식 — float로
        try:
            t = float(ts)
        except Exception:
            # vamp의 RealTime: .sec + .nsec
            t = float(getattr(ts, "sec", 0)) + float(getattr(ts, "nsec", 0)) / 1e9
        label = str(item.get("label", ""))
        starts.append(t)
        labels.append(label)

    # 다음 시작 = 현재 끝
    out: List[Tuple[float, float, str]] = []
    for i, (start, label) in enumerate(zip(starts, labels)):
        end = starts[i + 1] if i + 1 < len(starts) else start + 1.0  # 마지막은 1초로 추정
        normalized = _normalize_label(label)
        if not normalized:
            continue
        out.append((start, end, normalized))
    return out


def _compress_consecutive(items: List[Tuple[float, float, str]]) -> List[Tuple[float, float, str]]:
    """인접한 동일 코드 segment 병합."""
    if not items:
        return items
    merged: List[Tuple[float, float, str]] = []
    cur_start, cur_end, cur_chord = items[0]
    for start, end, chord in items[1:]:
        if chord == cur_chord:
            cur_end = end
        else:
            merged.append((cur_start, cur_end, cur_chord))
            cur_start, cur_end, cur_chord = start, end, chord
    merged.append((cur_start, cur_end, cur_chord))
    return merged


def analyze(path: str | Path, **kwargs) -> List[str]:
    """audio_analysis.analyze와 같은 형태의 코드 진행 리스트 반환."""
    timed = analyze_with_timing(path, **kwargs)
    merged = _compress_consecutive(timed)
    return [c for _, _, c in merged]
