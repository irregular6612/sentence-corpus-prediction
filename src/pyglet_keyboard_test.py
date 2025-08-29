#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pyglet 키보드 이벤트 테스트 스크립트
macOS에서 한국어 IME 입력 문제를 진단하기 위한 도구
"""

import pyglet
import sys
import traceback
from datetime import datetime

class KeyboardTestWindow:
    def __init__(self):
        # 윈도우 생성
        self.window = pyglet.window.Window(
            width=800, 
            height=600, 
            caption="pyglet 키보드 테스트",
            resizable=True
        )
        
        # 이벤트 바인딩
        self.window.on_key_press = self.on_key_press
        self.window.on_key_release = self.on_key_release
        self.window.on_text = self.on_text
        self.window.on_text_motion = self.on_text_motion
        self.window.on_text_motion_select = self.on_text_motion_select
        
        # 상태 변수
        self.current_text = ""
        self.log_events = []
        self.start_time = datetime.now()
        
        # 텍스트 표시용 라벨
        self.label = pyglet.text.Label(
            '키보드 입력을 테스트하세요...\nESC: 종료, C: 텍스트 지우기',
            font_name='Apple SD Gothic Neo',
            font_size=16,
            x=10, y=550,
            anchor_x='left', anchor_y='top',
            multiline=True,
            width=780
        )
        
        self.input_label = pyglet.text.Label(
            '',
            font_name='Apple SD Gothic Neo',
            font_size=20,
            x=10, y=400,
            anchor_x='left', anchor_y='top',
            color=(255, 255, 255, 255)
        )
        
        self.log_label = pyglet.text.Label(
            '',
            font_name='Apple SD Gothic Neo',
            font_size=12,
            x=10, y=350,
            anchor_x='left', anchor_y='top',
            color=(200, 200, 200, 255),
            multiline=True,
            width=780
        )
        
        print("=== pyglet 키보드 테스트 시작 ===")
        print(f"시작 시간: {self.start_time}")
        print("ESC: 종료, C: 텍스트 지우기")
        print("한국어 입력을 테스트해보세요...")
    
    def log_event(self, event_type, details):
        """이벤트 로깅"""
        timestamp = datetime.now()
        elapsed = (timestamp - self.start_time).total_seconds()
        log_entry = f"[{elapsed:.3f}s] {event_type}: {details}"
        self.log_events.append(log_entry)
        
        # 최근 10개 이벤트만 표시
        recent_events = self.log_events[-10:]
        self.log_label.text = '\n'.join(recent_events)
        
        print(log_entry)
    
    def on_key_press(self, symbol, modifiers):
        """키 누름 이벤트"""
        key_name = pyglet.window.key.symbol_string(symbol)
        mod_names = []
        if modifiers & pyglet.window.key.MOD_SHIFT:
            mod_names.append('SHIFT')
        if modifiers & pyglet.window.key.MOD_CTRL:
            mod_names.append('CTRL')
        if modifiers & pyglet.window.key.MOD_ALT:
            mod_names.append('ALT')
        if modifiers & pyglet.window.key.MOD_COMMAND:
            mod_names.append('CMD')
        
        mod_str = '+' + '+'.join(mod_names) if mod_names else ''
        details = f"symbol={symbol} ({key_name}){mod_str}"
        self.log_event("KEY_PRESS", details)
        
        # 특수 키 처리
        if symbol == pyglet.window.key.ESCAPE:
            print("ESC 키 감지 - 프로그램 종료")
            pyglet.app.exit()
        elif symbol == pyglet.window.key.C and modifiers & pyglet.window.key.MOD_CTRL:
            self.current_text = ""
            self.input_label.text = ""
            self.log_event("CLEAR", "텍스트 지움")
    
    def on_key_release(self, symbol, modifiers):
        """키 뗌 이벤트"""
        key_name = pyglet.window.key.symbol_string(symbol)
        details = f"symbol={symbol} ({key_name})"
        self.log_event("KEY_RELEASE", details)
    
    def on_text(self, text):
        """텍스트 입력 이벤트 (IME 처리)"""
        self.log_event("TEXT", f"'{text}' (len={len(text)}, ord={[ord(c) for c in text]})")
        
        # 텍스트 추가
        self.current_text += text
        self.input_label.text = f"입력된 텍스트: {self.current_text}"
    
    def on_text_motion(self, motion):
        """텍스트 모션 이벤트 (커서 이동 등)"""
        motion_name = pyglet.window.key.motion_string(motion)
        self.log_event("TEXT_MOTION", f"motion={motion} ({motion_name})")
    
    def on_text_motion_select(self, motion):
        """텍스트 선택 모션 이벤트"""
        motion_name = pyglet.window.key.motion_string(motion)
        self.log_event("TEXT_MOTION_SELECT", f"motion={motion} ({motion_name})")
    
    def on_draw(self):
        """화면 그리기"""
        self.window.clear()
        self.label.draw()
        self.input_label.draw()
        self.log_label.draw()
    
    def run(self):
        """테스트 실행"""
        try:
            # 이벤트 루프 시작
            pyglet.app.run()
        except Exception as e:
            print(f"오류 발생: {e}")
            traceback.print_exc()
        finally:
            print("\n=== 테스트 종료 ===")
            print(f"총 이벤트 수: {len(self.log_events)}")
            print("로그 저장 중...")
            
            # 로그 파일 저장
            with open('pyglet_keyboard_test.log', 'w', encoding='utf-8') as f:
                f.write(f"pyglet 키보드 테스트 로그\n")
                f.write(f"시작 시간: {self.start_time}\n")
                f.write(f"종료 시간: {datetime.now()}\n")
                f.write(f"총 이벤트 수: {len(self.log_events)}\n")
                f.write("-" * 50 + "\n")
                for event in self.log_events:
                    f.write(event + "\n")
            
            print("로그가 'pyglet_keyboard_test.log'에 저장되었습니다.")

if __name__ == "__main__":
    # pyglet 런타임 패치 적용 (기존 실험에서 사용한 패치)
    try:
        import pyglet.window.cocoa.pyglet_textview
        original_insert_text = pyglet.window.cocoa.pyglet_textview.PygletTextView.insertText_
        
        def patched_insert_text(self, text, length):
            try:
                if text is None or len(text) == 0:
                    return
                return original_insert_text(self, text, length)
            except IndexError:
                print(f"IndexError 방지: 빈 텍스트 무시 - '{text}'")
                return
        
        pyglet.window.cocoa.pyglet_textview.PygletTextView.insertText_ = patched_insert_text
        print("pyglet 런타임 패치 적용됨")
    except Exception as e:
        print(f"런타임 패치 적용 실패: {e}")
    
    # 테스트 실행
    test_window = KeyboardTestWindow()
    test_window.run()
