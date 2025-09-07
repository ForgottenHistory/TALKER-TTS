#!/usr/bin/env python3
# sync_voices_to_remote.py - Sync voice files to Vast.AI server
import os
import sys
import json
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional
from urllib.parse import urlparse

def load_remote_config() -> Optional[dict]:
    """Load remote configuration from config file"""
    config_file = Path("./remote_config.json")
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading remote config: {e}")
    return None

def extract_host_from_config(config: dict) -> Optional[str]:
    """Extract SSH host from server URL in config"""
    server_url = config.get('server_url', '')
    if not server_url:
        return None
    
    try:
        parsed = urlparse(server_url)
        host = parsed.hostname
        
        # If it's localhost/127.0.0.1, we can't SSH to it
        if host in ['127.0.0.1', 'localhost']:
            print("⚠️  Config contains localhost URL - cannot SSH to localhost")
            print("   You need to specify the public IP of your Vast.AI instance")
            return None
            
        return host
    except Exception as e:
        print(f"❌ Error parsing server URL: {e}")
        return None

class VoiceSyncer:
    def __init__(self, ssh_host: str, ssh_user: str = "root", ssh_port: int = 22, remote_path: str = None):
        self.ssh_host = ssh_host
        self.ssh_user = ssh_user
        self.ssh_port = ssh_port
        # Auto-detect remote path if not specified
        self.remote_path = remote_path or self._detect_remote_path()
        self.local_voices_dir = Path("./voices")
    
    def _detect_remote_path(self) -> str:
        """Detect where the remote TTS server is running"""
        try:
            print("Detecting remote server location...")
            # Check if remote_tts_server.py exists in common locations
            locations = ["/workspace", "~", "/root", "/home/root"]
            
            for location in locations:
                cmd = f'test -f {location}/remote_tts_server.py && echo "{location}"'
                result = subprocess.run([
                    'ssh', '-p', str(self.ssh_port), f'{self.ssh_user}@{self.ssh_host}', cmd
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0 and result.stdout.strip():
                    detected_path = result.stdout.strip()
                    print(f"✅ Found remote_tts_server.py in: {detected_path}")
                    return detected_path
            
            print("⚠️  Could not find remote_tts_server.py, using /workspace")
            return "/workspace"
            
        except Exception as e:
            print(f"⚠️  Could not detect remote path: {e}, using /workspace")
            return "/workspace"
        
    def test_ssh_connection(self) -> bool:
        """Test SSH connection to remote server"""
        try:
            print(f"Testing SSH connection to {self.ssh_user}@{self.ssh_host}:{self.ssh_port}...")
            result = subprocess.run([
                'ssh', '-p', str(self.ssh_port), 
                '-o', 'ConnectTimeout=10', 
                '-o', 'BatchMode=yes',
                '-o', 'StrictHostKeyChecking=no',  # Add this for Vast.AI
                f'{self.ssh_user}@{self.ssh_host}', 
                'echo "Connection successful"'
            ], capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                print("✅ SSH connection successful")
                return True
            else:
                print(f"❌ SSH connection failed (code {result.returncode})")
                if result.stderr:
                    print(f"   Error: {result.stderr.strip()}")
                if result.stdout:
                    print(f"   Output: {result.stdout.strip()}")
                return False
        except subprocess.TimeoutExpired:
            print("❌ SSH connection timed out")
            return False
        except Exception as e:
            print(f"❌ SSH test error: {e}")
            return False
    
    def create_remote_directories(self, voice_files: List[Tuple[Path, str]]) -> bool:
        """Create voice directory structure on remote server based on actual files"""
        try:
            print("Creating remote voice directory structure...")
            
            # Create base voices directory
            cmd = f'mkdir -p {self.remote_path}/voices'
            result = subprocess.run([
                'ssh', '-p', str(self.ssh_port), f'{self.ssh_user}@{self.ssh_host}', cmd
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Failed to create base directory: {result.stderr}")
                return False
            
            # Extract all unique directories from the voice files
            directories = set()
            for _, relative_path in voice_files:
                # Get directory part (everything except filename)
                dir_path = str(Path(relative_path).parent)
                if dir_path != '.':  # Skip root directory
                    directories.add(dir_path)
            
            # Convert Windows paths to Unix paths and create directories
            for directory in directories:
                # Convert backslashes to forward slashes for Unix
                unix_dir = directory.replace('\\', '/')
                full_remote_path = f'{self.remote_path}/voices/{unix_dir}'
                
                cmd = f'mkdir -p "{full_remote_path}"'
                result = subprocess.run([
                    'ssh', '-p', str(self.ssh_port), f'{self.ssh_user}@{self.ssh_host}', cmd
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    print(f"❌ Failed to create directory {unix_dir}: {result.stderr}")
                    return False
                else:
                    print(f"  Created: {unix_dir}")
            
            print("✅ Remote directories created successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error creating remote directories: {e}")
            return False
    
    def scan_local_voices(self) -> List[Tuple[Path, str]]:
        """Scan local voice files and return list of (local_path, relative_path)"""
        voice_files = []
        
        if not self.local_voices_dir.exists():
            print(f"❌ Local voices directory not found: {self.local_voices_dir}")
            return voice_files
        
        # Scan for all .wav files
        for wav_file in self.local_voices_dir.rglob("*.wav"):
            relative_path = wav_file.relative_to(self.local_voices_dir)
            voice_files.append((wav_file, str(relative_path)))
        
        return voice_files
    
    def upload_voice_files(self, voice_files: List[Tuple[Path, str]]) -> bool:
        """Upload voice files using scp"""
        if not voice_files:
            print("ℹ️  No voice files found to upload")
            return True
        
        print(f"Uploading {len(voice_files)} voice files...")
        
        success_count = 0
        for local_path, relative_path in voice_files:
            # Convert Windows path separators to Unix
            unix_relative_path = relative_path.replace('\\', '/')
            remote_file_path = f"{self.remote_path}/voices/{unix_relative_path}"
            
            try:
                print(f"  Uploading: {relative_path}")
                
                # Use scp to upload file
                result = subprocess.run([
                    'scp', '-P', str(self.ssh_port),  # Note: scp uses -P (capital)
                    '-o', 'StrictHostKeyChecking=no',
                    str(local_path), 
                    f'{self.ssh_user}@{self.ssh_host}:{remote_file_path}'
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    file_size = local_path.stat().st_size / (1024 * 1024)  # MB
                    print(f"    ✅ Uploaded ({file_size:.2f} MB)")
                    success_count += 1
                else:
                    print(f"    ❌ Upload failed: {result.stderr}")
            
            except Exception as e:
                print(f"    ❌ Upload error: {e}")
        
        print(f"Upload complete: {success_count}/{len(voice_files)} files uploaded")
        return success_count == len(voice_files)
    
    def sync_all(self) -> bool:
        """Complete sync process"""
        print("=" * 60)
        print("STALKER TTS Voice Files Sync to Vast.AI")
        print("=" * 60)
        print(f"SSH Host: {self.ssh_host}:{self.ssh_port}")
        print(f"Remote path: {self.remote_path}")
        
        # Test connection
        if not self.test_ssh_connection():
            print("\n💡 Troubleshooting tips:")
            print("   1. Make sure you're using the correct public IP")
            print("   2. Check if SSH is enabled on your Vast.AI instance")
            print("   3. Verify the SSH port (usually 22)")
            print("   4. Make sure your SSH key is added to the instance")
            return False
        
        # Scan local files
        voice_files = self.scan_local_voices()
        print(f"Found {len(voice_files)} voice files locally")
        
        if not voice_files:
            print("No voice files to sync!")
            return True
        
        # Show what will be uploaded
        print("\nFiles to upload:")
        for local_path, relative_path in voice_files:
            file_size = local_path.stat().st_size / (1024 * 1024)  # MB
            print(f"  {relative_path} ({file_size:.2f} MB)")
        
        # Confirm upload
        response = input(f"\nUpload {len(voice_files)} files? (y/N): ").lower()
        if response != 'y':
            print("Upload cancelled")
            return False
        
        # Create directories
        if not self.create_remote_directories(voice_files):
            return False
        
        # Upload files
        success = self.upload_voice_files(voice_files)
        
        if success:
            print("\n✅ Voice sync completed successfully!")
            print("Restart your remote TTS server to use the new voice files.")
        else:
            print("\n❌ Voice sync completed with errors")
        
        return success

def main():
    # Try to load from config file first
    config = load_remote_config()
    ssh_host = None
    
    if config and config.get('enabled'):
        ssh_host = extract_host_from_config(config)
        if ssh_host:
            print(f"Using SSH host from remote config: {ssh_host}")
    
    # Command line arguments override config
    if len(sys.argv) >= 2:
        ssh_host = sys.argv[1]
        print(f"Using SSH host from command line: {ssh_host}")
    
    if not ssh_host:
        print("No SSH host specified!")
        print()
        print("Usage:")
        print("  python sync_voices_to_remote.py                           # Use from remote_config.json")
        print("  python sync_voices_to_remote.py <ssh_host>                # Override config")
        print("  python sync_voices_to_remote.py <ssh_host> <user>         # Override config + user")
        print("  python sync_voices_to_remote.py <ssh_host> <user> <port>  # Override config + user + port")
        print()
        print("Examples:")
        print("  python sync_voices_to_remote.py 37.63.53.5               # Your Vast.AI public IP")
        print("  python sync_voices_to_remote.py 37.63.53.5 root 22       # Explicit port")
        print()
        if config:
            print(f"Current config: enabled={config.get('enabled')}, url={config.get('server_url')}")
            print("⚠️  Note: SSH host cannot be extracted from localhost URL")
        else:
            print("No remote_config.json found - run 'python configure_remote.py' first")
        return
    
    ssh_user = sys.argv[2] if len(sys.argv) > 2 else "root"
    ssh_port = int(sys.argv[3]) if len(sys.argv) > 3 else 22
    
    syncer = VoiceSyncer(ssh_host, ssh_user, ssh_port)
    syncer.sync_all()

if __name__ == '__main__':
    main()