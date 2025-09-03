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
        this.isWaitingForInput = false; // 입력 대기 상태 추적
        
        // 참가자 정보
        this.participantNumber = null;
        this.participantGender = null;
        this.participantAge = null;
        
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
            this.validateAndStartExperiment();
        });

        document.getElementById('confirmPrediction').addEventListener('click', () => {
            this.confirmPrediction();
        });

        document.getElementById('downloadResults').addEventListener('click', () => {
            this.downloadResults();
        });

        // 전역 키보드 이벤트 리스너 설정
        this.setupGlobalKeyboardListener();
    }

    // 참가자 정보 검증 및 실험 시작
    validateAndStartExperiment() {
        const participantNumber = document.getElementById('participantNumber').value;
        const participantGender = document.getElementById('participantGender').value;
        const participantAge = document.getElementById('participantAge').value;

        // 필수 입력 검증
        if (!participantNumber || !participantGender || !participantAge) {
            alert('모든 참가자 정보를 입력해 주세요.');
            return;
        }

        // 나이 범위 검증
        const age = parseInt(participantAge);
        if (age < 1 || age > 120) {
            alert('나이는 1세 이상 120세 이하여야 합니다.');
            return;
        }

        // 참가자 정보 저장
        this.participantNumber = participantNumber;
        this.participantGender = participantGender;
        this.participantAge = age;

        // 실험 시작
        this.startExperiment();
    }

    // 전역 키보드 이벤트 리스너 설정
    setupGlobalKeyboardListener() {
        document.addEventListener('keydown', (e) => {
            if (this.isWaitingForInput && e.target.id === 'predictionInput') {
                this.recordInputStart();
            }
        });

        document.addEventListener('keypress', (e) => {
            if (e.target.id === 'predictionInput' && e.key === 'Enter') {
                this.confirmPrediction();
            }
        });

        // 타이밍 테스트를 위한 전역 키 이벤트
        document.addEventListener('keydown', (e) => {
            if (e.key === 't' && e.ctrlKey) {
                this.testTiming();
            }
        });
    }

    // 타이밍 측정 테스트 함수
    testTiming() {
        console.log('=== 타이밍 측정 테스트 ===');
        const now1 = performance.now();
        const now2 = performance.now();
        console.log('performance.now() 연속 호출 차이:', now2 - now1, 'ms');
        
        const date1 = Date.now();
        const date2 = Date.now();
        console.log('Date.now() 연속 호출 차이:', date2 - date1, 'ms');
        
        console.log('현재 performance.now():', performance.now());
        console.log('현재 Date.now():', Date.now());
        
        // 1초 후 다시 측정
        setTimeout(() => {
            const after1 = performance.now();
            const after2 = Date.now();
            console.log('1초 후 performance.now():', after1);
            console.log('1초 후 Date.now():', after2);
            console.log('실제 경과 시간 (performance.now):', after1 - now1, 'ms');
            console.log('실제 경과 시간 (Date.now):', after2 - date1, 'ms');
        }, 1000);
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
            
            // 헤더를 포함한 JSON 데이터로 변환
            const jsonData = XLSX.utils.sheet_to_json(worksheet);
            
            // 컬럼명 확인
            if (jsonData.length > 0) {
                const columns = Object.keys(jsonData[0]);
                console.log('발견된 컬럼들:', columns);
                
                // 'sentence' 컬럼 찾기 (대소문자 구분 없이)
                let sentenceColumn = null;
                for (const column of columns) {
                    if (column.toLowerCase() === 'sentence' || 
                        column.toLowerCase() === 'text' || 
                        column.toLowerCase() === '문장') {
                        sentenceColumn = column;
                        break;
                    }
                }
                
                if (sentenceColumn) {
                    // 'sentence' 컬럼에서 데이터 추출
                    this.sentences = jsonData
                        .map(row => row[sentenceColumn])
                        .filter(sentence => sentence && sentence.toString().trim() !== '');
                    
                    console.log(`'${sentenceColumn}' 컬럼에서 로드된 문장 수: ${this.sentences.length}`);
                    console.log('첫 번째 문장 예시:', this.sentences[0]);
                } else {
                    throw new Error(`'sentence' 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: ${columns.join(', ')}`);
                }
            } else {
                throw new Error('Excel 파일에 데이터가 없습니다.');
            }
            
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
            console.log('테스트용 샘플 데이터를 사용합니다.');
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
        
        // 마지막 어절인지 확인
        const isLastWord = this.currentWordIndex === words.length - 1;
        
        if (isLastWord) {
            // 마지막 어절: 입력 필드 숨기고 완료 메시지 표시
            document.getElementById('currentSentence').textContent = displayText;
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
            // 예측 단계: 화면 업데이트 후 타이밍 측정
            this.prepareForPrediction(displayText);
        }
        
        // 진행률 업데이트 (예측 단계만 계산)
        const totalSteps = this.sentences.reduce((total, sentence) => {
            return total + this.splitIntoWords(sentence).length - 1;
        }, 0);
        const currentStep = this.getCurrentStep();
        document.getElementById('progressText').textContent = `${currentStep}/${totalSteps}`;
    }

    // 예측 단계 준비
    prepareForPrediction(displayText) {
        // 화면 업데이트
        document.getElementById('currentSentence').textContent = displayText;
        document.getElementById('predictionInput').style.display = 'block';
        document.getElementById('confirmPrediction').style.display = 'block';
        document.querySelector('.prediction-section p').textContent = '다음에 올 것 같은 어절을 입력해 주세요:';
        document.getElementById('predictionInput').value = '';
        
        // 입력 대기 상태 활성화
        this.isWaitingForInput = true;
        
        // inputStartTime 리셋
        this.inputStartTime = null;
        
        // 화면 렌더링 완료 후 제시 시간 기록
        this.recordScreenDisplayTime();
        
        // 포커스 설정
        requestAnimationFrame(() => {
            document.getElementById('predictionInput').focus();
        });
    }

    // 화면 제시 시간 기록 (렌더링 완료 후)
    recordScreenDisplayTime() {
        // DOM 업데이트가 완료된 후 시간 기록
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                // 추가로 약간의 지연을 두어 렌더링 완료 보장
                setTimeout(() => {
                    this.screenDisplayTime = performance.now();
                    console.log('화면 제시 시간 기록:', this.screenDisplayTime, 'ms');
                    console.log('화면 제시 시간 (Date.now):', Date.now(), 'ms');
                }, 50);
            });
        });
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
        if (!this.inputStartTime && this.isWaitingForInput) {
            this.inputStartTime = performance.now();
            console.log('입력 시작 시간 기록:', this.inputStartTime, 'ms');
            console.log('입력 시작 시간 (Date.now):', Date.now(), 'ms');
            
            // 입력 대기 상태 비활성화
            this.isWaitingForInput = false;
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
        
        // responseTime 계산
        let responseTime = 0;
        if (this.inputStartTime && this.screenDisplayTime) {
            responseTime = this.inputStartTime - this.screenDisplayTime;
            
            console.log('=== 반응시간 계산 결과 ===');
            console.log('화면 제시 시간:', this.screenDisplayTime, 'ms');
            console.log('입력 시작 시간:', this.inputStartTime, 'ms');
            console.log('반응시간:', responseTime, 'ms');
            console.log('반응시간 (초):', (responseTime / 1000).toFixed(3), '초');
            
            // 추가 디버깅 정보
            if (this.experimentStartTime) {
                console.log('실험 시작 시간:', this.experimentStartTime, 'ms');
                console.log('화면 제시까지 경과:', this.screenDisplayTime - this.experimentStartTime, 'ms');
                console.log('입력까지 경과:', this.inputStartTime - this.experimentStartTime, 'ms');
            }
            
            // 음수인 경우 경고
            if (responseTime < 0) {
                console.warn('⚠️ 음수 responseTime 감지:', responseTime, 'ms');
                console.warn('이는 화면 제시 시간이 입력 시작 시간보다 늦게 기록되었음을 의미합니다.');
                responseTime = 0;
            }
        } else {
            console.warn('⚠️ 타이밍 데이터 누락');
            console.warn('screenDisplayTime:', this.screenDisplayTime);
            console.warn('inputStartTime:', this.inputStartTime);
        }
        
        const result = {
            participantId: this.participantId,
            participantNumber: this.participantNumber,
            participantGender: this.participantGender,
            participantAge: this.participantAge,
            sentenceIndex: this.currentSentenceIndex,
            wordIndex: this.currentWordIndex,
            predictedWord: prediction,
            actualNextWord: actualNextWord,
            screenDisplayTime: this.screenDisplayTime || 0,
            inputStartTime: this.inputStartTime || 0,
            responseTime: responseTime,
            timestamp: new Date().toISOString()
        };
        
        this.results.push(result);
        console.log('결과 저장 완료:', result);
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
