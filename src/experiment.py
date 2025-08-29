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
        from pyglet.window.cocoa import pyglet_textview as _pt

        original_insert = getattr(_pt.PygletTextView, "insertText_", None)
        if original_insert is None:
            return

        def _safe_insert(self, text):  # type: ignore[no-redef]
            try:
                # 'text' can be an NSString proxy; best-effort length check
                if text is None:
                    return None
                try:
                    if len(text) == 0:  # works for NSString proxies
                        return None
                except Exception:
                    # Fallback for objects without __len__; convert to str
                    s = str(text)
                    if not s:
                        return None
            except Exception:
                # If anything goes wrong, avoid crashing; delegate to original
                pass
            return original_insert(self, text)

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
    from PyQt6 import QtWidgets, QtCore

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(["psychopy-input"])

    dlg = QtWidgets.QDialog()
    dlg.setWindowTitle("예측 입력")
    dlg.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
    layout = QtWidgets.QVBoxLayout(dlg)

    label = QtWidgets.QLabel(prompt)
    edit = QtWidgets.QLineEdit()
    btn = QtWidgets.QPushButton("확인")

    layout.addWidget(label)
    layout.addWidget(edit)
    layout.addWidget(btn, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

    started_typing_at: Optional[float] = None
    opened_at = core.getTime()

    def on_text(_text: str) -> None:
        nonlocal started_typing_at
        if started_typing_at is None and _text:
            started_typing_at = core.getTime()

    def on_return() -> None:
        dlg.accept()

    edit.textChanged.connect(on_text)
    edit.returnPressed.connect(on_return)
    btn.clicked.connect(on_return)

    edit.setFocus()
    dlg.raise_()
    dlg.activateWindow()
    dlg.exec()

    text = edit.text().strip()
    typing_onset_ms = float("nan") if started_typing_at is None else max(0.0, (started_typing_at - onset_ref_time) * 1000.0)
    confirm_rt_ms = max(0.0, (core.getTime() - opened_at) * 1000.0)
    return text, typing_onset_ms, confirm_rt_ms


def collect_prediction_with_ime(win: visual.Window, prompt: str, onset_ref_time: float) -> Tuple[str, float, float]:
    """Collect input using wx dialog (IME OK).

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
            # 전체화면 복귀 및 이벤트 정리
            if prev_full:
                win.setFullScr(True, forceRestart=True)
                core.wait(0.22)
            event.clearEvents()
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


