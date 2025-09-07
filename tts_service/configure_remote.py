#!/usr/bin/env python3
# configure_remote.py - Easy configuration for remote TTS
import sys
import json
from pathlib import Path
from remote_tts_client import remote_config, RemoteTTSClient

def test_remote_connection(server_url: str):
    """Test connection to remote server"""
    print(f"Testing connection to: {server_url}")
    client = RemoteTTSClient(server_url)
    return client.test_connection()

def enable_remote(server_url: str):
    """Enable remote TTS"""
    if test_remote_connection(server_url):
        remote_config.enable_remote(server_url)
        print("✅ Remote TTS enabled and tested successfully")
        return True
    else:
        print("❌ Failed to connect to remote server")
        return False

def disable_remote():
    """Disable remote TTS"""
    remote_config.disable_remote()
    print("✅ Remote TTS disabled, using local generation")

def show_status():
    """Show current configuration status"""
    # Reload config to get latest
    remote_config.config = remote_config._load_config()
    
    print("=" * 50)
    print("Remote TTS Configuration Status")
    print("=" * 50)
    print(f"Config file: {remote_config.config_file}")
    print(f"Enabled: {remote_config.enabled}")
    print(f"Server URL: {remote_config.server_url}")
    print(f"Timeout: {remote_config.timeout}s")
    print(f"Fallback to local: {remote_config.fallback_to_local}")
    
    if remote_config.enabled:
        print("\nTesting connection...")
        if test_remote_connection(remote_config.server_url):
            print("✅ Remote server is accessible")
        else:
            print("❌ Remote server is not accessible")

def show_config_file():
    """Show the current config file contents"""
    config_file = Path("./remote_config.json")
    if config_file.exists():
        with open(config_file, 'r') as f:
            config = json.load(f)
        print("Current remote_config.json:")
        print(json.dumps(config, indent=2))
    else:
        print("No config file found - will be created on first use")

def set_timeout(timeout_seconds: int):
    """Set remote TTS timeout"""
    remote_config.config["timeout"] = timeout_seconds
    remote_config._save_config()
    print(f"✅ Remote TTS timeout set to {timeout_seconds} seconds")

def main():
    if len(sys.argv) == 1:
        show_status()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'enable' and len(sys.argv) == 3:
        server_url = sys.argv[2]
        enable_remote(server_url)
    
    elif command == 'disable':
        disable_remote()
    
    elif command == 'test' and len(sys.argv) == 3:
        server_url = sys.argv[2]
        test_remote_connection(server_url)
    
    elif command == 'status':
        show_status()
    
    elif command == 'config':
        show_config_file()
    
    elif command == 'timeout' and len(sys.argv) == 3:
        timeout_val = int(sys.argv[2])
        set_timeout(timeout_val)

    else:
        print("Usage:")
        print("  python configure_remote.py                    # Show current status")
        print("  python configure_remote.py enable <url>       # Enable remote TTS")
        print("  python configure_remote.py disable            # Disable remote TTS")
        print("  python configure_remote.py test <url>         # Test connection")
        print("  python configure_remote.py status             # Show status")
        print("  python configure_remote.py config             # Show config file")
        print()
        print("Example:")
        print("  python configure_remote.py enable http://127.0.0.1::5000")

if __name__ == '__main__':
    main()