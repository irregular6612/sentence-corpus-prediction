#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pyglet 키보드 문제 진단 및 해결 스크립트
macOS에서 한국어 IME 입력 문제를 분석하고 해결책을 제시
"""

import pyglet
import sys
import traceback
import unicodedata
from datetime import datetime

def diagnose_pyglet_issues():
    """pyglet 키보드 문제 진단"""
    print("=== pyglet 키보드 문제 진단 시작 ===")
    
    # 1. 시스템 정보
    print("\n1. 시스템 정보:")
    print(f"   - pyglet 버전: {pyglet.version}")
    print(f"   - Python 버전: {sys.version}")
    print(f"   - 플랫폼: {sys.platform}")
    
    # 2. 문제 원인 분석
    print("\n2. 문제 원인 분석:")
    print("   - 한국어 IME 입력 시 빈 문자열('')이 insertText_에 전달됨")
    print("   - pyglet/window/cocoa/pyglet_textview.py:77줄에서 IndexError 발생")
    print("   - unicodedata.category(text[0])에서 text가 빈 문자열일 때 오류")
    
    # 3. 현재 패치 상태 확인
    print("\n3. 현재 패치 상태:")
    try:
        import pyglet.window.cocoa.pyglet_textview
        original_method = pyglet.window.cocoa.pyglet_textview.PygletTextView.insertText_
        print("   - insertText_ 메서드: 원본 상태")
    except Exception as e:
        print(f"   - 오류: {e}")
    
    # 4. 해결 방안 제시
    print("\n4. 해결 방안:")
    print("   A. 런타임 패치 (권장)")
    print("   B. pyglet 버전 다운그레이드")
    print("   C. 대안 GUI 툴킷 사용")
    
    return True

def apply_improved_patch():
    """개선된 런타임 패치 적용"""
    print("\n=== 개선된 런타임 패치 적용 ===")
    
    try:
        import pyglet.window.cocoa.pyglet_textview
        original_insert_text = pyglet.window.cocoa.pyglet_textview.PygletTextView.insertText_
        
        def improved_insert_text(self, text):
            """개선된 insertText_ 메서드"""
            try:
                # 1. 빈 문자열 체크
                if text is None:
                    print("DEBUG: None 텍스트 무시")
                    return
                
                text_str = pyglet.libs.darwin.cocoapy.cfstring_to_string(text)
                
                if not text_str or len(text_str) == 0:
                    print("DEBUG: 빈 문자열 무시")
                    return
                
                # 2. 기존 로직 실행
                self.setString_(self.empty_string)
                
                # 3. 제어 문자 체크 (안전하게)
                if len(text_str) > 0 and unicodedata.category(text_str[0]) != 'Cc':
                    self._window.dispatch_event("on_text", text_str)
                    print(f"DEBUG: 텍스트 이벤트 전송: '{text_str}'")
                else:
                    print(f"DEBUG: 제어 문자 무시: '{text_str}'")
                    
            except IndexError as e:
                print(f"DEBUG: IndexError 방지 - 텍스트: '{text_str}'")
                return
            except Exception as e:
                print(f"DEBUG: 예상치 못한 오류: {e}")
                return
        
        # 패치 적용
        pyglet.window.cocoa.pyglet_textview.PygletTextView.insertText_ = improved_insert_text
        print("✅ 개선된 패치 적용 완료")
        return True
        
    except Exception as e:
        print(f"❌ 패치 적용 실패: {e}")
        traceback.print_exc()
        return False

def test_keyboard_events():
    """키보드 이벤트 테스트"""
    print("\n=== 키보드 이벤트 테스트 ===")
    
    # 테스트 윈도우 생성
    window = pyglet.window.Window(
        width=600, height=400,
        caption="키보드 테스트",
        resizable=True
    )
    
    events_log = []
    
    @window.event
    def on_key_press(symbol, modifiers):
        key_name = pyglet.window.key.symbol_string(symbol)
        event_info = f"KEY_PRESS: {key_name} (symbol={symbol})"
        events_log.append(event_info)
        print(event_info)
        
        if symbol == pyglet.window.key.ESCAPE:
            pyglet.app.exit()
    
    @window.event
    def on_text(text):
        event_info = f"TEXT: '{text}' (len={len(text)}, ord={[ord(c) for c in text]})"
        events_log.append(event_info)
        print(event_info)
    
    @window.event
    def on_draw():
        window.clear()
        
        # 이벤트 로그 표시
        y = 350
        for i, event in enumerate(events_log[-15:]):  # 최근 15개만 표시
            label = pyglet.text.Label(
                event,
                font_name='Apple SD Gothic Neo',
                font_size=12,
                x=10, y=y,
                anchor_x='left', anchor_y='top',
                color=(255, 255, 255, 255)
            )
            label.draw()
            y -= 20
    
    print("키보드 입력을 테스트하세요... (ESC: 종료)")
    pyglet.app.run()
    
    return events_log

def main():
    """메인 진단 함수"""
    print("🔍 pyglet 키보드 문제 진단 도구")
    print("=" * 50)
    
    # 1. 기본 진단
    diagnose_pyglet_issues()
    
    # 2. 사용자 선택
    print("\n어떤 작업을 수행하시겠습니까?")
    print("1. 개선된 패치 적용 후 테스트")
    print("2. 패치 없이 테스트")
    print("3. 진단만 수행")
    
    try:
        choice = input("\n선택 (1-3): ").strip()
        
        if choice == "1":
            # 개선된 패치 적용
            if apply_improved_patch():
                print("\n패치 적용 완료. 테스트를 시작합니다...")
                test_keyboard_events()
            else:
                print("패치 적용 실패")
                
        elif choice == "2":
            # 패치 없이 테스트
            print("\n패치 없이 테스트를 시작합니다...")
            test_keyboard_events()
            
        elif choice == "3":
            print("진단 완료")
            
        else:
            print("잘못된 선택입니다.")
            
    except KeyboardInterrupt:
        print("\n진단이 중단되었습니다.")
    except Exception as e:
        print(f"오류 발생: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
