# mac의 경우, brew로 portaudio, libusb 
from psychopy import visual, core, event
from pathlib import Path
import os
import pandas as pd
import numpy as np
import platform
from typing import Optional

# macOS + pyglet IME 입력 시 발생하는 insertText_ 빈 문자열 예외를 완화하는 런타임 패치
try:
    import pyglet  # type: ignore
    # pyglet 1.5.x/2.x에서만 해당 모듈이 존재. 플랫폼 비대응 시 예외 무시
    from pyglet.window.cocoa import pyglet_textview  # type: ignore

    if hasattr(pyglet_textview, "insertText_") and not hasattr(pyglet_textview, "_orig_insertText_"):
        pyglet_textview._orig_insertText_ = pyglet_textview.insertText_  # type: ignore[attr-defined]

        def _safe_insertText_(py_self, text, *args):  # type: ignore[no-redef]
            try:
                # 빈 문자열 또는 None 방어
                if not text or len(text) == 0:
                    return None
            except Exception:
                return None
            try:
                return pyglet_textview._orig_insertText_(py_self, text, *args)  # type: ignore[attr-defined]
            except Exception:
                # 드문 IME 경계 케이스에서 발생하는 예외 무시
                return None

        pyglet_textview.insertText_ = _safe_insertText_  # type: ignore[assignment]
except Exception:
    # 패치 불가 환경은 조용히 진행
    pass


def load_paragraphs_or_default() -> list:
    proj_dir = os.path.join(Path.home(), "Documents", "WorkSpace", "sentence-corpus-prediction")
    stimuli_path = os.path.join(proj_dir, "data", "stimuli.xlsx")
    if os.path.exists(stimuli_path):
        try:
            df = pd.read_excel(stimuli_path)
            if "Paragraph_text" in df.columns:
                return [str(x) for x in df["Paragraph_text"].dropna().tolist()]
        except Exception:
            pass
    return [
        "내가 좋아하는 바나나가 있다.",
        "오늘은 날씨가 정말 좋다."
    ]


def choose_korean_font() -> str:
    system = platform.system()
    if system == "Darwin":
        return "AppleGothic"
    if system == "Windows":
        return "Malgun Gothic"
    return "NanumGothic"


def ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _is_korean_char(ch: str) -> bool:
    if not ch or len(ch) != 1:
        return False
    code = ord(ch)
    # Hangul Syllables
    if 0xAC00 <= code <= 0xD7A3:
        return True
    # Hangul Jamo
    if 0x1100 <= code <= 0x11FF:
        return True
    # Hangul Compatibility Jamo
    if 0x3130 <= code <= 0x318F:
        return True
    # Hangul Jamo Extended-A
    if 0xA960 <= code <= 0xA97F:
        return True
    # Hangul Jamo Extended-B
    if 0xD7B0 <= code <= 0xD7FF:
        return True
    return False


def main():
    korean_font = choose_korean_font()

    paragraphs = load_paragraphs_or_default()

    win = visual.Window([960, 720], monitor="testMonitor", units="deg", fullscr=True, allowGUI=True, color="black")
    # IME 사용을 허용하여 TextBox2가 직접 텍스트 입력을 처리하게 함 (exclusive 비활성)
    try:
        pyg_win = getattr(win, "winHandle", None) or getattr(win, "_win", None)
        if pyg_win is not None and hasattr(pyg_win, "set_exclusive_keyboard"):
            pyg_win.set_exclusive_keyboard(False)
    except Exception:
        pass

    results = []

    instruction = visual.TextStim(
        win=win,
        text="확인 버튼을 클릭하여 제출 / ESC: 종료",
        font=korean_font,
        color="white",
        pos=[0, 12],
        height=0.9,
        wrapWidth=30,
    )

    for paragraph_index, paragraph in enumerate(paragraphs, start=1):
        words = [w for w in str(paragraph).split() if len(w) > 0]
        if len(words) < 2:
            continue

        for step_index in range(1, len(words)):
            prefix_words = words[:step_index]
            target_word = words[step_index]

            prefix_text = " ".join(prefix_words)

            prefix_stim = visual.TextStim(
                win=win,
                text=prefix_text,
                font=korean_font,
                color="white",
                pos=[0, 6],
                height=1.0,
                wrapWidth=30,
            )

            label = visual.TextStim(
                win=win,
                text="다음 어절을 입력하세요",
                font=korean_font,
                color="#CCCCCC",
                pos=[0, -2.5],
                height=0.8,
            )

            # TextBox2 기반 입력 필드 (한글 IME 지원)
            input_box = visual.TextBox2(
                win=win,
                text="",
                font=korean_font,
                color="white",
                fillColor="#222222",
                borderColor="#888888",
                letterHeight=0.8,
                size=(28, 3),
                pos=(0, -6),
                alignment="center",ß
                editable=True,
            )
            try:
                input_box.setFocus(True)
            except Exception:
                pass
            typed_text = ""
            last_text = ""
            # 입력 히트 박스(포커스 전환용)
            input_hit = visual.Rect(
                win=win,
                width=28,
                height=3,
                pos=[0, -6],
                fillColor=None,
                lineColor=None,
                opacity=0.0,
            )
            # 플레이스홀더(입력 없을 때 표시)
            placeholder_tb = visual.TextStim(
                win=win,
                text="여기에 입력...",
                font=korean_font,
                color="#888888",
                pos=[0, -6],
                height=0.8,
            )

            # 확인 버튼(UI)
            confirm_bg = visual.Rect(
                win=win,
                width=8,
                height=3.5,
                pos=[12, -6],
                fillColor="#555555",
                lineColor="white",
                lineWidth=1.5,
            )
            confirm_label = visual.TextStim(
                win=win,
                text="확인",
                font=korean_font,
                color="white",
                pos=[12, -6],
                height=1.0,
            )
            mouse = event.Mouse(win=win, visible=True)

            event.clearEvents()
            prefix_stim.draw()
            instruction.draw()
            label.draw()
            input_box.draw()
            if not typed_text:
                placeholder_tb.draw()
            win.flip()

            stimulus_onset = core.getTime()
            first_key_ts = None

            responded = False
            mouse_was_down = False
            down_started_inside = False
            while not responded:
                # 키 입력 이벤트(첫 키 RT용) + IME 텍스트는 TextBox2가 처리
                keys = event.getKeys(timeStamped=True)
                if keys:
                    for key_name, key_ts in keys:
                        if first_key_ts is None:
                            first_key_ts = key_ts

                        if key_name == "escape":
                            win.close()
                            return
                        # 엔터로 진행하지 않음 (버튼 사용)
                        # 엔터/스페이스 등 텍스트 입력은 TextBox2에 맡김

                # TextBox2에서 편집된 텍스트를 가져와 정제(한글만, 공백 제거)
                # 포커스 유지 (전체화면 전환 등으로 포커스 잃을 수 있음)
                try:
                    input_box.setFocus(True)
                except Exception:
                    pass

                curr_text = input_box.text or ""
                if curr_text != last_text:
                    # 첫 텍스트가 입력된 순간을 보조적으로 RT로 사용(키 이벤트 누락 대비)
                    if first_key_ts is None and len(curr_text) > 0:
                        first_key_ts = core.getTime()

                    sanitized = "".join([c for c in curr_text if _is_korean_char(c)])
                    if sanitized != curr_text:
                        input_box.text = sanitized
                        curr_text = sanitized
                    typed_text = curr_text
                    last_text = curr_text

                # redraw current state
                prefix_stim.draw()
                instruction.draw()
                label.draw()
                input_box.draw()
                if not typed_text:
                    placeholder_tb.draw()

                # 확인 버튼 상태(활성/비활성) + 호버 표시
                mx, my = mouse.getPos()
                hover = confirm_bg.contains([mx, my])
                if typed_text:
                    confirm_bg.fillColor = "#43a047" if hover else "#2e7d32"
                    confirm_bg.lineColor = "white"
                else:
                    confirm_bg.fillColor = "#555555"
                    confirm_bg.lineColor = "#999999"
                confirm_bg.draw()
                confirm_label.draw()

                win.flip()
                core.wait(0.01)

                # 마우스 클릭 처리 (단순화 + 디버깅)
                mx, my = mouse.getPos()
                left_down = mouse.getPressed()[0]
                button_hover = confirm_bg.contains([mx, my])
                
                if left_down and not mouse_was_down:
                    mouse_was_down = True
                    down_started_inside = button_hover
                    print(f"마우스 다운: ({mx:.1f}, {my:.1f}), 버튼 내부: {down_started_inside}")
                elif not left_down and mouse_was_down:
                    mouse_was_down = False
                    print(f"마우스 업: ({mx:.1f}, {my:.1f}), 버튼 내부: {button_hover}, 텍스트 있음: {bool(typed_text)}")
                    if typed_text and down_started_inside and button_hover:
                        print("확인 버튼 클릭 성공!")
                        responded = True
                    down_started_inside = False
                
                # 간단한 클릭 감지 (백업) - 전역 변수 사용
                if left_down and button_hover and typed_text:
                    # 버튼 위에서 클릭하고 텍스트가 있으면 즉시 진행
                    current_time = core.getTime()
                    if not hasattr(main, '_last_click_time'):
                        main._last_click_time = 0
                    if current_time - main._last_click_time > 0.3:
                        main._last_click_time = current_time
                        print("백업 클릭 감지로 진행!")
                        responded = True

                # 입력 박스 클릭 시 포커스 강제 부여
                if left_down and input_hit.contains([mx, my]):
                    try:
                        input_box.setFocus(True)
                        print("입력 박스 포커스 설정")
                    except Exception:
                        pass

            rt_first_key = None
            if first_key_ts is not None:
                rt_first_key = float(first_key_ts - stimulus_onset)

            results.append(
                {
                    "paragraph_id": paragraph_index,
                    "step_index": step_index,
                    "prefix": prefix_text,
                    "target_word": target_word,
                    "predicted_word": typed_text,
                    "rt_first_key_sec": rt_first_key,
                }
            )

            # brief ISI
            core.wait(0.2)

    if len(results) > 0:
        df = pd.DataFrame(results)
        out_path_xlsx = os.path.join(Path.home(), "Documents", "WorkSpace", "sentence-corpus-prediction", "results", "predictions.xlsx")
        out_path_csv = os.path.join(Path.home(), "Documents", "WorkSpace", "sentence-corpus-prediction", "results", "predictions.csv")
        ensure_dir(out_path_xlsx)
        
        print(f"실험 완료! {len(results)}개 결과 저장 중...")
        saved = False
        try:
            with pd.ExcelWriter(out_path_xlsx, engine="openpyxl") as writer:
                df.to_excel(writer, index=False)
            print(f"Excel 파일 저장 완료: {out_path_xlsx}")
            saved = True
        except Exception as e:
            print(f"Excel 저장 실패: {e}")
            try:
                df.to_csv(out_path_csv, index=False)
                print(f"CSV 파일 저장 완료: {out_path_csv}")
                saved = True
            except Exception as e2:
                print(f"CSV 저장도 실패: {e2}")
        
        if not saved:
            print("저장 실패! 결과를 콘솔에 출력:")
            print(df.to_string())

    win.close()


if __name__ == "__main__":
    main()
