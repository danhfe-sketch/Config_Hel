"""
Profile Migration Utilities - Comprehensive migration tools for profile formats.

This module provides utilities for migrating legacy profile formats including:
1. Automatic detection of profile format versions
2. Migration of legacy profile formats to current standard
3. Backup and restore functionality for profile migrations
4. Validation tools for verifying migration accuracy
5. Batch migration operations for multiple profiles
"""

import os
import json
import shutil
import logging
import configparser
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union, Tuple
from pathlib import Path
from enum import Enum

# Import existing components
from services.profile_file_handler import (
    ProfileFileHandler, ProfileData, ProfileMetadata, ValidationInfo,
    ProfileFileResult, WriteResult, BackupResult
)
from services.profile_converter import ProfileConverter, ConversionResult, MigrationResult
from services.profile_validator import ProfileValidator, ValidationResult


class MigrationStatus(Enum):
    """Status of migration operations."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class BackupStrategy(Enum):
    """Backup strategies for migration operations."""
    NONE = "none"
    SIMPLE = "simple"
    TIMESTAMPED = "timestamped"
    VERSIONED = "versioned"


@dataclass
class MigrationConfig:
    """Configuration for migration operations."""
    backup_strategy: BackupStrategy = BackupStrategy.TIMESTAMPED
    validate_before_migration: bool = True
    validate_after_migration: bool = True
    preserve_original_timestamps: bool = True
    create_migration_log: bool = True
    skip_already_migrated: bool = True
    target_format_version: str = "1.0"


@dataclass
class ProfileVersionInfo:
    """Information about a profile's version and format."""
    file_path: str
    detected_version: str
    format_confidence: float  # 0.0 to 1.0
    version_indicators: List[str]
    needs_migration: bool
    migration_complexity: str  # 'simple', 'moderate', 'complex'
    estimated_migration_time: float  # seconds


@dataclass
class MigrationOperation:
    """Details of a single migration operation."""
    source_file: str
    target_file: str
    backup_file: Optional[str]
    source_version: str
    target_version: str
    status: MigrationStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    migration_log: List[str] = field(default_factory=list)
    validation_results: Optional[ValidationResult] = None


@dataclass
class BatchMigrationResult:
    """Result of batch migration operations."""
    total_files: int
    successful_migrations: int
    failed_migrations: int
    skipped_files: int
    migration_operations: List[MigrationOperation] = field(default_factory=list)
    overall_status: MigrationStatus = MigrationStatus.NOT_STARTED
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    summary_report: str = ""


@dataclass
class RestoreOperation:
    """Details of a restore operation."""
    backup_file: str
    target_file: str
    restore_timestamp: datetime
    success: bool
    error_message: Optional[str] = None


class ProfileMigrationUtilities:
    """
    Comprehensive migration tools for profile formats.
    
    Features:
    - Automatic detection of profile format versions
    - Migration of legacy profile formats to current standard
    - Backup and restore functionality for profile migrations
    - Validation tools for verifying migration accuracy
    - Batch migration operations for multiple profiles
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the profile migration utilities.
        
        Args:
            logger: Optional logger instance for detailed logging
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize component dependencies
        self.file_handler = ProfileFileHandler(logger)
        self.converter = ProfileConverter(logger)
        self.validator = ProfileValidator(logger)
        
        # Migration configuration
        self.default_config = MigrationConfig()
        
        # Version detection patterns
        self._init_version_detection_patterns()
        
        # Migration complexity rules
        self._init_migration_complexity_rules()
        
        self.logger.info("ProfileMigrationUtilities initialized")

    def detect_profile_version(self, file_path: str) -> ProfileVersionInfo:
        """
        Automatically detect the format version of a profile file.
        
        Args:
            file_path: Path to the profile file to analyze
            
        Returns:
            ProfileVersionInfo with detected version and migration requirements
        """
        self.logger.info(f"Detecting profile version for: {file_path}")
        
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                return ProfileVersionInfo(
                    file_path=file_path,
                    detected_version="unknown",
                    format_confidence=0.0,
                    version_indicators=["File not found"],
                    needs_migration=False,
                    migration_complexity="impossible",
                    estimated_migration_time=0.0
                )
            
            # Read file content for analysis
            config, error_msg = self.file_handler.read_ini_file(file_path)
            
            # Create file_result-like object for compatibility
            class FileResult:
                def __init__(self, success, config=None, error_message=None):
                    self.success = success
                    self.config = config
                    self.error_message = error_message
            
            if config is not None:
                file_result = FileResult(True, config)
            else:
                file_result = FileResult(False, error_message=error_msg)
            
            if not file_result.success:
                return ProfileVersionInfo(
                    file_path=file_path,
                    detected_version="unknown",
                    format_confidence=0.0,
                    version_indicators=[f"Read error: {file_result.error_message}"],
                    needs_migration=False,
                    migration_complexity="impossible",
                    estimated_migration_time=0.0
                )
            
            # Analyze profile data for version indicators
            profile_data = file_result.profile_data
            version_indicators = []
            confidence_score = 0.0
            detected_version = "unknown"
            
            # Check explicit version information
            if profile_data.metadata.app_version:
                version_indicators.append(f"App version: {profile_data.metadata.app_version}")
                detected_version = profile_data.metadata.app_version
                confidence_score += 0.4
            
            if profile_data.format_version:
                version_indicators.append(f"Format version: {profile_data.format_version}")
                detected_version = profile_data.format_version
                confidence_score += 0.4
            
            # Analyze file structure for version clues
            structure_analysis = self._analyze_file_structure(file_path)
            version_indicators.extend(structure_analysis['indicators'])
            confidence_score += structure_analysis['confidence_boost']
            
            if structure_analysis['suggested_version'] != "unknown":
                detected_version = structure_analysis['suggested_version']
            
            # Analyze parameter patterns
            parameter_analysis = self._analyze_parameter_patterns(profile_data.device_parameters)
            version_indicators.extend(parameter_analysis['indicators'])
            confidence_score += parameter_analysis['confidence_boost']
            
            if parameter_analysis['suggested_version'] != "unknown":
                detected_version = parameter_analysis['suggested_version']
            
            # Determine if migration is needed
            needs_migration = self._needs_migration(detected_version)
            
            # Assess migration complexity
            migration_complexity = self._assess_migration_complexity(
                detected_version, profile_data.device_parameters
            )
            
            # Estimate migration time
            estimated_time = self._estimate_migration_time(
                migration_complexity, len(profile_data.device_parameters)
            )
            
            # Ensure confidence is within bounds
            confidence_score = min(1.0, max(0.0, confidence_score))
            
            self.logger.info(f"Detected version {detected_version} with {confidence_score:.2f} confidence")
            
            return ProfileVersionInfo(
                file_path=file_path,
                detected_version=detected_version,
                format_confidence=confidence_score,
                version_indicators=version_indicators,
                needs_migration=needs_migration,
                migration_complexity=migration_complexity,
                estimated_migration_time=estimated_time
            )
            
        except Exception as e:
            error_msg = f"Error detecting profile version: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return ProfileVersionInfo(
                file_path=file_path,
                detected_version="unknown",
                format_confidence=0.0,
                version_indicators=[f"Detection error: {error_msg}"],
                needs_migration=False,
                migration_complexity="unknown",
                estimated_migration_time=0.0
            )

    def migrate_profile(self, source_file: str, target_file: Optional[str] = None,
                       config: Optional[MigrationConfig] = None) -> MigrationOperation:
        """
        Migrate a single profile file to the current format.
        
        Args:
            source_file: Path to the source profile file
            target_file: Optional target file path (defaults to source_file)
            config: Optional migration configuration
            
        Returns:
            MigrationOperation with detailed migration results
        """
        config = config or self.default_config
        target_file = target_file or source_file
        
        self.logger.info(f"Migrating profile: {source_file} -> {target_file}")
        
        operation = MigrationOperation(
            source_file=source_file,
            target_file=target_file,
            backup_file=None,
            source_version="unknown",
            target_version=config.target_format_version,
            status=MigrationStatus.NOT_STARTED,
            start_time=datetime.now()
        )
        
        try:
            operation.status = MigrationStatus.IN_PROGRESS
            operation.migration_log.append(f"Starting migration at {operation.start_time}")
            
            # Detect source version
            version_info = self.detect_profile_version(source_file)
            operation.source_version = version_info.detected_version
            operation.migration_log.append(f"Detected source version: {version_info.detected_version}")
            
            # Check if migration is needed
            if not version_info.needs_migration:
                operation.status = MigrationStatus.SKIPPED
                operation.migration_log.append("Migration not needed - profile is already current format")
                operation.end_time = datetime.now()
                return operation
            
            # Skip if already migrated and configured to do so
            if config.skip_already_migrated and self._is_already_migrated(source_file):
                operation.status = MigrationStatus.SKIPPED
                operation.migration_log.append("Skipping - profile already migrated")
                operation.end_time = datetime.now()
                return operation
            
            # Validate before migration if configured
            if config.validate_before_migration:
                operation.migration_log.append("Validating source profile")
                validation_result = self._validate_source_profile(source_file)
                if not validation_result.is_valid:
                    critical_errors = [e for e in validation_result.errors 
                                     if e.severity.value in ['critical', 'error']]
                    if critical_errors:
                        operation.status = MigrationStatus.FAILED
                        operation.error_message = f"Source validation failed: {len(critical_errors)} critical errors"
                        operation.end_time = datetime.now()
                        return operation
            
            # Create backup if configured
            if config.backup_strategy != BackupStrategy.NONE:
                backup_result = self._create_migration_backup(source_file, config.backup_strategy)
                if backup_result.success:
                    operation.backup_file = backup_result.backup_path
                    operation.migration_log.append(f"Created backup: {backup_result.backup_path}")
                else:
                    operation.migration_log.append(f"Backup failed: {backup_result.error_message}")
            
            # Perform the actual migration
            migration_result = self._perform_migration(source_file, target_file, config)
            
            if not migration_result.success:
                operation.status = MigrationStatus.FAILED
                operation.error_message = f"Migration failed: {migration_result.errors[0].error_message if migration_result.errors else 'Unknown error'}"
                operation.migration_log.extend([f"Error: {e.error_message}" for e in migration_result.errors])
                operation.end_time = datetime.now()
                return operation
            
            operation.migration_log.extend(migration_result.migration_log)
            
            # Validate after migration if configured
            if config.validate_after_migration:
                operation.migration_log.append("Validating migrated profile")
                validation_result = self._validate_migrated_profile(target_file)
                operation.validation_results = validation_result
                
                if not validation_result.is_valid:
                    critical_errors = [e for e in validation_result.errors 
                                     if e.severity.value in ['critical', 'error']]
                    if critical_errors:
                        operation.status = MigrationStatus.FAILED
                        operation.error_message = f"Post-migration validation failed: {len(critical_errors)} critical errors"
                        operation.end_time = datetime.now()
                        return operation
            
            # Migration successful
            operation.status = MigrationStatus.COMPLETED
            operation.migration_log.append("Migration completed successfully")
            operation.end_time = datetime.now()
            
            # Create migration log file if configured
            if config.create_migration_log:
                self._create_migration_log_file(operation)
            
            self.logger.info(f"Successfully migrated profile: {source_file}")
            return operation
            
        except Exception as e:
            error_msg = f"Unexpected error during migration: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            operation.status = MigrationStatus.FAILED
            operation.error_message = error_msg
            operation.migration_log.append(error_msg)
            operation.end_time = datetime.now()
            return operation

    def batch_migrate_profiles(self, source_directory: str, 
                             target_directory: Optional[str] = None,
                             file_pattern: str = "*.lt32config",
                             config: Optional[MigrationConfig] = None) -> BatchMigrationResult:
        """
        Migrate multiple profile files in batch.
        
        Args:
            source_directory: Directory containing source profile files
            target_directory: Optional target directory (defaults to source_directory)
            file_pattern: File pattern to match (e.g., "*.lt32config")
            config: Optional migration configuration
            
        Returns:
            BatchMigrationResult with comprehensive batch operation results
        """
        config = config or self.default_config
        target_directory = target_directory or source_directory
        
        self.logger.info(f"Starting batch migration: {source_directory} -> {target_directory}")
        
        result = BatchMigrationResult(
            total_files=0,
            successful_migrations=0,
            failed_migrations=0,
            skipped_files=0,
            overall_status=MigrationStatus.IN_PROGRESS,
            start_time=datetime.now()
        )
        
        try:
            # Find all matching profile files
            source_path = Path(source_directory)
            if not source_path.exists():
                result.overall_status = MigrationStatus.FAILED
                result.summary_report = f"Source directory not found: {source_directory}"
                result.end_time = datetime.now()
                return result
            
            profile_files = list(source_path.glob(file_pattern))
            result.total_files = len(profile_files)
            
            if result.total_files == 0:
                result.overall_status = MigrationStatus.COMPLETED
                result.summary_report = f"No files matching pattern '{file_pattern}' found in {source_directory}"
                result.end_time = datetime.now()
                return result
            
            self.logger.info(f"Found {result.total_files} profile files to migrate")
            
            # Ensure target directory exists
            target_path = Path(target_directory)
            target_path.mkdir(parents=True, exist_ok=True)
            
            # Process each file
            for source_file in profile_files:
                try:
                    # Determine target file path
                    if source_directory == target_directory:
                        target_file = str(source_file)  # In-place migration
                    else:
                        target_file = str(target_path / source_file.name)
                    
                    # Perform migration
                    migration_op = self.migrate_profile(str(source_file), target_file, config)
                    result.migration_operations.append(migration_op)
                    
                    # Update counters
                    if migration_op.status == MigrationStatus.COMPLETED:
                        result.successful_migrations += 1
                    elif migration_op.status == MigrationStatus.FAILED:
                        result.failed_migrations += 1
                    elif migration_op.status == MigrationStatus.SKIPPED:
                        result.skipped_files += 1
                    
                except Exception as e:
                    self.logger.error(f"Error processing file {source_file}: {str(e)}")
                    result.failed_migrations += 1
                    
                    # Create failed operation record
                    failed_op = MigrationOperation(
                        source_file=str(source_file),
                        target_file=str(target_file) if 'target_file' in locals() else str(source_file),
                        backup_file=None,
                        source_version="unknown",
                        target_version=config.target_format_version,
                        status=MigrationStatus.FAILED,
                        start_time=datetime.now(),
                        end_time=datetime.now(),
                        error_message=f"Processing error: {str(e)}"
                    )
                    result.migration_operations.append(failed_op)
            
            # Determine overall status
            if result.failed_migrations == 0:
                result.overall_status = MigrationStatus.COMPLETED
            elif result.successful_migrations > 0:
                result.overall_status = MigrationStatus.COMPLETED  # Partial success
            else:
                result.overall_status = MigrationStatus.FAILED
            
            result.end_time = datetime.now()
            
            # Generate summary report
            result.summary_report = self._generate_batch_summary_report(result)
            
            self.logger.info(f"Batch migration completed: {result.successful_migrations}/{result.total_files} successful")
            return result
            
        except Exception as e:
            error_msg = f"Batch migration error: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            result.overall_status = MigrationStatus.FAILED
            result.summary_report = error_msg
            result.end_time = datetime.now()
            return result

    def restore_from_backup(self, backup_file: str, target_file: str) -> RestoreOperation:
        """
        Restore a profile from a backup file.
        
        Args:
            backup_file: Path to the backup file
            target_file: Path where the restored file should be placed
            
        Returns:
            RestoreOperation with restore results
        """
        self.logger.info(f"Restoring from backup: {backup_file} -> {target_file}")
        
        operation = RestoreOperation(
            backup_file=backup_file,
            target_file=target_file,
            restore_timestamp=datetime.now(),
            success=False
        )
        
        try:
            # Validate backup file exists
            if not os.path.exists(backup_file):
                operation.error_message = f"Backup file not found: {backup_file}"
                return operation
            
            # Validate backup file is readable
            access_result = self.file_handler.validate_file_access(backup_file)
            if not access_result.can_read:
                operation.error_message = f"Cannot read backup file: {backup_file}"
                return operation
            
            # Create target directory if needed
            target_dir = os.path.dirname(target_file)
            if target_dir and not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
            
            # Copy backup to target location
            shutil.copy2(backup_file, target_file)
            
            # Verify restore was successful
            if not os.path.exists(target_file):
                operation.error_message = "Restore failed - target file was not created"
                return operation
            
            # Verify file sizes match
            backup_size = os.path.getsize(backup_file)
            target_size = os.path.getsize(target_file)
            
            if backup_size != target_size:
                operation.error_message = f"Restore verification failed - size mismatch ({backup_size} vs {target_size})"
                return operation
            
            operation.success = True
            self.logger.info(f"Successfully restored from backup: {backup_file}")
            return operation
            
        except Exception as e:
            error_msg = f"Error during restore operation: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            operation.error_message = error_msg
            return operation

    def verify_migration_accuracy(self, original_file: str, migrated_file: str) -> ValidationResult:
        """
        Verify the accuracy of a migration by comparing original and migrated profiles.
        
        Args:
            original_file: Path to the original profile file
            migrated_file: Path to the migrated profile file
            
        Returns:
            ValidationResult with accuracy verification details
        """
        self.logger.info(f"Verifying migration accuracy: {original_file} -> {migrated_file}")
        
        try:
            # Read both files
            original_config, original_error = self.file_handler.read_ini_file(original_file)
            migrated_config, migrated_error = self.file_handler.read_ini_file(migrated_file)
            
            # Create file_result-like objects for compatibility
            class FileResult:
                def __init__(self, success, config=None, error_message=None):
                    self.success = success
                    self.config = config
                    self.error_message = error_message
            
            original_result = FileResult(original_config is not None, original_config, original_error)
            migrated_result = FileResult(migrated_config is not None, migrated_config, migrated_error)
            
            if not original_result.success:
                return ValidationResult(
                    is_valid=False,
                    errors=[],
                    warnings=[],
                    suggestions=[],
                    validation_summary=None
                )
            
            if not migrated_result.success:
                return ValidationResult(
                    is_valid=False,
                    errors=[],
                    warnings=[],
                    suggestions=[],
                    validation_summary=None
                )
            
            # Compare parameter values
            original_params = original_result.profile_data.device_parameters
            migrated_params = migrated_result.profile_data.device_parameters
            
            # Use validator to check migrated file structure
            validation_result = self.validator.validate_profile_structure(migrated_result.profile_data)
            
            # Add parameter comparison results
            comparison_errors = self._compare_parameter_values(original_params, migrated_params)
            validation_result.errors.extend(comparison_errors)
            
            # Update validation status based on comparison
            if comparison_errors:
                validation_result.is_valid = False
            
            self.logger.info(f"Migration accuracy verification completed: {'PASSED' if validation_result.is_valid else 'FAILED'}")
            return validation_result
            
        except Exception as e:
            error_msg = f"Error verifying migration accuracy: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return ValidationResult(
                is_valid=False,
                errors=[],
                warnings=[],
                suggestions=[],
                validation_summary=None
            )

    def _init_version_detection_patterns(self):
        """Initialize patterns for detecting profile versions."""
        self.version_patterns = {
            '0.9': {
                'section_names': ['ProfileInfo', 'APNConfig', 'ServerConfig'],
                'parameter_names': ['apn_username', 'apn_pwd', 'server_address'],
                'format_indicators': ['legacy_format', 'old_style']
            },
            '1.0': {
                'section_names': ['Profile_Info', 'APN_Configuration', 'Server_Configuration'],
                'parameter_names': ['apn_user', 'apn_password', 'server_ip'],
                'format_indicators': ['standardized_format', 'current_format']
            }
        }

    def _init_migration_complexity_rules(self):
        """Initialize rules for assessing migration complexity."""
        self.complexity_rules = {
            'simple': {
                'parameter_count_max': 20,
                'version_gap_max': 1,
                'structural_changes': False
            },
            'moderate': {
                'parameter_count_max': 50,
                'version_gap_max': 2,
                'structural_changes': True
            },
            'complex': {
                'parameter_count_max': float('inf'),
                'version_gap_max': float('inf'),
                'structural_changes': True
            }
        }

    def _analyze_file_structure(self, file_path: str) -> Dict[str, Any]:
        """Analyze file structure for version detection."""
        try:
            config = configparser.ConfigParser()
            config.read(file_path)
            
            indicators = []
            confidence_boost = 0.0
            suggested_version = "unknown"
            
            sections = set(config.sections())
            
            # Check for version-specific section patterns
            for version, patterns in self.version_patterns.items():
                section_matches = len(sections.intersection(set(patterns['section_names'])))
                if section_matches > 0:
                    indicators.append(f"Found {section_matches} v{version} section patterns")
                    confidence_boost += 0.1 * section_matches
                    if section_matches >= 2:
                        suggested_version = version
            
            return {
                'indicators': indicators,
                'confidence_boost': min(0.3, confidence_boost),
                'suggested_version': suggested_version
            }
            
        except Exception:
            return {
                'indicators': ["Structure analysis failed"],
                'confidence_boost': 0.0,
                'suggested_version': "unknown"
            }

    def _analyze_parameter_patterns(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze parameter patterns for version detection."""
        indicators = []
        confidence_boost = 0.0
        suggested_version = "unknown"
        
        param_names = set(parameters.keys())
        
        # Check for version-specific parameter patterns
        for version, patterns in self.version_patterns.items():
            param_matches = len(param_names.intersection(set(patterns['parameter_names'])))
            if param_matches > 0:
                indicators.append(f"Found {param_matches} v{version} parameter patterns")
                confidence_boost += 0.05 * param_matches
                if param_matches >= 2:
                    suggested_version = version
        
        return {
            'indicators': indicators,
            'confidence_boost': min(0.2, confidence_boost),
            'suggested_version': suggested_version
        }

    def _needs_migration(self, detected_version: str) -> bool:
        """Determine if a profile needs migration."""
        if detected_version == "unknown":
            return True  # Assume migration needed for unknown versions
        
        try:
            # Parse version numbers for comparison
            detected_parts = [int(x) for x in detected_version.split('.')]
            current_parts = [int(x) for x in self.default_config.target_format_version.split('.')]
            
            # Compare major.minor versions
            return detected_parts < current_parts
            
        except (ValueError, AttributeError):
            return True  # Assume migration needed for unparseable versions

    def _assess_migration_complexity(self, version: str, parameters: Dict[str, Any]) -> str:
        """Assess the complexity of migrating from a specific version."""
        param_count = len(parameters)
        
        try:
            version_parts = [int(x) for x in version.split('.')]
            current_parts = [int(x) for x in self.default_config.target_format_version.split('.')]
            version_gap = sum(abs(a - b) for a, b in zip(current_parts, version_parts))
        except (ValueError, AttributeError):
            version_gap = 999  # Unknown version = high complexity
        
        # Determine complexity based on rules
        for complexity, rules in self.complexity_rules.items():
            if (param_count <= rules['parameter_count_max'] and 
                version_gap <= rules['version_gap_max']):
                return complexity
        
        return 'complex'

    def _estimate_migration_time(self, complexity: str, parameter_count: int) -> float:
        """Estimate migration time in seconds."""
        base_times = {
            'simple': 0.5,
            'moderate': 2.0,
            'complex': 5.0,
            'unknown': 10.0,
            'impossible': 0.0
        }
        
        base_time = base_times.get(complexity, 5.0)
        parameter_factor = max(1.0, parameter_count / 20.0)  # Scale with parameter count
        
        return base_time * parameter_factor

    def _is_already_migrated(self, file_path: str) -> bool:
        """Check if a profile has already been migrated."""
        try:
            version_info = self.detect_profile_version(file_path)
            return (version_info.detected_version == self.default_config.target_format_version and
                    version_info.format_confidence > 0.8)
        except Exception:
            return False

    def _validate_source_profile(self, file_path: str) -> ValidationResult:
        """Validate source profile before migration."""
        try:
            config, error_msg = self.file_handler.read_ini_file(file_path)
            
            # Create file_result-like object for compatibility
            class FileResult:
                def __init__(self, success, config=None, error_message=None, profile_data=None):
                    self.success = success
                    self.config = config
                    self.error_message = error_message
                    self.profile_data = profile_data
            
            if config is not None:
                # Create basic profile data from config
                profile_data = {'config': config}
                file_result = FileResult(True, config, profile_data=profile_data)
            else:
                file_result = FileResult(False, error_message=error_msg)
            
            if not file_result.success:
                return ValidationResult(is_valid=False, errors=[], warnings=[], suggestions=[])
            
            return self.validator.validate_profile_structure(file_result.profile_data)
        except Exception:
            return ValidationResult(is_valid=False, errors=[], warnings=[], suggestions=[])

    def _validate_migrated_profile(self, file_path: str) -> ValidationResult:
        """Validate migrated profile after migration."""
        return self._validate_source_profile(file_path)

    def _create_migration_backup(self, file_path: str, strategy: BackupStrategy) -> BackupResult:
        """Create backup according to specified strategy."""
        if strategy == BackupStrategy.NONE:
            return BackupResult(success=True, original_path=file_path)
        
        return self.file_handler.backup_profile_file(file_path)

    def _perform_migration(self, source_file: str, target_file: str, 
                          config: MigrationConfig) -> MigrationResult:
        """Perform the actual migration operation."""
        try:
            # Read source file
            config, error_msg = self.file_handler.read_ini_file(source_file)
            
            # Create file_result-like object for compatibility
            class FileResult:
                def __init__(self, success, config=None, error_message=None, profile_data=None):
                    self.success = success
                    self.config = config
                    self.error_message = error_message
                    self.profile_data = profile_data
            
            if config is not None:
                # Create basic profile data from config
                profile_data = {'config': config}
                file_result = FileResult(True, config, profile_data=profile_data)
            else:
                file_result = FileResult(False, error_message=error_msg)
            
            if not file_result.success:
                return MigrationResult(
                    success=False,
                    original_version="unknown",
                    target_version=config.target_format_version,
                    errors=[]
                )
            
            # Convert to current format
            conversion_result = self.converter.convert_to_standard_format(
                self._profile_data_to_dict(file_result.profile_data)
            )
            
            if not conversion_result.success:
                return MigrationResult(
                    success=False,
                    original_version="unknown",
                    target_version=config.target_format_version,
                    errors=conversion_result.errors
                )
            
            # Write migrated file
            write_result = self.file_handler.write_profile_file(
                target_file, conversion_result.profile_data
            )
            
            if not write_result.success:
                return MigrationResult(
                    success=False,
                    original_version="unknown",
                    target_version=config.target_format_version,
                    errors=[]
                )
            
            return MigrationResult(
                success=True,
                original_version="unknown",
                target_version=config.target_format_version,
                migrated_data=conversion_result.profile_data,
                migration_log=["Migration completed successfully"]
            )
            
        except Exception as e:
            return MigrationResult(
                success=False,
                original_version="unknown",
                target_version=config.target_format_version,
                errors=[],
                migration_log=[f"Migration error: {str(e)}"]
            )

    def _profile_data_to_dict(self, profile_data: ProfileData) -> Dict[str, Any]:
        """Convert ProfileData to dictionary format for converter."""
        result = {
            'Profile_Info': {
                'profile_name': profile_data.metadata.profile_name,
                'created_date': profile_data.metadata.created_date,
                'format_version': profile_data.format_version,
                'app_version': profile_data.metadata.app_version,
                'parameter_count': str(profile_data.metadata.parameter_count)
            },
            'Device_Parameters': profile_data.device_parameters.copy()
        }
        
        if profile_data.metadata.device_imei:
            result['Profile_Info']['device_imei'] = profile_data.metadata.device_imei
        if profile_data.metadata.device_version:
            result['Profile_Info']['device_version'] = profile_data.metadata.device_version
        if profile_data.metadata.checksum:
            result['Profile_Info']['checksum'] = profile_data.metadata.checksum
        
        return result

    def _create_migration_log_file(self, operation: MigrationOperation):
        """Create a detailed migration log file."""
        try:
            log_file = f"{operation.target_file}.migration.log"
            
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"Migration Log - {datetime.now().isoformat()}\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Source File: {operation.source_file}\n")
                f.write(f"Target File: {operation.target_file}\n")
                f.write(f"Source Version: {operation.source_version}\n")
                f.write(f"Target Version: {operation.target_version}\n")
                f.write(f"Status: {operation.status.value}\n")
                f.write(f"Start Time: {operation.start_time}\n")
                f.write(f"End Time: {operation.end_time}\n")
                
                if operation.backup_file:
                    f.write(f"Backup File: {operation.backup_file}\n")
                
                if operation.error_message:
                    f.write(f"Error: {operation.error_message}\n")
                
                f.write("\nMigration Log:\n")
                f.write("-" * 20 + "\n")
                for log_entry in operation.migration_log:
                    f.write(f"{log_entry}\n")
                
                if operation.validation_results:
                    f.write(f"\nValidation Results:\n")
                    f.write("-" * 20 + "\n")
                    f.write(f"Valid: {operation.validation_results.is_valid}\n")
                    f.write(f"Errors: {len(operation.validation_results.errors)}\n")
                    f.write(f"Warnings: {len(operation.validation_results.warnings)}\n")
            
            self.logger.debug(f"Created migration log: {log_file}")
            
        except Exception as e:
            self.logger.warning(f"Failed to create migration log: {str(e)}")

    def _generate_batch_summary_report(self, result: BatchMigrationResult) -> str:
        """Generate a summary report for batch migration results."""
        duration = (result.end_time - result.start_time).total_seconds() if result.end_time and result.start_time else 0
        
        report_lines = [
            f"Batch Migration Summary Report",
            f"Generated: {datetime.now().isoformat()}",
            f"",
            f"Overall Status: {result.overall_status.value.upper()}",
            f"Duration: {duration:.2f} seconds",
            f"",
            f"File Statistics:",
            f"  Total Files: {result.total_files}",
            f"  Successful: {result.successful_migrations}",
            f"  Failed: {result.failed_migrations}",
            f"  Skipped: {result.skipped_files}",
            f"  Success Rate: {(result.successful_migrations / result.total_files * 100):.1f}%" if result.total_files > 0 else "  Success Rate: N/A",
            f""
        ]
        
        if result.failed_migrations > 0:
            report_lines.extend([
                f"Failed Migrations:",
                f"-" * 20
            ])
            
            for op in result.migration_operations:
                if op.status == MigrationStatus.FAILED:
                    report_lines.append(f"  {op.source_file}: {op.error_message}")
        
        return "\n".join(report_lines)

    def _compare_parameter_values(self, original_params: Dict[str, Any], 
                                 migrated_params: Dict[str, Any]) -> List:
        """Compare parameter values between original and migrated profiles."""
        from services.profile_validator import ValidationError, ValidationErrorType, ValidationSeverity
        
        errors = []
        
        # Check for missing parameters
        for param_name in original_params:
            if param_name not in migrated_params:
                errors.append(ValidationError(
                    error_type=ValidationErrorType.MISSING_SECTION,
                    location=f"Device_Parameters.{param_name}",
                    message=f"Parameter '{param_name}' missing after migration",
                    severity=ValidationSeverity.ERROR,
                    parameter_name=param_name
                ))
        
        # Check for value differences (allowing for format conversions)
        for param_name in original_params:
            if param_name in migrated_params:
                original_value = str(original_params[param_name]).strip()
                migrated_value = str(migrated_params[param_name]).strip()
                
                # Allow for minor formatting differences
                if original_value.lower() != migrated_value.lower():
                    errors.append(ValidationError(
                        error_type=ValidationErrorType.INVALID_PARAMETER,
                        location=f"Device_Parameters.{param_name}",
                        message=f"Parameter '{param_name}' value changed during migration: '{original_value}' -> '{migrated_value}'",
                        severity=ValidationSeverity.WARNING,
                        parameter_name=param_name,
                        current_value=migrated_value
                    ))
        
        return errors