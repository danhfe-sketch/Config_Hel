import serial
import serial.tools.list_ports
import threading
import time
import re
import queue
from typing import Dict, Any, List, Optional, Callable
import datetime
from services.configuration_reader_service import ConfigurationReaderService

class SerialService:
    """Handles all serial communication in a separate thread."""

    def __init__(self, app_instance):
        self.app = app_instance
        self.serial_port = None
        self.is_connected = False
        self.read_thread = None
        self.stop_thread = False

        # Device info
        self.device_info = {
            'imei': None,
            'teriid': None,
            'iccid': None,
            'version': None
        }
        self.response_buffer = []
        self.waiting_for_response = False
        self.current_command_type = None

        # Command queue for bulk operations
        self.command_queue = queue.Queue()
        self.queue_processing = False
        self.queue_thread = None
        self.queue_delay = 0.5  # Delay between commands in seconds
        self.queue_callback = None
        self.queue_results = {}  # Store results from command queue execution
        self._waiting_for_teriid_response = False
        self._teriid_diagnostic_logged = False
        # How long to wait for a device response between queued commands
        self.queue_response_timeout = 20.0  # seconds

        # Connection monitoring
        self.last_activity_time = None
        self.connection_monitor_thread = None
        self.stop_monitor = False
        self.connection_timeout = 3600  # seconds without activity before checking connection (1 hour)

        # Configuration reader service
        self.configuration_reader = None

    def initialize_configuration_reader(self):
        """Initialize the configuration reader service with i18n support."""
        if hasattr(self.app, 'i18n') and self.configuration_reader is None:
            self.configuration_reader = ConfigurationReaderService(self.app, self.app.i18n)

    @staticmethod
    def list_com_ports():
        """Returns a list of available COM ports with descriptions."""
        ports = serial.tools.list_ports.comports()
        return [f"{port.device} - {port.description}" for port in ports] if ports else ["N/A"]

    def connect(self, port, baudrate=115200):
        """Connects to the specified serial port."""
        if self.is_connected:
            self.disconnect()

        try:
            # Extract port device name from "COMx - Description"
            port_device = port.split(' - ')[0]
            self.serial_port = serial.Serial(port_device, baudrate, timeout=1)
            self.is_connected = True
            self.stop_thread = False
            
            # Reset device info when connecting
            self.device_info = {
                'imei': None,
                'teriid': None,
                'iccid': None,
                'version': None
            }
            
            # Initialize connection monitoring
            self.last_activity_time = datetime.datetime.now()
            self.stop_monitor = False
            
            # Start read thread
            self.read_thread = threading.Thread(target=self.read_from_port, daemon=True)
            self.read_thread.start()
            
            # Connection monitoring disabled to prevent timeout issues
            # self.connection_monitor_thread = threading.Thread(target=self.monitor_connection, daemon=True)
            # self.connection_monitor_thread.start()
            
            # Log successful connection with detailed message
            self.app.log_frame.log_message(f"INFO: Successfully connected to {port} at {baudrate} baud\n")
            self.app.connection_frame.update_status(True)
            
            # Update connection status with visual indicator
            if hasattr(self.app, 'connection_frame'):
                self.app.connection_frame.update_connection_indicator(True)
            
            return True  # Return True on success
                
        except serial.SerialException as e:
            # Use error handling service if available
            if hasattr(self.app, 'error_handler'):
                error_type, context = self.app.error_handler.parse_error_from_exception(e)
                context['port'] = port
                self.app.error_handler.handle_error(
                    error_type, 
                    self.app.error_handler.SEVERITY_ERROR, 
                    context
                )
            else:
                # Fallback to basic error logging
                error_msg = str(e)
                if "PermissionError" in error_msg:
                    self.app.log_frame.log_message(f"ERROR: Access denied to port {port}. The port may be in use by another application.\n")
                elif "FileNotFoundError" in error_msg:
                    self.app.log_frame.log_message(f"ERROR: Port {port} not found. Please check your device connection.\n")
                else:
                    self.app.log_frame.log_message(f"ERROR: Failed to connect to {port}: {error_msg}\n")
            
            self.app.connection_frame.update_status(False)
            
            # Update connection status with visual indicator
            if hasattr(self.app, 'connection_frame'):
                self.app.connection_frame.update_connection_indicator(False)
            
            return False  # Return False on failure

    def disconnect(self):
        """Disconnects from the serial port."""
        if self.is_connected and self.serial_port:
            self.stop_thread = True
            self.stop_monitor = True
            
            # Stop any reconnection attempts if error handler exists
            if hasattr(self.app, 'error_handler'):
                self.app.error_handler.stop_reconnection()
                
            # Wait for threads to terminate
            if self.read_thread and self.read_thread.is_alive():
                self.read_thread.join(timeout=1)
            # Connection monitoring disabled
            # if self.connection_monitor_thread and self.connection_monitor_thread.is_alive():
            #     self.connection_monitor_thread.join(timeout=1)
                
            # Close the port
            self.serial_port.close()
            self.is_connected = False
            
            # Log disconnection with clear message
            self.app.log_frame.log_message("INFO: Device disconnected\n")
            self.app.connection_frame.update_status(False)
            
            # Update connection status with visual indicator
            if hasattr(self.app, 'connection_frame'):
                self.app.connection_frame.update_connection_indicator(False)

    def read_from_port(self):
        """Reads data from the serial port and logs it to the UI."""
        while not self.stop_thread and self.is_connected:
            try:
                if self.serial_port.in_waiting > 0:
                    line = self.serial_port.readline().decode('latin-1').strip()
                    if line:
                        # Update last activity timestamp
                        self.update_last_activity()
                        
                        # Safely update UI from a different thread
                        self.app.after(0, self.app.log_frame.log_message, f"DEV: {line}\n")
                        
                        # Process device response for information extraction
                        self.process_device_response(line)
                        
                        # Update connection indicator to show activity
                        if hasattr(self.app, 'connection_frame'):
                            self.app.after(0, self.app.connection_frame.flash_activity_indicator)
            except (serial.SerialException, TypeError) as e:
                # Use error handling service if available
                if hasattr(self.app, 'error_handler'):
                    error_type, context = self.app.error_handler.parse_error_from_exception(e)
                    if hasattr(self.serial_port, 'port'):
                        context['port'] = self.serial_port.port
                    self.app.after(0, self.app.error_handler.handle_error,
                                  error_type, 
                                  self.app.error_handler.SEVERITY_ERROR, 
                                  context)
                else:
                    # Fallback to basic error handling
                    self.app.after(0, self.app.log_frame.log_message, 
                                  f"ERROR: Serial communication error: {str(e)}\n")
                
                # Disconnect properly
                self.app.after(0, self._handle_connection_lost)
                break
            time.sleep(0.1)

    def send_command(self, command, command_type=None, bypass_validation=False):
        """
        Sends a command to the serial port with optional validation.
        
        Args:
            command: The command string to send
            command_type: Optional type of command for response processing
            bypass_validation: If True, skip command validation (for debugging/testing)
        """
        # Check if we're in a cancellation state
        if (hasattr(self, 'configuration_reader') and 
            self.configuration_reader is not None and
            hasattr(self.configuration_reader, 'cancel_requested') and 
            self.configuration_reader.cancel_requested):
            self.app.log_frame.log_message("INFO: Command not sent - operation was canceled\n")
            return False

        # Block new commands if a bulk operation is in progress, but allow
        # the internal queue processing thread to send commands.
        if self.queue_processing:
            try:
                current = threading.current_thread()
                # If the call originates from the queue thread, allow it.
                if hasattr(self, 'queue_thread') and current is self.queue_thread:
                    pass
                else:
                    self.app.log_frame.log_message(f"INFO: Command '{command}' blocked - bulk operation in progress\n")
                    return False
            except Exception:
                # On any error determining the thread, conservatively block external sends
                self.app.log_frame.log_message(f"INFO: Command '{command}' blocked - bulk operation in progress\n")
                return False
                
        if not self.is_connected or not self.serial_port:
            self.app.log_frame.log_message("ERROR: Not connected to device\n")
            return False
        
        # Validate command before sending (unless bypassed)
        if not bypass_validation and hasattr(self.app, 'command_validation_gateway'):
            from services.command_validation_gateway import ValidationContext
            
            # Create validation context
            context = ValidationContext(
                command_type=command_type or 'unknown',
                source='serial_service',
                timestamp=datetime.datetime.now()
            )
            
            # Validate the command
            validation_result = self.app.command_validation_gateway.validate_command_before_send(command, context)
            
            if not validation_result.is_valid:
                # Command failed validation - block it
                error_msg = f"Command blocked by validation: {validation_result.error_message}"
                self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
                
                # Log detailed information about the blocked command
                self.app.command_validation_gateway.log_blocked_command(validation_result, context)
                
                # Show suggestions if available
                if validation_result.suggestions:
                    suggestions_text = "; ".join(validation_result.suggestions)
                    self.app.log_frame.log_message(f"SUGGESTIONS: {suggestions_text}\n")
                
                return False
            
            # Log successful validation to console
            if validation_result.extracted_parameters:
                param_info = ", ".join([f"{k}={v}" for k, v in validation_result.extracted_parameters.items() if not k.startswith('_')])
                if param_info:
                    print(f"INFO: Command validated - Parameters: {param_info}")
        
        # Send the command
        try:
            # Ensure command has ATSMS: prefix for consistency across the codebase
            send_command = command
            if not isinstance(send_command, str):
                send_command = str(send_command)
            if not send_command.startswith("ATSMS:"):
                # Preserve original command in logs but send a prefixed command to device
                prefixed = f"ATSMS:{send_command}"
            else:
                prefixed = send_command
    
            encoded_command = f"{prefixed}\r\n".encode('utf-8')
            # Log both what we intended to send and the final bytes for transparency
            try:
                self.app.log_frame.log_message(f"DEBUG: Sending command (original): {command}\n")
                self.app.log_frame.log_message(f"DEBUG: Sending bytes: {encoded_command!r}\n")
            except Exception:
                print(f"DEBUG: Sending command (original): {command}")
                print(f"DEBUG: Sending bytes: {encoded_command!r}")
    
            self.serial_port.write(encoded_command)
            # Log the human-readable command that was sent to the device
            try:
                self.app.log_frame.log_message(f"APP: {prefixed}\n")
            except Exception:
                print(f"APP: {prefixed}")
            
            # Set the current command type for response processing
            self.current_command_type = command_type
            self.waiting_for_response = True
            
            return True
            
        except Exception as e:
            self.app.log_frame.log_message(f"ERROR: Failed to send command: {str(e)}\n")
            return False
            
    def process_device_response(self, response):
        """
        Process device responses and extract relevant information.
        
        Args:
            response: The response string from the device
        """
        # Add response to buffer for LT32ProDeviceReader and other components that need direct access
        self.response_buffer.append(response)
        
        # Check for cancellation before forwarding response
        config_reader_service = None
        if hasattr(self, 'configuration_reader') and self.configuration_reader:
            config_reader_service = self.configuration_reader
        elif hasattr(self.app, 'configuration_reader_service'):
            config_reader_service = self.app.configuration_reader_service
            
        # If we have a configuration reader service, check for cancellation
        if config_reader_service and hasattr(config_reader_service, 'cancel_requested') and config_reader_service.cancel_requested:
            self.app.log_frame.log_message(f"INFO: Ignoring response due to cancellation: '{response}'\n")
            return
        
        # Always forward response to configuration_reader if set
        if self.configuration_reader and hasattr(self.configuration_reader, 'capture_device_response'):
            try:
                self.configuration_reader.capture_device_response(response)
            except Exception as e:
                self.app.log_frame.log_message(f"WARNING: Failed to forward response to configuration reader: {str(e)}\n")
        elif hasattr(self.app, 'configuration_reader_service'):
            # Fallback: support legacy app attribute if present
            try:
                self.app.configuration_reader_service.capture_device_response(response)
            except Exception as e:
                self.app.log_frame.log_message(f"WARNING: Failed to forward response to app.configuration_reader_service: {str(e)}\n")
        else:
            self.app.log_frame.log_message("WARNING: No configuration reader available to capture device response\n")
            
        # Store the current command type for processing
        command_type = self.current_command_type
        
        # Parse the response using the device command mapper if available
        if hasattr(self.app, 'device_command_mapper') and command_type:
            try:
                parsed_data = self.app.device_command_mapper.parse_device_response(response, command_type)

                # Store results for bulk operations
                if self.queue_processing and parsed_data:
                    # Merge with existing results
                    self.queue_results.update(parsed_data)
                    self.app.log_frame.log_message(f"INFO: Parsed data: {parsed_data}\n")

                # Handle specific UI updates for IMEI, ICCID, and version
                if 'imei' in parsed_data:
                    self.device_info['imei'] = parsed_data['imei']
                    self.app.after(0, self.update_device_info)
                if 'teriid' in parsed_data:
                    self.device_info['teriid'] = parsed_data['teriid']
                    self.app.after(0, self.update_device_info)
                if 'iccid' in parsed_data:
                    self.device_info['iccid'] = parsed_data['iccid']
                    self.app.after(0, self.update_device_info)
                if 'version' in parsed_data:
                    self.device_info['version'] = parsed_data['version']
                    self.app.after(0, self.update_device_info)

                # Update UI with parsed data
                if parsed_data:
                    self.app.after(0, self.app.update_ui_with_parsed_data, parsed_data)

                # Update UI with parsed data
                if parsed_data:
                    self.app.after(0, self.app.update_ui_with_parsed_data, parsed_data)

            except Exception as e:
                self.app.log_frame.log_message(f"ERROR: Failed to parse response: {str(e)}\n")
        
        # Reset command type after processing
        self.current_command_type = None
        self.waiting_for_response = False
    
    def update_device_info(self):
        """Update the UI with device information."""
        if not hasattr(self.app, 'connection_frame'):
            return

        imei = self.device_info.get('imei')
        teriid = self.device_info.get('teriid')
        iccid = self.device_info.get('iccid')
        version = self.device_info.get('version')

        if imei:
            self.app.connection_frame.imei_value_var.set(imei)

        if teriid:
            self.app.connection_frame.teriid_value_var.set(teriid)
        else:
            self.app.connection_frame.teriid_value_var.set("N/A")

        if iccid:
            self.app.connection_frame.iccid_value_var.set(iccid)

        if version:
            self.app.connection_frame.version_value_var.set(version)
    
    def retrieve_device_info(self):
        """
        Send commands to retrieve device information (IMEI, ICCID).
        Should be called after successful connection.
        """
        if not self.is_connected:
            return
            
        # Get device command mapper from the app
        if hasattr(self.app, 'device_command_mapper'):
            # Send command to get IMEI
            imei_cmd = self.app.device_command_mapper.get_command('get_imei', None)
            self.send_command(imei_cmd, 'get_imei')
            
            # Schedule the TERIID command to run after a delay
            self.app.after(500, self._send_teriid_command)
        else:
            self.app.log_frame.log_message("ERROR: Device command mapper not available\n")
            
    def _send_teriid_command(self):
        """Helper method to send TERIID command after a delay."""
        if self.is_connected and hasattr(self.app, 'device_command_mapper'):
            teriid_cmd = self.app.device_command_mapper.get_command('get_teriid', None)
            self._waiting_for_teriid_response = True
            self._teriid_diagnostic_logged = False
            try:
                self.app.log_frame.log_message("DEBUG: Sending TERIID request to device\n")
            except Exception:
                print("DEBUG: Sending TERIID request to device")
            self.send_command(teriid_cmd, 'get_teriid')
            
            # Schedule the ICCID command to run after TERIID
            self.app.after(500, self._send_iccid_command)
            
    def _send_iccid_command(self):
        """Helper method to send ICCID command after a delay."""
        if self.is_connected and hasattr(self.app, 'device_command_mapper'):
            iccid_cmd = self.app.device_command_mapper.get_command('get_iccid', None)
            self.send_command(iccid_cmd, 'get_iccid')
            
            # Schedule the version command to run after ICCID
            self.app.after(500, self._send_version_command)
            
    def _send_version_command(self):
        """Helper method to send version command after ICCID."""
        if self.is_connected and hasattr(self.app, 'device_command_mapper'):
            version_cmd = self.app.device_command_mapper.get_command('get_version', None)
            self.app.log_frame.log_message("DEBUG: Sending VERSION command...")
            self.send_command(version_cmd, 'get_version')
            
            # Introduce a final delay after sending all commands
            time.sleep(1)
            
    def queue_command(self, command: str, command_type: str = None) -> None:
        """
        Add a command to the queue for sequential processing.
        
        Args:
            command: The command string to send
            command_type: Optional type of command for response processing
        """
        self.command_queue.put((command, command_type))
        
    def queue_commands(self, commands: List[str], command_types: List[str] = None, 
                      callback: Callable = None, delay: float = 0.5,
                      progress_dialog_id: str = None) -> None:
        """
        Queue multiple commands for sequential processing.
        
        Args:
            commands: List of command strings to send
            command_types: Optional list of command types for response processing
            callback: Optional callback function to call when all commands are processed
            delay: Delay between commands in seconds
            progress_dialog_id: Optional ID of a progress dialog to update
        """
        # Clear any existing queue
        while not self.command_queue.empty():
            self.command_queue.get()
            
        self.queue_results = {}
        self.queue_callback = callback
        self.queue_delay = delay
        
        # Store progress dialog ID if provided
        self.progress_dialog_id = progress_dialog_id
        self.total_commands = len(commands)
        self.processed_commands = 0
        
        # Add all commands to the queue
        for i, cmd in enumerate(commands):
            cmd_type = command_types[i] if command_types and i < len(command_types) else None
            self.queue_command(cmd, cmd_type)
            
        # Start processing the queue if not already processing
        if not self.queue_processing:
            self.start_queue_processing()
            
    def start_queue_processing(self) -> None:
        """Start processing the command queue in a separate thread."""
        if self.queue_processing:
            return
            
        self.queue_processing = True
        self.queue_thread = threading.Thread(target=self._process_command_queue, daemon=True)
        self.queue_thread.start()
        
        # Log the start of bulk operation to console
        print("INFO: Starting bulk command operation")
        
    def _process_command_queue(self) -> None:
        """Process commands from the queue sequentially with delays."""
        try:
            self.processed_commands = 0
            
            while self.queue_processing and self.is_connected:
                if self.command_queue.empty():
                    # Queue is empty, we're done
                    break
                    
                # Get the next command from the queue
                command, command_type = self.command_queue.get()
                
                # Send the command
                sent_ok = self.send_command(command, command_type)

                # If send succeeded, wait for the device response or timeout
                if sent_ok:
                    start_wait = time.time()
                    waited = 0.0
                    # Only wait while waiting_for_response is True and we haven't exceeded the timeout
                    while self.waiting_for_response and (time.time() - start_wait) < self.queue_response_timeout:
                        time.sleep(0.05)
                        waited = time.time() - start_wait
                    # If still waiting after timeout, log timeout notice
                    if self.waiting_for_response:
                        self.app.after(0, self.app.log_frame.log_message, f"INFO: Response timeout after {self.queue_response_timeout}s for command: {command}\n")
                        # reset waiting flag to avoid blocking future commands
                        self.waiting_for_response = False
                else:
                    # If send failed, log and continue to next command
                    self.app.after(0, self.app.log_frame.log_message, f"WARNING: Failed to send queued command: {command}\n")
                
                # Increment processed commands counter
                self.processed_commands += 1
                
                # Update progress dialog if available
                if hasattr(self.app, 'operation_confirmation_service') and hasattr(self, 'progress_dialog_id') and self.progress_dialog_id:
                    # Calculate percentage for status text
                    percentage = int((self.processed_commands / self.total_commands) * 100)
                    status_text = f"Processing command {self.processed_commands} of {self.total_commands} ({percentage}%)"
                    
                    # Update the progress dialog
                    self.app.after(0, self.app.operation_confirmation_service.update_progress,
                                  self.progress_dialog_id, self.processed_commands, status_text)
                
                # Show progress in log
                if hasattr(self.app, 'operation_confirmation_service'):
                    self.app.after(0, self.app.operation_confirmation_service.show_operation_progress_in_log,
                                  "Bulk Command Operation", self.processed_commands, self.total_commands)
                
                # Wait for the specified delay
                time.sleep(self.queue_delay)
                
                # Mark the task as done
                self.command_queue.task_done()
                
            # Log completion of bulk operation to console
            print("INFO: Bulk command operation completed")
            
            # Call the callback if provided
            if self.queue_callback:
                self.app.after(0, self.queue_callback, self.queue_results)
                
        except Exception as e:
            self.app.after(0, self.app.log_frame.log_message, f"ERROR: Bulk command operation failed: {str(e)}\n")
            
            # Close progress dialog if it exists with error
            if hasattr(self.app, 'operation_confirmation_service') and hasattr(self, 'progress_dialog_id') and self.progress_dialog_id:
                self.app.after(0, self.app.operation_confirmation_service.complete_progress,
                              self.progress_dialog_id, False, f"Error: {str(e)}")
        finally:
            self.queue_processing = False
            
    def stop_queue_processing(self) -> None:
        """Stop processing the command queue."""
        self.queue_processing = False
        if self.queue_thread and self.queue_thread.is_alive():
            self.queue_thread.join(timeout=1)
        
        # Clear the queue
        while not self.command_queue.empty():
            self.command_queue.get()
            self.command_queue.task_done()
            
        print("INFO: Bulk command operation stopped")
        
    def send_all_parameters(self) -> None:
        """
        Send all current UI parameters to the device in the correct sequence.
        Implements the "Enviar todos os comandos" functionality.
        """
        if not self.is_connected:
            self.app.log_frame.log_message("ERROR: Not connected to device\n")
            return
            
        if not hasattr(self.app, 'device_command_mapper'):
            self.app.log_frame.log_message("ERROR: Device command mapper not available\n")
            return
            
        # Check if we have the operation confirmation service
        if hasattr(self.app, 'operation_confirmation_service'):
            # Ask for confirmation before sending all parameters
            if not self.app.operation_confirmation_service.confirm_operation(
                self.app.operation_confirmation_service.OPERATION_BULK_SEND
            ):
                # Move INFO message to console instead of UI log
                print("INFO: Bulk send operation canceled by user")
                return
        
        # Collect all parameters from UI
        parameters = self._collect_parameters_from_ui()
        
        # Debug: Log the collected parameters structure
        self.app.log_frame.log_message(f"DEBUG: Collected parameters structure: {type(parameters)}\n")
        self.app.log_frame.log_message(f"DEBUG: Parameters keys: {list(parameters.keys()) if isinstance(parameters, dict) else 'Not a dict'}\n")
        
        # Flatten the hierarchical parameter structure for the device command mapper
        flattened_parameters = self._flatten_parameters_for_device_mapper(parameters)
        self.app.log_frame.log_message(f"DEBUG: Flattened parameters: {flattened_parameters}\n")
        print(f"DEBUG: Flattened parameters: {flattened_parameters}")  # Also print to console
        
        # Get bulk commands in the correct sequence
        progress_dialog_id = None
        try:
            self.app.log_frame.log_message("DEBUG: Calling device_command_mapper.get_bulk_commands()\n")
            commands = self.app.device_command_mapper.get_bulk_commands(flattened_parameters)
            self.app.log_frame.log_message(f"DEBUG: get_bulk_commands returned {len(commands) if commands else 0} commands\n")
            
            if not commands:
                warning_msg = "WARNING: No parameters to send"
                self.app.log_frame.log_message(f"{warning_msg}\n")
                print(warning_msg)  # Also print to console
                self.app.log_frame.log_message(f"DEBUG: Parameters passed to get_bulk_commands: {flattened_parameters}\n")
                print(f"DEBUG: Parameters passed to get_bulk_commands: {flattened_parameters}")  # Also print to console
                return
            
            # Create a progress dialog if we have the operation confirmation service
            progress_dialog_id = None
            if hasattr(self.app, 'operation_confirmation_service'):
                # Use i18n for progress dialog text
                sending_title = self.app.i18n.get("sending_parameters", "Sending Parameters")
                bulk_send_title = self.app.i18n.get("bulk_parameter_send", "Bulk Parameter Send")
                
                progress_dialog_id = self.app.operation_confirmation_service.create_progress_dialog(
                    sending_title,
                    bulk_send_title,
                    self.app.operation_confirmation_service.PROGRESS_TYPE_DETERMINATE,
                    len(commands),
                    True
                )
                
                # Set cancel callback
                self.app.operation_confirmation_service.set_cancel_callback(
                    progress_dialog_id,
                    self.stop_queue_processing
                )
            
            # Define a callback that updates progress and shows completion
            def on_complete(results):
                if progress_dialog_id:
                    # Use i18n for completion message
                    success_msg = self.app.i18n.get("all_parameters_sent_successfully", "All parameters sent successfully")
                    self.app.operation_confirmation_service.complete_progress(
                        progress_dialog_id,
                        True,
                        success_msg
                    )
                else:
                    # Move INFO message to console instead of UI log
                    print("INFO: All parameters sent successfully")
            
            # Queue the commands for sequential processing
            self.queue_commands(
                commands, 
                callback=on_complete,
                delay=0.8,  # Slightly longer delay for parameter commands
                progress_dialog_id=progress_dialog_id
            )
            
            # Move INFO message to console instead of UI log
            print(f"INFO: Queued {len(commands)} commands for sending")
            
        except Exception as e:
            self.app.log_frame.log_message(f"ERROR: Failed to prepare commands: {str(e)}\n")
            
            # Close progress dialog if it exists
            if hasattr(self.app, 'operation_confirmation_service') and progress_dialog_id:
                # Use i18n for error message
                error_template = self.app.i18n.get("error_preparing_commands", "Error preparing commands: {error}")
                error_msg = error_template.format(error=str(e))
                self.app.operation_confirmation_service.complete_progress(
                    progress_dialog_id,
                    False,
                    error_msg
                )
            
    def check_device_configuration(self) -> None:
        """
        Retrieve and populate all device settings.
        Implements the "Checar configuração" functionality.
        """
        if not self.is_connected:
            self.app.log_frame.log_message("ERROR: Not connected to device\n")
            return
        
        # Initialize configuration reader if not already done
        if self.configuration_reader is None:
            self.initialize_configuration_reader()
        
        if self.configuration_reader is None:
            self.app.log_frame.log_message("ERROR: Configuration reader service not available\n")
            return
        
        # Define completion callback
        def on_completion(result, error_message):
            # Check if operation was canceled
            if (hasattr(self, 'configuration_reader') and 
                self.configuration_reader is not None and 
                hasattr(self.configuration_reader, 'cancel_requested') and 
                self.configuration_reader.cancel_requested):
                self.app.log_frame.log_message("INFO: Configuration reading was canceled by user\n")
                return
            
            if result.success:
                success_msg = f"Configuration reading completed successfully."
                self.app.log_frame.log_message(f"INFO: {success_msg}\n")
                
                # Note: UI is already updated by the ConfigurationReaderService.read_all_configurations()
                # No need to call _update_ui_from_device_configuration again as it would duplicate the process
                
                if hasattr(self.app, 'operation_confirmation_service'):
                    self.app.operation_confirmation_service.show_success_notification(success_msg)
            else:
                error_msg = error_message or "Configuration reading failed"
                self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
        
        # Start configuration reading with progress indication
        try:
            self.configuration_reader.read_all_configurations(
                completion_callback=on_completion,
                show_progress_dialog=True
            )
            
        except Exception as e:
            self.app.log_frame.log_message(f"ERROR: Failed to start configuration reading: {str(e)}\n")
            
    def _collect_parameters_from_ui(self) -> Dict[str, Any]:
        """
        Collect all parameter values from the UI.
        
        Returns:
            Dictionary of parameter names and values
        """
        parameters = {}
        
        # Check if parameters frame exists
        if not hasattr(self.app, 'parameters_frame') and not hasattr(self.app, 'params_frame'):
            self.app.log_frame.log_message("DEBUG: No parameters frame found\n")
            return parameters
        
        # Get the parameters frame (try both possible names)
        params_frame = getattr(self.app, 'parameters_frame', None) or getattr(self.app, 'params_frame', None)
        
        if params_frame is None:
            self.app.log_frame.log_message("DEBUG: Parameters frame is None\n")
            return parameters
        
        # Use the modern specification-based parameter collection method
        if hasattr(params_frame, 'get_all_parameter_values'):
            try:
                parameters = params_frame.get_all_parameter_values()
                self.app.log_frame.log_message(f"DEBUG: Collected {len(parameters)} parameters using specification method\n")
                
                # Log the collected parameters for debugging
                for param_name, value in parameters.items():
                    self.app.log_frame.log_message(f"DEBUG: Parameter {param_name}: {value}\n")
                    
                return parameters
            except Exception as e:
                self.app.log_frame.log_message(f"ERROR: Failed to collect parameters using specification method: {str(e)}\n")
        
        # Fallback to legacy parameter collection methods
        self.app.log_frame.log_message("DEBUG: Using fallback parameter collection methods\n")
        
        # Try legacy parameter widgets
        if hasattr(params_frame, 'parameter_widgets'):
            for param_name, widget in params_frame.parameter_widgets.items():
                try:
                    if hasattr(widget, 'get_value'):
                        parameters[param_name] = widget.get_value()
                    elif hasattr(widget, 'get'):
                        parameters[param_name] = widget.get()
                except Exception as e:
                    self.app.log_frame.log_message(f"WARNING: Failed to get value for parameter {param_name}: {str(e)}\n")
        
        # Try legacy APN entries
        if hasattr(params_frame, 'apn_server_entry'):
            try:
                parameters['apn_server'] = params_frame.apn_server_entry.get()
            except:
                pass
        if hasattr(params_frame, 'apn_user_entry'):
            try:
                parameters['apn_user'] = params_frame.apn_user_entry.get()
            except:
                pass
        if hasattr(params_frame, 'apn_password_entry'):
            try:
                parameters['apn_password'] = params_frame.apn_password_entry.get()
            except:
                pass
        
        self.app.log_frame.log_message(f"DEBUG: Collected {len(parameters)} parameters using fallback methods\n")
        return parameters
    
    def _flatten_parameters_for_device_mapper(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten the hierarchical parameter structure to the format expected by device command mapper.
        
        Args:
            parameters: Hierarchical parameter structure from UI
            
        Returns:
            Flattened parameter dictionary
        """
        flattened = {}
        for section_name, section_data in parameters.items():
            if isinstance(section_data, dict):
                for param_name, param_data in section_data.items():
                    if isinstance(param_data, dict):
                        for field_name, field_value in param_data.items():
                            flattened[f"{param_name}.{field_name}"] = field_value
                    else:
                        flattened[param_name] = param_data
        return flattened
        
    def _process_config_check_results(self, results: Dict[str, Any]) -> None:
        """
        Process the results of a configuration check and update the UI.
        
        Args:
            results: Dictionary of results from the configuration check
        """
        self.app.log_frame.log_message("INFO: Processing configuration check results\n")
        
        # Check if parameters frame exists
        if not hasattr(self.app, 'parameters_frame'):
            return
            
        # Update APN parameters
        if 'apn_server' in results and hasattr(self.app.params_frame, 'apn_server_entry'):
            self.app.params_frame.apn_server_entry.delete(0, 'end')
            self.app.params_frame.apn_server_entry.insert(0, results['apn_server'])
            self.app.log_frame.log_message(f"INFO: Updated APN server to {results['apn_server']}\n")
            
        if 'apn_user' in results and hasattr(self.app.params_frame, 'apn_user_entry'):
            self.app.params_frame.apn_user_entry.delete(0, 'end')
            self.app.params_frame.apn_user_entry.insert(0, results['apn_user'])
            self.app.log_frame.log_message(f"INFO: Updated APN user to {results['apn_user']}\n")
            
        if 'apn_password' in results and hasattr(self.app.params_frame, 'apn_password_entry'):
            self.app.params_frame.apn_password_entry.delete(0, 'end')
            self.app.params_frame.apn_password_entry.insert(0, results['apn_password'])
            self.app.log_frame.log_message(f"INFO: Updated APN password\n")
        
        # Update transmission mode
        if 'transmission_mode' in results and hasattr(self.app.parameters_frame, 'trans_mode_var'):
            self.app.parameters_frame.trans_mode_var.set(results['transmission_mode'])
            self.app.log_frame.log_message(f"INFO: Updated transmission mode to {results['transmission_mode']}\n")
            
        # Update all other parameters using the parameter widgets
        if hasattr(self.app.parameters_frame, 'parameter_widgets'):
            # Create a reverse mapping from values to keys for dropdowns/radios
            reverse_mappings = {}
            if hasattr(self.app, 'device_command_mapper'):
                for param, mapping in self.app.device_command_mapper.value_mappings.items():
                    reverse_mappings[param] = {v: k for k, v in mapping.items()}

            for param_name, value in results.items():
                if param_name in self.app.parameters_frame.parameter_widgets:
                    try:
                        # If a reverse mapping exists, use it to get the display value
                        if param_name in reverse_mappings and value in reverse_mappings[param_name]:
                            display_value = reverse_mappings[param_name][value]
                        else:
                            display_value = value

                        self.app.parameters_frame.parameter_widgets[param_name].set_value(display_value)
                        self.app.log_frame.log_message(f"INFO: Updated parameter {param_name} to {display_value}\n")
                    except Exception as e:
                        self.app.log_frame.log_message(f"ERROR: Failed to update parameter {param_name}: {str(e)}\n")
        
        self.app.log_frame.log_message("INFO: Configuration check complete - UI updated with device values\n")
                    
        self.app.log_frame.log_message("INFO: Device configuration loaded to UI\n")
        
    def monitor_connection(self) -> None:
        """
        Monitor the connection status and detect disconnections.
        This runs in a separate thread and periodically checks if the connection is still active.
        """
        check_interval = 5  # Check every 5 seconds initially
        consecutive_failures = 0
        max_consecutive_failures = 3  # Number of consecutive failures before considering connection lost
        
        while not self.stop_monitor and self.is_connected:
            try:
                # Check if there has been activity recently
                current_time = datetime.datetime.now()
                time_since_activity = (current_time - self.last_activity_time).total_seconds()
                
                # If no activity for a while, check if the connection is still alive
                if time_since_activity > self.connection_timeout:
                    # Try to send a simple command to check connection
                    if hasattr(self.app, 'device_command_mapper'):
                        try:
                            # Log that we're checking connection status
                            self.app.after(0, self.app.log_frame.log_message, 
                                          "DEBUG: Checking connection status...\n")
                            
                            # Send a status request to check if device is still connected
                            self.serial_port.write(b"ATSMS:STATUS#\r\n")
                            
                            # Wait a short time for response
                            time.sleep(0.5)
                            
                            # If no response and no data in buffer, connection might be lost
                            if self.serial_port.in_waiting == 0:
                                consecutive_failures += 1
                                
                                # Log the failure attempt
                                self.app.after(0, self.app.log_frame.log_message, 
                                              f"DEBUG: No response from device (attempt {consecutive_failures}/{max_consecutive_failures})\n")
                                
                                # Try one more time with a longer timeout
                                self.serial_port.write(b"ATSMS:STATUS#\r\n")
                                time.sleep(1)
                                
                                if self.serial_port.in_waiting == 0:
                                    if consecutive_failures >= max_consecutive_failures:
                                        # Connection appears to be lost after multiple failures
                                        self.app.after(0, self.app.log_frame.log_message, 
                                                      "WARNING: Device not responding to status checks\n")
                                        self.app.after(0, self._handle_connection_lost)
                                        break
                                    
                                    # Increase check interval after failures
                                    check_interval = min(check_interval + 2, 15)  # Max 15 seconds
                                else:
                                    # Got a response on second try, reset failures but note it was slow
                                    consecutive_failures = 0
                                    self.app.after(0, self.app.log_frame.log_message, 
                                                  "INFO: Device responded slowly to status check\n")
                                    
                                    # Update connection quality if error handler exists
                                    if hasattr(self.app, 'error_handler'):
                                        self.app.after(0, self.app.error_handler._update_connection_quality, -5)
                            else:
                                # Got a response, connection is good
                                consecutive_failures = 0
                                
                                # Gradually decrease check interval back to normal
                                check_interval = max(check_interval - 1, 5)  # Min 5 seconds
                                
                                # Update connection quality if error handler exists
                                if hasattr(self.app, 'error_handler'):
                                    self.app.after(0, self.app.error_handler._update_connection_quality, 1)
                                    
                                # Flash the connection indicator to show activity
                                if hasattr(self.app, 'connection_frame'):
                                    self.app.after(0, self.app.connection_frame.flash_activity_indicator)
                        except serial.SerialException as se:
                            # Serial exception indicates connection is definitely lost
                            self.app.after(0, self.app.log_frame.log_message, 
                                          f"ERROR: Serial exception during connection check: {str(se)}\n")
                            self.app.after(0, self._handle_connection_lost)
                            break
                    
                    # Update last activity time even if we just checked
                    self.last_activity_time = current_time
            
            except Exception as e:
                # Log any errors in the monitoring thread
                self.app.after(0, self.app.log_frame.log_message, 
                              f"ERROR: Exception in connection monitoring: {str(e)}\n")
                
            # Sleep for the current check interval
            time.sleep(check_interval)
            
            # Sleep before next check
            time.sleep(5)  # Check every 5 seconds
    
    def _handle_connection_lost(self) -> None:
        """Handle a lost connection with appropriate error messages and reconnection attempts."""
        if not self.is_connected:
            return  # Already disconnected
            
        # Get the current port before disconnecting
        current_port = self.serial_port.port if self.serial_port else None
        
        # Stop threads
        self.stop_thread = True
        self.stop_monitor = True
        
        # Log the disconnection with timestamp
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        if hasattr(self.app, 'log_frame') and self.app.log_frame:
            self.app.log_frame.log_message(f"ERROR: Connection lost unexpectedly at {timestamp}\n")
        else:
            print(f"ERROR: Connection lost unexpectedly at {timestamp}\n")
        
        # Update connection status
        self.is_connected = False
        self.waiting_for_response = False
        
        # Close the port
        if self.serial_port:
            try:
                if self.serial_port.is_open:
                    self.serial_port.close()
            except Exception as e:
                self.app.log_frame.log_message(f"ERROR: Error closing port: {str(e)}\n")
        
        # Update UI to show disconnected state
        if hasattr(self.app, 'connection_frame'):
            self.app.connection_frame.update_status(False)
        
        # Use enhanced error handling service if available
        if hasattr(self.app, 'error_handler') and current_port:
            # Determine the likely cause of disconnection based on recent activity
            error_type = self.app.error_handler.CONN_ERROR_DEVICE_DISCONNECTED
            
            # If we have last_activity_time, check how long since last activity
            if hasattr(self, 'last_activity_time'):
                time_since_activity = (datetime.datetime.now() - self.last_activity_time).total_seconds()
                
                # If it's been a long time since activity, it might be a timeout
                if time_since_activity > self.connection_timeout:
                    error_type = self.app.error_handler.CONN_ERROR_TIMEOUT
                    self.app.log_frame.log_message(
                        f"INFO: No activity detected for {int(time_since_activity)} seconds before disconnection\n"
                    )
            
            # Create context with detailed information
            context = {
                'port': current_port,
                'last_activity': self.last_activity_time.strftime("%H:%M:%S") if hasattr(self, 'last_activity_time') else "unknown",
                'reconnect_enabled': self.app.connection_frame.auto_reconnect_var.get() if hasattr(self.app.connection_frame, 'auto_reconnect_var') else True
            }
            
            # Handle the error with appropriate type and severity
            self.app.error_handler.handle_error(
                error_type,
                self.app.error_handler.SEVERITY_ERROR,
                context
            )
            
            # Check if auto-reconnect is enabled in the UI
            auto_reconnect_enabled = (hasattr(self.app.connection_frame, 'auto_reconnect_var') and 
                                     self.app.connection_frame.auto_reconnect_var.get())
            
            # Attempt to reconnect if enabled
            if auto_reconnect_enabled:
                self.app.log_frame.log_message("INFO: Automatic reconnection enabled\n")
                self.app.error_handler._attempt_reconnection(current_port)
            else:
                self.app.log_frame.log_message("INFO: Automatic reconnection disabled. Please reconnect manually.\n")
        else:
            # Basic reconnection message if no error handler
            self.app.log_frame.log_message("INFO: Connection lost. Please check your device and reconnect manually.\n")
    
    def update_last_activity(self) -> None:
        """Update the last activity timestamp to indicate the connection is active."""
        self.last_activity_time = datetime.datetime.now()
        
        # Flash the connection indicator to show activity
        if hasattr(self.app, 'connection_frame'):
            self.app.after(0, self.app.connection_frame.flash_activity_indicator)
            
        # Slightly improve connection quality with successful activity
        if hasattr(self.app, 'error_handler'):
            # Small improvement for regular activity
            self.app.after(0, self.app.error_handler._update_connection_quality, 1)
    
    def _update_ui_from_device_configuration(self) -> None:
        """
        Update UI with processed parameters from device configuration.
        
        This method uses the ConfigurationReaderService directly (same approach as 
        check_device_configuration) to read all parameters from the device and 
        update the UI with the correct values.
        
        Requirements: 3.1, 3.2, 3.3, 3.5 (Odometer parameter updates)
        """
        try:
            # Check if configuration reader is available
            if self.configuration_reader is None:
                self.initialize_configuration_reader()
            
            if self.configuration_reader is None:
                self.app.log_frame.log_message("ERROR: Configuration reader service not available\n")
                return
            
            # Define completion callback to update UI with the read parameters
            def on_completion(result, error_message):
                if result.success:
                    success_msg = f"Configuration reading completed successfully."
                    self.app.log_frame.log_message(f"INFO: {success_msg}\n")
                    
                    # Check if operation was canceled before updating UI
                    if hasattr(self.configuration_reader, 'cancel_requested') and self.configuration_reader.cancel_requested:
                        self.app.log_frame.log_message("INFO: Configuration reading was canceled, skipping UI update\n")
                        return
                    
                    # Update UI with the read parameters
                    self._update_ui_with_parameters(result.parameters_read)
                    
                    if hasattr(self.app, 'operation_confirmation_service'):
                        self.app.operation_confirmation_service.show_success_notification(success_msg)
                else:
                    error_msg = error_message or "Configuration reading failed"
                    self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
            
            # Start configuration reading with progress indication (same as check_device_configuration)
            try:
                self.configuration_reader.read_all_configurations(
                    completion_callback=on_completion,
                    show_progress_dialog=True
                )
                
            except Exception as e:
                self.app.log_frame.log_message(f"ERROR: Failed to start configuration reading: {str(e)}\n")
                
        except Exception as e:
            self.app.log_frame.log_message(f"ERROR: Failed to start UI update from device configuration: {str(e)}\n")
    
    def _apply_ui_values_to_parameters_frame(self, ui_values: Dict[str, Any]) -> None:
        """
        Apply processed parameter values to the parameters frame UI.
        
        Args:
            ui_values: Dictionary of parameter names to processed values
        """
        try:
            # Update UI using the parameters frame update method
            if hasattr(self.app, 'params_frame') and hasattr(self.app.params_frame, 'update_fields_from_dict'):
                self.app.params_frame.update_fields_from_dict(ui_values)
                self.app.log_frame.log_message("INFO: Parameters frame updated with processed device values\n")
            elif hasattr(self.app, 'parameters_frame') and hasattr(self.app.parameters_frame, 'update_fields_from_dict'):
                self.app.parameters_frame.update_fields_from_dict(ui_values)
                self.app.log_frame.log_message("INFO: Parameters frame updated with processed device values\n")
            else:
                self.app.log_frame.log_message("WARNING: Parameters frame update method not available\n")
                
        except Exception as e:
            self.app.log_frame.log_message(f"ERROR: Failed to apply UI values to parameters frame: {str(e)}\n")
            
    def _update_ui_with_parameters(self, parameters_read):
        """
        Update UI with parameters read from the device based on specification.
        
        Args:
            parameters_read: List of parameter read results from ConfigurationReaderService
        """
        try:
            self.app.log_frame.log_message("DEBUG: Updating UI with parameters read from device\n")
            self.app.log_frame.log_message(f"DEBUG: Number of parameters to process: {len(parameters_read)}\n")
            
            # Debug: List all parameters
            for result in parameters_read:
                self.app.log_frame.log_message(f"DEBUG: Parameter {result.parameter_name}: success={result.success}, value={result.value}\n")
            
            # Check if we have access to the parameters frame
            if not hasattr(self.app, 'parameters_frame') or self.app.parameters_frame is None:
                self.app.log_frame.log_message("DEBUG: Parameters frame not available yet, cannot update UI\n")
                return
            else:
                self.app.log_frame.log_message("DEBUG: Parameters frame found, proceeding with UI updates\n")
            
            # Use the configuration reader's UI update method directly
            self.configuration_reader._update_ui_with_parameters(parameters_read)
            
            # Log successful UI updates
            updated_count = len([r for r in parameters_read if r.success])
            self.app.log_frame.log_message(f"INFO: Successfully updated UI with {updated_count} parameters\n")
            
        except Exception as e:
            self.app.log_frame.log_message(f"ERROR: Failed to update UI with parameters: {str(e)}\n")