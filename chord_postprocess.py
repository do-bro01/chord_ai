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
    """ParsedChord → 사람이 읽는 문자열.

    quality suffix는 music21.harmony.ChordSymbol이 파싱 가능한 표기로 통일.
    호환 안 되는 표기(`maj6`, `maj9`, `mMaj7`)는 가장 가까운 호환 표기로 매핑.
      - maj6 → 6   (major 6 is conventionally just "6")
      - maj9 → maj7 (lossy — 9th 텐션 손실, music21 미지원)
      - minmaj7 → mM7 (music21 표기)
    """
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
        "minmaj7": "mM7",
        "9": "9",
        "m9": "m9",
        "maj9": "maj7",
        "6": "6",
        "m6": "m6",
        "maj6": "6",
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


def chord_pitch_classes(parsed: ParsedChord) -> set:
    """ParsedChord → 구성음 pitch class 집합.

    텐션이 명시된 quality는 그대로 반영. 주요 quality만 다룸 — 알 수 없는 quality는 트라이어드로 fallback.
    """
    r = parsed.root_pc
    # 주요 quality별 인터벌 (semitones from root)
    intervals_by_quality = {
        "maj":      [0, 4, 7],
        "min":      [0, 3, 7],
        "maj7":     [0, 4, 7, 11],
        "m7":       [0, 3, 7, 10],
        "7":        [0, 4, 7, 10],
        "dim":      [0, 3, 6],
        "dim7":     [0, 3, 6, 9],
        "m7b5":     [0, 3, 6, 10],
        "aug":      [0, 4, 8],
        "sus4":     [0, 5, 7],
        "sus2":     [0, 2, 7],
        "minmaj7":  [0, 3, 7, 11],
        "9":        [0, 4, 7, 10, 2],
        "m9":       [0, 3, 7, 10, 2],
        "maj9":     [0, 4, 7, 11, 2],
        "6":        [0, 4, 7, 9],
        "m6":       [0, 3, 7, 9],
        "maj6":     [0, 4, 7, 9],
    }
    intervals = intervals_by_quality.get(parsed.quality, [0, 4, 7])
    return {(r + i) % 12 for i in intervals}


def normalize_label(label: str) -> str:
    """chordino의 Harte 슬래시(`C/5`, `D/2`)를 음 이름 슬래시(`C/G`, `D/E`)로 정규화.

    모든 라벨이 사용자에게 읽기 쉬운 형태로 나가도록 마지막 단계에서 호출.
    """
    parsed = parse_chord(label)
    if parsed is None:
        return label
    return chord_to_string(parsed)


def apply_bass_correction(
    segments_with_bass: List[Tuple[float, float, str, Optional[int], float]],
    key_root: str = "G",
    key_mode: str = "major",
) -> List[Segment]:
    """검출된 베이스 음을 이용해 chord 라벨 정정.

    입력: [(start, end, chord_label, bass_pc, confidence), ...]
    bass_pc=None이면 신뢰도 부족 → 정정 안 함.

    정정 규칙:
      1. 베이스가 chord_root와 같음 → 그대로 (단 라벨은 음 이름 표기로 정규화)
      2. m7 코드 + 베이스가 root - 4 (장3도 아래) → maj7 코드로 (Em7+bass=C → Cmaj7)
      3. major 트라이어드 + 베이스가 root - 3 (단3도 아래) → m7 코드로 (D+bass=B → Bm7)
      4. 베이스가 chord 구성음 안에 있음 → 인버전(slash) 표기 (단, root 외)
      5. 베이스가 chord 구성음 밖 → slash 표기 (poly-chord 표기, 예: C/D)

      단, 정정 후 결과가 키의 다이어토닉/borrowed 안에 들어와야 채택. 안 그러면 원본 유지.

    모든 출력 라벨은 마지막에 normalize_label로 정규화 (Harte `C/5` → `C/G` 등).
    """
    out: List[Segment] = []
    for start, end, label, bass_pc, conf in segments_with_bass:
        if bass_pc is None:
            out.append((start, end, normalize_label(label)))
            continue

        parsed = parse_chord(label)
        if parsed is None:
            out.append((start, end, label))
            continue

        current_bass = parsed.bass_pc if parsed.bass_pc is not None else parsed.root_pc
        if bass_pc == current_bass:
            out.append((start, end, normalize_label(label)))
            continue

        new_label = _try_bass_correction(parsed, bass_pc, key_root, key_mode)
        if new_label is None:
            out.append((start, end, normalize_label(label)))
        else:
            log.info("bass-correct: %s @[%.2f-%.2f] bass=%s conf=%.1f → %s",
                     label, start, end, _PC_TO_NOTE[bass_pc], conf, new_label)
            out.append((start, end, new_label))
    return out


def _try_bass_correction(
    parsed: ParsedChord,
    bass_pc: int,
    key_root: str,
    key_mode: str,
) -> Optional[str]:
    """베이스 정정 후 라벨을 만들고, 결과가 음악적으로 타당하면 반환. 아니면 None."""
    chord_pcs = chord_pitch_classes(parsed)

    # Rule 2: m7 + 베이스가 root - 4 → maj7 (상부구조 substitution)
    if parsed.quality == "m7":
        target_root = (parsed.root_pc - 4) % 12
        if bass_pc == target_root:
            new_chord = ParsedChord(target_root, "maj7", None, parsed.raw)
            new_label = chord_to_string(new_chord)
            return new_label if _is_acceptable(new_chord, key_root, key_mode) else None

    # Rule 3: major + 베이스가 root - 3 → m7 (상부구조 substitution)
    if parsed.quality in ("maj", "maj7", "6", "maj9"):
        target_root = (parsed.root_pc - 3) % 12
        if bass_pc == target_root:
            new_chord = ParsedChord(target_root, "m7", None, parsed.raw)
            new_label = chord_to_string(new_chord)
            return new_label if _is_acceptable(new_chord, key_root, key_mode) else None

    # Rule 4 + 5: slash 표기 (root와 다른 베이스)
    new_chord = ParsedChord(parsed.root_pc, parsed.quality, bass_pc, parsed.raw)
    return chord_to_string(new_chord) if _is_acceptable(new_chord, key_root, key_mode) else None


def _is_acceptable(parsed: ParsedChord, key_root: str, key_mode: str) -> bool:
    """음악적 타당성 — diatonic 또는 borrowed면 OK. foreign이면 거부."""
    cat = chord_membership(parsed, key_root, key_mode)
    return cat in ("diatonic", "borrowed")


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


# ============================================================================
# LLM 출력 검증 (PRD v2: 룰 베이스 검증 레이어)
# ============================================================================
#
# 목적: LLM이 뱉은 편곡 결과를 그대로 신뢰하지 않고, 음악 이론·표기 룰로
# 한 번 거른다. 이슈 11번에서 본 "music21 파싱 silent fail"을 이 단계에서
# 차단하고, 키 이탈(foreign chord)이 과도하면 LLM 재요청 신호로 사용한다.


@dataclass
class ChordValidation:
    """단일 코드 검증 결과."""
    label: str                  # LLM 원본 라벨
    normalized: str             # normalize_label 결과
    music21_ok: bool            # music21.harmony.ChordSymbol 파싱 가능 여부
    membership: str             # 'diatonic' | 'borrowed' | 'foreign' | 'unparseable'
    issue: Optional[str]        # 문제 설명 (없으면 None)


@dataclass
class ValidationReport:
    """편곡 한 섹션 전체의 검증 리포트."""
    chords: List[ChordValidation]
    foreign_count: int          # 키와 관계 없는 코드 개수
    unparseable_count: int      # parse_chord 실패 개수
    music21_failures: List[str] # music21이 못 읽는 라벨들
    has_issues: bool            # 위 셋 중 하나라도 있으면 True


def validate_music21_parse(label: str) -> bool:
    """music21.harmony.ChordSymbol이 파싱 가능한지 확인.

    정규화된 라벨에 대해 호출하는 것을 전제로 한다 (chord_to_string 출력).
    """
    if not label:
        return False
    try:
        from music21 import harmony
        harmony.ChordSymbol(label)
        return True
    except Exception:  # ChordException, ValueError, etc.
        return False


def validate_arrangement(
    chords: List[str],
    key_root: str,
    key_mode: str = "major",
) -> ValidationReport:
    """LLM이 뱉은 코드 진행을 검증.

    각 코드에 대해:
      1. normalize_label로 표기 정규화 (Harte 슬래시 → 음 이름, music21 미지원 표기 매핑)
      2. music21.harmony.ChordSymbol로 파싱 가능한지 확인
      3. parse_chord로 root/quality 분리 → chord_membership으로 키 안 위치 판정

    이 함수는 자동 수정하지 않는다. 호출자가 리포트를 보고:
      - foreign이 많으면 LLM에 재요청
      - music21_failures가 있으면 export 단계에서 silent fail 방지를 위해 처리
      - 임의로 nearest_diatonic 적용 가능 (선택)
    """
    items: List[ChordValidation] = []
    foreign_count = 0
    unparseable_count = 0
    music21_failures: List[str] = []

    for raw in chords:
        normalized = normalize_label(raw)
        m21_ok = validate_music21_parse(normalized)
        if not m21_ok:
            music21_failures.append(normalized)

        parsed = parse_chord(normalized)
        if parsed is None:
            unparseable_count += 1
            membership = "unparseable"
            issue = f"코드 파싱 실패: {raw!r}"
        else:
            membership = chord_membership(parsed, key_root, key_mode)
            if membership == "foreign":
                foreign_count += 1
                issue = f"키({key_root} {key_mode}) 외 코드"
            elif not m21_ok:
                issue = "music21 파싱 불가 (export 단계 silent fail 위험)"
            else:
                issue = None

        items.append(ChordValidation(
            label=raw,
            normalized=normalized,
            music21_ok=m21_ok,
            membership=membership,
            issue=issue,
        ))

    has_issues = bool(music21_failures) or foreign_count > 0 or unparseable_count > 0
    return ValidationReport(
        chords=items,
        foreign_count=foreign_count,
        unparseable_count=unparseable_count,
        music21_failures=music21_failures,
        has_issues=has_issues,
    )


def parse_key_string(key: str) -> Tuple[str, str]:
    """'C major', 'A minor' 형태의 키 문자열을 (root, mode)로 분리.

    LLM 입력 스키마는 'C major' 같은 문자열을 쓰지만, 검증 함수들은
    (root, mode) 튜플을 받는다. 이 헬퍼로 변환.
    """
    parts = key.strip().split()
    root = parts[0] if parts else "C"
    mode = parts[1].lower() if len(parts) > 1 else "major"
    if mode not in ("major", "minor"):
        mode = "major"
    return (root, mode)


def function_table_text(key: str) -> str:
    """LLM 프롬프트 주입용 — 주어진 키의 다이어토닉 + secondary dominant 표를 텍스트로.

    예: 'G major' →
        G major
          Diatonic: I=G, ii=Am, iii=Bm, IV=C, V=D, vi=Em, vii°=F#dim
          Secondary dominants: V/ii=E7, V/iii=F#7, V/IV=G7, V/V=A7, V/vi=B7
    """
    root, mode = parse_key_string(key)
    root_pc = _NOTE_TO_PC.get(root)
    if root_pc is None:
        return f"{key} (unknown root)"

    if mode == "minor":
        diatonic_specs = [
            (0, "i", "m"),
            (2, "ii°", "m7b5"),
            (3, "bIII", ""),
            (5, "iv", "m"),
            (7, "v", "m"),
            (8, "bVI", ""),
            (10, "bVII", ""),
        ]
        # 자연단음계 기준이지만, V (메이저)도 자주 차용됨 (harmonic minor V7)
        sec_dom_specs = [(3, "bIII"), (5, "iv"), (7, "v"), (8, "bVI"), (10, "bVII")]
    else:
        diatonic_specs = [
            (0, "I", ""),
            (2, "ii", "m"),
            (4, "iii", "m"),
            (5, "IV", ""),
            (7, "V", ""),
            (9, "vi", "m"),
            (11, "vii°", "dim"),
        ]
        sec_dom_specs = [(2, "ii"), (4, "iii"), (5, "IV"), (7, "V"), (9, "vi")]

    diatonic = []
    for offset, roman, qual in diatonic_specs:
        note = _PC_TO_NOTE[(root_pc + offset) % 12]
        diatonic.append(f"{roman}={note}{qual}")

    sec_dom = []
    for offset, target in sec_dom_specs:
        target_pc = (root_pc + offset) % 12
        v_pc = (target_pc + 7) % 12
        sec_dom.append(f"V/{target}={_PC_TO_NOTE[v_pc]}7")

    extra = ""
    if mode == "minor":
        extra = "\n  Note: 도미넌트 해결 시 v(마이너) 대신 V(메이저, 예: " \
                f"{_PC_TO_NOTE[(root_pc + 7) % 12]})를 차용하는 게 일반적."

    return (
        f"{root} {mode}\n"
        f"  Diatonic: {', '.join(diatonic)}\n"
        f"  Secondary dominants: {', '.join(sec_dom)}"
        f"{extra}"
    )
