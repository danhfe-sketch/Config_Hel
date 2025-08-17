"""
Profile File Handler for the LT32 PRO Universal Profile System.

This module provides comprehensive file I/O operations for universal profiles,
including JSON serialization/deserialization, metadata handling, version information,
timestamps, and profile migration logic for handling format changes.

Requirements addressed:
- 3.2: Save profile to file with proper validation metadata
- 3.3: Load profile from file with validation
- 3.4: Handle profile file format validation and migration
- 5.5: Include version information for future compatibility
"""

import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging

from models.universal_profile import UniversalProfile, ProfileMetadata, ParameterValue
from models.validation_result import ValidationResult
from models.operation_result import ProfileOperationResult, OperationType


@dataclass
class OperationResult:
    """Simple operation result for file operations."""
    operation_type: str
    success: bool
    message: str = ""
    error_message: str = ""
    duration_seconds: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


class ProfileFileError(Exception):
    """Custom exception for profile file operations."""
    pass


class ProfileMigrationError(Exception):
    """Custom exception for profile migration operations."""
    pass


class ProfileFileHandler:
    """
    Handles file I/O operations for universal profiles with JSON format.
    
    This handler provides robust file operations including:
    - JSON serialization/deserialization
    - Profile metadata handling with version information and timestamps
    - Profile migration logic for handling format changes
    - Comprehensive error handling and recovery
    - File validation and backup operations
    """
    
    # Current profile format version
    CURRENT_FORMAT_VERSION = "1.0"
    
    # Supported format versions for migration
    SUPPORTED_VERSIONS = ["1.0"]
    
    # File extension for profile files
    PROFILE_EXTENSION = ".json"
    
    # Backup directory name
    BACKUP_DIR = "backups"
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the profile file handler.
        
        Args:
            logger: Optional logger instance for logging operations
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def save_profile_to_file(self, profile: UniversalProfile, file_path: str, 
                           create_backup: bool = True) -> OperationResult:
        """
        Save a universal profile to a JSON file.
        
        Args:
            profile: Universal profile to save
            file_path: Path where to save the profile file
            create_backup: Whether to create a backup if file exists
            
        Returns:
            OperationResult: Result of the save operation
        """
        operation_start = datetime.now()
        
        try:
            # Ensure file has correct extension
            file_path = self._ensure_profile_extension(file_path)
            
            # Create backup if file exists and backup is requested
            if create_backup and os.path.exists(file_path):
                backup_result = self._create_backup(file_path)
                if not backup_result.success:
                    self.logger.warning(f"Backup creation failed: {backup_result.error_message}")
            
            # Ensure directory exists
            directory = os.path.dirname(file_path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            
            # Update profile metadata before saving
            profile.modified_at = datetime.now()
            profile.metadata.profile_format_version = self.CURRENT_FORMAT_VERSION
            
            # Convert profile to dictionary for saving (without runtime metadata)
            profile_data = profile.to_dict(for_save=True)
            
            # Add file metadata
            file_metadata = {
                "file_format_version": self.CURRENT_FORMAT_VERSION,
                "saved_at": datetime.now().isoformat(),
                "saved_by": "LT32 PRO Universal Profile System"
            }
            profile_data["_file_metadata"] = file_metadata
            
            # Write to temporary file first for atomic operation
            temp_file_path = file_path + ".tmp"
            
            with open(temp_file_path, 'w', encoding='utf-8') as file:
                json.dump(profile_data, file, indent=2, ensure_ascii=False)
            
            # Verify the written file
            verification_result = self._verify_saved_file(temp_file_path, profile)
            if not verification_result.success:
                os.remove(temp_file_path)
                return OperationResult(
                    operation_type="save_profile",
                    success=False,
                    error_message=f"File verification failed: {verification_result.error_message}",
                    duration_seconds=(datetime.now() - operation_start).total_seconds()
                )
            
            # Move temporary file to final location (atomic operation)
            shutil.move(temp_file_path, file_path)
            
            # Log successful save
            self.logger.info(f"Profile '{profile.name}' saved successfully to {file_path}")
            
            return OperationResult(
                operation_type="save_profile",
                success=True,
                message=f"Profile saved to {file_path}",
                duration_seconds=(datetime.now() - operation_start).total_seconds(),
                details={
                    "file_path": file_path,
                    "profile_name": profile.name,
                    "parameter_count": len(profile.parameters),
                    "file_size_bytes": os.path.getsize(file_path)
                }
            )
            
        except PermissionError as e:
            error_msg = f"Permission denied writing to {file_path}: {str(e)}"
            self.logger.error(error_msg)
            return OperationResult(
                operation_type="save_profile",
                success=False,
                error_message=error_msg,
                duration_seconds=(datetime.now() - operation_start).total_seconds()
            )
            
        except OSError as e:
            error_msg = f"OS error writing file {file_path}: {str(e)}"
            self.logger.error(error_msg)
            return OperationResult(
                operation_type="save_profile",
                success=False,
                error_message=error_msg,
                duration_seconds=(datetime.now() - operation_start).total_seconds()
            )
            
        except Exception as e:
            error_msg = f"Unexpected error saving profile: {str(e)}"
            self.logger.error(error_msg)
            return OperationResult(
                operation_type="save_profile",
                success=False,
                error_message=error_msg,
                duration_seconds=(datetime.now() - operation_start).total_seconds()
            )
    
    def load_profile_from_file(self, file_path: str, 
                             auto_migrate: bool = True) -> Tuple[Optional[UniversalProfile], OperationResult]:
        """
        Load a universal profile from a JSON file.
        
        Args:
            file_path: Path to the profile file to load
            auto_migrate: Whether to automatically migrate older format versions
            
        Returns:
            Tuple of (loaded profile or None, operation result)
        """
        operation_start = datetime.now()
        
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                error_msg = f"Profile file not found: {file_path}"
                return None, OperationResult(
                    operation_type="load_profile",
                    success=False,
                    error_message=error_msg,
                    duration_seconds=(datetime.now() - operation_start).total_seconds()
                )
            
            # Check file permissions
            if not os.access(file_path, os.R_OK):
                error_msg = f"Profile file is not readable: {file_path}"
                return None, OperationResult(
                    operation_type="load_profile",
                    success=False,
                    error_message=error_msg,
                    duration_seconds=(datetime.now() - operation_start).total_seconds()
                )
            
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                error_msg = "Profile file is empty"
                return None, OperationResult(
                    operation_type="load_profile",
                    success=False,
                    error_message=error_msg,
                    duration_seconds=(datetime.now() - operation_start).total_seconds()
                )
            
            # Read and parse JSON file
            with open(file_path, 'r', encoding='utf-8') as file:
                profile_data = json.load(file)
            
            # Validate file format
            validation_result = self._validate_profile_data(profile_data)
            if not validation_result.is_valid:
                error_msg = f"Invalid profile format: {'; '.join(validation_result.errors)}"
                return None, OperationResult(
                    operation_type="load_profile",
                    success=False,
                    error_message=error_msg,
                    duration_seconds=(datetime.now() - operation_start).total_seconds(),
                    details={"validation_errors": validation_result.errors}
                )
            
            # Check format version and migrate if needed
            file_format_version = self._get_format_version(profile_data)
            migration_performed = False
            
            if file_format_version != self.CURRENT_FORMAT_VERSION:
                if auto_migrate:
                    migration_result = self._migrate_profile_data(profile_data, file_format_version)
                    if migration_result.success:
                        profile_data = migration_result.details["migrated_data"]
                        migration_performed = True
                        self.logger.info(f"Profile migrated from version {file_format_version} to {self.CURRENT_FORMAT_VERSION}")
                    else:
                        error_msg = f"Profile migration failed: {migration_result.error_message}"
                        return None, OperationResult(
                            operation_type="load_profile",
                            success=False,
                            error_message=error_msg,
                            duration_seconds=(datetime.now() - operation_start).total_seconds()
                        )
                else:
                    self.logger.warning(f"Profile format version {file_format_version} differs from current {self.CURRENT_FORMAT_VERSION}")
            
            # Create profile from data
            profile = UniversalProfile.from_dict(profile_data)
            
            # Log successful load
            self.logger.info(f"Profile '{profile.name}' loaded successfully from {file_path}")
            
            return profile, OperationResult(
                operation_type="load_profile",
                success=True,
                message=f"Profile loaded from {file_path}",
                duration_seconds=(datetime.now() - operation_start).total_seconds(),
                details={
                    "file_path": file_path,
                    "profile_name": profile.name,
                    "parameter_count": len(profile.parameters),
                    "file_size_bytes": file_size,
                    "migration_performed": migration_performed,
                    "format_version": file_format_version
                }
            )
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON format in profile file: {str(e)}"
            self.logger.error(error_msg)
            return None, OperationResult(
                operation_type="load_profile",
                success=False,
                error_message=error_msg,
                duration_seconds=(datetime.now() - operation_start).total_seconds()
            )
            
        except UnicodeDecodeError as e:
            error_msg = f"File encoding error: {str(e)}"
            self.logger.error(error_msg)
            return None, OperationResult(
                operation_type="load_profile",
                success=False,
                error_message=error_msg,
                duration_seconds=(datetime.now() - operation_start).total_seconds()
            )
            
        except Exception as e:
            error_msg = f"Unexpected error loading profile: {str(e)}"
            self.logger.error(error_msg)
            return None, OperationResult(
                operation_type="load_profile",
                success=False,
                error_message=error_msg,
                duration_seconds=(datetime.now() - operation_start).total_seconds()
            )
    
    def validate_profile_file(self, file_path: str) -> ValidationResult:
        """
        Validate a profile file without loading it completely.
        
        Args:
            file_path: Path to the profile file to validate
            
        Returns:
            ValidationResult: Validation result with detailed information
        """
        result = ValidationResult(is_valid=True)
        
        try:
            # Check file existence and permissions
            if not os.path.exists(file_path):
                result.add_error(f"Profile file not found: {file_path}")
                return result
            
            if not os.access(file_path, os.R_OK):
                result.add_error(f"Profile file is not readable: {file_path}")
                return result
            
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                result.add_error("Profile file is empty")
                return result
            
            if file_size > 10 * 1024 * 1024:  # 10MB limit
                result.add_warning(f"Profile file is very large: {file_size} bytes")
            
            # Validate JSON format
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    profile_data = json.load(file)
            except json.JSONDecodeError as e:
                result.add_error(f"Invalid JSON format: {str(e)}")
                return result
            except UnicodeDecodeError as e:
                result.add_error(f"File encoding error: {str(e)}")
                return result
            
            # Validate profile data structure
            data_validation = self._validate_profile_data(profile_data)
            result.errors.extend(data_validation.errors)
            result.warnings.extend(data_validation.warnings)
            
            # Check format version
            format_version = self._get_format_version(profile_data)
            if format_version not in self.SUPPORTED_VERSIONS:
                result.add_error(f"Unsupported profile format version: {format_version}")
            elif format_version != self.CURRENT_FORMAT_VERSION:
                result.add_warning(f"Profile format version {format_version} is older than current {self.CURRENT_FORMAT_VERSION}")
            
            # Validate required fields
            required_fields = ["name", "version", "created_at", "modified_at", "metadata", "parameters"]
            for field in required_fields:
                if field not in profile_data:
                    result.add_error(f"Missing required field: {field}")
            
            # Validate metadata structure
            if "metadata" in profile_data:
                metadata = profile_data["metadata"]
                if not isinstance(metadata, dict):
                    result.add_error("Metadata must be a dictionary")
                else:
                    required_metadata_fields = ["parameter_spec_version", "device_model", "profile_format_version"]
                    for field in required_metadata_fields:
                        if field not in metadata:
                            result.add_warning(f"Missing metadata field: {field}")
            
            # Validate parameters structure
            if "parameters" in profile_data:
                parameters = profile_data["parameters"]
                if not isinstance(parameters, dict):
                    result.add_error("Parameters must be a dictionary")
                else:
                    # Validate parameter structure
                    for param_name, param_data in parameters.items():
                        if not isinstance(param_data, dict):
                            result.add_error(f"Parameter '{param_name}' data must be a dictionary")
                            continue
                        
                        required_param_fields = ["value", "source", "timestamp"]
                        for field in required_param_fields:
                            if field not in param_data:
                                result.add_warning(f"Parameter '{param_name}' missing field: {field}")
            
        except Exception as e:
            result.add_error(f"Unexpected error during validation: {str(e)}")
        
        return result 
   
    def migrate_profile_file(self, file_path: str, backup: bool = True) -> OperationResult:
        """
        Migrate a profile file to the current format version.
        
        Args:
            file_path: Path to the profile file to migrate
            backup: Whether to create a backup before migration
            
        Returns:
            OperationResult: Result of the migration operation
        """
        operation_start = datetime.now()
        
        try:
            # Load the profile
            profile, load_result = self.load_profile_from_file(file_path, auto_migrate=False)
            if not load_result.success:
                return OperationResult(
                    operation_type="migrate_profile",
                    success=False,
                    error_message=f"Failed to load profile for migration: {load_result.error_message}",
                    duration_seconds=(datetime.now() - operation_start).total_seconds()
                )
            
            # Check if migration is needed
            with open(file_path, 'r', encoding='utf-8') as file:
                profile_data = json.load(file)
            
            current_version = self._get_format_version(profile_data)
            if current_version == self.CURRENT_FORMAT_VERSION:
                return OperationResult(
                    operation_type="migrate_profile",
                    success=True,
                    message="Profile is already at current format version",
                    duration_seconds=(datetime.now() - operation_start).total_seconds(),
                    details={"format_version": current_version}
                )
            
            # Create backup if requested
            if backup:
                backup_result = self._create_backup(file_path)
                if not backup_result.success:
                    self.logger.warning(f"Backup creation failed: {backup_result.error_message}")
            
            # Perform migration
            migration_result = self._migrate_profile_data(profile_data, current_version)
            if not migration_result.success:
                return OperationResult(
                    operation_type="migrate_profile",
                    success=False,
                    error_message=f"Migration failed: {migration_result.error_message}",
                    duration_seconds=(datetime.now() - operation_start).total_seconds()
                )
            
            # Create migrated profile
            migrated_data = migration_result.details["migrated_data"]
            migrated_profile = UniversalProfile.from_dict(migrated_data)
            
            # Save migrated profile
            save_result = self.save_profile_to_file(migrated_profile, file_path, create_backup=False)
            if not save_result.success:
                return OperationResult(
                    operation_type="migrate_profile",
                    success=False,
                    error_message=f"Failed to save migrated profile: {save_result.error_message}",
                    duration_seconds=(datetime.now() - operation_start).total_seconds()
                )
            
            self.logger.info(f"Profile migrated from version {current_version} to {self.CURRENT_FORMAT_VERSION}")
            
            return OperationResult(
                operation_type="migrate_profile",
                success=True,
                message=f"Profile migrated from version {current_version} to {self.CURRENT_FORMAT_VERSION}",
                duration_seconds=(datetime.now() - operation_start).total_seconds(),
                details={
                    "old_version": current_version,
                    "new_version": self.CURRENT_FORMAT_VERSION,
                    "backup_created": backup
                }
            )
            
        except Exception as e:
            error_msg = f"Unexpected error during migration: {str(e)}"
            self.logger.error(error_msg)
            return OperationResult(
                operation_type="migrate_profile",
                success=False,
                error_message=error_msg,
                duration_seconds=(datetime.now() - operation_start).total_seconds()
            )
    
    def get_profile_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get basic information about a profile file without loading it completely.
        
        Args:
            file_path: Path to the profile file
            
        Returns:
            Dict[str, Any]: Profile information dictionary
        """
        info = {
            "file_path": file_path,
            "exists": False,
            "readable": False,
            "file_size_bytes": 0,
            "format_version": None,
            "profile_name": None,
            "created_at": None,
            "modified_at": None,
            "parameter_count": 0,
            "validation_status": "unknown"
        }
        
        try:
            if os.path.exists(file_path):
                info["exists"] = True
                info["readable"] = os.access(file_path, os.R_OK)
                info["file_size_bytes"] = os.path.getsize(file_path)
                
                if info["readable"] and info["file_size_bytes"] > 0:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as file:
                            profile_data = json.load(file)
                        
                        info["format_version"] = self._get_format_version(profile_data)
                        info["profile_name"] = profile_data.get("name")
                        info["created_at"] = profile_data.get("created_at")
                        info["modified_at"] = profile_data.get("modified_at")
                        
                        if "parameters" in profile_data and isinstance(profile_data["parameters"], dict):
                            info["parameter_count"] = len(profile_data["parameters"])
                        
                        # Quick validation
                        validation_result = self._validate_profile_data(profile_data)
                        if validation_result.is_valid:
                            info["validation_status"] = "valid"
                        elif validation_result.errors:
                            info["validation_status"] = "invalid"
                        else:
                            info["validation_status"] = "warnings"
                            
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        info["validation_status"] = "invalid_format"
                    except Exception:
                        info["validation_status"] = "error"
        
        except Exception:
            info["validation_status"] = "error"
        
        return info
    
    def list_profile_files(self, directory: str, recursive: bool = False) -> List[Dict[str, Any]]:
        """
        List all profile files in a directory.
        
        Args:
            directory: Directory to search for profile files
            recursive: Whether to search subdirectories recursively
            
        Returns:
            List[Dict[str, Any]]: List of profile file information dictionaries
        """
        profile_files = []
        
        try:
            if not os.path.exists(directory):
                return profile_files
            
            if recursive:
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        if file.endswith(self.PROFILE_EXTENSION):
                            file_path = os.path.join(root, file)
                            profile_info = self.get_profile_info(file_path)
                            profile_files.append(profile_info)
            else:
                for file in os.listdir(directory):
                    if file.endswith(self.PROFILE_EXTENSION):
                        file_path = os.path.join(directory, file)
                        if os.path.isfile(file_path):
                            profile_info = self.get_profile_info(file_path)
                            profile_files.append(profile_info)
        
        except Exception as e:
            self.logger.error(f"Error listing profile files in {directory}: {str(e)}")
        
        return profile_files
    
    def _ensure_profile_extension(self, file_path: str) -> str:
        """Ensure file path has the correct profile extension."""
        if not file_path.endswith(self.PROFILE_EXTENSION):
            return file_path + self.PROFILE_EXTENSION
        return file_path
    
    def _create_backup(self, file_path: str) -> OperationResult:
        """Create a backup of an existing profile file."""
        try:
            if not os.path.exists(file_path):
                return OperationResult(
                    operation_type="create_backup",
                    success=False,
                    error_message="File does not exist"
                )
            
            # Create backup directory
            directory = os.path.dirname(file_path)
            backup_dir = os.path.join(directory, self.BACKUP_DIR)
            os.makedirs(backup_dir, exist_ok=True)
            
            # Generate backup filename with timestamp
            filename = os.path.basename(file_path)
            name, ext = os.path.splitext(filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{name}_backup_{timestamp}{ext}"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # Copy file to backup location
            shutil.copy2(file_path, backup_path)
            
            return OperationResult(
                operation_type="create_backup",
                success=True,
                message=f"Backup created at {backup_path}",
                details={"backup_path": backup_path}
            )
            
        except Exception as e:
            return OperationResult(
                operation_type="create_backup",
                success=False,
                error_message=f"Backup creation failed: {str(e)}"
            )
    
    def _verify_saved_file(self, file_path: str, original_profile: UniversalProfile) -> OperationResult:
        """Verify that a saved file can be loaded and matches the original profile."""
        try:
            # Try to load the saved file
            with open(file_path, 'r', encoding='utf-8') as file:
                saved_data = json.load(file)
            
            # Basic structure validation
            validation_result = self._validate_profile_data(saved_data)
            if not validation_result.is_valid:
                return OperationResult(
                    operation_type="verify_file",
                    success=False,
                    error_message=f"Saved file validation failed: {'; '.join(validation_result.errors)}"
                )
            
            # Create profile from saved data and compare key fields
            loaded_profile = UniversalProfile.from_dict(saved_data)
            
            if loaded_profile.name != original_profile.name:
                return OperationResult(
                    operation_type="verify_file",
                    success=False,
                    error_message="Profile name mismatch after save"
                )
            
            if len(loaded_profile.parameters) != len(original_profile.parameters):
                return OperationResult(
                    operation_type="verify_file",
                    success=False,
                    error_message="Parameter count mismatch after save"
                )
            
            return OperationResult(
                operation_type="verify_file",
                success=True,
                message="File verification successful"
            )
            
        except Exception as e:
            return OperationResult(
                operation_type="verify_file",
                success=False,
                error_message=f"File verification error: {str(e)}"
            )
    
    def _validate_profile_data(self, profile_data: Dict[str, Any]) -> ValidationResult:
        """Validate the structure of profile data."""
        result = ValidationResult(is_valid=True)
        
        if not isinstance(profile_data, dict):
            result.add_error("Profile data must be a dictionary")
            return result
        
        # Check required top-level fields
        required_fields = ["name", "version", "created_at", "modified_at", "metadata", "parameters"]
        for field in required_fields:
            if field not in profile_data:
                result.add_error(f"Missing required field: {field}")
        
        # Validate field types
        if "name" in profile_data and not isinstance(profile_data["name"], str):
            result.add_error("Profile name must be a string")
        
        if "version" in profile_data and not isinstance(profile_data["version"], str):
            result.add_error("Profile version must be a string")
        
        if "metadata" in profile_data and not isinstance(profile_data["metadata"], dict):
            result.add_error("Profile metadata must be a dictionary")
        
        if "parameters" in profile_data and not isinstance(profile_data["parameters"], dict):
            result.add_error("Profile parameters must be a dictionary")
        
        # Validate timestamp formats
        for timestamp_field in ["created_at", "modified_at"]:
            if timestamp_field in profile_data:
                try:
                    datetime.fromisoformat(profile_data[timestamp_field])
                except (ValueError, TypeError):
                    result.add_error(f"Invalid timestamp format for {timestamp_field}")
        
        return result
    
    def _get_format_version(self, profile_data: Dict[str, Any]) -> str:
        """Extract format version from profile data."""
        # Check file metadata first
        if "_file_metadata" in profile_data:
            file_metadata = profile_data["_file_metadata"]
            if isinstance(file_metadata, dict) and "file_format_version" in file_metadata:
                return file_metadata["file_format_version"]
        
        # Check profile metadata
        if "metadata" in profile_data:
            metadata = profile_data["metadata"]
            if isinstance(metadata, dict) and "profile_format_version" in metadata:
                return metadata["profile_format_version"]
        
        # Default to version 1.0 if not found
        return "1.0"
    
    def _migrate_profile_data(self, profile_data: Dict[str, Any], from_version: str) -> OperationResult:
        """
        Migrate profile data from an older format version to the current version.
        
        Args:
            profile_data: Profile data to migrate
            from_version: Source format version
            
        Returns:
            OperationResult: Migration result with migrated data
        """
        try:
            migrated_data = profile_data.copy()
            migration_actions = []
            
            # Migration logic for different versions
            if from_version == "1.0":
                # Already current version, no migration needed
                pass
            else:
                # Future migration logic would go here
                # For now, we only support version 1.0
                migration_actions.append(f"No migration needed from version {from_version}")
            
            # Update format version in metadata
            if "metadata" not in migrated_data:
                migrated_data["metadata"] = {}
            
            if not isinstance(migrated_data["metadata"], dict):
                migrated_data["metadata"] = {}
            
            migrated_data["metadata"]["profile_format_version"] = self.CURRENT_FORMAT_VERSION
            
            # Add file metadata
            file_metadata = {
                "file_format_version": self.CURRENT_FORMAT_VERSION,
                "migrated_at": datetime.now().isoformat(),
                "migrated_from_version": from_version,
                "migration_actions": migration_actions
            }
            migrated_data["_file_metadata"] = file_metadata
            
            # Update modified timestamp
            migrated_data["modified_at"] = datetime.now().isoformat()
            
            return OperationResult(
                operation_type="migrate_profile_data",
                success=True,
                message=f"Profile data migrated from version {from_version} to {self.CURRENT_FORMAT_VERSION}",
                details={
                    "migrated_data": migrated_data,
                    "migration_actions": migration_actions,
                    "from_version": from_version,
                    "to_version": self.CURRENT_FORMAT_VERSION
                }
            )
            
        except Exception as e:
            return OperationResult(
                operation_type="migrate_profile_data",
                success=False,
                error_message=f"Migration failed: {str(e)}"
            )