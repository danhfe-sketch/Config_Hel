import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import datetime
from collections import deque

# Add the project root to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mock necessary modules that might cause issues in a test environment
sys.modules['tkinter'] = MagicMock()
sys.modules['tkinter.filedialog'] = MagicMock()
sys.modules['pyperclip'] = MagicMock()

class MockLogFrame:
    def __init__(self, master, i18n, serial_service):
        self.master = master
        self.i18n = i18n
        self.serial_service = serial_service
        self.log_entries = deque(maxlen=1000)
        self.log_buffer = [] # This is not used in the original code, but keeping it for consistency

    def log_message(self, message):
        """Mock implementation of log_message."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_entries.append((timestamp, message))

    def format_log_for_export(self, log_content):
        """
        Format the log content for export with timestamps and categories.
        This is a simplified version for testing.
        """
        formatted_lines = []
        for timestamp, message in self.log_entries:
            category = "APP" # Default category
            content = message.strip()

            if message.startswith("DEV:"):
                category = "DEV"
                content = message[4:].strip()
            elif message.startswith("INFO:"):
                category = "INFO"
                content = message[5:].strip()
            elif message.startswith("ERROR:"):
                category = "ERROR"
                content = message[6:].strip()
            elif message.startswith("WARNING:"):
                category = "WARNING"
                content = message[9:].strip()
            elif message.startswith("DEBUG:"):
                category = "DEBUG"
                content = message[6:].strip()
            
            formatted_lines.append(f"[{timestamp}] [{category}] {content}")
        return "\n".join(formatted_lines)

    def export_log(self):
        """Mock implementation of export_log."""
        from tkinter import filedialog

        log_content = self.format_log_for_export(self.log_entries)
        if not log_content:
            self.log_message("WARNING: No log content to export\n")
            return

        default_filename = f"LT32Pro_Log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            title=self.i18n.get("export_log"),
            initialfile=default_filename
        )

        if not file_path:
            return # User cancelled the dialog

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("LT32Pro Device Configurator - Log Export\n")
                f.write(f"Export Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                
                if self.serial_service and self.serial_service.device_info:
                    if self.serial_service.device_info.get('imei'):
                        f.write(f"Device IMEI: {self.serial_service.device_info['imei']}\n")
                    if self.serial_service.device_info.get('iccid'):
                        f.write(f"Device ICCID: {self.serial_service.device_info['iccid']}\n")
                f.write("-" * 50 + "\n\n")
                f.write(log_content)
            self.log_message(f"INFO: Log exported successfully to {os.path.basename(file_path)}\n")
        except Exception as e:
            self.log_message(f"ERROR: Failed to export log: {str(e)}\n")


class TestLogExport(unittest.TestCase):
    def setUp(self):
        """Set up the test environment."""
        self.mock_master = MagicMock()
        self.mock_i18n = MagicMock()
        self.mock_i18n.get.return_value = "Export Log" # Default return for i18n.get
        self.mock_serial_service = MagicMock()
        self.mock_serial_service.device_info = {'imei': '123456789012345', 'iccid': '98765432109876543210'}

        self.log_frame = MockLogFrame(self.mock_master, self.mock_i18n, self.mock_serial_service)

    @patch('tkinter.filedialog.asksaveasfilename')
    def test_export_log_success(self, mock_asksaveasfilename):
        """Test successful log export."""
        mock_asksaveasfilename.return_value = "test_log.txt"
        
        # Mock open for writing
        mock_open = MagicMock(spec=open)
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        with patch('builtins.open', mock_open):
            self.log_frame.log_message("INFO: Test log entry 1\n")
            self.log_frame.log_message("DEV: Device response\n")
            self.log_frame.export_log()

            self.mock_i18n.get.assert_called_with("export_log")
            mock_asksaveasfilename.assert_called_once()
            mock_open.assert_called_once_with("test_log.txt", 'w', encoding='utf-8')
            mock_file.write.assert_called()
            self.log_frame.log_entries.clear() # Clear entries after export

    @patch('tkinter.filedialog.asksaveasfilename')
    def test_export_log_cancel(self, mock_asksaveasfilename):
        """Test log export when user cancels the dialog."""
        mock_asksaveasfilename.return_value = "" # User cancels
        
        self.log_frame.log_message("INFO: Test log entry 1\n")
        self.log_frame.export_log()

        self.mock_i18n.get.assert_called_with("export_log")
        mock_asksaveasfilename.assert_called_once()
        # Ensure no file operations were attempted
        with patch('builtins.open') as mock_open:
            self.log_frame.export_log()
            mock_open.assert_not_called()

    @patch('tkinter.filedialog.asksaveasfilename')
    def test_export_log_no_content(self, mock_asksaveasfilename):
        """Test exporting an empty log."""
        mock_asksaveasfilename.return_value = "empty_log.txt"

        self.log_frame.export_log()
        self.log_frame.log_message.assert_called_with("WARNING: No log content to export\n")
        mock_asksaveasfilename.assert_not_called() # Dialog should not be opened

    @patch('tkinter.filedialog.asksaveasfilename')
    def test_export_log_with_exception(self, mock_asksaveasfilename):
        """Test handling exceptions during log export."""
        mock_asksaveasfilename.return_value = "error_log.txt"
        
        # Mock open to raise an exception
        with patch('builtins.open', side_effect=IOError("Disk full")):
            self.log_frame.log_message("INFO: Test log entry\n")
            self.log_frame.export_log()
            self.log_frame.log_message.assert_called_with("ERROR: Failed to export log: Disk full\n")

    def test_format_log_for_export(self):
        """Test the log formatting for export."""
        self.log_frame.log_entries.clear() # Clear any existing entries
        self.log_frame.log_message("INFO: App started\n")
        self.log_frame.log_message("DEV: Device data\n")
        self.log_frame.log_message("ERROR: Something went wrong\n")
        self.log_frame.log_message("WARNING: Low battery\n")
        self.log_frame.log_message("DEBUG: Debug info\n")
        self.log_frame.log_message("Plain message\n")

        formatted_log = self.log_frame.format_log_for_export(self.log_frame.log_entries)
        
        # Check that timestamps are included
        self.assertRegex(formatted_log, r"^\\[\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}\\]")
        
        # Check that all categories are included and content is correct
        self.assertIn("[INFO] App started", formatted_log)
        self.assertIn("[DEV] Device data", formatted_log)
        self.assertIn("[ERROR] Something went wrong", formatted_log)
        self.assertIn("[WARNING] Low battery", formatted_log)
        self.assertIn("[DEBUG] Debug info", formatted_log)
        self.assertIn("[APP] Plain message", formatted_log) # Default category

if __name__ == '__main__':
    unittest.main()
