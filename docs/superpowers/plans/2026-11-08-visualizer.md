# Fly-in Visualizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 手順を終えるたびに `- [ ]` を `- [x]` に書き換える（✓）。

**Goal:** Fly-in のマップファイルと出力ファイルを読み、各ターンの動きを動画プレーヤー風に再生し、規則違反を赤で示す pygame アプリを作る。

**Architecture:** 読み込み（`fly_map.py` / `replay.py`）、状態の復元と検証（`simulation.py`）、再生の時間管理（`player.py`）、座標計算（`layout.py`）は pygame に依存しない純粋なモジュールにして pytest でテストする。描画と入力（`view.py` / `panel.py` / `app.py`）だけが pygame を使い、手で確認する。

**Tech Stack:** Python 3.14, uv, pygame-ce（pygame 本家に 3.14 の wheel がないため。import 名は `pygame`）, pytest, flake8, mypy, ruff, pre-commit

**Spec:** `docs/superpowers/specs/2026-11-08-visualizer-design.md`

## Global Constraints

- Python `>=3.14`、`.python-version` は `3.14`。
- 行長 79 桁（flake8 / ruff）。mypy は `--warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs`。
- docstring は Google スタイル・英語。画面の文言と違反メッセージは日本語。
- `pytest.param` の id はケース番号だけ（例 `V3`、枝番は `V3a`）。
- Fly-in 本体を import しない。数え方は Fly-in の `ReservationTable` と一致させる。
- 1x = 1 ターン 1 秒。速度は 0.5 / 1 / 2 / 4。
- start / end の上限は `nb_drones`。既定値 `zone=normal`、`max_drones=1`、`max_link_capacity=1`。

## Review Focus

1. Fly-in の実際の出力（全マップ）で違反が 1 件も出ないこと（誤検出はアンチゴール）→ Task 4 の V20。
2. 出力ファイルが CRLF・末尾改行なし・末尾に空行あり → Task 2 の O6〜O8。
3. 同じターンに、着陸するドローンと同じリンクへ進入するドローンがいる（着陸はリンクを数えない）→ Task 3 の S6。
4. ターン 0 しかない出力（空ファイル）でシーク・再生しても落ちない → Task 5 の P9。
5. 日本語フォントがない環境（評価機が Linux など）で文字化けする → Task 7 で候補フォントを順に探し、見つからなければ起動時に標準エラーへ警告を出す。手で確認する。

---

### Task 1: プロジェクトの土台とマップの読み込み

**Files:**
- Create: `pyproject.toml`, `.python-version`, `.flake8`, `.gitignore`, `.pre-commit-config.yaml`, `Makefile`, `README.md`
- Create: `fly_map.py`
- Test: `tests/__init__.py`, `tests/test_fly_map.py`

**Interfaces:**
- Produces:
  - `type ZoneName = str`、`type Link = frozenset[ZoneName]`
  - `class ZoneType(StrEnum)`: `NORMAL`, `BLOCKED`, `RESTRICTED`, `PRIORITY`
  - `@dataclass(frozen=True) Zone(name, x: int, y: int, zone_type: ZoneType, color: str | None, max_drones: int)`
  - `@dataclass(frozen=True) Connection(a, b, max_link_capacity: int)`、プロパティ `link -> Link`、`name -> str`（`"a-b"`）
  - `@dataclass(frozen=True) FlyMap(nb_drones, start, end, zones: dict[ZoneName, Zone], connections: list[Connection])`
    - `connection_between(a, b) -> Connection | None`（向きを問わない）
    - `connection_named(name: str) -> Connection | None`（`"a-b"` / `"b-a"` どちらでも）
  - `class MapFileError(Exception)`: `__init__(self, line_no: int, message: str)`、メッセージ `line <n>: <message>`
  - `parse_map(path: str) -> FlyMap`

- [ ] **Step 1: 土台のファイルを作る**

Fly-in（`/Users/fu/dev/Fly-in`）の `pyproject.toml`・`.flake8`・`.pre-commit-config.yaml`・`Makefile` を写し、name を `fly-in-visualizer`、dependencies を `["pygame-ce>=2.5.8"]` にする。Makefile の `run` は `@uv run python main.py $(MAP) $(OUT)`、既定値 `MAP ?= tests/fixtures/maps/easy/02_simple_fork.txt`、`OUT ?= tests/fixtures/outputs/easy/02_simple_fork.txt`。`.gitignore` は `.venv/`、`__pycache__/`、各種 cache、`.superpowers/`。README は起動方法と操作キーだけ。

- [ ] **Step 2: `uv sync` を実行し、`uv run python -c "import pygame; print(pygame.version.ver)"` が 2.5 系を表示することを確認**

- [ ] **Step 3: 失敗するテストを書く**（`tests/test_fly_map.py`、マップは `tmp_path` に書いて読む）

- `M1`: Fly-in の `maps/easy/02_simple_fork.txt` と同じ内容 → `nb_drones == 4`、`start == "start"`、`end == "goal"`、`zones["junction"].max_drones == 2`、`zones["junction"].color == "yellow"`、`connections[0] == Connection("start", "junction", 2)`、`connections[1].max_link_capacity == 1`
- `M2`: start / end の `max_drones` は `nb_drones`（`[max_drones=1]` と書かれていても）
- `M3`: `[zone=restricted]` → `ZoneType.RESTRICTED`、指定なし → `NORMAL`
- `M4`: `#` で始まる行・空行は飛ばす
- `M5`: `connection_between("junction", "start")` と `connection_named("junction-start")` が `start-junction` の接続を返す。存在しなければ `None`
- `M6`（parametrize）: 読めない行 → `MapFileError`、`match=r"^line 3:"`。ケース: `hub: a 0`（引数不足）、`foo: x`（未知のキー）、`hub: a x 0`（整数でない）
- `M7`: start_hub がない → `MapFileError`

- [ ] **Step 4: `uv run pytest tests/test_fly_map.py -v` が FAIL（import できない）することを確認**

- [ ] **Step 5: `fly_map.py` を実装する**

行は `key: args [k=v ...]` を `str.partition(":")` と `[` の位置で分ける程度でよい（Fly-in ほど厳密でなくてよい）。

- [ ] **Step 6: `uv run pytest tests/test_fly_map.py -v` が PASS、`make lint` が通ることを確認**

- [ ] **Step 7: コミット**（`git add -A && git commit -m "プロジェクトの土台とマップの読み込みを追加"`）

---

### Task 2: 出力ファイルの読み込みと色付き表示用の分解

**Files:**
- Create: `replay.py`
- Test: `tests/test_replay.py`

**Interfaces:**
- Produces:
  - `type RGB = tuple[int, int, int]`
  - `@dataclass(frozen=True) Move(drone: int, name: str)`
  - `@dataclass(frozen=True) TurnRecord(raw: str, moves: list[Move])`（`raw` は色コード付きの元の行、改行なし）
  - `class OutputFileError(Exception)`: `MapFileError` と同じ形
  - `strip_ansi(text: str) -> str`
  - `parse_line(line_no: int, line: str) -> TurnRecord`（1 行を分解。書式エラーは `OutputFileError(line_no, ...)`）
  - `read_output(path: str) -> list[TurnRecord]`（要素 i がターン i+1。各行は `parse_line` で分解）
  - `colored_segments(raw: str) -> list[tuple[str, RGB | None]]`

- [ ] **Step 1: 失敗するテストを書く**（ファイルは `tmp_path` に bytes で書く）

- `O1`: `"D1-a D2-b\nD1-e\n"` → 2 ターン、`moves == [Move(1, "a"), Move(2, "b")]`、`[Move(1, "e")]`
- `O2`: 色付き `"D1-\033[38;2;255;230;0mjunction\033[0m"` → `Move(1, "junction")`、`raw` は色コードを含んだまま
- `O3`: 途中の空行は空の `moves` のターン
- `O4`: 接続名 `"D1-s-r"` → `Move(1, "s-r")`
- `O5`（parametrize）: 書式エラー → `OutputFileError`、`match=r"^line 2:"`。ケース: `"x1-a"`、`"D-a"`、`"D1a"`、`"D1-"`、`"D0x-a"`
- `O6`: CRLF（`b"D1-a\r\nD1-e\r\n"`）→ O1 と同じ結果
- `O7`: 末尾に改行なし → 同じ結果
- `O8`: 末尾の空行（`"D1-a\nD1-e\n\n\n"`）はターンに数えない → 2 ターン
- `O9`: `colored_segments("D1-\033[38;2;80;140;255mpath_a\033[0m D2-x")` → `[("D1-", None), ("path_a", (80, 140, 255)), (" D2-x", None)]`
- `O10`: 空ファイル → `[]`

- [ ] **Step 2: `uv run pytest tests/test_replay.py -v` が FAIL することを確認**

- [ ] **Step 3: `replay.py` を実装する**

移動は正規表現 `^D(\d+)-(.+)$`。ANSI は `\033\[[0-9;]*m`。`colored_segments` は `38;2;r;g;b` で色開始、`0` で解除、ほかの SGR は無視。

- [ ] **Step 4: `uv run pytest tests/test_replay.py -v` が PASS、`make lint` が通ることを確認**

- [ ] **Step 5: コミット**（`"出力ファイルの読み込みを追加"`）

---

### Task 3: 状態の復元と使用数

**Files:**
- Create: `simulation.py`
- Test: `tests/test_simulation.py`（テスト用に `make_map(hubs, links, nb_drones=2, capacities=None, link_capacities=None) -> FlyMap` を置く。Fly-in の `tests/test_planner.py` の `make_map` と同じ形。start `s`、end `e`）

**Interfaces:**
- Consumes: Task 1 の `FlyMap` / `Connection` / `Link`、Task 2 の `TurnRecord` / `Move`
- Produces:
  - `@dataclass(frozen=True) InFlight(connection: Connection, dst: ZoneName)`
  - `type Position = ZoneName | InFlight`
  - `class ViolationKind(StrEnum)`（Task 4 で中身を使う。ここで全メンバーを定義）: `ZONE_FULL`, `LINK_FULL`, `NO_CONNECTION`, `BLOCKED`, `RESTRICTED_SKIPPED`, `NOT_LANDED`, `NOT_RESTRICTED`, `UNKNOWN_NAME`, `UNKNOWN_DRONE`, `DUPLICATE_DRONE`, `MOVED_AFTER_END`, `NOT_DELIVERED`
  - `@dataclass(frozen=True) Violation(kind: ViolationKind, message: str, zone: ZoneName | None = None, link: Link | None = None, drone: int | None = None)`
  - `@dataclass TurnState(turn: int, positions: dict[int, Position], zone_counts: dict[ZoneName, int], link_counts: dict[Link, int], violations: list[Violation])`、プロパティ `used_links -> set[Link]`（`link_counts` の値が 1 以上のもの）
  - `simulate(fly_map: FlyMap, records: list[TurnRecord]) -> list[TurnState]`（長さ `len(records) + 1`、要素 0 はターン 0）

- [ ] **Step 1: 失敗するテストを書く**（`TurnRecord` は `read_output` を通さず直接作るヘルパー `turns(*lines: str) -> list[TurnRecord]` を置き、各行は `replay.parse_line` で分解する）

- `S1`: ターン 0 は全ドローンが start、`zone_counts["s"] == 2`
- `S2`: 行に現れないドローンは前のターンの位置のまま
- `S3`: 待機中のドローンもゾーンに数える。`s-a-e` で `["D1-a", "", "D1-e"]` → ターン 2 で `zone_counts["a"] == 1`、`link_counts` は空
- `S4`: 通常の移動はリンクを数える。向きは区別しない（`a-s` と書かれた接続を `s → a` に使っても `link_counts[frozenset({"s","a"})] == 1`）
- `S5`: restricted 進入 `"D1-s-r"` → 位置 `InFlight(sr, "r")`、ゾーンには数えない、リンクは 1。次の行 `"D1-r"` で着陸 → `zone_counts["r"] == 1`、リンクは数えない
- `S6`: 同じターンに D1 が着陸し D2 が同じリンクへ進入 → そのターンの `link_counts[sr] == 1`（Review Focus 3）
- `S7`: end に着いたドローンは以降の行に現れなくても end に数え続ける

- [ ] **Step 2: `uv run pytest tests/test_simulation.py -v` が FAIL することを確認**

- [ ] **Step 3: `simulate` を実装する（このタスクでは `violations` は常に空でよい）**

接続名の移動の行き先 `dst` は、接続の両端のうち現在のゾーンでないほう。どちらの端も現在のゾーンでなければ、restricted の端、それもなければ `b`。

- [ ] **Step 4: `uv run pytest tests/test_simulation.py -v` が PASS、`make lint` が通ることを確認**

- [ ] **Step 5: コミット**（`"状態の復元と使用数を追加"`）

---

### Task 4: 規則違反の検出

**Files:**
- Modify: `simulation.py`
- Create: `tests/fixtures/maps/**`（Fly-in の `maps/` を丸ごと写す）、`tests/fixtures/outputs/**`（同じ相対パスで、各マップの Fly-in の出力）
- Test: `tests/test_violations.py`

**Interfaces:**
- Consumes: Task 3 の `simulate` / `Violation` / `ViolationKind`
- Produces: `simulate` が `TurnState.violations` を埋める。各違反の `zone` / `link` / `drone` は、赤く描く対象を指す。

違反と設定するフィールド（メッセージは例。文言は自由）:

| kind | 条件 | zone / link / drone | message 例 |
|---|---|---|---|
| ZONE_FULL | ゾーンの使用数 > 上限 | zone | `junction: 3/2 (max_drones 超過)` |
| LINK_FULL | リンクの使用数 > 上限 | link | `s-a: 2/1 (max_link_capacity 超過)` |
| NO_CONNECTION | 接続のないゾーンへ移動、または接続の上だが現在のゾーンにつながっていない | drone | `D3: path_a-goal は接続がない` |
| BLOCKED | blocked ゾーンに入った | zone, drone | `D1: x は blocked` |
| RESTRICTED_SKIPPED | 接続の上を経由せずに restricted へ入った | zone, drone | `D1: r へ 1 ターンで入った` |
| NOT_LANDED | 前のターンに接続の上で、このターン `dst` にいない | drone | `D1: r に着陸していない` |
| NOT_RESTRICTED | 接続の上の `dst` が restricted でない | link, drone | `D1: a-b の先は restricted ではない` |
| UNKNOWN_NAME | ゾーンにも接続にもない名前 | drone | `D1: zz は存在しない` |
| UNKNOWN_DRONE | 番号が 1〜nb_drones の外 | なし | `D9 は存在しない` |
| DUPLICATE_DRONE | 同じ行に同じドローンが 2 回 | drone | `D1 が 2 回書かれている` |
| MOVED_AFTER_END | end に着いた後に動いた | drone | `D1: end の後に動いた` |
| NOT_DELIVERED | 最終ターンで end にいない（最終ターンの状態に付ける） | drone | `D2: end に着いていない` |

UNKNOWN_NAME / UNKNOWN_DRONE / DUPLICATE_DRONE の 2 回目は位置を変えない。NOT_LANDED で行に現れなければ `InFlight` のまま。

- [ ] **Step 1: フィクスチャを作る**

```bash
cp -R /Users/fu/dev/Fly-in/maps tests/fixtures/maps
rm tests/fixtures/maps/README.md
cd /Users/fu/dev/Fly-in && for m in $(cd maps && find . -name '*.txt'); do
  mkdir -p /Users/fu/dev/fly-in-visualizer/tests/fixtures/outputs/$(dirname $m)
  uv run python main.py maps/$m > /Users/fu/dev/fly-in-visualizer/tests/fixtures/outputs/$m
done
```

`tests/fixtures/outputs/` に 10 ファイルでき、どれも空でないことを確認。

- [ ] **Step 2: 失敗するテストを書く**（`V1`〜`V12` は表の各行に 1 つずつ、Task 3 の `make_map` / `turns` を使う。それぞれ違反のあるターンで `[v.kind for v in states[t].violations] == [期待する kind]` と、表のフィールドが正しいことを確かめる。加えて）

- `V13`: 正しい出力（Task 3 の S1〜S7 の入力すべて）では全ターン違反なし
- `V20`（parametrize、id はマップの相対パス）: `tests/fixtures/` の全マップ × 出力で、全ターン `violations == []`（Review Focus 1）

- [ ] **Step 3: `uv run pytest tests/test_violations.py -v` が FAIL することを確認**

- [ ] **Step 4: `simulate` に検出を追加する**

- [ ] **Step 5: `uv run pytest -v` が全部 PASS、`make lint` が通ることを確認。V20 が落ちたら、Fly-in の出力ではなく検出の数え方を疑い、`/Users/fu/dev/Fly-in/reservation.py` と突き合わせる**

- [ ] **Step 6: コミット**（`"規則違反の検出とフィクスチャを追加"`）

---

### Task 5: 再生の時間管理

**Files:**
- Create: `player.py`
- Test: `tests/test_player.py`

**Interfaces:**
- Produces: `SPEEDS: tuple[float, ...] = (0.5, 1.0, 2.0, 4.0)`、`class Player`:
  - `__init__(self, last_turn: int)`。初期値 `time = 0.0`、`playing = False`、`speed = 1.0`
  - 属性 `time: float`（0〜last_turn。1.5 はターン 1 → 2 の途中）、`playing: bool`、`speed: float`、`last_turn: int`
  - プロパティ `from_turn -> int`（`floor(time)`）、`shown_turn -> int`（`ceil(time)`）、`alpha -> float`（`time - from_turn`）
  - `toggle() -> None`、`step(delta: int) -> None`、`seek(turn: int) -> None`、`set_speed(speed: float) -> None`、`update(dt: float) -> None`（秒）

- [ ] **Step 1: 失敗するテストを書く**

- `P1`: `update(0.5)` を再生中に呼ぶと `time == 0.5`、`from_turn == 0`、`shown_turn == 1`、`alpha == 0.5`
- `P2`: 停止中は `update` で `time` が変わらない
- `P3`: `set_speed(2.0)` で `update(0.5)` → `time == 1.0`
- `P4`: 最終ターンを越えない。`last_turn=2` で `update(10)` → `time == 2.0`、`playing is False`
- `P5`: 最終ターンで止まっているとき `toggle()` → `time == 0.0`、`playing is True`
- `P6`: `time == 1.4` で `step(1)` → `2.0`、`step(-1)`（`time == 1.4` から）→ `1.0`、整数 `time == 1.0` で `step(-1)` → `0.0`
- `P7`: `step` と `seek` は範囲に収める（`seek(-3)` → `0.0`、`seek(99)` → `last_turn`）
- `P8`: `seek` / `step` は `playing` を変えない
- `P9`: `last_turn=0` で `toggle`・`update(1)`・`step(1)`・`seek(5)` がどれも例外なし、`time == 0.0`（Review Focus 4）

- [ ] **Step 2: FAIL を確認** → **Step 3: `player.py` を実装** → **Step 4: `uv run pytest tests/test_player.py -v` PASS、`make lint`**

- [ ] **Step 5: コミット**（`"再生の時間管理を追加"`）

---

### Task 6: 色と座標の計算

**Files:**
- Create: `colors.py`, `layout.py`
- Test: `tests/test_layout.py`

**Interfaces:**
- Consumes: Task 1 の `FlyMap`、Task 3 の `Position` / `InFlight`
- Produces:
  - `colors.py`: `ZONE_COLORS: dict[str, RGB]`（Fly-in の `output.py` の `Color` の値をそのまま写す。キーは小文字）、`UNKNOWN_ZONE = (100, 100, 100)`、`zone_rgb(color: str | None) -> RGB`（大文字小文字を区別しない）、`HIGHLIGHT = (255, 159, 26)`、`ERROR = (235, 50, 50)`
  - `layout.py`: `type Point = tuple[float, float]`、`class MapLayout`:
    - `__init__(self, fly_map: FlyMap, left: float, top: float, width: float, height: float, margin: float = 60)`
    - `zone_point(name: ZoneName) -> Point`、`position_point(position: Position) -> Point`（`InFlight` は接続の中点）
  - `lerp(a: Point, b: Point, t: float) -> Point`
  - `slot_offsets(count: int, radius: float) -> list[Point]`（同じ場所にいるドローンをずらす量）

- [ ] **Step 1: 失敗するテストを書く**

- `L1`: 全ゾーンが `margin` の内側に収まり、縦横比を保つ（x 幅 3・y 幅 2 のマップを 800×400 に置くと、y が詰まる側になり x 方向は中央寄せ）
- `L2`: ゾーンが 1 つ、または全ゾーンが同じ座標 → 領域の中央（0 除算しない）
- `L3`: y 軸は画面と同じ向き（マップの y が大きいほど画面の下）
- `L4`: `position_point(InFlight(sr, "r"))` は `s` と `r` の中点
- `L5`: `slot_offsets(1, 10) == [(0.0, 0.0)]`、`slot_offsets(4, 10)` は 4 点すべて原点から距離 10 で互いに異なる
- `L6`: `zone_rgb("RED") == zone_rgb("red") == (255, 60, 60)`、`zone_rgb(None) == zone_rgb("rainbow") == UNKNOWN_ZONE`

- [ ] **Step 2: FAIL を確認** → **Step 3: 実装** → **Step 4: `uv run pytest tests/test_layout.py -v` PASS、`make lint`**

- [ ] **Step 5: コミット**（`"色と座標の計算を追加"`）

---

### Task 7: マップの描画

**Files:**
- Create: `fonts.py`, `view.py`, `scripts/snapshot.py`

**Interfaces:**
- Consumes: Task 3 の `TurnState`、Task 5 の `Player` の `from_turn` / `shown_turn` / `alpha`、Task 6 のすべて
- Produces:
  - `fonts.py`: `load_font(size: int) -> pygame.font.Font`。`pygame.font.match_font` で `["hiraginosans", "hiraginokakugothicpron", "notosanscjkjp", "notosansjp", "ipagothic", "takaogothic"]` を順に探す。見つからなければ既定のフォントを使い、標準エラーに一度だけ `warning: no Japanese font found; Japanese text may not render` を出す（Review Focus 5）
  - `view.py`: `draw_map(surface: pygame.Surface, layout: MapLayout, fly_map: FlyMap, before: TurnState, after: TurnState, alpha: float, font: pygame.font.Font) -> None`
  - `scripts/snapshot.py`: `uv run python scripts/snapshot.py <map> <output> <turn> <png>` で、指定ターンの静止画を PNG に保存する（`SDL_VIDEODRIVER=dummy` で動く。手での確認用）

描画内容（スペックの「画面」の通り）:
- リンク: 灰色の線。`after.used_links` に含まれるものは `HIGHLIGHT` の太線。違反の `link` に含まれるものは `ERROR`。中点に `使用数/上限`（`after.link_counts`）。
- ゾーン: `zone_rgb` の円。違反の `zone` に含まれるものは `ERROR` の太い縁取り。近くに名前と `使用数/上限`（`after.zone_counts`）。上限超過は数字も `ERROR`。
- ドローン: `lerp(layout.position_point(before 位置), layout.position_point(after 位置), alpha)` に、同じ地点のドローン数に応じた `slot_offsets` を足した場所へ、番号入りの白い丸。違反の `drone` に含まれるものは赤い縁取り。`alpha == 0` のときは `before == after` として扱う。

- [ ] **Step 1: `fonts.py`・`view.py`・`scripts/snapshot.py` を実装する**

- [ ] **Step 2: スナップショットで確認する**

Run: `SDL_VIDEODRIVER=dummy uv run python scripts/snapshot.py tests/fixtures/maps/easy/02_simple_fork.txt tests/fixtures/outputs/easy/02_simple_fork.txt 2 /tmp/viz-turn2.png`
Expected: PNG を Read ツールで開き、ブレインストーミングのモックアップ v3（junction 2/2、start-junction 2/2 がオレンジ、D1 が path_a、D2 が path_b、D3・D4 が junction）と同じ内容が描かれている。`tests/fixtures/maps/challenger/01_the_impossible_dream.txt` の最終ターンも出力し、ゾーンが画面からはみ出していないことを見る。

- [ ] **Step 3: `make lint` が通ることを確認**

- [ ] **Step 4: コミット**（`"マップの描画を追加"`）

---

### Task 8: 操作パネル・メインループ・起動

**Files:**
- Create: `panel.py`, `app.py`, `main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: Task 1〜7 のすべて
- Produces:
  - `panel.py`: `PANEL_HEIGHT = 190`、`class Panel`:
    - `__init__(self, font: pygame.font.Font)`
    - `layout(self, rect: pygame.Rect) -> None`（ボタン・シークバーの矩形を決める。ウィンドウのリサイズごとに呼ぶ）
    - `draw(self, surface: pygame.Surface, player: Player, record: TurnRecord | None, state: TurnState, violation_turns: list[int], total_violations: int) -> None`
    - `handle_mouse_down(self, pos: tuple[int, int], player: Player) -> None`、`handle_mouse_drag(self, pos: tuple[int, int], player: Player) -> None`、`handle_mouse_up(self) -> None`
  - `app.py`: `run(fly_map: FlyMap, records: list[TurnRecord], states: list[TurnState], title: str) -> None`
  - `main.py`: `main() -> int`（引数 `map_file`、`output_file`。`OSError` / `MapFileError` / `OutputFileError` は `Error: ...` を標準エラーに出して 1 を返す）

パネルの中身（上から。スペックの「画面」の通り）:
1. シークバー: 左に `shown_turn / last_turn`、`violation_turns` の位置に `ERROR` の目印。クリック・ドラッグで、位置に最も近いターンへ `seek`。
2. ボタン: ⏮（`seek(0)`）、◀（`step(-1)`）、▶/⏸（`toggle`）、▶（`step(1)`）、⏭（`seek(last_turn)`）、`0.5x` `1x` `2x` `4x`（選択中を強調）。記号が出ないフォントでもよいよう、ボタンの記号は pygame の図形で描く。
3. 現在のターンの出力 1 行: `turn <n> $ ` に続けて `colored_segments(record.raw)` を色どおりに描く。ターン 0 は空。
4. 違反の理由: `state.violations` の `message` を ` / ` でつなぐ（`ERROR` 色）。`total_violations == 0` なら `違反なし ✓`（緑）を表示する。
5. キー操作の説明: `SPACE 再生/停止 · ←/→ 1ターン戻る/進む · Home/End 最初/最後 · 1-4 速度 · バーをクリックでジャンプ · Q/Esc 終了`

`app.run`: ウィンドウ 1280×800、リサイズ可（`pygame.RESIZABLE`）。マップ領域は上から `高さ - PANEL_HEIGHT`。60 FPS で `player.update(dt)`。キーは上記の説明どおり（1〜4 が `SPEEDS` の順）。描画には `states[player.from_turn]`、`states[player.shown_turn]`、`player.alpha`、パネルには `records[player.shown_turn - 1]`（ターン 0 は `None`）と `states[player.shown_turn]` を渡す。

- [ ] **Step 1: 失敗するテストを書く**（`tests/test_main.py`。`monkeypatch` で `sys.argv` を差し替え、`app.run` も何もしない関数に差し替える）

- `A1`: フィクスチャの `easy/02_simple_fork` で `main() == 0`、`app.run` が 1 回呼ばれ、`states` の長さが 5
- `A2`: 存在しないマップ → `main() == 1`、標準エラーが `Error: ` で始まる
- `A3`: 書式エラーの出力ファイル → `main() == 1`

- [ ] **Step 2: FAIL を確認** → **Step 3: `panel.py`・`app.py`・`main.py` を実装** → **Step 4: `uv run pytest -v` が全部 PASS、`make lint`**

- [ ] **Step 5: 手で確認する**（`make run`、続いて `make run MAP=tests/fixtures/maps/hard/03_ultimate_challenge.txt OUT=tests/fixtures/outputs/hard/03_ultimate_challenge.txt`）

確認項目:
- 再生でドローンがなめらかに動き、最終ターンで止まる。もう一度押すと最初から。
- ⏮ ◀ ▶ ⏭ と速度のボタン、キー操作がすべて効く。
- シークバーをクリック・ドラッグして飛べる。
- 出力 1 行が色付きで出て、`違反なし ✓` が表示される。
- ウィンドウをリサイズしても崩れない。
- `tests/fixtures/outputs/easy/02_simple_fork.txt` をコピーして 2 行目の `D3-junction` を消したファイルを開くと、該当ターンで赤表示・理由・シークバーの目印が出る。

- [ ] **Step 6: コミット**（`"操作パネルとメインループを追加"`）
