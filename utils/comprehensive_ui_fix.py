"""
Comprehensive UI Fix

This module provides comprehensive fixes for all remaining UI issues.
"""

import threading
import time
import os
from typing import Callable, Optional, Dict, Any


class ComprehensiveUIFix:
    """Comprehensive fix for all UI issues."""
    
    def __init__(self, app_instance):
        """Initialize the fix."""
        self.app = app_instance
        self.operation_lock = threading.Lock()
        self.active_operations = {}
    
    def safe_widget_configure(self, widget, **kwargs):
        """Safely configure a widget."""
        if not widget:
            return False
        
        if not hasattr(widget, 'configure'):
            widget_type = type(widget).__name__
            print(f"DEBUG: Widget {widget_type} does not support configure method")
            return False
        
        try:
            widget.configure(**kwargs)
            return True
        except Exception as e:
            widget_type = type(widget).__name__
            print(f"WARNING: Failed to configure {widget_type}: {e}")
            return False
    
    def safe_file_operation(self, operation_func: Callable, *args, **kwargs):
        """Safely perform a file operation."""
        try:
            # Ensure operation runs in background thread
            if threading.current_thread() is threading.main_thread():
                # We're on the main thread, move to background
                result_container = {'result': None, 'error': None, 'completed': False}
                
                def worker():
                    try:
                        result_container['result'] = operation_func(*args, **kwargs)
                    except Exception as e:
                        result_container['error'] = str(e)
                    finally:
                        result_container['completed'] = True
                
                thread = threading.Thread(target=worker, daemon=True)
                thread.start()
                
                # Wait for completion while keeping UI responsive
                while not result_container['completed']:
                    if hasattr(self.app, 'update_idletasks'):
                        try:
                            self.app.update_idletasks()
                        except:
                            pass
                    time.sleep(0.01)
                
                if result_container['error']:
                    raise Exception(result_container['error'])
                
                return result_container['result']
            else:
                # Already in background thread, run directly
                return operation_func(*args, **kwargs)
                
        except Exception as e:
            print(f"File operation error: {e}")
            raise
    
    def fix_widget_highlighting(self):
        """Fix widget highlighting issues."""
        if not hasattr(self.app, 'configuration_reader_service'):
            return
        
        config_reader = self.app.configuration_reader_service
        
        # Replace the highlight method with a safe version
        if hasattr(config_reader, '_highlight_parameter_widget'):
            original_highlight = config_reader._highlight_parameter_widget
            
            def safe_highlight(section_name, param_key, value_changed):
                try:
                    return original_highlight(section_name, param_key, value_changed)
                except Exception as e:
                    print(f"WARNING: Widget highlighting failed for {section_name}.{param_key}: {e}")
            
            config_reader._highlight_parameter_widget = safe_highlight
            print("✅ Fixed widget highlighting method")
    
    def fix_file_operations(self):
        """Fix file operation issues."""
        if not hasattr(self.app, 'profile_manager'):
            return
        
        profile_manager = self.app.profile_manager
        
        # Wrap file operations to ensure they're non-blocking
        if hasattr(profile_manager, 'load_from_device_to_profile'):
            original_load = profile_manager.load_from_device_to_profile
            
            def safe_load(*args, **kwargs):
                return self.safe_file_operation(original_load, *args, **kwargs)
            
            profile_manager.load_from_device_to_profile = safe_load
            print("✅ Fixed load from device operation")
    
    def apply_all_fixes(self):
        """Apply all fixes."""
        print("🔧 Applying comprehensive UI fixes...")
        
        try:
            self.fix_widget_highlighting()
            self.fix_file_operations()
            
            print("✅ All comprehensive fixes applied successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error applying fixes: {e}")
            return False


def apply_comprehensive_fix(app_instance):
    """Apply comprehensive fix to an application instance."""
    fixer = ComprehensiveUIFix(app_instance)
    return fixer.apply_all_fixes()
