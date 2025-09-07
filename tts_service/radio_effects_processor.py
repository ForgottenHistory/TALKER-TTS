# radio_effects_processor.py - Enhanced telephone-style audio effects for STALKER
import numpy as np
import soundfile as sf
import subprocess
from pathlib import Path
from typing import Optional

class RadioEffectsProcessor:
    def __init__(self, temp_dir: Path):
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(exist_ok=True)
        
        # Look for STALKER PDA beep file
        self.pda_beep_file = self._find_pda_beep_file()
    
    def _find_pda_beep_file(self) -> Optional[Path]:
        """Find the STALKER PDA beep MP3 file"""
        # Common locations to check
        possible_locations = [
            Path("./pda_beep.mp3"),
            Path("./audio/pda_beep.mp3"),
            Path("./sounds/pda_beep.mp3"),
            Path("./assets/pda_beep.mp3"),
            Path("./voices/pda_beep.mp3"),
        ]
        
        for location in possible_locations:
            if location.exists():
                print(f"[RADIO FX] Found STALKER PDA beep: {location}")
                return location
        
        print("[RADIO FX] STALKER PDA beep not found, will use generated beep")
        print("[RADIO FX] Place your pda_beep.mp3 file in one of these locations:")
        for location in possible_locations:
            print(f"[RADIO FX]   {location}")
        
        return None
    
    def apply_radio_effects(self, input_file: Path, effect_strength: float = 0.8) -> Optional[Path]:
        """Apply enhanced telephone-style radio effects"""
        if not input_file.exists():
            return None
        
        print(f"[RADIO FX] Applying telephone-style radio effects (strength: {effect_strength:.2f})")
        
        # Load audio
        try:
            audio_data, sample_rate = sf.read(input_file)
            
            # Ensure mono
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
            
            print(f"[RADIO FX] Loaded audio: {len(audio_data)} samples at {sample_rate}Hz")
            
            # Apply telephone EQ
            eq_processed = self._apply_telephone_eq(audio_data, sample_rate, effect_strength)
            
            # Apply digital transfer effects
            processed_audio = self._apply_digital_transfer_effects(eq_processed, sample_rate, effect_strength)
            
            # Add PDA beep (only start beep now)
            final_audio = self._add_pda_start_beep(processed_audio, sample_rate)
            
            # Normalize
            final_audio = self._normalize_audio(final_audio, target_peak=0.8)
            
            # Save processed audio
            output_file = self.temp_dir / f"radio_processed_{input_file.name}"
            sf.write(output_file, final_audio, sample_rate)
            
            print(f"[RADIO FX] Radio effects applied: {output_file.stat().st_size} bytes")
            return output_file
            
        except Exception as e:
            print(f"[RADIO FX] Processing failed: {e}")
            return input_file
    
    def _apply_telephone_eq(self, audio_data, sample_rate=24000, strength=0.8):
        """Apply muffled digital telephone-style EQ"""
        processed = audio_data.copy()
        
        # Check if audio is long enough for processing
        if len(processed) < 100:
            print(f"[RADIO FX] Audio too short for full EQ processing")
            return processed
        
        print("[RADIO FX] Applying telephone EQ...")
        
        # Create frequency domain representation
        fft_size = len(processed)
        freqs = np.fft.fftfreq(fft_size, 1/sample_rate)
        audio_fft = np.fft.fft(processed)
        
        # Create telephone frequency response curve
        freq_response = np.ones_like(freqs, dtype=complex)
        
        # Adjust strength
        hp_freq = 300.0 + (strength * 100.0)  # 300-400Hz
        lp_freq = 3000.0 - (strength * 200.0)  # 2800-3000Hz
        
        # 1. High-pass filter (remove low frequencies)
        for i, freq in enumerate(freqs):
            if abs(freq) < hp_freq:
                if abs(freq) > 0:
                    rolloff = (abs(freq) / hp_freq) ** 2
                else:
                    rolloff = 0
                freq_response[i] *= rolloff
        
        # 2. Low-pass filter (remove high frequencies)
        for i, freq in enumerate(freqs):
            if abs(freq) > lp_freq:
                rolloff = (lp_freq / abs(freq)) ** 2
                freq_response[i] *= rolloff
        
        # 3. Mid-range shaping for clarity
        boost_freq_1 = 800.0
        boost_width_1 = 600.0
        boost_gain_1 = 0.3 * strength
        
        boost_freq_2 = 1400.0
        boost_width_2 = 500.0
        boost_gain_2 = 0.4 * strength
        
        for i, freq in enumerate(freqs):
            abs_freq = abs(freq)
            
            if hp_freq <= abs_freq <= lp_freq:
                # 800Hz boost
                boost_1 = boost_gain_1 * np.exp(-((abs_freq - boost_freq_1) / boost_width_1) ** 2)
                freq_response[i] *= (1 + boost_1)
                
                # 1400Hz boost
                boost_2 = boost_gain_2 * np.exp(-((abs_freq - boost_freq_2) / boost_width_2) ** 2)
                freq_response[i] *= (1 + boost_2)
        
        # 4. Gentle rolloff above 2kHz
        for i, freq in enumerate(freqs):
            abs_freq = abs(freq)
            if abs_freq > 2000.0:
                attenuation = 1.0 - (0.2 * strength) * ((abs_freq - 2000.0) / (lp_freq - 2000.0))
                attenuation = max(0.4, attenuation)
                freq_response[i] *= attenuation
        
        # Apply the frequency response
        processed_fft = audio_fft * freq_response
        processed = np.real(np.fft.ifft(processed_fft))
        
        return processed
    
    def _apply_digital_transfer_effects(self, audio_data, sample_rate=24000, strength=0.8):
        """Apply smooth digital transfer effects"""
        processed = audio_data.copy()
        
        if len(processed) < 100:
            print(f"[RADIO FX] Audio too short for full processing")
            # Apply only gentle bit reduction for very short audio
            bit_depth = 15 - int(strength * 2)
            max_val = 2**(bit_depth-1) - 1
            processed = np.round(processed * max_val) / max_val
            return processed
        
        # 1. Bit depth reduction for digital warmth
        bit_depth = 15 - int(strength * 2)  # 13-15 bit
        max_val = 2**(bit_depth-1) - 1
        processed = np.round(processed * max_val) / max_val
        
        # 2. Smooth digital low-pass filtering
        if len(processed) > 20:
            kernel_size = 5
            kernel = np.array([0.1, 0.2, 0.4, 0.2, 0.1])
            padded = np.pad(processed, kernel_size//2, mode='edge')
            processed = np.convolve(padded, kernel, mode='valid')
        
        # 3. Gentle digital compression
        threshold = 0.15 + (strength * 0.1)
        ratio = 1.3 + (strength * 0.4)  # 1.3-1.7
        compressed_mask = np.abs(processed) > threshold
        if np.any(compressed_mask):
            over_threshold = processed[compressed_mask]
            sign = np.sign(over_threshold)
            magnitude = np.abs(over_threshold)
            
            compressed_magnitude = threshold + (magnitude - threshold) / ratio
            processed[compressed_mask] = sign * compressed_magnitude
        
        # 4. Subtle analog-style saturation
        saturation_amount = 0.05 + (strength * 0.05)
        processed = np.tanh(processed * (1 + saturation_amount)) / (1 + saturation_amount)
        
        # 5. Add digital "warmth"
        harmonic_amount = 0.01 + (strength * 0.01)
        processed += harmonic_amount * np.sign(processed) * (processed ** 2)
        
        # 6. High-frequency rolloff for smoothness
        if len(processed) > 10:
            alpha = 0.8 + (strength * 0.1)  # 0.8-0.9
            filtered = np.zeros_like(processed)
            filtered[0] = processed[0]
            for i in range(1, len(processed)):
                filtered[i] = alpha * filtered[i-1] + (1 - alpha) * processed[i]
            processed = filtered
        
        return processed
    
    def _add_pda_start_beep(self, audio_data, sample_rate):
        """Add PDA start beep to the audio (using real STALKER beep if available)"""
        try:
            start_beep = self._get_pda_start_beep(sample_rate)
            if start_beep is None:
                print("[RADIO FX] No PDA beep available, using original audio")
                return audio_data
            
            # Add small gap
            gap_samples = int(0.05 * sample_rate)  # 50ms gap
            
            # Create final audio with beep
            total_samples = len(start_beep) + gap_samples + len(audio_data)
            final_audio = np.zeros(total_samples)
            
            pos = 0
            # Start beep
            final_audio[pos:pos + len(start_beep)] = start_beep
            pos += len(start_beep) + gap_samples
            
            # Main audio
            final_audio[pos:pos + len(audio_data)] = audio_data
            
            return final_audio
        except Exception as e:
            print(f"[RADIO FX] Failed to add PDA beep: {e}")
            return audio_data
    
    def _get_pda_start_beep(self, target_sample_rate):
        """Get PDA start beep (real STALKER beep or generated fallback)"""
        if self.pda_beep_file:
            return self._load_real_pda_beep(target_sample_rate)
        else:
            return self._generate_fallback_beep(target_sample_rate)
    
    def _load_real_pda_beep(self, target_sample_rate):
        """Load and convert the real STALKER PDA beep MP3"""
        try:
            # Convert MP3 to WAV with target sample rate
            temp_wav = self.temp_dir / "pda_beep_converted.wav"
            
            result = subprocess.run([
                'ffmpeg', '-i', str(self.pda_beep_file),
                '-ar', str(target_sample_rate),
                '-ac', '1',  # Mono
                '-y', str(temp_wav)
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                print(f"[RADIO FX] FFmpeg conversion failed: {result.stderr}")
                return None
            
            # Load converted audio
            beep_data, _ = sf.read(temp_wav)
            
            # Ensure mono
            if len(beep_data.shape) > 1:
                beep_data = np.mean(beep_data, axis=1)
            
            # Adjust volume to be reasonable
            beep_data = beep_data * 0.4  # Make it quieter than the main audio
            
            print(f"[RADIO FX] Loaded real STALKER PDA beep: {len(beep_data)} samples")
            
            # Clean up temp file
            temp_wav.unlink(missing_ok=True)
            
            return beep_data.astype(np.float32)
            
        except Exception as e:
            print(f"[RADIO FX] Failed to load real PDA beep: {e}")
            return None
    
    def _generate_fallback_beep(self, sample_rate):
        """Generate fallback beep if real PDA beep not available"""
        try:
            # PDA message start - rising beep (same as before)
            duration = 0.18
            samples = int(duration * sample_rate)
            t = np.linspace(0, duration, samples)
            
            freq_start = 750
            freq_end = 1150
            frequency = freq_start + (freq_end - freq_start) * np.power(t / duration, 0.7)
            
            beep = 0.35 * np.sin(2 * np.pi * frequency * t)
            
            # Smooth envelope
            attack_time = 0.03
            decay_time = 0.08
            attack_samples = int(attack_time * sample_rate)
            decay_samples = int(decay_time * sample_rate)
            
            envelope = np.ones_like(t)
            envelope[:attack_samples] = np.power(t[:attack_samples] / attack_time, 2)
            envelope[-decay_samples:] = np.power((duration - t[-decay_samples:]) / decay_time, 1.5)
            
            beep *= envelope
            
            print("[RADIO FX] Generated fallback PDA beep")
            return beep.astype(np.float32)
            
        except Exception as e:
            print(f"[RADIO FX] Failed to generate fallback beep: {e}")
            return None
    
    def _normalize_audio(self, audio_data, target_peak=0.8):
        """Normalize audio to target peak level"""
        peak = np.max(np.abs(audio_data))
        if peak > 0:
            return audio_data * (target_peak / peak)
        return audio_data
    
    def add_transmission_effects(self, input_file: Path, faction: str = "") -> Optional[Path]:
        """Legacy method for compatibility - just applies radio effects"""
        return self.apply_radio_effects(input_file)