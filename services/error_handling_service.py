"""
Error Handling Service - Provides centralized error handling and user feedback.

This module provides a centralized service for handling errors, displaying
appropriate messages, and managing reconnection attempts for the LT32Pro
Device Configurator application.
"""

import threading
import time
from typing import Callable, Optional, Dict, Any, Tuple
import datetime
import tkinter as tk
from tkinter import messagebox

class ErrorHandlingService:
    """Centralized error handling and user feedback service."""
    
    # Error categories
    CONNECTION_ERROR = "connection"
    VALIDATION_ERROR = "validation"
    COMMAND_ERROR = "command"
    DEVICE_ERROR = "device"
    SYSTEM_ERROR = "system"
    
    # Error severity levels
    SEVERITY_INFO = "info"
    SEVERITY_WARNING = "warning"
    SEVERITY_ERROR = "error"
    SEVERITY_CRITICAL = "critical"
    
    # Connection error types
    CONN_ERROR_PORT_NOT_FOUND = "port_not_found"
    CONN_ERROR_PORT_IN_USE = "port_in_use"
    CONN_ERROR_ACCESS_DENIED = "access_denied"
    CONN_ERROR_TIMEOUT = "timeout"
    CONN_ERROR_DEVICE_DISCONNECTED = "device_disconnected"
    CONN_ERROR_NO_RESPONSE = "no_response"
    CONN_ERROR_SIGNAL_LOST = "signal_lost"
    CONN_ERROR_DEVICE_BUSY = "device_busy"
    CONN_ERROR_INVALID_RESPONSE = "invalid_response"
    CONN_ERROR_UNKNOWN = "unknown_connection_error"
    CONN_ERROR_DRIVER_ISSUE = "driver_issue"
    CONN_ERROR_HARDWARE_FAILURE = "hardware_failure"
    CONN_ERROR_CABLE_ISSUE = "cable_issue"
    CONN_ERROR_DEVICE_LOCKED = "device_locked"
    
    # Command error types
    CMD_ERROR_INVALID_FORMAT = "invalid_format"
    CMD_ERROR_TIMEOUT = "command_timeout"
    CMD_ERROR_REJECTED = "command_rejected"
    CMD_ERROR_UNKNOWN = "unknown_command_error"
    
    def __init__(self, app_instance):
        """
        Initialize the error handling service.
        
        Args:
            app_instance: Reference to the main application instance
        """
        self.app = app_instance
        self.reconnect_thread = None
        self.stop_reconnect = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
        self.reconnect_delay = 2  # seconds
        self.auto_reconnect_enabled = True  # Enable auto-reconnect by default
        self.last_error_time = {}  # Track last occurrence of each error type
        self.error_count = {}  # Count occurrences of each error type
        self.connection_status_history = []  # Track connection status changes
        self.connection_quality = 100  # Connection quality percentage (100 = perfect)
        
        # Error message templates with placeholders
        self.error_messages = {
            # Connection errors
            self.CONN_ERROR_PORT_NOT_FOUND: "COM port {port} not found. Please check your device connection and ensure the USB cable is properly connected.",
            self.CONN_ERROR_PORT_IN_USE: "COM port {port} is already in use by another application. Please close any other programs that might be using this port.",
            self.CONN_ERROR_ACCESS_DENIED: "Access denied to COM port {port}. Please check permissions or run the application as administrator.",
            self.CONN_ERROR_TIMEOUT: "Connection timeout on port {port}. Device not responding within the expected time frame.",
            self.CONN_ERROR_DEVICE_DISCONNECTED: "Device disconnected unexpectedly. Please check the physical connection and device power status.",
            self.CONN_ERROR_NO_RESPONSE: "Device connected but not responding to commands on port {port}. The device may be in an error state.",
            self.CONN_ERROR_SIGNAL_LOST: "Signal lost on port {port}. The connection was interrupted during communication.",
            self.CONN_ERROR_DEVICE_BUSY: "Device on port {port} is busy processing another command. Please try again in a few moments.",
            self.CONN_ERROR_INVALID_RESPONSE: "Invalid response received from device on port {port}. The device may be incompatible or in an error state.",
            self.CONN_ERROR_DRIVER_ISSUE: "Possible driver issue detected on port {port}. Please verify that the correct USB drivers are installed.",
            self.CONN_ERROR_HARDWARE_FAILURE: "Hardware failure detected on port {port}. The device may need service or replacement.",
            self.CONN_ERROR_CABLE_ISSUE: "Possible cable issue detected on port {port}. Try using a different USB cable.",
            self.CONN_ERROR_DEVICE_LOCKED: "Device on port {port} appears to be locked or in a protected state. Try power cycling the device.",
            self.CONN_ERROR_UNKNOWN: "Unknown connection error: {error_message}",
            
            # Command errors
            self.CMD_ERROR_INVALID_FORMAT: "Invalid command format: {command}",
            self.CMD_ERROR_TIMEOUT: "Command timeout: {command}",
            self.CMD_ERROR_REJECTED: "Command rejected by device: {command}",
            self.CMD_ERROR_UNKNOWN: "Unknown command error: {error_message}"
        }
        
        # Error resolution suggestions
        self.error_resolutions = {
            self.CONN_ERROR_PORT_NOT_FOUND: [
                "Verify the device is properly connected to your computer",
                "Try a different USB port",
                "Check if the USB cable is damaged and replace if necessary",
                "Restart the device and try again"
            ],
            self.CONN_ERROR_PORT_IN_USE: [
                "Close any other applications that might be using the COM port",
                "Check Device Manager to see which application is using the port",
                "Restart your computer to release all COM ports"
            ],
            self.CONN_ERROR_ACCESS_DENIED: [
                "Run the application as administrator",
                "Check Windows security settings for blocked access",
                "Verify you have proper permissions to access COM ports"
            ],
            self.CONN_ERROR_TIMEOUT: [
                "Check if the device is powered on",
                "Verify the device is in configuration mode",
                "Try increasing the connection timeout in settings",
                "Reset the device and try again"
            ],
            self.CONN_ERROR_DEVICE_DISCONNECTED: [
                "Check the physical connection",
                "Verify the device has power",
                "Try a different USB cable",
                "Check if the device needs to be reset"
            ],
            self.CONN_ERROR_DRIVER_ISSUE: [
                "Install or reinstall the USB drivers for the device",
                "Check Device Manager for driver warnings or errors",
                "Download the latest drivers from the manufacturer's website"
            ]
        }
        
        # Initialize connection status indicator
        self.connection_status_indicator = None
        self.connection_status_timer = None
        self.connection_quality_timer = None
    
    def handle_error(self, error_type: str, severity: str, context: Dict[str, Any] = None) -> None:
        """
        Handle an error with appropriate user feedback.
        
        Args:
            error_type: The type of error (from class constants)
            severity: The severity level (from class constants)
            context: Optional context dictionary with error details
        """
        if context is None:
            context = {}
            
        # Update error tracking
        current_time = datetime.datetime.now()
        self.last_error_time[error_type] = current_time
        self.error_count[error_type] = self.error_count.get(error_type, 0) + 1
        
        # Get the error message template
        message_template = self.error_messages.get(error_type, "Unknown error: {error_message}")
        
        # Format the error message with context
        try:
            error_message = message_template.format(**context)
        except KeyError:
            # Fallback if context doesn't have required keys
            error_message = message_template.format(error_message=str(context))
        
        # Log the error with appropriate prefix based on severity
        if severity == self.SEVERITY_ERROR or severity == self.SEVERITY_CRITICAL:
            self.app.log_frame.log_message(f"ERROR: {error_message}\n")
            
            # For critical errors, show a dialog
            if severity == self.SEVERITY_CRITICAL:
                self.app.after(0, lambda: messagebox.showerror("Critical Error", error_message))
        elif severity == self.SEVERITY_WARNING:
            self.app.log_frame.log_message(f"WARNING: {error_message}\n")
        else:
            self.app.log_frame.log_message(f"INFO: {error_message}\n")
        
        # Handle connection errors specially
        if error_type.startswith("conn_error_"):
            self._handle_connection_error(error_type, context)
            
            # Add resolution suggestions for connection errors
            if error_type in self.error_resolutions:
                suggestions = self.error_resolutions[error_type]
                self.app.log_frame.log_message(f"INFO: Suggested solutions:\n")
                for i, suggestion in enumerate(suggestions, 1):
                    self.app.log_frame.log_message(f"INFO: {i}. {suggestion}\n")
    
    def _handle_connection_error(self, error_type: str, context: Dict[str, Any]) -> None:
        """
        Handle connection errors with potential reconnection attempts.
        
        Args:
            error_type: The specific connection error type
            context: Error context dictionary
        """
        # Update connection status in UI
        if hasattr(self.app, 'connection_frame'):
            self.app.connection_frame.update_status(False)
            
            # Update connection quality based on error type
            if error_type == self.CONN_ERROR_DEVICE_DISCONNECTED:
                self._update_connection_quality(-30)  # Major issue
            elif error_type in [self.CONN_ERROR_TIMEOUT, self.CONN_ERROR_NO_RESPONSE]:
                self._update_connection_quality(-20)  # Moderate issue
            elif error_type in [self.CONN_ERROR_SIGNAL_LOST, self.CONN_ERROR_INVALID_RESPONSE]:
                self._update_connection_quality(-10)  # Minor issue
        
        # For unexpected disconnections or timeouts, attempt to reconnect if enabled
        if self.auto_reconnect_enabled and error_type in [
            self.CONN_ERROR_DEVICE_DISCONNECTED, 
            self.CONN_ERROR_TIMEOUT,
            self.CONN_ERROR_SIGNAL_LOST,
            self.CONN_ERROR_NO_RESPONSE
        ]:
            port = context.get('port')
            if port:
                self._attempt_reconnection(port)
    
    def _update_connection_quality(self, change: int) -> None:
        """
        Update the connection quality metric.
        
        Args:
            change: The change in quality (-100 to +100)
        """
        self.connection_quality = max(0, min(100, self.connection_quality + change))
        
        # Log significant quality changes
        if change <= -20:
            self.app.log_frame.log_message(f"WARNING: Connection quality degraded to {self.connection_quality}%\n")
        elif change >= 10:
            self.app.log_frame.log_message(f"INFO: Connection quality improved to {self.connection_quality}%\n")
            
        # Update the connection indicator if available
        if hasattr(self.app, 'connection_frame') and hasattr(self.app.connection_frame, 'update_connection_quality'):
            self.app.connection_frame.update_connection_quality(self.connection_quality)
    
    def _attempt_reconnection(self, port: Optional[str]) -> None:
        """
        Attempt to reconnect to the device.
        
        Args:
            port: The COM port to reconnect to
        """
        # Don't start a new reconnection thread if one is already running
        if self.reconnect_thread and self.reconnect_thread.is_alive():
            return
            
        # Reset reconnection state
        self.stop_reconnect = False
        self.reconnect_attempts = 0
        
        # Log the start of reconnection attempts
        self.app.log_frame.log_message(
            f"INFO: Starting automatic reconnection to {port}...\n"
        )
        
        # Start reconnection in a separate thread
        self.reconnect_thread = threading.Thread(
            target=self._reconnection_worker,
            args=(port,),
            daemon=True
        )
        self.reconnect_thread.start()
        
        # Update UI to show reconnection in progress
        if hasattr(self.app, 'connection_frame'):
            self.app.connection_frame.show_reconnecting_status()
    
    def _reconnection_worker(self, port: Optional[str]) -> None:
        """
        Worker thread for reconnection attempts.
        
        Args:
            port: The COM port to reconnect to
        """
        if not port or not hasattr(self.app, 'serial_service'):
            return
            
        while (not self.stop_reconnect and 
               self.reconnect_attempts < self.max_reconnect_attempts):
            
            self.reconnect_attempts += 1
            
            # Calculate backoff delay (increases with each attempt)
            current_delay = self.reconnect_delay * self.reconnect_attempts
            
            # Log reconnection attempt with progress bar
            self.app.log_frame.log_message(
                f"INFO: Reconnection attempt {self.reconnect_attempts}/{self.max_reconnect_attempts} "
                f"[{'=' * self.reconnect_attempts}{' ' * (self.max_reconnect_attempts - self.reconnect_attempts)}]\n"
            )
            
            # Update UI to show current reconnection attempt
            if hasattr(self.app, 'connection_frame'):
                self.app.after(0, self.app.connection_frame.update_reconnection_status, 
                              self.reconnect_attempts, self.max_reconnect_attempts)
            
            # Attempt to reconnect
            try:
                self.app.serial_service.connect(port)
                
                # Check if connection was successful
                if self.app.serial_service.is_connected:
                    self.app.log_frame.log_message(f"INFO: ✓ Reconnection successful\n")
                    
                    # Update connection quality
                    self._update_connection_quality(20)  # Successful reconnection improves quality
                    
                    # Reset reconnection UI
                    if hasattr(self.app, 'connection_frame'):
                        self.app.after(0, self.app.connection_frame.hide_reconnecting_status)
                    
                    return
            except Exception as e:
                # Log reconnection failure with details
                error_type, context = self.parse_error_from_exception(e)
                error_message = self.error_messages.get(error_type, str(e))
                
                try:
                    formatted_error = error_message.format(**context)
                except (KeyError, ValueError):
                    formatted_error = str(e)
                
                self.app.log_frame.log_message(f"ERROR: Reconnection failed: {formatted_error}\n")
            
            # Wait before next attempt with backoff
            for i in range(int(current_delay)):
                if self.stop_reconnect:
                    break
                time.sleep(1)
                
                # Update countdown in UI
                remaining = current_delay - i - 1
                if remaining > 0 and hasattr(self.app, 'connection_frame'):
                    self.app.after(0, self.app.connection_frame.update_reconnection_countdown, remaining)
        
        # Log if all reconnection attempts failed
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            self.app.log_frame.log_message(
                f"ERROR: Failed to reconnect after {self.max_reconnect_attempts} attempts\n"
            )
            
            # Show reconnection failure in UI
            if hasattr(self.app, 'connection_frame'):
                self.app.after(0, self.app.connection_frame.show_reconnection_failed)
                
            # Suggest manual reconnection
            self.app.log_frame.log_message(
                f"INFO: Please check your device connection and try reconnecting manually\n"
            )
    
    def stop_reconnection(self) -> None:
        """Stop any ongoing reconnection attempts."""
        self.stop_reconnect = True
        if self.reconnect_thread and self.reconnect_thread.is_alive():
            self.reconnect_thread.join(timeout=1)
            
        # Reset reconnection UI
        if hasattr(self.app, 'connection_frame'):
            self.app.connection_frame.hide_reconnecting_status()
            
        self.app.log_frame.log_message("INFO: Automatic reconnection stopped\n")
    
    def set_auto_reconnect(self, enabled: bool) -> None:
        """
        Enable or disable automatic reconnection attempts.
        
        Args:
            enabled: Whether to enable auto-reconnect
        """
        self.auto_reconnect_enabled = enabled
        status = "enabled" if enabled else "disabled"
        self.app.log_frame.log_message(f"INFO: Automatic reconnection {status}\n")
    
    def show_success_notification(self, message: str) -> None:
        """
        Show a success notification in the log.
        
        Args:
            message: The success message to display
        """
        self.app.log_frame.log_message(f"INFO: ✓ {message}\n")
    
    def show_operation_progress(self, operation: str, progress: int, total: int) -> None:
        """
        Show operation progress in the log.
        
        Args:
            operation: The operation name
            progress: Current progress value
            total: Total progress value
        """
        percentage = int((progress / total) * 100)
        bar_length = 20
        filled_length = int(bar_length * progress / total)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        self.app.log_frame.log_message(
            f"INFO: {operation}: {progress}/{total} ({percentage}%) [{bar}]\n"
        )
    
    def get_connection_status_message(self, is_connected: bool, port: Optional[str] = None, 
                                     quality: Optional[int] = None) -> str:
        """
        Get a detailed connection status message.
        
        Args:
            is_connected: Whether the device is connected
            port: Optional port name
            quality: Optional connection quality percentage
            
        Returns:
            Formatted status message
        """
        if is_connected:
            base_message = f"Connected to {port}" if port else "Connected"
            
            if quality is not None:
                if quality >= 90:
                    return f"{base_message} (Excellent)"
                elif quality >= 70:
                    return f"{base_message} (Good)"
                elif quality >= 40:
                    return f"{base_message} (Fair)"
                else:
                    return f"{base_message} (Poor)"
            return base_message
        else:
            return "Disconnected"
    
    def parse_error_from_exception(self, exception: Exception) -> tuple:
        """
        Parse an exception to determine error type and context.
        
        Args:
            exception: The exception to parse
            
        Returns:
            Tuple of (error_type, context_dict)
        """
        error_message = str(exception)
        error_type = self.CONN_ERROR_UNKNOWN
        context = {"error_message": error_message}
        
        # Check for common serial exception patterns
        if "could not open port" in error_message:
            if "PermissionError" in error_message:
                error_type = self.CONN_ERROR_ACCESS_DENIED
            elif "FileNotFoundError" in error_message:
                error_type = self.CONN_ERROR_PORT_NOT_FOUND
            else:
                error_type = self.CONN_ERROR_PORT_IN_USE
        elif "timeout" in error_message.lower():
            error_type = self.CONN_ERROR_TIMEOUT
        elif "disconnected" in error_message.lower():
            error_type = self.CONN_ERROR_DEVICE_DISCONNECTED
        elif "no response" in error_message.lower():
            error_type = self.CONN_ERROR_NO_RESPONSE
        elif "signal lost" in error_message.lower() or "connection lost" in error_message.lower():
            error_type = self.CONN_ERROR_SIGNAL_LOST
        elif "device busy" in error_message.lower() or "resource busy" in error_message.lower():
            error_type = self.CONN_ERROR_DEVICE_BUSY
        elif "invalid response" in error_message.lower() or "unexpected response" in error_message.lower():
            error_type = self.CONN_ERROR_INVALID_RESPONSE
        elif "driver" in error_message.lower():
            error_type = self.CONN_ERROR_DRIVER_ISSUE
        elif "hardware" in error_message.lower() or "failure" in error_message.lower():
            error_type = self.CONN_ERROR_HARDWARE_FAILURE
        elif "cable" in error_message.lower():
            error_type = self.CONN_ERROR_CABLE_ISSUE
        elif "locked" in error_message.lower() or "protected" in error_message.lower():
            error_type = self.CONN_ERROR_DEVICE_LOCKED
        
        return error_type, context
        
    def create_connection_status_indicator(self, parent_frame):
        """
        Create a visual connection status indicator in the parent frame.
        
        Args:
            parent_frame: The parent frame to place the indicator in
        """
        # Create a canvas for the status indicator
        self.connection_status_indicator = tk.Canvas(
            parent_frame, 
            width=15, 
            height=15, 
            bg=parent_frame.cget("bg"),
            highlightthickness=0
        )
        
        # Draw the initial indicator (red circle for disconnected)
        self.update_connection_indicator(False)
        
        return self.connection_status_indicator
        
    def update_connection_indicator(self, is_connected: bool, is_active: bool = False, quality: int = 100):
        """
        Update the visual connection status indicator.
        
        Args:
            is_connected: Whether the device is connected
            is_active: Whether there is active communication
            quality: Connection quality percentage (0-100)
        """
        if not self.connection_status_indicator:
            return
            
        # Clear previous indicator
        self.connection_status_indicator.delete("all")
        
        # Set color based on connection status and quality
        if is_connected:
            if is_active:
                # Bright green for active communication
                color = "#00FF00"
            else:
                # Color based on connection quality
                if quality >= 90:
                    color = "#00CC00"  # Good green
                elif quality >= 70:
                    color = "#88CC00"  # Yellow-green
                elif quality >= 40:
                    color = "#CCCC00"  # Yellow
                else:
                    color = "#CC8800"  # Orange
        else:
            # Red for disconnected
            color = "#FF0000"
            
        # Draw the indicator circle
        self.connection_status_indicator.create_oval(
            2, 2, 13, 13, 
            fill=color, 
            outline="#333333"
        )
        
        # Cancel any existing flash timer
        if self.connection_status_timer:
            self.connection_status_indicator.after_cancel(self.connection_status_timer)
            self.connection_status_timer = None
            
        # If active, schedule a return to normal state
        if is_active and is_connected:
            self.connection_status_timer = self.connection_status_indicator.after(
                300, lambda: self.update_connection_indicator(True, False, quality)
            )
            
    def flash_activity_indicator(self):
        """Flash the connection indicator to show activity."""
        if self.connection_status_indicator:
            self.update_connection_indicator(True, True, self.connection_quality)
            
    def start_connection_monitoring(self, interval_ms: int = 5000):
        """
        Start periodic connection quality monitoring.
        
        Args:
            interval_ms: Monitoring interval in milliseconds
        """
        # Cancel any existing timer
        if self.connection_quality_timer:
            self.app.after_cancel(self.connection_quality_timer)
            
        # Schedule the next check
        self.connection_quality_timer = self.app.after(
            interval_ms, lambda: self._check_connection_quality(interval_ms)
        )
        
    def _check_connection_quality(self, interval_ms: int):
        """
        Check connection quality and update indicators.
        
        Args:
            interval_ms: Monitoring interval for rescheduling
        """
        if hasattr(self.app, 'serial_service') and self.app.serial_service.is_connected:
            # Check time since last activity
            if hasattr(self.app.serial_service, 'last_activity_time'):
                time_since_activity = (datetime.datetime.now() - 
                                      self.app.serial_service.last_activity_time).total_seconds()
                
                # Gradually improve connection quality if no issues
                if time_since_activity < 10:  # Recent activity is good
                    self._update_connection_quality(1)  # Small improvement
                    
            # Update the connection indicator
            if hasattr(self.app, 'connection_frame'):
                self.app.connection_frame.update_connection_quality(self.connection_quality)
                
        # Reschedule the check
        self.connection_quality_timer = self.app.after(
            interval_ms, lambda: self._check_connection_quality(interval_ms)
        )