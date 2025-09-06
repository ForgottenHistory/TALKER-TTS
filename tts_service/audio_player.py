# audio_player.py - Refactored Windows audio playback with queue system
import subprocess
from pathlib import Path
from typing import Optional
from audio_queue import AudioQueue
from audio_backends import AudioBackendDetector

class AudioPlayer:
    def __init__(self):
        self.backend_detector = AudioBackendDetector()
        self.preferred_backend = None
        self.audio_queue = None
        
        self._initialize()
    
    def _initialize(self):
        """Initialize audio system"""
        # Detect best audio backend
        self.preferred_backend = self.backend_detector.detect_best_backend()
        if not self.preferred_backend:
            print("[AUDIO PLAYER] ERROR: No audio backends available!")
            return
        
        # Initialize audio queue with playback callback
        self.audio_queue = AudioQueue(self._play_audio_direct)
        print("[AUDIO PLAYER] Audio player initialized successfully")
    
    def play_audio(self, audio_file: Path, volume: float = 1.0) -> bool:
        """Queue audio file for playback (non-blocking)"""
        if not self.audio_queue:
            print("[AUDIO PLAYER] ERROR: Audio system not initialized")
            return False
        
        return self.audio_queue.queue_audio(audio_file, volume)
    
    def _play_audio_direct(self, audio_file: Path, volume: float) -> bool:
        """Direct audio playback (used by queue worker)"""
        if not self.preferred_backend:
            print("[AUDIO PLAYER] ERROR: No audio backend available")
            return False
        
        print(f"[AUDIO PLAYER] ==> Starting playback: {audio_file.name} (method: {self.preferred_backend.name}, volume: {volume})")
        
        success = self.preferred_backend.play(audio_file, volume)
        
        print(f"[AUDIO PLAYER] ==> Playback result: {'SUCCESS' if success else 'FAILED'} - {audio_file.name}")
        return success
    
    def is_currently_playing(self) -> bool:
        """Check if audio is currently playing"""
        if not self.audio_queue:
            return False
        return self.audio_queue.is_currently_playing()
    
    def get_queue_size(self) -> int:
        """Get number of items waiting in queue"""
        if not self.audio_queue:
            return 0
        return self.audio_queue.get_queue_size()
    
    def clear_queue(self):
        """Clear pending audio queue"""
        if self.audio_queue:
            self.audio_queue.clear_pending()
    
    def get_preferred_method(self) -> str:
        """Get the name of the preferred audio method"""
        if self.preferred_backend:
            return self.preferred_backend.name
        return "none"
    
    def test_audio(self) -> bool:
        """Test audio system with a simple beep"""
        try:
            print("[AUDIO PLAYER] Testing Windows audio system...")
            subprocess.run([
                'powershell', '-Command', '[Console]::Beep(800, 500)'
            ], capture_output=True, check=True, timeout=3)
            print("[AUDIO PLAYER] Audio test successful")
            return True
        except Exception as e:
            print(f"[AUDIO PLAYER] Audio test failed: {e}")
            return False
    
    def shutdown(self):
        """Clean shutdown of audio system"""
        print("[AUDIO PLAYER] Shutting down audio player...")
        
        if self.audio_queue:
            self.audio_queue.shutdown()
        
        print("[AUDIO PLAYER] Audio player shutdown complete")

# For backward compatibility, expose the old method names
AudioPlayer._clear_queue = lambda self: self.clear_queue()
AudioPlayer.preferred_method = property(lambda self: self.get_preferred_method())