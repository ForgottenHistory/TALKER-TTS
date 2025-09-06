# tts_server.py - Chatterbox TTS Server for STALKER
from flask import Flask, request, jsonify
import os
from pathlib import Path
from tts_config import TTSConfig
from chatterbox_generator import ChatterboxGenerator
from radio_effects_processor import RadioEffectsProcessor
from audio_player import AudioPlayer

app = Flask(__name__)

# Configuration
CONFIG_DIR = Path("./config")
CACHE_DIR = Path("./cache")
TEMP_DIR = Path("./temp")
VOICES_DIR = Path("./voices")

# Create directories
CONFIG_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)
VOICES_DIR.mkdir(exist_ok=True)

print(f"[TTS SERVER] Starting Chatterbox TTS Server...")
print(f"[TTS SERVER] Config dir: {CONFIG_DIR}")
print(f"[TTS SERVER] Cache dir: {CACHE_DIR}")
print(f"[TTS SERVER] Temp dir: {TEMP_DIR}")
print(f"[TTS SERVER] Voices dir: {VOICES_DIR}")

# Initialize components
config_manager = TTSConfig(CONFIG_DIR)
audio_player = AudioPlayer()

# Initialize Chatterbox TTS generator
chatterbox_generator = None
radio_processor = None
try:
    chatterbox_generator = ChatterboxGenerator(CACHE_DIR, TEMP_DIR, VOICES_DIR)
    radio_processor = RadioEffectsProcessor(TEMP_DIR)
    print("[TTS SERVER] Chatterbox TTS generator initialized successfully")
except Exception as e:
    print(f"[TTS SERVER] Failed to initialize Chatterbox: {e}")
    print("[TTS SERVER] Make sure 'chatterbox-tts' package is installed: pip install chatterbox-tts")

@app.route('/tts', methods=['POST'])
def tts_endpoint():
    """Handle TTS requests using Chatterbox"""
    print(f"[TTS SERVER] ========== NEW TTS REQUEST ==========")
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        text = data.get('text', '')
        character_info = data.get('character_info', {})
        
        # Handle volume from multiple sources
        mcm_volume = data.get('mcm_volume')
        request_volume = data.get('volume', 1.0)
        
        if mcm_volume is not None:
            final_volume = max(0.0, min(1.0, mcm_volume / 100.0))
            print(f"[TTS SERVER] Using MCM volume: {mcm_volume}% -> {final_volume:.2f}")
        else:
            final_volume = max(0.0, min(1.0, request_volume))
            print(f"[TTS SERVER] Using request volume: {final_volume:.2f}")
        
        print(f"[TTS SERVER] Text: '{text}'")
        print(f"[TTS SERVER] Character: {character_info}")
        print(f"[TTS SERVER] Final Volume: {final_volume}")
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        if not chatterbox_generator:
            return jsonify({'error': 'Chatterbox TTS not available - check installation'}), 500
        
        # Get voice configuration (for compatibility, though Chatterbox uses voice files)
        voice_config = config_manager.get_voice_config(character_info)
        print(f"[TTS SERVER] Voice config: {voice_config}")
        
        # Generate TTS audio using Chatterbox
        tts_file = chatterbox_generator.generate_tts(text, voice_config, character_info, final_volume)
        
        if not tts_file:
            return jsonify({'error': 'TTS generation failed'}), 500
        
        # Apply radio effects
        processed_file = radio_processor.apply_radio_effects(tts_file, effect_strength=0.8)
        if not processed_file:
            processed_file = tts_file  # Use original if effects fail
        
        # Play audio
        success = audio_player.play_audio(processed_file, 1.0)  # Volume already applied
        if not success:
            return jsonify({'error': 'Audio playback failed'}), 500
        
        return jsonify({
            'status': 'playing',
            'method': 'windows_audio',
            'provider': 'chatterbox',
            'text': text,
            'character_info': character_info,
            'voice_config': voice_config,
            'applied_volume': final_volume,
            'voice_file_used': chatterbox_generator._get_voice_file_for_character(character_info)
        })
            
    except Exception as e:
        print(f"[TTS SERVER] Exception: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/voices', methods=['GET'])
def get_voices():
    """Get available voice files"""
    if not chatterbox_generator:
        return jsonify({'error': 'Chatterbox TTS not available'}), 500
    
    voices = chatterbox_generator.get_available_voices()
    return jsonify({
        'provider': 'chatterbox',
        'voices': voices
    })

@app.route('/voices/setup', methods=['POST'])
def setup_voices():
    """Set up voice directory structure"""
    if not chatterbox_generator:
        return jsonify({'error': 'Chatterbox TTS not available'}), 500
    
    try:
        chatterbox_generator.setup_voice_structure()
        voices = chatterbox_generator.get_available_voices()
        
        return jsonify({
            'status': 'success',
            'message': 'Voice directory structure created',
            'voices': voices
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/characters/status', methods=['GET'])
def characters_status():
    """Get character configuration status"""
    try:
        status = config_manager.get_status()
        
        characters_dir = CONFIG_DIR / "characters"
        character_files = list(characters_dir.glob("*.yaml")) if characters_dir.exists() else []
        
        # Add voice assignment info
        voice_assignments = {}
        if chatterbox_generator:
            voice_assignments = chatterbox_generator.character_voices
        
        return jsonify({
            'character_configs': {
                'total_configs': len(character_files),
                'config_files': [f.stem for f in character_files],
                'characters_dir': str(characters_dir)
            },
            'voice_assignments': {
                'total_assignments': len(voice_assignments),
                'assignments': voice_assignments
            },
            'config_system_status': status
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/audio/status', methods=['GET'])
def audio_status():
    """Get audio playback status"""
    return jsonify({
        'is_playing': audio_player.is_currently_playing(),
        'queue_size': audio_player.get_queue_size(),
        'preferred_method': audio_player.get_preferred_method()
    })

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'running', 
        'audio_method': 'windows_system',
        'tts_provider': 'chatterbox',
        'available': bool(chatterbox_generator and chatterbox_generator.model),
        'voices_available': chatterbox_generator.get_available_voices()['total_files'] if chatterbox_generator else 0
    })

@app.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint"""
    audio_test = audio_player.test_audio()
    
    # Test Chatterbox
    chatterbox_status = {}
    if chatterbox_generator:
        voices = chatterbox_generator.get_available_voices()
        chatterbox_status = {
            'available': bool(chatterbox_generator.model),
            'voices_count': voices['total_files'],
            'factions_with_voices': len(voices['factions']),
            'has_default_voice': bool(voices['default'])
        }
    else:
        chatterbox_status = {
            'available': False,
            'reason': 'Chatterbox not initialized - check installation'
        }
    
    return jsonify({
        'status': 'test_successful',
        'windows_audio_available': audio_test,
        'tts_provider': 'chatterbox',
        'chatterbox_status': chatterbox_status,
        'config_files_loaded': config_manager.get_status()
    })

@app.route('/test/tts', methods=['POST'])
def test_tts():
    """Test TTS generation with sample text"""
    try:
        data = request.get_json() or {}
        text = data.get('text', 'This is a test message from the Zone.')
        faction = data.get('faction', 'stalker')
        
        character_info = {
            'name': 'Test Character',
            'faction': faction,
            'personality': 'neutral'
        }
        
        if not chatterbox_generator:
            return jsonify({'error': 'Chatterbox TTS not available'}), 500
        
        # Generate TTS
        voice_config = config_manager.get_voice_config(character_info)
        tts_file = chatterbox_generator.generate_tts(text, voice_config, character_info, 0.8)
        
        if not tts_file:
            return jsonify({'error': 'TTS generation failed'}), 500
        
        # Apply effects
        processed_file = radio_processor.apply_radio_effects(tts_file, effect_strength=0.8)
        if not processed_file:
            processed_file = tts_file
        
        # Play audio
        success = audio_player.play_audio(processed_file, 1.0)
        
        return jsonify({
            'status': 'success' if success else 'playback_failed',
            'text': text,
            'faction': faction,
            'voice_file_used': chatterbox_generator._get_voice_file_for_character(character_info),
            'file_size_kb': round(processed_file.stat().st_size / 1024, 1)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("STALKER Chatterbox TTS Server")
    print("Features:")
    print("- Chatterbox TTS with voice cloning")
    print("- Faction-based voice file system")  
    print("- Character-specific voice consistency")
    print("- Enhanced telephone-style radio effects")
    print("- Audio queue system")
    print("=" * 60)
    
    # Initialize configuration files if they don't exist
    config_manager.create_default_configs()
    
    # Set up voice structure
    if chatterbox_generator:
        chatterbox_generator.setup_voice_structure()
    
    audio_player.test_audio()
    
    try:
        app.run(host='127.0.0.1', port=8001, debug=True)
    finally:
        # Clean shutdown
        audio_player.shutdown() 