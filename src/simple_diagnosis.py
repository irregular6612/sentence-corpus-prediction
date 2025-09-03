#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 pyglet 키보드 문제 진단
"""

import pyglet
import sys
import unicodedata

print("=== pyglet 키보드 문제 진단 ===")
print(f"pyglet 버전: {pyglet.version}")
print(f"Python 버전: {sys.version}")
print(f"플랫폼: {sys.platform}")

print("\n문제 원인:")
print("- 한국어 IME 입력 시 빈 문자열('')이 insertText_에 전달됨")
print("- pyglet/window/cocoa/pyglet_textview.py:77줄에서 IndexError 발생")
print("- unicodedata.category(text[0])에서 text가 빈 문자열일 때 오류")

print("\n해결 방안:")
print("1. 런타임 패치 (권장)")
print("2. pyglet 버전 다운그레이드")
print("3. 대안 GUI 툴킷 사용")

# 개선된 패치 적용
try:
    import pyglet.window.cocoa.pyglet_textview
    original_insert_text = pyglet.window.cocoa.pyglet_textview.PygletTextView.insertText_
    
    def improved_insert_text(self, text):
        """개선된 insertText_ 메서드"""
        try:
            # 빈 문자열 체크
            if text is None:
                return
            
            text_str = pyglet.libs.darwin.cocoapy.cfstring_to_string(text)
            
            if not text_str or len(text_str) == 0:
                return
            
            # 기존 로직 실행
            self.setString_(self.empty_string)
            
            # 제어 문자 체크 (안전하게)
            if len(text_str) > 0 and unicodedata.category(text_str[0]) != 'Cc':
                self._window.dispatch_event("on_text", text_str)
                
        except IndexError:
            return
        except Exception:
            return
    
    # 패치 적용
    pyglet.window.cocoa.pyglet_textview.PygletTextView.insertText_ = improved_insert_text
    print("\n✅ 개선된 패치 적용 완료")
    
except Exception as e:
    print(f"\n❌ 패치 적용 실패: {e}")

print("\n진단 완료!")

