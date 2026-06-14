from transformers import AutoModelForSeq2SeqLM
model = AutoModelForSeq2SeqLM.from_pretrained("bosonai/higgs-audio-v3-tts-4b", dtype="auto")