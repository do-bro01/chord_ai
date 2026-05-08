"""코드 추출 결과 후처리 — 키 감지 + 다이어토닉 보정 + 잡음 필터.

목표:
  - 짧은 segment(<0.5s) 잡음 제거
  - 키 안에서 비다이어토닉 + 짧은 segment를 가까운 다이어토닉으로 스냅
  - "정당한 차용화음(E7, A7, G7 등 secondary dominant)"은 보존

비교: chordino 원본 vs 후처리 후
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

log = logging.getLogger("chord_ai.postprocess")

# 음이름 → 정수 (C=0, ..., B=11)
_NOTE_TO_PC = {
    "C": 0, "C#": 1, "Db": 1,
    "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4, "E#": 5,
    "F": 5, "F#": 6, "Gb": 6,
    "G": 7, "G#": 8, "Ab": 8,
    "A": 9, "A#": 10, "Bb": 10,
    "B": 11, "Cb": 11,
}
_PC_TO_NOTE = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Major scale degrees (intervals from tonic in pitch classes)
_MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]
_MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]


@dataclass
class ParsedChord:
    root_pc: int           # pitch class of the root (0-11)
    quality: str           # 'maj', 'min', 'maj7', 'm7', '7', 'dim', 'aug', 'sus4', 'sus2', etc.
    bass_pc: Optional[int] # pitch class of bass (None = root in bass)
    raw: str               # 원본 라벨


def parse_chord(label: str) -> Optional[ParsedChord]:
    """코드 라벨 파싱.

    예시:
      "C"       → root=0, quality=maj
      "Cm"      → root=0, quality=min
      "Cmaj7"   → root=0, quality=maj7
      "Cm7"     → root=0, quality=m7
      "C7"      → root=0, quality=7
      "Cdim"    → root=0, quality=dim
      "Cm7b5"   → root=0, quality=m7b5
      "F#"      → root=6, quality=maj
      "Bb"      → root=10, quality=maj
      "C/D"     → root=0, bass=2, quality=maj
      "C/5"     → root=0, bass=7 (5도=G), quality=maj  (chordino Harte 베이스도 표기)
      "Eaug"    → root=4, quality=aug
      "Bm7b5"   → root=11, quality=m7b5
    """
    if not label:
        return None
    s = label.strip()
    if not s or s in ("N", "X"):
        return None

    # 슬래시 분리
    bass_pc: Optional[int] = None
    if "/" in s:
        s, bass_str = s.split("/", 1)
        bass_str = bass_str.strip()
        # 숫자(베이스 도수)면 root + interval 로 계산
        if bass_str.isdigit():
            interval = int(bass_str)
            # 1=root, 2=major2, 3=major3, 4=perfect4, 5=perfect5, 6=major6, 7=major7
            interval_to_semitones = {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11}
            offset = interval_to_semitones.get(interval)
            # bass_pc은 아래 root 계산 후에 더해야 함 — 일단 표시만
            bass_interval_offset = offset
            bass_str = None
        else:
            bass_interval_offset = None
            # 음이름이면 그대로
            m = re.match(r"^([A-Ga-g])([#b]?)$", bass_str)
            if not m:
                bass_str = None
                bass_interval_offset = None
            else:
                note = m.group(1).upper() + m.group(2)
                bass_pc = _NOTE_TO_PC.get(note)
                bass_interval_offset = None
    else:
        bass_interval_offset = None

    # 루트 파싱
    m = re.match(r"^([A-G])([#b]?)(.*)$", s)
    if not m:
        return None
    root_note = m.group(1) + m.group(2)
    root_pc = _NOTE_TO_PC.get(root_note)
    if root_pc is None:
        return None
    quality_str = m.group(3).strip()

    # quality 정규화
    quality = _canonical_quality(quality_str)

    # bass interval offset 처리 (root 결정 후)
    if bass_interval_offset is not None:
        bass_pc = (root_pc + bass_interval_offset) % 12

    return ParsedChord(root_pc=root_pc, quality=quality, bass_pc=bass_pc, raw=label)


def _canonical_quality(q: str) -> str:
    """coding suffix → canonical quality 토큰."""
    q = q.strip()
    if q == "":
        return "maj"
    # 우선순위 높은 순서로 매칭
    table = [
        ("maj7", "maj7"),
        ("Maj7", "maj7"),
        ("M7", "maj7"),
        ("m7b5", "m7b5"),
        ("min7b5", "m7b5"),
        ("dim7", "dim7"),
        ("dim", "dim"),
        ("aug", "aug"),
        ("sus2", "sus2"),
        ("sus4", "sus4"),
        ("sus", "sus4"),
        ("mMaj7", "minmaj7"),
        ("minmaj7", "minmaj7"),
        ("m9", "m9"),
        ("m7", "m7"),
        ("min7", "m7"),
        ("min", "min"),
        ("maj9", "maj9"),
        ("maj6", "maj6"),
        ("m6", "m6"),
        ("min6", "m6"),
        ("9", "9"),
        ("7", "7"),
        ("6", "6"),
        ("m", "min"),
    ]
    for token, canonical in table:
        if q == token:
            return canonical
        if q.startswith(token):
            return canonical
    return q  # 모르는 quality는 그대로 반환


def chord_to_string(parsed: ParsedChord) -> str:
    """ParsedChord → 사람이 읽는 문자열."""
    root = _PC_TO_NOTE[parsed.root_pc]
    quality_str = {
        "maj": "",
        "min": "m",
        "maj7": "maj7",
        "m7": "m7",
        "7": "7",
        "dim": "dim",
        "dim7": "dim7",
        "m7b5": "m7b5",
        "aug": "aug",
        "sus2": "sus2",
        "sus4": "sus4",
        "minmaj7": "mMaj7",
        "9": "9",
        "m9": "m9",
        "maj9": "maj9",
        "6": "6",
        "m6": "m6",
        "maj6": "maj6",
    }.get(parsed.quality, parsed.quality)
    out = f"{root}{quality_str}"
    if parsed.bass_pc is not None and parsed.bass_pc != parsed.root_pc:
        out += f"/{_PC_TO_NOTE[parsed.bass_pc]}"
    return out


# --- 키 컨텍스트 ---

def diatonic_chords(key_root: str, key_mode: str = "major") -> List[ParsedChord]:
    """키의 다이어토닉 트라이어드 7개 반환 (확장 quality 포함)."""
    root_pc = _NOTE_TO_PC[key_root]
    if key_mode == "major":
        scale = _MAJOR_SCALE
        # 주요 chord quality (trad. major scale chords)
        qualities = ["maj", "min", "min", "maj", "maj", "min", "dim"]
        # 확장 (7th)
        ext_qualities = ["maj7", "m7", "m7", "maj7", "7", "m7", "m7b5"]
    else:  # minor (natural)
        scale = _MINOR_SCALE
        qualities = ["min", "dim", "maj", "min", "min", "maj", "maj"]
        ext_qualities = ["m7", "m7b5", "maj7", "m7", "m7", "maj7", "7"]

    result: List[ParsedChord] = []
    for deg, q in zip(scale, qualities):
        result.append(ParsedChord(root_pc=(root_pc + deg) % 12, quality=q, bass_pc=None, raw=""))
    for deg, q in zip(scale, ext_qualities):
        result.append(ParsedChord(root_pc=(root_pc + deg) % 12, quality=q, bass_pc=None, raw=""))
    return result


def common_borrowed_chords(key_root: str, key_mode: str = "major") -> List[ParsedChord]:
    """자주 쓰이는 차용화음. major key 기준 secondary dominants + 흔한 modal interchange."""
    root_pc = _NOTE_TO_PC[key_root]
    out: List[ParsedChord] = []
    if key_mode == "major":
        # secondary dominants: V7/x for x in II, III, IV, V, VI
        # 즉 D7 → V7 (이건 다이어토닉), A7 → V7/V, B7 → V7/vi, E7 → V7/ii(아니 V7/vi)... wait
        # G major 기준:
        #   - A7 = V7/V (도미넌트 of D)
        #   - B7 = V7/vi (도미넌트 of Em)
        #   - C7 = V7/IV (도미넌트 of F? F는 다이어토닉 아님), 잘 안 쓰임
        #   - D7 = V7 (다이어토닉)
        #   - E7 = V7/vi  ← user 곡에 있는 그것!
        #   - G7 = V7/IV (도미넌트 of C)  ← user 곡에 있음
        # 7도 위 메이저 (b7도 차용)
        secondary_dom_intervals = [
            (2, "7"),    # A7 (V/V)
            (4, "7"),    # B7 (V/vi)
            (4, "7"),    # E7 (V/ii) 라고 잘못 - 다시 계산
            (7, "7"),    # G7 (V/IV)
            (9, "7"),    # E7 등 (V/vi)
        ]
        # 사실 메이저 키의 대표적 secondary dominants는 V7/ii, V7/iii, V7/IV, V7/V, V7/vi
        # G major 기준 ii=Am(2 semitone), iii=Bm(4), IV=C(5), V=D(7), vi=Em(9)
        # V7/ii = E7 (E는 ii에서 5도 위 = 9+7=16 mod12 = 4) → E (root 4)
        # V7/iii = F#7 (4+7=11) → F# (root 11) - 거의 안 씀
        # V7/IV = G7 (5+7=12 mod12=0 → root_pc + 0... wait, V7/IV의 V는 IV의 5도 위)
        # 실제로 G major에서:
        #   V7/ii (E7), V7/iii (F#7), V7/IV (G7), V7/V (A7), V7/vi (B7)
        v_of_x_intervals = {
            "V7/ii":  (9 + 7) % 12,   # E (4)
            "V7/iii": (11 + 7) % 12,  # F# (6)? 아니 11+7=18 mod12=6 → F# 맞음
            "V7/IV":  (5 + 7) % 12,   # G (0)? 5+7=12 mod12=0 → C가 됨. 음, 아니다
            # 헷갈리니 직접 계산하자
        }
        # G major(root=7) 기준 흔한 secondary dominants (offset from tonic in semitones):
        # 절대 음 → 오프셋 환산:
        #   E7 (V/vi)  : E pc=4 → offset (4-7) mod 12 = 9
        #   A7 (V/V)   : A pc=9 → offset 2
        #   B7 (V/iii) : B pc=11 → offset 4
        #   C7 (V/IV)  : C pc=0 → offset 5
        #   G7 (V/IV의 V7 형태, 발라드에 흔함) : G pc=7 → offset 0
        #   D7 는 다이어토닉 V7 이라서 여기 안 넣음
        secondary_doms = [
            (9, "7"),   # E7 (V/vi)
            (2, "7"),   # A7 (V/V)
            (4, "7"),   # B7 (V/iii)
            (5, "7"),   # C7 (V/IV)
            (0, "7"),   # G7 (V/IV의 도미넌트)
            (9, "aug"), # E7#5 → Eaug (chordino 표기)
            (9, "maj"), # E 트라이어드 (V/vi 골격)
            (2, "maj"), # A 트라이어드 (V/V 골격)
            (4, "maj"), # B 트라이어드 (V/iii 골격)
        ]
        for offset, q in secondary_doms:
            out.append(ParsedChord(root_pc=(root_pc + offset) % 12, quality=q, bass_pc=None, raw=""))

        # modal interchange (parallel minor에서 빌려옴): bIII, bVI, bVII, iv, v°
        modal = [
            (3, "maj"),   # bIII (Bb)
            (8, "maj"),   # bVI (Eb)
            (10, "maj"),  # bVII (F)
            (5, "min"),   # iv (Cm)
            (7, "dim"),   # v° (rare)
        ]
        for offset, q in modal:
            out.append(ParsedChord(root_pc=(root_pc + offset) % 12, quality=q, bass_pc=None, raw=""))
    return out


def chord_membership(parsed: ParsedChord, key_root: str, key_mode: str = "major") -> str:
    """코드가 키 안에서 어떤 위치인지 분류.

    Returns: 'diatonic' | 'borrowed' | 'foreign'
    """
    diatonic = diatonic_chords(key_root, key_mode)
    borrowed = common_borrowed_chords(key_root, key_mode)

    def matches(a: ParsedChord, b: ParsedChord) -> bool:
        return a.root_pc == b.root_pc and _quality_compatible(a.quality, b.quality)

    for d in diatonic:
        if matches(parsed, d):
            return "diatonic"
    for b in borrowed:
        if matches(parsed, b):
            return "borrowed"
    return "foreign"


def _quality_compatible(q1: str, q2: str) -> bool:
    """두 quality가 '같은 부류'인지 (트라이어드 골격 일치 여부)."""
    if q1 == q2:
        return True
    # major 패밀리
    major_family = {"maj", "maj7", "maj9", "maj6", "6", "sus2", "sus4", "9"}
    minor_family = {"min", "m7", "m9", "m6", "minmaj7"}
    dom_family = {"7", "9", "13"}
    dim_family = {"dim", "dim7", "m7b5"}

    families = [major_family, minor_family, dom_family, dim_family]
    for fam in families:
        if q1 in fam and q2 in fam:
            return True
    return False


def nearest_diatonic(parsed: ParsedChord, key_root: str, key_mode: str = "major") -> ParsedChord:
    """비다이어토닉 코드를 가장 가까운 다이어토닉으로 스냅.

    전략:
      1. 같은 root의 다이어토닉이 있으면 그쪽으로 quality만 변경 (예: Bm7b5 → Bm7)
      2. 없으면 trial 음표 가장 많이 겹치는 다이어토닉
    """
    diatonic = diatonic_chords(key_root, key_mode)

    # 1. 같은 root
    for d in diatonic:
        if d.root_pc == parsed.root_pc:
            # quality는 다이어토닉 quality로 (텐션은 보존 시도)
            new_q = d.quality
            # 만약 원본이 7th을 표시하고 있고 다이어토닉도 7th을 가지면 그걸 우선
            if parsed.quality in ("7", "maj7", "m7"):
                # 다이어토닉 7th 사용
                ext = {q.quality for q in diatonic if q.root_pc == parsed.root_pc and q.quality in ("maj7", "m7", "m7b5", "7")}
                if "maj7" in ext and parsed.quality in ("maj7", "7"):
                    new_q = "maj7"
                elif "m7" in ext and parsed.quality == "m7":
                    new_q = "m7"
            return ParsedChord(root_pc=parsed.root_pc, quality=new_q, bass_pc=None, raw=parsed.raw)

    # 2. 음표 겹침 — 일단 root가 가장 가까운 (반음 거리) 다이어토닉으로
    def pc_dist(a: int, b: int) -> int:
        d = abs(a - b)
        return min(d, 12 - d)

    best = min(diatonic, key=lambda d: pc_dist(d.root_pc, parsed.root_pc))
    return ParsedChord(root_pc=best.root_pc, quality=best.quality, bass_pc=None, raw=parsed.raw)


# --- 메인 후처리 파이프라인 ---

Segment = Tuple[float, float, str]


def filter_short_segments(segments: List[Segment], min_dur: float = 0.5) -> List[Segment]:
    """짧은 segment를 인접한 더 긴 segment에 합침.

    각 짧은 segment를 양옆 중 더 긴 쪽으로 흡수. 결과적으로 segment 수 감소 + 잡음 제거.
    """
    if not segments:
        return segments
    segs = list(segments)
    changed = True
    while changed:
        changed = False
        for i, (s, e, c) in enumerate(segs):
            dur = e - s
            if dur >= min_dur:
                continue
            # 인접 segment와 합쳐버림
            if i == 0 and len(segs) > 1:
                # 다음으로 합침
                ns, ne, nc = segs[1]
                segs[1] = (s, ne, nc)
                segs.pop(0)
            elif i == len(segs) - 1:
                ps, pe, pc = segs[-2]
                segs[-2] = (ps, e, pc)
                segs.pop()
            else:
                ps, pe, pc = segs[i - 1]
                ns, ne, nc = segs[i + 1]
                # 더 긴 쪽으로 흡수
                if (pe - ps) >= (ne - ns):
                    segs[i - 1] = (ps, e, pc)
                else:
                    segs[i + 1] = (s, ne, nc)
                segs.pop(i)
            changed = True
            break
    return segs


def merge_consecutive(segments: List[Segment]) -> List[Segment]:
    """인접한 동일 코드 segment 병합."""
    if not segments:
        return segments
    out: List[Segment] = []
    cs, ce, cc = segments[0]
    for s, e, c in segments[1:]:
        if c == cc:
            ce = e
        else:
            out.append((cs, ce, cc))
            cs, ce, cc = s, e, c
    out.append((cs, ce, cc))
    return out


def apply_diatonic_correction(
    segments: List[Segment],
    key_root: str,
    key_mode: str = "major",
    suspect_max_dur: float = 1.5,
) -> List[Segment]:
    """비다이어토닉 + 짧은 segment를 다이어토닉으로 스냅.

    - diatonic: 그대로
    - borrowed (E7, A7, G7 등 secondary dom): 그대로 (의도적 사용으로 가정)
    - foreign + 짧음 (< suspect_max_dur): nearest_diatonic으로 변경
    - foreign + 김 (>= suspect_max_dur): 그대로 (의도적 modulation일 수 있음)
    """
    out: List[Segment] = []
    for s, e, c in segments:
        parsed = parse_chord(c)
        if parsed is None:
            out.append((s, e, c))
            continue
        membership = chord_membership(parsed, key_root, key_mode)
        if membership == "foreign" and (e - s) < suspect_max_dur:
            corrected = nearest_diatonic(parsed, key_root, key_mode)
            new_label = chord_to_string(corrected)
            log.info("correction: %s @[%.2f-%.2f] → %s (foreign, short)", c, s, e, new_label)
            out.append((s, e, new_label))
        else:
            out.append((s, e, c))
    return out


def detect_key(audio_path: str) -> Tuple[str, str]:
    """qm-keydetector로 곡 전체 키 추정.

    Returns: (root_note, mode) 예: ('G', 'major')
    """
    import librosa
    import vamp
    from collections import Counter

    y, sr = librosa.load(str(audio_path), sr=44100, mono=True)
    res = vamp.collect(y, sr, "qm-vamp-plugins:qm-keydetector", output="key")
    items = res.get("list", [])
    labels = [str(it.get("label", "")) for it in items if it.get("label")]
    if not labels:
        return ("C", "major")  # fallback
    most = Counter(labels).most_common(1)[0][0]
    # 라벨 형식: "G major" or "A minor"
    parts = most.split()
    root = parts[0] if parts else "C"
    mode = parts[1] if len(parts) > 1 else "major"
    return (root, mode)


def postprocess(
    segments: List[Segment],
    key_root: str = "G",
    key_mode: str = "major",
    min_dur: float = 0.5,
    suspect_max_dur: float = 1.5,
) -> List[Segment]:
    """전체 후처리 파이프라인."""
    log.info(
        "postprocess: %d segments, key=%s %s, min_dur=%.2f, suspect_max=%.2f",
        len(segments), key_root, key_mode, min_dur, suspect_max_dur,
    )
    # 1. 짧은 잡음 제거
    s1 = filter_short_segments(segments, min_dur=min_dur)
    s1 = merge_consecutive(s1)
    log.info("after short-filter + merge: %d segments", len(s1))

    # 2. 다이어토닉 보정
    s2 = apply_diatonic_correction(s1, key_root, key_mode, suspect_max_dur=suspect_max_dur)
    s2 = merge_consecutive(s2)
    log.info("after diatonic correction + merge: %d segments", len(s2))

    return s2
