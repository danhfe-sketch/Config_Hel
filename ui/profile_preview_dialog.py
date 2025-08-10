"""
Profile Preview Dialog - Preview functionality for profile contents before loading.

This module provides profile preview functionality including:
1. Preview of profile contents before loading
2. Profile metadata display
3. Parameter categorization and organization
4. Validation status preview
5. Option to proceed with loading or cancel
"""

import customtkinter as ctk
from typing import Dict, Any, Optional, Callable, List
from services.profile_data_models import ProfileData, ValidationResult
from services.profile_validator import ProfileValidator
from services.profile_file_handler import ProfileFileHandler
import os


class ProfilePreviewDialog:
    """Preview dialog for profile contents before loading."""
    
    def __init__(self, parent, profile_path: str, on_load: Callable = None, on_cancel: Callable = None):
        """
        Initialize the profile preview dialog.
        
        Args:
            parent: Parent window
            profile_path: Path to the profile file to preview
            on_load: Callback for when user chooses to load the profile
            on_cancel: Callback for when user chooses to cancel
        """
        self.parent = parent
        self.profile_path = profile_path
        self.on_load = on_load
        self.on_cancel = on_cancel
        self.user_choice = None
        
        # Initialize services
        self.profile_handler = ProfileFileHandler()
        self.profile_validator = ProfileValidator()
        
        # Profile data
        self.profile_data = None
        self.validation_result = None
        
        # Get i18n service from parent if available
        self.i18n = parent.i18n_service if hasattr(parent, 'i18n_service') else None
        
        # Get theme service from parent
        self.theme_service = parent.theme_service if hasattr(parent, 'theme_service') else None
        
        # Create the dialog window
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Profile Preview")
        self.dialog.geometry("800x700")
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
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_window_close)
        
        # Load profile data
        self._load_profile_data()
    
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
            
            dialog_width = 800
            dialog_height = 700
            x = parent_x + (parent_width // 2) - (dialog_width // 2)
            y = parent_y + (parent_height // 2) - (dialog_height // 2)
            
            screen_width = self.dialog.winfo_screenwidth()
            screen_height = self.dialog.winfo_screenheight()
            
            x = max(0, min(x, screen_width - dialog_width))
            y = max(0, min(y, screen_height - dialog_height))
            
            self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        except Exception:
            self.dialog.geometry("800x700+200+100")
    
    def _create_ui(self):
        """Create the dialog UI elements."""
        # Configure main dialog grid
        self.dialog.grid_columnconfigure(0, weight=1)
        self.dialog.grid_rowconfigure(0, weight=1)
        
        # Create main frame
        main_frame = ctk.CTkFrame(self.dialog, corner_radius=10)
        main_frame.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(2, weight=1)  # Make content area expandable
        
        # Header section
        self._create_header(main_frame)
        
        # Profile metadata section
        self._create_metadata_section(main_frame)
        
        # Content area with tabs
        self._create_content_area(main_frame)
        
        # Action buttons
        self._create_action_buttons(main_frame)
        
        # Loading indicator (initially shown)
        self._create_loading_indicator(main_frame)
    
    def _create_header(self, parent):
        """Create the header section."""
        header_frame = ctk.CTkFrame(parent, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 15), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)
        
        # Preview icon
        icon_label = ctk.CTkLabel(
            header_frame,
            text="👁",  # Eye icon for preview
            width=40,
            height=40,
            fg_color="#1f538d",
            corner_radius=20,
            text_color="white",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        icon_label.grid(row=0, column=0, padx=(0, 15), pady=0, sticky="w")
        
        # Title and file info
        title_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_frame.grid(row=0, column=1, sticky="ew")
        title_frame.grid_columnconfigure(0, weight=1)
        
        self.title_label = ctk.CTkLabel(
            title_frame,
            text="Profile Preview",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=("gray10", "gray90")
        )
        self.title_label.grid(row=0, column=0, sticky="w")
        
        # File path
        file_name = os.path.basename(self.profile_path)
        file_label = ctk.CTkLabel(
            title_frame,
            text=f"File: {file_name}",
            font=ctk.CTkFont(size=12),
            text_color=("gray30", "gray70")
        )
        file_label.grid(row=1, column=0, sticky="w", pady=(2, 0))
        
        # File size and modification date
        try:
            file_stats = os.stat(self.profile_path)
            file_size = file_stats.st_size
            size_text = f"{file_size} bytes"
            if file_size > 1024:
                size_text = f"{file_size / 1024:.1f} KB"
            
            import datetime
            mod_time = datetime.datetime.fromtimestamp(file_stats.st_mtime)
            mod_text = mod_time.strftime("%Y-%m-%d %H:%M:%S")
            
            file_info_label = ctk.CTkLabel(
                title_frame,
                text=f"Size: {size_text} • Modified: {mod_text}",
                font=ctk.CTkFont(size=10),
                text_color=("gray40", "gray60")
            )
            file_info_label.grid(row=2, column=0, sticky="w", pady=(2, 0))
        except Exception:
            pass  # Skip file info if not available
    
    def _create_metadata_section(self, parent):
        """Create the profile metadata section."""
        self.metadata_frame = ctk.CTkFrame(parent, corner_radius=8, fg_color=("gray95", "gray15"))
        self.metadata_frame.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="ew")
        self.metadata_frame.grid_columnconfigure(0, weight=1)
        
        # Metadata will be populated when profile is loaded
        loading_label = ctk.CTkLabel(
            self.metadata_frame,
            text="Loading profile metadata...",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60")
        )
        loading_label.pack(pady=20)
    
    def _create_content_area(self, parent):
        """Create the main content area with tabs."""
        self.content_frame = ctk.CTkFrame(parent, corner_radius=8)
        self.content_frame.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(1, weight=1)
        
        # Tab buttons
        tab_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        tab_frame.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")
        
        self.tab_buttons = {}
        self.current_tab = "parameters"
        
        # Parameters tab
        self.tab_buttons["parameters"] = ctk.CTkButton(
            tab_frame,
            text="Parameters",
            command=lambda: self._switch_tab("parameters"),
            width=100,
            height=30,
            font=ctk.CTkFont(size=12),
            fg_color="#1f538d",
            hover_color="#144870"
        )
        self.tab_buttons["parameters"].pack(side="left", padx=(0, 5))
        
        # Validation tab
        self.tab_buttons["validation"] = ctk.CTkButton(
            tab_frame,
            text="Validation",
            command=lambda: self._switch_tab("validation"),
            width=100,
            height=30,
            font=ctk.CTkFont(size=12),
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40")
        )
        self.tab_buttons["validation"].pack(side="left", padx=5)
        
        # Raw data tab
        self.tab_buttons["raw"] = ctk.CTkButton(
            tab_frame,
            text="Raw Data",
            command=lambda: self._switch_tab("raw"),
            width=100,
            height=30,
            font=ctk.CTkFont(size=12),
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40")
        )
        self.tab_buttons["raw"].pack(side="left", padx=5)
        
        # Content area for tabs
        self.tab_content_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.tab_content_frame.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        self.tab_content_frame.grid_columnconfigure(0, weight=1)
        self.tab_content_frame.grid_rowconfigure(0, weight=1)
    
    def _create_action_buttons(self, parent):
        """Create the action buttons section."""
        button_frame = ctk.CTkFrame(parent, fg_color="transparent")
        button_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        
        # Left side buttons
        left_buttons = ctk.CTkFrame(button_frame, fg_color="transparent")
        left_buttons.grid(row=0, column=0, sticky="w")
        
        self.refresh_button = ctk.CTkButton(
            left_buttons,
            text="Refresh",
            command=self._refresh_preview,
            width=100,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40")
        )
        self.refresh_button.pack(side="left", padx=(0, 10))
        
        self.validate_button = ctk.CTkButton(
            left_buttons,
            text="Validate",
            command=self._validate_profile,
            width=100,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40")
        )
        self.validate_button.pack(side="left")
        
        # Right side buttons
        right_buttons = ctk.CTkFrame(button_frame, fg_color="transparent")
        right_buttons.grid(row=0, column=1, sticky="e")
        
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
        
        self.load_button = ctk.CTkButton(
            right_buttons,
            text="Load Profile",
            command=self._on_load_clicked,
            width=120,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#2AAA8A",
            hover_color="#27AE60",
            state="disabled"  # Initially disabled until profile is loaded
        )
        self.load_button.pack(side="right")
    
    def _create_loading_indicator(self, parent):
        """Create loading indicator overlay."""
        self.loading_frame = ctk.CTkFrame(parent, fg_color=("gray90", "gray20"))
        self.loading_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        
        loading_content = ctk.CTkFrame(self.loading_frame, fg_color="transparent")
        loading_content.place(relx=0.5, rely=0.5, anchor="center")
        
        # Loading spinner (using text animation)
        self.loading_label = ctk.CTkLabel(
            loading_content,
            text="⏳ Loading profile...",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("gray10", "gray90")
        )
        self.loading_label.pack(pady=20)
        
        # Progress bar
        self.loading_progress = ctk.CTkProgressBar(loading_content, width=300)
        self.loading_progress.pack(pady=10)
        self.loading_progress.set(0)
        
        # Start loading animation
        self._animate_loading()
    
    def _animate_loading(self):
        """Animate the loading indicator."""
        if hasattr(self, 'loading_frame') and self.loading_frame.winfo_exists():
            current_text = self.loading_label.cget("text")
            if "⏳" in current_text:
                self.loading_label.configure(text=current_text.replace("⏳", "⌛"))
            else:
                self.loading_label.configure(text=current_text.replace("⌛", "⏳"))
            
            # Continue animation
            self.dialog.after(500, self._animate_loading)
    
    def _hide_loading(self):
        """Hide the loading indicator."""
        if hasattr(self, 'loading_frame'):
            self.loading_frame.grid_remove()
    
    def _load_profile_data(self):
        """Load profile data in background."""
        def load_in_thread():
            try:
                # Update loading progress
                self.dialog.after(0, lambda: self.loading_progress.set(0.2))
                self.dialog.after(0, lambda: self.loading_label.configure(text="⏳ Reading profile file..."))
                
                # Load profile data
                result = self.profile_handler.read_profile_file(self.profile_path)
                
                self.dialog.after(0, lambda: self.loading_progress.set(0.6))
                self.dialog.after(0, lambda: self.loading_label.configure(text="⏳ Validating profile..."))
                
                if result.success and result.profile_data:
                    self.profile_data = result.profile_data
                    
                    # Validate profile
                    self.validation_result = self.profile_validator.validate_profile_structure(self.profile_data)
                    
                    self.dialog.after(0, lambda: self.loading_progress.set(1.0))
                    self.dialog.after(0, lambda: self.loading_label.configure(text="✅ Profile loaded successfully"))
                    
                    # Update UI on main thread
                    self.dialog.after(100, self._update_ui_with_profile_data)
                else:
                    error_msg = result.error_message or "Failed to load profile"
                    self.dialog.after(0, lambda: self._show_load_error(error_msg))
                
            except Exception as e:
                error_msg = f"Error loading profile: {str(e)}"
                self.dialog.after(0, lambda: self._show_load_error(error_msg))
        
        # Start loading in background thread
        import threading
        thread = threading.Thread(target=load_in_thread, daemon=True)
        thread.start()
    
    def _show_load_error(self, error_message: str):
        """Show error when profile loading fails."""
        self.loading_label.configure(text="❌ Failed to load profile")
        self.loading_progress.set(0)
        
        # Show error in content area
        error_frame = ctk.CTkFrame(self.loading_frame, fg_color="#E74C3C", corner_radius=8)
        error_frame.place(relx=0.5, rely=0.7, anchor="center")
        
        error_label = ctk.CTkLabel(
            error_frame,
            text=f"Error: {error_message}",
            font=ctk.CTkFont(size=12),
            text_color="white",
            wraplength=400
        )
        error_label.pack(padx=20, pady=15)
        
        # Enable only cancel button
        self.load_button.configure(state="disabled")
        self.validate_button.configure(state="disabled")
        self.refresh_button.configure(state="normal")
    
    def _update_ui_with_profile_data(self):
        """Update UI with loaded profile data."""
        self._hide_loading()
        
        # Update metadata section
        self._update_metadata_display()
        
        # Update content tabs
        self._update_content_tabs()
        
        # Enable buttons
        self.load_button.configure(state="normal")
        self.validate_button.configure(state="normal")
        
        # Update load button color based on validation
        if self.validation_result and not self.validation_result.is_valid:
            if self.validation_result.has_critical_errors():
                self.load_button.configure(
                    fg_color="#E74C3C",
                    hover_color="#C0392B",
                    text="Load (Errors Found)"
                )
            else:
                self.load_button.configure(
                    fg_color="#FF8C00",
                    hover_color="#E67E22",
                    text="Load (Warnings)"
                )
    
    def _update_metadata_display(self):
        """Update the metadata display section."""
        # Clear existing content
        for widget in self.metadata_frame.winfo_children():
            widget.destroy()
        
        if not self.profile_data:
            return
        
        # Metadata header
        header_label = ctk.CTkLabel(
            self.metadata_frame,
            text="Profile Information",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("gray10", "gray90")
        )
        header_label.pack(anchor="w", padx=15, pady=(15, 10))
        
        # Metadata grid
        metadata_grid = ctk.CTkFrame(self.metadata_frame, fg_color="transparent")
        metadata_grid.pack(fill="x", padx=15, pady=(0, 15))
        metadata_grid.grid_columnconfigure(1, weight=1)
        metadata_grid.grid_columnconfigure(3, weight=1)
        
        metadata = self.profile_data.metadata
        
        # Row 0: Profile name and creation date
        ctk.CTkLabel(metadata_grid, text="Name:", font=ctk.CTkFont(size=11, weight="bold"), 
                    text_color=("gray30", "gray70")).grid(row=0, column=0, sticky="w", padx=(0, 10), pady=2)
        ctk.CTkLabel(metadata_grid, text=metadata.profile_name or "Unknown", font=ctk.CTkFont(size=11),
                    text_color=("gray10", "gray90")).grid(row=0, column=1, sticky="w", pady=2)
        
        ctk.CTkLabel(metadata_grid, text="Created:", font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=("gray30", "gray70")).grid(row=0, column=2, sticky="w", padx=(20, 10), pady=2)
        ctk.CTkLabel(metadata_grid, text=metadata.created_date or "Unknown", font=ctk.CTkFont(size=11),
                    text_color=("gray10", "gray90")).grid(row=0, column=3, sticky="w", pady=2)
        
        # Row 1: Parameter count and app version
        ctk.CTkLabel(metadata_grid, text="Parameters:", font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=("gray30", "gray70")).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=2)
        ctk.CTkLabel(metadata_grid, text=str(metadata.parameter_count), font=ctk.CTkFont(size=11),
                    text_color=("gray10", "gray90")).grid(row=1, column=1, sticky="w", pady=2)
        
        ctk.CTkLabel(metadata_grid, text="App Version:", font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=("gray30", "gray70")).grid(row=1, column=2, sticky="w", padx=(20, 10), pady=2)
        ctk.CTkLabel(metadata_grid, text=metadata.app_version or "Unknown", font=ctk.CTkFont(size=11),
                    text_color=("gray10", "gray90")).grid(row=1, column=3, sticky="w", pady=2)
        
        # Row 2: Device IMEI and version (if available)
        if metadata.device_imei:
            ctk.CTkLabel(metadata_grid, text="Device IMEI:", font=ctk.CTkFont(size=11, weight="bold"),
                        text_color=("gray30", "gray70")).grid(row=2, column=0, sticky="w", padx=(0, 10), pady=2)
            ctk.CTkLabel(metadata_grid, text=metadata.device_imei, font=ctk.CTkFont(size=11),
                        text_color=("gray10", "gray90")).grid(row=2, column=1, sticky="w", pady=2)
        
        if metadata.device_version:
            ctk.CTkLabel(metadata_grid, text="Device Version:", font=ctk.CTkFont(size=11, weight="bold"),
                        text_color=("gray30", "gray70")).grid(row=2, column=2, sticky="w", padx=(20, 10), pady=2)
            ctk.CTkLabel(metadata_grid, text=metadata.device_version, font=ctk.CTkFont(size=11),
                        text_color=("gray10", "gray90")).grid(row=2, column=3, sticky="w", pady=2)
        
        # Validation status indicator
        if self.validation_result:
            status_frame = ctk.CTkFrame(self.metadata_frame, corner_radius=6)
            status_frame.pack(fill="x", padx=15, pady=(10, 15))
            
            if self.validation_result.is_valid:
                status_color = "#2AAA8A"
                status_text = "✅ Profile validation passed"
            elif self.validation_result.has_critical_errors():
                status_color = "#E74C3C"
                status_text = f"❌ Critical errors found ({len(self.validation_result.get_errors_by_severity('critical'))} issues)"
            else:
                status_color = "#FF8C00"
                error_count = len(self.validation_result.get_errors_by_severity('error'))
                warning_count = len(self.validation_result.warnings)
                status_text = f"⚠️ Issues found ({error_count} errors, {warning_count} warnings)"
            
            status_frame.configure(fg_color=status_color)
            
            status_label = ctk.CTkLabel(
                status_frame,
                text=status_text,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="white"
            )
            status_label.pack(pady=8)
    
    def _update_content_tabs(self):
        """Update the content tabs with profile data."""
        # Clear existing content
        for widget in self.tab_content_frame.winfo_children():
            widget.destroy()
        
        # Show current tab content
        self._switch_tab(self.current_tab)
    
    def _switch_tab(self, tab_name: str):
        """Switch to a different tab."""
        self.current_tab = tab_name
        
        # Update tab button styles
        for name, button in self.tab_buttons.items():
            if name == tab_name:
                button.configure(fg_color="#1f538d", hover_color="#144870")
            else:
                button.configure(fg_color=("gray70", "gray30"), hover_color=("gray60", "gray40"))
        
        # Clear content area
        for widget in self.tab_content_frame.winfo_children():
            widget.destroy()
        
        # Show selected tab content
        if tab_name == "parameters":
            self._show_parameters_tab()
        elif tab_name == "validation":
            self._show_validation_tab()
        elif tab_name == "raw":
            self._show_raw_data_tab()
    
    def _show_parameters_tab(self):
        """Show the parameters tab content."""
        if not self.profile_data:
            return
        
        # Create scrollable frame for parameters
        params_scrollable = ctk.CTkScrollableFrame(self.tab_content_frame)
        params_scrollable.grid(row=0, column=0, sticky="nsew")
        params_scrollable.grid_columnconfigure(0, weight=1)
        
        parameters = self.profile_data.device_parameters
        
        if not parameters:
            no_params_label = ctk.CTkLabel(
                params_scrollable,
                text="No parameters found in profile",
                font=ctk.CTkFont(size=12),
                text_color=("gray40", "gray60")
            )
            no_params_label.pack(pady=50)
            return
        
        # Group parameters by category (if possible)
        categorized_params = self._categorize_parameters(parameters)
        
        for category, params in categorized_params.items():
            if not params:
                continue
            
            # Category header
            category_frame = ctk.CTkFrame(params_scrollable, fg_color="#1f538d", corner_radius=6)
            category_frame.pack(fill="x", pady=(10, 5))
            
            category_label = ctk.CTkLabel(
                category_frame,
                text=f"{category} ({len(params)} parameters)",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="white"
            )
            category_label.pack(pady=8)
            
            # Parameters in this category
            for param_name, param_value in params.items():
                param_frame = ctk.CTkFrame(params_scrollable, fg_color=("gray95", "gray15"), corner_radius=4)
                param_frame.pack(fill="x", pady=2)
                param_frame.grid_columnconfigure(1, weight=1)
                
                # Parameter name
                name_label = ctk.CTkLabel(
                    param_frame,
                    text=param_name,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=("gray10", "gray90"),
                    width=200
                )
                name_label.grid(row=0, column=0, padx=15, pady=8, sticky="w")
                
                # Parameter value
                value_text = str(param_value)
                if len(value_text) > 50:
                    value_text = value_text[:47] + "..."
                
                value_label = ctk.CTkLabel(
                    param_frame,
                    text=value_text,
                    font=ctk.CTkFont(size=11),
                    text_color=("gray20", "gray80")
                )
                value_label.grid(row=0, column=1, padx=15, pady=8, sticky="w")
    
    def _show_validation_tab(self):
        """Show the validation tab content."""
        if not self.validation_result:
            no_validation_label = ctk.CTkLabel(
                self.tab_content_frame,
                text="No validation results available",
                font=ctk.CTkFont(size=12),
                text_color=("gray40", "gray60")
            )
            no_validation_label.pack(pady=50)
            return
        
        # Create scrollable frame for validation results
        validation_scrollable = ctk.CTkScrollableFrame(self.tab_content_frame)
        validation_scrollable.grid(row=0, column=0, sticky="nsew")
        validation_scrollable.grid_columnconfigure(0, weight=1)
        
        # Validation summary
        summary_frame = ctk.CTkFrame(validation_scrollable, fg_color=("gray95", "gray15"), corner_radius=6)
        summary_frame.pack(fill="x", pady=(0, 15))
        
        summary_label = ctk.CTkLabel(
            summary_frame,
            text="Validation Summary",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("gray10", "gray90")
        )
        summary_label.pack(anchor="w", padx=15, pady=(15, 10))
        
        # Summary stats
        critical_errors = len(self.validation_result.get_errors_by_severity('critical'))
        errors = len(self.validation_result.get_errors_by_severity('error'))
        warnings = len(self.validation_result.warnings)
        
        summary_text = f"Status: {'PASSED' if self.validation_result.is_valid else 'FAILED'}\n"
        summary_text += f"Critical Errors: {critical_errors}\n"
        summary_text += f"Errors: {errors}\n"
        summary_text += f"Warnings: {warnings}"
        
        summary_details = ctk.CTkLabel(
            summary_frame,
            text=summary_text,
            font=ctk.CTkFont(size=11),
            text_color=("gray20", "gray80"),
            justify="left"
        )
        summary_details.pack(anchor="w", padx=15, pady=(0, 15))
        
        # Show errors and warnings
        all_issues = []
        for error in self.validation_result.errors:
            all_issues.append(('error', error))
        for warning in self.validation_result.warnings:
            all_issues.append(('warning', warning))
        
        if all_issues:
            issues_label = ctk.CTkLabel(
                validation_scrollable,
                text="Issues Found:",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=("gray10", "gray90")
            )
            issues_label.pack(anchor="w", pady=(0, 10))
            
            for issue_type, issue in all_issues[:20]:  # Show first 20 issues
                issue_frame = ctk.CTkFrame(validation_scrollable, fg_color=("gray95", "gray15"), corner_radius=4)
                issue_frame.pack(fill="x", pady=2)
                
                # Issue type and location
                type_color = "#E74C3C" if issue_type == 'error' else "#F39C12"
                type_text = f"{'ERROR' if issue_type == 'error' else 'WARNING'}: {getattr(issue, 'location', 'Unknown location')}"
                
                type_label = ctk.CTkLabel(
                    issue_frame,
                    text=type_text,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    text_color=type_color
                )
                type_label.pack(anchor="w", padx=15, pady=(8, 2))
                
                # Issue message
                message_label = ctk.CTkLabel(
                    issue_frame,
                    text=getattr(issue, 'message', 'No message'),
                    font=ctk.CTkFont(size=10),
                    text_color=("gray20", "gray80"),
                    wraplength=700,
                    justify="left"
                )
                message_label.pack(anchor="w", padx=15, pady=(0, 8))
            
            if len(all_issues) > 20:
                more_label = ctk.CTkLabel(
                    validation_scrollable,
                    text=f"... and {len(all_issues) - 20} more issues",
                    font=ctk.CTkFont(size=10),
                    text_color=("gray40", "gray60")
                )
                more_label.pack(pady=10)
        else:
            success_frame = ctk.CTkFrame(validation_scrollable, fg_color="#2AAA8A", corner_radius=6)
            success_frame.pack(fill="x", pady=10)
            
            success_label = ctk.CTkLabel(
                success_frame,
                text="✅ No validation issues found!",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="white"
            )
            success_label.pack(pady=15)
    
    def _show_raw_data_tab(self):
        """Show the raw data tab content."""
        if not self.profile_data:
            return
        
        # Create text widget for raw data
        raw_text = ctk.CTkTextbox(
            self.tab_content_frame,
            font=ctk.CTkFont(family="Courier", size=10),
            wrap="none"
        )
        raw_text.grid(row=0, column=0, sticky="nsew")
        
        # Read and display raw file content
        try:
            with open(self.profile_path, 'r', encoding='utf-8') as f:
                content = f.read()
                raw_text.insert("1.0", content)
        except Exception as e:
            raw_text.insert("1.0", f"Error reading file: {str(e)}")
        
        # Make read-only
        raw_text.configure(state="disabled")
    
    def _categorize_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Categorize parameters by type/function."""
        categories = {
            "Network & APN": {},
            "Server Configuration": {},
            "Timing & Intervals": {},
            "Device Settings": {},
            "Alert & Notification": {},
            "Other Parameters": {}
        }
        
        # Define parameter categories
        network_keywords = ['apn', 'network', 'gsm', 'gprs', 'lte', 'operator', 'carrier']
        server_keywords = ['server', 'host', 'port', 'url', 'ip', 'domain', 'protocol']
        timing_keywords = ['time', 'interval', 'period', 'delay', 'timeout', 'heartbeat', 'hbt']
        device_keywords = ['device', 'imei', 'version', 'config', 'mode', 'status']
        alert_keywords = ['alert', 'alarm', 'notification', 'sms', 'call', 'emergency']
        
        for param_name, param_value in parameters.items():
            param_lower = param_name.lower()
            
            if any(keyword in param_lower for keyword in network_keywords):
                categories["Network & APN"][param_name] = param_value
            elif any(keyword in param_lower for keyword in server_keywords):
                categories["Server Configuration"][param_name] = param_value
            elif any(keyword in param_lower for keyword in timing_keywords):
                categories["Timing & Intervals"][param_name] = param_value
            elif any(keyword in param_lower for keyword in device_keywords):
                categories["Device Settings"][param_name] = param_value
            elif any(keyword in param_lower for keyword in alert_keywords):
                categories["Alert & Notification"][param_name] = param_value
            else:
                categories["Other Parameters"][param_name] = param_value
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}
    
    def _refresh_preview(self):
        """Refresh the profile preview."""
        # Show loading indicator
        self._create_loading_indicator(self.dialog.winfo_children()[0])
        
        # Reload profile data
        self._load_profile_data()
    
    def _validate_profile(self):
        """Run validation on the profile."""
        if not self.profile_data:
            return
        
        # Show validation progress
        self.validate_button.configure(text="Validating...", state="disabled")
        
        def validate_in_thread():
            try:
                # Re-run validation
                self.validation_result = self.profile_validator.validate_profile_structure(self.profile_data)
                
                # Update UI on main thread
                self.dialog.after(0, self._validation_complete)
            except Exception as e:
                error_msg = f"Validation error: {str(e)}"
                self.dialog.after(0, lambda: self._validation_error(error_msg))
        
        import threading
        thread = threading.Thread(target=validate_in_thread, daemon=True)
        thread.start()
    
    def _validation_complete(self):
        """Handle validation completion."""
        self.validate_button.configure(text="Validate", state="normal")
        
        # Update metadata display
        self._update_metadata_display()
        
        # Switch to validation tab if not already there
        if self.current_tab != "validation":
            self._switch_tab("validation")
        
        # Show validation summary dialog
        from ui.profile_validation_summary_dialog import show_validation_summary_dialog
        show_validation_summary_dialog(
            self.dialog, 
            self.validation_result, 
            self.profile_data.metadata.profile_name
        )
    
    def _validation_error(self, error_message: str):
        """Handle validation error."""
        self.validate_button.configure(text="Validate", state="normal")
        
        from ui.custom_dialogs import show_error
        show_error(self.dialog, "Validation Error", error_message)
    
    def _on_load_clicked(self):
        """Handle load button click."""
        self.user_choice = 'load'
        if self.on_load:
            self.on_load(self.profile_data, self.validation_result)
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


def show_profile_preview_dialog(parent, profile_path: str, on_load: Callable = None, 
                               on_cancel: Callable = None) -> str:
    """
    Show a profile preview dialog and return user choice.
    
    Args:
        parent: Parent window
        profile_path: Path to the profile file to preview
        on_load: Callback for when user chooses to load the profile
        on_cancel: Callback for when user chooses to cancel
        
    Returns:
        User choice: 'load' or 'cancel'
    """
    dialog = ProfilePreviewDialog(parent, profile_path, on_load, on_cancel)
    return dialog.wait_for_choice()