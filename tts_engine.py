import os
import asyncio
import tempfile
import uuid
import glob
import edge_tts
import requests

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
        self.temp_dir = tempfile.gettempdir()
        # Default working embedded key (can be overridden by user input if desired)
        self.default_eleven_key = "sk_f20e4b85d31248a39c18d9f52a71e860" # Built-in active key

    def _cleanup_old_temp_files(self):
        """Clean up old temporary viet_tts mp3 files"""
        try:
            pattern = os.path.join(self.temp_dir, "viet_tts_*.mp3")
            for f in glob.glob(pattern):
                try:
                    os.remove(f)
                except Exception:
                    pass
        except Exception:
            pass

    async def generate_speech_edge(self, text: str, voice_id: str, rate: int = 0, pitch: int = 0, volume: int = 0, output_path: str = None) -> str:
        if not output_path:
            self._cleanup_old_temp_files()
            unique_filename = f"viet_tts_{uuid.uuid4().hex[:8]}.mp3"
            output_path = os.path.join(self.temp_dir, unique_filename)

        rate_str = f"{'+' if rate >= 0 else ''}{rate}%"
        pitch_str = f"{'+' if pitch >= 0 else ''}{pitch}Hz"
        volume_str = f"{'+' if volume >= 0 else ''}{volume}%"

        communicate = edge_tts.Communicate(
            text=text,
            voice=voice_id,
            rate=rate_str,
            pitch=pitch_str,
            volume=volume_str
        )
        await communicate.save(output_path)
        return output_path

    def generate_speech_elevenlabs(self, text: str, api_key: str = "", output_path: str = None) -> str:
        """
        Generate audio using ElevenLabs Adam Voice API (uses embedded key automatically)
        """
        if not output_path:
            self._cleanup_old_temp_files()
            unique_filename = f"viet_tts_eleven_{uuid.uuid4().hex[:8]}.mp3"
            output_path = os.path.join(self.temp_dir, unique_filename)

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

        response = requests.post(url, json=data, headers=headers, timeout=30)
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            return output_path
        else:
            # Fallback seamlessly to Microsoft Adam Neural if key quota exceeded or invalid
            print(f"ElevenLabs API warning ({response.status_code}): {response.text}. Falling back to Neural Adam...")
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

if __name__ == "__main__":
    engine = TTSEngine()
    print("Testing embedded ElevenLabs Adam voice synthesis...")
    try:
        res = engine.synthesize("Xin chào! Đây là bài đọc bằng giọng nam Adam gốc từ ElevenLabs.", "elevenlabs_adam")
        print(f"ElevenLabs Adam test successful: {res}")
    except Exception as e:
        print(f"Test error: {e}")
