import os
import re
import sys
import asyncio
import tempfile
import uuid
import glob
import subprocess
import edge_tts
import requests
import imageio_ffmpeg

# Voice Mapping Definitions
VOICES = {
    "female_hoaimy": {
        "id": "vi-VN-HoaiMyNeural",
        "name": "Giọng Nữ - Hoài My (Việt Nam)",
        "gender": "Nữ",
        "desc": "Giọng đọc nữ Tiếng Việt truyền cảm, tự nhiên",
        "icon": "👩"
    },
    "male_namminh": {
        "id": "vi-VN-NamMinhNeural",
        "name": "Giọng Nam - Nam Minh (Việt Nam)",
        "gender": "Nam",
        "desc": "Giọng đọc nam Tiếng Việt trầm ấm, rõ ràng",
        "icon": "👨"
    },
    "elevenlabs_adam": {
        "id": "pNInz6obpgDQGcFmaJgB",
        "name": "Giọng Nam - Adam (ElevenLabs Chuẩn 100% Gốc)",
        "gender": "Nam",
        "desc": "Giọng Adam gốc chính chủ từ ElevenLabs AI",
        "icon": "🌟"
    },
    "male_adam_neural": {
        "id": "en-US-AndrewMultilingualNeural",
        "name": "Giọng Nam - Adam (Microsoft Multilingual)",
        "gender": "Nam",
        "desc": "Giọng Nam đa ngôn ngữ miễn phí (Phong cách Adam)",
        "icon": "🎙️"
    }
}

class TTSEngine:
    def __init__(self):
        self.temp_dir = os.path.join(tempfile.gettempdir(), "viet_tts_studio")
        os.makedirs(self.temp_dir, exist_ok=True)
        self.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        self.win_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        self.default_eleven_key = "sk_f20e4b85d31248a39c18d9f52a71e860"

    def _cleanup_old_temp_files(self):
        """Clean up old temporary viet_tts audio files"""
        try:
            pattern = os.path.join(self.temp_dir, "tts_*.*")
            for f in glob.glob(pattern):
                try:
                    os.remove(f)
                except Exception:
                    pass
        except Exception:
            pass

    def split_text_into_chunks(self, text: str, max_chunk_len: int = 350) -> list[str]:
        """
        Split long text into natural sentence chunks to prevent edge-tts WebSocket
        timeouts or packet dropping on long scripts.
        """
        text = text.strip()
        if not text:
            return []
        
        if len(text) <= max_chunk_len:
            return [text]

        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        chunks = []

        for para in paragraphs:
            if len(para) <= max_chunk_len:
                chunks.append(para)
            else:
                sentences = re.split(r'(?<=[.!?;\n])\s+', para)
                current_chunk = ""
                for s in sentences:
                    s = s.strip()
                    if not s:
                        continue
                    if len(current_chunk) + len(s) + 1 <= max_chunk_len:
                        current_chunk = f"{current_chunk} {s}".strip()
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        if len(s) > max_chunk_len:
                            sub_parts = re.split(r'(?<=[,])\s+', s)
                            sub_chunk = ""
                            for sp in sub_parts:
                                if len(sub_chunk) + len(sp) + 1 <= max_chunk_len:
                                    sub_chunk = f"{sub_chunk} {sp}".strip()
                                else:
                                    if sub_chunk:
                                        chunks.append(sub_chunk)
                                    sub_chunk = sp
                            if sub_chunk:
                                chunks.append(sub_chunk)
                            current_chunk = ""
                        else:
                            current_chunk = s
                if current_chunk:
                    chunks.append(current_chunk)

        return chunks if chunks else [text]

    async def _generate_chunk_edge(self, text_chunk: str, voice_id: str, rate_str: str, pitch_str: str, volume_str: str, raw_chunk_path: str):
        communicate = edge_tts.Communicate(
            text=text_chunk,
            voice=voice_id,
            rate=rate_str,
            pitch=pitch_str,
            volume=volume_str
        )
        await communicate.save(raw_chunk_path)

    def reencode_to_standard_audio(self, raw_audio_files: list[str], final_output_path: str, format_type: str = "mp3") -> str:
        """
        Re-encodes and fixes raw audio chunks into standard 44.1kHz Stereo LAME MP3 / WAV
        with full frame index and valid duration header for 100% compatibility with CapCut,
        Premiere Pro, Audacity, DaVinci Resolve, Canva, etc.
        """
        if not raw_audio_files:
            raise ValueError("Không có file âm thanh đầu vào để xử lý!")

        if len(raw_audio_files) == 1:
            if format_type.lower() == "wav":
                cmd = [
                    self.ffmpeg_exe, "-y",
                    "-i", raw_audio_files[0],
                    "-c:a", "pcm_s16le",
                    "-ar", "44100",
                    "-ac", "2",
                    final_output_path
                ]
            else:
                cmd = [
                    self.ffmpeg_exe, "-y",
                    "-i", raw_audio_files[0],
                    "-c:a", "libmp3lame",
                    "-b:a", "320k",
                    "-ar", "44100",
                    "-ac", "2",
                    "-id3v2_version", "3",
                    final_output_path
                ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, creationflags=self.win_flags)
        else:
            concat_list_file = os.path.join(self.temp_dir, f"concat_{uuid.uuid4().hex[:8]}.txt")
            with open(concat_list_file, "w", encoding="utf-8") as f:
                for path in raw_audio_files:
                    escaped_path = path.replace("\\", "/")
                    f.write(f"file '{escaped_path}'\n")

            if format_type.lower() == "wav":
                cmd = [
                    self.ffmpeg_exe, "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", concat_list_file,
                    "-c:a", "pcm_s16le",
                    "-ar", "44100",
                    "-ac", "2",
                    final_output_path
                ]
            else:
                cmd = [
                    self.ffmpeg_exe, "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", concat_list_file,
                    "-c:a", "libmp3lame",
                    "-b:a", "320k",
                    "-ar", "44100",
                    "-ac", "2",
                    "-id3v2_version", "3",
                    final_output_path
                ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, creationflags=self.win_flags)
            try:
                os.remove(concat_list_file)
            except Exception:
                pass

        return final_output_path

    async def generate_speech_edge(self, text: str, voice_id: str, rate: int = 0, pitch: int = 0, volume: int = 0, output_path: str = None) -> str:
        self._cleanup_old_temp_files()
        
        rate_str = f"{'+' if rate >= 0 else ''}{rate}%"
        pitch_str = f"{'+' if pitch >= 0 else ''}{pitch}Hz"
        volume_str = f"{'+' if volume >= 0 else ''}{volume}%"

        chunks = self.split_text_into_chunks(text)
        chunk_files = []

        try:
            for idx, chunk in enumerate(chunks):
                chunk_file = os.path.join(self.temp_dir, f"tts_chunk_{uuid.uuid4().hex[:8]}_{idx}.mp3")
                await self._generate_chunk_edge(chunk, voice_id, rate_str, pitch_str, volume_str, chunk_file)
                chunk_files.append(chunk_file)

            if not output_path:
                output_path = os.path.join(self.temp_dir, f"tts_master_{uuid.uuid4().hex[:8]}.mp3")

            self.reencode_to_standard_audio(chunk_files, output_path, format_type="mp3")
            return output_path
        finally:
            for cf in chunk_files:
                try:
                    if os.path.exists(cf):
                        os.remove(cf)
                except Exception:
                    pass

    def generate_speech_elevenlabs(self, text: str, api_key: str = "", output_path: str = None) -> str:
        self._cleanup_old_temp_files()
        
        raw_output_path = os.path.join(self.temp_dir, f"tts_eleven_raw_{uuid.uuid4().hex[:8]}.mp3")
        if not output_path:
            output_path = os.path.join(self.temp_dir, f"tts_eleven_master_{uuid.uuid4().hex[:8]}.mp3")

        key_to_use = api_key.strip() if api_key and api_key.strip() else self.default_eleven_key.strip()

        adam_voice_id = "pNInz6obpgDQGcFmaJgB"
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{adam_voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": key_to_use
        }

        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True
            }
        }

        try:
            response = requests.post(url, json=data, headers=headers, timeout=30)
            if response.status_code == 200:
                with open(raw_output_path, "wb") as f:
                    f.write(response.content)
                self.reencode_to_standard_audio([raw_output_path], output_path, format_type="mp3")
                try:
                    os.remove(raw_output_path)
                except Exception:
                    pass
                return output_path
            else:
                print(f"ElevenLabs API warning ({response.status_code}): {response.text}. Falling back to Neural Adam...")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(
                        self.generate_speech_edge(text, "en-US-AndrewMultilingualNeural", 0, -4, 0, output_path)
                    )
                finally:
                    loop.close()
        except Exception as e:
            print(f"ElevenLabs error ({e}). Falling back to Neural Adam...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.generate_speech_edge(text, "en-US-AndrewMultilingualNeural", 0, -4, 0, output_path)
                )
            finally:
                loop.close()

    def synthesize(self, text: str, voice_key: str, rate: int = 0, pitch: int = 0, volume: int = 0, api_key: str = "", output_path: str = None) -> str:
        if not text or not text.strip():
            raise ValueError("Văn bản không được để trống!")

        text = text.strip()

        if voice_key == "elevenlabs_adam":
            return self.generate_speech_elevenlabs(text, api_key, output_path)

        voice_info = VOICES.get(voice_key, VOICES["female_hoaimy"])
        voice_id = voice_info["id"]

        adjusted_pitch = pitch
        if voice_key == "male_adam_neural" and pitch == 0:
            adjusted_pitch = -4

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result_path = loop.run_until_complete(
                self.generate_speech_edge(text, voice_id, rate, adjusted_pitch, volume, output_path)
            )
            return result_path
        finally:
            loop.close()

    def export_audio_file(self, source_path: str, target_path: str) -> str:
        """
        Exports source audio into standard 320kbps MP3 or 16-bit PCM WAV depending on target extension.
        """
        ext = os.path.splitext(target_path)[1].lower()
        format_type = "wav" if ext == ".wav" else "mp3"
        return self.reencode_to_standard_audio([source_path], target_path, format_type=format_type)
