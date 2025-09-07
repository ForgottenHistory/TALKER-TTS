# chatterbox_generator.py - Fixed generator with proper remote TTS queue handling
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, Optional

from voice_file_manager import VoiceFileManager
from tts_engine import TTSEngine

class ChatterboxGenerator:
    def __init__(self, cache_dir: Path, temp_dir: Path, voices_dir: Path = None):
        self.cache_dir = cache_dir
        self.temp_dir = temp_dir
        self.voices_dir = voices_dir or Path("./voices")
        
        # Create directories
        self.cache_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        self.voices_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.voice_manager = VoiceFileManager(self.voices_dir, self.cache_dir)
        self.tts_engine = TTSEngine(self.temp_dir)
        
        print("[CHATTERBOX] Generator initialized with modular components")
    
    @property
    def model(self):
        """Expose model for compatibility"""
        return self.tts_engine.model
    
    @property
    def sample_rate(self):
        """Expose sample rate for compatibility"""
        return self.tts_engine.sample_rate
    
    @property
    def character_voices(self):
        """Expose character voices for compatibility"""
        return self.voice_manager.character_voices
    
    def _get_voice_file_for_character(self, character_info: Dict[str, Any]) -> Optional[str]:
        """Get voice file for character (delegate to voice manager)"""
        return self.voice_manager.get_voice_file_for_character(character_info)
    
    def generate_tts(self, text: str, voice_config: Dict[str, Any], character_info: Dict[str, Any] = None, 
                    target_volume: float = 1.0) -> Optional[Path]:
        """Generate TTS audio - try remote first, then local (all through queue)"""
        
        # Try remote TTS first if enabled
        remote_file = self._try_remote_tts(text, character_info, target_volume)
        if remote_file:
            return remote_file
        
        # Fall back to local generation
        return self._generate_local_tts(text, voice_config, character_info, target_volume)
    
    def _try_remote_tts(self, text: str, character_info: Dict[str, Any] = None, target_volume: float = 1.0) -> Optional[Path]:
        """Try remote TTS generation"""
        try:
            from remote_tts_client import create_remote_client
            remote_client = create_remote_client()
            
            if remote_client:
                print("[CHATTERBOX] Using remote TTS generation...")
                
                # Get voice file for character (for remote reference)
                reference_voice = None
                if character_info:
                    reference_voice = self.voice_manager.get_voice_file_for_character(character_info)
                
                remote_file = remote_client.generate_tts_file(text, character_info, target_volume)
                if remote_file:
                    print(f"[CHATTERBOX] Remote TTS successful: {remote_file}")
                    return remote_file
                else:
                    print("[CHATTERBOX] Remote TTS failed, falling back to local...")
                    
        except Exception as e:
            print(f"[CHATTERBOX] Remote TTS error: {e}, falling back to local...")
        
        return None
    
    def _generate_local_tts(self, text: str, voice_config: Dict[str, Any], character_info: Dict[str, Any] = None, 
                           target_volume: float = 1.0) -> Optional[Path]:
        """Generate TTS locally"""
        if not self.tts_engine.model:
            print("[CHATTERBOX] TTS engine not initialized")
            return None

        print(f"[CHATTERBOX] Generating TTS locally: '{text[:50]}...'")
        
        # Get voice file for character
        reference_voice = None
        if character_info:
            reference_voice = self.voice_manager.get_voice_file_for_character(character_info)
        
        # Create cache key and output file
        cache_key = self._create_cache_key(text, target_volume, reference_voice)
        output_wav = self.temp_dir / f"{cache_key}.wav"
        
        # Check cache first
        if output_wav.exists():
            print("[CHATTERBOX] Using cached audio")
            return output_wav
        
        # Generate audio using TTS engine (now returns file path)
        audio_file = self.tts_engine.generate_audio(text, reference_voice, target_volume)
        if audio_file is None:
            return None
        
        # Move to final cache location
        audio_file.rename(output_wav)
        print(f"[CHATTERBOX] TTS complete: {output_wav.stat().st_size} bytes")
        return output_wav    
    
    def _create_cache_key(self, text: str, target_volume: float = 1.0, reference_voice: str = None) -> str:
        """Create unique cache key with working parameters"""
        cache_data = {
            'text': text,
            'reference_voice': reference_voice or 'default',
            'target_volume': round(target_volume, 2),
            'exaggeration': 0.2,    # Back to working values
            'cfg_weight': 0.8,
        }
        return hashlib.md5(json.dumps(cache_data, sort_keys=True).encode()).hexdigest()
    
    def get_available_voices(self) -> Dict[str, Any]:
        """Get available voice files (delegate to voice manager)"""
        return self.voice_manager.get_available_voices()
    
    def setup_voice_structure(self):
        """Create voice directory structure"""
        print("[CHATTERBOX] Setting up voice directory structure...")
        
        # Create factions directory
        factions_dir = self.voices_dir / "factions"
        factions_dir.mkdir(exist_ok=True)
        
        # Standard STALKER factions
        factions = ['loner', 'bandit', 'army', 'duty', 'freedom', 'ecolog', 'monolith', 'mercenary', 'clear sky', 'renegade', 'unisg', 'sin']
        
        for faction in factions:
            faction_dir = factions_dir / faction
            faction_dir.mkdir(exist_ok=True)
            
            # Create readme
            readme = faction_dir / "README.txt"
            if not readme.exists():
                with open(readme, 'w', encoding='utf-8') as f:
                    f.write(f"# {faction.upper()} Faction Voice Files\n\n")
                    f.write(f"Place .wav voice files here for {faction} faction characters.\n")
                    f.write(f"Each character will be randomly assigned one of these voices for consistency.\n\n")
                    f.write(f"Recommended: 3-5 different voice files per faction\n")
                    f.write(f"Format: WAV files (any sample rate, mono/stereo)\n\n")
                    f.write(f"Example files:\n")
                    f.write(f"- {faction}_voice_1.wav\n")
                    f.write(f"- {faction}_voice_2.wav\n")
                    f.write(f"- {faction}_voice_3.wav\n")
        
        # Create main readme
        main_readme = self.voices_dir / "README.txt"
        if not main_readme.exists():
            with open(main_readme, 'w', encoding='utf-8') as f:
                f.write("# STALKER TTS Voice Files\n\n")
                f.write("This directory contains voice reference files for Chatterbox TTS voice cloning.\n\n")
                f.write("## Structure:\n")
                f.write("voices/\n")
                f.write("|-- default.wav              # Default voice (fallback)\n")
                f.write("|-- factions/\n")
                f.write("    |-- army/               # Army faction voices\n")
                f.write("    |   |-- army_voice_1.wav\n")
                f.write("    |   |-- army_voice_2.wav\n")
                f.write("    |-- bandit/             # Bandit faction voices\n")
                f.write("        |-- bandit_voice_1.wav\n\n")
                f.write("## Speed Optimizations:\n")
                f.write("- Aggressive speed settings (quality vs speed trade-off)\n")
                f.write("- FP16 autocast for faster inference\n")
                f.write("- Reduced CFG weight and exaggeration\n")
                f.write("- Flash attention when available\n")
                f.write("- Target: >1.0x real-time factor (RTF)\n\n")
                f.write("## Voice File Requirements:\n")
                f.write("- Format: WAV files\n")
                f.write("- Length: 10-30 seconds recommended\n")
                f.write("- Content: Clear speech, representative of character type\n")
                f.write("- Quality: Good quality recordings work best\n\n")
                f.write("## Radio Effects:\n")
                f.write("- All voices get the same radio effects automatically\n")
                f.write("- No configuration needed - hardcoded for consistency\n")
        
        print(f"[CHATTERBOX] Voice structure created at {self.voices_dir}")