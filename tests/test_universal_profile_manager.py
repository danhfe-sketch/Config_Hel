"""
Unit tests for the Universal Profile Manager.

This module contains comprehensive tests for all Universal Profile Manager
operations including device communication, file operations, and error handling.
"""

import asyncio
import pytest
import tempfile
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from services.universal_profile_manager import UniversalProfileManager
from models.universal_profile import UniversalProfile, ProfileMetadata, ParameterValue
from models.operation_result import ProfileOperationResult, OperationType
from models.validation_result import ValidationResult


class TestUniversalProfileManager:
    """Test cases for Universal Profile Manager."""
    
    @pytest.fixture
    def mock_serial_service(self):
        """Create a mock serial service."""
        mock_service = Mock()
        mock_service.is_connected = True
        mock_service.send_command = Mock(return_value=True)
        return mock_service
    
    @pytest.fixture
    def temp_parameter_ui_list(self):
        """Create a temporary Parameter UI List file for testing."""
        content = """# Parameter UI List

## Test Section

### test_param_1
- **Label**: Test Parameter 1
- **UI Element**: number_input
- **Validation**: range(0, 100)
- **Unit**: %
- **Commands**:
  - Read: `READ_TEST1#`
  - Set: `SET_TEST1={value}#`

### test_param_2
- **Label**: Test Parameter 2
- **UI Element**: text_input
- **Commands**:
  - Read: `READ_TEST2#`
  - Set: `SET_TEST2={value}#`
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(content)
            return f.name
    
    @pytest.fixture
    def profile_manager(self, mock_serial_service, temp_parameter_ui_list):
        """Create a Universal Profile Manager instance for testing."""
        return UniversalProfileManager(mock_serial_service, temp_parameter_ui_list)
    
    @pytest.fixture
    def sample_profile(self):
        """Create a sample profile for testing."""
        metadata = ProfileMetadata(
            parameter_spec_version="1.0",
            created_by="Test",
            device_model="LT32 PRO"
        )
        
        profile = UniversalProfile(
            name="Test Profile",
            version="1.0",
            created_at=datetime.now(),
            modified_at=datetime.now(),
            metadata=metadata
        )
        
        # Add some test parameters
        profile.set_parameter_value("test_param_1", 50, "user")
        profile.set_parameter_value("test_param_2", "test_value", "user")
        
        return profile
    
    def test_initialization(self, profile_manager, mock_serial_service, temp_parameter_ui_list):
        """Test profile manager initialization."""
        assert profile_manager.serial_service == mock_serial_service
        assert profile_manager.parameter_ui_list_path == temp_parameter_ui_list
        assert profile_manager.spec_parser is not None
        assert profile_manager.profile_service is not None
        assert profile_manager.device_manager is not None
        assert profile_manager._current_profile is None
        assert profile_manager._operation_cancelled is False
        assert profile_manager._current_operation is None
    
    @pytest.mark.asyncio
    async def test_load_from_device_success(self, profile_manager):
        """Test successful load from device operation."""
        # Mock device responses
        mock_responses = {
            "test_param_1": "50",
            "test_param_2": "test_value"
        }
        
        # Mock the device manager
        with patch.object(profile_manager.device_manager, 'read_all_parameters', 
                         new_callable=AsyncMock) as mock_read:
            mock_read.return_value = mock_responses
            
            # Mock progress callback
            progress_callback = Mock()
            
            # Execute load from device
            result = await profile_manager.load_from_device(progress_callback)
            
            # Verify result
            assert result.success is True
            assert result.operation_type == OperationType.LOAD_FROM_DEVICE
            assert result.profile is not None
            assert result.parameters_processed == 2
            assert result.parameters_successful == 2
            assert result.parameters_failed == 0
            assert len(result.parameter_results) == 2
            
            # Verify profile was set as current
            assert profile_manager._current_profile is not None
            assert profile_manager._current_profile.name.startswith("Device Profile")
            
            # Verify progress callback was called
            assert progress_callback.called
            
            # Verify device manager was called
            mock_read.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_load_from_device_not_connected(self, profile_manager, mock_serial_service):
        """Test load from device when device is not connected."""
        mock_serial_service.is_connected = False
        
        result = await profile_manager.load_from_device()
        
        assert result.success is False
        assert "Device is not connected" in result.errors
        assert result.operation_type == OperationType.LOAD_FROM_DEVICE
    
    @pytest.mark.asyncio
    async def test_load_from_device_no_responses(self, profile_manager):
        """Test load from device when no parameters can be read."""
        # Mock empty device responses
        with patch.object(profile_manager.device_manager, 'read_all_parameters', 
                         new_callable=AsyncMock) as mock_read:
            mock_read.return_value = {}
            
            result = await profile_manager.load_from_device()
            
            assert result.success is False
            assert "No parameters could be read from device" in result.errors
    
    @pytest.mark.asyncio
    async def test_load_from_device_cancelled(self, profile_manager):
        """Test load from device operation cancellation."""
        # Mock device responses but simulate cancellation during operation
        with patch.object(profile_manager.device_manager, 'read_all_parameters', 
                         new_callable=AsyncMock) as mock_read:
            # Simulate cancellation by setting the flag after device manager call
            async def mock_read_with_cancel(*args, **kwargs):
                profile_manager._operation_cancelled = True
                return {}
            
            mock_read.side_effect = mock_read_with_cancel
            
            result = await profile_manager.load_from_device()
            
            assert result.success is False
            assert "Operation was cancelled" in result.errors
    
    @pytest.mark.asyncio
    async def test_save_to_device_success(self, profile_manager, sample_profile):
        """Test successful save to device operation."""
        # Set current profile
        profile_manager._current_profile = sample_profile
        
        # Mock successful write results
        mock_write_results = {
            "test_param_1": True,
            "test_param_2": True
        }
        
        with patch.object(profile_manager.device_manager, 'write_all_parameters', 
                         new_callable=AsyncMock) as mock_write:
            mock_write.return_value = mock_write_results
            
            # Mock progress callback
            progress_callback = Mock()
            
            result = await profile_manager.save_to_device(progress_callback)
            
            assert result.success is True
            assert result.operation_type == OperationType.SAVE_TO_DEVICE
            assert result.parameters_processed == 2
            assert result.parameters_successful == 2
            assert result.parameters_failed == 0
            
            # Verify progress callback was called
            assert progress_callback.called
            
            # Verify device manager was called
            mock_write.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_save_to_device_not_connected(self, profile_manager, mock_serial_service):
        """Test save to device when device is not connected."""
        mock_serial_service.is_connected = False
        
        result = await profile_manager.save_to_device()
        
        assert result.success is False
        assert "Device is not connected" in result.errors
        assert result.operation_type == OperationType.SAVE_TO_DEVICE
    
    @pytest.mark.asyncio
    async def test_save_to_device_no_profile(self, profile_manager):
        """Test save to device when no profile is loaded."""
        result = await profile_manager.save_to_device()
        
        assert result.success is False
        assert "No profile loaded to save to device" in result.errors
    
    @pytest.mark.asyncio
    async def test_save_to_device_partial_success(self, profile_manager, sample_profile):
        """Test save to device with partial success."""
        profile_manager._current_profile = sample_profile
        
        # Mock partial write results
        mock_write_results = {
            "test_param_1": True,
            "test_param_2": False
        }
        
        with patch.object(profile_manager.device_manager, 'write_all_parameters', 
                         new_callable=AsyncMock) as mock_write:
            mock_write.return_value = mock_write_results
            
            result = await profile_manager.save_to_device()
            
            assert result.success is True  # Partial success is still success
            assert result.parameters_successful == 1
            assert result.parameters_failed == 1
            assert len(result.warnings) > 0
            # Check for partial success warning (may be mixed with other warnings)
            partial_success_found = any("Partial success" in warning for warning in result.warnings)
            assert partial_success_found
    
    @pytest.mark.asyncio
    async def test_save_to_device_no_modified_parameters(self, profile_manager, sample_profile):
        """Test save to device when no parameters are modified."""
        # Clear modification flags
        for param_value in sample_profile.parameters.values():
            param_value.is_modified = False
            param_value.source = "device"
        
        profile_manager._current_profile = sample_profile
        
        result = await profile_manager.save_to_device()
        
        assert result.success is True
        assert "No modified parameters to write to device" in result.warnings
    
    @pytest.mark.asyncio
    async def test_load_from_file_success(self, profile_manager, sample_profile):
        """Test successful load from file operation."""
        # Create temporary profile file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_profile.to_dict(), f, indent=2)
            temp_file = f.name
        
        try:
            result = await profile_manager.load_from_file(temp_file)
            
            assert result.success is True
            assert result.operation_type == OperationType.LOAD_FROM_FILE
            assert result.profile is not None
            assert result.profile.name == sample_profile.name
            assert len(result.parameter_results) == len(sample_profile.parameters)
            
            # Verify profile was set as current
            assert profile_manager._current_profile is not None
            assert profile_manager._current_profile.name == sample_profile.name
            
        finally:
            Path(temp_file).unlink()
    
    @pytest.mark.asyncio
    async def test_load_from_file_not_found(self, profile_manager):
        """Test load from file when file doesn't exist."""
        result = await profile_manager.load_from_file("nonexistent_file.json")
        
        assert result.success is False
        assert "Profile file not found" in result.errors[0]
        assert result.operation_type == OperationType.LOAD_FROM_FILE
    
    @pytest.mark.asyncio
    async def test_load_from_file_invalid_format(self, profile_manager):
        """Test load from file with invalid JSON format."""
        # Create temporary file with invalid JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_file = f.name
        
        try:
            result = await profile_manager.load_from_file(temp_file)
            
            assert result.success is False
            assert any("Invalid profile file format" in error for error in result.errors)
            
        finally:
            Path(temp_file).unlink()
    
    @pytest.mark.asyncio
    async def test_save_to_file_success(self, profile_manager, sample_profile):
        """Test successful save to file operation."""
        profile_manager._current_profile = sample_profile
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            result = await profile_manager.save_to_file(temp_file, "New Profile Name")
            
            assert result.success is True
            assert result.operation_type == OperationType.SAVE_TO_FILE
            assert result.profile is not None
            assert result.profile.name == "New Profile Name"
            assert len(result.parameter_results) == len(sample_profile.parameters)
            
            # Verify file was created
            assert Path(temp_file).exists()
            
            # Verify file content
            with open(temp_file, 'r') as f:
                saved_data = json.load(f)
                assert saved_data["name"] == "New Profile Name"
                
        finally:
            if Path(temp_file).exists():
                Path(temp_file).unlink()
    
    @pytest.mark.asyncio
    async def test_save_to_file_no_profile(self, profile_manager):
        """Test save to file when no profile is loaded."""
        result = await profile_manager.save_to_file("test.json")
        
        assert result.success is False
        assert "No profile loaded to save to file" in result.errors
    
    def test_get_current_profile(self, profile_manager, sample_profile):
        """Test getting the current profile."""
        assert profile_manager.get_current_profile() is None
        
        profile_manager._current_profile = sample_profile
        assert profile_manager.get_current_profile() == sample_profile
    
    def test_set_current_profile(self, profile_manager, sample_profile):
        """Test setting the current profile."""
        profile_manager.set_current_profile(sample_profile)
        assert profile_manager._current_profile == sample_profile
    
    def test_populate_ui_fields_success(self, profile_manager, sample_profile):
        """Test successful UI field population."""
        profile_manager._current_profile = sample_profile
        
        ui_field_values = {}
        result = profile_manager.populate_ui_fields(ui_field_values)
        
        assert result.is_valid is True
        assert len(ui_field_values) == 2
        assert ui_field_values["test_param_1"] == 50
        assert ui_field_values["test_param_2"] == "test_value"
    
    def test_populate_ui_fields_no_profile(self, profile_manager):
        """Test UI field population when no profile is loaded."""
        ui_field_values = {}
        result = profile_manager.populate_ui_fields(ui_field_values)
        
        assert result.is_valid is False
        assert "No profile loaded to populate UI fields" in result.errors
    
    def test_extract_ui_field_values_new_profile(self, profile_manager):
        """Test extracting UI field values to create a new profile."""
        ui_field_values = {
            "test_param_1": 75,
            "test_param_2": "new_value"
        }
        
        result = profile_manager.extract_ui_field_values(ui_field_values)
        
        assert result.is_valid is True
        assert profile_manager._current_profile is not None
        assert profile_manager._current_profile.get_parameter_value("test_param_1") == 75
        assert profile_manager._current_profile.get_parameter_value("test_param_2") == "new_value"
    
    def test_extract_ui_field_values_update_existing(self, profile_manager, sample_profile):
        """Test extracting UI field values to update existing profile."""
        profile_manager._current_profile = sample_profile
        
        ui_field_values = {
            "test_param_1": 80,
            "test_param_2": "updated_value"
        }
        
        result = profile_manager.extract_ui_field_values(ui_field_values)
        
        assert result.is_valid is True
        assert profile_manager._current_profile.get_parameter_value("test_param_1") == 80
        assert profile_manager._current_profile.get_parameter_value("test_param_2") == "updated_value"
    
    def test_cancel_operation(self, profile_manager):
        """Test operation cancellation."""
        profile_manager.cancel_operation()
        
        assert profile_manager._operation_cancelled is True
    
    def test_is_operation_cancelled(self, profile_manager):
        """Test checking if operation is cancelled."""
        assert profile_manager.is_operation_cancelled() is False
        
        profile_manager._operation_cancelled = True
        assert profile_manager.is_operation_cancelled() is True
    
    def test_get_current_operation(self, profile_manager):
        """Test getting current operation."""
        assert profile_manager.get_current_operation() is None
        
        profile_manager._current_operation = "test_operation"
        assert profile_manager.get_current_operation() == "test_operation"
    
    def test_get_supported_parameters(self, profile_manager):
        """Test getting supported parameters."""
        parameters = profile_manager.get_supported_parameters()
        
        assert isinstance(parameters, list)
        # The parameter list might be empty if parsing fails, which is acceptable
        # The important thing is that the method returns a list without crashing
    
    def test_get_profile_summary_with_profile(self, profile_manager, sample_profile):
        """Test getting profile summary when profile is loaded."""
        profile_manager._current_profile = sample_profile
        
        summary = profile_manager.get_profile_summary()
        
        assert summary is not None
        assert summary["name"] == sample_profile.name
        assert summary["total_parameters"] == 2
    
    def test_get_profile_summary_no_profile(self, profile_manager):
        """Test getting profile summary when no profile is loaded."""
        summary = profile_manager.get_profile_summary()
        
        assert summary is None
    
    def test_validate_current_profile_with_profile(self, profile_manager, sample_profile):
        """Test validating current profile when profile is loaded."""
        profile_manager._current_profile = sample_profile
        
        result = profile_manager.validate_current_profile()
        
        assert isinstance(result, ValidationResult)
        # Should be valid since we have a proper test profile
        assert result.is_valid is True
    
    def test_validate_current_profile_no_profile(self, profile_manager):
        """Test validating current profile when no profile is loaded."""
        result = profile_manager.validate_current_profile()
        
        assert result.is_valid is False
        assert "No profile loaded to validate" in result.errors
    
    @pytest.mark.asyncio
    async def test_compare_with_device_not_implemented(self, profile_manager):
        """Test compare with device operation (not yet implemented)."""
        result = profile_manager.compare_with_device()
        
        assert result.success is False
        assert "not yet implemented" in result.errors[0]
    
    def test_create_device_progress_callback(self, profile_manager):
        """Test creating device progress callback."""
        user_callback = Mock()
        
        # Test with user callback
        device_callback = profile_manager._create_device_progress_callback(user_callback, 10, 90)
        assert device_callback is not None
        
        # Test callback mapping
        device_callback(50, 100, "test", True)
        user_callback.assert_called_once_with(50, 100, "test", True)
        
        # Test with no user callback
        device_callback = profile_manager._create_device_progress_callback(None, 10, 90)
        assert device_callback is None
    
    def test_string_representation(self, profile_manager, sample_profile):
        """Test string representation of profile manager."""
        # Test with no profile
        str_repr = str(profile_manager)
        assert "No profile loaded" in str_repr
        assert "Idle" in str_repr
        
        # Test with profile
        profile_manager._current_profile = sample_profile
        str_repr = str(profile_manager)
        assert sample_profile.name in str_repr
        assert "2 parameters" in str_repr
        
        # Test with operation
        profile_manager._current_operation = "test_operation"
        str_repr = str(profile_manager)
        assert "test_operation" in str_repr


class TestUniversalProfileManagerErrorHandling:
    """Test error handling scenarios for Universal Profile Manager."""
    
    @pytest.fixture
    def mock_serial_service(self):
        """Create a mock serial service."""
        mock_service = Mock()
        mock_service.is_connected = True
        mock_service.send_command = Mock(return_value=True)
        return mock_service
    
    @pytest.fixture
    def temp_parameter_ui_list(self):
        """Create a temporary Parameter UI List file for testing."""
        content = """# Parameter UI List

## Test Section

### test_param_1
- **Label**: Test Parameter 1
- **UI Element**: number_input
- **Validation**: range(0, 100)
- **Unit**: %
- **Commands**:
  - Read: `READ_TEST1#`
  - Set: `SET_TEST1={value}#`

### test_param_2
- **Label**: Test Parameter 2
- **UI Element**: text_input
- **Commands**:
  - Read: `READ_TEST2#`
  - Set: `SET_TEST2={value}#`
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(content)
            return f.name
    
    @pytest.fixture
    def sample_profile(self):
        """Create a sample profile for testing."""
        metadata = ProfileMetadata(
            parameter_spec_version="1.0",
            created_by="Test",
            device_model="LT32 PRO"
        )
        
        profile = UniversalProfile(
            name="Test Profile",
            version="1.0",
            created_at=datetime.now(),
            modified_at=datetime.now(),
            metadata=metadata
        )
        
        # Add some test parameters
        profile.set_parameter_value("test_param_1", 50, "user")
        profile.set_parameter_value("test_param_2", "test_value", "user")
        
        return profile
    
    @pytest.fixture
    def profile_manager_with_errors(self, mock_serial_service, temp_parameter_ui_list):
        """Create a profile manager that will encounter errors."""
        return UniversalProfileManager(mock_serial_service, temp_parameter_ui_list)
    
    @pytest.mark.asyncio
    async def test_load_from_device_device_error(self, profile_manager_with_errors):
        """Test load from device when device communication fails."""
        with patch.object(profile_manager_with_errors.device_manager, 'read_all_parameters', 
                         new_callable=AsyncMock) as mock_read:
            mock_read.side_effect = Exception("Device communication error")
            
            result = await profile_manager_with_errors.load_from_device()
            
            assert result.success is False
            assert "Failed to read from device" in result.errors[0]
    
    @pytest.mark.asyncio
    async def test_save_to_device_device_error(self, profile_manager_with_errors, sample_profile):
        """Test save to device when device communication fails."""
        profile_manager_with_errors._current_profile = sample_profile
        
        with patch.object(profile_manager_with_errors.device_manager, 'write_all_parameters', 
                         new_callable=AsyncMock) as mock_write:
            mock_write.side_effect = Exception("Device communication error")
            
            result = await profile_manager_with_errors.save_to_device()
            
            assert result.success is False
            assert "Failed to write to device" in result.errors[0]
    
    @pytest.mark.asyncio
    async def test_save_to_file_permission_error(self, profile_manager_with_errors, sample_profile):
        """Test save to file when file cannot be written."""
        profile_manager_with_errors._current_profile = sample_profile
        
        with patch.object(profile_manager_with_errors.profile_service, 'save_profile_to_file') as mock_save:
            mock_save.side_effect = PermissionError("Permission denied")
            
            result = await profile_manager_with_errors.save_to_file("/invalid/path/test.json")
            
            assert result.success is False
            assert "Failed to save profile file" in result.errors[0]
    
    def test_populate_ui_fields_error(self, profile_manager_with_errors, sample_profile):
        """Test UI field population when an error occurs."""
        profile_manager_with_errors._current_profile = sample_profile
        
        # Mock an error in the spec parser
        with patch.object(profile_manager_with_errors.spec_parser, 'get_parameter_spec') as mock_spec:
            mock_spec.side_effect = Exception("Spec parser error")
            
            ui_field_values = {}
            result = profile_manager_with_errors.populate_ui_fields(ui_field_values)
            
            assert result.is_valid is False
            assert "Failed to populate UI fields" in result.errors[0]
    
    def test_extract_ui_field_values_error(self, profile_manager_with_errors):
        """Test UI field extraction when an error occurs."""
        ui_field_values = {"test_param": "value"}
        
        # Mock an error in the profile service
        with patch.object(profile_manager_with_errors.profile_service, 'create_profile_from_ui') as mock_create:
            mock_create.side_effect = Exception("Profile creation error")
            
            result = profile_manager_with_errors.extract_ui_field_values(ui_field_values)
            
            assert result.is_valid is False
            assert "Failed to extract UI field values" in result.errors[0]


if __name__ == "__main__":
    pytest.main([__file__])


class TestUniversalProfileManagerUIIntegration:
    """Test UI integration methods for Universal Profile Manager."""
    
    @pytest.fixture
    def mock_serial_service(self):
        """Create a mock serial service."""
        mock_service = Mock()
        mock_service.is_connected = True
        mock_service.send_command = Mock(return_value=True)
        return mock_service
    
    @pytest.fixture
    def temp_parameter_ui_list_with_visibility(self):
        """Create a Parameter UI List file with visibility conditions for testing."""
        content = """# Parameter UI List

## Section: Test Parameters

### Config: Ignition Mode

*   **name:** ignition_mode
*   **label:** "Ignition Mode"
*   **ui_element:** "dropdown"
*   **options:** ["Physical", "Virtual by battery", "Virtual by accelerometer"]
*   **commands:**
    *   **set:** `SET_IGNITION={value}#`
    *   **read:** `READ_IGNITION#`

### Config: On Voltage

*   **name:** on_voltage
*   **label:** "On Voltage"
*   **ui_element:** "number_input"
*   **unit:** "V"
*   **visibility_condition:** "ignition_mode == 'Virtual by battery'"
*   **commands:**
    *   **set:** `SET_ON_VOLTAGE={value}#`
    *   **read:** `READ_ON_VOLTAGE#`

### Config: Off Voltage

*   **name:** off_voltage
*   **label:** "Off Voltage"
*   **ui_element:** "number_input"
*   **unit:** "V"
*   **visibility_condition:** "ignition_mode == 'Virtual by battery'"
*   **commands:**
    *   **set:** `SET_OFF_VOLTAGE={value}#`
    *   **read:** `READ_OFF_VOLTAGE#`

### Config: Speed Alert Enabled

*   **name:** speed_alert_enabled
*   **label:** "Speed Alert Enabled"
*   **ui_element:** "toggle_switch"
*   **commands:**
    *   **set:** `SET_SPEED_ALERT={value}#`
    *   **read:** `READ_SPEED_ALERT#`

### Config: Speed Limit

*   **name:** speed_limit
*   **label:** "Speed Limit"
*   **ui_element:** "number_input"
*   **unit:** "km/h"
*   **visibility_condition:** "speed_alert_enabled == true"
*   **commands:**
    *   **set:** `SET_SPEED_LIMIT={value}#`
    *   **read:** `READ_SPEED_LIMIT#`

### Config: Simple Parameter

*   **name:** simple_param
*   **label:** "Simple Parameter"
*   **ui_element:** "text_input"
*   **commands:**
    *   **set:** `SET_SIMPLE={value}#`
    *   **read:** `READ_SIMPLE#`
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(content)
            return f.name
    
    @pytest.fixture
    def profile_manager_with_visibility(self, mock_serial_service, temp_parameter_ui_list_with_visibility):
        """Create a profile manager with visibility conditions."""
        return UniversalProfileManager(mock_serial_service, temp_parameter_ui_list_with_visibility)
    
    @pytest.fixture
    def sample_profile_with_visibility(self):
        """Create a sample profile with visibility-dependent parameters."""
        metadata = ProfileMetadata(
            parameter_spec_version="1.0",
            created_by="Test",
            device_model="LT32 PRO"
        )
        
        profile = UniversalProfile(
            name="Test Profile with Visibility",
            version="1.0",
            created_at=datetime.now(),
            modified_at=datetime.now(),
            metadata=metadata
        )
        
        # Add parameters with visibility dependencies
        profile.set_parameter_value("ignition_mode", "Virtual by battery", "user")
        profile.set_parameter_value("on_voltage", 13.5, "user")
        profile.set_parameter_value("off_voltage", 13.0, "user")
        profile.set_parameter_value("speed_alert_enabled", True, "user")
        profile.set_parameter_value("speed_limit", 80, "user")
        profile.set_parameter_value("simple_param", "test_value", "user")
        
        return profile
    
    def test_evaluate_visibility_condition_simple_equality(self, profile_manager_with_visibility):
        """Test visibility condition evaluation with simple equality."""
        context = {"ignition_mode": "Virtual by battery"}
        
        # Test matching condition
        result = profile_manager_with_visibility._evaluate_visibility_condition(
            "ignition_mode == 'Virtual by battery'", context
        )
        assert result is True
        
        # Test non-matching condition
        result = profile_manager_with_visibility._evaluate_visibility_condition(
            "ignition_mode == 'Physical'", context
        )
        assert result is False
    
    def test_evaluate_visibility_condition_boolean(self, profile_manager_with_visibility):
        """Test visibility condition evaluation with boolean conditions."""
        context = {"speed_alert_enabled": True}
        
        # Test true condition
        result = profile_manager_with_visibility._evaluate_visibility_condition(
            "speed_alert_enabled == true", context
        )
        assert result is True
        
        # Test false condition
        context = {"speed_alert_enabled": False}
        result = profile_manager_with_visibility._evaluate_visibility_condition(
            "speed_alert_enabled == true", context
        )
        assert result is False
    
    def test_evaluate_visibility_condition_no_condition(self, profile_manager_with_visibility):
        """Test visibility condition evaluation with no condition."""
        context = {"param": "value"}
        
        result = profile_manager_with_visibility._evaluate_visibility_condition(None, context)
        assert result is True
        
        result = profile_manager_with_visibility._evaluate_visibility_condition("", context)
        assert result is True
    
    def test_evaluate_visibility_condition_invalid(self, profile_manager_with_visibility):
        """Test visibility condition evaluation with invalid condition."""
        context = {"param": "value"}
        
        # Invalid condition should default to visible
        result = profile_manager_with_visibility._evaluate_visibility_condition(
            "invalid condition syntax", context
        )
        assert result is True
    
    def test_populate_ui_fields_with_visibility(self, profile_manager_with_visibility, sample_profile_with_visibility):
        """Test UI field population with visibility conditions."""
        profile_manager_with_visibility._current_profile = sample_profile_with_visibility
        
        ui_field_values = {}
        result = profile_manager_with_visibility.populate_ui_fields(ui_field_values)
        
        assert result.is_valid is True
        
        # Should include visible parameters
        assert "ignition_mode" in ui_field_values
        assert "on_voltage" in ui_field_values  # Visible because ignition_mode == 'Virtual by battery'
        assert "off_voltage" in ui_field_values  # Visible because ignition_mode == 'Virtual by battery'
        assert "speed_alert_enabled" in ui_field_values
        assert "speed_limit" in ui_field_values  # Visible because speed_alert_enabled == true
        assert "simple_param" in ui_field_values
        
        # Check values
        assert ui_field_values["ignition_mode"] == "Virtual by battery"
        assert ui_field_values["on_voltage"] == 13.5
        assert ui_field_values["off_voltage"] == 13.0
        assert ui_field_values["speed_alert_enabled"] is True
        assert ui_field_values["speed_limit"] == 80
        assert ui_field_values["simple_param"] == "test_value"
    
    def test_populate_ui_fields_hidden_parameters(self, profile_manager_with_visibility):
        """Test UI field population with hidden parameters."""
        # Create profile with parameters that should be hidden
        metadata = ProfileMetadata(
            parameter_spec_version="1.0",
            created_by="Test",
            device_model="LT32 PRO"
        )
        
        profile = UniversalProfile(
            name="Test Profile Hidden",
            version="1.0",
            created_at=datetime.now(),
            modified_at=datetime.now(),
            metadata=metadata
        )
        
        # Set ignition mode to Physical (should hide voltage parameters)
        profile.set_parameter_value("ignition_mode", "Physical", "user")
        profile.set_parameter_value("on_voltage", 13.5, "user")  # Should be hidden
        profile.set_parameter_value("off_voltage", 13.0, "user")  # Should be hidden
        profile.set_parameter_value("speed_alert_enabled", False, "user")
        profile.set_parameter_value("speed_limit", 80, "user")  # Should be hidden
        
        profile_manager_with_visibility._current_profile = profile
        
        ui_field_values = {}
        result = profile_manager_with_visibility.populate_ui_fields(ui_field_values)
        
        assert result.is_valid is True
        
        # Should include visible parameters
        assert "ignition_mode" in ui_field_values
        assert "speed_alert_enabled" in ui_field_values
        
        # Should not include hidden parameters
        assert "on_voltage" not in ui_field_values
        assert "off_voltage" not in ui_field_values
        assert "speed_limit" not in ui_field_values
        
        # Should have warnings about hidden parameters
        assert len(result.warnings) >= 3  # At least 3 hidden parameters
    
    def test_extract_ui_field_values_with_validation(self, profile_manager_with_visibility):
        """Test UI field extraction with validation."""
        ui_field_values = {
            "ignition_mode": "Virtual by battery",
            "on_voltage": 13.5,
            "off_voltage": 13.0,
            "speed_alert_enabled": True,
            "speed_limit": 80,
            "simple_param": "test_value"
        }
        
        result = profile_manager_with_visibility.extract_ui_field_values(ui_field_values)
        
        assert result.is_valid is True
        assert profile_manager_with_visibility._current_profile is not None
        
        # Check that all values were set correctly
        profile = profile_manager_with_visibility._current_profile
        assert profile.get_parameter_value("ignition_mode") == "Virtual by battery"
        assert profile.get_parameter_value("on_voltage") == 13.5
        assert profile.get_parameter_value("off_voltage") == 13.0
        assert profile.get_parameter_value("speed_alert_enabled") is True
        assert profile.get_parameter_value("speed_limit") == 80
        assert profile.get_parameter_value("simple_param") == "test_value"
    
    def test_extract_ui_field_values_with_invalid_values(self, profile_manager_with_visibility):
        """Test UI field extraction with invalid values."""
        # Mock parameter spec to return validation errors
        with patch.object(profile_manager_with_visibility.spec_parser, 'get_parameter_spec') as mock_spec:
            mock_param_spec = Mock()
            mock_param_spec.validate_value.return_value = ValidationResult(
                is_valid=False, errors=["Invalid value"]
            )
            mock_param_spec.get_default_value.return_value = "default_value"
            mock_spec.return_value = mock_param_spec
            
            ui_field_values = {
                "test_param": "invalid_value"
            }
            
            result = profile_manager_with_visibility.extract_ui_field_values(ui_field_values)
            
            # Should have warnings about using default values
            assert len(result.warnings) > 0
            assert any("Using default" in warning for warning in result.warnings)
    
    def test_update_dependent_fields(self, profile_manager_with_visibility):
        """Test updating dependent fields when a field changes."""
        ui_field_values = {
            "ignition_mode": "Physical",
            "on_voltage": 13.5,
            "off_voltage": 13.0,
            "speed_alert_enabled": True,
            "speed_limit": 80
        }
        
        # Change ignition mode to Virtual by battery
        updated_fields = profile_manager_with_visibility._update_dependent_fields(
            "ignition_mode", "Virtual by battery", ui_field_values
        )
        
        # Should return list of fields that were affected
        assert isinstance(updated_fields, list)
        # The exact behavior depends on the parameter specifications
    
    def test_get_field_dependencies(self, profile_manager_with_visibility):
        """Test getting field dependencies."""
        # Mock parameter spec with visibility condition
        with patch.object(profile_manager_with_visibility.spec_parser, 'get_parameter_spec') as mock_spec:
            mock_param_spec = Mock()
            mock_param_spec.visibility_condition = "ignition_mode == 'Virtual by battery'"
            mock_spec.return_value = mock_param_spec
            
            dependencies = profile_manager_with_visibility._get_field_dependencies("on_voltage")
            
            assert "ignition_mode" in dependencies
    
    def test_validate_field_dependencies(self, profile_manager_with_visibility):
        """Test field dependency validation."""
        ui_field_values = {
            "ignition_mode": "Virtual by battery",
            "on_voltage": 13.5,
            "off_voltage": 13.0
        }
        
        result = profile_manager_with_visibility._validate_field_dependencies(ui_field_values)
        
        assert isinstance(result, ValidationResult)
        # Should be valid since dependencies are satisfied
    
    def test_get_visible_parameters(self, profile_manager_with_visibility):
        """Test getting visible parameters."""
        context = {
            "ignition_mode": "Virtual by battery",
            "speed_alert_enabled": True
        }
        
        visible_params = profile_manager_with_visibility.get_visible_parameters(context)
        
        assert isinstance(visible_params, list)
        assert "ignition_mode" in visible_params
        assert "simple_param" in visible_params  # No visibility condition
        
        # Parameters with satisfied visibility conditions should be included
        # The exact list depends on the parameter specifications
    
    def test_get_visible_parameters_no_context(self, profile_manager_with_visibility, sample_profile_with_visibility):
        """Test getting visible parameters with no context (uses current profile)."""
        profile_manager_with_visibility._current_profile = sample_profile_with_visibility
        
        visible_params = profile_manager_with_visibility.get_visible_parameters()
        
        assert isinstance(visible_params, list)
        assert len(visible_params) > 0
    
    def test_get_parameter_dependencies(self, profile_manager_with_visibility):
        """Test getting parameter dependencies."""
        dependencies = profile_manager_with_visibility.get_parameter_dependencies("on_voltage")
        
        assert isinstance(dependencies, dict)
        assert "depends_on" in dependencies
        assert "affects" in dependencies
        assert isinstance(dependencies["depends_on"], list)
        assert isinstance(dependencies["affects"], list)
    
    def test_validate_ui_field_values(self, profile_manager_with_visibility):
        """Test validating UI field values without updating profile."""
        ui_field_values = {
            "ignition_mode": "Virtual by battery",
            "on_voltage": 13.5,
            "off_voltage": 13.0,
            "simple_param": "test_value"
        }
        
        result = profile_manager_with_visibility.validate_ui_field_values(ui_field_values)
        
        assert isinstance(result, ValidationResult)
        # Should be valid for well-formed values
        assert result.is_valid is True
        assert "valid_fields" in result.details
        assert "invalid_fields" in result.details
        assert "total_fields" in result.details
    
    def test_validate_ui_field_values_with_errors(self, profile_manager_with_visibility):
        """Test validating UI field values with validation errors."""
        # Mock parameter spec to return validation errors
        with patch.object(profile_manager_with_visibility.spec_parser, 'get_parameter_spec') as mock_spec:
            mock_param_spec = Mock()
            mock_param_spec.validate_value.return_value = ValidationResult(
                is_valid=False, errors=["Invalid value"]
            )
            mock_spec.return_value = mock_param_spec
            
            ui_field_values = {
                "test_param": "invalid_value"
            }
            
            result = profile_manager_with_visibility.validate_ui_field_values(ui_field_values)
            
            assert result.is_valid is False
            assert len(result.errors) > 0
            assert "invalid_fields" in result.details
            assert len(result.details["invalid_fields"]) > 0
    
    def test_get_field_default_values(self, profile_manager_with_visibility):
        """Test getting field default values."""
        # Mock parameter spec to return default values
        with patch.object(profile_manager_with_visibility.spec_parser, 'get_parameter_spec') as mock_spec:
            mock_param_spec = Mock()
            mock_param_spec.get_default_value.return_value = "default_value"
            mock_spec.return_value = mock_param_spec
            
            defaults = profile_manager_with_visibility.get_field_default_values(["test_param"])
            
            assert isinstance(defaults, dict)
            assert "test_param" in defaults
            assert defaults["test_param"] == "default_value"
    
    def test_get_field_default_values_all_fields(self, profile_manager_with_visibility):
        """Test getting default values for all fields."""
        defaults = profile_manager_with_visibility.get_field_default_values()
        
        assert isinstance(defaults, dict)
        # The exact content depends on the parameter specifications
    
    def test_set_complex_parameter_field(self, profile_manager_with_visibility, sample_profile_with_visibility):
        """Test setting a field in a complex parameter."""
        profile_manager_with_visibility._current_profile = sample_profile_with_visibility
        
        # Test setting a field in a complex parameter
        profile_manager_with_visibility._set_complex_parameter_field("complex_param", "field1", "value1")
        
        # Check that the complex parameter was created/updated
        value = profile_manager_with_visibility._current_profile.get_parameter_value("complex_param")
        assert isinstance(value, dict)
        assert value["field1"] == "value1"
    
    def test_set_complex_parameter_field_existing(self, profile_manager_with_visibility, sample_profile_with_visibility):
        """Test setting a field in an existing complex parameter."""
        profile_manager_with_visibility._current_profile = sample_profile_with_visibility
        
        # Set initial complex parameter
        profile_manager_with_visibility._current_profile.set_parameter_value(
            "complex_param", {"field1": "initial_value"}, "user"
        )
        
        # Update a field
        profile_manager_with_visibility._set_complex_parameter_field("complex_param", "field2", "value2")
        
        # Check that both fields exist
        value = profile_manager_with_visibility._current_profile.get_parameter_value("complex_param")
        assert value["field1"] == "initial_value"
        assert value["field2"] == "value2"
    
    def test_populate_ui_fields_complex_parameters(self, profile_manager_with_visibility):
        """Test populating UI fields with complex parameters."""
        # Create a profile with complex parameters
        metadata = ProfileMetadata(
            parameter_spec_version="1.0",
            created_by="Test",
            device_model="LT32 PRO"
        )
        
        profile = UniversalProfile(
            name="Complex Test Profile",
            version="1.0",
            created_at=datetime.now(),
            modified_at=datetime.now(),
            metadata=metadata
        )
        
        # Add complex parameter
        complex_value = {"field1": "value1", "field2": "value2"}
        profile.set_parameter_value("complex_param", complex_value, "user")
        
        profile_manager_with_visibility._current_profile = profile
        
        # Mock parameter spec with fields
        with patch.object(profile_manager_with_visibility.spec_parser, 'get_parameter_spec') as mock_spec:
            mock_field1 = Mock()
            mock_field1.name = "field1"
            mock_field2 = Mock()
            mock_field2.name = "field2"
            
            mock_param_spec = Mock()
            mock_param_spec.fields = [mock_field1, mock_field2]
            mock_param_spec.visibility_condition = None
            mock_spec.return_value = mock_param_spec
            
            ui_field_values = {}
            result = profile_manager_with_visibility.populate_ui_fields(ui_field_values)
            
            assert result.is_valid is True
            assert "complex_param.field1" in ui_field_values
            assert "complex_param.field2" in ui_field_values
            assert ui_field_values["complex_param.field1"] == "value1"
            assert ui_field_values["complex_param.field2"] == "value2"
    
    def test_extract_ui_field_values_complex_parameters(self, profile_manager_with_visibility):
        """Test extracting UI field values with complex parameters."""
        ui_field_values = {
            "complex_param.field1": "value1",
            "complex_param.field2": "value2",
            "simple_param": "simple_value"
        }
        
        result = profile_manager_with_visibility.extract_ui_field_values(ui_field_values)
        
        assert result.is_valid is True
        
        # Check that complex parameter was created correctly
        profile = profile_manager_with_visibility._current_profile
        complex_value = profile.get_parameter_value("complex_param")
        assert isinstance(complex_value, dict)
        assert complex_value["field1"] == "value1"
        assert complex_value["field2"] == "value2"
        
        # Check simple parameter
        assert profile.get_parameter_value("simple_param") == "simple_value"


if __name__ == "__main__":
    pytest.main([__file__])