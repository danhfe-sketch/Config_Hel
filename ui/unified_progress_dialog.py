"""
Unified Progress Dialog - Single progress dialog for all profile operations.

This module provides a unified progress dialog that replaces multiple progress dialog types
with translation support, clean minimal interface, and non-modal operation support.
"""

import customtkinter as ctk
import threading
import time
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class UnifiedProgressInfo:
    """Unified progress information for all profile operations."""
    operation_type: str  # 'load_from_device', 'load_to_device', 'load_to_ui', 'save_from_ui'
    current_step: int    # Current step number (1-based)
    total_steps: int     # Total number of steps
    progress_percentage: float  # Overall progress (0.0 to 1.0)
    status_message: str  # Current status message
    current_parameter: str = ""  # Current parameter being processed
    parameter_count: int = 0  # Current parameter index
    total_parameters: int = 0  # Total parameters to process
    can_cancel: bool = True  # Whether operation can be cancelled
    is_complete: bool = False  # Whether operation is complete
    is_cancelled: bool = False  # Whether operation was cancelled
    has_error: bool = False  # Whether operation has error
    error_message: str = ""  # Error message if any


class UnifiedProgressDialog:
    """Unified progress dialog for all profile operations with translation support."""
    
    def __init__(self, parent, operation_type: str, i18n_service=None):
        """
        Initialize the unified progress dialog.
        
        Args:
            parent: Parent window
            operation_type: Type of operation ('load_from_device', 'load_to_device', 'load_to_ui', 'save_from_ui')
            i18n_service: Translation service instance
        """
        self.parent = parent
        self.operation_type = operation_type
        self.i18n = i18n_service
        self.is_cancelled = False
        self.is_closed = False
        self.completion_called = False  # Flag to prevent multiple completion callbacks
        self.cancel_callback = None
        self.completion_callback = None
        
        # Operation timeout handling
        self.operation_timeout = 300.0  # 5 minutes default
        self.operation_start_time = None
        self.timeout_after_id = None
        
        # Create the dialog
        self._create_dialog()
        
    def _create_dialog(self):
        """Create the unified progress dialog with clean, minimal interface."""
        try:
            # Create toplevel window
            self.dialog = ctk.CTkToplevel(self.parent)
            
            # Set title based on operation type
            title = self._get_operation_title()
            self.dialog.title(title)
            
            # Set dialog properties
            self.dialog.geometry("480x320")
            self.dialog.resizable(False, False)
            self.dialog.transient(self.parent)
            self.dialog.grab_set()
            
            # Apply consistent theming
            self._apply_theming()
            
            # Center the dialog
            self._center_dialog()
            
            # Create UI elements
            self._create_ui()
            
            # Handle window close event
            self.dialog.protocol("WM_DELETE_WINDOW", self._on_window_close)
            
        except Exception as e:
            print(f"Error creating unified progress dialog: {e}")
            self.dialog = None
            
    def _get_operation_title(self) -> str:
        """Get localized title based on operation type."""
        title_keys = {
            'load_from_device': 'load_from_device',
            'load_to_device': 'load_profile_to_device', 
            'load_to_ui': 'load_profile',
            'save_from_ui': 'save_profile'
        }
        
        title_defaults = {
            'load_from_device': 'Load Profile from Device',
            'load_to_device': 'Load Profile to Device',
            'load_to_ui': 'Load Profile to UI',
            'save_from_ui': 'Save Profile from UI'
        }
        
        key = title_keys.get(self.operation_type, 'profile_operation')
        default = title_defaults.get(self.operation_type, 'Profile Operation')
        
        return self._get_translated_text(key, default)
        
    def _get_translated_text(self, key: str, default: str) -> str:
        """Get translated text using i18n service or return default."""
        if self.i18n:
            return self.i18n.get(key, default)
        return default
        
    def _apply_theming(self):
        """Apply consistent theming with the main application."""
        # Get theme from parent if available
        if hasattr(self.parent, 'theme_service'):
            try:
                current_theme = self.parent.theme_service.get_current_theme()
                ctk.set_appearance_mode(current_theme)
            except Exception:
                ctk.set_appearance_mode("dark")
        else:
            ctk.set_appearance_mode("dark")
            
        # Set consistent color theme
        ctk.set_default_color_theme("blue")
        
    def _center_dialog(self):
        """Center the dialog on the parent window."""
        try:
            # Update parent to get accurate dimensions
            self.parent.update_idletasks()
            
            # Get parent position and size
            parent_x = self.parent.winfo_x()
            parent_y = self.parent.winfo_y()
            parent_width = self.parent.winfo_width()
            parent_height = self.parent.winfo_height()
            
            # Calculate center position
            dialog_width = 480
            dialog_height = 320
            x = parent_x + (parent_width - dialog_width) // 2
            y = parent_y + (parent_height - dialog_height) // 2
            
            # Ensure dialog stays within screen bounds
            screen_width = self.dialog.winfo_screenwidth()
            screen_height = self.dialog.winfo_screenheight()
            
            x = max(0, min(x, screen_width - dialog_width))
            y = max(0, min(y, screen_height - dialog_height))
            
            self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
            
        except Exception:
            # Fallback positioning
            self.dialog.geometry("480x320+400+200")
            
    def _create_ui(self):
        """Create the clean, minimal UI elements."""
        # Configure main dialog grid
        self.dialog.grid_columnconfigure(0, weight=1)
        self.dialog.grid_rowconfigure(0, weight=1)
        
        # Create main frame
        main_frame = ctk.CTkFrame(self.dialog, corner_radius=10)
        main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Header section
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 15), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)
        
        # Operation icon
        icon_text = self._get_operation_icon()
        icon_label = ctk.CTkLabel(
            header_frame,
            text=icon_text,
            width=40,
            height=40,
            fg_color=("#1f538d", "#1f538d"),
            corner_radius=20,
            text_color="white",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        icon_label.grid(row=0, column=0, padx=(0, 15), pady=0, sticky="w")
        
        # Operation title
        title_text = self._get_operation_title()
        self.title_label = ctk.CTkLabel(
            header_frame,
            text=title_text,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("gray10", "gray90")
        )
        self.title_label.grid(row=0, column=1, padx=0, pady=0, sticky="w")
        
        # Status message
        self.status_label = ctk.CTkLabel(
            main_frame,
            text=self._get_translated_text("initializing", "Initializing..."),
            font=ctk.CTkFont(size=13),
            text_color=("gray20", "gray80"),
            wraplength=420,
            justify="left"
        )
        self.status_label.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="w")
        
        # Progress section
        progress_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        progress_frame.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="ew")
        progress_frame.grid_columnconfigure(0, weight=1)
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            height=16,
            corner_radius=8,
            progress_color=("#1f538d", "#1f538d")
        )
        self.progress_bar.grid(row=0, column=0, pady=(0, 8), sticky="ew")
        self.progress_bar.set(0)
        
        # Progress details frame
        progress_details = ctk.CTkFrame(progress_frame, fg_color="transparent")
        progress_details.grid(row=1, column=0, sticky="ew")
        progress_details.grid_columnconfigure(0, weight=1)
        progress_details.grid_columnconfigure(1, weight=0)
        
        # Progress text (step and parameter info)
        self.progress_text = ctk.CTkLabel(
            progress_details,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=("gray30", "gray70")
        )
        self.progress_text.grid(row=0, column=0, sticky="w")
        
        # Percentage display
        self.percentage_label = ctk.CTkLabel(
            progress_details,
            text="0%",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("#1f538d", "#1f538d")
        )
        self.percentage_label.grid(row=0, column=1, sticky="e")
        
        # Current parameter display
        self.parameter_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60"),
            wraplength=420,
            justify="left"
        )
        self.parameter_label.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="w")
        
        # Button frame
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        
        # Cancel button
        cancel_text = self._get_translated_text("cancel", "Cancel")
        self.cancel_button = ctk.CTkButton(
            button_frame,
            text=cancel_text,
            command=self._on_cancel,
            width=100,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40")
        )
        self.cancel_button.grid(row=0, column=0, pady=0, sticky="e")
        
        # Close button (initially hidden)
        close_text = self._get_translated_text("close", "Close")
        self.close_button = ctk.CTkButton(
            button_frame,
            text=close_text,
            command=self._on_close,
            width=100,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=("#1f538d", "#1f538d"),
            hover_color=("#144870", "#144870")
        )
        # Don't grid the close button initially
        
    def _get_operation_icon(self) -> str:
        """Get icon for the operation type."""
        icons = {
            'load_from_device': '📱',
            'load_to_device': '📤',
            'load_to_ui': '📂',
            'save_from_ui': '💾'
        }
        return icons.get(self.operation_type, '⚙')
        
    def update_progress(self, progress_info: UnifiedProgressInfo):
        """
        Update the progress dialog with new information - thread safe.
        
        Args:
            progress_info: Progress information
        """
        if self.is_closed or not self.dialog:
            return
            
        # Schedule update on main thread
        try:
            if self.dialog.winfo_exists():
                self.dialog.after_idle(self._do_update, progress_info)
        except Exception:
            # Dialog may have been destroyed
            pass
            
    def update_translations(self):
        """Update all translatable text in the dialog."""
        if self.is_closed or not self.dialog:
            return
            
        try:
            if self.dialog.winfo_exists():
                self.dialog.after_idle(self._do_update_translations)
        except Exception:
            pass
            
    def _do_update_translations(self):
        """Update translations on main thread."""
        try:
            if self.is_closed or not self.dialog:
                return
                
            # Update dialog title
            title = self._get_operation_title()
            self.dialog.title(title)
            
            # Update title label
            if hasattr(self, 'title_label') and self.title_label:
                self.title_label.configure(text=title)
                
            # Update button text
            if hasattr(self, 'cancel_button') and self.cancel_button:
                cancel_text = self._get_translated_text("cancel", "Cancel")
                self.cancel_button.configure(text=cancel_text)
                
            if hasattr(self, 'close_button') and self.close_button:
                close_text = self._get_translated_text("close", "Close")
                self.close_button.configure(text=close_text)
                
            # Update status label if it has translatable text
            if hasattr(self, 'status_label') and self.status_label:
                current_text = self.status_label.cget("text")
                
                # Check for various translatable status messages
                translatable_patterns = {
                    # Initializing messages
                    ("Initializing...", "Inicializando...", "Inicializando..."): ("initializing", "Initializing..."),
                    # Processing step messages
                    ("Processing step", "Processando passo", "Procesando paso"): ("processing_step", "Processing step"),
                    # Connection messages
                    ("Connecting to device", "Conectando ao dispositivo", "Conectando al dispositivo"): ("connecting_to_device", "Connecting to device..."),
                    # Reading messages
                    ("Reading profile file", "Lendo arquivo de perfil", "Leyendo archivo de perfil"): ("reading_profile_file", "Reading profile file..."),
                    # Finalizing messages
                    ("Finalizing operation", "Finalizando operação", "Finalizando operación"): ("finalizing_operation", "Finalizing operation..."),
                    ("Writing profile file", "Escrevendo arquivo de perfil", "Escribiendo archivo de perfil"): ("writing_profile_file", "Writing profile file..."),
                    ("Applying configuration", "Aplicando configuração", "Aplicando configuración"): ("applying_configuration", "Applying configuration..."),
                }
                
                # Check if current text matches any translatable pattern
                for patterns, (key, default) in translatable_patterns.items():
                    if any(pattern in current_text for pattern in patterns):
                        # Extract any dynamic parts (like step numbers)
                        import re
                        step_match = re.search(r'(\d+)', current_text)
                        if step_match and key == "processing_step":
                            step_num = step_match.group(1)
                            translated_text = f"{self._get_translated_text(key, default)} {step_num}..."
                        else:
                            translated_text = self._get_translated_text(key, default)
                        
                        self.status_label.configure(text=translated_text)
                        break
                    
        except Exception as e:
            print(f"Translation update error: {e}")
            
    def _do_update(self, progress_info: UnifiedProgressInfo):
        """Perform the actual update on main thread."""
        try:
            if self.is_closed or not self.dialog:
                return
                
            # Start timeout monitoring on first progress update
            if self.operation_start_time is None and progress_info.current_step > 0:
                self._start_timeout_monitoring()
                
            # Update status message
            if progress_info.status_message:
                self.status_label.configure(text=progress_info.status_message)
                
            # Update progress bar
            progress_value = max(0, min(1, progress_info.progress_percentage))
            self.progress_bar.set(progress_value)
            
            # Update percentage display
            percentage = int(progress_value * 100)
            self.percentage_label.configure(text=f"{percentage}%")
            
            # Update progress text with step and parameter info
            progress_parts = []
            if progress_info.total_steps > 0:
                step_text = self._get_translated_text("step", "Step")
                progress_parts.append(f"{step_text} {progress_info.current_step}/{progress_info.total_steps}")
                
            if progress_info.total_parameters > 0 and progress_info.parameter_count > 0:
                param_text = self._get_translated_text("parameter", "Parameter")
                progress_parts.append(f"{param_text} {progress_info.parameter_count}/{progress_info.total_parameters}")
                
            self.progress_text.configure(text=" • ".join(progress_parts))
            
            # Update current parameter display
            if progress_info.current_parameter:
                param_text = self._get_translated_text("processing_parameter", "Processing parameter")
                parameter_display = f"{param_text}: {progress_info.current_parameter}"
                self.parameter_label.configure(text=parameter_display)
            else:
                self.parameter_label.configure(text="")
                
            # Handle completion
            if progress_info.is_complete:
                self._handle_completion(progress_info)
                
            # Handle cancellation
            if progress_info.is_cancelled:
                self._handle_cancellation()
                
        except Exception as e:
            print(f"Progress update error: {e}")
            
    def _handle_completion(self, progress_info: UnifiedProgressInfo):
        """Handle operation completion."""
        # Stop timeout monitoring
        self._stop_timeout_monitoring()
        
        # Update UI for completion
        if progress_info.has_error:
            # Show error state
            error_text = self._get_translated_text("operation_failed", "Operation failed")
            if progress_info.error_message:
                error_text += f": {progress_info.error_message}"
            self.status_label.configure(text=error_text)
            
            # Change progress bar color to red
            self.progress_bar.configure(progress_color=("#cc0000", "#cc0000"))
            
        else:
            # Show success state
            success_text = self._get_translated_text("operation_completed", "Operation completed successfully")
            self.status_label.configure(text=success_text)
            
            # Change progress bar color to green
            self.progress_bar.configure(progress_color=("#00aa00", "#00aa00"))
            self.progress_bar.set(1.0)
            self.percentage_label.configure(text="100%")
            
        # Hide cancel button and show close button
        self.cancel_button.grid_remove()
        self.close_button.grid(row=0, column=0, pady=0, sticky="e")
        
        # Call completion callback if set (only once)
        if self.completion_callback and not self.completion_called:
            self.completion_called = True
            try:
                self.completion_callback(progress_info)
            except Exception as e:
                print(f"Completion callback error: {e}")
                
    def _handle_cancellation(self):
        """Handle operation cancellation."""
        # Stop timeout monitoring
        self._stop_timeout_monitoring()
        
        # Update UI for cancellation
        cancelled_text = self._get_translated_text("operation_cancelled", "Operation cancelled")
        self.status_label.configure(text=cancelled_text)
        
        # Change progress bar color to orange
        self.progress_bar.configure(progress_color=("#ff8c00", "#ff8c00"))
        
        # Hide cancel button and show close button
        self.cancel_button.grid_remove()
        self.close_button.grid(row=0, column=0, pady=0, sticky="e")
        
    def _start_timeout_monitoring(self):
        """Start monitoring for operation timeout."""
        self.operation_start_time = time.time()
        self._check_timeout()
        
    def _check_timeout(self):
        """Check if operation has timed out."""
        if self.is_closed or not self.dialog:
            return
            
        if self.operation_start_time:
            elapsed = time.time() - self.operation_start_time
            if elapsed > self.operation_timeout:
                # Operation timed out
                timeout_text = self._get_translated_text("operation_timeout", "Operation timed out")
                self.status_label.configure(text=timeout_text)
                
                # Trigger cancellation
                self._on_cancel()
                return
                
        # Schedule next timeout check
        self.timeout_after_id = self.dialog.after(5000, self._check_timeout)
        
    def _stop_timeout_monitoring(self):
        """Stop timeout monitoring."""
        if self.timeout_after_id:
            try:
                self.dialog.after_cancel(self.timeout_after_id)
            except Exception:
                pass
            self.timeout_after_id = None
            
    def set_cancel_callback(self, callback: Callable):
        """Set callback function for cancel operation."""
        self.cancel_callback = callback
        
    def set_completion_callback(self, callback: Callable):
        """Set callback function for operation completion."""
        self.completion_callback = callback
        
    def _on_cancel(self):
        """Handle cancel button click."""
        if not self.is_cancelled and self.cancel_callback:
            self.is_cancelled = True
            try:
                self.cancel_callback()
            except Exception as e:
                print(f"Cancel callback error: {e}")
        self.close_dialog()
        
    def _on_close(self):
        """Handle close button click."""
        self.close_dialog()
        
    def _on_window_close(self):
        """Handle window close event."""
        if not self.is_cancelled:
            self._on_cancel()
        else:
            self.close_dialog()
            
    def show(self):
        """Show the dialog."""
        try:
            if self.dialog and not self.is_closed:
                self.dialog.deiconify()
                self.dialog.lift()
                self.dialog.focus()
        except Exception:
            pass
            
    def hide(self):
        """Hide the dialog."""
        try:
            if self.dialog and not self.is_closed:
                self.dialog.withdraw()
        except Exception:
            pass
            
    def close_dialog(self):
        """Close the dialog safely."""
        if self.is_closed:
            return
            
        self.is_closed = True
        
        # Stop timeout monitoring
        self._stop_timeout_monitoring()
        
        try:
            if self.dialog:
                self.dialog.grab_release()
                self.dialog.destroy()
                self.dialog = None
        except Exception:
            pass
            
        # Clear references
        self.status_label = None
        self.progress_bar = None
        self.progress_text = None
        self.percentage_label = None
        self.parameter_label = None
        self.cancel_button = None
        self.close_button = None


def create_unified_progress_dialog(parent, operation_type: str, i18n_service=None) -> UnifiedProgressDialog:
    """
    Factory function to create a unified progress dialog.
    
    Args:
        parent: Parent window
        operation_type: Type of operation ('load_from_device', 'load_to_device', 'load_to_ui', 'save_from_ui')
        i18n_service: Translation service instance
        
    Returns:
        UnifiedProgressDialog instance
    """
    return UnifiedProgressDialog(parent, operation_type, i18n_service)