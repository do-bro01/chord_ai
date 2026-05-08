"""기능 1, 2: 오디오 로드 + 코드 진행 추출 (demucs + autochord 파이프라인)

흐름:
  1. demucs(htdemucs)로 stem 분리 → vocals/drums/bass/other
  2. bass + other 채널만 합쳐 화성 신호 생성 (보컬·드럼 노이즈 제거)
  3. 임시 WAV로 저장 후 autochord(BTC 모델)에 입력
  4. autochord가 (start, end, "C:maj") 형식 라벨 리스트 반환
  5. 'C:maj' → 'C', 'A:min' → 'Am', 'C:7' → 'C7' 형태로 정규화
  6. 인접 동일 코드 합쳐서 진행 리스트로 반환

demucs 실패 시 원본 신호로 autochord 직접 실행 (fallback).
"""

from __future__ import annotations

import os

# autochord/tensorflow가 import되기 전에 반드시 설정해야 한다.
# tf 2.16+의 Keras 3는 autochord의 레거시 SavedModel을 못 읽으므로
# tf-keras (Keras 2 호환) 사용을 강제한다.
os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")

import logging
import tempfile
from pathlib import Path
from typing import List, Tuple

SUPPORTED_EXTS = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}
DEMUCS_MODEL_NAME = "htdemucs"
DEMUCS_HARMONIC_STEMS = ("bass", "other")  # 화성 정보가 담긴 stem들

log = logging.getLogger("chord_ai.audio_analysis")

# 무거운 라이브러리는 lazy import
_demucs_model = None
_demucs_device = None


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


def _separate_harmonic(audio_path: Path) -> Tuple["torch.Tensor", int]:
    """demucs로 stem 분리 후 bass+other 합친 텐서를 반환.

    반환: (waveform[channels, samples], sample_rate)
    """
    import numpy as np
    import torch
    import librosa
    from demucs.apply import apply_model

    model, device = _get_demucs()

    # librosa로 로드 — mp3/m4a/flac/ogg/wav 모두 지원하고 백엔드 일관됨.
    # torchaudio.load는 PyTorch 2.11+에서 torchcodec 의존성 이슈 있음.
    y, _sr = librosa.load(str(audio_path), sr=model.samplerate, mono=False)
    if y.ndim == 1:
        # 모노 → 스테레오 (demucs는 stereo 가정)
        y = np.stack([y, y], axis=0)
    elif y.shape[0] == 1:
        y = np.repeat(y, 2, axis=0)

    wav = torch.from_numpy(y).float()
    sr = model.samplerate

    # apply_model 입력은 (batch, channels, time)
    with torch.no_grad():
        sources = apply_model(model, wav[None].to(device), device=device, progress=False)
    sources = sources.cpu()  # (1, n_sources, channels, time)

    # 화성 stem 합성
    stem_names = list(model.sources)  # ['drums', 'bass', 'other', 'vocals']
    harmonic = None
    for name in DEMUCS_HARMONIC_STEMS:
        if name not in stem_names:
            continue
        idx = stem_names.index(name)
        track = sources[0, idx]
        harmonic = track if harmonic is None else harmonic + track

    if harmonic is None:
        raise RuntimeError(f"demucs 출력에서 화성 stem({DEMUCS_HARMONIC_STEMS}) 을 찾을 수 없습니다.")

    return harmonic, sr


def _save_temp_wav(waveform: "torch.Tensor", sr: int) -> Path:
    """torch tensor를 임시 WAV로 저장하고 경로 반환.

    soundfile은 (samples, channels) 형식을 받으므로 transpose 필요.
    torchaudio.save는 PyTorch 2.11+에서 torchcodec 의존성을 요구해서 사용 안 함.
    """
    import soundfile as sf

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmp.close()
    tmp_path = Path(tmp.name)

    # waveform: (channels, samples) → (samples, channels)
    arr = waveform.numpy().T
    sf.write(str(tmp_path), arr, sr, subtype="PCM_16")
    return tmp_path


def _normalize_label(label: str) -> str:
    """autochord의 'C:maj', 'A:min', 'D:7' 같은 라벨을 일반 표기로 변환."""
    if not label or label == "N":
        return ""

    if ":" not in label:
        return label

    root, quality = label.split(":", 1)

    # 매핑 — autochord의 BTC 라벨 셋 기준
    mapping = {
        "maj": "",
        "min": "m",
        "7": "7",
        "maj7": "maj7",
        "min7": "m7",
        "dim": "dim",
        "dim7": "dim7",
        "hdim7": "m7b5",
        "aug": "aug",
        "sus2": "sus2",
        "sus4": "sus4",
        "minmaj7": "mMaj7",
    }
    suffix = mapping.get(quality, quality)
    return f"{root}{suffix}"


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

    내부 단계가 실패할 수 있어, demucs 분리 실패 시 원본 신호로 fallback.
    """
    p = _validate_path(path)

    # autochord는 import 비용이 크므로 사용 시점에 import
    import autochord

    tmp_path: Path | None = None
    audio_for_recognize: str

    try:
        harmonic, sr = _separate_harmonic(p)
        tmp_path = _save_temp_wav(harmonic, sr)
        audio_for_recognize = str(tmp_path)
        log.info("demucs separation OK, using harmonic stem (%s)", tmp_path)
    except Exception as e:
        log.warning("demucs 분리 실패, 원본 신호로 fallback: %s", e)
        audio_for_recognize = str(p)

    try:
        raw = autochord.recognize(audio_for_recognize)
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)

    # raw: List[Tuple[float, float, str]]  — autochord 0.1.4 반환 형식
    result: List[Tuple[float, float, str]] = []
    for entry in raw:
        start, end, label = float(entry[0]), float(entry[1]), str(entry[2])
        normalized = _normalize_label(label)
        if not normalized:
            continue
        result.append((start, end, normalized))
    return result


def analyze(path: str | Path) -> List[str]:
    """파일 → 코드 진행 리스트 (인접 동일 코드 압축).

    기존 인터페이스 유지. main.py / backend 모두 이 함수를 호출.
    """
    timed = analyze_with_timing(path)
    chords = [c for _, _, c in timed]
    return _compress_consecutive(chords)
