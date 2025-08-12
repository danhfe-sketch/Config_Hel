#!/usr/bin/env python3
"""
Build script for creating executable with custom icon.

This script uses PyInstaller to create an executable with a custom icon.
"""

import os
import subprocess
import sys

def build_executable_with_icon():
    """Build the executable with custom icon."""
    
    # Path to your custom icon
    icon_path = "assets/icons/app_icon.ico"  # Change this to your icon path
    
    # Check if icon exists
    if not os.path.exists(icon_path):
        print(f"Warning: Icon file not found at {icon_path}")
        print("Building without custom icon...")
        icon_arg = ""
    else:
        icon_arg = f"--icon={icon_path}"
        print(f"Using icon: {icon_path}")
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",                    # Create single executable
        "--windowed",                   # No console window
        "--name=LT32Pro_Configurator",  # Executable name
        icon_arg,                       # Icon argument
        "--add-data=assets;assets",     # Include assets folder
        "--add-data=assets\locales;assets\locales",   # Include locales folder
        "main.py"                       # Main script
    ]
    
    # Remove empty icon argument if no icon
    cmd = [arg for arg in cmd if arg]
    
    print("Building executable...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True)
        print("✅ Executable built successfully!")
        print("📁 Check the 'dist' folder for your executable")
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        return False
    except FileNotFoundError:
        print("❌ PyInstaller not found. Install it with: pip install pyinstaller")
        return False
    
    return True

def main():
    """Main function."""
    print("=" * 50)
    print("LT32Pro Configurator - Build with Icon")
    print("=" * 50)
    
    success = build_executable_with_icon()
    
    if success:
        print("\n" + "=" * 50)
        print("✅ Build completed successfully!")
        print("=" * 50)
        print("\nNext steps:")
        print("1. Check the 'dist' folder for your executable")
        print("2. Test the executable to ensure the icon appears correctly")
        print("3. The icon should appear in:")
        print("   - Window title bar")
        print("   - Windows taskbar")
        print("   - File explorer")
        print("   - Alt+Tab switcher")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)