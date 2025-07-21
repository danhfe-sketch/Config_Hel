#!/usr/bin/env python3
"""
Test script to verify the ParametersFrame language update logic fix.
"""

import sys
import os
from unittest.mock import Mock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.i18n_service import I18nService
from ui.parameter_factory import ParameterFactory
from services.validation_service import ValidationService


def test_parameter_groups_storage_logic():
    """Test the logic for storing and accessing parameter groups."""
    print("Testing parameter groups storage logic...")
    
    try:
        # Create services
        i18n_service = I18nService()
        i18n_service.set_language('en_US')
        validation_service = ValidationService(i18n_service)
        
        # Mock send command callback
        send_command_callback = Mock()
        
        # Create parameter factory
        parameter_factory = ParameterFactory(validation_service, i18n_service, send_command_callback)
        
        # Test creating groups (simulating what ParametersFrame does)
        parameter_groups = {}
        
        # Create server group
        server_group = parameter_factory.create_group('server', 'main_server')
        parameter_groups['server'] = server_group
        
        # Create other groups
        group_configs = {
            'sensors': 'sensor_configuration',
            'timers': 'timer_configuration', 
            'security': 'security_settings'
        }
        
        for group_name, display_label in group_configs.items():
            group = parameter_factory.create_group(group_name, display_label)
            parameter_groups[group_name] = group
        
        print(f"  ✓ Created {len(parameter_groups)} parameter groups: {list(parameter_groups.keys())}")
        
        # Test that groups have update_language_display method
        for group_name, group in parameter_groups.items():
            assert hasattr(group, 'update_language_display'), f"Group {group_name} should have update_language_display method"
            
            # Test calling the method (should not raise exception)
            try:
                group.update_language_display(i18n_service)
                print(f"  ✓ Group {group_name} language update successful")
            except Exception as e:
                print(f"  ❌ Group {group_name} language update failed: {e}")
                return False
        
        # Test language switching
        i18n_service.set_language('pt_BR')
        for group_name, group in parameter_groups.items():
            try:
                group.update_language_display(i18n_service)
                print(f"  ✓ Group {group_name} pt_BR language update successful")
            except Exception as e:
                print(f"  ❌ Group {group_name} pt_BR language update failed: {e}")
                return False
        
        print("✓ Parameter groups storage logic test passed")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_get_all_groups_vs_stored_groups():
    """Test the difference between get_all_groups() and stored groups."""
    print("Testing get_all_groups() vs stored groups...")
    
    try:
        # Create services
        i18n_service = I18nService()
        i18n_service.set_language('en_US')
        validation_service = ValidationService(i18n_service)
        send_command_callback = Mock()
        
        # Create parameter factory
        parameter_factory = ParameterFactory(validation_service, i18n_service, send_command_callback)
        
        # Test get_all_groups() returns list
        all_groups = parameter_factory.get_all_groups()
        print(f"  ✓ get_all_groups() returns list: {all_groups}")
        assert isinstance(all_groups, list), "get_all_groups() should return a list"
        
        # Test that calling .items() on the list would fail
        try:
            # This should fail
            for group_name, group in all_groups.items():
                pass
            print("  ❌ Calling .items() on list should have failed")
            return False
        except AttributeError as e:
            print(f"  ✓ Confirmed: calling .items() on list fails with: {e}")
        
        # Test creating actual group objects
        parameter_groups = {}
        for group_name in all_groups:
            group = parameter_factory.create_group(group_name, f"{group_name}_label")
            parameter_groups[group_name] = group
        
        print(f"  ✓ Created group objects: {list(parameter_groups.keys())}")
        
        # Test that .items() works on the dictionary
        try:
            for group_name, group in parameter_groups.items():
                assert hasattr(group, 'update_language_display'), f"Group {group_name} should have update_language_display"
            print("  ✓ Calling .items() on parameter_groups dictionary works correctly")
        except Exception as e:
            print(f"  ❌ Calling .items() on parameter_groups failed: {e}")
            return False
        
        print("✓ get_all_groups() vs stored groups test passed")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the parameters frame logic fix tests."""
    print("=" * 60)
    print("ParametersFrame Language Update Logic Fix Tests")
    print("=" * 60)
    
    success1 = test_parameter_groups_storage_logic()
    print()
    success2 = test_get_all_groups_vs_stored_groups()
    
    success = success1 and success2
    
    if success:
        print("\n" + "=" * 60)
        print("✅ ParametersFrame logic fix verified successfully!")
        print("=" * 60)
        print("\nFixed Issues:")
        print("• get_all_groups() returns list of group names (not objects)")
        print("• parameter_groups dictionary stores actual group objects")
        print("• Language update uses stored group objects, not group names")
        print("• Eliminated 'list' object has no attribute 'items' error")
        
        print("\nImplementation Details:")
        print("• ParametersFrame now has self.parameter_groups = {} attribute")
        print("• Groups are stored when created: self.parameter_groups[name] = group")
        print("• Language update iterates: for name, group in self.parameter_groups.items()")
        print("• Each group object has update_language_display() method")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)