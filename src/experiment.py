import argparse
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import pandas as pd

from psychopy import core, event, gui, visual


# ------------------------------
# Data structures
# ------------------------------


@dataclass
class TrialRecord:
    participant: str
    trial_index: int
    sentence_id: str
    step_index: int
    displayed_prefix: str
    true_next_token: str
    prediction: str
    typing_onset_ms: float
    confirm_rt_ms: float


# ------------------------------
# Utilities
# ------------------------------


def choose_korean_font() -> str:
    """Pick a reasonable Korean font among common options.

    PsychoPy may fallback silently if font is unavailable; we simply return the
    first candidate and rely on system fallback if missing.
    """
    candidates = [
        "Apple SD Gothic Neo",  # macOS default
        "Noto Sans CJK KR",
        "NanumGothic",
        "Nanum Gothic",
        "Malgun Gothic",  # Windows
    ]
    return candidates[0]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _patch_pyglet_cocoa_textview_empty_text_guard() -> None:
    """Guard pyglet Cocoa TextView against empty text IME events on macOS.

    Prevents IndexError in pyglet_textview.insertText_ when text is empty.
    Safe no-op on non-macOS or if pyglet internals change.
    """
    if sys.platform != "darwin":
        return
    try:
        import pyglet  # noqa: F401
        import unicodedata
        from pyglet.window.cocoa import pyglet_textview as _pt

        original_insert = getattr(_pt.PygletTextView, "insertText_", None)
        if original_insert is None:
            return

        def _safe_insert(self, text):  # type: ignore[no-redef]
            try:
                # 1. None 체크
                if text is None:
                    return None
                
                # 2. 빈 문자열 체크 (NSString proxy 지원)
                try:
                    if len(text) == 0:  # works for NSString proxies
                        return None
                except Exception:
                    # Fallback for objects without __len__; convert to str
                    s = str(text)
                    if not s:
                        return None
                
                # 3. 기존 로직 실행
                self.setString_(self.empty_string)
                
                # 4. 텍스트 변환 및 안전한 처리
                text_str = pyglet.libs.darwin.cocoapy.cfstring_to_string(text)
                
                if not text_str or len(text_str) == 0:
                    return None
                
                # 5. 제어 문자 체크 (안전하게)
                if len(text_str) > 0 and unicodedata.category(text_str[0]) != 'Cc':
                    self._window.dispatch_event("on_text", text_str)
                
            except IndexError:
                # IndexError 방지
                return None
            except Exception:
                # If anything goes wrong, avoid crashing; delegate to original
                pass
            return None

        _pt.PygletTextView.insertText_ = _safe_insert  # type: ignore[assignment]
    except Exception:
        # Non-fatal if patching fails
        pass


def load_stimuli(xlsx_path: Optional[Path]) -> List[Tuple[str, str]]:
    """Load sentences from Excel.

    Returns list of tuples (sentence_id, sentence_text).
    Column preference: 'sentence' or 'text' if present, otherwise first object dtype column.
    If an 'id' column exists, use it; else generate sequential IDs.
    """
    if xlsx_path is None:
        xlsx_path = _project_root() / "data" / "stimuli.xlsx"

    if not xlsx_path.exists():
        raise FileNotFoundError(f"Stimuli file not found: {xlsx_path}")

    df = pd.read_excel(xlsx_path)
    if df.empty:
        raise ValueError("Stimuli Excel is empty")

    # Determine text column
    text_col_candidates = [c for c in df.columns if c.lower() in ("sentence", "text")]
    if text_col_candidates:
        text_col = text_col_candidates[0]
    else:
        # Fallback: first object dtype column
        obj_cols = [c for c in df.columns if df[c].dtype == object]
        if not obj_cols:
            raise ValueError("No suitable text column found in stimuli.xlsx")
        text_col = obj_cols[0]

    # Determine id column
    id_col_candidates = [c for c in df.columns if c.lower() in ("id", "sentence_id")]
    if id_col_candidates:
        id_col = id_col_candidates[0]
        ids = df[id_col].astype(str).fillna("")
    else:
        ids = pd.Series([f"S{idx+1:03d}" for idx in range(len(df))])

    texts = df[text_col].astype(str).fillna("")
    rows: List[Tuple[str, str]] = []
    for sid, txt in zip(ids, texts):
        cleaned = str(txt).strip()
        if cleaned:
            rows.append((sid, cleaned))
    if not rows:
        raise ValueError("No non-empty sentences found in stimuli.xlsx")
    return rows


def split_eojeol(sentence: str) -> List[str]:
    """Very simple eojeol split by whitespace.

    Example: "나는 바나나가 좋아." -> ["나는", "바나나가", "좋아."]
    """
    # Normalize spaces
    return [tok for tok in sentence.strip().split() if tok]


# ------------------------------
# PyQt6 dialog for IME-capable input (macOS-safe)
# ------------------------------


def _qt_input_dialog(prompt: str, onset_ref_time: float) -> Tuple[str, float, float]:
    """Open a PyQt6 modal dialog with a QLineEdit (IME-friendly).

    Returns (text, typing_onset_ms, confirm_rt_ms).
    """
    from PyQt6 import QtWidgets, QtCore, QtGui

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(["psychopy-input"])

    dlg = QtWidgets.QDialog()
    dlg.setWindowTitle("예측 입력")
    dlg.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
    dlg.setWindowFlags(QtCore.Qt.WindowType.Window | QtCore.Qt.WindowType.WindowStaysOnTopHint)
    layout = QtWidgets.QVBoxLayout(dlg)

    # 프롬프트 라벨
    label = QtWidgets.QLabel(prompt)
    label.setWordWrap(True)
    layout.addWidget(label)

    # 입력 필드 (플레이스홀더 + 한글 IME 지원)
    edit = QtWidgets.QLineEdit()
    edit.setFont(QtGui.QFont("Apple SD Gothic Neo", 14))
    edit.setMinimumHeight(40)
    edit.setPlaceholderText("여기에 예측 어절을 입력하세요...")
    edit.setStyleSheet("""
        QLineEdit {
            padding: 8px;
            border: 2px solid #ddd;
            border-radius: 6px;
            background-color: #fafafa;
        }
        QLineEdit:focus {
            border-color: #0066cc;
            background-color: white;
        }
    """)
    layout.addWidget(edit)

    # 실시간 입력 표시 라벨 (플레이스홀더 스타일)
    preview_label = QtWidgets.QLabel("입력 중: ")
    preview_label.setFont(QtGui.QFont("Apple SD Gothic Neo", 12))
    preview_label.setStyleSheet("color: #666; font-style: italic; padding: 4px;")
    layout.addWidget(preview_label)

    # 버튼들
    button_layout = QtWidgets.QHBoxLayout()
    
    # 수정 버튼 (입력 내용 지우기)
    clear_btn = QtWidgets.QPushButton("지우기")
    clear_btn.setFont(QtGui.QFont("Apple SD Gothic Neo", 11))
    clear_btn.setStyleSheet("""
        QPushButton {
            padding: 6px 12px;
            background-color: #f0f0f0;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #e0e0e0;
        }
    """)
    
    # 확인 버튼
    btn = QtWidgets.QPushButton("확인")
    btn.setFont(QtGui.QFont("Apple SD Gothic Neo", 12))
    btn.setStyleSheet("""
        QPushButton {
            padding: 8px 16px;
            background-color: #0066cc;
            color: white;
            border: none;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #0052a3;
        }
    """)
    
    button_layout.addWidget(clear_btn)
    button_layout.addStretch()
    button_layout.addWidget(btn)
    layout.addLayout(button_layout)

    started_typing_at: Optional[float] = None
    opened_at = core.getTime()

    def on_text_changed(text: str) -> None:
        nonlocal started_typing_at
        if started_typing_at is None and text:
            started_typing_at = core.getTime()
        # 실시간 입력 표시 업데이트
        if text:
            preview_label.setText(f"입력 중: {text}")
        else:
            preview_label.setText("입력 중: ")

    def clear_text() -> None:
        edit.clear()
        edit.setFocus()

    def on_accept() -> None:
        # 창을 닫기 전에 잠시 대기하여 IME 조합 완료 보장
        QtCore.QTimer.singleShot(50, dlg.accept)  # 대기 시간 단축

    edit.textChanged.connect(on_text_changed)
    edit.returnPressed.connect(on_accept)
    clear_btn.clicked.connect(clear_text)
    btn.clicked.connect(on_accept)

    edit.setFocus()
    dlg.raise_()
    dlg.activateWindow()
    dlg.exec()

    text = edit.text().strip()
    typing_onset_ms = float("nan") if started_typing_at is None else max(0.0, (started_typing_at - onset_ref_time) * 1000.0)
    confirm_rt_ms = max(0.0, (core.getTime() - opened_at) * 1000.0)
    return text, typing_onset_ms, confirm_rt_ms


def collect_prediction_with_ime(win: visual.Window, prompt: str, onset_ref_time: float) -> Tuple[str, float, float]:
    """Collect input using PyQt6 dialog (IME OK).

    In macOS fullscreen, other toolkits' dialogs can be hidden. Temporarily exit
    fullscreen during input, then restore fullscreen.
    """
    try:
        prev_full = getattr(win, "fullscr", True)
        try:
            # Flush 키 이벤트 후 전체화면만 해제 (창 숨김 제거)
            event.clearEvents()
            win.setFullScr(False, forceRestart=True)
            core.wait(0.18)
        except Exception:
            pass
        return _qt_input_dialog(prompt, onset_ref_time)
    except Exception:
        # Fallback: PsychoPy key capture (IME unfriendly)
        typed = ""
        onset: Optional[float] = None
        while True:
            keys = event.getKeys(timeStamped=False)
            now = core.getTime()
            for k in keys:
                if k == "return":
                    return typed, (float("nan") if onset is None else max(0.0, (onset - onset_ref_time) * 1000.0)), 0.0
                if k in ("backspace",):
                    typed = typed[:-1]
                elif len(k) == 1:
                    if onset is None:
                        onset = now
                    typed += k
    finally:
        try:
            # 전체화면 복귀 및 이벤트 정리 (빠른 포커스)
            if prev_full:
                win.setFullScr(True, forceRestart=True)
                core.wait(0.1)  # 대기 시간 단축
            # 창을 다시 활성화하고 포커스 복원
            if hasattr(win, 'winHandle'):
                win.winHandle.set_visible(True)
                win.winHandle.activate()
            # 강제로 실험창에 포커스 (빠른 복원)
            win.winHandle.raise_()
            win.winHandle.requestActivate()
            event.clearEvents()
            # 최소 대기로 포커스 안정화
            core.wait(0.05)
        except Exception:
            pass


# ------------------------------
# PsychoPy drawing helpers
# ------------------------------


def draw_button(win: visual.Window, center: Tuple[float, float], size: Tuple[float, float], text: str, font: str) -> Tuple[visual.Rect, visual.TextStim]:
    rect = visual.Rect(win, width=size[0], height=size[1], lineColor="#444444", fillColor="#eeeeee", pos=center)
    label = visual.TextStim(win, text=text, font=font, height=28, color="#222222", pos=center)
    rect.draw()
    label.draw()
    return rect, label


def point_in_rect(x: float, y: float, rect: visual.Rect) -> bool:
    cx, cy = rect.pos
    w2 = rect.width / 2.0
    h2 = rect.height / 2.0
    return (cx - w2) <= x <= (cx + w2) and (cy - h2) <= y <= (cy + h2)


# ------------------------------
# Experiment flow
# ------------------------------


def run_experiment(participant: str, stimuli_path: Optional[str] = None) -> Path:
    font = choose_korean_font()
    _patch_pyglet_cocoa_textview_empty_text_guard()
    # 전체화면 실행
    win = visual.Window(units="pix", fullscr=True, color="#ffffff")
    mouse = event.Mouse(win=win)
    event.clearEvents()
    mouse.clickReset()

    # Instruction screen
    instruction_lines = [
        "문장 예측 과제",
        "",
        "- 화면에 문장의 일부가 제시됩니다.",
        "- 다음에 올 어절을 예측하여 입력하세요.",
        "- 입력을 마친 뒤 확인을 누르면 다음 어절이 공개됩니다.",
        "",
        "시작하려면 하단의 [시작] 버튼을 클릭하세요.",
    ]
    instr_text = visual.TextStim(win, text="\n".join(instruction_lines), font=font, color="#111111", height=32, wrapWidth=1100, pos=(0, 120))
    start_rect, _ = draw_button(win, center=(0, -220), size=(240, 70), text="시작", font=font)
    instr_text.draw()
    start_rect, start_label = draw_button(win, center=(0, -220), size=(240, 70), text="시작", font=font)
    win.flip()

    # Wait for start
    mouse.clickReset()
    event.clearEvents()
    while True:
        buttons, times = mouse.getPressed(getTime=True)
        if any(buttons):
            if point_in_rect(*mouse.getPos(), start_rect):
                break
        if "escape" in event.getKeys():
            win.close()
            core.quit()
        core.wait(0.01)

    # Load stimuli
    stimuli = load_stimuli(Path(stimuli_path) if stimuli_path else None)

    # Prepare text stimulus for sentence prefix
    sentence_text = visual.TextStim(
        win,
        text="",
        font=font,
        color="#000000",
        height=40,
        wrapWidth=1100,
        pos=(0, 120),
    )

    prompt_text = visual.TextStim(
        win,
        text="다음 어절을 예측하여 입력하세요.",
        font=font,
        color="#333333",
        height=28,
        wrapWidth=1100,
        pos=(0, -60),
    )

    # 실시간 입력 표시용 텍스트
    input_preview_text = visual.TextStim(
        win,
        text="",
        font=font,
        color="#0066cc",
        height=24,
        wrapWidth=1100,
        pos=(0, -120),
    )

    input_button_rect = None

    records: List[TrialRecord] = []

    trial_clock = core.Clock()

    for t_index, (sid, sentence) in enumerate(stimuli, start=1):
        tokens = split_eojeol(sentence)
        if len(tokens) < 2:
            continue  # Need at least one prediction step

        # Start with the first token visible
        for step_index in range(1, len(tokens)):
            prefix = " ".join(tokens[:step_index])
            true_next = tokens[step_index]

            sentence_text.text = prefix
            prompt_text.text = "다음 어절을 예측하여 입력하세요."

            # Draw frame
            sentence_text.draw()
            prompt_text.draw()
            input_preview_text.text = ""  # 입력 표시 초기화
            input_preview_text.draw()
            input_button_rect, _ = draw_button(win, center=(0, -200), size=(280, 70), text="예측 입력", font=font)
            win.flip()

            # Present time reference for onset
            present_time = core.getTime()

            # Wait for click on input button or press return to open input
            mouse.clickReset()
            event.clearEvents()
            opened = False
            while not opened:
                buttons, times = mouse.getPressed(getTime=True)
                if any(buttons):
                    if point_in_rect(*mouse.getPos(), input_button_rect):
                        opened = True
                keys = event.getKeys()
                if "return" in keys:
                    opened = True
                if "escape" in keys:
                    win.close()
                    core.quit()
                core.wait(0.01)

            # Collect prediction using IME-capable dialog
            prompt_str = f"표시된 문장: {prefix}\n다음 어절을 입력 후 [확인]을 누르세요."
            pred, onset_ms, confirm_rt_ms = collect_prediction_with_ime(win, prompt_str, present_time)
            # 입력 종료 후 이벤트/마우스 재정비
            event.clearEvents()
            mouse = event.Mouse(win=win)
            mouse.clickReset()

            # 입력 결과를 실험창에 표시
            input_preview_text.text = f"입력한 예측: {pred}"
            sentence_text.draw()
            prompt_text.draw()
            input_preview_text.draw()
            win.flip()
            core.wait(0.8)  # 입력 결과를 잠시 보여줌

            # Log record
            rec = TrialRecord(
                participant=participant,
                trial_index=t_index,
                sentence_id=sid,
                step_index=step_index,
                displayed_prefix=prefix,
                true_next_token=true_next,
                prediction=pred,
                typing_onset_ms=onset_ms,
                confirm_rt_ms=confirm_rt_ms,
            )
            records.append(rec)

            # Reveal next token (briefly show updated prefix)
            updated_prefix = " ".join(tokens[: step_index + 1])
            sentence_text.text = updated_prefix
            prompt_text.text = "다음 단계로 넘어갑니다..."
            sentence_text.draw()
            prompt_text.draw()
            win.flip()
            core.wait(0.4)

    # End screen
    end_text = visual.TextStim(win, text="실험이 종료되었습니다. 감사합니다.", font=font, color="#111111", height=36, wrapWidth=1100, pos=(0, 60))
    end_text.draw()
    win.flip()
    core.wait(1.0)

    # Save results
    out_dir = _project_root() / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"results_{participant}_{ts}.xlsx"

    df = pd.DataFrame([
        {
            "participant": r.participant,
            "trial_index": r.trial_index,
            "sentence_id": r.sentence_id,
            "step_index": r.step_index,
            "displayed_prefix": r.displayed_prefix,
            "true_next_token": r.true_next_token,
            "prediction": r.prediction,
            "typing_onset_ms": r.typing_onset_ms,
            "confirm_rt_ms": r.confirm_rt_ms,
        }
        for r in records
    ])
    df.to_excel(out_path, index=False)

    win.close()
    core.quit()
    return out_path


def _ask_participant_id(default: str = "P001") -> str:
    dlg = gui.Dlg(title="참가자 정보")
    dlg.addText("Participant ID를 입력하세요")
    dlg.addField("Participant ID:", default)
    ok = dlg.show()
    if dlg.OK and ok:
        pid = ok[0].strip() if isinstance(ok, list) else str(ok).strip()
        return pid or default
    return default


def main():
    parser = argparse.ArgumentParser(description="Sentence Prediction Experiment (PsychoPy)")
    parser.add_argument("--participant", "-p", type=str, default=None, help="Participant ID (optional; GUI prompt if omitted)")
    parser.add_argument("--stimuli", "-s", type=str, default=None, help="Path to stimuli.xlsx (optional)")
    args = parser.parse_args()

    participant = args.participant or _ask_participant_id()
    try:
        out = run_experiment(participant=participant, stimuli_path=args.stimuli)
        print(f"Saved results to: {out}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()


