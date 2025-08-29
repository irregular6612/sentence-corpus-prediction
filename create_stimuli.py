import pandas as pd
import os

# 실험용 자극 문장들
stimuli_sentences = [
    "멀리 배웅하던 길 그자리 서서 그곳에 서서 그대가 사랑한 이 계절의 오고감을 봅니다. 아무 노력 말아요. 버거울 땐 언제든 나의 이름을 불러요. 꽃잎이 번지면 그대 새로운 봄이 오겠죠. 시간이 걸려도 그대 반드시 행복 해지세요. 그 다음 말엔",
    "오늘 날씨가 정말 좋다.",
    "너와 나 사이에 우주를 건너 내게로 우주 like to come over to me.",
]

# DataFrame 생성
df = pd.DataFrame({
    'Sentence': stimuli_sentences
})

# data 폴더가 없으면 생성
os.makedirs('data', exist_ok=True)

# Excel 파일로 저장
df.to_excel('data/stimuli.xlsx', index=False, sheet_name='Stimuli')

print(f"자극 데이터가 생성되었습니다: data/stimuli.xlsx")
print(f"총 {len(stimuli_sentences)}개의 문장이 포함되었습니다.")
