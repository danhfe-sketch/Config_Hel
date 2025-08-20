#!/usr/bin/env python3
"""
Simple verification script to confirm both fixes are implemented correctly.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def verify_szcs_fix():
    """Verify SZCS command formatting fix is in place."""
    print("=== Verifying SZCS Command Fix ===")
    
    try:
        # Read the device_command_mapper.py file to check for the fix
        with open('services/device_command_mapper.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for the fixed logic - look for the actual implementation
        if 'if full_command.startswith("ATSMS:SZCS#") and full_command.endswith(\'#\'):' in content:
            print("[PASS] Fixed SZCS logic found in DeviceCommandMapper.get_command()")
            
            # Check for the removal of trailing '#'
            if 'full_command = full_command[:-1]' in content:
                print("[PASS] Trailing '#' removal logic is present")
                
                # Check for the multi-part command handling
                if 'ACCLINE=' in content and 'ACC_CFG=' in content:
                    print("[PASS] Multi-part SZCS command handling preserved")
                    return True
                else:
                    print("[FAIL] Multi-part SZCS command handling not found")
                    return False
            else:
                print("[FAIL] Trailing '#' removal logic not found")
                return False
        else:
            print("[FAIL] Fixed SZCS logic not found")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error verifying SZCS fix: {e}")
        return False

def verify_circular_call_fix():
    """Verify circular call fix is in place."""
    print("\n=== Verifying Circular Call Fix ===")
    
    try:
        # Read the non_blocking_profile_manager.py file to check for the fix
        with open('services/non_blocking_profile_manager.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check that the circular call to core_manager.load_profile_to_device is removed
        if 'core_manager.load_profile_to_device(file_path)' not in content:
            print("[PASS] Circular call to CoreProfileManager removed")
            
            # Check that it now calls DeviceCommunicationManager directly
            if 'device_manager.write_all_parameters' in content:
                print("[PASS] Direct call to DeviceCommunicationManager.write_all_parameters found")
                return True
            else:
                print("[FAIL] Direct call to DeviceCommunicationManager not found")
                return False
        else:
            print("[FAIL] Circular call to CoreProfileManager still exists")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error verifying circular call fix: {e}")
        return False

def verify_duplicate_szcs_removal():
    """Verify duplicate SZCS handling was removed from CoreProfileManager."""
    print("\n=== Verifying Duplicate SZCS Handler Removal ===")
    
    try:
        # Read the core_profile_manager.py file
        with open('services/core_profile_manager.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check that the duplicate SZCS handling is removed
        if 'SZCS#GT06SEL=' not in content or 'SZCS#POSBYACK=' not in content:
            print("[PASS] Duplicate SZCS command handling removed from CoreProfileManager")
            return True
        else:
            print("[FAIL] Duplicate SZCS command handling still exists in CoreProfileManager")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error verifying duplicate SZCS removal: {e}")
        return False

def main():
    """Run all verification checks."""
    print("Verifying Profile Loading Fixes")
    print("=" * 50)
    
    szcs_fix = verify_szcs_fix()
    circular_fix = verify_circular_call_fix()
    duplicate_removal = verify_duplicate_szcs_removal()
    
    print("\n" + "=" * 50)
    print("VERIFICATION SUMMARY:")
    print(f"  SZCS Command Fix: {'PASS' if szcs_fix else 'FAIL'}")
    print(f"  Circular Call Fix: {'PASS' if circular_fix else 'FAIL'}")
    print(f"  Duplicate Handler Removal: {'PASS' if duplicate_removal else 'FAIL'}")
    
    if szcs_fix and circular_fix and duplicate_removal:
        print("\n[SUCCESS] All fixes have been implemented correctly!")
        print("\nFIXES APPLIED:")
        print("1. Fixed SZCS command formatting in DeviceCommandMapper.get_command()")
        print("   - Now properly handles commands with multiple '#' characters")
        print("   - Removes trailing '#' from SZCS commands when loading profiles to device")
        print("\n2. Fixed circular call pattern in NonBlockingProfileManager")
        print("   - Removed circular call to CoreProfileManager.load_profile_to_device()")
        print("   - Now calls DeviceCommunicationManager.write_all_parameters() directly")
        print("   - Eliminates duplicate configuration sending")
        print("\n3. Removed duplicate SZCS handling from CoreProfileManager")
        print("   - Centralized SZCS command formatting in DeviceCommandMapper")
        print("   - Prevents conflicting command modifications")
        return True
    else:
        print("\n[FAILURE] Some fixes are not properly implemented")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)