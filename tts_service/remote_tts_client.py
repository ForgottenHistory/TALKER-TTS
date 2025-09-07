# remote_tts_client.py - Connect to remote TTS server on Vast.ai
import requests
import time
import json
from pathlib import Path
from typing import Optional

class RemoteTTSClient:
    def __init__(self, server_url: str, timeout: int = 30):
        self.server_url = server_url.rstrip('/')
        self.timeout = timeout
        self.temp_dir = Path("./temp")
        self.temp_dir.mkdir(exist_ok=True)
    
    def generate_tts_file(self, text: str, character_info: dict = None, 
                    target_volume: float = 1.0) -> Optional[Path]:
        """Generate TTS on remote server and download WAV file"""
        try:
            print(f"[REMOTE TTS] Sending request to {self.server_url}...")
            
            payload = {
                'text': text,
                'character_info': character_info,
                'target_volume': target_volume
            }
            
            # Calculate timeout based on text length (same logic as server)
            estimated_duration = len(text) / 10.0  # chars per second estimate  
            dynamic_timeout = max(60, estimated_duration + 30)  # minimum 60s
            actual_timeout = max(self.timeout, dynamic_timeout)
            
            print(f"[REMOTE TTS] Text length: {len(text)} chars, using timeout: {actual_timeout:.1f}s")
            
            start_time = time.time()
            
            response = requests.post(
                f"{self.server_url}/generate_tts",
                json=payload,
                timeout=actual_timeout,  # Use dynamic timeout
                stream=True
            )
            
            if response.status_code == 200:
                # Save downloaded audio file
                audio_file = self.temp_dir / f"remote_tts_{int(time.time() * 1000)}.wav"
                
                with open(audio_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                network_time = time.time() - start_time
                file_size = audio_file.stat().st_size / 1024  # KB
                
                print(f"[REMOTE TTS] ✅ Success in {network_time:.2f}s")
                print(f"[REMOTE TTS] Downloaded: {file_size:.1f} KB")
                
                return audio_file
            else:
                print(f"[REMOTE TTS] ❌ Server error: {response.status_code}")
                print(f"[REMOTE TTS] Response: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"[REMOTE TTS] ❌ Timeout after {self.timeout}s")
            return None
        except requests.exceptions.ConnectionError:
            print(f"[REMOTE TTS] ❌ Connection failed to {self.server_url}")
            return None
        except Exception as e:
            print(f"[REMOTE TTS] ❌ Error: {e}")
            return None
    
    def test_connection(self) -> bool:
        """Test connection to remote server"""
        try:
            print(f"[REMOTE TTS] Testing connection to {self.server_url}...")
            response = requests.get(f"{self.server_url}/health", timeout=10)
            
            if response.status_code == 200:
                health = response.json()
                print(f"[REMOTE TTS] ✅ Server online: {health}")
                return health.get('tts_available', False)
            else:
                print(f"[REMOTE TTS] ❌ Server unhealthy: {response.status_code}")
                return False
        except Exception as e:
            print(f"[REMOTE TTS] ❌ Connection test failed: {e}")
            return False

# Shared configuration management
class RemoteConfig:
    def __init__(self):
        self.config_file = Path("./remote_config.json")
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[REMOTE CONFIG] Error loading config: {e}")
        
        # Default config
        return {
            "enabled": False,
            "server_url": "http://127.0.0.1:5000",
            "timeout": 30,
            "fallback_to_local": True
        }
    
    def _save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"[REMOTE CONFIG] Error saving config: {e}")
    
    @property
    def enabled(self) -> bool:
        return self.config.get("enabled", False)
    
    @property
    def server_url(self) -> str:
        return self.config.get("server_url", "")
    
    @property
    def timeout(self) -> int:
        return self.config.get("timeout", 30)
    
    @property
    def fallback_to_local(self) -> bool:
        return self.config.get("fallback_to_local", True)
    
    def enable_remote(self, server_url: str):
        """Enable remote TTS with server URL"""
        self.config["enabled"] = True
        self.config["server_url"] = server_url
        self._save_config()
        print(f"[REMOTE CONFIG] Remote TTS enabled: {server_url}")
        
    def disable_remote(self):
        """Disable remote TTS (use local)"""
        self.config["enabled"] = False
        self._save_config()
        print("[REMOTE CONFIG] Remote TTS disabled, using local")

# Global config instance
remote_config = RemoteConfig()

def create_remote_client() -> Optional[RemoteTTSClient]:
    """Create remote TTS client if configured and enabled"""
    # Reload config each time to get latest settings
    remote_config.config = remote_config._load_config()
    
    if remote_config.enabled:
        client = RemoteTTSClient(remote_config.server_url, remote_config.timeout)
        if client.test_connection():
            return client
        elif remote_config.fallback_to_local:
            print("[REMOTE TTS] Remote failed, falling back to local")
            return None
        else:
            print("[REMOTE TTS] Remote failed, no fallback configured")
            return None
    return None 