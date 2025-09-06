# config_loader.py - Simplified configuration loading for Chatterbox TTS
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

class ConfigLoader:
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
    
    def load_default_config(self) -> Dict[str, Any]:
        """Load default voice configuration"""
        default_file = self.config_dir / "default_voices.yaml"
        if default_file.exists():
            try:
                with open(default_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                    print(f"[CONFIG LOADER] Loaded default config: {len(config)} keys")
                    return config
            except Exception as e:
                print(f"[CONFIG LOADER] Error loading default config: {e}")
        
        return self._get_default_chatterbox_config()
    
    def load_faction_configs(self) -> Dict[str, Dict[str, Any]]:
        """Load all faction-specific configurations"""
        faction_configs = {}
        factions_dir = self.config_dir / "factions"
        
        if not factions_dir.exists():
            print(f"[CONFIG LOADER] Factions directory not found: {factions_dir}")
            return faction_configs
        
        for config_file in factions_dir.glob("*.yaml"):
            faction_name = config_file.stem.lower()
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                    faction_configs[faction_name] = config
                    print(f"[CONFIG LOADER] Loaded faction config: {faction_name}")
            except Exception as e:
                print(f"[CONFIG LOADER] Error loading faction config {faction_name}: {e}")
        
        return faction_configs
    
    def load_character_configs(self) -> Dict[str, Dict[str, Any]]:
        """Load all character-specific configurations"""
        character_configs = {}
        characters_dir = self.config_dir / "characters"
        
        if not characters_dir.exists():
            print(f"[CONFIG LOADER] Characters directory not found: {characters_dir}")
            return character_configs
        
        for config_file in characters_dir.glob("*.yaml"):
            character_name = config_file.stem.lower()
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                    character_configs[character_name] = config
                    print(f"[CONFIG LOADER] Loaded character config: {character_name}")
            except Exception as e:
                print(f"[CONFIG LOADER] Error loading character config {character_name}: {e}")
        
        return character_configs
    
    def _get_default_chatterbox_config(self) -> Dict[str, Any]:
        """Get default Chatterbox configuration template"""
        print("[CONFIG LOADER] Using built-in default Chatterbox config")
        return {
            'tts_provider': 'chatterbox'
        }
    
    def validate_voice_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize Chatterbox voice configuration"""
        validated = config.copy()
        
        # Ensure required fields exist with defaults
        validated.setdefault('tts_provider', 'chatterbox')
        
        # Remove obsolete fields that might exist in old configs
        obsolete_fields = [
            'kokoro_voice', 'kokoro_speed',  # Old Kokoro fields
            'voice_effects', 'style_prompt',  # No longer used
            'stability', 'similarity_boost', 'style', 'use_speaker_boost', 'model_id', 'voice_id'  # Old ElevenLabs fields
        ]
        
        for field in obsolete_fields:
            if field in validated:
                del validated[field]
                print(f"[CONFIG LOADER] Removed obsolete field: {field}")
        
        return validated