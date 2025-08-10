"""
Unit tests for the Device Communication Manager.

This module tests the device communication functionality including parameter
reading, writing, response parsing, and command formatting.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from services.device_communication_manager import DeviceCommunicationManager
from services.parameter_specification_parser import ParameterSpecificationParser
from models.parameter_spec import ParameterSpec, ParameterCommands, ParameterField, UIElementType
from models.validation_result import ValidationResult


class TestDeviceCommunicationManager:
    """Test cases for DeviceCommunicationManager."""
    
    @pytest.fixture
    def mock_serial_service(self):
        """Create a mock serial service."""
        mock_service = Mock()
        mock_service.is_connected = True
        mock_service.send_command = Mock(return_value=True)
        mock_service.app = Mock()
        mock_service.app.log_frame = Mock()
        mock_service.app.log_frame.log_message = Mock()
        return mock_service
    
    @pytest.fixture
    def mock_spec_parser(self):
        """Create a mock parameter specification parser."""
        mock_parser = Mock(spec=ParameterSpecificationParser)
        
        # Create sample parameter specifications
        apn_commands = ParameterCommands(
            set_command="APN,<apn>,<user>,<password>#",
            read_command="APN#"
        )
        
        apn_fields = [
            ParameterField("apn", "APN", UIElementType.TEXT_INPUT),
            ParameterField("user", "User", UIElementType.TEXT_INPUT),
            ParameterField("password", "Password", UIElementType.TEXT_INPUT)
        ]
        
        apn_spec = ParameterSpec(
            name="apn_settings",
            label="APN Settings",
            section="Network Parameters",
            commands=apn_commands,
            fields=apn_fields
        )
        
        server_commands = ParameterCommands(
            set_command="SERVER,<type>,<address>,<port>,0#",
            read_command="SERVER#"
        )
        
        server_fields = [
            ParameterField("address", "Address", UIElementType.TEXT_INPUT),
            ParameterField("port", "Port", UIElementType.NUMBER_INPUT)
        ]
        
        server_spec = ParameterSpec(
            name="server_settings",
            label="Server Settings",
            section="Network Parameters",
            commands=server_commands,
            fields=server_fields
        )
        
        protocol_commands = ParameterCommands(
            set_command="SZCS#GT06SEL=<protocol>",
            read_command="CXCS#GT06SEL"
        )
        
        protocol_spec = ParameterSpec(
            name="protocol",
            label="Protocol",
            section="Service Parameters",
            ui_element=UIElementType.DROPDOWN,
            options=["0", "1", "2"],
            commands=protocol_commands
        )
        
        # Mock the parse_specifications method
        mock_parser.parse_specifications.return_value = {
            "apn_settings": apn_spec,
            "server_settings": server_spec,
            "protocol": protocol_spec
        }
        
        return mock_parser
    
    @pytest.fixture
    def device_manager(self, mock_serial_service, mock_spec_parser):
        """Create a DeviceCommunicationManager instance for testing."""
        return DeviceCommunicationManager(mock_serial_service, mock_spec_parser)
    
    def test_initialization(self, mock_serial_service, mock_spec_parser):
        """Test DeviceCommunicationManager initialization."""
        manager = DeviceCommunicationManager(mock_serial_service, mock_spec_parser)
        
        assert manager.serial_service == mock_serial_service
        assert manager.spec_parser == mock_spec_parser
        assert manager.device_reader is not None
        assert manager.device_writer is not None
        assert not manager._operation_cancelled
        assert manager._current_operation is None
    
    @pytest.mark.asyncio
    async def test_read_all_parameters_success(self, device_manager, mock_serial_service):
        """Test successful reading of all parameters."""
        # Mock device reader responses
        with patch.object(device_manager.device_reader, 'read_single_parameter') as mock_read:
            mock_read.side_effect = [
                "APN:test.apn,testuser,testpass",
                "SERVER:0,192.168.1.1,8080,0",
                "GT06SEL=1"
            ]
            
            # Mock progress callback
            progress_callback = Mock()
            
            # Execute the read operation
            result = await device_manager.read_all_parameters(progress_callback)
            
            # Verify results
            assert len(result) == 3
            assert "apn_settings" in result
            assert "server_settings" in result
            assert "protocol" in result
            
            # Verify progress callback was called
            assert progress_callback.call_count >= 6  # Start + end for each parameter
    
    @pytest.mark.asyncio
    async def test_read_all_parameters_device_not_connected(self, device_manager, mock_serial_service):
        """Test read operation when device is not connected."""
        mock_serial_service.is_connected = False
        
        with pytest.raises(ConnectionError, match="Device is not connected"):
            await device_manager.read_all_parameters()
    
    @pytest.mark.asyncio
    async def test_read_all_parameters_with_failures(self, device_manager):
        """Test read operation with some parameter failures."""
        # Mock device reader with some failures
        with patch.object(device_manager.device_reader, 'read_single_parameter') as mock_read:
            mock_read.side_effect = [
                "APN:test.apn,testuser,testpass",
                None,  # Failure for server_settings
                "GT06SEL=1"
            ]
            
            progress_callback = Mock()
            
            result = await device_manager.read_all_parameters(progress_callback)
            
            # Should have 2 successful reads
            assert len(result) == 2
            assert "apn_settings" in result
            assert "protocol" in result
            assert "server_settings" not in result
    
    @pytest.mark.asyncio
    async def test_write_all_parameters_success(self, device_manager, mock_serial_service):
        """Test successful writing of all parameters."""
        parameters = {
            "apn_settings": {
                "apn": "test.apn",
                "user": "testuser",
                "password": "testpass"
            },
            "server_settings": {
                "address": "192.168.1.1",
                "port": "8080"
            },
            "protocol": "1"
        }
        
        progress_callback = Mock()
        
        result = await device_manager.write_all_parameters(parameters, progress_callback)
        
        # Verify all parameters were processed
        assert len(result) == 3
        assert all(result.values())  # All should be successful
        
        # Verify serial commands were sent
        assert mock_serial_service.send_command.call_count == 3
    
    @pytest.mark.asyncio
    async def test_write_all_parameters_device_not_connected(self, device_manager, mock_serial_service):
        """Test write operation when device is not connected."""
        mock_serial_service.is_connected = False
        
        with pytest.raises(ConnectionError, match="Device is not connected"):
            await device_manager.write_all_parameters({"test": "value"})
    
    @pytest.mark.asyncio
    async def test_write_all_parameters_empty_parameters(self, device_manager):
        """Test write operation with empty parameters."""
        with pytest.raises(ValueError, match="No parameters provided for writing"):
            await device_manager.write_all_parameters({})
    
    @pytest.mark.asyncio
    async def test_write_all_parameters_validation_failure(self, device_manager, mock_spec_parser):
        """Test write operation with validation failures."""
        # Mock validation failure
        mock_spec = Mock()
        mock_spec.validate_value.return_value = ValidationResult(
            is_valid=False,
            errors=["Invalid value"]
        )
        
        mock_spec_parser.parse_specifications.return_value = {
            "test_param": mock_spec
        }
        
        # Mock has_write_command to return True
        with patch.object(device_manager, '_has_write_command', return_value=True):
            result = await device_manager.write_all_parameters({"test_param": "invalid_value"})
            
            # Should return empty result due to validation failure
            assert len(result) == 0
    
    def test_parse_device_response_apn(self, device_manager, mock_spec_parser):
        """Test parsing APN device response."""
        apn_spec = mock_spec_parser.parse_specifications()["apn_settings"]
        
        response = "APN:test.apn,testuser,testpass"
        result = device_manager.parse_device_response("APN#", response, apn_spec)
        
        assert result is not None
        assert "apn" in result
        assert result["apn"] == "test.apn"
        assert result["user"] == "testuser"
        assert result["password"] == "testpass"
    
    def test_parse_device_response_server(self, device_manager, mock_spec_parser):
        """Test parsing server device response."""
        server_spec = mock_spec_parser.parse_specifications()["server_settings"]
        
        response = "SERVER:0,192.168.1.1,8080,0"
        result = device_manager.parse_device_response("SERVER#", response, server_spec)
        
        assert result is not None
        assert "address" in result
        assert result["address"] == "192.168.1.1"
        assert result["port"] == "8080"
    
    def test_parse_device_response_protocol(self, device_manager, mock_spec_parser):
        """Test parsing protocol device response."""
        protocol_spec = mock_spec_parser.parse_specifications()["protocol"]
        
        response = "GT06SEL=1"
        result = device_manager.parse_device_response("CXCS#GT06SEL", response, protocol_spec)
        
        assert result is not None
        assert "protocol" in result
        assert result["protocol"] == "1"
    
    def test_parse_device_response_empty(self, device_manager, mock_spec_parser):
        """Test parsing empty device response."""
        apn_spec = mock_spec_parser.parse_specifications()["apn_settings"]
        
        result = device_manager.parse_device_response("APN#", "", apn_spec)
        assert result is None
        
        result = device_manager.parse_device_response("APN#", None, apn_spec)
        assert result is None
    
    def test_format_parameter_for_device_complex(self, device_manager, mock_spec_parser):
        """Test formatting complex parameter for device command."""
        apn_spec = mock_spec_parser.parse_specifications()["apn_settings"]
        
        value = {
            "apn": "test.apn",
            "user": "testuser",
            "password": "testpass"
        }
        
        # Mock the format_set_command method
        apn_spec.commands.format_set_command = Mock(return_value="APN,test.apn,testuser,testpass#")
        
        result = device_manager.format_parameter_for_device(apn_spec, value)
        
        assert result == "APN,test.apn,testuser,testpass#"
        apn_spec.commands.format_set_command.assert_called_once_with(value)
    
    def test_format_parameter_for_device_simple(self, device_manager, mock_spec_parser):
        """Test formatting simple parameter for device command."""
        protocol_spec = mock_spec_parser.parse_specifications()["protocol"]
        
        # Mock the format_set_command method
        protocol_spec.commands.format_set_command = Mock(return_value="SZCS#GT06SEL=1")
        
        result = device_manager.format_parameter_for_device(protocol_spec, "1")
        
        assert result == "SZCS#GT06SEL=1"
    
    def test_format_parameter_for_device_failure(self, device_manager, mock_spec_parser):
        """Test formatting parameter when formatting fails."""
        apn_spec = mock_spec_parser.parse_specifications()["apn_settings"]
        
        # Mock format_set_command to raise an exception
        apn_spec.commands.format_set_command = Mock(side_effect=Exception("Format error"))
        
        result = device_manager.format_parameter_for_device(apn_spec, {"test": "value"})
        
        assert result is None
    
    def test_cancel_operation(self, device_manager):
        """Test operation cancellation."""
        device_manager.cancel_operation()
        
        assert device_manager.is_operation_cancelled()
        assert device_manager._operation_cancelled
    
    def test_get_supported_parameters(self, device_manager, mock_spec_parser):
        """Test getting supported parameters."""
        result = device_manager.get_supported_parameters()
        
        # All mock parameters have read/write commands
        assert len(result) == 3
        assert "apn_settings" in result
        assert "server_settings" in result
        assert "protocol" in result
    
    def test_get_supported_parameters_exception(self, device_manager, mock_spec_parser):
        """Test getting supported parameters when parser fails."""
        mock_spec_parser.parse_specifications.side_effect = Exception("Parser error")
        
        result = device_manager.get_supported_parameters()
        
        assert result == []
    
    def test_has_read_command(self, device_manager, mock_spec_parser):
        """Test checking if parameter has read command."""
        apn_spec = mock_spec_parser.parse_specifications()["apn_settings"]
        
        assert device_manager._has_read_command(apn_spec)
        
        # Test with no read command
        no_read_spec = ParameterSpec(
            name="test",
            label="Test",
            section="Test",
            commands=ParameterCommands()
        )
        
        assert not device_manager._has_read_command(no_read_spec)
    
    def test_has_write_command(self, device_manager, mock_spec_parser):
        """Test checking if parameter has write command."""
        apn_spec = mock_spec_parser.parse_specifications()["apn_settings"]
        
        assert device_manager._has_write_command(apn_spec)
        
        # Test with no write command
        no_write_spec = ParameterSpec(
            name="test",
            label="Test",
            section="Test",
            commands=ParameterCommands()
        )
        
        assert not device_manager._has_write_command(no_write_spec)
    
    def test_get_read_command(self, device_manager, mock_spec_parser):
        """Test getting read command from specification."""
        apn_spec = mock_spec_parser.parse_specifications()["apn_settings"]
        
        result = device_manager._get_read_command(apn_spec)
        assert result == "APN#"
        
        # Test with read_level command
        level_spec = ParameterSpec(
            name="test",
            label="Test",
            section="Test",
            commands=ParameterCommands(read_level="TEST_LEVEL#")
        )
        
        result = device_manager._get_read_command(level_spec)
        assert result == "TEST_LEVEL#"
        
        # Test with no read command
        no_read_spec = ParameterSpec(
            name="test",
            label="Test",
            section="Test",
            commands=ParameterCommands()
        )
        
        result = device_manager._get_read_command(no_read_spec)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_execute_read_command_success(self, device_manager):
        """Test successful execution of read command."""
        with patch.object(device_manager.device_reader, 'read_single_parameter') as mock_read:
            mock_read.return_value = "TEST_RESPONSE"
            
            result = await device_manager._execute_read_command("TEST#", "test_param")
            
            assert result == "TEST_RESPONSE"
            mock_read.assert_called_once_with("TEST", timeout=5, max_retries=2)
    
    @pytest.mark.asyncio
    async def test_execute_read_command_failure(self, device_manager):
        """Test failed execution of read command."""
        with patch.object(device_manager.device_reader, 'read_single_parameter') as mock_read:
            mock_read.side_effect = Exception("Read error")
            
            result = await device_manager._execute_read_command("TEST#", "test_param")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_execute_write_command_success(self, device_manager, mock_serial_service):
        """Test successful execution of write command."""
        spec = ParameterSpec(
            name="test",
            label="Test",
            section="Test",
            commands=ParameterCommands(set_command="TEST,<value>#")
        )
        
        with patch.object(device_manager, 'format_parameter_for_device') as mock_format:
            mock_format.return_value = "TEST,123#"
            
            result = await device_manager._execute_write_command(spec, "test_param", "123")
            
            assert result is True
            mock_serial_service.send_command.assert_called_once_with("TEST,123#", "test_param")
    
    @pytest.mark.asyncio
    async def test_execute_write_command_format_failure(self, device_manager):
        """Test write command execution when formatting fails."""
        spec = ParameterSpec(
            name="test",
            label="Test",
            section="Test",
            commands=ParameterCommands(set_command="TEST,<value>#")
        )
        
        with patch.object(device_manager, 'format_parameter_for_device') as mock_format:
            mock_format.return_value = None
            
            result = await device_manager._execute_write_command(spec, "test_param", "123")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_execute_write_command_send_failure(self, device_manager, mock_serial_service):
        """Test write command execution when send fails."""
        spec = ParameterSpec(
            name="test",
            label="Test",
            section="Test",
            commands=ParameterCommands(set_command="TEST,<value>#")
        )
        
        mock_serial_service.send_command.return_value = False
        
        with patch.object(device_manager, 'format_parameter_for_device') as mock_format:
            mock_format.return_value = "TEST,123#"
            
            result = await device_manager._execute_write_command(spec, "test_param", "123")
            
            assert result is False
    
    def test_map_response_to_fields_complex(self, device_manager, mock_spec_parser):
        """Test mapping response to fields for complex parameter."""
        apn_spec = mock_spec_parser.parse_specifications()["apn_settings"]
        
        parsed_data = {
            "value_0": "test.apn",
            "value_1": "testuser",
            "value_2": "testpass"
        }
        
        result = device_manager._map_response_to_fields(parsed_data, apn_spec)
        
        assert result["apn"] == "test.apn"
        assert result["user"] == "testuser"
        assert result["password"] == "testpass"
    
    def test_map_response_to_fields_simple(self, device_manager, mock_spec_parser):
        """Test mapping response to fields for simple parameter."""
        protocol_spec = mock_spec_parser.parse_specifications()["protocol"]
        
        parsed_data = {"value": "1"}
        
        result = device_manager._map_response_to_fields(parsed_data, protocol_spec)
        
        # Simple parameter should return as-is
        assert result == parsed_data
    
    def test_parse_response_basic_apn(self, device_manager, mock_spec_parser):
        """Test basic response parsing for APN."""
        apn_spec = mock_spec_parser.parse_specifications()["apn_settings"]
        
        result = device_manager._parse_response_basic("APN:test.apn,user,pass", apn_spec)
        
        assert result["apn"] == "test.apn"
        assert result["user"] == "user"
        assert result["password"] == "pass"
    
    def test_parse_response_basic_server(self, device_manager, mock_spec_parser):
        """Test basic response parsing for server."""
        server_spec = mock_spec_parser.parse_specifications()["server_settings"]
        
        result = device_manager._parse_response_basic("SERVER:0,192.168.1.1,8080,0", server_spec)
        
        assert result["address"] == "192.168.1.1"
        assert result["port"] == "8080"
    
    def test_parse_response_basic_protocol(self, device_manager, mock_spec_parser):
        """Test basic response parsing for protocol."""
        protocol_spec = mock_spec_parser.parse_specifications()["protocol"]
        
        result = device_manager._parse_response_basic("GT06SEL=1", protocol_spec)
        
        assert result["protocol"] == "1"
    
    def test_parse_response_basic_tcp_ack(self, device_manager, mock_spec_parser):
        """Test basic response parsing for TCP ACK."""
        tcp_spec = ParameterSpec(
            name="tcp_ack",
            label="TCP ACK",
            section="Test"
        )
        
        result = device_manager._parse_response_basic("POSBYACK=1", tcp_spec)
        
        assert result["tcp_ack"] == "1"
    
    def test_parse_response_basic_default(self, device_manager):
        """Test basic response parsing default case."""
        unknown_spec = ParameterSpec(
            name="unknown",
            label="Unknown",
            section="Test"
        )
        
        result = device_manager._parse_response_basic("UNKNOWN_RESPONSE", unknown_spec)
        
        assert result["value"] == "UNKNOWN_RESPONSE"


if __name__ == "__main__":
    pytest.main([__file__])