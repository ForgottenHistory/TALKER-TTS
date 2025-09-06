# voice_file_manager.py - Manages voice file selection and character assignments
import json
import random
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional

class VoiceFileManager:
    def __init__(self, voices_dir: Path, cache_dir: Path):
        self.voices_dir = voices_dir
        self.cache_dir = cache_dir
        
        # Character voice mapping for consistency
        self.character_voices = {}
        self.character_voices_file = self.cache_dir / "character_voices.json"
        self._load_character_voices()
    
    def _load_character_voices(self):
        """Load character voice mappings from cache"""
        if self.character_voices_file.exists():
            try:
                with open(self.character_voices_file, 'r') as f:
                    self.character_voices = json.load(f)
                print(f"[VOICE MGR] Loaded voice mappings for {len(self.character_voices)} characters")
            except Exception as e:
                print(f"[VOICE MGR] Failed to load character voices: {e}")
                self.character_voices = {}
    
    def _save_character_voices(self):
        """Save character voice mappings to cache"""
        try:
            with open(self.character_voices_file, 'w') as f:
                json.dump(self.character_voices, f, indent=2)
        except Exception as e:
            print(f"[VOICE MGR] Failed to save character voices: {e}")
    
    def get_voice_file_for_character(self, character_info: Dict[str, Any]) -> Optional[str]:
        """Get or assign voice file for character (ensures consistency)"""
        character_key = self._get_character_key(character_info)
        
        # Check if character already has assigned voice
        if character_key in self.character_voices:
            voice_file = self.character_voices[character_key]
            if Path(voice_file).exists():
                print(f"[VOICE MGR] Using cached voice for {character_key}: {Path(voice_file).name}")
                return voice_file
            else:
                print(f"[VOICE MGR] Cached voice file missing for {character_key}, reassigning...")
                del self.character_voices[character_key]
        
        # Assign new voice file
        voice_file = self._select_voice_file(character_info)
        if voice_file:
            self.character_voices[character_key] = voice_file
            self._save_character_voices()
            print(f"[VOICE MGR] Assigned voice to {character_key}: {Path(voice_file).name}")
        
        return voice_file
    
    def _get_character_key(self, character_info: Dict[str, Any]) -> str:
        """Create unique key for character"""
        name = character_info.get('name', '').lower().strip()
        faction = character_info.get('faction', '').lower().strip()
        personality = character_info.get('personality', '').lower().strip()
        
        if name and name not in ['', 'unknown', 'unnamed', 'npc']:
            clean_name = name.replace(' ', '_').replace('-', '_')
            return f"{faction}_{clean_name}" if faction else clean_name
        else:
            # For unnamed NPCs, create key from faction+personality+hash
            unique_data = f"{faction}_{personality}_{str(sorted(character_info.items()))}"
            hash_suffix = hashlib.md5(unique_data.encode()).hexdigest()[:6]
            
            if personality:
                return f"{faction}_{personality}_{hash_suffix}".replace(' ', '_')
            else:
                return f"{faction}_npc_{hash_suffix}".replace(' ', '_')
    
    def _select_voice_file(self, character_info: Dict[str, Any]) -> Optional[str]:
        """Select appropriate voice file for character"""
        faction = character_info.get('faction', '').lower().strip()
        
        # 1. Try faction-specific voices
        if faction:
            faction_dir = self.voices_dir / "factions" / faction
            if faction_dir.exists():
                wav_files = list(faction_dir.glob("*.wav"))
                if wav_files:
                    selected = random.choice(wav_files)
                    print(f"[VOICE MGR] Selected faction voice: {selected}")
                    return str(selected)
                else:
                    print(f"[VOICE MGR] No wav files found in {faction_dir}")
        
        # 2. Try default voice
        default_voice = self.voices_dir / "default.wav"
        if default_voice.exists():
            print(f"[VOICE MGR] Using default voice: {default_voice}")
            return str(default_voice)
        
        # 3. No voice file found
        print(f"[VOICE MGR] No voice file found for faction '{faction}' or default")
        return None
    
    def get_available_voices(self) -> Dict[str, Any]:
        """Get available voice files"""
        voices = {
            'default': None,
            'factions': {},
            'total_files': 0
        }
        
        # Check default voice
        default_voice = self.voices_dir / "default.wav"
        if default_voice.exists():
            voices['default'] = {
                'path': str(default_voice),
                'size_mb': round(default_voice.stat().st_size / (1024*1024), 2)
            }
            voices['total_files'] += 1
        
        # Check faction voices
        factions_dir = self.voices_dir / "factions"
        if factions_dir.exists():
            for faction_dir in factions_dir.iterdir():
                if faction_dir.is_dir():
                    wav_files = list(faction_dir.glob("*.wav"))
                    if wav_files:
                        voices['factions'][faction_dir.name] = []
                        for wav_file in wav_files:
                            voices['factions'][faction_dir.name].append({
                                'name': wav_file.name,
                                'path': str(wav_file),
                                'size_mb': round(wav_file.stat().st_size / (1024*1024), 2)
                            })
                            voices['total_files'] += 1
        
        return voices