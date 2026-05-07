"""기능 1, 2: 오디오 로드 + 코드 진행 추출

librosa로 오디오를 로드한 뒤 크로마 특징(chroma feature)을 사용해
비트 단위로 코드를 추정하고, 마디 단위 코드 진행을 반환한다.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import librosa
import numpy as np

SUPPORTED_EXTS = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}
SAMPLE_RATE = 16000

# 12개 피치클래스를 코드 이름으로 매핑할 때 사용
PITCH_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# 24개 코드 템플릿(메이저 12 + 마이너 12)을 만든다.
# 메이저 트라이어드: 루트, 장3도, 완전5도 → [0, 4, 7]
# 마이너 트라이어드: 루트, 단3도, 완전5도 → [0, 3, 7]
def _build_chord_templates() -> Tuple[np.ndarray, List[str]]:
    templates = []
    labels = []
    for i, root in enumerate(PITCH_NAMES):
        major = np.zeros(12)
        major[[i, (i + 4) % 12, (i + 7) % 12]] = 1.0
        templates.append(major)
        labels.append(root)
    for i, root in enumerate(PITCH_NAMES):
        minor = np.zeros(12)
        minor[[i, (i + 3) % 12, (i + 7) % 12]] = 1.0
        templates.append(minor)
        labels.append(f"{root}m")
    T = np.stack(templates, axis=0)
    # 각 템플릿을 단위 벡터로 정규화 → 코사인 유사도와 동일하게 비교
    T = T / np.linalg.norm(T, axis=1, keepdims=True)
    return T, labels


_CHORD_TEMPLATES, _CHORD_LABELS = _build_chord_templates()


def load_audio(path: str | Path) -> Tuple[np.ndarray, int]:
    """음원 파일을 로드해 16kHz 모노 신호로 반환."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"음원 파일을 찾을 수 없습니다: {p}")
    if p.suffix.lower() not in SUPPORTED_EXTS:
        raise ValueError(
            f"지원하지 않는 포맷입니다: {p.suffix}. "
            f"지원 포맷: {', '.join(sorted(SUPPORTED_EXTS))}"
        )
    try:
        y, sr = librosa.load(str(p), sr=SAMPLE_RATE, mono=True)
    except Exception as e:
        raise RuntimeError(f"음원 로드 실패: {e}") from e
    if y.size == 0:
        raise RuntimeError("음원이 비어 있습니다.")
    return y, sr


def _classify_chord(chroma_vec: np.ndarray) -> str:
    """단일 크로마 벡터에 대해 가장 잘 맞는 코드 라벨을 반환."""
    norm = np.linalg.norm(chroma_vec)
    if norm < 1e-6:
        return "N"  # 무음/노이즈
    v = chroma_vec / norm
    scores = _CHORD_TEMPLATES @ v
    return _CHORD_LABELS[int(np.argmax(scores))]


def extract_chord_progression(
    y: np.ndarray,
    sr: int,
    beats_per_measure: int = 4,
) -> List[str]:
    """크로마 특징 기반 마디별 코드 진행을 추출."""
    # CQT 기반 크로마가 화성 추정에 더 안정적
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)

    # 비트 추적 후 비트 동기 크로마 계산
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    if len(beat_frames) < 2:
        # 비트 추적 실패 시 전체 평균을 단일 코드로 처리
        return [_classify_chord(chroma.mean(axis=1))]

    chroma_sync = librosa.util.sync(chroma, beat_frames, aggregate=np.median)

    # 비트들을 마디 단위로 묶어 평균 → 마디 코드 추정
    n_beats = chroma_sync.shape[1]
    progression: List[str] = []
    for start in range(0, n_beats, beats_per_measure):
        end = min(start + beats_per_measure, n_beats)
        if end <= start:
            break
        measure_chroma = chroma_sync[:, start:end].mean(axis=1)
        progression.append(_classify_chord(measure_chroma))

    # 동일 코드가 연속되면 합쳐서 출력 (가독성)
    compressed: List[str] = []
    for c in progression:
        if not compressed or compressed[-1] != c:
            compressed.append(c)
    return compressed


def analyze(path: str | Path) -> List[str]:
    """파일 경로 → 코드 진행 리스트."""
    y, sr = load_audio(path)
    return extract_chord_progression(y, sr)
