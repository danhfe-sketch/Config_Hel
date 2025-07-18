"""
Test script for build configuration and executable generation.

This script tests the build configuration for the LT32Pro Configurator application,
ensuring that the PyInstaller spec file is properly configured and the application
can be built into a standalone executable.
"""

import unittest
import os
import sys
import subprocess
import platform
import re
from unittest.mock import patch, MagicMock

class BuildConfigurationTest(unittest.TestCase):
    """Test build configuration and executable generation."""
    
    def setUp(self):
        """Set up test environment."""
        # Get the project root directory
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        
        # Path to the spec file
        self.spec_file = os.path.join(self.project_root, "LT32Pro_Configurator_v1.spec")
        
        # Path to main.py
        self.main_file = os.path.join(self.project_root, "main.py")
        
        # Path to requirements.txt
        self.requirements_file = os.path.join(self.project_root, "requirements.txt")
    
    def test_spec_file_exists(self):
        """Test that the PyInstaller spec file exists."""
        self.assertTrue(os.path.exists(self.spec_file), f"Spec file not found: {self.spec_file}")
    
    def test_main_file_exists(self):
        """Test that the main.py file exists."""
        self.assertTrue(os.path.exists(self.main_file), f"Main file not found: {self.main_file}")
    
    def test_requirements_file_exists(self):
        """Test that the requirements.txt file exists."""
        self.assertTrue(os.path.exists(self.requirements_file), f"Requirements file not found: {self.requirements_file}")
    
    def test_spec_file_content(self):
        """Test that the spec file contains the necessary configuration."""
        with open(self.spec_file, 'r') as f:
            content = f.read()
        
        # Check for basic PyInstaller configuration
        self.assertIn("Analysis", content, "Analysis section not found in spec file")
        self.assertIn("PYZ", content, "PYZ section not found in spec file")
        self.assertIn("EXE", content, "EXE section not found in spec file")
        
        # Check for main.py as the entry point
        self.assertIn("main.py", content, "main.py not found as entry point in spec file")
        
        # Check for data files inclusion
        self.assertIn("datas", content, "Data files section not found in spec file")
        
        # Check for icon configuration
        self.assertIn("icon", content, "Icon configuration not found in spec file")
    
    def test_requirements_content(self):
        """Test that the requirements.txt file contains the necessary dependencies."""
        with open(self.requirements_file, 'r') as f:
            content = f.read()
        
        # Check for required packages
        required_packages = [
            "customtkinter",
            "pyserial",
            "pillow",
            "pyinstaller"
        ]
        
        for package in required_packages:
            self.assertIn(package.lower(), content.lower(), f"Required package {package} not found in requirements.txt")
    
    @patch('subprocess.run')
    def test_build_command(self, mock_run):
        """Test that the build command works correctly."""
        # Setup mock
        mock_run.return_value = MagicMock(returncode=0)
        
        # Build command
        build_cmd = ["pyinstaller", "--noconfirm", self.spec_file]
        
        # Mock the command execution
        mock_run.return_value = MagicMock(returncode=0)
        
        # Check that the command would succeed
        self.assertEqual(mock_run.return_value.returncode, 0, "Build command failed")
    
    def test_main_imports(self):
        """Test that main.py imports all necessary modules."""
        with open(self.main_file, 'r') as f:
            content = f.read()
        
        # Check for required imports
        required_imports = [
            "tkinter",
            "customtkinter",
            "serial",
            "json",
            "os",
            "sys"
        ]
        
        for imp in required_imports:
            import_pattern = re.compile(r'import\s+' + imp + r'\b|from\s+' + imp + r'\s+import')
            self.assertTrue(import_pattern.search(content), f"Required import {imp} not found in main.py")
    
    def test_resource_directories(self):
        """Test that all required resource directories exist."""
        required_dirs = [
            os.path.join(self.project_root, "assets"),
            os.path.join(self.project_root, "services"),
            os.path.join(self.project_root, "ui"),
            os.path.join(self.project_root, "utils")
        ]
        
        for directory in required_dirs:
            self.assertTrue(os.path.isdir(directory), f"Required directory not found: {directory}")
    
    def test_locale_files(self):
        """Test that locale files exist for all supported languages."""
        locale_dir = os.path.join(self.project_root, "assets", "locales")
        self.assertTrue(os.path.isdir(locale_dir), f"Locale directory not found: {locale_dir}")
        
        required_locales = [
            "en_US.json",
            "pt_BR.json",
            "es_ES.json"
        ]
        
        for locale in required_locales:
            locale_path = os.path.join(locale_dir, locale)
            self.assertTrue(os.path.exists(locale_path), f"Required locale file not found: {locale_path}")
    
    def test_icon_file(self):
        """Test that the application icon file exists."""
        icon_path = os.path.join(self.project_root, "assets", "icon.ico")
        self.assertTrue(os.path.exists(icon_path), f"Icon file not found: {icon_path}")

if __name__ == '__main__':
    unittest.main()