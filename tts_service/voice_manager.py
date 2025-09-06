# voice_manager.py - Manage custom .pt voice files for factions
import shutil
from pathlib import Path
from typing import Dict, List

class VoiceManager:
    def __init__(self):
        self.voices_dir = Path("voices")
        self.voices_dir.mkdir(exist_ok=True)
        
        self.factions = [
            'army', 'bandit', 'duty', 'freedom', 'stalker', 
            'loner', 'monolith', 'ecologist', 'mercenary'
        ]
    
    def setup_voice_structure(self):
        """Create voice directory structure for all factions"""
        print("Setting up voice directory structure...")
        
        for faction in self.factions:
            faction_dir = self.voices_dir / faction
            faction_dir.mkdir(exist_ok=True)
            
            # Create placeholder file with instructions
            placeholder = faction_dir / "README.txt"
            if not placeholder.exists():
                with open(placeholder, 'w', encoding='utf-8') as f:
                    f.write(f"# {faction.upper()} Voice Files\n")
                    f.write(f"# Place your custom {faction} voice files here:\n\n")
                    f.write(f"# Option 1: Single voice file\n")
                    f.write(f"#   voices/{faction}.pt\n\n")
                    f.write(f"# Option 2: Default voice in faction folder\n")
                    f.write(f"#   voices/{faction}/default.pt\n\n")
                    f.write(f"# Option 3: Multiple voices (future feature)\n")
                    f.write(f"#   voices/{faction}/male.pt\n")
                    f.write(f"#   voices/{faction}/female.pt\n\n")
                    f.write(f"# Custom .pt voice files can be:\n")
                    f.write(f"# - Trained Kokoro voices\n")
                    f.write(f"# - Downloaded from community\n")
                    f.write(f"# - Created using Kokoro training scripts\n\n")
                    f.write(f"# If no custom voice is found, built-in voices are used:\n")
                    f.write(f"# am_adam, am_michael, af_heart, af_sky\n")
                
                print(f"Created: voices/{faction}/README.txt")
        
        # Create main voices directory readme
        main_readme = self.voices_dir / "README.txt"
        if not main_readme.exists():
            with open(main_readme, 'w', encoding='utf-8') as f:
                f.write("# STALKER TTS Custom Voice Files\n\n")
                f.write("This directory contains custom .pt voice files for different factions.\n\n")
                f.write("## File Structure:\n")
                f.write("voices/\n")
                f.write("|-- army.pt              # Army faction voice (Option 1)\n")
                f.write("|-- bandit.pt            # Bandit faction voice\n")
                f.write("|-- army/\n")
                f.write("|   |-- default.pt       # Army faction voice (Option 2)\n")
                f.write("|-- bandit/\n")
                f.write("    |-- default.pt       # Bandit faction voice\n\n")
                f.write("## How to Add Custom Voices:\n")
                f.write("1. Get a .pt voice file (trained Kokoro voice)\n")
                f.write("2. Place it as voices/FACTION_NAME.pt\n")
                f.write("3. Restart the TTS server\n")
                f.write("4. Test with that faction's characters\n\n")
                f.write("## Built-in Voices (used if no custom file found):\n")
                f.write("- am_adam: Deep, authoritative male\n")
                f.write("- am_michael: Versatile male\n")
                f.write("- af_heart: Warm, expressive female\n")
                f.write("- af_sky: Clear, professional female\n\n")
                f.write("## Training Your Own Voices:\n")
                f.write("Use Kokoro training scripts to create custom .pt files\n")
                f.write("from your own audio samples.\n")
        
        print("✅ Voice directory structure created")
    
    def scan_available_voices(self) -> Dict[str, Dict]:
        """Scan for available voice files"""
        available_voices = {
            'built_in': ['am_adam', 'am_michael', 'af_heart', 'af_sky'],
            'custom_files': {},
            'faction_voices': {}
        }
        
        # Scan for faction-specific .pt files
        for faction in self.factions:
            # FIRST: Check faction directory for any .pt files
            faction_dir = self.voices_dir / faction
            if faction_dir.exists():
                pt_files = list(faction_dir.glob("*.pt"))
                if pt_files:
                    # Use first .pt file found
                    voice_file = pt_files[0]
                    available_voices['faction_voices'][faction] = str(voice_file)
                    available_voices['custom_files'][f"{faction}/{voice_file.name}"] = {
                        'path': str(voice_file),
                        'size_mb': round(voice_file.stat().st_size / (1024*1024), 2),
                        'faction': faction
                    }
                    continue  # Don't check root directory if we found one in faction dir
            
            # SECOND: Check root voices directory for faction.pt
            faction_pt = self.voices_dir / f"{faction}.pt"
            if faction_pt.exists():
                available_voices['faction_voices'][faction] = str(faction_pt)
                available_voices['custom_files'][f"{faction}.pt"] = {
                    'path': str(faction_pt),
                    'size_mb': round(faction_pt.stat().st_size / (1024*1024), 2),
                    'faction': faction
                }
        
        return available_voices
    
    def install_voice_file(self, source_path: str, faction: str) -> bool:
        """Install a voice file for a specific faction"""
        source = Path(source_path)
        if not source.exists():
            print(f"❌ Source file not found: {source_path}")
            return False
        
        if not source.suffix == '.pt':
            print(f"❌ File must be a .pt file: {source_path}")
            return False
        
        if faction not in self.factions:
            print(f"❌ Unknown faction: {faction}")
            print(f"Available factions: {', '.join(self.factions)}")
            return False
        
        # Copy to faction directory
        destination = self.voices_dir / f"{faction}.pt"
        try:
            shutil.copy2(source, destination)
            print(f"✅ Installed {faction} voice: {destination}")
            print(f"   File size: {destination.stat().st_size / (1024*1024):.2f} MB")
            return True
        except Exception as e:
            print(f"❌ Failed to install voice file: {e}")
            return False
    
    def remove_voice_file(self, faction: str) -> bool:
        """Remove custom voice file for a faction"""
        if faction not in self.factions:
            print(f"❌ Unknown faction: {faction}")
            return False
        
        # Check both locations
        faction_pt = self.voices_dir / f"{faction}.pt"
        faction_default = self.voices_dir / faction / "default.pt"
        
        removed = False
        if faction_pt.exists():
            faction_pt.unlink()
            print(f"✅ Removed: {faction_pt}")
            removed = True
        
        if faction_default.exists():
            faction_default.unlink()
            print(f"✅ Removed: {faction_default}")
            removed = True
        
        if not removed:
            print(f"ℹ️  No custom voice file found for {faction}")
        
        return removed
    
    def print_status(self):
        """Print current voice configuration status"""
        voices = self.scan_available_voices()
        
        print("=" * 60)
        print("STALKER TTS Voice Configuration Status")
        print("=" * 60)
        
        print(f"\n📁 Voice directory: {self.voices_dir.absolute()}")
        
        print(f"\n🎵 Built-in voices: {len(voices['built_in'])}")
        for voice in voices['built_in']:
            print(f"   - {voice}")
        
        print(f"\n📦 Custom voice files: {len(voices['custom_files'])}")
        if voices['custom_files']:
            for filename, info in voices['custom_files'].items():
                print(f"   - {filename} ({info['size_mb']} MB) → {info['faction']}")
        else:
            print("   (none found)")
        
        print(f"\n🏴 Faction voice assignments:")
        for faction in self.factions:
            if faction in voices['faction_voices']:
                voice_file = Path(voices['faction_voices'][faction]).name
                print(f"   - {faction:12} → {voice_file} (custom)")
            else:
                print(f"   - {faction:12} → built-in voice (from config)")
        
        print(f"\n💡 To add custom voices:")
        print(f"   python voice_manager.py install <voice_file.pt> <faction>")

def main():
    import sys
    
    vm = VoiceManager()
    
    if len(sys.argv) == 1:
        # No arguments - show status and setup
        vm.setup_voice_structure()
        vm.print_status()
    
    elif sys.argv[1] == 'setup':
        vm.setup_voice_structure()
        print("✅ Voice structure setup complete")
    
    elif sys.argv[1] == 'status':
        vm.print_status()
    
    elif sys.argv[1] == 'install' and len(sys.argv) == 4:
        voice_file = sys.argv[2]
        faction = sys.argv[3]
        if vm.install_voice_file(voice_file, faction):
            print("🔄 Restart the TTS server to use the new voice")
    
    elif sys.argv[1] == 'remove' and len(sys.argv) == 3:
        faction = sys.argv[2]
        if vm.remove_voice_file(faction):
            print("🔄 Restart the TTS server to revert to built-in voice")
    
    else:
        print("Usage:")
        print("  python voice_manager.py                    # Setup and show status")
        print("  python voice_manager.py status             # Show current status")
        print("  python voice_manager.py setup              # Create voice directories")
        print("  python voice_manager.py install <file.pt> <faction>  # Install custom voice")
        print("  python voice_manager.py remove <faction>   # Remove custom voice")

if __name__ == '__main__':
    main()