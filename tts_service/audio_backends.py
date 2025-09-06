# audio_backends.py - Different audio playback backend implementations
import subprocess
import time
from pathlib import Path
from typing import Optional

class AudioBackend:
    """Base class for audio backends"""
    
    def __init__(self, name: str):
        self.name = name
    
    def test(self) -> bool:
        """Test if this backend is available"""
        raise NotImplementedError
    
    def play(self, audio_file: Path, volume: float) -> bool:
        """Play audio file with specified volume"""
        raise NotImplementedError

class PygameBackend(AudioBackend):
    def __init__(self):
        super().__init__("pygame")
        self.pygame = None
    
    def test(self) -> bool:
        """Test if pygame is available"""
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.quit()
            self.pygame = pygame
            return True
        except ImportError:
            print("[PYGAME] Pygame not available")
            return False
        except Exception as e:
            print(f"[PYGAME] Pygame test failed: {e}")
            return False
    
    def play(self, audio_file: Path, volume: float) -> bool:
        """Play audio using pygame"""
        if not self.pygame:
            return False
            
        try:
            # Initialize mixer if not already done
            if not self.pygame.mixer.get_init():
                self.pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
            
            print(f"[PYGAME] Loading audio file: {audio_file}")
            self.pygame.mixer.music.load(str(audio_file))
            self.pygame.mixer.music.set_volume(min(1.0, max(0.0, volume)))
            
            print(f"[PYGAME] Starting pygame playback...")
            self.pygame.mixer.music.play()
            
            # Wait for playback to complete
            start_time = time.time()
            while self.pygame.mixer.music.get_busy():
                time.sleep(0.1)
                
                # Safety timeout (max 30 seconds)
                if time.time() - start_time > 30:
                    print("[PYGAME] Pygame playback timeout, stopping")
                    self.pygame.mixer.music.stop()
                    break
            
            print("[PYGAME] Pygame playback completed")
            return True
            
        except Exception as e:
            print(f"[PYGAME] Pygame playback failed: {e}")
            import traceback
            traceback.print_exc()
            return False

class WindowsMediaPlayerBackend(AudioBackend):
    def __init__(self):
        super().__init__("wmplayer")
    
    def test(self) -> bool:
        """Test if Windows Media Player is available"""
        try:
            result = subprocess.run([
                'cmd', '/c', 'where', 'wmplayer'
            ], capture_output=True, check=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def play(self, audio_file: Path, volume: float) -> bool:
        """Play audio using Windows Media Player"""
        try:
            # Windows Media Player command line
            process = subprocess.Popen([
                'cmd', '/c', 'start', '/min', 'wmplayer', '/close', str(audio_file)
            ], creationflags=subprocess.CREATE_NO_WINDOW)
            
            # Wait for a reasonable time (estimate audio duration)
            file_size = audio_file.stat().st_size
            estimated_duration = max(2, min(15, file_size / 50000))  # Rough estimate
            
            time.sleep(estimated_duration)
            
            print("[WMPLAYER] Windows Media Player playback completed (estimated)")
            return True
            
        except Exception as e:
            print(f"[WMPLAYER] Windows Media Player failed: {e}")
            return False

class PowerShellBackend(AudioBackend):
    def __init__(self):
        super().__init__("powershell")
    
    def test(self) -> bool:
        """PowerShell is always available on Windows"""
        return True
    
    def play(self, audio_file: Path, volume: float) -> bool:
        """Play audio using PowerShell MediaPlayer"""
        try:
            abs_path = audio_file.resolve()
            
            powershell_script = f'''
            try {{
                Add-Type -AssemblyName presentationCore
                $player = New-Object system.windows.media.mediaplayer
                $player.Volume = {min(1.0, max(0.0, volume))}
                $player.open([uri]"{abs_path}")
                $player.Play()
                
                Write-Host "Audio player started successfully"
                Start-Sleep -Seconds 8  # Wait for audio playback
                
                $player.Stop()
                $player.Close()
                Write-Host "Audio playback completed"
            }} catch {{
                Write-Host "PowerShell audio error: $($_.Exception.Message)"
                exit 1
            }}
            '''
            
            result = subprocess.run([
                'powershell', '-WindowStyle', 'Hidden', '-Command', powershell_script
            ], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            success = result.returncode == 0
            if success:
                print("[POWERSHELL] PowerShell playback completed")
            else:
                print(f"[POWERSHELL] PowerShell playback failed: {result.stderr}")
            
            return success
            
        except Exception as e:
            print(f"[POWERSHELL] PowerShell playback failed: {e}")
            return False

class AudioBackendDetector:
    """Detects and manages available audio backends"""
    
    def __init__(self):
        self.backends = [
            PygameBackend(),
            WindowsMediaPlayerBackend(), 
            PowerShellBackend()
        ]
        self.preferred_backend = None
    
    def detect_best_backend(self) -> Optional[AudioBackend]:
        """Detect the best available audio backend"""
        print("[BACKEND DETECTOR] Detecting best audio playback method...")
        
        for backend in self.backends:
            if backend.test():
                self.preferred_backend = backend
                print(f"[BACKEND DETECTOR] Selected {backend.name} as preferred method")
                return backend
        
        print("[BACKEND DETECTOR] No audio backends available!")
        return None
    
    def get_preferred_backend(self) -> Optional[AudioBackend]:
        """Get the preferred backend (detect if not already done)"""
        if not self.preferred_backend:
            return self.detect_best_backend()
        return self.preferred_backend