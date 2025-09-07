#!/usr/bin/env python3
# remote_tts_server.py - TTS server with queue management and voice system
from flask import Flask, request, jsonify, send_file
import time
import tempfile
import os
import threading
import uuid
from pathlib import Path
from queue import Queue, Empty
import torch
import traceback

import json
import random
import hashlib
from typing import Dict, Any, Optional

app = Flask(__name__)

# Global TTS model and voice management
tts_model = None
sample_rate = 24000
voice_manager = None

# Queue management
tts_queue = Queue()
is_processing = False
queue_thread = None
stop_requested = False

class TTSRequest:
    def __init__(self, request_id: str, text: str, character_info: dict = None, 
                 target_volume: float = 1.0):
        self.request_id = request_id
        self.text = text
        self.character_info = character_info
        self.target_volume = target_volume
        self.result_file = None
        self.error = None
        self.completed = threading.Event()

# Copied from voice_file_manager.py
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

def initialize_chatterbox():
    """Initialize Chatterbox TTS model and voice management"""
    global tts_model, sample_rate, voice_manager
    
    try:
        print("[REMOTE SERVER] Initializing Chatterbox TTS...")
        from chatterbox.tts import ChatterboxTTS
        
        # Check GPU availability
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[REMOTE SERVER] Using device: {device}")
        
        if device == "cuda":
            print(f"[REMOTE SERVER] GPU: {torch.cuda.get_device_name()}")
            # CUDA optimizations
            torch.backends.cudnn.benchmark = True
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
        
        # Initialize model
        tts_model = ChatterboxTTS.from_pretrained(device=device)
        sample_rate = tts_model.sr
        
        # Initialize voice management system
        voices_dir = Path("./voices")
        cache_dir = Path("./cache")
        voices_dir.mkdir(exist_ok=True)
        cache_dir.mkdir(exist_ok=True)
        
        voice_manager = VoiceFileManager(voices_dir, cache_dir)
        print(f"[REMOTE SERVER] Voice manager initialized with {len(voice_manager.character_voices)} cached voices")
        
        # Show available voices
        available_voices = voice_manager.get_available_voices()
        print(f"[REMOTE SERVER] Available voices: {available_voices['total_files']} files")
        for faction, voices in available_voices['factions'].items():
            print(f"[REMOTE SERVER]   {faction}: {len(voices)} voice files")
        
        print(f"[REMOTE SERVER] Chatterbox initialized (sample rate: {sample_rate}Hz)")
        return True
        
    except Exception as e:
        print(f"[REMOTE SERVER] Failed to initialize Chatterbox: {e}")
        traceback.print_exc()
        return False

def process_tts_queue():
    """Process TTS requests one by one in queue"""
    global is_processing, stop_requested
    
    print("[REMOTE SERVER] TTS queue processor started")
    
    while not stop_requested:
        try:
            # Wait for next request (blocks until available)
            try:
                tts_request = tts_queue.get(timeout=1.0)
            except Empty:
                continue  # Timeout is normal - just continue the loop
            except Exception as e:
                print(f"[REMOTE SERVER] Queue get error: {e}")
                continue
            
            if tts_request is None:  # Shutdown signal
                print("[REMOTE SERVER] Queue processor received shutdown signal")
                break
            
            print(f"[REMOTE SERVER] Processing queued request: {tts_request.request_id}")
            print(f"[REMOTE SERVER]   Text: '{tts_request.text[:50]}...' (length: {len(tts_request.text)})")
            print(f"[REMOTE SERVER]   Character: {tts_request.character_info}")
            
            is_processing = True
            
            try:
                # Get voice file for character using voice manager
                reference_voice = None
                if voice_manager and tts_request.character_info:
                    reference_voice = voice_manager.get_voice_file_for_character(tts_request.character_info)
                    if reference_voice:
                        print(f"[REMOTE SERVER]   Using voice: {Path(reference_voice).name}")
                    else:
                        print(f"[REMOTE SERVER]   No voice file found for character")
                
                # Generate TTS
                result_file = generate_tts_audio(
                    tts_request.text,
                    reference_voice,
                    tts_request.target_volume
                )
                
                tts_request.result_file = result_file
                
                if result_file:
                    print(f"[REMOTE SERVER] Completed request: {tts_request.request_id}")
                else:
                    tts_request.error = "TTS generation failed"
                    print(f"[REMOTE SERVER] Failed request: {tts_request.request_id}")
                    
            except Exception as e:
                tts_request.error = str(e)
                print(f"[REMOTE SERVER] Error processing request {tts_request.request_id}: {e}")
                traceback.print_exc()
            
            # Signal completion
            tts_request.completed.set()
            is_processing = False
            tts_queue.task_done()
            
        except Exception as e:
            print(f"[REMOTE SERVER] Queue processor unexpected error: {e}")
            traceback.print_exc()
            is_processing = False
            time.sleep(1.0)  # Pause on unexpected errors
    
    print("[REMOTE SERVER] TTS queue processor stopped")

def generate_tts_audio(text: str, reference_voice: str = None, target_volume: float = 1.0):
    """Generate TTS audio and return file path"""
    global tts_model
    
    if not tts_model:
        raise Exception("TTS model not initialized")
    
    start_time = time.time()
    
    print(f"[REMOTE SERVER] Generating TTS for: '{text[:50]}...' (length: {len(text)})")
    
    # Generate audio
    if reference_voice and os.path.exists(reference_voice):
        print(f"[REMOTE SERVER] Using voice reference: {Path(reference_voice).name}")
        wav = tts_model.generate(
            text,
            audio_prompt_path=reference_voice,
            exaggeration=0.2,
            cfg_weight=0.8
        )
    else:
        print("[REMOTE SERVER] Using default voice (no reference)")
        wav = tts_model.generate(
            text,
            exaggeration=0.2,
            cfg_weight=0.8
        )
    
    generation_time = time.time() - start_time
    
    # Get audio info
    if hasattr(wav, 'shape'):
        audio_length = wav.shape[0] if len(wav.shape) == 1 else wav.shape[-1]
    else:
        audio_length = len(wav)
    
    audio_duration = audio_length / sample_rate
    rtf = audio_duration / generation_time if generation_time > 0 else 0
    
    print(f"[REMOTE SERVER] Generated audio: {audio_duration:.2f}s, RTF: {rtf:.2f}x")
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
        temp_path = tmp_file.name
    
    # Save audio using torchaudio
    import torchaudio as ta
    ta.save(temp_path, wav, sample_rate)
    
    print(f"[REMOTE SERVER] Saved audio to: {temp_path}")
    return temp_path

def start_queue_processor():
    """Start the TTS queue processing thread"""
    global queue_thread
    queue_thread = threading.Thread(target=process_tts_queue, daemon=True)
    queue_thread.start()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'online',
        'tts_available': tts_model is not None,
        'device': 'cuda' if torch.cuda.is_available() else 'cpu',
        'gpu_name': torch.cuda.get_device_name() if torch.cuda.is_available() else None,
        'queue_size': tts_queue.qsize(),
        'is_processing': is_processing,
        'voice_manager_available': voice_manager is not None,
        'cached_character_voices': len(voice_manager.character_voices) if voice_manager else 0
    })

@app.route('/generate_tts', methods=['POST'])
def generate_tts():
    """Generate TTS audio and return WAV file (with queueing and voice management)"""
    if not tts_model:
        return jsonify({'error': 'TTS model not initialized'}), 500
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        text = data.get('text', '')
        character_info = data.get('character_info', {})
        target_volume = data.get('target_volume', 1.0)
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Create TTS request
        request_id = str(uuid.uuid4())[:8]
        tts_request = TTSRequest(
            request_id=request_id,
            text=text,
            character_info=character_info,
            target_volume=target_volume
        )
        
        print(f"[REMOTE SERVER] Queuing TTS request: {request_id} (Queue size: {tts_queue.qsize()})")
        
        # Add to queue
        tts_queue.put(tts_request)
        
        # Calculate reasonable timeout based on text length
        # Estimate: 1 second per 10 characters + 30 second base timeout
        estimated_duration = len(text) / 10.0  # chars per second estimate
        timeout_duration = max(60, estimated_duration + 30)  # minimum 60s, longer for long text
        
        print(f"[REMOTE SERVER] Using timeout: {timeout_duration:.1f}s for {len(text)} characters")
        
        # Wait for completion (this blocks until the request is processed)
        completed = tts_request.completed.wait(timeout=timeout_duration)
        
        if not completed:
            return jsonify({'error': f'TTS generation timeout after {timeout_duration:.1f}s'}), 500
        
        if tts_request.error:
            return jsonify({'error': tts_request.error}), 500
        
        if not tts_request.result_file:
            return jsonify({'error': 'TTS generation failed - no result file'}), 500
        
        # Return the file
        return send_file(
            tts_request.result_file,
            as_attachment=True,
            download_name='generated_audio.wav',
            mimetype='audio/wav'
        )
        
    except Exception as e:
        print(f"[REMOTE SERVER] Error in generate_tts: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/voices', methods=['GET'])
def get_voices():
    """Get available voice files"""
    if not voice_manager:
        return jsonify({'error': 'Voice manager not available'}), 500
    
    voices = voice_manager.get_available_voices()
    return jsonify({
        'provider': 'chatterbox',
        'voices': voices,
        'character_assignments': voice_manager.character_voices
    })

@app.route('/queue/status', methods=['GET'])
def queue_status():
    """Get queue status"""
    return jsonify({
        'queue_size': tts_queue.qsize(),
        'is_processing': is_processing,
        'total_processed': 'N/A'  # Could track this if needed
    })

@app.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint with sample generation"""
    test_text = "This is a test message from the remote TTS server."
    test_character = {
        'name': 'Test Character',
        'faction': 'stalker',
        'personality': 'neutral'
    }
    
    try:
        # Create test request
        request_id = str(uuid.uuid4())[:8]
        tts_request = TTSRequest(
            request_id=f"test_{request_id}",
            text=test_text,
            character_info=test_character,
            target_volume=0.8
        )
        
        # Add to queue and wait
        tts_queue.put(tts_request)
        tts_request.completed.wait(timeout=60)
        
        if tts_request.error:
            return jsonify({
                'status': 'test_failed',
                'error': tts_request.error
            }), 500
        
        return jsonify({
            'status': 'test_successful',
            'message': 'TTS generation test completed',
            'model_available': tts_model is not None,
            'voice_manager_available': voice_manager is not None,
            'queue_size': tts_queue.qsize(),
            'test_character': test_character
        })
        
    except Exception as e:
        return jsonify({
            'status': 'test_failed',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("=" * 60)
    print("STALKER Remote TTS Server with Queue Management (Vast.AI)")
    print("=" * 60)
    
    # Initialize TTS model and voice system
    if initialize_chatterbox():
        print("[REMOTE SERVER] ✅ Ready to serve TTS requests")
    else:
        print("[REMOTE SERVER] ❌ TTS initialization failed")
    
    # Start queue processor
    start_queue_processor()
    print("[REMOTE SERVER] ✅ Queue processor started")
    
    # Start server
    print("[REMOTE SERVER] Starting server on 127.0.0.1:5050...")
    try:
        app.run(host='127.0.0.1', port=5050, debug=False, threaded=True)
    finally:
        # Clean shutdown
        stop_requested = True
        if queue_thread:
            tts_queue.put(None)  # Shutdown signal
            queue_thread.join(timeout=2)