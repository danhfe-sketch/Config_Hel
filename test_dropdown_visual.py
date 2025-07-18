#!/usr/bin/env python3
"""
Visual test for dropdown parameters to verify UI appearance and functionality.
"""

import customtkinter as ctk
import sys
import threading
import time

sys.path.append('.')

from main import App


def test_visual_dropdowns():
    """Test dropdown parameters visually."""
    print("Starting visual test for dropdown parameters...")
    
    # Create the main application
    app = App()
    
    # Get the parameters frame
    params_frame = app.params_frame
    
    # Print information about dropdown parameters
    if hasattr(params_frame, 'parameter_widgets'):
        widgets = params_frame.parameter_widgets
        
        print(f"\nFound {len(widgets)} parameter widgets:")
        for name, widget in widgets.items():
            widget_type = type(widget).__name__
            print(f"  - {name}: {widget_type}")
            
            # Check if it's a dropdown parameter
            if widget_type == 'DropdownParameter':
                allowed_values = widget.definition.validation_rules.get('allowed_values', [])
                print(f"    Options: {allowed_values}")
                print(f"    AT Command: {widget.definition.at_command_template}")
    
    # Function to test dropdown functionality after a delay
    def test_dropdowns():
        time.sleep(2)  # Wait for UI to load
        
        try:
            # Test heartbeat interval
            if 'heartbeat_interval' in widgets:
                heartbeat_widget = widgets['heartbeat_interval']
                print(f"\nTesting heartbeat interval dropdown...")
                print(f"Current value: {heartbeat_widget.get_value()}")
                
                # Test setting a value
                heartbeat_widget.set_value('5min')
                print(f"Set to 5min, current value: {heartbeat_widget.get_value()}")
            
            # Test curve sensor
            if 'curve_sensor' in widgets:
                curve_widget = widgets['curve_sensor']
                print(f"\nTesting curve sensor dropdown...")
                print(f"Current value: {curve_widget.get_value()}")
                
                # Test setting a value
                curve_widget.set_value('Auto')
                print(f"Set to Auto, current value: {curve_widget.get_value()}")
            
            print("\n✅ Dropdown functionality test completed!")
            
        except Exception as e:
            print(f"❌ Error during dropdown test: {e}")
    
    # Start the test in a separate thread
    test_thread = threading.Thread(target=test_dropdowns)
    test_thread.daemon = True
    test_thread.start()
    
    print("\nApplication started. Check the UI for dropdown parameters.")
    print("The application should show:")
    print("  - Heartbeat Interval dropdown with time options")
    print("  - Curve Sensor dropdown with Enabled/Disabled/Auto options")
    print("\nClose the window to exit.")
    
    # Run the application
    app.mainloop()


if __name__ == "__main__":
    test_visual_dropdowns()