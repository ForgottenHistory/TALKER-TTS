# audio_normalizer.py - Audio normalization and volume equalization
import subprocess
from pathlib import Path
from typing import Optional

class AudioNormalizer:
    def __init__(self, temp_dir: Path):
        self.temp_dir = temp_dir
        self.target_lufs = -23.0  # Standard loudness target (similar to broadcast standards)
        
    def normalize_audio(self, input_file: Path, target_volume: float = 1.0) -> Optional[Path]:
        """Normalize audio levels and apply target volume"""
        if not input_file.exists():
            print(f"[NORMALIZER] Input file does not exist: {input_file}")
            return None
        
        # Create normalized filename
        normalized_file = self.temp_dir / f"normalized_{input_file.name}"
        
        try:
            # Two-pass normalization using FFmpeg
            # Pass 1: Analyze loudness
            loudness_data = self._analyze_loudness(input_file)
            if not loudness_data:
                print("[NORMALIZER] Loudness analysis failed, using simple volume adjustment")
                return self._simple_volume_adjustment(input_file, target_volume)
            
            # Pass 2: Apply loudness normalization + target volume
            success = self._apply_normalization(input_file, normalized_file, loudness_data, target_volume)
            
            if success and normalized_file.exists():
                print(f"[NORMALIZER] Audio normalized: {normalized_file.stat().st_size} bytes")
                return normalized_file
            else:
                print("[NORMALIZER] Normalization failed, using original file")
                return input_file
                
        except Exception as e:
            print(f"[NORMALIZER] Normalization error: {e}")
            return input_file  # Return original on failure
    
    def _analyze_loudness(self, audio_file: Path) -> Optional[dict]:
        """Analyze audio loudness using FFmpeg"""
        try:
            # Use FFmpeg loudnorm filter to analyze
            result = subprocess.run([
                'ffmpeg', '-i', str(audio_file),
                '-af', f'loudnorm=I={self.target_lufs}:print_format=json',
                '-f', 'null', '-'
            ], capture_output=True, text=True, timeout=30)
            
            # Parse loudness data from stderr (FFmpeg outputs analysis there)
            stderr_lines = result.stderr.split('\n')
            json_started = False
            json_lines = []
            
            for line in stderr_lines:
                if '"input_i"' in line:
                    json_started = True
                if json_started:
                    json_lines.append(line)
                if json_started and '}' in line:
                    break
            
            if json_lines:
                import json
                try:
                    # Clean up the JSON lines
                    json_text = '\n'.join(json_lines)
                    json_text = json_text.replace('\t', '').strip()
                    if not json_text.startswith('{'):
                        json_text = '{' + json_text
                    
                    loudness_info = json.loads(json_text)
                    print(f"[NORMALIZER] Analyzed loudness: {loudness_info.get('input_i', 'unknown')} LUFS")
                    return loudness_info
                except json.JSONDecodeError as e:
                    print(f"[NORMALIZER] JSON parse error: {e}")
                    return None
            
        except subprocess.TimeoutExpired:
            print("[NORMALIZER] Loudness analysis timeout")
        except Exception as e:
            print(f"[NORMALIZER] Loudness analysis failed: {e}")
        
        return None
    
    def _apply_normalization(self, input_file: Path, output_file: Path, loudness_data: dict, target_volume: float) -> bool:
        """Apply loudness normalization with target volume"""
        try:
            # Get loudness values
            input_i = float(loudness_data.get('input_i', -23.0))
            input_tp = float(loudness_data.get('input_tp', -2.0))
            input_lra = float(loudness_data.get('input_lra', 7.0))
            input_thresh = float(loudness_data.get('input_thresh', -34.0))
            
            # Calculate final volume adjustment (MCM volume + normalization)
            # Convert target_volume (0.0-1.0) to dB adjustment
            volume_db = 20 * (target_volume ** 0.5) - 20  # Perceptual volume curve
            
            # Apply two-pass loudness normalization
            result = subprocess.run([
                'ffmpeg', '-i', str(input_file),
                '-af', f'loudnorm=I={self.target_lufs}:TP=-1.0:LRA=7.0:measured_I={input_i}:measured_TP={input_tp}:measured_LRA={input_lra}:measured_thresh={input_thresh}:linear=true,volume={volume_db}dB',
                '-ar', '44100', '-ac', '1',  # Ensure consistent format
                '-y', str(output_file)
            ], capture_output=True, text=True, timeout=30)
            
            success = result.returncode == 0
            if not success:
                print(f"[NORMALIZER] Normalization failed: {result.stderr}")
            
            return success
            
        except Exception as e:
            print(f"[NORMALIZER] Apply normalization error: {e}")
            return False
    
    def _simple_volume_adjustment(self, input_file: Path, target_volume: float) -> Optional[Path]:
        """Simple volume adjustment as fallback"""
        try:
            adjusted_file = self.temp_dir / f"volume_adjusted_{input_file.name}"
            
            # Convert target_volume to dB
            if target_volume <= 0:
                volume_db = -60  # Very quiet
            else:
                volume_db = 20 * (target_volume ** 0.5) - 20
            
            result = subprocess.run([
                'ffmpeg', '-i', str(input_file),
                '-af', f'volume={volume_db}dB',
                '-ar', '44100', '-ac', '1',
                '-y', str(adjusted_file)
            ], capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0 and adjusted_file.exists():
                print(f"[NORMALIZER] Simple volume adjustment applied: {volume_db:.1f}dB")
                return adjusted_file
            else:
                print(f"[NORMALIZER] Volume adjustment failed: {result.stderr}")
                return input_file
                
        except Exception as e:
            print(f"[NORMALIZER] Simple volume adjustment error: {e}")
            return input_file