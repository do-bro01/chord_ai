# 추출 정확도 비교 — autochord vs chordino vs 실측

테스트 곡: 유재하 - 사랑하기 때문에 (Acoustic Guitar)
실측 진행 (사용자 제공):

```
Loop A:  G  CM7  Bm7  E7(#5)  E7  Am9  C/D  D7  Gsus4  G
Loop B:  G  CM7  Bm7  E7(#5)  E7  Am7  C/D  D7
Loop C:  G  CM7  Bm7  E7(#5)  E7  Am7  C/D  D7  Gsus4  G  Gsus4  G7
Loop D:  CM7  Bm7  Am7  G  Gsus4
... (반복)
```

## 첫 ~50초(Loop A + Loop B 시작) 비교

| 실측 | autochord | chordino | 평가 |
|---|---|---|---|
| **G** | G ✓ | G ✓ | 둘 다 OK |
| **CM7** | C (텐션 손실) | Em (오인) → G → D | 둘 다 미스, autochord가 더 가까움 |
| **Bm7** | Em ✗ | (위에 포함) | autochord 일관 오인 |
| **E7(#5)** | D ✗ | **Eaug ✓** | chordino 정확 (Eaug=E7#5의 #5 텐션 정확 인식) |
| **E7** | Em ✗ | **E7 ✓** | chordino 완벽 |
| **Am9** | Am ✓ (텐션 손실) | Am ✓ (텐션 손실) | 둘 다 9 텐션은 못 잡음 |
| **C/D** | C (slash 손실) | D/2 (D with E bass — 베이스 오인) | 둘 다 미스, chordino가 슬래시 인지는 함 |
| **D7** | D | (생략됨) | autochord가 텐션 손실, chordino는 누락 |
| **Gsus4 G** | G | G | 둘 다 sus 못 잡음 |

## Loop B 후반(~30-50초) 비교

| 실측 | autochord | chordino | 평가 |
|---|---|---|---|
| G | G ✓ | G ✓ | OK |
| CM7 | (gap) | Em7 ✗ | 둘 다 미스 (chordino는 또 같은 오인) |
| Bm7 | C/D ✗ | D ✗ | 둘 다 미스 |
| E7#5 | (D 흐름) | **Eaug ✓** | chordino 정확 |
| E7 | (Em 흐름) | **E7 ✓** | chordino 완벽 |
| **Am7** | Am ✓ | **Am7 ✓** | chordino 텐션까지 정확 |
| C/D | C ✗ | C/5 (G bass — 오인) | 둘 다 미스 |
| **D7** | D | **D7 ✓** | chordino 텐션까지 정확 |

## 중반 후반(~80~100초) 일부 발췌

| 실측 위치 | autochord | chordino | 평가 |
|---|---|---|---|
| G7 | G | **G7 ✓** | chordino 정확 |
| CM7 | (놓침) | **Cmaj7 ✓** | chordino 정확 — 한 번 제대로 잡음! |
| Bm7 | (놓침) | **Bm7 ✓** | chordino 정확 |
| Am7 | Am | **Am7 ✓** | chordino 정확 |

## 정량 비교

| 지표 | autochord | chordino |
|---|---|---|
| 총 segment | 108 | 136 |
| 사용 코드 종류 | 10종 (G C Em D Am A Bm E Dm F) | 30+ (G C Em D Am Em7 Eaug E7 Am7 D7 Cmaj7 Bm7 G7 Dmaj6 Bm7b5 Am7b5 Am6 Dm7 F#aug Bbm6 Gmaj7 슬래시들 등) |
| **maj7 검출** | 0% | 가끔 (Cmaj7 ~1회, Gmaj7 ~1회) |
| **m7 검출** | 0% | 다수 (Am7, Bm7, Em7, Dm7) |
| **7 검출** | 0% | 다수 (E7, D7, G7) |
| **alt 검출 (E7#5)** | 0% | **거의 매번 Eaug로 정확 인식** |
| **Slash 검출** | 0% | 시도함 (단, bass note 오인 잦음 — C/D를 C/5나 D/2로) |
| **sus4 검출** | 0% | 0% (둘 다 sus는 못 잡음) |
| 추출 시간 | 46.9s | 38.7s |

## 주요 발견

### chordino의 강점
1. **E7(#5) → Eaug 매번 정확** — autochord가 D/Em으로 일관되게 틀린 자리를 깔끔히 잡음
2. **E7, D7, G7, Am7, Bm7 등 7th 코드 직접 출력** — 발라드 텐션 복구의 핵심
3. **Cmaj7, Gmaj7도 가끔 정확히 잡음** (일관되진 않음)
4. **Am6, Dmaj6 같은 변형 6 코드도 시도함**

### chordino의 약점 (개선 여지)
1. **CM7 → Em7 일관 오인** (상부구조 공유: C E G B vs E G B D)
2. **C/D → C/5 또는 D/2 같은 베이스 음 오인** (슬래시 인식은 되지만 베이스 음 정확도 낮음)
3. **Gsus4 미검출** (sus4가 라벨에 거의 안 나옴)
4. **잡음성 짧은 segment 다수** — Bm7b5, Am7b5, Bbm6, F#aug 같은 비다이어토닉 코드가 몇 군데 끼어있음 (실제로는 Am/Bm을 잘못 분석한 결과)
5. **Loop마다 인식 일관성 낮음** — 같은 CM7 위치를 어디선 Em7, 어디선 Cmaj7로 (cycle별로 흔들림)

### autochord에 비교한 chordino의 트레이드오프
- ✅ 텐션 코드 인식 (autochord 압도)
- ❌ 트라이어드 골격 정확도는 비슷하거나 약간 떨어짐 (chordino도 CM7→Em7 같은 오인 있음)
- ❌ 짧은 잡음 segment 더 많음 (136 vs 108)

## 결론

**chordino는 7th 텐션 회복이라는 본래 목표는 달성했지만, 트라이어드 골격에서 같은 종류의 오류가 남아있고 잡음 segment가 더 많다.**

→ 두 가지 보완책 후보:
1. **앙상블** — autochord(골격 안정) + chordino(텐션 풍부)을 결합
2. **다이어토닉/키 보정 + 길이 필터** — chordino 결과를 후처리 (Bm7b5, Am7b5, Bbm6 같은 잡음 제거)
3. **LLM 보정** — 추출 결과 + 키 + 장르를 LLM에 줘서 일관된 진행으로 정리
