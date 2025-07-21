#!/usr/bin/env python3
"""
Test script to verify the ParameterFactory get_all_groups method fix.
"""

import sys
import os
from unittest.mock import Mock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.parameter_factory import ParameterFactory
from services.validation_service import ValidationService
from services.i18n_service import I18nService


def test_parameter_factory_get_all_groups():
    """Test that get_all_groups method works correctly."""
    print("Testing ParameterFactory.get_all_groups() method...")
    
    # Create mock services
    i18n_service = I18nService()
    i18n_service.set_language('en_US')
    validation_service = ValidationService(i18n_service)
    
    # Mock send command callback
    send_command_callback = Mock()
    
    # Create parameter factory
    parameter_factory = ParameterFactory(validation_service, i18n_service, send_command_callback)
    
    # Test get_all_groups method
    try:
        groups = parameter_factory.get_all_groups()
        print(f"  ✓ get_all_groups() returned: {groups}")
        
        # Verify it returns a list
        assert isinstance(groups, list), "get_all_groups should return a list"
        
        # Verify it contains expected groups
        expected_groups = ['server', 'sensors', 'timers', 'security']
        for expected_group in expected_groups:
            assert expected_group in groups, f"Expected group '{expected_group}' should be in groups list"
        
        print(f"  ✓ All expected groups found: {expected_groups}")
        
        # Test get_parameters_by_group method
        for group in groups:
            parameters = parameter_factory.get_parameters_by_group(group)
            print(f"  ✓ Group '{group}' has {len(parameters)} parameters: {parameters}")
            assert isinstance(parameters, list), f"get_parameters_by_group should return a list for group {group}"
        
        print("✓ ParameterFactory.get_all_groups() method test passed")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the parameter factory fix test."""
    print("=" * 60)
    print("ParameterFactory get_all_groups() Method Fix Test")
    print("=" * 60)
    
    success = test_parameter_factory_get_all_groups()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ ParameterFactory fix verified successfully!")
        print("=" * 60)
        print("\nFixed Issues:")
        print("• Added missing get_all_groups() method")
        print("• Added get_parameters_by_group() helper method")
        print("• Methods return properly formatted lists")
        print("• UI language refresh should now work without errors")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)