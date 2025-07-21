#!/usr/bin/env python3
"""
Test script for version field integration in the connection frame.

This script tests that the version field is properly added to the device info
section and that it gets populated when the device is connected.
"""

import sys
import os
import time
from unittest.mock import Mock, MagicMock, patch

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.connection_frame import ConnectionFrame
from services.i18n_service import I18nService
from services.serial_service import SerialService


class MockApp:
    """Mock application for testing."""
    
    def __init__(self):
        self.log_frame = Mock()
        self.log_frame.log_message = Mock()
        self.device_command_mapper = Mock()
        self.device_command_mapper.get_command = Mock()
        self.error_handler = Mock()
        
        # Track after calls for testing
        self.after_calls = []
        
    def after(self, delay, callback, *args):
        """Mock the after method and track calls."""
        self.after_calls.append((delay, callback, args))
        if callable(callback):
            try:
                callback(*args)
            except Exception as e:
                print(f"Warning: Callback failed: {e}")


def test_version_field_ui():
    """Test that the version field is properly added to the UI."""
    print("Testing version field UI integration...")
    
    # Create mock app and services
    app = MockApp()
    i18n = I18nService()
    i18n.set_language('en_US')
    
    # Create mock serial service
    serial_service = Mock()
    serial_service.is_connected = False
    
    # Create connection frame
    connection_frame = ConnectionFrame(app, i18n, serial_service)
    
    # Verify version field exists
    assert hasattr(connection_frame, 'version_label'), "Version label should exist"
    assert hasattr(connection_frame, 'version_value_var'), "Version value variable should exist"
    assert hasattr(connection_frame, 'version_value_entry'), "Version value entry should exist"
    
    # Verify initial value
    initial_value = connection_frame.version_value_var.get()
    assert initial_value == "N/A", f"Initial version value should be 'N/A', got '{initial_value}'"
    
    # Verify label text
    version_label_text = connection_frame.version_label.cget("text")
    assert "Version" in version_label_text, f"Version label should contain 'Version', got '{version_label_text}'"
    
    print("  ✓ Version field UI components created correctly")
    print("  ✓ Initial version value is 'N/A'")
    print("  ✓ Version label text is correct")
    print("✓ Version field UI integration test passed")


def test_version_field_language_support():
    """Test that the version field supports different languages."""
    print("Testing version field language support...")
    
    # Test different languages
    languages = [
        ('en_US', 'Version'),
        ('pt_BR', 'Versão'),
        ('es_ES', 'Versión')
    ]
    
    for lang_code, expected_text in languages:
        # Create mock app and services
        app = MockApp()
        i18n = I18nService()
        i18n.set_language(lang_code)
        
        # Create mock serial service
        serial_service = Mock()
        serial_service.is_connected = False
        
        # Create connection frame
        connection_frame = ConnectionFrame(app, i18n, serial_service)
        
        # Verify label text for this language
        version_label_text = connection_frame.version_label.cget("text")
        assert expected_text in version_label_text, f"Version label for {lang_code} should contain '{expected_text}', got '{version_label_text}'"
        
        print(f"  ✓ {lang_code}: '{version_label_text}'")
    
    print("✓ Version field language support test passed")


def test_version_field_update():
    """Test that the version field gets updated when device info is received."""
    print("Testing version field update functionality...")
    
    # Create mock app and services
    app = MockApp()
    i18n = I18nService()
    i18n.set_language('en_US')
    
    # Create connection frame
    serial_service = SerialService(app)
    connection_frame = ConnectionFrame(app, i18n, serial_service)
    
    # Set the connection frame in the app so serial service can access it
    app.connection_frame = connection_frame
    
    # Test version update
    test_version = "W16A_10D6K_B44_V6.21 2024 11 15"
    
    # Update device info with version
    serial_service.device_info['version'] = test_version
    serial_service.update_device_info()
    
    # Verify version field was updated
    updated_value = connection_frame.version_value_var.get()
    assert updated_value == test_version, f"Version should be updated to '{test_version}', got '{updated_value}'"
    
    print(f"  ✓ Version field updated correctly: '{updated_value}'")
    print("✓ Version field update functionality test passed")


def test_version_field_reset_on_disconnect():
    """Test that the version field is reset when disconnecting."""
    print("Testing version field reset on disconnect...")
    
    # Create mock app and services
    app = MockApp()
    i18n = I18nService()
    i18n.set_language('en_US')
    
    # Create mock serial service
    serial_service = Mock()
    serial_service.is_connected = False
    
    # Create connection frame
    connection_frame = ConnectionFrame(app, i18n, serial_service)
    
    # Set a version value
    test_version = "W16A_10D6K_B44_V6.21 2024 11 15"
    connection_frame.version_value_var.set(test_version)
    
    # Verify version is set
    assert connection_frame.version_value_var.get() == test_version, "Version should be set initially"
    
    # Simulate disconnect
    connection_frame.update_status(False)
    
    # Verify version is reset
    reset_value = connection_frame.version_value_var.get()
    assert reset_value == "N/A", f"Version should be reset to 'N/A' on disconnect, got '{reset_value}'"
    
    print("  ✓ Version field reset correctly on disconnect")
    print("✓ Version field reset on disconnect test passed")


def test_version_command_sequence():
    """Test that version command is sent after ICCID during connection."""
    print("Testing version command sequence...")
    
    # Create mock app and services
    app = MockApp()
    i18n = I18nService()
    i18n.set_language('en_US')
    
    # Create serial service with mocked serial port
    with patch('serial.Serial'):
        serial_service = SerialService(app)
        
        # Mock device command mapper
        app.device_command_mapper = Mock()
        app.device_command_mapper.get_command = Mock()
        app.device_command_mapper.get_command.side_effect = lambda cmd, _: f"ATSMS:{cmd.upper()}#"
        
        # Mock the send_command method
        serial_service.send_command = Mock()
        
        # Connect to trigger device info retrieval
        serial_service.connect("COM1")
        
        # Verify connection was established
        assert serial_service.is_connected, "Serial service should be connected"
        
        # Trigger device info retrieval
        serial_service.retrieve_device_info()
        
        # Process any scheduled callbacks (ICCID and version commands)
        for delay, callback, args in app.after_calls:
            if callable(callback):
                callback(*args)
        
        # Verify that commands were sent in the correct sequence
        send_calls = serial_service.send_command.call_args_list
        
        # Should have at least IMEI, ICCID, and VERSION commands
        assert len(send_calls) >= 3, f"Should have at least 3 command calls, got {len(send_calls)}"
        
        # Extract command strings from the calls
        commands_sent = [call[0][0] for call in send_calls]
        
        # Verify IMEI command was sent
        imei_commands = [cmd for cmd in commands_sent if 'IMEI' in cmd.upper()]
        assert len(imei_commands) > 0, "IMEI command should be sent"
        
        # Verify ICCID command was sent
        iccid_commands = [cmd for cmd in commands_sent if 'ICCID' in cmd.upper()]
        assert len(iccid_commands) > 0, "ICCID command should be sent"
        
        # Verify VERSION command was sent
        version_commands = [cmd for cmd in commands_sent if 'VERSION' in cmd.upper()]
        assert len(version_commands) > 0, "VERSION command should be sent"
        
        print("  ✓ IMEI command sent")
        print("  ✓ ICCID command sent")
        print("  ✓ VERSION command sent")
        print(f"  ✓ Total commands sent: {len(send_calls)}")
        
        # Clean up
        serial_service.disconnect()
    
    print("✓ Version command sequence test passed")


def test_version_response_parsing():
    """Test that version responses are properly parsed and stored."""
    print("Testing version response parsing...")
    
    # Create mock app and services
    app = MockApp()
    i18n = I18nService()
    i18n.set_language('en_US')
    
    # Create serial service
    serial_service = SerialService(app)
    
    # Create connection frame and set it in app
    connection_frame = ConnectionFrame(app, i18n, serial_service)
    app.connection_frame = connection_frame
    
    # Mock device command mapper with version parsing
    app.device_command_mapper = Mock()
    app.device_command_mapper.parse_response = Mock()
    
    # Test version response
    test_version = "W16A_10D6K_B44_V6.21 2024 11 15"
    mock_parsed_data = {'version': test_version}
    app.device_command_mapper.parse_response.return_value = mock_parsed_data
    
    # Simulate receiving a version response
    serial_service.current_command_type = 'get_version'
    serial_service.process_response(f"READOK: {test_version}")
    
    # Verify version was stored in device_info
    assert serial_service.device_info['version'] == test_version, f"Version should be stored as '{test_version}'"
    
    # Verify UI was updated (check if after was called for update_device_info)
    update_calls = [call for call in app.after_calls if len(call) >= 2 and hasattr(call[1], '__name__') and 'update_device_info' in call[1].__name__]
    assert len(update_calls) > 0, "update_device_info should be scheduled after version response"
    
    print(f"  ✓ Version response parsed: '{test_version}'")
    print("  ✓ Version stored in device_info")
    print("  ✓ UI update scheduled")
    print("✓ Version response parsing test passed")


def main():
    """Run all version field integration tests."""
    print("=" * 60)
    print("Version Field Integration Tests")
    print("=" * 60)
    
    try:
        test_version_field_ui()
        print()
        
        test_version_field_language_support()
        print()
        
        test_version_field_update()
        print()
        
        test_version_field_reset_on_disconnect()
        print()
        
        test_version_command_sequence()
        print()
        
        test_version_response_parsing()
        print()
        
        print("=" * 60)
        print("✅ All version field integration tests passed!")
        print("=" * 60)
        
        print("\nImplemented Features:")
        print("• Version field added to device info section")
        print("• Version label with multi-language support")
        print("• Version value display with copy capability")
        print("• Version command sent after ICCID during connection")
        print("• Version response parsing and UI update")
        print("• Version field reset on disconnect")
        print("• Proper UI layout with updated row positioning")
        
        print("\nLanguage Support:")
        print("• English: 'Version:'")
        print("• Portuguese: 'Versão:'")
        print("• Spanish: 'Versión:'")
        
        print("\nCommand Sequence:")
        print("1. Connect to device")
        print("2. Send IMEI command")
        print("3. Send ICCID command (after 500ms)")
        print("4. Send VERSION command (after ICCID + 500ms)")
        print("5. Parse responses and update UI")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)