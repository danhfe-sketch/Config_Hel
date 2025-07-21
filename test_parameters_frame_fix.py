#!/usr/bin/env python3
"""
Test script to verify the ParametersFrame language update fix.
"""

import sys
import os
from unittest.mock import Mock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.i18n_service import I18nService


def test_parameters_frame_language_update():
    """Test that parameters frame language update works without errors."""
    print("Testing ParametersFrame language update fix...")
    
    try:
        # Create mock services
        i18n_service = I18nService()
        i18n_service.set_language('en_US')
        
        # Create mock master with serial service
        mock_master = Mock()
        mock_master.serial_service = Mock()
        
        # Import and create parameters frame
        from ui.parameters_frame import ParametersFrame
        
        # This should not raise an exception during initialization
        params_frame = ParametersFrame(mock_master, i18n_service)
        
        print("  ✓ ParametersFrame created successfully")
        
        # Test that parameter_groups attribute exists
        assert hasattr(params_frame, 'parameter_groups'), "ParametersFrame should have parameter_groups attribute"
        assert isinstance(params_frame.parameter_groups, dict), "parameter_groups should be a dictionary"
        
        print(f"  ✓ parameter_groups attribute exists: {list(params_frame.parameter_groups.keys())}")
        
        # Test language update (this should not raise an exception)
        try:
            params_frame.update_language_display(i18n_service)
            print("  ✓ update_language_display() executed without errors")
        except Exception as e:
            print(f"  ❌ update_language_display() failed: {e}")
            return False
        
        # Test switching to different language
        try:
            i18n_service.set_language('pt_BR')
            params_frame.update_language_display(i18n_service)
            print("  ✓ Language switch to pt_BR successful")
        except Exception as e:
            print(f"  ❌ Language switch failed: {e}")
            return False
        
        print("✓ ParametersFrame language update fix test passed")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the parameters frame fix test."""
    print("=" * 60)
    print("ParametersFrame Language Update Fix Test")
    print("=" * 60)
    
    success = test_parameters_frame_language_update()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ ParametersFrame fix verified successfully!")
        print("=" * 60)
        print("\nFixed Issues:")
        print("• Added parameter_groups storage in ParametersFrame")
        print("• Fixed language update to use stored group objects")
        print("• Eliminated 'list' object has no attribute 'items' error")
        print("• Language switching now works without crashes")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)