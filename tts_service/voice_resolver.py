# voice_resolver.py - Simplified voice configuration resolution for Chatterbox TTS
from typing import Dict, Any
import hashlib

class VoiceResolver:
    def __init__(self, default_config: Dict[str, Any], faction_configs: Dict[str, Dict[str, Any]], 
                 character_configs: Dict[str, Dict[str, Any]]):
        self.default_config = default_config
        self.faction_configs = faction_configs
        self.character_configs = character_configs
    
    def resolve_voice_config(self, character_info: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve voice configuration for a character using simplified priority system"""
        name = character_info.get('name', '').lower().strip()
        faction = character_info.get('faction', '').lower().strip()
        personality = character_info.get('personality', '').lower().strip()
        
        print(f"[VOICE RESOLVER] Resolving config for: name='{name}', faction='{faction}', personality='{personality}'")
        
        # Start with default config
        config = self.default_config.copy()
        
        # Apply faction configuration (if exists)
        if faction in self.faction_configs:
            faction_config = self.faction_configs[faction]
            config.update(faction_config)
            print(f"[VOICE RESOLVER] Applied faction config: {faction}")
        
        # Apply character-specific configuration (highest priority)
        character_key = self._create_character_key(character_info)
        
        if character_key in self.character_configs:
            character_config = self.character_configs[character_key]
            config.update(character_config)
            print(f"[VOICE RESOLVER] Applied character-specific config: {character_key}")
        else:
            print(f"[VOICE RESOLVER] No character-specific config found for key: {character_key}")
        
        print(f"[VOICE RESOLVER] Final resolved config: {config}")
        return config
    
    def _create_character_key(self, character_info: Dict[str, Any]) -> str:
        """Create character key using EXACT same logic as CharacterConfigGenerator"""
        name = character_info.get('name', '').lower().strip()
        faction = character_info.get('faction', '').lower().strip()
        personality = character_info.get('personality', '').lower().strip()
        
        # Use name if available and meaningful
        if name and name not in ['', 'unknown', 'unnamed', 'npc']:
            # Clean up the name for filename
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
    
    def update_configs(self, default_config: Dict[str, Any], faction_configs: Dict[str, Dict[str, Any]], 
                      character_configs: Dict[str, Dict[str, Any]]):
        """Update configuration data (for reload functionality)"""
        self.default_config = default_config
        self.faction_configs = faction_configs
        self.character_configs = character_configs
        print("[VOICE RESOLVER] Configuration data updated")
    
    def get_status(self) -> Dict[str, Any]:
        """Get resolver status information"""
        return {
            'factions_loaded': list(self.faction_configs.keys()),
            'characters_loaded': list(self.character_configs.keys()),
            'default_config_loaded': bool(self.default_config),
            'tts_provider': 'chatterbox'
        }