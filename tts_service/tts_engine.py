# tts_engine.py - Reverted to working TTS engine approach
import time
import torch
import numpy as np
import soundfile as sf
import torchaudio as ta
from pathlib import Path
from typing import Optional
import os

class TTSEngine:
    def __init__(self, temp_dir: Path):
        self.temp_dir = temp_dir
        self.model = None
        self.sample_rate = 24000
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize Chatterbox TTS model"""
        try:
            print("[TTS ENGINE] Initializing Chatterbox TTS...")
            from chatterbox.tts import ChatterboxTTS
            
            # Check GPU availability
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"[TTS ENGINE] Using device: {device}")
            
            if device == "cuda":
                print(f"[TTS ENGINE] GPU: {torch.cuda.get_device_name()}")
                
                # Basic CUDA optimizations
                torch.backends.cudnn.benchmark = True
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True
                print("[TTS ENGINE] Enabled CUDA optimizations")
            
            # Initialize model
            self.model = ChatterboxTTS.from_pretrained(device=device)
            self.sample_rate = self.model.sr
            
            print(f"[TTS ENGINE] Chatterbox initialized (sample rate: {self.sample_rate}Hz)")
            
        except ImportError:
            print("[TTS ENGINE] ERROR: chatterbox package not found")
            self.model = None
        except Exception as e:
            print(f"[TTS ENGINE] Failed to initialize: {e}")
            self.model = None
    
    def generate_audio(self, text: str, reference_voice: Optional[str] = None, target_volume: float = 1.0) -> Optional[Path]:
        """Generate audio and return path to saved file (supports local and remote)"""
        # Try remote TTS first if enabled
        from remote_tts_client import create_remote_client
        remote_client = create_remote_client()
        
        if remote_client:
            print("[TTS ENGINE] Using remote TTS generation...")
            remote_file = remote_client.generate_tts_file(text, reference_voice, target_volume)
            if remote_file:
                print(f"[TTS ENGINE] Remote TTS successful: {remote_file}")
                return remote_file
            else:
                print("[TTS ENGINE] Remote TTS failed, falling back to local...")
        
        # Local TTS generation (original code)
        if not self.model:
            print("[TTS ENGINE] Local model not initialized")
            return None

        start_time = time.time()

        try:
            print(f"[TTS ENGINE] Generating audio locally...")
            
            # Use working parameters
            if reference_voice and os.path.exists(reference_voice):
                print(f"[TTS ENGINE] Using voice reference: {Path(reference_voice).name}")
                wav = self.model.generate(
                    text,
                    audio_prompt_path=reference_voice,
                    exaggeration=0.2,
                    cfg_weight=0.8
                )
            else:
                print("[TTS ENGINE] Using default voice")
                wav = self.model.generate(
                    text,
                    exaggeration=0.2,
                    cfg_weight=0.8
                )
            
            generation_time = time.time() - start_time
            
            # Get audio info
            if hasattr(wav, 'shape'):
                audio_length = wav.shape[0] if len(wav.shape) == 1 else wav.shape[-1]
            else:
                audio_length = len(wav)
            
            audio_duration = audio_length / self.sample_rate
            rtf = audio_duration / generation_time if generation_time > 0 else 0
            
            print(f"[TTS ENGINE] Generated audio: {audio_duration:.2f}s ({audio_length} samples)")
            print(f"[TTS ENGINE] Generation time: {generation_time:.2f}s, RTF: {rtf:.2f}x")
            
            if audio_length <= 1:
                print("[TTS ENGINE] ERROR: TTS generation failed - only got 1 sample")
                return None
            
            # Use the WORKING method: save with torchaudio first, then reload
            temp_raw = self.temp_dir / f"raw_tts_{int(time.time() * 1000)}.wav"
            
            print(f"[TTS ENGINE] Saving raw audio: {temp_raw}")
            ta.save(temp_raw, wav, self.sample_rate)
            
            # Load back as numpy for volume processing
            audio_data, loaded_sr = sf.read(temp_raw)
            print(f"[TTS ENGINE] Loaded audio: {len(audio_data)} samples at {loaded_sr}Hz")
            
            # Ensure mono
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
                print("[TTS ENGINE] Converted to mono")
            
            # Apply volume scaling
            if target_volume != 1.0:
                audio_data = audio_data * target_volume
                # Prevent clipping
                max_val = np.max(np.abs(audio_data))
                if max_val > 1.0:
                    audio_data = audio_data / max_val
                print(f"[TTS ENGINE] Applied volume scaling: {target_volume}")
            
            # Save final audio
            final_file = self.temp_dir / f"final_tts_{int(time.time() * 1000)}.wav"
            sf.write(final_file, audio_data, self.sample_rate)
            
            # Clean up temp file
            temp_raw.unlink(missing_ok=True)
            
            print(f"[TTS ENGINE] Final audio: {len(audio_data)} samples, {final_file.stat().st_size} bytes")
            
            return final_file
            
        except Exception as e:
            print(f"[TTS ENGINE] Generation failed: {e}")
            import traceback
            traceback.print_exc()
            return None