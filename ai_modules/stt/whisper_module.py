import whisper

# 모델 로드 (처음 실행 시 자동 다운로드)
model = whisper.load_model("base")#테스트용으로 base사용, 차후 변경 O

def transcribe_audio(file_path: str):
    """
    음성 파일을 텍스트로 변환하는 함수
    - file_path: 음성 파일 경로 (wav, mp3 등)
    """
    result = model.transcribe(file_path)#음성분석 결과
    
    return {
        "text": result["text"],         # 변환된 텍스트
        "language": result["language"]  # 감지된 언어 (ko, en 등)
    }