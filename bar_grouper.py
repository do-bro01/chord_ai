"""마디(bar) 단위 코드 그룹핑 — 비트 검출 + 마디별 비트 슬롯 코드 매핑.

vamp 'qm-vamp-plugins:qm-barbeattracker'로:
  - 'bars' output: 마디 시작 시점
  - 'beats' output: 각 비트 시각 + 마디 내 위치 라벨 ('1', '2', '3', '4')

각 마디를 4비트 슬롯으로 분할하고, 각 슬롯에 해당 비트에서 새로 시작하는 코드를 배치.
Real Book 스타일 chord chart의 핵심 표현.

출력 형식 (Bar):
  {
    "index": 1,                                # 1-based
    "start": 2.31,                             # 마디 시작(초)
    "end": 4.33,                               # 마디 끝(초)
    "beats": [                                 # 4 슬롯(또는 더 적게 — partial bar)
      {"beat": "1", "chord": "G",   "time": 2.31},
      {"beat": "2", "chord": null,  "time": 2.82},   # 코드 변화 없음
      {"beat": "3", "chord": "C",   "time": 3.33},   # 비트 3에서 C로 변경
      {"beat": "4", "chord": null,  "time": 3.82},
    ],
    "chords": ["G", "C"]                       # 호환 — 이 마디 distinct chords
  }
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Tuple, TypedDict

log = logging.getLogger("chord_ai.bar_grouper")


class BeatSlot(TypedDict):
    beat: str           # '1', '2', '3', '4'
    chord: Optional[str]  # None이면 직전 비트와 같은 코드 (지속)
    time: float         # 비트 시작 시각


class Bar(TypedDict):
    index: int
    start: float
    end: float
    beats: List[BeatSlot]
    chords: List[str]   # 이 마디 안 distinct 코드 (호환용)


def _ts_to_float(ts) -> float:
    try:
        return float(ts)
    except Exception:
        return float(getattr(ts, "sec", 0)) + float(getattr(ts, "nsec", 0)) / 1e9


def detect_bar_starts(audio_path: str | Path) -> List[float]:
    """qm-barbeattracker로 마디 시작 시점 리스트(초) 반환."""
    import librosa
    import vamp

    y, sr = librosa.load(str(audio_path), sr=44100, mono=True)
    res = vamp.collect(y, sr, "qm-vamp-plugins:qm-barbeattracker", output="bars")
    items = res.get("list", [])
    return [_ts_to_float(it.get("timestamp")) for it in items]


def detect_beats(audio_path: str | Path) -> List[Tuple[float, str]]:
    """qm-barbeattracker로 비트 + 마디 내 위치 라벨 리스트 반환.

    반환: [(time_sec, beat_label), ...] — beat_label은 '1', '2', '3', '4' 등.
    """
    import librosa
    import vamp

    y, sr = librosa.load(str(audio_path), sr=44100, mono=True)
    res = vamp.collect(y, sr, "qm-vamp-plugins:qm-barbeattracker", output="beats")
    items = res.get("list", [])
    out: List[Tuple[float, str]] = []
    for it in items:
        t = _ts_to_float(it.get("timestamp"))
        label = str(it.get("label", ""))
        out.append((t, label))
    return out


def _chord_at_time(timed_chords: List[Tuple[float, float, str]], t: float) -> Optional[str]:
    """시각 t에 재생되는 코드 반환. 없으면 None."""
    for cs, ce, c in timed_chords:
        if cs <= t < ce:
            return c
    return None


def group_chords_by_bar(
    timed_chords: List[Tuple[float, float, str]],
    bar_starts: List[float],
    beats: List[Tuple[float, str]],
    *,
    audio_duration: float | None = None,
) -> List[Bar]:
    """timed chord segments를 비트 슬롯 단위 마디로 그룹핑.

    각 마디 안에서 비트별로 "이 비트에서 시작하는 코드"를 표시:
      - 비트 1: 항상 현재 코드 표시 (마디 시작 표시)
      - 비트 2~4: 직전 비트와 코드가 다를 때만 표시 (코드 변화 시점)

    Args:
        timed_chords: [(start, end, chord), ...]
        bar_starts: 마디 시작 시각들 (오름차순)
        beats: [(time, label '1'/'2'/'3'/'4'), ...] qm-barbeattracker 비트 출력
        audio_duration: 마지막 마디 끝 보정용

    Returns:
        [Bar, ...] — 비트 슬롯이 채워진 마디 리스트.
    """
    if not bar_starts or not beats:
        return []

    # 마지막 마디 끝 시점
    last_end = audio_duration
    if last_end is None and timed_chords:
        last_end = max(end for _, end, _ in timed_chords)
    if last_end is None:
        last_end = bar_starts[-1] + (bar_starts[-1] - bar_starts[-2] if len(bar_starts) >= 2 else 2.0)

    bar_boundaries: List[Tuple[float, float]] = []
    for i, s in enumerate(bar_starts):
        e = bar_starts[i + 1] if i + 1 < len(bar_starts) else last_end
        bar_boundaries.append((s, e))

    bars: List[Bar] = []

    # 비트별 "현재 재생 중인 코드" 미리 계산 — O(beats * chords) 회피
    # timed_chords가 시간순이라고 가정.
    chord_idx = 0
    actual_chord_per_beat: List[Optional[str]] = []
    for t, _label in beats:
        # t에 활성 chord 찾기 (시간 단조 증가 가정)
        while (
            chord_idx + 1 < len(timed_chords)
            and timed_chords[chord_idx + 1][0] <= t
        ):
            chord_idx += 1
        if chord_idx < len(timed_chords):
            cs, ce, ch = timed_chords[chord_idx]
            actual_chord_per_beat.append(ch if cs <= t < ce else None)
        else:
            actual_chord_per_beat.append(None)

    for bi, (b_start, b_end) in enumerate(bar_boundaries):
        # 이 마디 안의 비트 인덱스 찾기 (b_start <= beat_t < b_end)
        bar_beats: List[BeatSlot] = []
        prev_actual: Optional[str] = None  # 비트 간 변화 추적용
        for beat_i, ((bt, label), actual) in enumerate(zip(beats, actual_chord_per_beat)):
            if bt < b_start or bt >= b_end:
                continue

            # 표시 규칙:
            #   - 비트 1: 항상 현재 코드 표시 (없으면 None)
            #   - 그 외: 직전 비트와 다르면 표시
            if label == "1":
                display = actual
            elif actual is not None and actual != prev_actual:
                display = actual
            else:
                display = None

            bar_beats.append(BeatSlot(beat=label, chord=display, time=bt))
            prev_actual = actual

        if not bar_beats:
            continue

        # distinct chord 리스트 (호환용)
        seen: List[str] = []
        for slot in bar_beats:
            if slot["chord"] and slot["chord"] not in seen:
                seen.append(slot["chord"])
        if not seen:
            continue  # 코드가 하나도 없으면 마디 자체 제외

        bars.append(Bar(
            index=bi + 1,
            start=b_start,
            end=b_end,
            beats=bar_beats,
            chords=seen,
        ))

    return bars


def grouped_bars(
    audio_path: str | Path,
    timed_chords: List[Tuple[float, float, str]],
) -> List[Bar]:
    """audio + timed_chords → 비트 슬롯 마디 리스트.

    내부에서 마디 + 비트 검출 + 비트별 코드 매핑 모두 수행.
    """
    import librosa

    p = Path(audio_path)
    bar_starts = detect_bar_starts(p)
    if not bar_starts:
        log.warning("bar detection 실패 — 빈 리스트 반환")
        return []

    beats = detect_beats(p)
    if not beats:
        log.warning("beat detection 실패 — 빈 리스트 반환")
        return []

    duration = librosa.get_duration(path=str(p))
    return group_chords_by_bar(
        timed_chords, bar_starts, beats, audio_duration=duration,
    )
