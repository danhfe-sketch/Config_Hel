"""
Integration tests for profile file I/O operations.

This module tests the complete integration between UniversalProfileService
and ProfileFileHandler to ensure end-to-end functionality works correctly.
"""

import json
import os
import tempfile
import shutil
import unittest
from datetime import datetime

from models.universal_profile import UniversalProfile, ProfileMetadata, ParameterValue
from services.universal_profile_service import UniversalProfileService
from services.parameter_specification_parser import ParameterSpecificationParser
from services.profile_file_handler import ProfileFileHandler


class TestProfileFileIntegration(unittest.TestCase):
    """Integration tests for profile file operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create mock parameter specification parser
        self.spec_parser = self._create_mock_spec_parser()
        
        # Create service instances
        self.profile_service = UniversalProfileService(self.spec_parser)
        self.file_handler = ProfileFileHandler()
        
        # Create sample profile
        self.sample_profile = self._create_sample_profile()
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_mock_spec_parser(self):
        """Create a mock parameter specification parser."""
        class MockSpecParser:
            def get_parameter_spec(self, param_name):
                return None
            
            def get_all_parameters(self):
                return ["server_ip", "server_port", "apn_server"]
        
        return MockSpecParser()
    
    def _create_sample_profile(self) -> UniversalProfile:
        """Create a sample profile for testing."""
        metadata = ProfileMetadata(
            parameter_spec_version="1.0",
            created_by="Integration Test",
            device_model="LT32 PRO",
            profile_format_version="1.0"
        )
        
        profile = UniversalProfile(
            name="Integration Test Profile",
            version="1.0",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            modified_at=datetime(2024, 1, 1, 12, 0, 0),
            metadata=metadata
        )
        
        # Add test parameters
        profile.set_parameter_value("server_ip", "192.168.1.100", "user")
        profile.set_parameter_value("server_port", "8080", "user")
        profile.set_parameter_value("apn_server", "internet.provider.com", "device")
        
        return profile
    
    def test_complete_save_load_cycle(self):
        """Test complete save and load cycle using both services."""
        file_path = os.path.join(self.temp_dir, "integration_test.json")
        
        # Save profile using UniversalProfileService
        save_success = self.profile_service.save_profile_to_file(self.sample_profile, file_path)
        self.assertTrue(save_success)
        self.assertTrue(os.path.exists(file_path))
        
        # Load profile using UniversalProfileService
        loaded_profile = self.profile_service.load_profile_from_file(file_path)
        
        # Verify profile data
        self.assertEqual(loaded_profile.name, "Integration Test Profile")
        self.assertEqual(len(loaded_profile.parameters), 3)
        self.assertEqual(loaded_profile.get_parameter_value("server_ip"), "192.168.1.100")
        self.assertEqual(loaded_profile.get_parameter_value("server_port"), "8080")
        self.assertEqual(loaded_profile.get_parameter_value("apn_server"), "internet.provider.com")
    
    def test_file_handler_direct_operations(self):
        """Test direct file handler operations."""
        file_path = os.path.join(self.temp_dir, "direct_test.json")
        
        # Save using file handler directly
        save_result = self.file_handler.save_profile_to_file(self.sample_profile, file_path)
        self.assertTrue(save_result.success)
        self.assertIn("Profile saved", save_result.message)
        
        # Load using file handler directly
        loaded_profile, load_result = self.file_handler.load_profile_from_file(file_path)
        self.assertTrue(load_result.success)
        self.assertIsNotNone(loaded_profile)
        self.assertEqual(loaded_profile.name, "Integration Test Profile")
    
    def test_profile_validation_integration(self):
        """Test profile validation integration."""
        file_path = os.path.join(self.temp_dir, "validation_test.json")
        
        # Save profile
        save_result = self.file_handler.save_profile_to_file(self.sample_profile, file_path)
        self.assertTrue(save_result.success)
        
        # Validate file
        validation_result = self.file_handler.validate_profile_file(file_path)
        self.assertTrue(validation_result.is_valid)
        
        # Get profile info
        profile_info = self.file_handler.get_profile_info(file_path)
        self.assertTrue(profile_info["exists"])
        self.assertEqual(profile_info["profile_name"], "Integration Test Profile")
        self.assertEqual(profile_info["parameter_count"], 3)
        self.assertEqual(profile_info["validation_status"], "valid")
    
    def test_profile_migration_integration(self):
        """Test profile migration integration."""
        file_path = os.path.join(self.temp_dir, "migration_test.json")
        
        # Create old format profile data
        old_profile_data = self.sample_profile.to_dict()
        old_profile_data["metadata"]["profile_format_version"] = "0.9"
        
        # Save old format manually
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(old_profile_data, f, indent=2)
        
        # Load through service (should auto-migrate)
        loaded_profile, load_result = self.file_handler.load_profile_from_file(file_path, auto_migrate=True)
        
        self.assertTrue(load_result.success)
        self.assertTrue(load_result.details.get("migration_performed", False))
        self.assertEqual(loaded_profile.metadata.profile_format_version, "1.0")
    
    def test_backup_creation_integration(self):
        """Test backup creation during save operations."""
        file_path = os.path.join(self.temp_dir, "backup_test.json")
        
        # Create initial file
        initial_profile = self.sample_profile.clone("Initial Profile")
        save_result1 = self.file_handler.save_profile_to_file(initial_profile, file_path)
        self.assertTrue(save_result1.success)
        
        # Save different profile (should create backup)
        updated_profile = self.sample_profile.clone("Updated Profile")
        save_result2 = self.file_handler.save_profile_to_file(updated_profile, file_path, create_backup=True)
        self.assertTrue(save_result2.success)
        
        # Check backup was created
        backup_dir = os.path.join(self.temp_dir, "backups")
        self.assertTrue(os.path.exists(backup_dir))
        backup_files = os.listdir(backup_dir)
        self.assertTrue(any(f.startswith("backup_test_backup_") for f in backup_files))
        
        # Verify current file has updated content
        loaded_profile, _ = self.file_handler.load_profile_from_file(file_path)
        self.assertEqual(loaded_profile.name, "Updated Profile")
    
    def test_error_handling_integration(self):
        """Test error handling integration."""
        # Test loading non-existent file
        nonexistent_path = os.path.join(self.temp_dir, "nonexistent.json")
        
        with self.assertRaises(FileNotFoundError):
            self.profile_service.load_profile_from_file(nonexistent_path)
        
        # Test loading invalid JSON
        invalid_path = os.path.join(self.temp_dir, "invalid.json")
        with open(invalid_path, 'w') as f:
            f.write("{ invalid json")
        
        with self.assertRaises(ValueError):
            self.profile_service.load_profile_from_file(invalid_path)
    
    def test_profile_listing_integration(self):
        """Test profile listing functionality."""
        # Create multiple profiles
        profiles = [
            self.sample_profile.clone("Profile A"),
            self.sample_profile.clone("Profile B"),
            self.sample_profile.clone("Profile C")
        ]
        
        for i, profile in enumerate(profiles):
            file_path = os.path.join(self.temp_dir, f"profile_{i}.json")
            save_result = self.file_handler.save_profile_to_file(profile, file_path)
            self.assertTrue(save_result.success)
        
        # List profiles
        profile_list = self.file_handler.list_profile_files(self.temp_dir)
        
        self.assertEqual(len(profile_list), 3)
        profile_names = [info["profile_name"] for info in profile_list]
        self.assertIn("Profile A", profile_names)
        self.assertIn("Profile B", profile_names)
        self.assertIn("Profile C", profile_names)
        
        # Verify all profiles are valid
        for profile_info in profile_list:
            self.assertEqual(profile_info["validation_status"], "valid")
            self.assertEqual(profile_info["parameter_count"], 3)
    
    def test_file_format_consistency(self):
        """Test that saved files have consistent format."""
        file_path = os.path.join(self.temp_dir, "format_test.json")
        
        # Save profile
        save_result = self.file_handler.save_profile_to_file(self.sample_profile, file_path)
        self.assertTrue(save_result.success)
        
        # Read raw JSON to verify format
        with open(file_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        # Verify required top-level fields
        required_fields = ["name", "version", "created_at", "modified_at", "metadata", "parameters"]
        for field in required_fields:
            self.assertIn(field, saved_data)
        
        # Verify file metadata
        self.assertIn("_file_metadata", saved_data)
        file_metadata = saved_data["_file_metadata"]
        self.assertEqual(file_metadata["file_format_version"], "1.0")
        self.assertIn("saved_at", file_metadata)
        self.assertIn("saved_by", file_metadata)
        
        # Verify parameter structure
        for param_name, param_data in saved_data["parameters"].items():
            self.assertIn("value", param_data)
            self.assertIn("source", param_data)
            self.assertIn("timestamp", param_data)
            self.assertIn("is_modified", param_data)


if __name__ == '__main__':
    unittest.main()