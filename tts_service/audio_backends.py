# audio_backends.py - Different audio playback backend implementations
import subprocess
import time
from pathlib import Path
from typing import Optional

def get_audio_duration(audio_file: Path) -> float:
    """Get actual audio duration from file"""
    try:
        # Try soundfile first (most accurate)
        import soundfile as sf
        info = sf.info(audio_file)
        duration = info.duration
        print(f"[DURATION] Detected duration: {duration:.2f}s via soundfile")
        return duration
    except:
        try:
            # Fallback: FFprobe
            result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', str(audio_file)
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                print(f"[DURATION] Detected duration: {duration:.2f}s via ffprobe")
                return duration
        except:
            pass
    
    # Last resort: file size estimate (very rough)
    file_size = audio_file.stat().st_size
    estimated_duration = max(3, min(60, file_size / 50000))
    print(f"[DURATION] Estimated duration: {estimated_duration:.2f}s (file size estimate)")
    return estimated_duration

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
            # Get actual audio duration
            duration = get_audio_duration(audio_file)
            timeout_duration = duration + 5.0  # Add 5 second buffer for pygame
            
            # Initialize mixer if not already done
            if not self.pygame.mixer.get_init():
                self.pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
            
            print(f"[PYGAME] Loading audio file: {audio_file}")
            self.pygame.mixer.music.load(str(audio_file))
            self.pygame.mixer.music.set_volume(min(1.0, max(0.0, volume)))
            
            print(f"[PYGAME] Starting pygame playback for {duration:.1f}s...")
            self.pygame.mixer.music.play()
            
            # Wait for playback to complete with proper timeout
            start_time = time.time()
            while self.pygame.mixer.music.get_busy():
                time.sleep(0.1)
                
                # Use calculated timeout instead of hardcoded 30s
                if time.time() - start_time > timeout_duration:
                    print(f"[PYGAME] Pygame playback timeout after {timeout_duration:.1f}s, stopping")
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
            # Get actual audio duration  
            duration = get_audio_duration(audio_file)
            wait_time = duration + 1.0  # Add 1 second buffer
            
            process = subprocess.Popen([
                'cmd', '/c', 'start', '/min', 'wmplayer', '/close', str(audio_file)
            ], creationflags=subprocess.CREATE_NO_WINDOW)
            
            print(f"[WMPLAYER] Playing for {wait_time:.1f}s (duration: {duration:.1f}s)")
            time.sleep(wait_time)
            
            print("[WMPLAYER] Windows Media Player playback completed")
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
            # Get actual audio duration
            duration = get_audio_duration(audio_file)
            wait_time = duration + 2.0  # Add 2 second buffer
            
            abs_path = audio_file.resolve()
            
            powershell_script = f'''
            try {{
                Add-Type -AssemblyName presentationCore
                $player = New-Object system.windows.media.mediaplayer
                $player.Volume = {min(1.0, max(0.0, volume))}
                $player.open([uri]"{abs_path}")
                $player.Play()
                
                Write-Host "Audio player started successfully"
                Start-Sleep -Seconds {wait_time}
                
                $player.Stop()
                $player.Close()
                Write-Host "Audio playback completed"
            }} catch {{
                Write-Host "PowerShell audio error: $($_.Exception.Message)"
                exit 1
            }}
            '''
            
            print(f"[POWERSHELL] Playing for {wait_time:.1f}s (duration: {duration:.1f}s)")
            
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