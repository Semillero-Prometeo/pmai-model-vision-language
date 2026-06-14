import os
from huggingface_hub import InferenceClient
import nemo.collections.asr as nemo_asr
asr_model = nemo_asr.models.ASRModel.from_pretrained("nvidia/nemotron-3.5-asr-streaming-0.6b")
transcriptions = asr_model.transcribe(["file.wav"])


def transcribe_audio(file_path):
    os.environ['HF_TOKEN'] = 'YOUR_TOKEN_HERE'
    client = InferenceClient(
        provider="auto",
        api_key=os.environ["HF_TOKEN"],
    )

    output = client.automatic_speech_recognition("sample1.flac", model="nvidia/nemotron-3.5-asr-streaming-0.6b")