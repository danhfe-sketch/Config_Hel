"""
Profile Validation Error Dialog - Detailed error display with specific parameter locations.

This module provides detailed error display for profile validation including:
1. Detailed error display with specific parameter locations
2. Error categorization and severity indication
3. Expandable error details with suggestions
4. Navigation between errors
"""

import customtkinter as ctk
from typing import List, Optional, Dict, Any
from services.profile_validator import ValidationError, ValidationWarning, ValidationResult, ValidationSeverity
from services.profile_error_handler import Suggestion


class ProfileValidationErrorDialog:
    """Detailed error dialog for profile validation results."""
    
    def __init__(self, parent, validation_result: ValidationResult, profile_name: str = ""):
        """
        Initialize the profile validation error dialog.
        
        Args:
            parent: Parent window
            validation_result: ValidationResult with errors and warnings
            profile_name: Name of the profile being validated
        """
        self.parent = parent
        self.validation_result = validation_result
        self.profile_name = profile_name
        self.current_error_index = 0
        
        # Get i18n service from parent if available
        self.i18n = parent.i18n_service if hasattr(parent, 'i18n_service') else None
        
        # Get theme service from parent
        self.theme_service = parent.theme_service if hasattr(parent, 'theme_service') else None
        
        # Create the dialog window
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Profile Validation Errors")
        self.dialog.geometry("700x600")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Apply consistent theming
        self._apply_consistent_theming()
        
        # Center the dialog
        self._center_dialog()
        
        # Create UI elements
        self._create_ui()
        
        # Handle window close event
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Load initial error data
        self._load_error_data()
    
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
            
            dialog_width = 700
            dialog_height = 600
            x = parent_x + (parent_width // 2) - (dialog_width // 2)
            y = parent_y + (parent_height // 2) - (dialog_height // 2)
            
            screen_width = self.dialog.winfo_screenwidth()
            screen_height = self.dialog.winfo_screenheight()
            
            x = max(0, min(x, screen_width - dialog_width))
            y = max(0, min(y, screen_height - dialog_height))
            
            self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        except Exception:
            self.dialog.geometry("700x600+300+150")
    
    def _create_ui(self):
        """Create the dialog UI elements."""
        # Configure main dialog grid
        self.dialog.grid_columnconfigure(0, weight=1)
        self.dialog.grid_rowconfigure(0, weight=1)
        
        # Create main frame
        main_frame = ctk.CTkFrame(self.dialog, corner_radius=10)
        main_frame.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(2, weight=1)  # Make error details expandable
        
        # Header section
        self._create_header(main_frame)
        
        # Summary section
        self._create_summary_section(main_frame)
        
        # Error details section (expandable)
        self._create_error_details_section(main_frame)
        
        # Navigation and action buttons
        self._create_button_section(main_frame)
    
    def _create_header(self, parent):
        """Create the header section."""
        header_frame = ctk.CTkFrame(parent, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 15), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)
        
        # Determine header icon and color based on validation result
        if self.validation_result.has_critical_errors():
            icon_text = "🔴"
            icon_color = "#E74C3C"
            title_text = "Critical Validation Errors Found"
        elif len(self.validation_result.get_errors_by_severity('error')) > 0:
            icon_text = "🟠"
            icon_color = "#FF8C00"
            title_text = "Validation Errors Found"
        else:
            icon_text = "🟡"
            icon_color = "#F39C12"
            title_text = "Validation Warnings Found"
        
        # Error icon
        icon_label = ctk.CTkLabel(
            header_frame,
            text=icon_text,
            width=40,
            height=40,
            fg_color=icon_color,
            corner_radius=20,
            text_color="white",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        icon_label.grid(row=0, column=0, padx=(0, 15), pady=0, sticky="w")
        
        # Title and profile name
        title_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_frame.grid(row=0, column=1, sticky="ew")
        title_frame.grid_columnconfigure(0, weight=1)
        
        self.title_label = ctk.CTkLabel(
            title_frame,
            text=title_text,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=("gray10", "gray90")
        )
        self.title_label.grid(row=0, column=0, sticky="w")
        
        if self.profile_name:
            profile_label = ctk.CTkLabel(
                title_frame,
                text=f"Profile: {self.profile_name}",
                font=ctk.CTkFont(size=12),
                text_color=("gray30", "gray70")
            )
            profile_label.grid(row=1, column=0, sticky="w", pady=(2, 0))
    
    def _create_summary_section(self, parent):
        """Create the validation summary section."""
        summary_frame = ctk.CTkFrame(parent, corner_radius=8, fg_color=("gray95", "gray15"))
        summary_frame.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="ew")
        summary_frame.grid_columnconfigure(0, weight=1)
        
        # Summary header
        summary_header = ctk.CTkLabel(
            summary_frame,
            text="Validation Summary",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("gray10", "gray90")
        )
        summary_header.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="w")
        
        # Summary statistics
        summary_stats_frame = ctk.CTkFrame(summary_frame, fg_color="transparent")
        summary_stats_frame.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="ew")
        summary_stats_frame.grid_columnconfigure(0, weight=1)
        summary_stats_frame.grid_columnconfigure(1, weight=1)
        summary_stats_frame.grid_columnconfigure(2, weight=1)
        summary_stats_frame.grid_columnconfigure(3, weight=1)
        
        # Count different types of issues
        critical_errors = len(self.validation_result.get_errors_by_severity('critical'))
        errors = len(self.validation_result.get_errors_by_severity('error'))
        warnings = len(self.validation_result.warnings)
        total_issues = critical_errors + errors + warnings
        
        # Critical errors
        critical_frame = ctk.CTkFrame(summary_stats_frame, fg_color="#E74C3C", corner_radius=6)
        critical_frame.grid(row=0, column=0, padx=(0, 5), pady=0, sticky="ew")
        
        ctk.CTkLabel(
            critical_frame,
            text=str(critical_errors),
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="white"
        ).pack(pady=(8, 2))
        
        ctk.CTkLabel(
            critical_frame,
            text="Critical",
            font=ctk.CTkFont(size=10),
            text_color="white"
        ).pack(pady=(0, 8))
        
        # Errors
        error_frame = ctk.CTkFrame(summary_stats_frame, fg_color="#FF8C00", corner_radius=6)
        error_frame.grid(row=0, column=1, padx=5, pady=0, sticky="ew")
        
        ctk.CTkLabel(
            error_frame,
            text=str(errors),
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="white"
        ).pack(pady=(8, 2))
        
        ctk.CTkLabel(
            error_frame,
            text="Errors",
            font=ctk.CTkFont(size=10),
            text_color="white"
        ).pack(pady=(0, 8))
        
        # Warnings
        warning_frame = ctk.CTkFrame(summary_stats_frame, fg_color="#F39C12", corner_radius=6)
        warning_frame.grid(row=0, column=2, padx=5, pady=0, sticky="ew")
        
        ctk.CTkLabel(
            warning_frame,
            text=str(warnings),
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="white"
        ).pack(pady=(8, 2))
        
        ctk.CTkLabel(
            warning_frame,
            text="Warnings",
            font=ctk.CTkFont(size=10),
            text_color="white"
        ).pack(pady=(0, 8))
        
        # Total
        total_frame = ctk.CTkFrame(summary_stats_frame, fg_color="#1f538d", corner_radius=6)
        total_frame.grid(row=0, column=3, padx=(5, 0), pady=0, sticky="ew")
        
        ctk.CTkLabel(
            total_frame,
            text=str(total_issues),
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="white"
        ).pack(pady=(8, 2))
        
        ctk.CTkLabel(
            total_frame,
            text="Total Issues",
            font=ctk.CTkFont(size=10),
            text_color="white"
        ).pack(pady=(0, 8))
    
    def _create_error_details_section(self, parent):
        """Create the expandable error details section."""
        details_frame = ctk.CTkFrame(parent, corner_radius=8)
        details_frame.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="nsew")
        details_frame.grid_columnconfigure(0, weight=1)
        details_frame.grid_rowconfigure(1, weight=1)
        
        # Details header with navigation
        details_header_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
        details_header_frame.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")
        details_header_frame.grid_columnconfigure(1, weight=1)
        
        details_header = ctk.CTkLabel(
            details_header_frame,
            text="Error Details",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("gray10", "gray90")
        )
        details_header.grid(row=0, column=0, sticky="w")
        
        # Navigation controls
        nav_frame = ctk.CTkFrame(details_header_frame, fg_color="transparent")
        nav_frame.grid(row=0, column=2, sticky="e")
        
        self.prev_button = ctk.CTkButton(
            nav_frame,
            text="◀",
            command=self._previous_error,
            width=30,
            height=25,
            font=ctk.CTkFont(size=12)
        )
        self.prev_button.pack(side="left", padx=(0, 5))
        
        self.error_counter_label = ctk.CTkLabel(
            nav_frame,
            text="1 / 1",
            font=ctk.CTkFont(size=11),
            text_color=("gray30", "gray70")
        )
        self.error_counter_label.pack(side="left", padx=5)
        
        self.next_button = ctk.CTkButton(
            nav_frame,
            text="▶",
            command=self._next_error,
            width=30,
            height=25,
            font=ctk.CTkFont(size=12)
        )
        self.next_button.pack(side="left", padx=(5, 0))
        
        # Scrollable error details
        self.error_details_frame = ctk.CTkScrollableFrame(details_frame)
        self.error_details_frame.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        self.error_details_frame.grid_columnconfigure(0, weight=1)
    
    def _create_button_section(self, parent):
        """Create the button section."""
        button_frame = ctk.CTkFrame(parent, fg_color="transparent")
        button_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        
        # Action buttons
        action_frame = ctk.CTkFrame(button_frame, fg_color="transparent")
        action_frame.grid(row=0, column=0, sticky="w")
        
        self.export_button = ctk.CTkButton(
            action_frame,
            text="Export Report",
            command=self._export_report,
            width=120,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40")
        )
        self.export_button.pack(side="left", padx=(0, 10))
        
        self.copy_button = ctk.CTkButton(
            action_frame,
            text="Copy Details",
            command=self._copy_details,
            width=120,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40")
        )
        self.copy_button.pack(side="left")
        
        # Close button
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
        self.close_button.grid(row=0, column=1, sticky="e")
    
    def _load_error_data(self):
        """Load and display error data."""
        # Combine errors and warnings for navigation
        self.all_issues = []
        
        # Add critical errors first
        for error in self.validation_result.get_errors_by_severity('critical'):
            self.all_issues.append(('critical', error))
        
        # Add regular errors
        for error in self.validation_result.get_errors_by_severity('error'):
            self.all_issues.append(('error', error))
        
        # Add warnings
        for warning in self.validation_result.warnings:
            self.all_issues.append(('warning', warning))
        
        # Update navigation
        self._update_navigation()
        
        # Display first error
        if self.all_issues:
            self._display_current_error()
    
    def _update_navigation(self):
        """Update navigation controls."""
        total_issues = len(self.all_issues)
        
        if total_issues == 0:
            self.error_counter_label.configure(text="No issues")
            self.prev_button.configure(state="disabled")
            self.next_button.configure(state="disabled")
            return
        
        # Update counter
        self.error_counter_label.configure(text=f"{self.current_error_index + 1} / {total_issues}")
        
        # Update button states
        self.prev_button.configure(state="normal" if self.current_error_index > 0 else "disabled")
        self.next_button.configure(state="normal" if self.current_error_index < total_issues - 1 else "disabled")
    
    def _display_current_error(self):
        """Display the current error in the details section."""
        # Clear existing content
        for widget in self.error_details_frame.winfo_children():
            widget.destroy()
        
        if not self.all_issues:
            no_issues_label = ctk.CTkLabel(
                self.error_details_frame,
                text="No validation issues found.",
                font=ctk.CTkFont(size=12),
                text_color=("gray40", "gray60")
            )
            no_issues_label.pack(pady=20)
            return
        
        issue_type, issue = self.all_issues[self.current_error_index]
        
        # Issue header
        header_frame = ctk.CTkFrame(self.error_details_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 15))
        header_frame.grid_columnconfigure(1, weight=1)
        
        # Severity indicator
        severity_colors = {
            'critical': "#E74C3C",
            'error': "#FF8C00",
            'warning': "#F39C12"
        }
        
        severity_icons = {
            'critical': "🔴",
            'error': "🟠",
            'warning': "🟡"
        }
        
        severity_color = severity_colors.get(issue_type, "#1f538d")
        severity_icon = severity_icons.get(issue_type, "ℹ")
        
        severity_label = ctk.CTkLabel(
            header_frame,
            text=f"{severity_icon} {issue_type.upper()}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=severity_color,
            width=80
        )
        severity_label.grid(row=0, column=0, sticky="w", padx=(0, 15))
        
        # Location
        location_text = getattr(issue, 'location', 'Unknown location')
        location_label = ctk.CTkLabel(
            header_frame,
            text=f"Location: {location_text}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray10", "gray90")
        )
        location_label.grid(row=0, column=1, sticky="w")
        
        # Error message
        message_frame = ctk.CTkFrame(self.error_details_frame, corner_radius=6, fg_color=("gray95", "gray15"))
        message_frame.pack(fill="x", pady=(0, 15))
        
        message_label = ctk.CTkLabel(
            message_frame,
            text=getattr(issue, 'message', 'No message available'),
            font=ctk.CTkFont(size=12),
            text_color=("gray10", "gray90"),
            wraplength=600,
            justify="left"
        )
        message_label.pack(padx=15, pady=15, anchor="w")
        
        # Additional details
        details_frame = ctk.CTkFrame(self.error_details_frame, fg_color="transparent")
        details_frame.pack(fill="x", pady=(0, 15))
        details_frame.grid_columnconfigure(1, weight=1)
        
        # Parameter name (if available)
        parameter_name = getattr(issue, 'parameter_name', None)
        if parameter_name:
            ctk.CTkLabel(
                details_frame,
                text="Parameter:",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("gray30", "gray70"),
                width=100
            ).grid(row=0, column=0, sticky="w", pady=2)
            
            ctk.CTkLabel(
                details_frame,
                text=parameter_name,
                font=ctk.CTkFont(size=11),
                text_color=("gray10", "gray90")
            ).grid(row=0, column=1, sticky="w", pady=2)
        
        # Current value (if available)
        current_value = getattr(issue, 'current_value', None) or getattr(issue, 'actual_value', None)
        if current_value:
            row = 1 if parameter_name else 0
            ctk.CTkLabel(
                details_frame,
                text="Current Value:",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("gray30", "gray70"),
                width=100
            ).grid(row=row, column=0, sticky="w", pady=2)
            
            ctk.CTkLabel(
                details_frame,
                text=str(current_value),
                font=ctk.CTkFont(size=11),
                text_color=("gray10", "gray90")
            ).grid(row=row, column=1, sticky="w", pady=2)
        
        # Expected format (if available)
        expected_format = getattr(issue, 'expected_format', None) or getattr(issue, 'expected_value', None)
        if expected_format:
            row = (1 if parameter_name else 0) + (1 if current_value else 0)
            ctk.CTkLabel(
                details_frame,
                text="Expected:",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("gray30", "gray70"),
                width=100
            ).grid(row=row, column=0, sticky="w", pady=2)
            
            ctk.CTkLabel(
                details_frame,
                text=str(expected_format),
                font=ctk.CTkFont(size=11),
                text_color=("gray10", "gray90")
            ).grid(row=row, column=1, sticky="w", pady=2)
        
        # Suggestion (if available)
        suggestion = getattr(issue, 'suggestion', None)
        if suggestion:
            suggestion_frame = ctk.CTkFrame(self.error_details_frame, corner_radius=6, fg_color="#2AAA8A")
            suggestion_frame.pack(fill="x", pady=(0, 10))
            
            suggestion_header = ctk.CTkLabel(
                suggestion_frame,
                text="💡 Suggestion:",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="white"
            )
            suggestion_header.pack(anchor="w", padx=15, pady=(10, 5))
            
            suggestion_text = ctk.CTkLabel(
                suggestion_frame,
                text=suggestion,
                font=ctk.CTkFont(size=11),
                text_color="white",
                wraplength=600,
                justify="left"
            )
            suggestion_text.pack(anchor="w", padx=15, pady=(0, 10))
    
    def _previous_error(self):
        """Navigate to previous error."""
        if self.current_error_index > 0:
            self.current_error_index -= 1
            self._update_navigation()
            self._display_current_error()
    
    def _next_error(self):
        """Navigate to next error."""
        if self.current_error_index < len(self.all_issues) - 1:
            self.current_error_index += 1
            self._update_navigation()
            self._display_current_error()
    
    def _export_report(self):
        """Export validation report to file."""
        try:
            from tkinter import filedialog
            import os
            from datetime import datetime
            
            # Ask user for save location
            filename = filedialog.asksaveasfilename(
                title="Export Validation Report",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialname=f"validation_report_{self.profile_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )
            
            if filename:
                self._write_report_to_file(filename)
                
                # Show success message
                from ui.custom_dialogs import show_info
                show_info(self.dialog, "Export Successful", f"Validation report exported to:\n{filename}")
        
        except Exception as e:
            from ui.custom_dialogs import show_error
            show_error(self.dialog, "Export Failed", f"Failed to export report:\n{str(e)}")
    
    def _write_report_to_file(self, filename: str):
        """Write validation report to file."""
        from datetime import datetime
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("PROFILE VALIDATION REPORT\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Profile Name: {self.profile_name}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Validation Status: {'FAILED' if not self.validation_result.is_valid else 'PASSED'}\n\n")
            
            # Summary
            critical_errors = len(self.validation_result.get_errors_by_severity('critical'))
            errors = len(self.validation_result.get_errors_by_severity('error'))
            warnings = len(self.validation_result.warnings)
            
            f.write("SUMMARY\n")
            f.write("-" * 20 + "\n")
            f.write(f"Critical Errors: {critical_errors}\n")
            f.write(f"Errors: {errors}\n")
            f.write(f"Warnings: {warnings}\n")
            f.write(f"Total Issues: {critical_errors + errors + warnings}\n\n")
            
            # Detailed errors
            f.write("DETAILED ISSUES\n")
            f.write("-" * 20 + "\n\n")
            
            for i, (issue_type, issue) in enumerate(self.all_issues, 1):
                f.write(f"{i}. {issue_type.upper()}\n")
                f.write(f"   Location: {getattr(issue, 'location', 'Unknown')}\n")
                f.write(f"   Message: {getattr(issue, 'message', 'No message')}\n")
                
                if hasattr(issue, 'parameter_name') and issue.parameter_name:
                    f.write(f"   Parameter: {issue.parameter_name}\n")
                
                current_value = getattr(issue, 'current_value', None) or getattr(issue, 'actual_value', None)
                if current_value:
                    f.write(f"   Current Value: {current_value}\n")
                
                expected = getattr(issue, 'expected_format', None) or getattr(issue, 'expected_value', None)
                if expected:
                    f.write(f"   Expected: {expected}\n")
                
                if hasattr(issue, 'suggestion') and issue.suggestion:
                    f.write(f"   Suggestion: {issue.suggestion}\n")
                
                f.write("\n")
    
    def _copy_details(self):
        """Copy current error details to clipboard."""
        try:
            if not self.all_issues:
                return
            
            issue_type, issue = self.all_issues[self.current_error_index]
            
            details = f"{issue_type.upper()}\n"
            details += f"Location: {getattr(issue, 'location', 'Unknown')}\n"
            details += f"Message: {getattr(issue, 'message', 'No message')}\n"
            
            if hasattr(issue, 'parameter_name') and issue.parameter_name:
                details += f"Parameter: {issue.parameter_name}\n"
            
            current_value = getattr(issue, 'current_value', None) or getattr(issue, 'actual_value', None)
            if current_value:
                details += f"Current Value: {current_value}\n"
            
            expected = getattr(issue, 'expected_format', None) or getattr(issue, 'expected_value', None)
            if expected:
                details += f"Expected: {expected}\n"
            
            if hasattr(issue, 'suggestion') and issue.suggestion:
                details += f"Suggestion: {issue.suggestion}\n"
            
            # Copy to clipboard
            self.dialog.clipboard_clear()
            self.dialog.clipboard_append(details)
            
            # Show brief confirmation
            from ui.custom_dialogs import show_info
            show_info(self.dialog, "Copied", "Error details copied to clipboard.")
            
        except Exception as e:
            from ui.custom_dialogs import show_error
            show_error(self.dialog, "Copy Failed", f"Failed to copy details:\n{str(e)}")
    
    def _on_close(self):
        """Handle close button click."""
        self.dialog.destroy()


def show_validation_error_dialog(parent, validation_result: ValidationResult, profile_name: str = "") -> None:
    """
    Show a profile validation error dialog.
    
    Args:
        parent: Parent window
        validation_result: ValidationResult with errors and warnings
        profile_name: Name of the profile being validated
    """
    ProfileValidationErrorDialog(parent, validation_result, profile_name)