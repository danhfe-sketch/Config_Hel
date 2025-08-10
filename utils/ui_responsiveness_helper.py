"""
UI Responsiveness Helper

This module provides utilities to keep the UI responsive during long operations.
"""

import threading
import time
from typing import Callable, Optional


class UIResponsivenessHelper:
    """Helper class to maintain UI responsiveness during operations."""
    
    @staticmethod
    def run_with_ui_updates(operation_func: Callable, 
                           ui_update_func: Optional[Callable] = None,
                           update_interval: float = 0.1):
        """
        Run an operation while keeping the UI responsive.
        
        Args:
            operation_func: Function to run in background
            ui_update_func: Function to call for UI updates
            update_interval: How often to update UI (seconds)
        """
        result = {'completed': False, 'result': None, 'error': None}
        
        def worker():
            try:
                result['result'] = operation_func()
            except Exception as e:
                result['error'] = str(e)
            finally:
                result['completed'] = True
        
        # Start operation in background thread
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        
        # Keep UI responsive while waiting
        while not result['completed']:
            if ui_update_func:
                try:
                    ui_update_func()
                except:
                    pass  # Ignore UI update errors
            time.sleep(update_interval)
        
        # Wait for thread to complete
        thread.join(timeout=1.0)
        
        if result['error']:
            raise Exception(result['error'])
        
        return result['result']
    
    @staticmethod
    def safe_ui_call(ui_func: Callable, *args, **kwargs):
        """Safely call a UI function, ignoring errors."""
        try:
            return ui_func(*args, **kwargs)
        except Exception as e:
            print(f"UI call error (ignored): {e}")
            return None
