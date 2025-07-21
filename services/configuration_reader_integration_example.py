"""
Integration example for ConfigurationReaderService.

This file shows how to integrate the ConfigurationReaderService with the main application
and connect it to the serial service for actual device communication.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.configuration_reader_service import ConfigurationReaderService


def integrate_configuration_reader_service(app_instance):
    """
    Example of how to integrate ConfigurationReaderService with the main application.
    
    Args:
        app_instance: Main application instance
    """
    
    # 1. Initialize the service (this would typically be done in main.py)
    if not hasattr(app_instance, 'configuration_reader_service'):
        app_instance.configuration_reader_service = ConfigurationReaderService(
            app_instance, 
            app_instance.i18n
        )
    
    # 2. Connect the service to the serial service for response capture
    # This would modify the serial service's process_device_response method
    original_process_response = app_instance.serial_service.process_device_response
    
    def enhanced_process_response(response):
        # Call original processing
        original_process_response(response)
        
        # Also let configuration reader service capture responses if it's waiting
        if hasattr(app_instance, 'configuration_reader_service'):
            app_instance.configuration_reader_service.capture_device_response(response)
    
    # Replace the method
    app_instance.serial_service.process_device_response = enhanced_process_response
    
    return app_instance.configuration_reader_service


def add_configuration_reading_to_actions_frame(actions_frame, app_instance):
    """
    Example of how to add configuration reading functionality to the ActionsFrame.
    
    Args:
        actions_frame: The ActionsFrame instance
        app_instance: Main application instance
    """
    import customtkinter as ctk
    
    # Ensure the configuration reader service is available
    if not hasattr(app_instance, 'configuration_reader_service'):
        integrate_configuration_reader_service(app_instance)
    
    def on_read_configuration():
        """Handle the read configuration button click."""
        service = app_instance.configuration_reader_service
        
        if service.is_reading_in_progress():
            app_instance.log_frame.log_message("INFO: Configuration reading is already in progress\n")
            return
        
        if not app_instance.serial_service.is_connected:
            app_instance.log_frame.log_message("ERROR: Device must be connected to read configuration\n")
            return
        
        # Define progress callback
        def on_progress(current, total, status):
            progress_percent = int((current / total) * 100)
            app_instance.log_frame.log_message(f"INFO: Reading progress: {progress_percent}% - {status}\n")
        
        # Define completion callback
        def on_completion(result, error_message):
            if result.success:
                success_msg = f"Configuration reading completed successfully. " \
                             f"Read {len(result.parameters_read) - len(result.failed_parameters)} of {result.total_parameters} parameters " \
                             f"in {result.read_duration:.2f} seconds."
                app_instance.log_frame.log_message(f"INFO: {success_msg}\n")
                
                if result.failed_parameters:
                    app_instance.log_frame.log_message(f"WARNING: Failed to read: {', '.join(result.failed_parameters)}\n")
            else:
                app_instance.log_frame.log_message(f"ERROR: Configuration reading failed: {error_message}\n")
        
        # Start the configuration reading
        app_instance.log_frame.log_message("INFO: Starting device configuration reading...\n")
        service.read_all_configurations(
            progress_callback=on_progress,
            completion_callback=on_completion
        )
    
    # Add the button to the actions frame (this would be integrated into the actual UI)
    read_config_button = ctk.CTkButton(
        actions_frame,
        text=app_instance.i18n.get("read_configuration", "Read Configuration"),
        command=on_read_configuration
    )
    
    return read_config_button


def example_usage():
    """
    Example of how the ConfigurationReaderService would be used.
    """
    print("ConfigurationReaderService Integration Example")
    print("=" * 50)
    
    print("\n1. Service Integration:")
    print("   - Add ConfigurationReaderService to main application")
    print("   - Connect to serial service for response capture")
    print("   - Integrate with UI components")
    
    print("\n2. Reading All Configurations:")
    print("   - Call read_all_configurations() with callbacks")
    print("   - Monitor progress through progress_callback")
    print("   - Handle completion through completion_callback")
    
    print("\n3. Reading Specific Parameters:")
    print("   - Call read_specific_parameter() for individual parameters")
    print("   - Parse responses using built-in parsing logic")
    print("   - Handle errors with specific error messages")
    
    print("\n4. UI Integration:")
    print("   - Connect to 'Checar configuração' button")
    print("   - Update UI fields automatically from device responses")
    print("   - Show progress indication during reading")
    
    print("\n5. Error Handling:")
    print("   - Specific error messages for different failure types")
    print("   - Graceful handling of partial configuration reads")
    print("   - Retry logic for failed parameter queries")
    
    print("\nThe service is now ready for integration with the main application!")


if __name__ == "__main__":
    example_usage()