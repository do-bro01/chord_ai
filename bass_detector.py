"""베이스 음 검출 — demucs bass stem에서 segment별 dominant pitch class 추출.

용도: chordino가 잡지 못하는 슬래시 코드 + 상부구조 substitution(CM7↔Em7) 정정.

흐름:
  1. demucs로 분리한 bass stem 로드 (audio_analysis.get_bass_stem 캐시 활용)
  2. mono 변환 + chroma_cqt로 12음 분포 시계열 계산
  3. 각 chord segment 시간 범위에서 chroma 평균 → argmax = bass pitch class
  4. (선택) 신뢰도 측정: 1순위 / 2순위 비율로 약하면 None 리턴
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Tuple

log = logging.getLogger("chord_ai.bass_detector")

_PC_TO_NOTE = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _bass_chroma(audio_path: Path, target_sr: int = 22050) -> Tuple["np.ndarray", int, int]:
    """bass stem → mono → chroma_cqt 시계열.

    반환: (chroma[12, T], sr, hop_length)
    """
    import numpy as np
    import librosa
    from audio_analysis import get_bass_stem

    bass, demucs_sr = get_bass_stem(audio_path)
    arr = bass.numpy()
    mono = arr.mean(axis=0)

    # bass는 저역 위주이므로 sr 22050이면 충분 (fmin은 librosa 기본 = C1 = 32.7Hz)
    if demucs_sr != target_sr:
        mono = librosa.resample(mono, orig_sr=demucs_sr, target_sr=target_sr)

    hop_length = 512
    # chroma_cqt: bass 영역에 더 적합 (CQT 기반, 저음 해상도 좋음)
    # n_octaves를 줄여서 베이스 영역(C1~C4 정도)에 집중
    chroma = librosa.feature.chroma_cqt(
        y=mono.astype("float32"),
        sr=target_sr,
        hop_length=hop_length,
        fmin=librosa.note_to_hz("C1"),
        n_octaves=4,  # C1~C5 (베이스 영역)
    )
    return chroma, target_sr, hop_length


def detect_bass_per_segment(
    audio_path: str | Path,
    segments: List[Tuple[float, float, str]],
    confidence_ratio: float = 1.5,
) -> List[Tuple[float, float, str, Optional[int], float]]:
    """각 segment별 dominant bass pitch class와 신뢰도 추출.

    Args:
        audio_path: 원본 오디오 경로
        segments: [(start, end, chord_label), ...]
        confidence_ratio: top1/top2 chroma 강도 비율. 이 값보다 낮으면 신뢰도 낮음 표시.

    Returns:
        [(start, end, chord_label, bass_pc or None, confidence), ...]
        bass_pc: 0=C, 1=C#, ..., 11=B. None이면 신뢰도 부족.
        confidence: top1/top2 비율 (참고용).
    """
    import numpy as np

    p = Path(audio_path)
    chroma, sr, hop = _bass_chroma(p)
    n_frames = chroma.shape[1]

    results: List[Tuple[float, float, str, Optional[int], float]] = []
    for start, end, chord in segments:
        # 시간 → 프레임 인덱스
        sf = int(start * sr / hop)
        ef = int(end * sr / hop)
        sf = max(0, min(sf, n_frames - 1))
        ef = max(sf + 1, min(ef, n_frames))

        if ef <= sf:
            results.append((start, end, chord, None, 0.0))
            continue

        seg = chroma[:, sf:ef]  # (12, frames)
        # 시간 평균 → 12-dim 벡터
        profile = seg.mean(axis=1)
        if profile.sum() == 0:
            results.append((start, end, chord, None, 0.0))
            continue

        # 정렬해서 top1/top2 비율로 신뢰도 측정
        sorted_idx = np.argsort(profile)[::-1]
        top1_pc = int(sorted_idx[0])
        top1_val = float(profile[sorted_idx[0]])
        top2_val = float(profile[sorted_idx[1]]) if len(sorted_idx) > 1 else 1e-6
        ratio = top1_val / max(top2_val, 1e-6)

        if ratio < confidence_ratio:
            # 신뢰도 부족 — None 반환
            results.append((start, end, chord, None, ratio))
        else:
            results.append((start, end, chord, top1_pc, ratio))

    return results


def pc_to_note(pc: int) -> str:
    return _PC_TO_NOTE[pc % 12]
