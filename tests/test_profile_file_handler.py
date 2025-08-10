"""
Unit tests for the Profile File Handler.

This module tests all aspects of profile file I/O operations including:
- JSON serialization/deserialization
- Profile metadata handling with version information and timestamps
- Profile migration logic for handling format changes
- Error handling and recovery scenarios
- File validation and backup operations

Requirements tested:
- 3.2: Save profile to file with proper validation metadata
- 3.3: Load profile from file with validation
- 3.4: Handle profile file format validation and migration
- 5.5: Include version information for future compatibility
"""

import json
import os
import tempfile
import shutil
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from models.universal_profile import UniversalProfile, ProfileMetadata, ParameterValue
from models.validation_result import ValidationResult
from services.profile_file_handler import ProfileFileHandler, ProfileFileError, ProfileMigrationError, OperationResult


class TestProfileFileHandler(unittest.TestCase):
    """Test cases for ProfileFileHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.handler = ProfileFileHandler()
        
        # Create a sample profile for testing
        self.sample_profile = self._create_sample_profile()
        
        # Sample profile data for testing
        self.sample_profile_data = {
            "name": "Test Profile",
            "version": "1.0",
            "created_at": "2024-01-01T12:00:00",
            "modified_at": "2024-01-01T12:00:00",
            "metadata": {
                "parameter_spec_version": "1.0",
                "created_by": "LT32 PRO Configurator",
                "device_model": "LT32 PRO",
                "profile_format_version": "1.0",
                "tags": {}
            },
            "parameters": {
                "test_param": {
                    "value": "test_value",
                    "source": "user",
                    "timestamp": "2024-01-01T12:00:00",
                    "is_modified": False
                }
            }
        }
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_sample_profile(self) -> UniversalProfile:
        """Create a sample profile for testing."""
        metadata = ProfileMetadata(
            parameter_spec_version="1.0",
            created_by="Test User",
            device_model="LT32 PRO",
            profile_format_version="1.0"
        )
        
        profile = UniversalProfile(
            name="Test Profile",
            version="1.0",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            modified_at=datetime(2024, 1, 1, 12, 0, 0),
            metadata=metadata
        )
        
        # Add some test parameters
        profile.set_parameter_value("server_ip", "192.168.1.100", "user")
        profile.set_parameter_value("server_port", "8080", "user")
        profile.set_parameter_value("apn_server", "internet.provider.com", "device")
        
        return profile
    
    def test_save_profile_to_file_success(self):
        """Test successful profile saving to file."""
        file_path = os.path.join(self.temp_dir, "test_profile.json")
        
        result = self.handler.save_profile_to_file(self.sample_profile, file_path)
        
        self.assertTrue(result.success)
        self.assertEqual(result.operation_type, "save_profile")
        self.assertIn("Profile saved to", result.message)
        self.assertTrue(os.path.exists(file_path))
        
        # Verify file content
        with open(file_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        self.assertEqual(saved_data["name"], "Test Profile")
        self.assertIn("_file_metadata", saved_data)
        self.assertEqual(saved_data["_file_metadata"]["file_format_version"], "1.0")
    
    def test_save_profile_adds_extension(self):
        """Test that profile saving adds .json extension if missing."""
        file_path = os.path.join(self.temp_dir, "test_profile")
        expected_path = file_path + ".json"
        
        result = self.handler.save_profile_to_file(self.sample_profile, file_path)
        
        self.assertTrue(result.success)
        self.assertTrue(os.path.exists(expected_path))
        self.assertFalse(os.path.exists(file_path))
    
    def test_save_profile_creates_directory(self):
        """Test that profile saving creates directory if it doesn't exist."""
        nested_dir = os.path.join(self.temp_dir, "nested", "directory")
        file_path = os.path.join(nested_dir, "test_profile.json")
        
        result = self.handler.save_profile_to_file(self.sample_profile, file_path)
        
        self.assertTrue(result.success)
        self.assertTrue(os.path.exists(nested_dir))
        self.assertTrue(os.path.exists(file_path))
    
    def test_save_profile_creates_backup(self):
        """Test that profile saving creates backup of existing file."""
        file_path = os.path.join(self.temp_dir, "test_profile.json")
        
        # Create initial file
        with open(file_path, 'w') as f:
            json.dump({"test": "data"}, f)
        
        result = self.handler.save_profile_to_file(self.sample_profile, file_path, create_backup=True)
        
        self.assertTrue(result.success)
        
        # Check backup was created
        backup_dir = os.path.join(self.temp_dir, "backups")
        self.assertTrue(os.path.exists(backup_dir))
        backup_files = os.listdir(backup_dir)
        self.assertTrue(any(f.startswith("test_profile_backup_") for f in backup_files))
    
    def test_save_profile_permission_error(self):
        """Test profile saving with permission error."""
        # Skip this test on Windows as chmod doesn't work the same way
        import platform
        if platform.system() == "Windows":
            self.skipTest("Permission test not applicable on Windows")
        
        # Create a read-only directory
        readonly_dir = os.path.join(self.temp_dir, "readonly")
        os.makedirs(readonly_dir)
        os.chmod(readonly_dir, 0o444)
        
        file_path = os.path.join(readonly_dir, "test_profile.json")
        
        result = self.handler.save_profile_to_file(self.sample_profile, file_path)
        
        self.assertFalse(result.success)
        self.assertEqual(result.operation_type, "save_profile")
        self.assertIn("Permission denied", result.error_message)
        
        # Cleanup
        os.chmod(readonly_dir, 0o755)
    
    def test_load_profile_from_file_success(self):
        """Test successful profile loading from file."""
        file_path = os.path.join(self.temp_dir, "test_profile.json")
        
        # Save profile first
        save_result = self.handler.save_profile_to_file(self.sample_profile, file_path)
        self.assertTrue(save_result.success)
        
        # Load profile
        loaded_profile, load_result = self.handler.load_profile_from_file(file_path)
        
        self.assertTrue(load_result.success)
        self.assertEqual(load_result.operation_type, "load_profile")
        self.assertIsNotNone(loaded_profile)
        self.assertEqual(loaded_profile.name, "Test Profile")
        self.assertEqual(len(loaded_profile.parameters), 3)
        self.assertEqual(loaded_profile.get_parameter_value("server_ip"), "192.168.1.100")
    
    def test_load_profile_file_not_found(self):
        """Test loading profile from non-existent file."""
        file_path = os.path.join(self.temp_dir, "nonexistent.json")
        
        loaded_profile, result = self.handler.load_profile_from_file(file_path)
        
        self.assertFalse(result.success)
        self.assertIsNone(loaded_profile)
        self.assertIn("not found", result.error_message)
    
    def test_load_profile_empty_file(self):
        """Test loading profile from empty file."""
        file_path = os.path.join(self.temp_dir, "empty.json")
        
        # Create empty file
        with open(file_path, 'w') as f:
            pass
        
        loaded_profile, result = self.handler.load_profile_from_file(file_path)
        
        self.assertFalse(result.success)
        self.assertIsNone(loaded_profile)
        self.assertIn("empty", result.error_message)
    
    def test_load_profile_invalid_json(self):
        """Test loading profile from file with invalid JSON."""
        file_path = os.path.join(self.temp_dir, "invalid.json")
        
        # Create file with invalid JSON
        with open(file_path, 'w') as f:
            f.write("{ invalid json content")
        
        loaded_profile, result = self.handler.load_profile_from_file(file_path)
        
        self.assertFalse(result.success)
        self.assertIsNone(loaded_profile)
        self.assertIn("Invalid JSON", result.error_message)
    
    def test_load_profile_invalid_format(self):
        """Test loading profile with invalid format."""
        file_path = os.path.join(self.temp_dir, "invalid_format.json")
        
        # Create file with invalid profile format
        invalid_data = {"invalid": "format"}
        with open(file_path, 'w') as f:
            json.dump(invalid_data, f)
        
        loaded_profile, result = self.handler.load_profile_from_file(file_path)
        
        self.assertFalse(result.success)
        self.assertIsNone(loaded_profile)
        self.assertIn("Invalid profile format", result.error_message)
    
    def test_validate_profile_file_success(self):
        """Test successful profile file validation."""
        file_path = os.path.join(self.temp_dir, "test_profile.json")
        
        # Save profile first
        save_result = self.handler.save_profile_to_file(self.sample_profile, file_path)
        self.assertTrue(save_result.success)
        
        # Validate file
        result = self.handler.validate_profile_file(file_path)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_validate_profile_file_not_found(self):
        """Test validation of non-existent file."""
        file_path = os.path.join(self.temp_dir, "nonexistent.json")
        
        result = self.handler.validate_profile_file(file_path)
        
        self.assertFalse(result.is_valid)
        self.assertTrue(any("not found" in error for error in result.errors))
    
    def test_validate_profile_file_invalid_json(self):
        """Test validation of file with invalid JSON."""
        file_path = os.path.join(self.temp_dir, "invalid.json")
        
        # Create file with invalid JSON
        with open(file_path, 'w') as f:
            f.write("{ invalid json")
        
        result = self.handler.validate_profile_file(file_path)
        
        self.assertFalse(result.is_valid)
        self.assertTrue(any("Invalid JSON" in error for error in result.errors))
    
    def test_validate_profile_file_missing_fields(self):
        """Test validation of file with missing required fields."""
        file_path = os.path.join(self.temp_dir, "incomplete.json")
        
        # Create file with incomplete data
        incomplete_data = {"name": "Test"}
        with open(file_path, 'w') as f:
            json.dump(incomplete_data, f)
        
        result = self.handler.validate_profile_file(file_path)
        
        self.assertFalse(result.is_valid)
        self.assertTrue(any("Missing required field" in error for error in result.errors))
    
    def test_migrate_profile_file_no_migration_needed(self):
        """Test migration when profile is already current version."""
        file_path = os.path.join(self.temp_dir, "current_version.json")
        
        # Save current version profile
        save_result = self.handler.save_profile_to_file(self.sample_profile, file_path)
        self.assertTrue(save_result.success)
        
        # Attempt migration
        result = self.handler.migrate_profile_file(file_path)
        
        self.assertTrue(result.success)
        self.assertIn("already at current format version", result.message)
    
    def test_migrate_profile_file_with_backup(self):
        """Test migration with backup creation."""
        file_path = os.path.join(self.temp_dir, "old_version.json")
        
        # Create old version profile data
        old_data = self.sample_profile_data.copy()
        old_data["metadata"]["profile_format_version"] = "0.9"  # Simulate old version
        
        with open(file_path, 'w') as f:
            json.dump(old_data, f)
        
        # Migrate with backup
        result = self.handler.migrate_profile_file(file_path, backup=True)
        
        self.assertTrue(result.success)
        
        # Check backup was created
        backup_dir = os.path.join(self.temp_dir, "backups")
        self.assertTrue(os.path.exists(backup_dir))
    
    def test_get_profile_info_success(self):
        """Test getting profile information."""
        file_path = os.path.join(self.temp_dir, "test_profile.json")
        
        # Save profile first
        save_result = self.handler.save_profile_to_file(self.sample_profile, file_path)
        self.assertTrue(save_result.success)
        
        # Get profile info
        info = self.handler.get_profile_info(file_path)
        
        self.assertTrue(info["exists"])
        self.assertTrue(info["readable"])
        self.assertGreater(info["file_size_bytes"], 0)
        self.assertEqual(info["format_version"], "1.0")
        self.assertEqual(info["profile_name"], "Test Profile")
        self.assertEqual(info["parameter_count"], 3)
        self.assertEqual(info["validation_status"], "valid")
    
    def test_get_profile_info_nonexistent_file(self):
        """Test getting info for non-existent file."""
        file_path = os.path.join(self.temp_dir, "nonexistent.json")
        
        info = self.handler.get_profile_info(file_path)
        
        self.assertFalse(info["exists"])
        self.assertFalse(info["readable"])
        self.assertEqual(info["file_size_bytes"], 0)
        self.assertIsNone(info["format_version"])
        self.assertEqual(info["validation_status"], "unknown")
    
    def test_get_profile_info_invalid_file(self):
        """Test getting info for invalid file."""
        file_path = os.path.join(self.temp_dir, "invalid.json")
        
        # Create invalid file
        with open(file_path, 'w') as f:
            f.write("invalid json")
        
        info = self.handler.get_profile_info(file_path)
        
        self.assertTrue(info["exists"])
        self.assertTrue(info["readable"])
        self.assertGreater(info["file_size_bytes"], 0)
        self.assertEqual(info["validation_status"], "invalid_format")
    
    def test_list_profile_files_empty_directory(self):
        """Test listing profile files in empty directory."""
        result = self.handler.list_profile_files(self.temp_dir)
        
        self.assertEqual(len(result), 0)
    
    def test_list_profile_files_with_profiles(self):
        """Test listing profile files in directory with profiles."""
        # Create multiple profile files
        for i in range(3):
            file_path = os.path.join(self.temp_dir, f"profile_{i}.json")
            profile = self.sample_profile.clone(f"Profile {i}")
            save_result = self.handler.save_profile_to_file(profile, file_path)
            self.assertTrue(save_result.success)
        
        # Create non-profile file
        with open(os.path.join(self.temp_dir, "not_profile.txt"), 'w') as f:
            f.write("not a profile")
        
        result = self.handler.list_profile_files(self.temp_dir)
        
        self.assertEqual(len(result), 3)
        profile_names = [info["profile_name"] for info in result]
        self.assertIn("Profile 0", profile_names)
        self.assertIn("Profile 1", profile_names)
        self.assertIn("Profile 2", profile_names)
    
    def test_list_profile_files_recursive(self):
        """Test recursive listing of profile files."""
        # Create nested directory structure
        nested_dir = os.path.join(self.temp_dir, "nested")
        os.makedirs(nested_dir)
        
        # Create profiles in both directories
        file_path1 = os.path.join(self.temp_dir, "profile1.json")
        file_path2 = os.path.join(nested_dir, "profile2.json")
        
        profile1 = self.sample_profile.clone("Profile 1")
        profile2 = self.sample_profile.clone("Profile 2")
        
        self.handler.save_profile_to_file(profile1, file_path1)
        self.handler.save_profile_to_file(profile2, file_path2)
        
        # Test non-recursive
        result_non_recursive = self.handler.list_profile_files(self.temp_dir, recursive=False)
        self.assertEqual(len(result_non_recursive), 1)
        
        # Test recursive
        result_recursive = self.handler.list_profile_files(self.temp_dir, recursive=True)
        self.assertEqual(len(result_recursive), 2)
    
    def test_list_profile_files_nonexistent_directory(self):
        """Test listing profile files in non-existent directory."""
        nonexistent_dir = os.path.join(self.temp_dir, "nonexistent")
        
        result = self.handler.list_profile_files(nonexistent_dir)
        
        self.assertEqual(len(result), 0)
    
    def test_create_backup_success(self):
        """Test successful backup creation."""
        file_path = os.path.join(self.temp_dir, "test_profile.json")
        
        # Create original file
        with open(file_path, 'w') as f:
            json.dump({"test": "data"}, f)
        
        # Create backup
        result = self.handler._create_backup(file_path)
        
        self.assertTrue(result.success)
        self.assertIn("Backup created", result.message)
        
        # Check backup exists
        backup_dir = os.path.join(self.temp_dir, "backups")
        self.assertTrue(os.path.exists(backup_dir))
        backup_files = os.listdir(backup_dir)
        self.assertTrue(any(f.startswith("test_profile_backup_") for f in backup_files))
    
    def test_create_backup_nonexistent_file(self):
        """Test backup creation for non-existent file."""
        file_path = os.path.join(self.temp_dir, "nonexistent.json")
        
        result = self.handler._create_backup(file_path)
        
        self.assertFalse(result.success)
        self.assertIn("does not exist", result.error_message)
    
    def test_verify_saved_file_success(self):
        """Test successful file verification."""
        file_path = os.path.join(self.temp_dir, "test_profile.json")
        
        # Save profile
        save_result = self.handler.save_profile_to_file(self.sample_profile, file_path)
        self.assertTrue(save_result.success)
        
        # Verify file
        result = self.handler._verify_saved_file(file_path, self.sample_profile)
        
        self.assertTrue(result.success)
        self.assertIn("verification successful", result.message)
    
    def test_verify_saved_file_invalid_json(self):
        """Test file verification with invalid JSON."""
        file_path = os.path.join(self.temp_dir, "invalid.json")
        
        # Create invalid JSON file
        with open(file_path, 'w') as f:
            f.write("{ invalid json")
        
        result = self.handler._verify_saved_file(file_path, self.sample_profile)
        
        self.assertFalse(result.success)
        self.assertIn("verification error", result.error_message)
    
    def test_verify_saved_file_name_mismatch(self):
        """Test file verification with name mismatch."""
        file_path = os.path.join(self.temp_dir, "test_profile.json")
        
        # Create profile data with different name
        different_profile_data = self.sample_profile.to_dict()
        different_profile_data["name"] = "Different Name"
        
        with open(file_path, 'w') as f:
            json.dump(different_profile_data, f)
        
        result = self.handler._verify_saved_file(file_path, self.sample_profile)
        
        self.assertFalse(result.success)
        self.assertIn("name mismatch", result.error_message)
    
    def test_validate_profile_data_success(self):
        """Test successful profile data validation."""
        result = self.handler._validate_profile_data(self.sample_profile_data)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_validate_profile_data_not_dict(self):
        """Test profile data validation with non-dictionary input."""
        result = self.handler._validate_profile_data("not a dict")
        
        self.assertFalse(result.is_valid)
        self.assertTrue(any("must be a dictionary" in error for error in result.errors))
    
    def test_validate_profile_data_missing_fields(self):
        """Test profile data validation with missing required fields."""
        incomplete_data = {"name": "Test"}
        
        result = self.handler._validate_profile_data(incomplete_data)
        
        self.assertFalse(result.is_valid)
        self.assertTrue(any("Missing required field" in error for error in result.errors))
    
    def test_validate_profile_data_invalid_types(self):
        """Test profile data validation with invalid field types."""
        invalid_data = self.sample_profile_data.copy()
        invalid_data["name"] = 123  # Should be string
        invalid_data["metadata"] = "not a dict"  # Should be dict
        
        result = self.handler._validate_profile_data(invalid_data)
        
        self.assertFalse(result.is_valid)
        self.assertTrue(any("must be a string" in error for error in result.errors))
        self.assertTrue(any("must be a dictionary" in error for error in result.errors))
    
    def test_validate_profile_data_invalid_timestamps(self):
        """Test profile data validation with invalid timestamp formats."""
        invalid_data = self.sample_profile_data.copy()
        invalid_data["created_at"] = "invalid timestamp"
        invalid_data["modified_at"] = 12345
        
        result = self.handler._validate_profile_data(invalid_data)
        
        self.assertFalse(result.is_valid)
        self.assertTrue(any("Invalid timestamp format" in error for error in result.errors))
    
    def test_get_format_version_from_file_metadata(self):
        """Test format version extraction from file metadata."""
        data_with_file_metadata = self.sample_profile_data.copy()
        data_with_file_metadata["_file_metadata"] = {
            "file_format_version": "2.0"
        }
        
        version = self.handler._get_format_version(data_with_file_metadata)
        
        self.assertEqual(version, "2.0")
    
    def test_get_format_version_from_profile_metadata(self):
        """Test format version extraction from profile metadata."""
        version = self.handler._get_format_version(self.sample_profile_data)
        
        self.assertEqual(version, "1.0")
    
    def test_get_format_version_default(self):
        """Test format version extraction with no version info."""
        data_without_version = {"name": "Test"}
        
        version = self.handler._get_format_version(data_without_version)
        
        self.assertEqual(version, "1.0")
    
    def test_migrate_profile_data_current_version(self):
        """Test migration of current version data."""
        result = self.handler._migrate_profile_data(self.sample_profile_data, "1.0")
        
        self.assertTrue(result.success)
        migrated_data = result.details["migrated_data"]
        self.assertEqual(migrated_data["metadata"]["profile_format_version"], "1.0")
        self.assertIn("_file_metadata", migrated_data)
    
    def test_migrate_profile_data_future_version(self):
        """Test migration of future version data."""
        result = self.handler._migrate_profile_data(self.sample_profile_data, "2.0")
        
        self.assertTrue(result.success)
        migrated_data = result.details["migrated_data"]
        self.assertEqual(migrated_data["metadata"]["profile_format_version"], "1.0")
        self.assertIn("migrated_at", migrated_data["_file_metadata"])


if __name__ == '__main__':
    unittest.main()