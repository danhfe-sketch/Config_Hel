"""
Profile Warning Confirmation Dialog - User confirmation dialog for operations with validation warnings.

This module provides a dialog for asking users whether to continue operations
when validation warnings are present, supporting comprehensive error recovery.
"""

import customtkinter as ctk
import tkinter as tk
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass


@dataclass
class WarningDialogResult:
    """Result of warning confirmation dialog."""
    continue_operation: bool
    user_choice: str  # 'continue', 'cancel', 'fix_and_retry'
    ignore_similar_warnings: bool = False


class ProfileWarningConfirmationDialog(ctk.CTkToplevel):
    """
    Dialog for confirming continuation of operations with validation warnings.
    
    Features:
    - Display detailed warning information
    - Allow user to continue, cancel, or fix issues
    - Option to ignore similar warnings in the future
    - Comprehensive warning categorization and display
    """
    
    def __init__(self, parent, title: str, message: str, warnings: List[Dict[str, Any]],
                 operation_context: Dict[str, Any] = None,
                 callback: Optional[Callable[[WarningDialogResult], None]] = None):
        """
        Initialize the warning confirmation dialog.
        
        Args:
            parent: Parent window
            title: Dialog title
            message: Main message to display
            warnings: List of warning dictionaries
            operation_context: Context information about the operation
            callback: Optional callback function for result
        """
        super().__init__(parent)
        
        self.parent = parent
        self.callback = callback
        self.warnings = warnings or []
        self.operation_context = operation_context or {}
        self.result = None
        
        # Configure dialog
        self.title(title)
        self.geometry("600x500")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()
        
        # Center the dialog
        self._center_dialog()
        
        # Create UI elements
        self._create_dialog_content(title, message)
        
        # Focus on the dialog
        self.focus()
        
        # Bind close event
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _center_dialog(self):
        """Center the dialog on the parent window."""
        self.update_idletasks()
        
        # Get parent window position and size
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # Calculate center position
        dialog_width = 600
        dialog_height = 500
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        self.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

    def _create_dialog_content(self, title: str, message: str):
        """Create the dialog content."""
        # Main container
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title and message
        title_label = ctk.CTkLabel(
            main_frame,
            text=title,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(0, 10))
        
        message_label = ctk.CTkLabel(
            main_frame,
            text=message,
            font=ctk.CTkFont(size=12),
            wraplength=550
        )
        message_label.pack(pady=(0, 15))
        
        # Warning details section
        self._create_warning_details_section(main_frame)
        
        # Options section
        self._create_options_section(main_frame)
        
        # Buttons section
        self._create_buttons_section(main_frame)

    def _create_warning_details_section(self, parent):
        """Create the warning details section."""
        # Warning details frame
        details_frame = ctk.CTkFrame(parent)
        details_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        # Details label
        details_label = ctk.CTkLabel(
            details_frame,
            text=f"Warning Details ({len(self.warnings)} warnings found):",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        details_label.pack(anchor="w", padx=15, pady=(15, 5))
        
        # Scrollable text widget for warnings
        self.warnings_text = ctk.CTkTextbox(
            details_frame,
            height=200,
            font=ctk.CTkFont(size=10)
        )
        self.warnings_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Populate warnings
        self._populate_warning_details()

    def _populate_warning_details(self):
        """Populate the warning details text widget."""
        self.warnings_text.delete("1.0", "end")
        
        if not self.warnings:
            self.warnings_text.insert("1.0", "No warnings to display.")
            return
        
        # Group warnings by category
        warning_categories = {}
        for warning in self.warnings:
            category = warning.get('category', 'General')
            if category not in warning_categories:
                warning_categories[category] = []
            warning_categories[category].append(warning)
        
        # Display warnings by category
        for category, category_warnings in warning_categories.items():
            self.warnings_text.insert("end", f"▼ {category} ({len(category_warnings)} warnings)\n")
            
            for i, warning in enumerate(category_warnings, 1):
                parameter = warning.get('parameter', 'Unknown')
                message = warning.get('message', 'No message')
                suggestion = warning.get('suggestion', '')
                
                self.warnings_text.insert("end", f"  {i}. {parameter}: {message}\n")
                
                if suggestion:
                    self.warnings_text.insert("end", f"     → Suggestion: {suggestion}\n")
                
                self.warnings_text.insert("end", "\n")
        
        # Add operation context if available
        if self.operation_context:
            self.warnings_text.insert("end", "\n" + "="*50 + "\n")
            self.warnings_text.insert("end", "Operation Context:\n")
            
            for key, value in self.operation_context.items():
                if key not in ['successful_parameters', 'failed_parameters', 'warnings']:
                    self.warnings_text.insert("end", f"  {key.replace('_', ' ').title()}: {value}\n")

    def _create_options_section(self, parent):
        """Create the options section."""
        options_frame = ctk.CTkFrame(parent)
        options_frame.pack(fill="x", pady=(0, 15))
        
        options_label = ctk.CTkLabel(
            options_frame,
            text="Options:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        options_label.pack(anchor="w", padx=15, pady=(15, 5))
        
        # Ignore similar warnings checkbox
        self.ignore_similar_var = ctk.BooleanVar()
        self.ignore_similar_checkbox = ctk.CTkCheckBox(
            options_frame,
            text="Don't show similar warnings for this session",
            variable=self.ignore_similar_var
        )
        self.ignore_similar_checkbox.pack(anchor="w", padx=15, pady=(0, 15))

    def _create_buttons_section(self, parent):
        """Create the buttons section."""
        buttons_frame = ctk.CTkFrame(parent, fg_color="transparent")
        buttons_frame.pack(fill="x")
        
        # Button container for centering
        button_container = ctk.CTkFrame(buttons_frame, fg_color="transparent")
        button_container.pack(expand=True)
        
        # Continue button
        self.continue_button = ctk.CTkButton(
            button_container,
            text="Continue with Warnings",
            command=self._on_continue,
            width=150,
            fg_color="#28a745",
            hover_color="#218838"
        )
        self.continue_button.pack(side="left", padx=5)
        
        # Cancel button
        self.cancel_button = ctk.CTkButton(
            button_container,
            text="Cancel Operation",
            command=self._on_cancel,
            width=150,
            fg_color="#dc3545",
            hover_color="#c82333"
        )
        self.cancel_button.pack(side="left", padx=5)
        
        # Fix and retry button (if applicable)
        if self._can_fix_warnings():
            self.fix_button = ctk.CTkButton(
                button_container,
                text="Fix and Retry",
                command=self._on_fix_and_retry,
                width=150,
                fg_color="#ffc107",
                hover_color="#e0a800",
                text_color="#000000"
            )
            self.fix_button.pack(side="left", padx=5)

    def _can_fix_warnings(self) -> bool:
        """Check if warnings can be automatically fixed."""
        # Check if any warnings have suggestions that can be auto-applied
        for warning in self.warnings:
            if warning.get('suggestion') and warning.get('auto_fixable', False):
                return True
        return False

    def _on_continue(self):
        """Handle continue button click."""
        self.result = WarningDialogResult(
            continue_operation=True,
            user_choice='continue',
            ignore_similar_warnings=self.ignore_similar_var.get()
        )
        self._close_dialog()

    def _on_cancel(self):
        """Handle cancel button click."""
        self.result = WarningDialogResult(
            continue_operation=False,
            user_choice='cancel',
            ignore_similar_warnings=False
        )
        self._close_dialog()

    def _on_fix_and_retry(self):
        """Handle fix and retry button click."""
        self.result = WarningDialogResult(
            continue_operation=False,
            user_choice='fix_and_retry',
            ignore_similar_warnings=self.ignore_similar_var.get()
        )
        self._close_dialog()

    def _close_dialog(self):
        """Close the dialog and call callback if provided."""
        if self.callback and self.result:
            self.callback(self.result)
        
        self.grab_release()
        self.destroy()

    def get_result(self) -> Optional[WarningDialogResult]:
        """Get the dialog result (for synchronous usage)."""
        return self.result


def show_warning_confirmation_dialog(parent, title: str, message: str, 
                                   warnings: List[Dict[str, Any]],
                                   operation_context: Dict[str, Any] = None) -> WarningDialogResult:
    """
    Show warning confirmation dialog and return result.
    
    Args:
        parent: Parent window
        title: Dialog title
        message: Main message
        warnings: List of warning dictionaries
        operation_context: Operation context information
        
    Returns:
        WarningDialogResult with user's choice
    """
    result = [None]
    
    def callback(dialog_result):
        result[0] = dialog_result
    
    dialog = ProfileWarningConfirmationDialog(
        parent, title, message, warnings, operation_context, callback
    )
    
    # Wait for dialog to close
    parent.wait_window(dialog)
    
    return result[0] or WarningDialogResult(
        continue_operation=False,
        user_choice='cancel'
    )


def show_warning_confirmation_dialog_async(parent, title: str, message: str,
                                         warnings: List[Dict[str, Any]],
                                         operation_context: Dict[str, Any] = None,
                                         callback: Optional[Callable[[WarningDialogResult], None]] = None):
    """
    Show warning confirmation dialog asynchronously.
    
    Args:
        parent: Parent window
        title: Dialog title
        message: Main message
        warnings: List of warning dictionaries
        operation_context: Operation context information
        callback: Callback function for result
    """
    dialog = ProfileWarningConfirmationDialog(
        parent, title, message, warnings, operation_context, callback
    )
    
    return dialog