#!/usr/bin/env python3
# test_chatterbox_tts.py - Simplified test script for Chatterbox TTS system

import sys
import time
from pathlib import Path
from chatterbox_generator import ChatterboxGenerator
from radio_effects_processor import RadioEffectsProcessor

def test_voice_setup():
    """Test voice directory setup"""
    print("=== Testing Voice Directory Setup ===")
    
    voices_dir = Path("./voices")
    cache_dir = Path("./cache")
    temp_dir = Path("./temp")
    
    generator = ChatterboxGenerator(cache_dir, temp_dir, voices_dir)
    generator.setup_voice_structure()
    
    # Check structure
    expected_dirs = [
        voices_dir,
        voices_dir / "factions",
        voices_dir / "factions" / "army",
        voices_dir / "factions" / "bandit",
        voices_dir / "factions" / "duty",
    ]
    
    for dir_path in expected_dirs:
        if dir_path.exists():
            print(f"✅ {dir_path}")
        else:
            print(f"❌ {dir_path}")
    
    # Check for voice files
    available_voices = generator.get_available_voices()
    print(f"\n📊 Voice Status:")
    print(f"   Default voice: {'✅' if available_voices['default'] else '❌'}")
    print(f"   Faction voices: {len(available_voices['factions'])} factions")
    print(f"   Total voice files: {available_voices['total_files']}")
    
    if available_voices['total_files'] == 0:
        print("\n⚠️  No voice files found!")
        print("   Add voice files to test TTS generation:")
        print("   - voices/default.wav (fallback voice)")
        print("   - voices/factions/army/army_voice_1.wav")
        print("   - voices/factions/bandit/bandit_voice_1.wav")
        print("   etc.")
    
    return available_voices

def test_chatterbox_initialization():
    """Test Chatterbox TTS initialization"""
    print("\n=== Testing Chatterbox Initialization ===")
    
    try:
        generator = ChatterboxGenerator(Path("./cache"), Path("./temp"))
        
        if generator.model:
            print("✅ Chatterbox TTS initialized successfully")
            print(f"   Sample rate: {generator.sample_rate}Hz")
            return generator
        else:
            print("❌ Chatterbox TTS initialization failed")
            print("   Make sure chatterbox-tts is installed: pip install chatterbox-tts")
            return None
    except Exception as e:
        print(f"❌ Error initializing Chatterbox: {e}")
        return None

def test_radio_effects():
    """Test radio effects processor"""
    print("\n=== Testing Radio Effects Processor ===")
    
    try:
        temp_dir = Path("./temp")
        processor = RadioEffectsProcessor(temp_dir)
        print("✅ Radio effects processor initialized")
        
        # Test beep generation
        test_beep = processor._generate_pda_beep("activation", 24000)
        if len(test_beep) > 0:
            print("✅ PDA beep generation working")
        else:
            print("❌ PDA beep generation failed")
        
        return processor
    except Exception as e:
        print(f"❌ Error initializing radio effects: {e}")
        return None

def test_tts_generation(generator, processor):
    """Test full TTS generation with hardcoded radio effects"""
    print("\n=== Testing TTS Generation ===")
    
    if not generator or not generator.model:
        print("❌ Cannot test TTS - Chatterbox not available")
        return False
    
    test_cases = [
        {
            'text': "Anomaly detected in sector C-12, all units maintain safe distance.",
            'character_info': {
                'name': 'Sergeant Petrov',
                'faction': 'army',
                'personality': 'gruff'  # Saved but not used for voice effects
            }
        },
        {
            'text': "This is a test of the emergency broadcast system.",
            'character_info': {
                'name': 'Unknown',
                'faction': 'bandit',
                'personality': 'rude'  # Saved but not used for voice effects
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n🎯 Test Case {i+1}: {test_case['character_info']['faction']} character")
        print(f"   Text: '{test_case['text'][:50]}...'")
        
        try:
            start_time = time.time()
            
            # Generate TTS (voice config is minimal now)
            voice_config = {'tts_provider': 'chatterbox'}
            tts_file = generator.generate_tts(
                test_case['text'], 
                voice_config, 
                test_case['character_info'],
                target_volume=0.8
            )
            
            if not tts_file:
                print("❌ TTS generation failed")
                continue
            
            print(f"✅ TTS generated: {tts_file.name}")
            
            # Apply hardcoded radio effects (no configuration needed)
            processed_file = processor.apply_radio_effects(tts_file, effect_strength=0.8)
            
            if processed_file:
                print(f"✅ Radio effects applied: {processed_file.name}")
                
                generation_time = time.time() - start_time
                file_size = processed_file.stat().st_size / 1024  # KB
                
                print(f"   📊 Generation time: {generation_time:.2f}s")
                print(f"   📊 File size: {file_size:.1f} KB")
                print(f"   📁 Output: {processed_file}")
            else:
                print("❌ Radio effects failed")
            
        except Exception as e:
            print(f"❌ Test case failed: {e}")
            import traceback
            traceback.print_exc()
    
    return True

def main():
    print("🎮 STALKER Simplified Chatterbox TTS Test Suite")
    print("=" * 60)
    print("Features:")
    print("- Voice cloning from WAV files (no config complexity)")
    print("- Hardcoded radio effects (consistent for all)")
    print("- Minimal config files (personalities saved for future)")
    print("=" * 60)
    
    # Test 1: Voice setup
    available_voices = test_voice_setup()
    
    # Test 2: Chatterbox initialization
    generator = test_chatterbox_initialization()
    
    # Test 3: Radio effects
    processor = test_radio_effects()
    
    # Test 4: Full TTS generation (only if voices available)
    if generator and processor:
        if available_voices['total_files'] > 0:
            test_tts_generation(generator, processor)
        else:
            print("\n⚠️  Skipping TTS generation test - no voice files found")
            print("   Add voice files and run again to test full pipeline")
    
    print("\n" + "=" * 60)
    print("🏁 Test Suite Complete")
    
    # Summary
    print("\n📋 Summary:")
    print(f"   Voice setup: {'✅' if Path('./voices').exists() else '❌'}")
    print(f"   Chatterbox TTS: {'✅' if generator and generator.model else '❌'}")
    print(f"   Radio effects: {'✅' if processor else '❌'} (hardcoded for all)")
    print(f"   Voice files: {available_voices['total_files']} found")
    print(f"   Config complexity: ✅ Simplified (no voice effects/style prompts)")
    
    if not generator or not generator.model:
        print("\n📦 To install Chatterbox TTS:")
        print("   pip install chatterbox-tts")
    
    if available_voices['total_files'] == 0:
        print("\n📁 To add voice files:")
        print("   1. Add voices/default.wav (fallback)")
        print("   2. Add faction voices in voices/factions/FACTION_NAME/")
        print("   3. Use 10-30 second WAV files with clear speech")
        print("   4. Radio effects are applied automatically to all voices")

if __name__ == "__main__":
    main()