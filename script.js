// 실험 데이터 및 상태 관리
class ExperimentManager {
    constructor() {
        this.sentences = [];
        this.currentSentenceIndex = 0;
        this.currentWordIndex = 0;
        this.results = [];
        this.experimentStartTime = null;
        this.screenDisplayTime = null;
        this.inputStartTime = null;
        this.timerInterval = null;
        this.participantId = this.generateParticipantId();
        
        this.initializeEventListeners();
        this.loadStimuliData();
    }

    // 참가자 ID 생성
    generateParticipantId() {
        const timestamp = new Date().toISOString().replace(/[-:]/g, '').split('.')[0];
        return `P${Math.floor(Math.random() * 1000).toString().padStart(3, '0')}_${timestamp}`;
    }

    // 이벤트 리스너 초기화
    initializeEventListeners() {
        document.getElementById('startExperiment').addEventListener('click', () => {
            this.startExperiment();
        });

        document.getElementById('confirmPrediction').addEventListener('click', () => {
            this.confirmPrediction();
        });

        document.getElementById('downloadResults').addEventListener('click', () => {
            this.downloadResults();
        });

        // 키보드 이벤트 (Enter 키로 예측 확인)
        document.getElementById('predictionInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.confirmPrediction();
            }
        });

        // 입력 시작 시간 측정
        document.getElementById('predictionInput').addEventListener('focus', () => {
            this.recordInputStart();
        });
    }

    // 자극 데이터 로드
    async loadStimuliData() {
        try {
            const response = await fetch('data/stimuli.xlsx');
            const arrayBuffer = await response.arrayBuffer();
            const workbook = XLSX.read(arrayBuffer, { type: 'array' });
            
            // 첫 번째 시트의 데이터 가져오기
            const sheetName = workbook.SheetNames[0];
            const worksheet = workbook.Sheets[sheetName];
            const data = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
            
            // 헤더 제거하고 문장 데이터 추출
            this.sentences = data.slice(1).map(row => row[0]).filter(sentence => sentence);
            
            console.log(`로드된 문장 수: ${this.sentences.length}`);
        } catch (error) {
            console.error('자극 데이터 로드 실패:', error);
            // 테스트용 샘플 데이터
            this.sentences = [
                '나는 바나나가 좋아.',
                '오늘 날씨가 정말 좋다.',
                '커피를 마시면서 책을 읽었다.',
                '새로운 영화를 보러 갔다.',
                '친구와 함께 저녁을 먹었다.'
            ];
        }
    }

    // 실험 시작
    startExperiment() {
        this.experimentStartTime = performance.now();
        this.showScreen('experiment');
        this.startTimer();
        this.displayCurrentSentence();
    }

    // 화면 전환
    showScreen(screenId) {
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.add('hidden');
        });
        document.getElementById(screenId).classList.remove('hidden');
    }

    // 타이머 시작
    startTimer() {
        this.timerInterval = setInterval(() => {
            const elapsed = Math.floor((performance.now() - this.experimentStartTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            document.getElementById('timer').textContent = 
                `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }, 1000);
    }

    // 현재 문장 표시
    displayCurrentSentence() {
        if (this.currentSentenceIndex >= this.sentences.length) {
            this.completeExperiment();
            return;
        }

        const sentence = this.sentences[this.currentSentenceIndex];
        const words = this.splitIntoWords(sentence);
        
        if (this.currentWordIndex >= words.length) {
            this.currentSentenceIndex++;
            this.currentWordIndex = 0;
            this.displayCurrentSentence();
            return;
        }

        const currentWords = words.slice(0, this.currentWordIndex + 1);
        const displayText = currentWords.join(' ');
        
        document.getElementById('currentSentence').textContent = displayText;
        
        // 마지막 어절인지 확인
        const isLastWord = this.currentWordIndex === words.length - 1;
        
        if (isLastWord) {
            // 마지막 어절: 입력 필드 숨기고 완료 메시지 표시
            document.getElementById('predictionInput').style.display = 'none';
            document.getElementById('confirmPrediction').style.display = 'none';
            document.querySelector('.prediction-section p').textContent = '문장이 완성되었습니다. 다음 문장으로 진행합니다.';
            
            // 2초 후 다음 문장으로 자동 진행
            setTimeout(() => {
                this.currentSentenceIndex++;
                this.currentWordIndex = 0;
                this.displayCurrentSentence();
            }, 2000);
        } else {
            // 예측 단계: 입력 필드 표시
            document.getElementById('predictionInput').style.display = 'block';
            document.getElementById('confirmPrediction').style.display = 'block';
            document.querySelector('.prediction-section p').textContent = '다음에 올 것 같은 어절을 입력해 주세요:';
            document.getElementById('predictionInput').value = '';
            
            // 화면 제시 시간을 먼저 기록
            this.screenDisplayTime = performance.now();
            console.log('화면 제시 시간 기록:', this.screenDisplayTime);
            
            // inputStartTime 리셋 (새로운 타이밍 시작)
            this.inputStartTime = null;
            
            // DOM 업데이트를 기다린 후 포커스
            requestAnimationFrame(() => {
                document.getElementById('predictionInput').focus();
                // focus 이벤트가 발생하지 않았을 경우를 대비해 직접 시간 기록
                setTimeout(() => {
                    if (!this.inputStartTime) {
                        this.inputStartTime = performance.now();
                        console.log('강제 입력 시작 시간 기록 (백업):', this.inputStartTime);
                    }
                }, 10);
            });
        }
        
        // 진행률 업데이트 (예측 단계만 계산)
        const totalSteps = this.sentences.reduce((total, sentence) => {
            return total + this.splitIntoWords(sentence).length - 1;
        }, 0);
        const currentStep = this.getCurrentStep();
        document.getElementById('progressText').textContent = `${currentStep}/${totalSteps}`;
    }

    // 문장을 어절 단위로 분리
    splitIntoWords(sentence) {
        // 한글 어절 분리 (공백 기준)
        return sentence.trim().split(/\s+/).filter(word => word.length > 0);
    }

    // 현재 단계 계산 (예측 단계만 계산)
    getCurrentStep() {
        let step = 0;
        for (let i = 0; i < this.currentSentenceIndex; i++) {
            step += this.splitIntoWords(this.sentences[i]).length - 1;
        }
        // 현재 문장의 예측 단계만 추가 (마지막 어절 제외)
        const currentWords = this.splitIntoWords(this.sentences[this.currentSentenceIndex]);
        step += Math.min(this.currentWordIndex, currentWords.length - 1);
        return step;
    }

    // 입력 시작 시간 기록
    recordInputStart() {
        // 이미 기록된 경우 중복 기록 방지
        if (!this.inputStartTime) {
            this.inputStartTime = performance.now();
            console.log('입력 시작 시간 기록 (focus 이벤트):', this.inputStartTime);
        }
    }

    // 예측 확인
    confirmPrediction() {
        const prediction = document.getElementById('predictionInput').value.trim();
        
        if (!prediction) {
            alert('예측 어절을 입력해 주세요.');
            return;
        }

        // 결과 저장
        this.saveResult(prediction);
        
        // 다음 단계로 진행
        this.currentWordIndex++;
        this.displayCurrentSentence();
    }

    // 결과 저장
    saveResult(prediction) {
        const sentence = this.sentences[this.currentSentenceIndex];
        const words = this.splitIntoWords(sentence);
        const actualNextWord = words[this.currentWordIndex + 1] || '';
        
        // responseTime 계산 개선 (동기 처리)
        let responseTime = 0;
        if (this.inputStartTime && this.screenDisplayTime) {
            responseTime = this.inputStartTime - this.screenDisplayTime;
            console.log('responseTime 계산:', responseTime, 'inputStartTime:', this.inputStartTime, 'screenDisplayTime:', this.screenDisplayTime);
            
            // 음수인 경우 0으로 설정
            if (responseTime < 0) {
                console.warn('음수 responseTime 감지:', responseTime, 'screenDisplayTime:', this.screenDisplayTime, 'inputStartTime:', this.inputStartTime);
                responseTime = 0;
            }
        } else {
            console.warn('타이밍 데이터 누락:', 'screenDisplayTime:', this.screenDisplayTime, 'inputStartTime:', this.inputStartTime);
        }
        
        const result = {
            participantId: this.participantId,
            sentenceIndex: this.currentSentenceIndex,
            wordIndex: this.currentWordIndex,
            sentence: sentence,
            displayedWords: words.slice(0, this.currentWordIndex + 1).join(' '),
            predictedWord: prediction,
            actualNextWord: actualNextWord,
            screenDisplayTime: this.screenDisplayTime || 0,
            inputStartTime: this.inputStartTime || 0,
            responseTime: responseTime,
            timestamp: new Date().toISOString()
        };
        
        this.results.push(result);
        console.log('결과 저장:', result);
    }

    // 실험 완료
    completeExperiment() {
        clearInterval(this.timerInterval);
        this.showScreen('completion');
    }

    // 결과 다운로드
    downloadResults() {
        // 결과 데이터를 워크시트로 변환
        const worksheet = XLSX.utils.json_to_sheet(this.results);
        const workbook = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(workbook, worksheet, 'Results');
        
        // 파일명 생성
        const timestamp = new Date().toISOString().replace(/[-:]/g, '').split('.')[0];
        const filename = `results_${this.participantId}_${timestamp}.xlsx`;
        
        // 파일 다운로드
        XLSX.writeFile(workbook, filename);
        
        // 추가 정보 표시
        const downloadSection = document.getElementById('downloadSection');
        downloadSection.innerHTML = `
            <p>결과가 다운로드되었습니다: ${filename}</p>
            <p>총 ${this.results.length}개의 예측 데이터가 저장되었습니다.</p>
            <button onclick="window.close()" class="btn btn-primary">창 닫기</button>
        `;
    }
}

// 페이지 로드 시 실험 매니저 초기화
document.addEventListener('DOMContentLoaded', () => {
    new ExperimentManager();
});

// 페이지 언로드 시 경고
window.addEventListener('beforeunload', (e) => {
    e.preventDefault();
    e.returnValue = '실험 중입니다. 정말로 나가시겠습니까?';
});

// 브라우저 탭 변경 감지
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        console.warn('브라우저 탭이 변경되었습니다. 실험 정확도에 영향을 줄 수 있습니다.');
    }
});
