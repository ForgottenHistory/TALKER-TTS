# config_templates.py - Simplified configuration templates for Chatterbox TTS
import yaml
from pathlib import Path
from typing import Dict, Any

class ConfigTemplateGenerator:
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
    
    def create_all_default_configs(self):
        """Create all default configuration files if they don't exist"""
        self.create_default_voices_config()
        self.create_faction_configs()
        self.create_example_character_configs()
    
    def create_default_voices_config(self):
        """Create minimal default voices configuration file"""
        default_file = self.config_dir / "default_voices.yaml"
        if default_file.exists():
            return
        
        default_config = {
            'tts_provider': 'chatterbox'
        }
        
        header_comment = """# Default Voice Configuration for Chatterbox TTS
# This is used as fallback when no faction/character specific config is found
#
# Chatterbox TTS uses voice cloning from WAV files in the ./voices directory:
# - ./voices/default.wav (fallback voice)
# - ./voices/factions/FACTION_NAME/*.wav (faction-specific voices)
#
# Characters are randomly assigned voices from their faction for consistency.
# Radio effects are hardcoded for all characters.

"""
        
        with open(default_file, 'w', encoding='utf-8') as f:
            f.write(header_comment)
            yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
        
        print(f"[CONFIG TEMPLATES] Created {default_file}")
    
    def create_faction_configs(self):
        """Create minimal faction configuration files"""
        factions_dir = self.config_dir / "factions"
        factions_dir.mkdir(exist_ok=True)
        
        faction_templates = self._get_faction_templates()
        
        for faction_name, config in faction_templates.items():
            faction_file = factions_dir / f"{faction_name}.yaml"
            if not faction_file.exists():
                header_comment = self._get_faction_header_comment(faction_name)
                
                with open(faction_file, 'w', encoding='utf-8') as f:
                    f.write(header_comment)
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True, width=100)
                
                print(f"[CONFIG TEMPLATES] Created {faction_file}")
    
    def create_example_character_configs(self):
        """Create minimal example character configurations"""
        characters_dir = self.config_dir / "characters"
        characters_dir.mkdir(exist_ok=True)
        
        example_chars = {
            'army_sergeant_garkovenko': {
                'tts_provider': 'chatterbox',
                'faction': 'army',
                'name': 'Sergeant Garkovenko',
                'personality': 'gruff'  # Saved for future use
            }
        }
        
        for char_name, config in example_chars.items():
            char_file = characters_dir / f"{char_name}.yaml"
            if not char_file.exists():
                header_comment = self._get_character_header_comment(char_name)
                
                with open(char_file, 'w', encoding='utf-8') as f:
                    f.write(header_comment)
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                
                print(f"[CONFIG TEMPLATES] Created {char_file}")
    
    def _get_faction_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get minimal faction configuration templates"""
        factions = ['army', 'bandit', 'duty', 'freedom', 'stalker', 'loner', 'monolith', 'ecologist', 'mercenary']
        
        templates = {}
        for faction in factions:
            templates[faction] = {
                'tts_provider': 'chatterbox',
                'faction': faction
            }
        
        return templates
    
    def _get_faction_header_comment(self, faction_name: str) -> str:
        """Get header comment for faction config files"""
        return f"""# {faction_name.upper()} Faction Configuration for Chatterbox TTS
#
# Voice files are stored in: ./voices/factions/{faction_name}/
# Characters from this faction will be randomly assigned one of these voices for consistency.
#
# Radio effects are hardcoded for all factions - no configuration needed.
# Voice character comes from the WAV files, not from config settings.

"""
    
    def _get_character_header_comment(self, char_name: str) -> str:
        """Get header comment for character config files"""
        return f"""# Character configuration for {char_name.replace('_', ' ').title()}
# Using Chatterbox TTS with voice cloning
#
# Voice files are selected from the character's faction directory in ./voices/factions/
# Radio effects are hardcoded - no configuration needed.
# Personality is saved for potential future use.

"""