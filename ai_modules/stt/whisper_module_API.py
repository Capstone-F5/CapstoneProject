"""
스크립트/테스트용 동기 Whisper 래퍼.

FastAPI 백엔드에서는 backend/core/stt_service.py 의 비동기 transcribe_bytes 를 사용한다.
이 파일은 ai_modules/stt/test_whisper.py 등 독립 실행 테스트용으로 유지.

Zero-shot 자동 언어 감지: language 파라미터를 넘기지 않고 verbose_json 으로 감지된 언어 반환.
"""
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def transcribe_audio(file_path: str):
    """파일 경로 → {text, language, duration} (또는 {text:'', error:str})"""
    try:
        with open(file_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
            )
        return {
            "text": (response.text or "").strip(),
            "language": getattr(response, "language", None),
            "duration": getattr(response, "duration", None),
        }
    except Exception as e:
        return {"text": "", "error": str(e)}
