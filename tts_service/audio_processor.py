# audio_processor.py - Audio conversion and radio effects
import subprocess
from pathlib import Path
from typing import Optional
from audio_normalizer import AudioNormalizer
from radio_effects_processor import RadioEffectsProcessor

class AudioProcessor:
    def __init__(self, temp_dir: Path):
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(exist_ok=True)
        self.normalizer = AudioNormalizer(temp_dir)
        self.radio_processor = RadioEffectsProcessor(temp_dir)
    
    def convert_mp3_to_wav(self, mp3_file: Path, wav_file: Path, voice_config: dict = None, target_volume: float = 1.0) -> bool:
        """Convert MP3 to WAV with advanced radio effects and normalization"""
        print(f"[AUDIO PROC] Converting MP3 to WAV with advanced processing...")
        
        # Extract faction info from voice config for faction-specific effects
        faction = ""
        radio_strength = 0.8  # Default radio strength
        
        if voice_config:
            # Try to get faction from voice effects
            voice_effects = voice_config.get('voice_effects', [])
            for effect in voice_effects:
                if effect.get('type') == 'radio':
                    radio_strength = effect.get('strength', 0.8)
                    break
            
            # Get faction from style prompt or other sources
            style_prompt = voice_config.get('style_prompt', '').lower()
            if 'military' in style_prompt or 'army' in style_prompt:
                faction = 'army'
            elif 'duty' in style_prompt:
                faction = 'duty'
            elif 'bandit' in style_prompt or 'criminal' in style_prompt:
                faction = 'bandit'
            elif 'freedom' in style_prompt or 'rebel' in style_prompt:
                faction = 'freedom'
            elif 'monolith' in style_prompt or 'fanatical' in style_prompt:
                faction = 'monolith'
            else:
                faction = 'stalker'  # Generic
        
        print(f"[AUDIO PROC] Detected faction: {faction}, radio strength: {radio_strength}")
        
        try:
            # Step 1: Basic MP3 to WAV conversion
            temp_wav = self.temp_dir / f"temp_{wav_file.name}"
            result = subprocess.run([
                'ffmpeg', '-i', str(mp3_file),
                '-acodec', 'pcm_s16le',  # PCM 16-bit for Windows
                '-ar', '44100',          # 44.1kHz sample rate
                '-ac', '1',              # Mono
                '-y', str(temp_wav)      # Overwrite existing
            ], check=True, capture_output=True, text=True)
            
            if not temp_wav.exists():
                print(f"[AUDIO PROC] Basic conversion failed")
                return False
            
            print(f"[AUDIO PROC] Basic conversion complete: {temp_wav.stat().st_size} bytes")
            
            # Step 2: Apply advanced radio effects
            radio_processed = self.radio_processor.apply_radio_effects(temp_wav, radio_strength)
            if radio_processed and radio_processed != temp_wav:
                temp_wav = radio_processed
                print(f"[AUDIO PROC] Radio effects applied: {temp_wav.stat().st_size} bytes")
            
            # Step 3: Add faction-specific transmission effects (squelch)
            transmission_processed = self.radio_processor.add_transmission_effects(temp_wav, faction)
            if transmission_processed and transmission_processed != temp_wav:
                temp_wav = transmission_processed
                print(f"[AUDIO PROC] Transmission effects applied: {temp_wav.stat().st_size} bytes")
            
            # Step 4: Normalize audio levels and apply target volume
            normalized_file = self.normalizer.normalize_audio(temp_wav, target_volume)
            if normalized_file and normalized_file != temp_wav:
                # Move normalized file to final location
                normalized_file.rename(wav_file)
                print(f"[AUDIO PROC] Audio normalized and moved to final location")
            else:
                # Move temp file to final location
                temp_wav.rename(wav_file)
                print(f"[AUDIO PROC] Audio moved to final location (normalization skipped)")
            
            print(f"[AUDIO PROC] Final enhanced audio ready: {wav_file.stat().st_size} bytes")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"[AUDIO PROC] FFmpeg error: {e}")
            if e.stderr:
                print(f"[AUDIO PROC] FFmpeg stderr: {e.stderr}")
            return False
        except Exception as e:
            print(f"[AUDIO PROC] Processing error: {e}")
            return False
                
        except subprocess.CalledProcessError as e:
            print(f"[AUDIO PROC] FFmpeg error: {e}")
            if e.stderr:
                print(f"[AUDIO PROC] FFmpeg stderr: {e.stderr}")
            return False
        except Exception as e:
            print(f"[AUDIO PROC] Conversion error: {e}")
            return False
    
    def add_radio_squelch_effects(self, wav_file: Path) -> Optional[Path]:
        """Add radio squelch sounds before and after the audio"""
        try:
            # Create radio squelch files if they don't exist
            squelch_start = self._create_or_get_squelch_audio("start")
            squelch_end = self._create_or_get_squelch_audio("end")
            
            if not squelch_start or not squelch_end:
                print("[AUDIO PROC] Could not create squelch audio, skipping radio effects")
                return wav_file
            
            # Create enhanced filename
            enhanced_file = wav_file.parent / f"radio_{wav_file.name}"
            
            # Use FFmpeg to concatenate: squelch_start + audio + squelch_end
            concat_list = self.temp_dir / f"concat_{wav_file.stem}.txt"
            with open(concat_list, 'w') as f:
                f.write(f"file '{squelch_start.resolve()}'\n")
                f.write(f"file '{wav_file.resolve()}'\n") 
                f.write(f"file '{squelch_end.resolve()}'\n")
            
            result = subprocess.run([
                'ffmpeg', '-f', 'concat', '-safe', '0', '-i', str(concat_list),
                '-c', 'copy', '-y', str(enhanced_file)
            ], check=True, capture_output=True, text=True)
            
            # Clean up concat file
            concat_list.unlink(missing_ok=True)
            
            if enhanced_file.exists():
                # Replace original with enhanced version
                wav_file.unlink()
                enhanced_file.rename(wav_file)
                return wav_file
            else:
                print("[AUDIO PROC] Enhanced audio file not created")
                return wav_file
                
        except Exception as e:
            print(f"[AUDIO PROC] Radio effects failed: {e}")
            return wav_file  # Return original on failure
    
    def _create_or_get_squelch_audio(self, position: str) -> Optional[Path]:
        """Create or get radio squelch audio file"""
        squelch_file = self.temp_dir / f"radio_squelch_{position}.wav"
        
        if squelch_file.exists():
            return squelch_file
        
        try:
            # Generate radio squelch sound using FFmpeg
            if position == "start":
                # Short ascending tone burst
                result = subprocess.run([
                    'ffmpeg', '-f', 'lavfi', 
                    '-i', 'sine=frequency=800:duration=0.15',  # 150ms tone
                    '-af', 'volume=0.3,highpass=f=500,lowpass=f=1500',  # Radio filter
                    '-ar', '44100', '-ac', '1',
                    '-y', str(squelch_file)
                ], check=True, capture_output=True, text=True)
            else:  # end
                # Short descending tone burst  
                result = subprocess.run([
                    'ffmpeg', '-f', 'lavfi',
                    '-i', 'sine=frequency=600:duration=0.1',   # 100ms lower tone
                    '-af', 'volume=0.2,highpass=f=500,lowpass=f=1500',  # Radio filter
                    '-ar', '44100', '-ac', '1', 
                    '-y', str(squelch_file)
                ], check=True, capture_output=True, text=True)
            
            if squelch_file.exists():
                print(f"[AUDIO PROC] Created radio squelch: {position}")
                return squelch_file
            else:
                return None
                
        except subprocess.CalledProcessError as e:
            print(f"[AUDIO PROC] Failed to create radio squelch {position}: {e}")
            return None
        except Exception as e:
            print(f"[AUDIO PROC] Squelch creation error: {e}")
            return None