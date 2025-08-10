"""
Profile Validation Summary Dialog - Summary dialog with error counts and suggestions.

This module provides validation summary dialog including:
1. Validation summary with error counts and statistics
2. Categorized suggestions for fixing issues
3. Quick actions for common fixes
4. Option to proceed with warnings or cancel operation
"""

import customtkinter as ctk
from typing import List, Optional, Dict, Any, Callable
from services.profile_validator import ValidationResult, ValidationError, ValidationSeverity
from services.profile_error_handler import Suggestion, ProfileErrorHandler


class ProfileValidationSummaryDialog:
    """Summary dialog for profile validation results with suggestions."""
    
    def __init__(self, parent, validation_result: ValidationResult, profile_name: str = "", 
                 operation_context: Dict[str, Any] = None, on_proceed: Callable = None, 
                 on_cancel: Callable = None):
        """
        Initialize the profile validation summary dialog.
        
        Args:
            parent: Parent window
            validation_result: ValidationResult with errors and warnings
            profile_name: Name of the profile being validated
            operation_context: Context about the operation being performed
            on_proceed: Callback for when user chooses to proceed
            on_cancel: Callback for when user chooses to cancel
        """
        self.parent = parent
        self.validation_result = validation_result
        self.profile_name = profile_name
        self.operation_context = operation_context or {}
        self.on_proceed = on_proceed
        self.on_cancel = on_cancel
        self.user_choice = None
        
        # Initialize error handler for suggestions
        self.error_handler = ProfileErrorHandler()
        
        # Get i18n service from parent if available
        self.i18n = parent.i18n_service if hasattr(parent, 'i18n_service') else None
        
        # Get theme service from parent
        self.theme_service = parent.theme_service if hasattr(parent, 'theme_service') else None
        
        # Create the dialog window
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Profile Validation Summary")
        self.dialog.geometry("650x550")
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
        
        # Generate suggestions
        self._generate_suggestions()
    
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
            
            dialog_width = 650
            dialog_height = 550
            x = parent_x + (parent_width // 2) - (dialog_width // 2)
            y = parent_y + (parent_height // 2) - (dialog_height // 2)
            
            screen_width = self.dialog.winfo_screenwidth()
            screen_height = self.dialog.winfo_screenheight()
            
            x = max(0, min(x, screen_width - dialog_width))
            y = max(0, min(y, screen_height - dialog_height))
            
            self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        except Exception:
            self.dialog.geometry("650x550+300+150")
    
    def _create_ui(self):
        """Create the dialog UI elements."""
        # Configure main dialog grid
        self.dialog.grid_columnconfigure(0, weight=1)
        self.dialog.grid_rowconfigure(0, weight=1)
        
        # Create main frame
        main_frame = ctk.CTkFrame(self.dialog, corner_radius=10)
        main_frame.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(2, weight=1)  # Make suggestions section expandable
        
        # Header section
        self._create_header(main_frame)
        
        # Validation statistics section
        self._create_statistics_section(main_frame)
        
        # Suggestions section (expandable)
        self._create_suggestions_section(main_frame)
        
        # Action buttons
        self._create_action_buttons(main_frame)
    
    def _create_header(self, parent):
        """Create the header section."""
        header_frame = ctk.CTkFrame(parent, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 15), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)
        
        # Determine header based on validation result
        if self.validation_result.has_critical_errors():
            icon_text = "🔴"
            icon_color = "#E74C3C"
            title_text = "Validation Failed"
            subtitle_text = "Critical errors prevent operation from continuing"
        elif len(self.validation_result.get_errors_by_severity('error')) > 0:
            icon_text = "🟠"
            icon_color = "#FF8C00"
            title_text = "Validation Issues Found"
            subtitle_text = "Errors found that should be addressed"
        elif len(self.validation_result.warnings) > 0:
            icon_text = "🟡"
            icon_color = "#F39C12"
            title_text = "Validation Warnings"
            subtitle_text = "Minor issues found - operation can continue"
        else:
            icon_text = "✅"
            icon_color = "#2AAA8A"
            title_text = "Validation Successful"
            subtitle_text = "No issues found - ready to proceed"
        
        # Status icon
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
        
        # Title and subtitle
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
        
        subtitle_label = ctk.CTkLabel(
            title_frame,
            text=subtitle_text,
            font=ctk.CTkFont(size=12),
            text_color=("gray30", "gray70")
        )
        subtitle_label.grid(row=1, column=0, sticky="w", pady=(2, 0))
        
        # Profile name
        if self.profile_name:
            profile_label = ctk.CTkLabel(
                title_frame,
                text=f"Profile: {self.profile_name}",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("gray20", "gray80")
            )
            profile_label.grid(row=2, column=0, sticky="w", pady=(5, 0))
    
    def _create_statistics_section(self, parent):
        """Create the validation statistics section."""
        stats_frame = ctk.CTkFrame(parent, corner_radius=8, fg_color=("gray95", "gray15"))
        stats_frame.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="ew")
        stats_frame.grid_columnconfigure(0, weight=1)
        
        # Statistics header
        stats_header = ctk.CTkLabel(
            stats_frame,
            text="Validation Statistics",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("gray10", "gray90")
        )
        stats_header.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="w")
        
        # Statistics grid
        stats_grid = ctk.CTkFrame(stats_frame, fg_color="transparent")
        stats_grid.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="ew")
        
        # Configure grid columns
        for i in range(4):
            stats_grid.grid_columnconfigure(i, weight=1)
        
        # Count different types of issues
        critical_errors = len(self.validation_result.get_errors_by_severity('critical'))
        errors = len(self.validation_result.get_errors_by_severity('error'))
        warnings = len(self.validation_result.warnings)
        total_issues = critical_errors + errors + warnings
        
        # Get total parameters from validation summary if available
        total_parameters = 0
        valid_parameters = 0
        if self.validation_result.validation_summary:
            total_parameters = self.validation_result.validation_summary.total_parameters
            valid_parameters = self.validation_result.validation_summary.valid_parameters
        
        # Statistics cards
        stats_data = [
            ("Total Parameters", str(total_parameters), "#1f538d"),
            ("Valid Parameters", str(valid_parameters), "#2AAA8A"),
            ("Issues Found", str(total_issues), "#FF8C00" if total_issues > 0 else "#2AAA8A"),
            ("Critical Issues", str(critical_errors), "#E74C3C" if critical_errors > 0 else "#2AAA8A")
        ]
        
        for i, (label, value, color) in enumerate(stats_data):
            card_frame = ctk.CTkFrame(stats_grid, fg_color=color, corner_radius=6)
            card_frame.grid(row=0, column=i, padx=5, pady=0, sticky="ew")
            
            value_label = ctk.CTkLabel(
                card_frame,
                text=value,
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color="white"
            )
            value_label.pack(pady=(10, 2))
            
            label_label = ctk.CTkLabel(
                card_frame,
                text=label,
                font=ctk.CTkFont(size=10),
                text_color="white"
            )
            label_label.pack(pady=(0, 10))
        
        # Detailed breakdown
        if total_issues > 0:
            breakdown_frame = ctk.CTkFrame(stats_frame, fg_color="transparent")
            breakdown_frame.grid(row=2, column=0, padx=15, pady=(10, 15), sticky="ew")
            breakdown_frame.grid_columnconfigure(0, weight=1)
            
            breakdown_text = f"Breakdown: {critical_errors} critical, {errors} errors, {warnings} warnings"
            breakdown_label = ctk.CTkLabel(
                breakdown_frame,
                text=breakdown_text,
                font=ctk.CTkFont(size=11),
                text_color=("gray30", "gray70")
            )
            breakdown_label.grid(row=0, column=0, sticky="w")
            
            # Success rate
            if total_parameters > 0:
                success_rate = (valid_parameters / total_parameters) * 100
                success_text = f"Success Rate: {success_rate:.1f}%"
                success_label = ctk.CTkLabel(
                    breakdown_frame,
                    text=success_text,
                    font=ctk.CTkFont(size=11),
                    text_color=("#2AAA8A" if success_rate >= 80 else "#FF8C00" if success_rate >= 60 else "#E74C3C")
                )
                success_label.grid(row=1, column=0, sticky="w", pady=(2, 0))
    
    def _create_suggestions_section(self, parent):
        """Create the suggestions section."""
        suggestions_frame = ctk.CTkFrame(parent, corner_radius=8)
        suggestions_frame.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="nsew")
        suggestions_frame.grid_columnconfigure(0, weight=1)
        suggestions_frame.grid_rowconfigure(1, weight=1)
        
        # Suggestions header
        suggestions_header = ctk.CTkLabel(
            suggestions_frame,
            text="Recommended Actions",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("gray10", "gray90")
        )
        suggestions_header.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="w")
        
        # Scrollable suggestions area
        self.suggestions_scrollable = ctk.CTkScrollableFrame(suggestions_frame)
        self.suggestions_scrollable.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        self.suggestions_scrollable.grid_columnconfigure(0, weight=1)
    
    def _create_action_buttons(self, parent):
        """Create the action buttons section."""
        button_frame = ctk.CTkFrame(parent, fg_color="transparent")
        button_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        
        # Left side buttons (additional actions)
        left_buttons = ctk.CTkFrame(button_frame, fg_color="transparent")
        left_buttons.grid(row=0, column=0, sticky="w")
        
        self.details_button = ctk.CTkButton(
            left_buttons,
            text="View Details",
            command=self._show_detailed_errors,
            width=120,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40")
        )
        self.details_button.pack(side="left", padx=(0, 10))
        
        self.export_button = ctk.CTkButton(
            left_buttons,
            text="Export Report",
            command=self._export_summary,
            width=120,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40")
        )
        self.export_button.pack(side="left")
        
        # Right side buttons (main actions)
        right_buttons = ctk.CTkFrame(button_frame, fg_color="transparent")
        right_buttons.grid(row=0, column=1, sticky="e")
        
        # Determine button text and behavior based on validation result
        if self.validation_result.has_critical_errors():
            # Critical errors - only allow cancel
            self.cancel_button = ctk.CTkButton(
                right_buttons,
                text="Close",
                command=self._on_cancel_clicked,
                width=100,
                height=32,
                font=ctk.CTkFont(size=12),
                fg_color="#E74C3C",
                hover_color="#C0392B"
            )
            self.cancel_button.pack(side="right")
        else:
            # Errors or warnings - allow proceed or cancel
            self.cancel_button = ctk.CTkButton(
                right_buttons,
                text="Cancel",
                command=self._on_cancel_clicked,
                width=90,
                height=32,
                font=ctk.CTkFont(size=12),
                fg_color=("gray70", "gray30"),
                hover_color=("gray60", "gray40")
            )
            self.cancel_button.pack(side="right", padx=(10, 0))
            
            # Proceed button text depends on issues found
            if len(self.validation_result.get_errors_by_severity('error')) > 0:
                proceed_text = "Proceed Anyway"
                proceed_color = "#FF8C00"
                proceed_hover = "#E67E22"
            else:
                proceed_text = "Proceed"
                proceed_color = "#2AAA8A"
                proceed_hover = "#27AE60"
            
            self.proceed_button = ctk.CTkButton(
                right_buttons,
                text=proceed_text,
                command=self._on_proceed_clicked,
                width=120,
                height=32,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color=proceed_color,
                hover_color=proceed_hover
            )
            self.proceed_button.pack(side="right")
    
    def _generate_suggestions(self):
        """Generate and display suggestions."""
        # Clear existing suggestions
        for widget in self.suggestions_scrollable.winfo_children():
            widget.destroy()
        
        # Get suggestions from error handler
        all_errors = self.validation_result.errors
        suggestions = self.error_handler.suggest_corrections(all_errors)
        
        if not suggestions and not all_errors:
            # No issues found
            success_frame = ctk.CTkFrame(self.suggestions_scrollable, fg_color="#2AAA8A", corner_radius=6)
            success_frame.pack(fill="x", pady=(0, 10))
            
            success_label = ctk.CTkLabel(
                success_frame,
                text="✅ No issues found! The profile is ready for use.",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="white"
            )
            success_label.pack(pady=15)
            return
        
        if not suggestions:
            # No specific suggestions available
            general_frame = ctk.CTkFrame(self.suggestions_scrollable, fg_color=("gray95", "gray15"), corner_radius=6)
            general_frame.pack(fill="x", pady=(0, 10))
            
            general_label = ctk.CTkLabel(
                general_frame,
                text="ℹ️ Review the validation errors and fix the identified issues.",
                font=ctk.CTkFont(size=12),
                text_color=("gray10", "gray90")
            )
            general_label.pack(pady=15)
            return
        
        # Group suggestions by priority
        high_priority = [s for s in suggestions if s.priority == 1]
        medium_priority = [s for s in suggestions if s.priority == 2]
        low_priority = [s for s in suggestions if s.priority == 3]
        
        # Display high priority suggestions
        if high_priority:
            self._create_suggestion_group("🔴 High Priority", high_priority, "#E74C3C")
        
        # Display medium priority suggestions
        if medium_priority:
            self._create_suggestion_group("🟡 Medium Priority", medium_priority, "#F39C12")
        
        # Display low priority suggestions
        if low_priority:
            self._create_suggestion_group("🟢 Low Priority", low_priority, "#2AAA8A")
        
        # Add general recommendations
        self._add_general_recommendations()
    
    def _create_suggestion_group(self, title: str, suggestions: List[Suggestion], color: str):
        """Create a group of suggestions with a title."""
        # Group header
        header_frame = ctk.CTkFrame(self.suggestions_scrollable, fg_color=color, corner_radius=6)
        header_frame.pack(fill="x", pady=(0, 5))
        
        header_label = ctk.CTkLabel(
            header_frame,
            text=title,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="white"
        )
        header_label.pack(pady=8)
        
        # Suggestions in this group
        for i, suggestion in enumerate(suggestions[:5]):  # Limit to 5 suggestions per group
            suggestion_frame = ctk.CTkFrame(self.suggestions_scrollable, fg_color=("gray95", "gray15"), corner_radius=4)
            suggestion_frame.pack(fill="x", pady=(0, 5))
            suggestion_frame.grid_columnconfigure(0, weight=1)
            
            # Suggestion text
            suggestion_text = f"• {suggestion.description}"
            if suggestion.parameter_name:
                suggestion_text += f" (Parameter: {suggestion.parameter_name})"
            
            suggestion_label = ctk.CTkLabel(
                suggestion_frame,
                text=suggestion_text,
                font=ctk.CTkFont(size=11),
                text_color=("gray10", "gray90"),
                wraplength=550,
                justify="left"
            )
            suggestion_label.grid(row=0, column=0, padx=15, pady=10, sticky="w")
            
            # Show suggested value if available
            if suggestion.suggested_value:
                value_label = ctk.CTkLabel(
                    suggestion_frame,
                    text=f"Suggested value: {suggestion.suggested_value}",
                    font=ctk.CTkFont(size=10),
                    text_color=color
                )
                value_label.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="w")
        
        if len(suggestions) > 5:
            more_label = ctk.CTkLabel(
                self.suggestions_scrollable,
                text=f"... and {len(suggestions) - 5} more suggestions in this category",
                font=ctk.CTkFont(size=10),
                text_color=("gray40", "gray60")
            )
            more_label.pack(pady=(0, 10))
    
    def _add_general_recommendations(self):
        """Add general recommendations based on validation results."""
        recommendations = []
        
        # Add recommendations based on error types
        error_types = set()
        for error in self.validation_result.errors:
            error_types.add(error.error_type.value if hasattr(error.error_type, 'value') else str(error.error_type))
        
        if 'missing_section' in error_types:
            recommendations.append("📋 Add missing required sections to the profile file")
        
        if 'invalid_parameter' in error_types:
            recommendations.append("🔧 Review and correct invalid parameter values")
        
        if 'format_error' in error_types:
            recommendations.append("📝 Check parameter formats and data types")
        
        if 'range_error' in error_types:
            recommendations.append("📊 Ensure parameter values are within valid ranges")
        
        # Add general recommendations
        if len(self.validation_result.warnings) > 0:
            recommendations.append("⚠️ Review warnings - they may indicate potential issues")
        
        if self.validation_result.has_critical_errors():
            recommendations.append("🚫 Fix critical errors before proceeding with the operation")
        
        if recommendations:
            # General recommendations header
            general_header = ctk.CTkFrame(self.suggestions_scrollable, fg_color="#1f538d", corner_radius=6)
            general_header.pack(fill="x", pady=(10, 5))
            
            general_header_label = ctk.CTkLabel(
                general_header,
                text="💡 General Recommendations",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="white"
            )
            general_header_label.pack(pady=8)
            
            # Recommendations list
            for recommendation in recommendations:
                rec_frame = ctk.CTkFrame(self.suggestions_scrollable, fg_color=("gray95", "gray15"), corner_radius=4)
                rec_frame.pack(fill="x", pady=(0, 3))
                
                rec_label = ctk.CTkLabel(
                    rec_frame,
                    text=recommendation,
                    font=ctk.CTkFont(size=11),
                    text_color=("gray10", "gray90"),
                    wraplength=550,
                    justify="left"
                )
                rec_label.pack(padx=15, pady=8, anchor="w")
    
    def _show_detailed_errors(self):
        """Show detailed error dialog."""
        from ui.profile_validation_error_dialog import show_validation_error_dialog
        show_validation_error_dialog(self.dialog, self.validation_result, self.profile_name)
    
    def _export_summary(self):
        """Export validation summary to file."""
        try:
            from tkinter import filedialog
            from datetime import datetime
            
            filename = filedialog.asksaveasfilename(
                title="Export Validation Summary",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialname=f"validation_summary_{self.profile_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )
            
            if filename:
                self._write_summary_to_file(filename)
                
                from ui.custom_dialogs import show_info
                show_info(self.dialog, "Export Successful", f"Validation summary exported to:\n{filename}")
        
        except Exception as e:
            from ui.custom_dialogs import show_error
            show_error(self.dialog, "Export Failed", f"Failed to export summary:\n{str(e)}")
    
    def _write_summary_to_file(self, filename: str):
        """Write validation summary to file."""
        from datetime import datetime
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("PROFILE VALIDATION SUMMARY\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Profile Name: {self.profile_name}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Validation Status: {'FAILED' if not self.validation_result.is_valid else 'PASSED'}\n\n")
            
            # Statistics
            critical_errors = len(self.validation_result.get_errors_by_severity('critical'))
            errors = len(self.validation_result.get_errors_by_severity('error'))
            warnings = len(self.validation_result.warnings)
            
            f.write("STATISTICS\n")
            f.write("-" * 20 + "\n")
            f.write(f"Critical Errors: {critical_errors}\n")
            f.write(f"Errors: {errors}\n")
            f.write(f"Warnings: {warnings}\n")
            f.write(f"Total Issues: {critical_errors + errors + warnings}\n\n")
            
            if self.validation_result.validation_summary:
                summary = self.validation_result.validation_summary
                f.write(f"Total Parameters: {summary.total_parameters}\n")
                f.write(f"Valid Parameters: {summary.valid_parameters}\n")
                if summary.total_parameters > 0:
                    success_rate = (summary.valid_parameters / summary.total_parameters) * 100
                    f.write(f"Success Rate: {success_rate:.1f}%\n")
                f.write("\n")
            
            # Recommendations
            f.write("RECOMMENDATIONS\n")
            f.write("-" * 20 + "\n")
            
            if self.validation_result.has_critical_errors():
                f.write("❌ CRITICAL: Fix critical errors before proceeding\n")
            elif errors > 0:
                f.write("⚠️  Fix errors before proceeding (or proceed with caution)\n")
            elif warnings > 0:
                f.write("ℹ️  Review warnings - operation can proceed\n")
            else:
                f.write("✅ No issues found - ready to proceed\n")
            
            f.write("\nFor detailed error information, use the 'View Details' option.\n")
    
    def _on_proceed_clicked(self):
        """Handle proceed button click."""
        self.user_choice = 'proceed'
        if self.on_proceed:
            self.on_proceed()
        self.dialog.destroy()
    
    def _on_cancel_clicked(self):
        """Handle cancel button click."""
        self.user_choice = 'cancel'
        if self.on_cancel:
            self.on_cancel()
        self.dialog.destroy()
    
    def _on_window_close(self):
        """Handle window close event."""
        self.user_choice = 'cancel'
        if self.on_cancel:
            self.on_cancel()
        self.dialog.destroy()
    
    def get_user_choice(self) -> Optional[str]:
        """Get the user's choice after dialog closes."""
        return self.user_choice
    
    def wait_for_choice(self) -> str:
        """Wait for user choice and return it."""
        self.dialog.wait_window()
        return self.user_choice or 'cancel'


def show_validation_summary_dialog(parent, validation_result: ValidationResult, 
                                 profile_name: str = "", operation_context: Dict[str, Any] = None,
                                 on_proceed: Callable = None, on_cancel: Callable = None) -> str:
    """
    Show a profile validation summary dialog and return user choice.
    
    Args:
        parent: Parent window
        validation_result: ValidationResult with errors and warnings
        profile_name: Name of the profile being validated
        operation_context: Context about the operation being performed
        on_proceed: Callback for when user chooses to proceed
        on_cancel: Callback for when user chooses to cancel
        
    Returns:
        User choice: 'proceed' or 'cancel'
    """
    dialog = ProfileValidationSummaryDialog(
        parent, validation_result, profile_name, operation_context, on_proceed, on_cancel
    )
    return dialog.wait_for_choice()