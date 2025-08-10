"""
Operation Confirmation Service - Provides confirmation dialogs and success feedback.

This module provides a centralized service for handling confirmation dialogs for
destructive operations, success notifications, and progress indicators for
long-running operations in the LT32Pro Device Configurator application.
"""

import tkinter as tk
from tkinter import messagebox
import threading
import time
from typing import Callable, Optional, Dict, Any, List
import customtkinter as ctk

class OperationConfirmationService:
    """Centralized service for operation confirmations and success feedback."""
    
    # Operation types that require confirmation
    OPERATION_FACTORY_RESET = "factory_reset"
    OPERATION_DEVICE_RESET = "device_reset"
    OPERATION_FORMAT_DEVICE = "format_device"
    OPERATION_CLEAR_MEMORY = "clear_memory"
    OPERATION_RESTORE_DEFAULTS = "restore_defaults"
    OPERATION_BULK_SEND = "bulk_send"
    
    # Progress indicator types
    PROGRESS_TYPE_DETERMINATE = "determinate"  # Known total steps
    PROGRESS_TYPE_INDETERMINATE = "indeterminate"  # Unknown total steps
    
    def __init__(self, app_instance):
        """
        Initialize the operation confirmation service.
        
        Args:
            app_instance: Reference to the main application instance
        """
        self.app = app_instance
        self.progress_dialogs = {}  # Store active progress dialogs
        self.progress_threads = {}  # Store progress update threads
        self.stop_progress = {}  # Flags to stop progress threads
        
        # Define confirmation messages for different operation types
        self.confirmation_messages = {
            self.OPERATION_FACTORY_RESET: {
                "title": "Confirm Factory Reset",
                "message": "WARNING: This will reset the device to factory settings.\n\nAll device configurations will be lost. This action cannot be undone.\n\nDo you want to continue?",
                "detail": "The device will restart after the factory reset."
            },
            self.OPERATION_DEVICE_RESET: {
                "title": "Confirm Device Reset",
                "message": "This will restart the device.\n\nThe current connection will be lost and you will need to reconnect after the device restarts.\n\nDo you want to continue?",
                "detail": "Device settings will be preserved."
            },
            self.OPERATION_FORMAT_DEVICE: {
                "title": "Confirm Device Format",
                "message": "WARNING: This will format the device memory.\n\nAll stored data will be permanently deleted. This action cannot be undone.\n\nDo you want to continue?",
                "detail": "Device configuration settings will be preserved."
            },
            self.OPERATION_CLEAR_MEMORY: {
                "title": "Confirm Clear Memory",
                "message": "This will clear all stored messages in the device memory.\n\nAll unsent data will be deleted. This action cannot be undone.\n\nDo you want to continue?",
                "detail": "Device configuration settings will be preserved."
            },
            self.OPERATION_RESTORE_DEFAULTS: {
                "title": "Confirm Restore Defaults",
                "message": "This will restore all application settings to default values.\n\nCurrent UI values will be reset. This will not affect the device settings.\n\nDo you want to continue?",
                "detail": "You will need to send the commands to update the device."
            },
            self.OPERATION_BULK_SEND: {
                "title": "Confirm Bulk Send",
                "message": "This will send all current parameter values to the device.\n\nThis will overwrite all device settings with the current UI values.\n\nDo you want to continue?",
                "detail": "The device may restart after receiving some commands."
            }
        }
    
    def confirm_operation(self, operation_type: str, custom_message: Optional[str] = None) -> bool:
        """
        Show a confirmation dialog for a potentially destructive operation.
        
        Args:
            operation_type: The type of operation (from class constants)
            custom_message: Optional custom message to override the default
            
        Returns:
            True if the user confirmed, False otherwise
        """
        # Get the confirmation message for this operation type
        if operation_type in self.confirmation_messages:
            title = self.confirmation_messages[operation_type]["title"]
            message = custom_message or self.confirmation_messages[operation_type]["message"]
            detail = self.confirmation_messages[operation_type]["detail"]
            
            # Format the full message with detail
            full_message = f"{message}\n\n{detail}"
            
            # Show the confirmation dialog
            return messagebox.askyesno(title, full_message, icon=messagebox.WARNING)
        else:
            # For unknown operation types, use a generic confirmation
            return messagebox.askyesno(
                "Confirm Operation", 
                "Are you sure you want to perform this operation?",
                icon=messagebox.QUESTION
            )
    
    def show_success_notification(self, message: str) -> None:
        """
        Show a success notification in the log.
        
        Args:
            message: The success message to display
        """
        if hasattr(self.app, 'log_frame'):
            self.app.log_frame.log_message(f"INFO: ✓ {message}\n")
            
            # Flash the log area to draw attention for important success messages
            if hasattr(self.app.log_frame, '_flash_log_for_attention'):
                self.app.log_frame._flash_log_for_attention(success=True)
    
    def create_progress_dialog(self, title: str, operation_name: str, 
                              progress_type: str = PROGRESS_TYPE_DETERMINATE,
                              total_steps: int = 100,
                              cancelable: bool = True) -> str:
        """
        Create a progress dialog for a long-running operation.
        
        Args:
            title: The dialog title
            operation_name: Name of the operation
            progress_type: Type of progress indicator (determinate/indeterminate)
            total_steps: Total number of steps for determinate progress
            cancelable: Whether the operation can be canceled
            
        Returns:
            Dialog ID for updating the progress
        """
        # Generate a unique ID for this dialog
        dialog_id = f"progress_{len(self.progress_dialogs) + 1}_{int(time.time())}"
        
        # Create the dialog window
        dialog = ctk.CTkToplevel(self.app)
        dialog.title(title)
        dialog.geometry("400x150")
        dialog.resizable(False, False)
        dialog.transient(self.app)  # Make it float on top of the main window
        dialog.grab_set()  # Make it modal
        
        # Center the dialog on the main window
        if hasattr(self.app, 'winfo_x') and hasattr(self.app, 'winfo_y'):
            x = self.app.winfo_x() + (self.app.winfo_width() // 2) - 200
            y = self.app.winfo_y() + (self.app.winfo_height() // 2) - 75
            dialog.geometry(f"+{x}+{y}")
        
        # Create dialog content
        dialog.grid_columnconfigure(0, weight=1)
        
        # Operation name label
        operation_label = ctk.CTkLabel(dialog, text=operation_name, font=ctk.CTkFont(size=14, weight="bold"))
        operation_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Progress bar
        progress_bar = ctk.CTkProgressBar(dialog)
        progress_bar.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        if progress_type == self.PROGRESS_TYPE_INDETERMINATE:
            # For indeterminate progress, we'll animate the progress bar
            progress_bar.set(0)
            self.stop_progress[dialog_id] = False
            self._start_indeterminate_animation(dialog_id, progress_bar)
        else:
            # For determinate progress, initialize to 0
            progress_bar.set(0)
        
        # Status label
        status_label = ctk.CTkLabel(dialog, text="Starting operation...")
        status_label.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="w")
        
        # Cancel button (if cancelable)
        if cancelable:
            cancel_button = ctk.CTkButton(
                dialog, 
                text="Cancel", 
                command=lambda: self._cancel_operation(dialog_id)
            )
            cancel_button.grid(row=3, column=0, padx=20, pady=(0, 20))
        
        # Store dialog components
        self.progress_dialogs[dialog_id] = {
            "dialog": dialog,
            "progress_bar": progress_bar,
            "status_label": status_label,
            "operation_name": operation_name,
            "progress_type": progress_type,
            "total_steps": total_steps,
            "current_step": 0,
            "cancelable": cancelable,
            "cancel_callback": None
        }
        
        return dialog_id
    
    def update_progress(self, dialog_id: str, step: int = None, 
                       status_text: Optional[str] = None,
                       increment: int = None) -> None:
        """
        Update the progress of an operation.
        
        Args:
            dialog_id: The dialog ID returned from create_progress_dialog
            step: Current step (for determinate progress)
            status_text: Optional status text to display
            increment: Optional increment to add to current step
        """
        if dialog_id not in self.progress_dialogs:
            return

        dialog_info = self.progress_dialogs[dialog_id]
        dialog = dialog_info["dialog"]
        # Check if dialog and widgets still exist
        if not dialog.winfo_exists() or not dialog_info["progress_bar"].winfo_exists() or not dialog_info["status_label"].winfo_exists():
            return

        # Update step if provided
        if step is not None:
            dialog_info["current_step"] = min(step, dialog_info["total_steps"])
        elif increment is not None:
            dialog_info["current_step"] = min(
                dialog_info["current_step"] + increment,
                dialog_info["total_steps"]
            )

        # Calculate progress value (0.0 to 1.0)
        if dialog_info["progress_type"] == self.PROGRESS_TYPE_DETERMINATE:
            progress_value = dialog_info["current_step"] / dialog_info["total_steps"]
            if dialog_info["progress_bar"].winfo_exists():
                dialog_info["progress_bar"].set(progress_value)

        # Update status text if provided
        if status_text and dialog_info["status_label"].winfo_exists():
            dialog_info["status_label"].configure(text=status_text)
    
    def complete_progress(self, dialog_id: str, success: bool = True, 
                         completion_message: Optional[str] = None) -> None:
        """
        Complete a progress operation and close the dialog.
        
        Args:
            dialog_id: The dialog ID returned from create_progress_dialog
            success: Whether the operation completed successfully
            completion_message: Optional completion message
        """
        if dialog_id not in self.progress_dialogs:
            return

        dialog_info = self.progress_dialogs[dialog_id]
        dialog = dialog_info["dialog"]
        # Check if dialog and widgets still exist
        if not dialog.winfo_exists() or not dialog_info["progress_bar"].winfo_exists() or not dialog_info["status_label"].winfo_exists():
            return

        # Stop any animation
        if dialog_id in self.stop_progress:
            self.stop_progress[dialog_id] = True

        # Set progress to 100% if successful
        if success and dialog_info["progress_type"] == self.PROGRESS_TYPE_DETERMINATE:
            if dialog_info["progress_bar"].winfo_exists():
                dialog_info["progress_bar"].set(1.0)

        # Update status text
        if completion_message and dialog_info["status_label"].winfo_exists():
            dialog_info["status_label"].configure(text=completion_message)
        elif success and dialog_info["status_label"].winfo_exists():
            dialog_info["status_label"].configure(text="Operation completed successfully.")
        elif dialog_info["status_label"].winfo_exists():
            dialog_info["status_label"].configure(text="Operation failed or was canceled.")

        # Show completion message in log
        operation_name = dialog_info["operation_name"]
        if success:
            self.show_success_notification(f"{operation_name} completed successfully")
        else:
            if hasattr(self.app, 'log_frame'):
                self.app.log_frame.log_message(f"WARNING: {operation_name} was not completed\n")

        # Close the dialog after a short delay
        self.app.after(1500, lambda: self._close_progress_dialog(dialog_id))
    
    def set_cancel_callback(self, dialog_id: str, callback: Callable) -> None:
        """
        Set a callback function to be called when the operation is canceled.
        
        Args:
            dialog_id: The dialog ID returned from create_progress_dialog
            callback: The callback function
        """
        if dialog_id in self.progress_dialogs:
            self.progress_dialogs[dialog_id]["cancel_callback"] = callback
    
    def _cancel_operation(self, dialog_id: str) -> None:
        """
        Cancel an operation and close its progress dialog.
        
        Args:
            dialog_id: The dialog ID to cancel
        """
        if dialog_id not in self.progress_dialogs:
            return
            
        dialog_info = self.progress_dialogs[dialog_id]
        
        # Call the cancel callback if provided
        if dialog_info["cancel_callback"]:
            dialog_info["cancel_callback"]()
        
        # Stop any animation
        if dialog_id in self.stop_progress:
            self.stop_progress[dialog_id] = True
        
        # Update status text
        dialog_info["status_label"].configure(text="Operation canceled.")
        
        # Log the cancellation
        operation_name = dialog_info["operation_name"]
        if hasattr(self.app, 'log_frame'):
            self.app.log_frame.log_message(f"INFO: {operation_name} was canceled by user\n")
        
        # Close the dialog after a short delay
        self.app.after(1000, lambda: self._close_progress_dialog(dialog_id))
    
    def _close_progress_dialog(self, dialog_id: str) -> None:
        """
        Close a progress dialog and clean up resources.
        
        Args:
            dialog_id: The dialog ID to close
        """
        if dialog_id not in self.progress_dialogs:
            return
            
        # Get the dialog window
        dialog = self.progress_dialogs[dialog_id]["dialog"]
        
        # Release grab and destroy the dialog
        dialog.grab_release()
        dialog.destroy()
        
        # Clean up resources
        if dialog_id in self.progress_threads:
            self.progress_threads.pop(dialog_id, None)
        if dialog_id in self.stop_progress:
            self.stop_progress.pop(dialog_id, None)
        
        # Remove from progress dialogs
        self.progress_dialogs.pop(dialog_id, None)
    
    def _start_indeterminate_animation(self, dialog_id: str, progress_bar) -> None:
        """
        Start an animation for indeterminate progress.
        
        Args:
            dialog_id: The dialog ID
            progress_bar: The progress bar widget
        """
        # Create a thread to animate the progress bar
        def animate_progress():
            direction = 1  # 1 for increasing, -1 for decreasing
            value = 0.0
            
            while not self.stop_progress.get(dialog_id, True):
                # Update progress value
                value += 0.02 * direction
                
                # Reverse direction at the ends
                if value >= 1.0:
                    value = 1.0
                    direction = -1
                elif value <= 0.0:
                    value = 0.0
                    direction = 1
                
                # Update the progress bar
                self.app.after(0, lambda v=value: progress_bar.set(v))
                
                # Sleep briefly
                time.sleep(0.05)
        
        # Start the animation thread
        thread = threading.Thread(target=animate_progress, daemon=True)
        self.progress_threads[dialog_id] = thread
        thread.start()
    
    def show_operation_progress_in_log(self, operation: str, progress: int, total: int) -> None:
        """
        Show operation progress in the log.
        
        Args:
            operation: The operation name
            progress: Current progress value
            total: Total progress value
        """
        if hasattr(self.app, 'error_handler'):
            self.app.error_handler.show_operation_progress(operation, progress, total)
        elif hasattr(self.app, 'log_frame'):
            percentage = int((progress / total) * 100)
            bar_length = 20
            filled_length = int(bar_length * progress / total)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            
            self.app.log_frame.log_message(
                f"INFO: {operation}: {progress}/{total} ({percentage}%) [{bar}]\n"
            )