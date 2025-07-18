import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import time

# Add the project root to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.serial_service import SerialService
from services.device_command_mapper import DeviceCommandMapper

class TestBulkOperations(unittest.TestCase):
    """Test the bulk command operations functionality."""

    def setUp(self):
        """Set up the test environment."""
        # Create mock app
        self.app = MagicMock()
        self.app.log_frame = MagicMock()
        
        # Create device command mapper
        self.device_command_mapper = DeviceCommandMapper()
        self.app.device_command_mapper = self.device_command_mapper
        
        # Create serial service
        self.serial_service = SerialService(self.app)
        self.serial_service.is_connected = True  # Simulate connected state
        
        # Mock the send_command method
        self.serial_service.send_command = MagicMock()
        
    def test_queue_command(self):
        """Test adding a command to the queue."""
        self.serial_service.queue_command("ATSMS:TEST#", "test")
        self.assertEqual(self.serial_service.command_queue.qsize(), 1)
        
        # Get the command from the queue
        cmd, cmd_type = self.serial_service.command_queue.get()
        self.assertEqual(cmd, "ATSMS:TEST#")
        self.assertEqual(cmd_type, "test")
        
    def test_queue_commands(self):
        """Test adding multiple commands to the queue."""
        commands = ["ATSMS:TEST1#", "ATSMS:TEST2#", "ATSMS:TEST3#"]
        command_types = ["test1", "test2", "test3"]
        
        # Mock the start_queue_processing method
        self.serial_service.start_queue_processing = MagicMock()
        
        # Queue the commands
        self.serial_service.queue_commands(commands, command_types)
        
        # Check that the queue has the correct number of commands
        self.assertEqual(self.serial_service.command_queue.qsize(), 3)
        
        # Check that start_queue_processing was called
        self.serial_service.start_queue_processing.assert_called_once()
        
    def test_process_command_queue(self):
        """Test processing commands from the queue."""
        # Setup test data
        commands = ["ATSMS:TEST1#", "ATSMS:TEST2#", "ATSMS:TEST3#"]
        command_types = ["test1", "test2", "test3"]
        
        # Add commands to the queue
        for i, cmd in enumerate(commands):
            self.serial_service.queue_command(cmd, command_types[i])
            
        # Set a very short delay for testing
        self.serial_service.queue_delay = 0.01
        
        # Process the queue in a separate thread
        self.serial_service.queue_processing = True
        thread = threading.Thread(target=self.serial_service._process_command_queue)
        thread.daemon = True
        thread.start()
        
        # Wait for the queue to be processed
        time.sleep(0.1)
        
        # Check that send_command was called for each command
        self.assertEqual(self.serial_service.send_command.call_count, 3)
        
        # Check the arguments for each call
        calls = self.serial_service.send_command.call_args_list
        for i, call in enumerate(calls):
            args, kwargs = call
            self.assertEqual(args[0], commands[i])
            self.assertEqual(args[1], command_types[i])
            
    def test_send_all_parameters(self):
        """Test sending all parameters to the device."""
        # Mock the _collect_parameters_from_ui method
        self.serial_service._collect_parameters_from_ui = MagicMock(return_value={
            'apn_server': 'internet',
            'apn_user': 'user',
            'apn_password': 'password',
            'timer_ign_on': '30',
            'timer_ign_off': '300'
        })
        
        # Mock the queue_commands method
        self.serial_service.queue_commands = MagicMock()
        
        # Call the method
        self.serial_service.send_all_parameters()
        
        # Check that queue_commands was called
        self.serial_service.queue_commands.assert_called_once()
        
        # Check that the first argument is a list of commands
        args, kwargs = self.serial_service.queue_commands.call_args
        self.assertIsInstance(args[0], list)
        
    def test_check_device_configuration(self):
        """Test checking device configuration."""
        # Mock the queue_commands method
        self.serial_service.queue_commands = MagicMock()
        
        # Call the method
        self.serial_service.check_device_configuration()
        
        # Check that queue_commands was called
        self.serial_service.queue_commands.assert_called_once()
        
        # Check that the first argument is a list of commands
        args, kwargs = self.serial_service.queue_commands.call_args
        self.assertIsInstance(args[0], list)
        
    def test_process_device_response(self):
        """Test processing device responses."""
        # Set up test data
        self.serial_service.current_command_type = 'get_imei'
        self.serial_service.queue_processing = True
        
        # Process a response
        self.serial_service.process_device_response("IMEI: 123456789012345")
        
        # Check that the IMEI was extracted
        self.assertEqual(self.serial_service.device_info['imei'], "123456789012345")
        
        # Check that the queue results were updated
        self.assertIn('imei', self.serial_service.queue_results)
        
if __name__ == '__main__':
    import threading  # Import here to avoid issues with the mock
    unittest.main()