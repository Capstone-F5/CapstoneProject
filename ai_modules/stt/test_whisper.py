from whisper_module_API import transcribe_audio

result = transcribe_audio("test.mp3.m4a")
print("변환된 텍스트:", result["text"])
print("감지된 언어:", result["language"])