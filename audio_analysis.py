"""기능 1, 2: 오디오 로드 + 코드 진행 추출

파이프라인 (현재):
  1. qm-keydetector로 곡 키 감지 (예: G major, D minor)
  2. demucs(htdemucs)로 stem 분리 → vocals/drums/bass/other (캐시됨)
  3. bass+other 합친 화성 stem → chordino(NNLS-Chroma) 코드 추출
     - usehartesyntax=1 → maj7/m7/7/sus 등 확장 라벨 출력
  4. 후처리:
     a. 짧은 잡음 segment(<0.5s) 인접 segment에 흡수
     b. 다이어토닉 보정 — 비다이어토닉 + 짧은 segment를 다이어토닉으로 스냅
        (E7, A7 등 secondary dominants는 보존)
  5. 베이스 검출 + 보정 — bass stem chroma_cqt로 segment별 베이스 음 추출
     a. CM7↔Em7 같은 상부구조 substitution 정정
     b. 슬래시 코드 베이스 음 정정

이전: autochord(BTC) 단독 사용 → 7th 텐션 0% 검출 + 일관된 substitution 오류로 교체.

External tools (이미 설치됨):
  - demucs (PyTorch) — stem 분리
  - vamp + chordino + qm-keydetector — vamp plugin pack
  - librosa — chroma_cqt
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Tuple

SUPPORTED_EXTS = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}
DEMUCS_MODEL_NAME = "htdemucs"
DEMUCS_HARMONIC_STEMS = ("bass", "other")  # 화성 정보가 담긴 stem들

log = logging.getLogger("chord_ai.audio_analysis")

# 무거운 라이브러리는 lazy import
_demucs_model = None
_demucs_device = None

# demucs 분리 결과 캐시 — 같은 파일을 여러 모듈(chordino, bass_detector 등)에서
# 사용해도 demucs를 한 번만 돌리도록.
# key: f"{absolute_path}:{mtime}", value: (stems_dict, sample_rate)
_separation_cache: dict = {}


def _validate_path(path: str | Path) -> Path:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"음원 파일을 찾을 수 없습니다: {p}")
    if p.suffix.lower() not in SUPPORTED_EXTS:
        raise ValueError(
            f"지원하지 않는 포맷입니다: {p.suffix}. "
            f"지원 포맷: {', '.join(sorted(SUPPORTED_EXTS))}"
        )
    return p


def _get_demucs():
    """htdemucs 모델 + 디바이스를 한 번 로드하고 캐시."""
    global _demucs_model, _demucs_device
    if _demucs_model is not None:
        return _demucs_model, _demucs_device

    import torch
    from demucs.pretrained import get_model

    if torch.backends.mps.is_available():
        device = "mps"
    elif torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"

    model = get_model(DEMUCS_MODEL_NAME)
    model.to(device)
    model.eval()

    _demucs_model = model
    _demucs_device = device
    log.info("demucs %s loaded on %s", DEMUCS_MODEL_NAME, device)
    return model, device


def separate_all_stems(audio_path: Path) -> Tuple[dict, int]:
    """demucs로 모든 stem 분리, dict로 반환. 같은 파일 재호출 시 캐시 사용.

    반환: ({'drums': tensor, 'bass': tensor, 'other': tensor, 'vocals': tensor}, sample_rate)
          각 tensor는 (channels, samples) 형식 stereo.
    """
    import numpy as np
    import torch
    import librosa
    from demucs.apply import apply_model

    audio_path = Path(audio_path).resolve()
    cache_key = f"{audio_path}:{audio_path.stat().st_mtime}"
    if cache_key in _separation_cache:
        log.info("demucs cache hit: %s", audio_path.name)
        return _separation_cache[cache_key]

    model, device = _get_demucs()

    y, _sr = librosa.load(str(audio_path), sr=model.samplerate, mono=False)
    if y.ndim == 1:
        y = np.stack([y, y], axis=0)
    elif y.shape[0] == 1:
        y = np.repeat(y, 2, axis=0)

    wav = torch.from_numpy(y).float()
    sr = model.samplerate

    with torch.no_grad():
        sources = apply_model(model, wav[None].to(device), device=device, progress=False)
    sources = sources.cpu()  # (1, n_sources, channels, time)

    stem_names = list(model.sources)
    stems = {name: sources[0, idx] for idx, name in enumerate(stem_names)}
    _separation_cache[cache_key] = (stems, sr)
    log.info("demucs separation done: %s, stems=%s", audio_path.name, list(stems.keys()))
    return stems, sr


def _separate_harmonic(audio_path: Path) -> Tuple["torch.Tensor", int]:
    """demucs로 stem 분리 후 bass+other 합친 텐서를 반환.

    반환: (waveform[channels, samples], sample_rate)
    """
    stems, sr = separate_all_stems(audio_path)
    harmonic = None
    for name in DEMUCS_HARMONIC_STEMS:
        if name not in stems:
            continue
        track = stems[name]
        harmonic = track.clone() if harmonic is None else harmonic + track

    if harmonic is None:
        raise RuntimeError(f"demucs 출력에서 화성 stem({DEMUCS_HARMONIC_STEMS}) 을 찾을 수 없습니다.")

    return harmonic, sr


def get_bass_stem(audio_path: Path) -> Tuple["torch.Tensor", int]:
    """demucs의 bass stem만 반환 (베이스 음 추출용)."""
    stems, sr = separate_all_stems(audio_path)
    if "bass" not in stems:
        raise RuntimeError("demucs 출력에 bass stem이 없습니다.")
    return stems["bass"], sr


# --- 후처리 파이프라인 파라미터 (튜닝값은 STEP1 평가에서 도출) ---
_PIPELINE_MIN_DUR = 0.5            # 짧은 잡음 segment 임계값(초)
_PIPELINE_SUSPECT_MAX_DUR = 3.0    # 비다이어토닉 보정 적용 최대 길이(초)
_PIPELINE_BASS_CONF_RATIO = 2.5    # 베이스 검출 신뢰도 임계값(top1/top2)


def _compress_consecutive(chords: List[str]) -> List[str]:
    """인접한 동일 코드 합치기."""
    out: List[str] = []
    for c in chords:
        if not c:
            continue
        if not out or out[-1] != c:
            out.append(c)
    return out


def analyze_with_timing(path: str | Path) -> List[Tuple[float, float, str]]:
    """파일 → [(start_sec, end_sec, chord), ...] 시간축 코드 진행.

    내부적으로 chordino + 후처리 + 베이스 보정 파이프라인 실행.
    """
    # 무거운 모듈은 호출 시점에 import (CLI/백엔드 cold start 영향 줄임)
    from chordino_extractor import analyze_with_timing as chordino_analyze
    from chord_postprocess import (
        detect_key,
        filter_short_segments,
        apply_diatonic_correction,
        apply_bass_correction,
        merge_consecutive,
    )
    from bass_detector import detect_bass_per_segment

    p = _validate_path(path)

    # 1. 키 감지 (qm-keydetector)
    try:
        key_root, key_mode = detect_key(p)
        log.info("detected key: %s %s", key_root, key_mode)
    except Exception as e:
        log.warning("key detection failed (%s) — fallback to G major", e)
        key_root, key_mode = "G", "major"

    # 2. chordino로 raw 코드 추출 (demucs harmonic stem 사용)
    raw = chordino_analyze(p, use_demucs_stem=True, use_harte_syntax=True)
    if not raw:
        log.warning("chordino returned 0 segments")
        return []

    # 3. 짧은 잡음 필터 + 인접 병합 + 다이어토닉 보정
    s1 = filter_short_segments(raw, min_dur=_PIPELINE_MIN_DUR)
    s1 = merge_consecutive(s1)
    s2 = apply_diatonic_correction(
        s1, key_root, key_mode, suspect_max_dur=_PIPELINE_SUSPECT_MAX_DUR
    )
    s2 = merge_consecutive(s2)

    # 4. 베이스 검출 + 보정 (CM7↔Em7, slash 등)
    try:
        seg_with_bass = detect_bass_per_segment(
            p, s2, confidence_ratio=_PIPELINE_BASS_CONF_RATIO
        )
        s3 = apply_bass_correction(seg_with_bass, key_root, key_mode)
        s3 = merge_consecutive(s3)
    except Exception as e:
        log.warning("bass correction failed (%s) — using diatonic-only result", e)
        s3 = s2

    return s3


def analyze(path: str | Path) -> List[str]:
    """파일 → 코드 진행 리스트 (인접 동일 코드 압축).

    main.py / backend 모두 이 함수를 호출. 시그니처 그대로 유지.
    """
    timed = analyze_with_timing(path)
    chords = [c for _, _, c in timed]
    return _compress_consecutive(chords)
