"""
Profile Validation Progress Dialog - Enhanced progress dialog for profile validation operations.

This module provides specialized progress dialogs for profile validation including:
1. Validation progress indicators during profile operations
2. Real-time validation status updates
3. Parameter-level validation feedback
4. Integration with existing ProfileProgressDialog
"""

import customtkinter as ctk
import threading
import time
from typing import Callable, Optional, Dict, Any, List
from dataclasses import dataclass
from services.profile_validator import ValidationResult, ValidationError, ValidationSeverity
from services.profile_data_models import ProfileData


@dataclass
class ValidationProgressInfo:
    """Information about profile validation progress."""
    operation_type: str  # 'validate_structure', 'validate_parameters', 'validate_compatibility'
    current_step: int    # Current validation step (1-4)
    total_steps: int     # Total validation steps (4)
    step_name: str       # Step name (e.g., "Validating Structure")
    current_parameter: int    # Current parameter being validated (index)
    total_parameters: int     # Total parameters to validate
    parameter_name: str       # Name of current parameter being validated
    status_message: str       # Detailed status message
    progress_percentage: float # Overall progress percentage
    
    # Validation-specific tracking
    validation_errors: List[ValidationError] = None
    validation_warnings: List[ValidationError] = None
    errors_found: int = 0
    warnings_found: int = 0
    critical_errors: int = 0
    
    # Parameter-level validation tracking
    parameters_validated: int = 0
    parameters_passed: int = 0
    parameters_failed: int = 0
    current_parameter_status: str = ""  # 'validating', 'passed', 'failed', 'warning'
    
    # Timing information
    validation_start_time: Optional[float] = None
    estimated_time_remaining: str = ""
    validation_speed: str = ""  # params/sec
    
    # Control flags
    can_cancel: bool = True
    is_completed: bool = False
    is_cancelled: bool = False
    has_errors: bool = False
    has_warnings: bool = False


class ProfileValidationProgressDialog:
    """Enhanced progress dialog specifically for profile validation operations."""
    
    def __init__(self, parent, title: str, operation_type: str):
        """
        Initialize the profile validation progress dialog.
        
        Args:
            parent: Parent window
            title: Dialog title
            operation_type: Type of validation operation
        """
        self.parent = parent
        self.operation_type = operation_type
        self.is_cancelled = False
        self.cancel_callback = None
        
        # Validation tracking
        self.validation_errors = []
        self.validation_warnings = []
        self.current_validation_result = None
        
        # Get i18n service from parent if available
        self.i18n = parent.i18n_service if hasattr(parent, 'i18n_service') else None
        
        # Get theme service from parent to ensure consistent theming
        self.theme_service = parent.theme_service if hasattr(parent, 'theme_service') else None
        
        # Create the dialog window
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("600x500")  # Larger for validation details
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Apply consistent theming
        self._apply_consistent_theming()
        
        # Center the dialog
        self._center_dialog()
        
        # Create UI elements
        self._create_ui()
        
        # Handle window close event
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_window_close)
    
    def _apply_consistent_theming(self):
        """Apply consistent theming with the main application."""
        if self.theme_service:
            current_theme = self.theme_service.get_current_theme()
            ctk.set_appearance_mode(current_theme)
        else:
            ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
    
    def _center_dialog(self):
        """Center the dialog on the parent window."""
        try:
            self.parent.update_idletasks()
            
            parent_x = self.parent.winfo_x()
            parent_y = self.parent.winfo_y()
            parent_width = self.parent.winfo_width()
            parent_height = self.parent.winfo_height()
            
            dialog_width = 600
            dialog_height = 500
            x = parent_x + (parent_width // 2) - (dialog_width // 2)
            y = parent_y + (parent_height // 2) - (dialog_height // 2)
            
            screen_width = self.dialog.winfo_screenwidth()
            screen_height = self.dialog.winfo_screenheight()
            
            x = max(0, min(x, screen_width - dialog_width))
            y = max(0, min(y, screen_height - dialog_height))
            
            self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        except Exception:
            self.dialog.geometry("600x500+400+200")
    
    def _create_ui(self):
        """Create the dialog UI elements."""
        # Configure main dialog grid
        self.dialog.grid_columnconfigure(0, weight=1)
        self.dialog.grid_rowconfigure(0, weight=1)
        
        # Create main frame
        main_frame = ctk.CTkFrame(self.dialog, corner_radius=10)
        main_frame.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Header section
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 15), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)
        
        # Validation icon
        icon_label = ctk.CTkLabel(
            header_frame,
            text="✓",  # Checkmark icon for validation
            width=36,
            height=36,
            fg_color="#1f538d",
            corner_radius=18,
            text_color="white",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        icon_label.grid(row=0, column=0, padx=(0, 15), pady=0, sticky="w")
        
        # Operation title
        operation_titles = {
            'validate_structure': 'Profile Structure Validation',
            'validate_parameters': 'Profile Parameter Validation',
            'validate_compatibility': 'Profile Compatibility Check',
            'validate_complete': 'Complete Profile Validation'
        }
        title_text = operation_titles.get(self.operation_type, 'Profile Validation')
        
        self.title_label = ctk.CTkLabel(
            header_frame, 
            text=title_text,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=("gray10", "gray90")
        )
        self.title_label.grid(row=0, column=1, padx=0, pady=0, sticky="w")
        
        # Validation summary section
        summary_frame = ctk.CTkFrame(main_frame, corner_radius=8, fg_color=("gray95", "gray15"))
        summary_frame.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="ew")
        summary_frame.grid_columnconfigure(1, weight=1)
        
        # Summary icon
        summary_icon = ctk.CTkLabel(
            summary_frame,
            text="📊",  # Chart icon for summary
            width=32,
            height=32,
            fg_color="#1f538d",
            corner_radius=16,
            text_color="white",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        summary_icon.grid(row=0, column=0, padx=15, pady=15, sticky="nw")
        
        # Validation summary content
        summary_content_frame = ctk.CTkFrame(summary_frame, fg_color="transparent")
        summary_content_frame.grid(row=0, column=1, padx=(0, 15), pady=15, sticky="ew")
        summary_content_frame.grid_columnconfigure(0, weight=1)
        
        # Summary header
        summary_header = ctk.CTkLabel(
            summary_content_frame,
            text="Validation Summary:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("gray10", "gray90")
        )
        summary_header.grid(row=0, column=0, sticky="w", pady=(0, 8))
        
        # Summary details
        self.summary_details = ctk.CTkLabel(
            summary_content_frame,
            text="Parameters: 0/0 validated\nErrors: 0 • Warnings: 0 • Passed: 0",
            font=ctk.CTkFont(size=12),
            justify="left",
            text_color=("gray20", "gray80")
        )
        self.summary_details.grid(row=1, column=0, sticky="w")
        
        # Validation steps indicator
        steps_frame = ctk.CTkFrame(main_frame, corner_radius=8, fg_color=("gray95", "gray15"))
        steps_frame.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="ew")
        
        # Create validation step indicators
        self.step_indicators = []
        step_names = ["Structure", "Parameters", "Compatibility", "Summary"]
        
        for i, name in enumerate(step_names):
            step_container = ctk.CTkFrame(steps_frame, fg_color="transparent")
            step_container.grid(row=0, column=i, padx=8, pady=12, sticky="ew")
            steps_frame.grid_columnconfigure(i, weight=1)
            
            # Step circle
            step_circle = ctk.CTkLabel(
                step_container,
                text=str(i+1),
                width=28,
                height=28,
                fg_color=("gray60", "gray40"),
                corner_radius=14,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="white"
            )
            step_circle.grid(row=0, column=0, pady=(0, 5), sticky="n")
            
            # Step name
            step_name = ctk.CTkLabel(
                step_container,
                text=name,
                font=ctk.CTkFont(size=11),
                text_color=("gray40", "gray60")
            )
            step_name.grid(row=1, column=0, sticky="n")
            
            self.step_indicators.append((step_circle, step_name))
        
        # Current parameter validation status
        self.parameter_label = ctk.CTkLabel(
            main_frame,
            text="Initializing validation...",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("gray10", "gray90")
        )
        self.parameter_label.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="w")
        
        # Progress section
        progress_section = ctk.CTkFrame(main_frame, fg_color="transparent")
        progress_section.grid(row=4, column=0, padx=20, pady=(0, 15), sticky="ew")
        progress_section.grid_columnconfigure(0, weight=1)
        
        # Overall progress
        overall_progress_label = ctk.CTkLabel(
            progress_section,
            text="Overall Validation Progress",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("gray30", "gray70")
        )
        overall_progress_label.grid(row=0, column=0, sticky="w", pady=(0, 3))
        
        self.progress_bar = ctk.CTkProgressBar(
            progress_section, 
            height=14,
            corner_radius=7,
            progress_color="#1f538d"
        )
        self.progress_bar.grid(row=1, column=0, pady=(0, 8), sticky="ew")
        self.progress_bar.set(0)
        
        # Parameter validation progress
        param_progress_label = ctk.CTkLabel(
            progress_section,
            text="Current Step Progress",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("gray30", "gray70")
        )
        param_progress_label.grid(row=2, column=0, sticky="w", pady=(5, 3))
        
        self.param_progress_bar = ctk.CTkProgressBar(
            progress_section,
            height=10,
            corner_radius=5,
            progress_color="#2AAA8A"
        )
        self.param_progress_bar.grid(row=3, column=0, pady=(0, 10), sticky="ew")
        self.param_progress_bar.set(0)
        
        # Progress details
        progress_details = ctk.CTkFrame(progress_section, fg_color="transparent")
        progress_details.grid(row=4, column=0, sticky="ew")
        progress_details.grid_columnconfigure(0, weight=1)
        progress_details.grid_columnconfigure(1, weight=0)
        
        self.progress_text = ctk.CTkLabel(
            progress_details,
            text="Step 0/0 • Parameter 0/0",
            font=ctk.CTkFont(size=11),
            text_color=("gray30", "gray70")
        )
        self.progress_text.grid(row=0, column=0, sticky="w")
        
        self.percentage_text = ctk.CTkLabel(
            progress_details,
            text="0%",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#1f538d"
        )
        self.percentage_text.grid(row=0, column=1, sticky="e")
        
        # Real-time validation results section
        results_frame = ctk.CTkFrame(main_frame, corner_radius=8, fg_color=("gray95", "gray15"))
        results_frame.grid(row=5, column=0, padx=20, pady=(0, 15), sticky="ew")
        results_frame.grid_columnconfigure(0, weight=1)
        results_frame.grid_rowconfigure(1, weight=1)
        
        # Results header
        results_header = ctk.CTkLabel(
            results_frame,
            text="Validation Results (Real-time)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray10", "gray90")
        )
        results_header.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")
        
        # Results text area (scrollable)
        self.results_text = ctk.CTkTextbox(
            results_frame,
            height=100,
            font=ctk.CTkFont(size=10),
            wrap="word"
        )
        self.results_text.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="ew")
        
        # Status and timing information
        status_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        status_frame.grid(row=6, column=0, padx=20, pady=(0, 15), sticky="ew")
        status_frame.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="Starting validation...",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60"),
            wraplength=550,
            justify="left"
        )
        self.status_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        self.timing_label = ctk.CTkLabel(
            status_frame,
            text="",
            font=ctk.CTkFont(size=10),
            text_color=("gray50", "gray50"),
            justify="left"
        )
        self.timing_label.grid(row=1, column=0, sticky="w")
        
        # Button frame
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.grid(row=7, column=0, padx=20, pady=(0, 20), sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=0)
        
        # Cancel button
        self.cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
            width=90,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40")
        )
        self.cancel_button.grid(row=0, column=1, padx=(10, 0), pady=0, sticky="e")
        
        # Close button (initially hidden)
        self.close_button = ctk.CTkButton(
            button_frame,
            text="Close",
            command=self._on_close,
            width=90,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color="#1f538d",
            hover_color="#144870"
        )
    
    def update_validation_progress(self, progress_info: ValidationProgressInfo):
        """Update the validation progress dialog with new information."""
        # Update validation summary
        if hasattr(self, 'summary_details'):
            summary_text = (
                f"Parameters: {progress_info.parameters_validated}/{progress_info.total_parameters} validated\n"
                f"Errors: {progress_info.errors_found} • Warnings: {progress_info.warnings_found} • "
                f"Passed: {progress_info.parameters_passed}"
            )
            self.summary_details.configure(text=summary_text)
        
        # Update step indicators
        if hasattr(self, 'step_indicators'):
            current_step = progress_info.current_step
            for i, (circle, name) in enumerate(self.step_indicators):
                step_num = i + 1
                
                if step_num < current_step:
                    # Completed step
                    if progress_info.errors_found > 0 and step_num <= 2:  # Structure or Parameters step had errors
                        circle.configure(fg_color="#E74C3C", text="✗", text_color="white")  # Red X for errors
                        name.configure(text_color="#E74C3C", font=ctk.CTkFont(size=11, weight="bold"))
                    else:
                        circle.configure(fg_color="#2AAA8A", text="✓", text_color="white")  # Green checkmark
                        name.configure(text_color="#2AAA8A", font=ctk.CTkFont(size=11, weight="bold"))
                elif step_num == current_step:
                    # Current step
                    circle.configure(fg_color="#1f538d", text=str(step_num), text_color="white")
                    name.configure(text_color="#1f538d", font=ctk.CTkFont(size=11, weight="bold"))
                else:
                    # Future step
                    circle.configure(fg_color=("gray60", "gray40"), text=str(step_num), text_color="white")
                    name.configure(text_color=("gray40", "gray60"), font=ctk.CTkFont(size=11))
        
        # Update progress bars
        if progress_info.total_steps > 0:
            overall_progress = progress_info.progress_percentage
            self.progress_bar.set(overall_progress)
        
        if progress_info.total_parameters > 0 and progress_info.parameters_validated > 0:
            param_progress = progress_info.parameters_validated / progress_info.total_parameters
            self.param_progress_bar.set(param_progress)
        
        # Update progress text
        progress_text = f"Step {progress_info.current_step}/{progress_info.total_steps}"
        if progress_info.total_parameters > 0:
            progress_text += f" • Parameter {progress_info.parameters_validated}/{progress_info.total_parameters}"
        if progress_info.validation_speed:
            progress_text += f" • {progress_info.validation_speed}"
        self.progress_text.configure(text=progress_text)
        
        # Update percentage
        percentage = int(progress_info.progress_percentage * 100)
        self.percentage_text.configure(text=f"{percentage}%")
        
        # Color code percentage based on errors
        if progress_info.critical_errors > 0:
            color = "#E74C3C"  # Red for critical errors
        elif progress_info.errors_found > 0:
            color = "#FF8C00"  # Orange for errors
        elif progress_info.warnings_found > 0:
            color = "#F39C12"  # Yellow for warnings
        else:
            color = "#2AAA8A"  # Green for success
        self.percentage_text.configure(text_color=color)
        
        # Update current parameter status
        if progress_info.parameter_name:
            status_text = f"Validating: {progress_info.parameter_name}"
            if progress_info.current_parameter_status:
                status_icons = {
                    'validating': '⏳',
                    'passed': '✓',
                    'failed': '✗',
                    'warning': '⚠'
                }
                icon = status_icons.get(progress_info.current_parameter_status, '')
                status_text = f"{icon} {status_text}"
            self.parameter_label.configure(text=status_text)
        elif progress_info.step_name:
            self.parameter_label.configure(text=progress_info.step_name)
        
        # Update status message
        if progress_info.status_message:
            self.status_label.configure(text=progress_info.status_message)
        
        # Update timing information
        timing_parts = []
        if progress_info.estimated_time_remaining:
            timing_parts.append(f"ETA: {progress_info.estimated_time_remaining}")
        if progress_info.validation_speed:
            timing_parts.append(f"Speed: {progress_info.validation_speed}")
        
        timing_text = " • ".join(timing_parts) if timing_parts else ""
        self.timing_label.configure(text=timing_text)
        
        # Update real-time results
        if progress_info.validation_errors or progress_info.validation_warnings:
            self._update_results_display(progress_info.validation_errors, progress_info.validation_warnings)
        
        # Handle completion
        if progress_info.is_completed:
            self._on_validation_completion(progress_info)
        
        # Handle cancellation
        if progress_info.is_cancelled:
            self._on_cancellation()
    
    def _update_results_display(self, errors: List[ValidationError], warnings: List[ValidationError]):
        """Update the real-time results display."""
        if not hasattr(self, 'results_text'):
            return
        
        # Clear existing content
        self.results_text.delete("1.0", "end")
        
        # Add errors
        if errors:
            self.results_text.insert("end", "ERRORS:\n", "error_header")
            for error in errors[-10:]:  # Show last 10 errors
                severity_icon = "🔴" if error.severity == ValidationSeverity.CRITICAL else "🟠"
                error_text = f"{severity_icon} {error.location}: {error.message}\n"
                self.results_text.insert("end", error_text, "error")
            
            if len(errors) > 10:
                self.results_text.insert("end", f"... and {len(errors) - 10} more errors\n\n", "info")
            else:
                self.results_text.insert("end", "\n", "info")
        
        # Add warnings
        if warnings:
            self.results_text.insert("end", "WARNINGS:\n", "warning_header")
            for warning in warnings[-5:]:  # Show last 5 warnings
                warning_text = f"🟡 {warning.location}: {warning.message}\n"
                self.results_text.insert("end", warning_text, "warning")
            
            if len(warnings) > 5:
                self.results_text.insert("end", f"... and {len(warnings) - 5} more warnings\n", "info")
        
        # Configure text tags for styling
        self.results_text.tag_config("error_header", foreground="#E74C3C", font=ctk.CTkFont(size=10, weight="bold"))
        self.results_text.tag_config("warning_header", foreground="#F39C12", font=ctk.CTkFont(size=10, weight="bold"))
        self.results_text.tag_config("error", foreground="#E74C3C")
        self.results_text.tag_config("warning", foreground="#F39C12")
        self.results_text.tag_config("info", foreground=("gray40", "gray60"))
        
        # Scroll to bottom
        self.results_text.see("end")
    
    def _on_validation_completion(self, progress_info: ValidationProgressInfo):
        """Handle validation completion."""
        # Update UI for completion
        self.cancel_button.grid_remove()
        self.close_button.grid(row=0, column=1, padx=(10, 0), pady=0, sticky="e")
        
        # Update title based on results
        if progress_info.critical_errors > 0:
            self.title_label.configure(text="Validation Failed - Critical Errors Found")
            icon_color = "#E74C3C"
            icon_text = "✗"
        elif progress_info.errors_found > 0:
            self.title_label.configure(text="Validation Completed with Errors")
            icon_color = "#FF8C00"
            icon_text = "⚠"
        elif progress_info.warnings_found > 0:
            self.title_label.configure(text="Validation Completed with Warnings")
            icon_color = "#F39C12"
            icon_text = "⚠"
        else:
            self.title_label.configure(text="Validation Completed Successfully")
            icon_color = "#2AAA8A"
            icon_text = "✓"
        
        # Update header icon
        if hasattr(self, 'header_icon'):
            self.header_icon.configure(fg_color=icon_color, text=icon_text)
        
        # Final status message
        final_status = (
            f"Validation completed. "
            f"Parameters: {progress_info.parameters_validated}/{progress_info.total_parameters}, "
            f"Errors: {progress_info.errors_found}, "
            f"Warnings: {progress_info.warnings_found}"
        )
        self.status_label.configure(text=final_status)
    
    def _on_cancel(self):
        """Handle cancel button click."""
        self.is_cancelled = True
        if self.cancel_callback:
            self.cancel_callback()
        self._on_close()
    
    def _on_close(self):
        """Handle close button click."""
        self.dialog.destroy()
    
    def _on_window_close(self):
        """Handle window close event."""
        if not self.is_cancelled:
            self._on_cancel()
    
    def set_cancel_callback(self, callback: Callable):
        """Set callback function for cancel operation."""
        self.cancel_callback = callback
    
    def show(self):
        """Show the dialog."""
        self.dialog.deiconify()
        self.dialog.lift()
        self.dialog.focus_force()
    
    def hide(self):
        """Hide the dialog."""
        self.dialog.withdraw()
    
    def destroy(self):
        """Destroy the dialog."""
        self.dialog.destroy()


def show_validation_progress_dialog(parent, title: str, operation_type: str) -> ProfileValidationProgressDialog:
    """
    Show a profile validation progress dialog.
    
    Args:
        parent: Parent window
        title: Dialog title
        operation_type: Type of validation operation
        
    Returns:
        ProfileValidationProgressDialog instance
    """
    return ProfileValidationProgressDialog(parent, title, operation_type)