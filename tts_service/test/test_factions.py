#!/usr/bin/env python3
# test_factions.py - Test faction system and voice assignment

import json
from pathlib import Path
from voice_file_manager import VoiceFileManager
from config_templates import ConfigTemplateGenerator

def test_faction_setup():
    """Test that all factions get proper directory structure"""
    print("=== Testing Faction Directory Setup ===")
    
    config_dir = Path("./config")
    voices_dir = Path("./voices")
    
    # Create config templates
    template_gen = ConfigTemplateGenerator(config_dir)
    template_gen.create_faction_configs()
    
    # Check faction configs were created
    factions_dir = config_dir / "factions"
    faction_files = list(factions_dir.glob("*.yaml"))
    
    expected_factions = ['loner', 'bandit', 'army', 'duty', 'freedom', 'ecolog', 'monolith', 'mercenary', 'clear sky', 'renegade', 'unisg', 'sin']
    
    print(f"Expected factions: {len(expected_factions)}")
    print(f"Created configs: {len(faction_files)}")
    
    for faction in expected_factions:
        config_file = factions_dir / f"{faction}.yaml"
        if config_file.exists():
            print(f"✅ {faction}.yaml")
        else:
            print(f"❌ {faction}.yaml")
    
    return faction_files

def test_voice_assignment():
    """Test voice file assignment and persistence"""
    print("\n=== Testing Voice Assignment System ===")
    
    voices_dir = Path("./voices")
    cache_dir = Path("./cache")
    cache_dir.mkdir(exist_ok=True)
    
    voice_mgr = VoiceFileManager(voices_dir, cache_dir)
    
    # Test characters from different factions
    test_characters = [
        {'name': 'Sidorovich', 'faction': 'loner', 'personality': 'greedy'},
        {'name': 'Beard', 'faction': 'loner', 'personality': 'friendly'},
        {'name': 'Unknown Bandit', 'faction': 'bandit', 'personality': 'hostile'},
        {'name': 'Colonel Skulsky', 'faction': 'army', 'personality': 'military'},
        {'name': 'General Voronin', 'faction': 'duty', 'personality': 'authoritative'},
        {'name': 'Unknown', 'faction': 'freedom', 'personality': 'rebellious'},
        {'name': 'Professor Sakharov', 'faction': 'ecolog', 'personality': 'scientific'},
        {'name': 'Unknown Monolith', 'faction': 'monolith', 'personality': 'fanatical'},
        {'name': 'Dushman', 'faction': 'mercenary', 'personality': 'professional'},
        {'name': 'Lebedev', 'faction': 'clear sky', 'personality': 'determined'},
        {'name': 'Unknown Renegade', 'faction': 'renegade', 'personality': 'chaotic'},
        {'name': 'Unknown UNISG', 'faction': 'unisg', 'personality': 'organized'},
        {'name': 'Unknown SIN', 'faction': 'sin', 'personality': 'mysterious'}
    ]
    
    assignments = {}
    
    for char_info in test_characters:
        voice_file = voice_mgr.get_voice_file_for_character(char_info)
        faction = char_info['faction']
        name = char_info['name']
        
        if voice_file:
            voice_name = Path(voice_file).name
            print(f"✅ {faction:8} | {name:20} → {voice_name}")
            assignments[faction] = assignments.get(faction, []) + [voice_name]
        else:
            print(f"❌ {faction:8} | {name:20} → No voice found")
        
        # Test persistence - same character should get same voice
        voice_file_2 = voice_mgr.get_voice_file_for_character(char_info)
        if voice_file == voice_file_2:
            print(f"   Persistence: ✅")
        else:
            print(f"   Persistence: ❌ ({voice_file} != {voice_file_2})")
    
    # Show voice assignments by faction
    print(f"\n📊 Voice Distribution:")
    for faction, voices in assignments.items():
        unique_voices = set(voices)
        print(f"   {faction}: {len(unique_voices)} unique voices used")
    
    return assignments

def test_character_cache():
    """Test the character voice cache system"""
    print("\n=== Testing Character Cache System ===")
    
    cache_file = Path("./cache/character_voices.json")
    
    if cache_file.exists():
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        print(f"📁 Cache file exists: {len(cache_data)} character mappings")
        
        # Show some examples
        for i, (char_key, voice_file) in enumerate(cache_data.items()):
            if i < 5:  # Show first 5
                voice_name = Path(voice_file).name if Path(voice_file).exists() else "MISSING"
                print(f"   {char_key} → {voice_name}")
            elif i == 5:
                print(f"   ... and {len(cache_data) - 5} more")
                break
        
        return cache_data
    else:
        print("📁 No cache file found (run voice assignment test first)")
        return {}

def show_voice_files_status():
    """Show current voice files status"""
    print("\n=== Voice Files Status ===")
    
    voices_dir = Path("./voices")
    
    # Check default voice
    default_voice = voices_dir / "default.wav"
    print(f"Default voice: {'✅' if default_voice.exists() else '❌'} default.wav")
    
    # Check faction voices
    factions_dir = voices_dir / "factions"
    if factions_dir.exists():
        total_files = 0
        for faction_dir in factions_dir.iterdir():
            if faction_dir.is_dir():
                wav_files = list(faction_dir.glob("*.wav"))
                if wav_files:
                    print(f"✅ {faction_dir.name:8}: {len(wav_files)} voice files")
                    total_files += len(wav_files)
                else:
                    print(f"❌ {faction_dir.name:8}: No voice files")
        
        print(f"\n📊 Total voice files: {total_files}")
        
        if total_files == 0:
            print("\n💡 To add voice files:")
            print("   1. Add voices/default.wav (fallback)")
            print("   2. Add voices/factions/FACTION_NAME/voice_file.wav")
            print("   3. Characters will be randomly assigned voices from their faction")
    else:
        print("❌ No factions directory found")

def main():
    print("🎮 STALKER Faction System Test")
    print("=" * 60)
    
    # Test 1: Faction setup
    faction_files = test_faction_setup()
    
    # Test 2: Voice file status
    show_voice_files_status()
    
    # Test 3: Voice assignment
    assignments = test_voice_assignment()
    
    # Test 4: Cache system
    cache_data = test_character_cache()
    
    print("\n" + "=" * 60)
    print("🏁 Test Complete")
    print(f"📋 Summary:")
    print(f"   Faction configs: {len(faction_files)} created")
    print(f"   Character cache: {len(cache_data)} mappings")
    print(f"   Voice assignments tested for all factions")

if __name__ == "__main__":
    main()