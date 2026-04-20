import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# 1. API 키를 사용해 클라이언트 설정
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def transcribe_audio(file_path: str):
    """
    OpenAI 서버에 파일을 보내서 결과를 받아옴
    """
    try:
        # 2. 파일 읽어서 서버로 전송
        with open(file_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ko"
            )

        return {
            "text": response.text.strip(),
            "language": "ko"
        }
    except Exception as e:
        return {"text": "", "error": str(e)}