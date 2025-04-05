import ffmpeg
import logging

logging.basicConfig(level=logging.INFO)

def convert_to_wav_bytes(file_bytes: bytes) -> bytes:
    """
    Convert input audio to 16kHz mono WAV using ffmpeg.
    """
    try:
        out, _ = (
            ffmpeg
            .input('pipe:0')
            .output('pipe:1', format='wav', acodec='pcm_s16le', ac=1, ar='16k')
            .run(input=file_bytes, capture_stdout=True, capture_stderr=True)
        )
        return out
    except ffmpeg.Error as e:
        logging.error(f"ffmpeg error: {e.stderr.decode()}")
        raise RuntimeError("Audio conversion failed.")
