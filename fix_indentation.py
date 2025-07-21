"""
Fix indentation issues in the ConfigurationReaderService file.
"""

import os
import sys

def fix_indentation():
    """Fix indentation issues in the ConfigurationReaderService file."""
    # Path to the configuration reader service file
    service_path = os.path.join('services', 'configuration_reader_service.py')
    
    # Check if the file exists
    if not os.path.exists(service_path):
        print(f"ERROR: Could not find {service_path}")
        return False
    
    # Read the file
    with open(service_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find and fix indentation issues
    fixed_lines = []
    in_method = False
    method_indent = 0
    
    for i, line in enumerate(lines):
        # Check for method definitions
        if line.strip().startswith('def ') and line.strip().endswith(':'):
            in_method = True
            method_indent = len(line) - len(line.lstrip())
            fixed_lines.append(line)
        # Check for empty method bodies
        elif in_method and line.strip() == '"""':
            # This is a docstring after a method definition, add proper indentation
            if method_indent == 0:
                # Class method
                fixed_lines.append(' ' * 4 + line.lstrip())
            else:
                # Already indented
                fixed_lines.append(line)
        # Regular line
        else:
            fixed_lines.append(line)
            # Reset method tracking if we're past the method definition
            if in_method and line.strip() and not line.strip().startswith('"""'):
                in_method = False
    
    # Write the fixed content back to the file
    with open(service_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    print("SUCCESS: Fixed indentation issues in ConfigurationReaderService")
    return True

if __name__ == "__main__":
    fix_indentation()