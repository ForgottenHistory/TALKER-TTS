# tts_config.py - Configuration management for Chatterbox TTS
from pathlib import Path
from typing import Dict, Any
from config_loader import ConfigLoader
from voice_resolver import VoiceResolver
from config_templates import ConfigTemplateGenerator
from character_config_generator import CharacterConfigGenerator

class TTSConfig:
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.loader = ConfigLoader(config_dir)
        self.template_generator = ConfigTemplateGenerator(config_dir)
        self.char_generator = CharacterConfigGenerator(config_dir)
        
        # Load initial configurations
        self.default_config = {}
        self.faction_configs = {}
        self.character_configs = {}
        
        # Initialize resolver (will be updated after loading configs)
        self.resolver = VoiceResolver({}, {}, {})
        
        self.load_configs()
    
    def load_configs(self):
        """Load all configuration files"""
        print(f"[TTS CONFIG] Loading configurations from {self.config_dir}")
        
        # Load configurations using the loader
        self.default_config = self.loader.load_default_config()
        self.faction_configs = self.loader.load_faction_configs()
        self.character_configs = self.loader.load_character_configs()
        
        # Update resolver with loaded configs
        self.resolver.update_configs(
            self.default_config, 
            self.faction_configs, 
            self.character_configs
        )
        
        print(f"[TTS CONFIG] Loaded {len(self.faction_configs)} faction configs, {len(self.character_configs)} character configs")
    
    def get_voice_config(self, character_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get voice configuration for a character (auto-generate config if needed)"""
        # Ensure character has a config (auto-generate if needed)
        character_key = self.char_generator.ensure_character_config(character_info)
        print(f"[TTS CONFIG] Using character config key: {character_key}")
        
        # Reload character configs if we just created a new one
        new_character_configs = self.loader.load_character_configs()
        if len(new_character_configs) > len(self.character_configs):
            self.character_configs = new_character_configs
            self.resolver.update_configs(
                self.default_config, 
                self.faction_configs, 
                self.character_configs
            )
            print(f"[TTS CONFIG] Reloaded character configs: {len(self.character_configs)} total")
        
        # Use existing resolver (it will now find the auto-generated config)
        config = self.resolver.resolve_voice_config(character_info)
        
        # Validate and sanitize the final configuration for Chatterbox
        validated_config = self.loader.validate_voice_config(config)
        
        return validated_config
    
    def reload_configs(self):
        """Reload all configuration files"""
        print("[TTS CONFIG] Reloading all configuration files...")
        self.load_configs()
    
    def create_default_configs(self):
        """Create default configuration files if they don't exist"""
        print("[TTS CONFIG] Creating default configuration files...")
        self.template_generator.create_all_default_configs()
    
    def get_status(self) -> Dict[str, Any]:
        """Get configuration system status"""
        status = self.resolver.get_status()
        status['character_generator_active'] = True
        status['tts_provider'] = 'chatterbox'
        return status