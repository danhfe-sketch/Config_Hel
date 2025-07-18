#!/usr/bin/env python3
"""
Test script to verify parameter factory functionality
"""

from services.i18n_service import I18nService
from services.validation_service import ValidationService
from ui.parameter_factory import ParameterFactory

def test_parameter_creation():
    """Test if numeric parameters can be created properly."""
    
    # Initialize services
    i18n = I18nService(language='pt_BR')
    validation_service = ValidationService(i18n)
    
    def dummy_send_command(command):
        print(f"Would send command: {command}")
    
    # Create parameter factory
    factory = ParameterFactory(validation_service, i18n, dummy_send_command)
    
    # Test numeric parameters
    numeric_params = ['vibration', 'sensitivity', 'timer_ign_on', 'timer_ign_off', 'heartbeat_ign_on', 'heartbeat_ign_off']
    
    print("Testing numeric parameter creation:")
    for param_name in numeric_params:
        param = factory.create_parameter(param_name)
        if param:
            print(f"✓ {param_name}: Created successfully")
            print(f"  - Type: {param.definition.param_type}")
            print(f"  - Label: {param.definition.display_label}")
            print(f"  - Command: {param.definition.at_command_template}")
            print(f"  - Validation rules: {param.definition.validation_rules}")
        else:
            print(f"✗ {param_name}: Failed to create")
        print()

if __name__ == "__main__":
    test_parameter_creation()