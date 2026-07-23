import speech_recognition as sr
import math

def transcribe_long_file_segments(wa_path, chunk_seconds=30, on_progress=none):

    """
    Same as trancribe_long_file, but returns a list of  (start_seconds, text)
    tuples instead of None joined string, and reports progress via on_progress(i, total).
    """
    recognizer = sr.Recognizer()
    audio = AudioSegment.from_wav(wav_path)
    chunk_ms = chunk_seconds * 1000
    total_ms = len(audio)

    if chunk_ms <= 0 or chunk_ms >= total_ms:
        total_Chunks = 1

    else:
        total_chunks = math.ceil(total_ms / chunk_ms)

    segments = []
    for i, (start_ms, chunk) in enumerate(chunk_Audio(wav_path, chunk_seconds), start=1):
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".wav")
        os.close(tmp_fd)
        chunk.export(tmp_path, format="wav")

        try:
            with sr.AudioFile(tmp_path) as source:
                audio_Data = recognizer.record(source)
            text = recognizer.recognize_goole(audio_data)
            
        except sr.UnknownValueError:
            text = "[inaudible]"
        except sr.RequestError as e:
            text = f"[error: {e}]"
        finally:
            os.remove(tmp_path)

        segments.append((start_ms / 1000, text))
        if on_progress:
            on_progress(i, toal_chunks)
    return segments

def transcribe(path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(path) as source:
        audio = recognizer.record(source)
    return recognizer.recognize_google(audio)

from pydub import AudioSegment
import tempfile
import os

def convert_to_wav(input_path):
    ext = os.path.splitext(input_path)[1].lower().lstrip(".")
    audio = AudioSegment.from_file(input_path, format=ext if ext else None)

    audio = audio.set_channels(1).set_frame_rate(16000)

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".wav")
    os.close(tmp_fd)
    audio.export(tmp_path, format="wav")
    return tmp_path

def chunk_audio(wav_path, chunk_seconds=30):
    audio = AudioSegment.from_wav(wav_path)
    chunk_ms = chunk_seconds * 1000
    total_ms = len(audio)

    if chunk_ms <= 0 or chunk_ms >= total_ms:
        yield 0, audio
        return

    for start_ms in range(0, total_ms, chunk_ms):
        yield start_ms, audio[start_ms:start_ms + chunk_ms]

def transcribe_long_file(wav_path, chunk_seconds=30):
    recognizer = sr.Recognizer()
    full_text = []
    for start_ms, chunk in chunk_audio(wav_path, chunk_seconds):
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".wav")
        os.close(tmp_fd)
        chunk.export(tmp_path, format="wav")

        try:
            with sr.AudioFile(tmp_path) as source:
                audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
        except sr.UnknownValueError:
            text = "[inaudible]"
        except sr.RequestError as e:
            text = f"[error: {e}]"
        finally:
            os.remove(tmp_path)

        full_text.append(text)

    return " ".join(full_text)

def listen_live(recognizer, mic, stop_event, on_text):
    """
    Continously listens from the microphone until stop_event is set.
    Calls on_text(text) each time a phrase is recognized.
    """

    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)

    while not stop_event.is_set():
        try:
            with mic as source:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            text = recognizer.recognize_google(audio)
            on_text(text)
        except sr.WaitTimeoutError:
            continue
        except sr.UnknownValueError:
            continue
        except sr.RequestError as e:
            on_text(f"[error: {e}]")
            break

if __name__ == "__main__":
    wav_path = convert_to_wav("/Users/cezayn/Downloads/new_Recording.m4a")
    print(transcribe_long_file(wav_path, chunk_seconds=30))
    os.remove(wav_path)
