import unittest
from services.device_command_mapper import DeviceCommandMapper

class TestTransmissionMode(unittest.TestCase):
    """Test that transmission mode is always TCP."""
    
    def setUp(self):
        """Set up the test environment."""
        self.device_command_mapper = DeviceCommandMapper()
    
    def test_transmission_mode_always_tcp(self):
        """Test that transmission mode is always TCP regardless of input value."""
        # Test with TCP value
        tcp_command = self.device_command_mapper.get_command('transmission_mode', 'TCP')
        self.assertIn('PROTOCOL=0', tcp_command)  # 0 is TCP
        
        # Test with UDP value (should still return TCP)
        udp_command = self.device_command_mapper.get_command('transmission_mode', 'UDP')
        self.assertIn('PROTOCOL=0', udp_command)  # Should still be 0 (TCP)
        
        # Test with any other value (should still return TCP)
        other_command = self.device_command_mapper.get_command('transmission_mode', 'OTHER')
        self.assertIn('PROTOCOL=0', other_command)  # Should still be 0 (TCP)
        
        print("Transmission mode is always TCP test passed!")
    
    def test_bulk_commands_include_tcp(self):
        """Test that bulk commands always include TCP transmission mode."""
        # Create parameters without transmission_mode
        parameters = {
            'server_ip': '192.168.1.1',
            'server_port': '8080'
        }
        
        # Get bulk commands
        commands = self.device_command_mapper.get_bulk_commands(parameters)
        
        # Check that the first command is for transmission mode and sets it to TCP
        self.assertTrue(any('PROTOCOL=0' in cmd for cmd in commands))
        
        print("Bulk commands include TCP test passed!")

if __name__ == "__main__":
    unittest.main()