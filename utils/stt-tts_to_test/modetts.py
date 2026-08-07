from transformers import pipeline

pipe = pipeline("text-to-speech", model="Audio8/Audio8-TTS-Preview-0.6b", trust_remote_code=True)