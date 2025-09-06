# audio_queue.py - Audio queue management system
import threading
import time
import uuid
from pathlib import Path
from queue import Queue, Empty
from typing import Optional, Tuple, Callable

class AudioQueue:
    def __init__(self, playback_callback: Callable[[Path, float], bool]):
        self.audio_queue = Queue()
        self.is_playing = False
        self.current_playback_id = None
        self.queue_thread = None
        self.stop_requested = False
        self.playback_callback = playback_callback
        
        self._start_queue_worker()
    
    def _start_queue_worker(self):
        """Start the audio queue worker thread"""
        self.queue_thread = threading.Thread(target=self._process_audio_queue, daemon=True)
        self.queue_thread.start()
        print("[AUDIO QUEUE] Audio queue worker started")
    
    def _process_audio_queue(self):
        """Process audio files from queue one at a time"""
        print("[AUDIO QUEUE] Audio queue worker started")
        
        while not self.stop_requested:
            try:
                # Wait for next audio item (blocks until available)
                try:
                    audio_item = self.audio_queue.get(timeout=1.0)
                except Empty:
                    # Timeout is normal - just continue the loop
                    continue
                except Exception as e:
                    print(f"[AUDIO QUEUE] Queue get error: {e}")
                    continue
                
                if audio_item is None:  # Shutdown signal
                    print("[AUDIO QUEUE] Queue worker received shutdown signal")
                    break
                
                try:
                    audio_file, volume, playback_id = audio_item
                except ValueError as e:
                    print(f"[AUDIO QUEUE] Invalid audio item format: {e}")
                    self.audio_queue.task_done()
                    continue
                
                # Skip if this playback was cancelled
                if playback_id != self.current_playback_id:
                    print(f"[AUDIO QUEUE] Skipping cancelled playback: {playback_id}")
                    self.audio_queue.task_done()
                    continue
                
                print(f"[AUDIO QUEUE] Playing queued audio: {audio_file.name}")
                self.is_playing = True
                
                try:
                    # Use the callback to play the audio file
                    success = self.playback_callback(audio_file, volume)
                    
                    if success:
                        print(f"[AUDIO QUEUE] Completed playback: {audio_file.name}")
                    else:
                        print(f"[AUDIO QUEUE] Failed playback: {audio_file.name}")
                        
                except Exception as e:
                    print(f"[AUDIO QUEUE] Playback error: {e}")
                    success = False
                
                self.is_playing = False
                self.audio_queue.task_done()
                
            except Exception as e:
                print(f"[AUDIO QUEUE] Queue worker unexpected error: {e}")
                import traceback
                traceback.print_exc()
                self.is_playing = False
                time.sleep(1.0)  # Longer pause on unexpected errors
        
        print("[AUDIO QUEUE] Audio queue worker stopped")
    
    def queue_audio(self, audio_file: Path, volume: float = 1.0) -> bool:
        """Queue audio file for playback (non-blocking)"""
        if not audio_file.exists():
            print(f"[AUDIO QUEUE] ERROR: Audio file does not exist: {audio_file}")
            return False
        
        # Generate unique playback ID
        playback_id = str(uuid.uuid4())
        self.current_playback_id = playback_id
        
        print(f"[AUDIO QUEUE] New audio request: {audio_file.name} (ID: {playback_id})")
        
        # Only clear queue if something is queued but not playing
        # Don't interrupt currently playing audio
        if not self.is_playing and not self.audio_queue.empty():
            print("[AUDIO QUEUE] Clearing pending queue (not currently playing)")
            self.clear_pending()
        elif self.is_playing:
            print("[AUDIO QUEUE] Audio currently playing, will queue after current")
        
        # Add to queue
        self.audio_queue.put((audio_file, volume, playback_id))
        print(f"[AUDIO QUEUE] Queued audio: {audio_file.name} (Queue size: {self.get_queue_size()})")
        
        return True
    
    def clear_pending(self):
        """Clear pending audio items from queue"""
        cleared_count = 0
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
                cleared_count += 1
            except:
                break
        
        if cleared_count > 0:
            print(f"[AUDIO QUEUE] Cleared {cleared_count} pending audio items from queue")
    
    def is_currently_playing(self) -> bool:
        """Check if audio is currently playing"""
        return self.is_playing
    
    def get_queue_size(self) -> int:
        """Get number of items waiting in queue"""
        return self.audio_queue.qsize()
    
    def shutdown(self):
        """Clean shutdown of audio queue system"""
        print("[AUDIO QUEUE] Shutting down audio queue...")
        self.stop_requested = True
        
        # Signal queue worker to stop
        if self.queue_thread and self.queue_thread.is_alive():
            self.audio_queue.put(None)  # Shutdown signal
            self.queue_thread.join(timeout=2)
        
        print("[AUDIO QUEUE] Audio queue shutdown complete")