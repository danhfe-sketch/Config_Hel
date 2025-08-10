"""
Simple Progress Dialog - Thread-safe progress dialog with language support.

This module provides a simple, reliable progress dialog for profile operations
that integrates with the existing translation system and uses thread-safe updates.
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
from typing import Callable, Optional


class SimpleProgressDialog:
    """Simple, thread-safe progress dialog with language support."""
    
    def __init__(self, parent, title_key: str, total_steps: int, i18n_service=None):
        """
        Initialize the progress dialog.
        
        Args:
            parent: Parent window
            title_key: Translation key for dialog title
            total_steps: Total number of steps for progress calculation
            i18n_service: Translation service instance
        """
        self.parent = parent
        self.title_key = title_key
        self.total_steps = max(1, total_steps)  # Ensure at least 1 to avoid division by zero
        self.i18n = i18n_service
        self.current_step = 0
        self.is_cancelled = False
        self.is_closed = False
        self.cancel_callback = None
        self.dialog = None
        
        # Create dialog in main thread
        self._create_dialog()
        
    def _create_dialog(self):
        """Create the progress dialog using basic Tkinter components."""
        try:
            # Create toplevel window
            self.dialog = tk.Toplevel(self.parent)
            
            # Set title using translation service
            title = self._get_translated_text(self.title_key, "Progress")
            self.dialog.title(title)
            
            self.dialog.geometry("400x150")
            self.dialog.resizable(False, False)
            
            # Set colors to match application theme
            self.dialog.configure(bg='#2b2b2b')
            
            # Center the dialog
            self._center_dialog()
            
            # Make modal
            self.dialog.transient(self.parent)
            self.dialog.grab_set()
            
            # Create main container with padding
            main_frame = tk.Frame(self.dialog, bg='#2b2b2b', padx=20, pady=20)
            main_frame.pack(fill="both", expand=True)
            
            # Status message label
            self.status_label = tk.Label(
                main_frame,
                text=self._get_translated_text("initializing", "Initializing..."),
                font=("Segoe UI", 10),
                fg='#cccccc',
                bg='#2b2b2b',
                wraplength=360,
                justify='center'
            )
            self.status_label.pack(pady=(0, 15))
            
            # Progress bar using ttk for better appearance
            style = ttk.Style()
            style.theme_use('clam')
            style.configure("Custom.Horizontal.TProgressbar", 
                          background='#0078d4',
                          troughcolor='#404040',
                          borderwidth=0,
                          lightcolor='#0078d4',
                          darkcolor='#0078d4')
            
            self.progress_var = tk.DoubleVar()
            self.progress_bar = ttk.Progressbar(
                main_frame,
                variable=self.progress_var,
                maximum=100,
                style="Custom.Horizontal.TProgressbar",
                length=350
            )
            self.progress_bar.pack(pady=(0, 10))
            
            # Percentage label
            self.percentage_label = tk.Label(
                main_frame,
                text="0%",
                font=("Segoe UI", 9),
                fg='#cccccc',
                bg='#2b2b2b'
            )
            self.percentage_label.pack(pady=(0, 15))
            
            # Cancel button
            self.cancel_button = tk.Button(
                main_frame,
                text=self._get_translated_text("cancel", "Cancel"),
                command=self._on_cancel,
                font=("Segoe UI", 9),
                bg='#404040',
                fg='white',
                activebackground='#505050',
                activeforeground='white',
                relief='flat',
                borderwidth=0,
                padx=15,
                pady=5
            )
            self.cancel_button.pack()
            
            # Handle window close
            self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)
            
        except Exception as e:
            print(f"Error creating progress dialog: {e}")
            self.dialog = None
            
    def _get_translated_text(self, key: str, default: str) -> str:
        """Get translated text using i18n service or return default."""
        if self.i18n:
            return self.i18n.get(key, default)
        return default
        
    def _center_dialog(self):
        """Center the dialog on parent window."""
        try:
            self.dialog.update_idletasks()
            
            # Get parent position and size
            parent_x = self.parent.winfo_x()
            parent_y = self.parent.winfo_y()
            parent_width = self.parent.winfo_width()
            parent_height = self.parent.winfo_height()
            
            # Calculate center position
            dialog_width = 400
            dialog_height = 150
            x = parent_x + (parent_width - dialog_width) // 2
            y = parent_y + (parent_height - dialog_height) // 2
            
            self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        except Exception:
            # If centering fails, dialog will appear at default position
            pass
            
    def update_progress(self, current_step: int, message_key: str, param_name: str = ""):
        """
        Update progress - thread safe using tkinter's after() method.
        
        Args:
            current_step: Current step number (0-based or 1-based)
            message_key: Translation key for status message
            param_name: Optional parameter name to include in message
        """
        if self.is_closed or not self.dialog:
            return
            
        # Schedule update on main thread using after_idle for immediate execution
        try:
            if self.dialog.winfo_exists():
                self.dialog.after_idle(self._do_update, current_step, message_key, param_name)
        except Exception:
            # Dialog may have been destroyed
            pass
            
    def _do_update(self, current_step: int, message_key: str, param_name: str = ""):
        """Perform the actual update on main thread."""
        try:
            if self.is_closed or not self.dialog:
                return
                
            # Update current step
            self.current_step = current_step
            
            # Calculate progress percentage
            progress_percentage = min(100, (current_step / self.total_steps) * 100)
            
            # Update status message
            status_text = self._get_translated_text(message_key, f"Step {current_step}")
            if param_name:
                # Format message with parameter name
                status_text = f"{status_text}: {param_name}"
                
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.config(text=status_text)
            
            # Update progress bar
            if hasattr(self, 'progress_var') and self.progress_var:
                self.progress_var.set(progress_percentage)
            
            # Update percentage label
            percentage_text = f"{int(progress_percentage)}%"
            if hasattr(self, 'percentage_label') and self.percentage_label:
                self.percentage_label.config(text=percentage_text)
                
        except Exception as e:
            print(f"Progress update error: {e}")
            
    def set_cancel_callback(self, callback: Callable):
        """Set callback function for cancel operation."""
        self.cancel_callback = callback
        
    def _on_cancel(self):
        """Handle cancel button click."""
        if self.cancel_callback and not self.is_cancelled:
            self.is_cancelled = True
            try:
                self.cancel_callback()
            except Exception as e:
                print(f"Cancel callback error: {e}")
        self.close_dialog()
        
    def _on_close(self):
        """Handle window close event."""
        self._on_cancel()
        
    def show_success(self, message_key: str = "operation_completed"):
        """Show success state with localized message."""
        if self.is_closed or not self.dialog:
            return
            
        try:
            if self.dialog.winfo_exists():
                self.dialog.after_idle(self._do_show_success, message_key)
        except Exception:
            pass
            
    def _do_show_success(self, message_key: str):
        """Show success state on main thread."""
        try:
            if hasattr(self, 'status_label') and self.status_label:
                success_text = self._get_translated_text(message_key, "Operation completed successfully!")
                self.status_label.config(text=success_text)
                
            if hasattr(self, 'progress_var') and self.progress_var:
                self.progress_var.set(100)
                
            if hasattr(self, 'percentage_label') and self.percentage_label:
                self.percentage_label.config(text="100%")
                
            if hasattr(self, 'cancel_button') and self.cancel_button:
                close_text = self._get_translated_text("close", "Close")
                self.cancel_button.config(text=close_text, bg='#00aa00')
        except Exception:
            pass
            
    def show_error(self, error_message: str, message_key: str = "operation_failed"):
        """Show error state with localized message."""
        if self.is_closed or not self.dialog:
            return
            
        try:
            if self.dialog.winfo_exists():
                self.dialog.after_idle(self._do_show_error, error_message, message_key)
        except Exception:
            pass
            
    def _do_show_error(self, error_message: str, message_key: str):
        """Show error state on main thread."""
        try:
            if hasattr(self, 'status_label') and self.status_label:
                error_prefix = self._get_translated_text(message_key, "Operation failed")
                error_text = f"{error_prefix}: {error_message}"
                self.status_label.config(text=error_text)
                
            if hasattr(self, 'cancel_button') and self.cancel_button:
                close_text = self._get_translated_text("close", "Close")
                self.cancel_button.config(text=close_text, bg='#cc0000')
        except Exception:
            pass
            
    def show(self):
        """Show dialog."""
        try:
            if self.dialog and not self.is_closed:
                self.dialog.deiconify()
                self.dialog.lift()
                self.dialog.focus()
        except Exception:
            pass
            
    def hide(self):
        """Hide dialog."""
        try:
            if self.dialog and not self.is_closed:
                self.dialog.withdraw()
        except Exception:
            pass
            
    def close_dialog(self):
        """Close dialog safely."""
        if self.is_closed:
            return
            
        self.is_closed = True
        
        try:
            if self.dialog:
                self.dialog.grab_release()
                self.dialog.destroy()
                self.dialog = None
        except Exception:
            pass
            
        # Clear references to prevent further access
        self.status_label = None
        self.progress_bar = None
        self.progress_var = None
        self.percentage_label = None
        self.cancel_button = None


# Utility function for easy dialog creation
def create_progress_dialog(parent, title_key: str, total_steps: int, i18n_service=None) -> SimpleProgressDialog:
    """
    Factory function to create a simple progress dialog.
    
    Args:
        parent: Parent window
        title_key: Translation key for dialog title
        total_steps: Total number of steps
        i18n_service: Translation service instance
        
    Returns:
        SimpleProgressDialog instance
    """
    return SimpleProgressDialog(parent, title_key, total_steps, i18n_service)