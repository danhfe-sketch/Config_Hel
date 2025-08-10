"""
UI Responsiveness Monitor

This module helps monitor and maintain UI responsiveness during long operations.
"""

import threading
import time
import tkinter as tk
from typing import Callable, Optional


class UIResponsivenessMonitor:
    """Monitor and maintain UI responsiveness."""
    
    def __init__(self, root_widget):
        """Initialize the monitor."""
        self.root = root_widget
        self.monitoring = False
        self.monitor_thread = None
        self.update_interval = 0.05  # 50ms updates
    
    def start_monitoring(self):
        """Start monitoring UI responsiveness."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="UIResponsivenessMonitor"
        )
        self.monitor_thread.start()
        print("🔍 UI responsiveness monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring UI responsiveness."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        print("⏹️  UI responsiveness monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                # Schedule a UI update to keep it responsive
                if self.root:
                    self.root.after_idle(self._ui_update)
                
                # Sleep to prevent excessive CPU usage
                time.sleep(self.update_interval)
                
            except Exception as e:
                print(f"UI monitor error (non-critical): {e}")
                break
    
    def _ui_update(self):
        """Perform a minimal UI update."""
        try:
            # Just update the UI without doing anything visible
            self.root.update_idletasks()
        except Exception:
            # Ignore UI update errors
            pass
    
    def ensure_responsive_operation(self, operation_func: Callable, 
                                  progress_callback: Optional[Callable] = None):
        """
        Run an operation while ensuring UI remains responsive.
        
        Args:
            operation_func: Function to run
            progress_callback: Optional progress callback
        """
        def wrapper():
            try:
                # Start monitoring
                self.start_monitoring()
                
                # Run the operation
                result = operation_func()
                
                return result
                
            finally:
                # Stop monitoring
                self.stop_monitoring()
        
        # Run in background thread
        result_container = {'result': None, 'error': None, 'completed': False}
        
        def worker():
            try:
                result_container['result'] = wrapper()
            except Exception as e:
                result_container['error'] = str(e)
            finally:
                result_container['completed'] = True
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        
        # Wait for completion while keeping UI responsive
        while not result_container['completed']:
            if self.root:
                try:
                    self.root.update_idletasks()
                except:
                    pass
            time.sleep(0.01)  # 10ms updates
        
        if result_container['error']:
            raise Exception(result_container['error'])
        
        return result_container['result']


# Global monitor instance
_ui_monitor = None


def get_ui_monitor(root_widget=None):
    """Get or create the global UI monitor."""
    global _ui_monitor
    if _ui_monitor is None and root_widget:
        _ui_monitor = UIResponsivenessMonitor(root_widget)
    return _ui_monitor


def ensure_ui_responsive(operation_func: Callable, root_widget=None):
    """Decorator to ensure UI responsiveness during operations."""
    def decorator(*args, **kwargs):
        monitor = get_ui_monitor(root_widget)
        if monitor:
            return monitor.ensure_responsive_operation(lambda: operation_func(*args, **kwargs))
        else:
            return operation_func(*args, **kwargs)
    return decorator
