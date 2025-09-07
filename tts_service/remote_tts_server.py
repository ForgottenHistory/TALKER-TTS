#!/usr/bin/env python3
# remote_tts_server.py - TTS server for Vast.AI instance
from flask import Flask, request, jsonify, send_file
import time
import tempfile
import os
from pathlib import Path
import torch
import traceback

app = Flask(__name__)

# Global TTS model
tts_model = None
sample_rate = 24000

def initialize_chatterbox():
    """Initialize Chatterbox TTS model"""
    global tts_model, sample_rate
    
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
        
        print(f"[REMOTE SERVER] Chatterbox initialized (sample rate: {sample_rate}Hz)")
        return True
        
    except Exception as e:
        print(f"[REMOTE SERVER] Failed to initialize Chatterbox: {e}")
        traceback.print_exc()
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'online',
        'tts_available': tts_model is not None,
        'device': 'cuda' if torch.cuda.is_available() else 'cpu',
        'gpu_name': torch.cuda.get_device_name() if torch.cuda.is_available() else None
    })

@app.route('/generate_tts', methods=['POST'])
def generate_tts():
    """Generate TTS audio and return WAV file"""
    global tts_model
    
    if not tts_model:
        return jsonify({'error': 'TTS model not initialized'}), 500
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        text = data.get('text', '')
        reference_voice = data.get('reference_voice')  # Optional voice file path
        target_volume = data.get('target_volume', 1.0)
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        print(f"[REMOTE SERVER] Generating TTS for: '{text[:50]}...'")
        
        start_time = time.time()
        
        # Generate audio
        if reference_voice and os.path.exists(reference_voice):
            print(f"[REMOTE SERVER] Using voice reference: {reference_voice}")
            wav = tts_model.generate(
                text,
                audio_prompt_path=reference_voice,
                exaggeration=0.2,
                cfg_weight=0.8
            )
        else:
            print("[REMOTE SERVER] Using default voice")
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
        
        # Return the file
        return send_file(
            temp_path,
            as_attachment=True,
            download_name='generated_audio.wav',
            mimetype='audio/wav'
        )
        
    except Exception as e:
        print(f"[REMOTE SERVER] Error generating TTS: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint with sample generation"""
    test_text = "This is a test message from the remote TTS server."
    
    try:
        response = generate_tts()
        return jsonify({
            'status': 'test_successful',
            'message': 'TTS generation test completed',
            'model_available': tts_model is not None
        })
    except Exception as e:
        return jsonify({
            'status': 'test_failed',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("=" * 60)
    print("STALKER Remote TTS Server (Vast.AI)")
    print("=" * 60)
    
    # Initialize TTS model
    if initialize_chatterbox():
        print("[REMOTE SERVER] ✅ Ready to serve TTS requests")
    else:
        print("[REMOTE SERVER] ❌ TTS initialization failed")
    
    # Start server
    print("[REMOTE SERVER] Starting server on 127.0.0.1:5000...")
    app.run(host='127.0.0.1', port=5000, debug=False)