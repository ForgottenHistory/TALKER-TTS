# character_config_generator.py - Simplified character config generation for Chatterbox TTS
import yaml
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional

class CharacterConfigGenerator:
    """Auto-generates minimal character-specific config files for Chatterbox TTS"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.characters_dir = config_dir / "characters"
        self.characters_dir.mkdir(exist_ok=True)
    
    def ensure_character_config(self, character_info: Dict[str, Any]) -> str:
        """Ensure character has a config file, create if needed. Returns character config key."""
        character_key = self._create_character_key(character_info)
        config_file = self.characters_dir / f"{character_key}.yaml"
        
        # If config already exists, just return the key
        if config_file.exists():
            print(f"[CHAR CONFIG GEN] Using existing config: {character_key}")
            return character_key
        
        # Create new character config
        print(f"[CHAR CONFIG GEN] Creating new character config: {character_key}")
        config = self._generate_character_config(character_info)
        print(f"[CHAR CONFIG GEN] Generated config: {config}")
        self._save_character_config(config_file, config, character_info)
        
        return character_key
    
    def _create_character_key(self, character_info: Dict[str, Any]) -> str:
        """Create character key (same logic as existing system expects)"""
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
    
    def _generate_character_config(self, character_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate minimal character config for Chatterbox TTS"""
        faction = character_info.get('faction', '').lower()
        personality = character_info.get('personality', '').lower()
        name = character_info.get('name', 'Unknown')
        
        # Minimal config - just store basic info for future use
        config = {
            'tts_provider': 'chatterbox',
            'faction': faction,
            'name': name,
        }
        
        # Save personality for future use (but don't use it for voice effects)
        if personality:
            config['personality'] = personality
        
        # Note: Voice files are automatically selected from ./voices/factions/FACTION/ by the ChatterboxGenerator
        # Note: Radio effects are hardcoded in RadioEffectsProcessor
        
        return config
    
    def _save_character_config(self, config_file: Path, config: Dict[str, Any], character_info: Dict[str, Any]):
        """Save character config with helpful header"""
        name = character_info.get('name', 'Unknown')
        faction = character_info.get('faction', 'unknown')
        personality = character_info.get('personality', 'none')
        
        header = f"""# Auto-generated character config for {name}
# Faction: {faction}
# Personality: {personality}
# 
# This file was automatically created for character tracking.
# Voice files are automatically selected from ./voices/factions/{faction}/
# Radio effects are hardcoded for all characters.
#
# The personality field is saved for potential future use.

"""
    
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(header)
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, width=100)
            
            print(f"[CHAR CONFIG GEN] Saved character config: {config_file.name}")
            
        except Exception as e:
            print(f"[CHAR CONFIG GEN] Error saving config {config_file}: {e}")