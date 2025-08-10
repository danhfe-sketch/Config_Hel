"""
Profile Progress Dialog - Specialized progress dialogs for profile operations.

This module provides progress dialogs specifically designed for profile operations
including device-to-profile and profile-to-device operations with cancellation support.
"""

import customtkinter as ctk
import threading
import time
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class ProfileProgressInfo:
    """Information about profile operation progress with enhanced tracking."""
    operation_type: str  # 'device_to_profile' or 'profile_to_device'
    current_step: int    # Overall step (1-4)
    total_steps: int     # Total steps (4)
    step_name: str       # Step name (e.g., "Deploying Configuration")
    current_parameter: int    # Current parameter being processed (index)
    total_parameters: int     # Total parameters to process
    parameter_name: str       # Name of current parameter
    status_message: str       # Detailed status message
    progress_percentage: float # Overall progress percentage
    
    # Enhanced step-level tracking
    step_progress_percentage: float = 0.0  # Current step progress percentage
    step_description: str = ""  # Detailed description of current step
    step_start_time: Optional[float] = None  # Step start timestamp
    step_estimated_duration: float = 0.0  # Estimated step duration in seconds
    
    # Enhanced parameter-level tracking
    parameter_index: int = 0  # Current parameter index (1-based for display)
    parameter_value: str = ""  # Current parameter value being processed
    parameter_type: str = ""  # Type of parameter (e.g., "APN", "Server", "Timing")
    parameter_validation_status: str = ""  # Validation status of parameter
    parameter_start_time: Optional[float] = None  # Parameter processing start time
    parameter_estimated_duration: float = 0.0  # Estimated parameter processing time
    
    # Profile metadata
    profile_name: str = ""  # Name of the profile being processed
    profile_created: str = ""  # Creation date of the profile
    profile_device_imei: str = ""  # Original device IMEI
    profile_parameter_count: int = 0  # Number of parameters in the profile
    profile_version: str = ""  # Profile version information
    profile_description: str = ""  # Profile description
    
    # Operation timing and performance
    operation_start_time: Optional[float] = None  # Operation start timestamp
    estimated_time_remaining: str = ""  # Estimated time remaining
    operation_speed: str = ""  # Current operation speed (params/sec)
    average_parameter_time: float = 0.0  # Average time per parameter in seconds
    
    # Enhanced status tracking
    current_operation: str = ""  # Current specific operation being performed
    last_successful_parameter: str = ""  # Last successfully processed parameter
    error_count: int = 0  # Number of errors encountered
    retry_count: int = 0  # Number of retries performed
    
    # Control flags
    can_cancel: bool = True
    is_completed: bool = False
    is_cancelled: bool = False
    is_paused: bool = False
    has_errors: bool = False


class ProfileProgressDialog:
    """Progress dialog specifically for profile operations."""
    
    def __init__(self, parent, title: str, operation_type: str):
        """
        Initialize the profile progress dialog.
        
        Args:
            parent: Parent window
            title: Dialog title
            operation_type: Type of operation ('device_to_profile' or 'profile_to_device')
        """
        self.parent = parent
        self.operation_type = operation_type
        self.is_cancelled = False
        self.cancel_callback = None
        
        # Timeout handling
        self.operation_timeout = 300.0  # 5 minutes default timeout
        self.operation_start_time = None
        self.timeout_check_interval = 5000  # Check every 5 seconds
        self.timeout_after_id = None
        
        # Get i18n service from parent if available
        self.i18n = parent.i18n_service if hasattr(parent, 'i18n_service') else None
        
        # Get theme service from parent to ensure consistent theming
        self.theme_service = parent.theme_service if hasattr(parent, 'theme_service') else None
        
        # Create the dialog window with improved sizing
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("550x450")  # Optimized size for better content layout
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Ensure dialog uses the same theme as the application
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
            # Get current theme from theme service
            current_theme = self.theme_service.get_current_theme()
            ctk.set_appearance_mode(current_theme)
        else:
            # Fallback to checking parent's theme or default to dark
            if hasattr(self.parent, 'theme_service'):
                current_theme = self.parent.theme_service.get_current_theme()
                ctk.set_appearance_mode(current_theme)
            else:
                ctk.set_appearance_mode("dark")
        
        # Ensure blue color theme consistency
        ctk.set_default_color_theme("blue")
    
    def _center_dialog(self):
        """Center the dialog on the parent window with improved positioning."""
        try:
            # Update parent window to get accurate dimensions
            self.parent.update_idletasks()
            
            # Get parent window position and size
            parent_x = self.parent.winfo_x()
            parent_y = self.parent.winfo_y()
            parent_width = self.parent.winfo_width()
            parent_height = self.parent.winfo_height()
            
            # Calculate center position (accounting for new dialog size)
            dialog_width = 550
            dialog_height = 450
            x = parent_x + (parent_width // 2) - (dialog_width // 2)
            y = parent_y + (parent_height // 2) - (dialog_height // 2)
            
            # Ensure dialog stays within screen bounds
            screen_width = self.dialog.winfo_screenwidth()
            screen_height = self.dialog.winfo_screenheight()
            
            x = max(0, min(x, screen_width - dialog_width))
            y = max(0, min(y, screen_height - dialog_height))
            
            self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        except Exception:
            # Fallback to simple centering if parent info is not available
            self.dialog.geometry("550x450+400+200")
    
    def _create_ui(self):
        """Create the dialog UI elements with improved layout and theming."""
        # Configure main dialog grid
        self.dialog.grid_columnconfigure(0, weight=1)
        self.dialog.grid_rowconfigure(0, weight=1)
        
        # Create main frame with consistent application styling
        main_frame = ctk.CTkFrame(self.dialog, corner_radius=10)
        main_frame.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Header section with improved styling
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 15), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)
        
        # Operation icon with consistent blue theme
        icon_label = ctk.CTkLabel(
            header_frame,
            text="⚙",  # Gear icon for operations
            width=36,
            height=36,
            fg_color="#1f538d",  # Darker blue for better contrast
            corner_radius=18,
            text_color="white",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        icon_label.grid(row=0, column=0, padx=(0, 15), pady=0, sticky="w")
        
        # Operation title with consistent font styling
        if self.i18n:
            operation_titles = {
                'device_to_profile': self.i18n.get('load_from_device', 'Load Profile from Device'),
                'profile_to_device': self.i18n.get('load_profile_to_device', 'Load Profile to Device')
            }
        else:
            operation_titles = {
                'device_to_profile': 'Load Profile from Device',
                'profile_to_device': 'Load Profile to Device'
            }
        title_text = operation_titles.get(self.operation_type, 'Profile Operation')
        
        self.title_label = ctk.CTkLabel(
            header_frame, 
            text=title_text,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=("gray10", "gray90")  # Consistent with app theme
        )
        self.title_label.grid(row=0, column=1, padx=0, pady=0, sticky="w")
        
        # Profile information section with improved styling
        info_frame = ctk.CTkFrame(main_frame, corner_radius=8, fg_color=("gray95", "gray15"))
        info_frame.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="ew")
        info_frame.grid_columnconfigure(1, weight=1)
        
        # Information icon with consistent styling
        info_icon = ctk.CTkLabel(
            info_frame,
            text="ℹ",  # Info icon
            width=32,
            height=32,
            fg_color="#1f538d",  # Consistent blue theme
            corner_radius=16,
            text_color="white",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        info_icon.grid(row=0, column=0, padx=15, pady=15, sticky="nw")
        
        # Profile information content frame
        profile_info_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        profile_info_frame.grid(row=0, column=1, padx=(0, 15), pady=15, sticky="ew")
        profile_info_frame.grid_columnconfigure(0, weight=1)
        
        # Profile information header
        profile_info_text = "Profile Information:"
        if self.i18n:
            profile_info_text = self.i18n.get('profile_information', 'Profile Information:')
            
        profile_info_label = ctk.CTkLabel(
            profile_info_frame,
            text=profile_info_text,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("gray10", "gray90")
        )
        profile_info_label.grid(row=0, column=0, sticky="w", pady=(0, 8))
        
        # Profile details with improved formatting
        self.profile_details = ctk.CTkLabel(
            profile_info_frame,
            text="Name: [Profile Name]\nCreated: [Date]\nOriginal Device IMEI: [IMEI]\nParameters: [Count]",
            font=ctk.CTkFont(size=12),
            justify="left",
            text_color=("gray20", "gray80")
        )
        self.profile_details.grid(row=1, column=0, sticky="w")
        
        # Description text with improved styling and spacing
        description_text = ctk.CTkLabel(
            main_frame,
            text="This will deploy the profile configuration to the connected device.\n\nThe device must be connected and responding.\nExisting device settings will be overwritten.",
            font=ctk.CTkFont(size=12),
            justify="left",
            wraplength=500,
            text_color=("gray30", "gray70")
        )
        description_text.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="w")
        
        # Step indicator frame with improved styling
        step_frame = ctk.CTkFrame(main_frame, corner_radius=8, fg_color=("gray95", "gray15"))
        step_frame.grid(row=3, column=0, padx=20, pady=(0, 15), sticky="ew")
        
        # Create step indicators with better visual design
        self.step_indicators = []
        step_names = ["Prepare", "Connect", "Deploy", "Verify"]
        
        for i, name in enumerate(step_names):
            # Step container with improved spacing
            step_container = ctk.CTkFrame(step_frame, fg_color="transparent")
            step_container.grid(row=0, column=i, padx=8, pady=12, sticky="ew")
            step_frame.grid_columnconfigure(i, weight=1)
            
            # Step number circle with consistent theming
            step_circle = ctk.CTkLabel(
                step_container,
                text=str(i+1),
                width=28,
                height=28,
                fg_color=("gray60", "gray40"),  # Inactive state
                corner_radius=14,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=("white", "white")
            )
            step_circle.grid(row=0, column=0, pady=(0, 5), sticky="n")
            
            # Step name with consistent font
            step_name = ctk.CTkLabel(
                step_container,
                text=name,
                font=ctk.CTkFont(size=11),
                text_color=("gray40", "gray60")
            )
            step_name.grid(row=1, column=0, sticky="n")
            
            # Store references
            self.step_indicators.append((step_circle, step_name))
        
        # Current parameter label with improved styling
        self.parameter_label = ctk.CTkLabel(
            main_frame,
            text="Initializing...",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("gray10", "gray90")
        )
        self.parameter_label.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="w")
        
        # Progress section with enhanced dual-level progress display
        progress_section = ctk.CTkFrame(main_frame, fg_color="transparent")
        progress_section.grid(row=5, column=0, padx=20, pady=(0, 15), sticky="ew")
        progress_section.grid_columnconfigure(0, weight=1)
        
        # Overall progress label
        overall_progress_label = ctk.CTkLabel(
            progress_section,
            text="Overall Progress",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("gray30", "gray70")
        )
        overall_progress_label.grid(row=0, column=0, sticky="w", pady=(0, 3))
        
        # Overall progress bar with consistent styling
        self.progress_bar = ctk.CTkProgressBar(
            progress_section, 
            height=14,
            corner_radius=7,
            progress_color="#1f538d"  # Consistent blue theme
        )
        self.progress_bar.grid(row=1, column=0, pady=(0, 8), sticky="ew")
        self.progress_bar.set(0)
        
        # Step progress label
        step_progress_label = ctk.CTkLabel(
            progress_section,
            text="Current Step Progress",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("gray30", "gray70")
        )
        step_progress_label.grid(row=2, column=0, sticky="w", pady=(5, 3))
        
        # Step progress bar for current step details
        self.step_progress_bar = ctk.CTkProgressBar(
            progress_section,
            height=10,
            corner_radius=5,
            progress_color="#2AAA8A"  # Green for step progress
        )
        self.step_progress_bar.grid(row=3, column=0, pady=(0, 10), sticky="ew")
        self.step_progress_bar.set(0)
        
        # Progress details frame with better spacing
        progress_details = ctk.CTkFrame(progress_section, fg_color="transparent")
        progress_details.grid(row=4, column=0, sticky="ew")
        progress_details.grid_columnconfigure(0, weight=1)
        progress_details.grid_columnconfigure(1, weight=0)
        
        # Progress text with improved formatting
        self.progress_text = ctk.CTkLabel(
            progress_details,
            text="Step 0/0 • Parameter 0/0",
            font=ctk.CTkFont(size=11),
            text_color=("gray30", "gray70")
        )
        self.progress_text.grid(row=0, column=0, sticky="w")
        
        # Percentage display with emphasis
        self.percentage_text = ctk.CTkLabel(
            progress_details,
            text="0%",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#1f538d"  # Blue theme for emphasis
        )
        self.percentage_text.grid(row=0, column=1, sticky="e")
        
        # Status and timing information frame
        status_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        status_frame.grid(row=6, column=0, padx=20, pady=(0, 15), sticky="ew")
        status_frame.grid_columnconfigure(0, weight=1)
        
        # Status message with improved styling
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="Starting operation...",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60"),
            wraplength=500,
            justify="left"
        )
        self.status_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        # Time and speed information
        self.timing_label = ctk.CTkLabel(
            status_frame,
            text="",
            font=ctk.CTkFont(size=10),
            text_color=("gray50", "gray50"),
            justify="left"
        )
        self.timing_label.grid(row=1, column=0, sticky="w")
        
        # Button frame with improved layout
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.grid(row=7, column=0, padx=20, pady=(0, 20), sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=0)
        button_frame.grid_columnconfigure(2, weight=0)
        
        # Continue question with consistent styling
        continue_label = ctk.CTkLabel(
            button_frame,
            text="Continue?",
            font=ctk.CTkFont(size=12),
            text_color=("gray10", "gray90")
        )
        continue_label.grid(row=0, column=0, padx=0, pady=0, sticky="w")
        
        # Cancel button with consistent styling
        cancel_text = "Não"
        if self.i18n:
            cancel_text = self.i18n.get('no', 'Não')
            
        self.cancel_button = ctk.CTkButton(
            button_frame,
            text=cancel_text,
            command=self._on_cancel,
            width=90,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40")
        )
        self.cancel_button.grid(row=0, column=2, padx=(15, 0), pady=0, sticky="e")
        
        # Confirm button with primary styling
        confirm_text = "Sim"
        if self.i18n:
            confirm_text = self.i18n.get('yes', 'Sim')
            
        self.confirm_button = ctk.CTkButton(
            button_frame,
            text=confirm_text,
            command=self._on_confirm,
            width=90,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#1f538d",
            hover_color="#144870"
        )
        self.confirm_button.grid(row=0, column=1, padx=(10, 0), pady=0, sticky="e")
        
        # Close button with consistent styling (initially hidden)
        close_text = "Close"
        if self.i18n:
            close_text = self.i18n.get('close', 'Close')
            
        self.close_button = ctk.CTkButton(
            button_frame,
            text=close_text,
            command=self._on_close,
            width=90,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color="#1f538d",
            hover_color="#144870"
        )
        # Don't grid the close button initially
    
    def update_progress(self, progress_info: ProfileProgressInfo):
        """
        Update the progress dialog with new information.
        
        Args:
            progress_info: Progress information
        """
        # Update profile information if available
        if hasattr(self, 'profile_details'):
            profile_name = progress_info.profile_name or "[Profile Name]"
            profile_created = progress_info.profile_created or "[Date]"
            profile_device_imei = progress_info.profile_device_imei or "[IMEI]"
            profile_parameter_count = progress_info.profile_parameter_count or "[Count]"
            
            profile_text = (
                f"Name: {profile_name}\n"
                f"Created: {profile_created}\n"
                f"Original Device IMEI: {profile_device_imei}\n"
                f"Parameters: {profile_parameter_count}"
            )
            self.profile_details.configure(text=profile_text)
        
        # Hide confirmation buttons if we're in progress mode
        if hasattr(self, 'confirm_button') and progress_info.current_step > 0:
            self.confirm_button.grid_remove()
            self.cancel_button.grid_remove()
            
            # Show cancel button in progress mode
            self.cancel_button.configure(text="Cancel")
            self.cancel_button.grid(row=0, column=2, padx=(10, 0), pady=0, sticky="e")
        
        # Update step indicators with consistent theming
        if hasattr(self, 'step_indicators'):
            current_step = progress_info.current_step
            for i, (circle, name) in enumerate(self.step_indicators):
                step_num = i + 1
                
                if step_num < current_step:
                    # Completed step - green with checkmark
                    circle.configure(fg_color="#2AAA8A", text="✓", text_color="white")
                    name.configure(text_color="#2AAA8A", font=ctk.CTkFont(size=11, weight="bold"))
                elif step_num == current_step:
                    # Current step - blue theme
                    circle.configure(fg_color="#1f538d", text=str(step_num), text_color="white")
                    name.configure(text_color="#1f538d", font=ctk.CTkFont(size=11, weight="bold"))
                else:
                    # Future step - gray inactive
                    circle.configure(fg_color=("gray60", "gray40"), text=str(step_num), text_color="white")
                    name.configure(text_color=("gray40", "gray60"), font=ctk.CTkFont(size=11))
        
        # Update overall progress bar
        if progress_info.total_steps > 0:
            # Use the provided progress percentage if available, otherwise calculate from steps
            if progress_info.progress_percentage > 0:
                self.progress_bar.set(progress_info.progress_percentage)
            else:
                progress_value = progress_info.current_step / progress_info.total_steps
                self.progress_bar.set(progress_value)
        
        # Update step progress bar
        if hasattr(self, 'step_progress_bar'):
            if progress_info.step_progress_percentage > 0:
                self.step_progress_bar.set(progress_info.step_progress_percentage)
            elif progress_info.total_parameters > 0 and progress_info.parameter_index > 0:
                # Calculate step progress based on parameter progress
                step_progress = progress_info.parameter_index / progress_info.total_parameters
                self.step_progress_bar.set(step_progress)
            else:
                # Default step progress based on overall progress within current step
                if progress_info.total_steps > 0:
                    step_base = (progress_info.current_step - 1) / progress_info.total_steps
                    step_size = 1.0 / progress_info.total_steps
                    current_step_progress = (progress_info.progress_percentage - step_base) / step_size
                    self.step_progress_bar.set(max(0, min(1, current_step_progress)))
        
        # Update progress text with comprehensive information
        if progress_info.total_parameters > 0:
            # Show detailed progress with parameter count
            progress_text = f"Step {progress_info.current_step}/{progress_info.total_steps}"
            if progress_info.parameter_index > 0:
                progress_text += f" • Parameter {progress_info.parameter_index}/{progress_info.total_parameters}"
            
            # Add operation speed if available
            if progress_info.operation_speed:
                progress_text += f" • {progress_info.operation_speed}"
                
            self.progress_text.configure(text=progress_text)
        else:
            # Basic step progress
            progress_text = f"Step {progress_info.current_step}/{progress_info.total_steps}"
            if progress_info.operation_speed:
                progress_text += f" • {progress_info.operation_speed}"
            self.progress_text.configure(text=progress_text)
        
        # Update percentage display with consistent theming
        percentage = int(progress_info.progress_percentage * 100)
        if hasattr(self, 'percentage_text'):
            self.percentage_text.configure(text=f"{percentage}%")
            
            # Change color based on progress with consistent theme colors
            if percentage < 30:
                color = "#FF8C00"  # Orange for early progress
            elif percentage < 70:
                color = "#1f538d"  # Blue theme for mid progress
            else:
                color = "#2AAA8A"  # Green for near completion
                
            self.percentage_text.configure(text_color=color)
        
        # Update current parameter with enhanced information display
        if progress_info.parameter_name and progress_info.parameter_index > 0:
            # Show descriptive parameter name with count
            parameter_text = f"Configuring Parameter {progress_info.parameter_index}/{progress_info.total_parameters}: {progress_info.parameter_name}"
            if progress_info.parameter_value:
                parameter_text += f" = {progress_info.parameter_value}"
            self.parameter_label.configure(text=parameter_text)
        elif progress_info.step_name and progress_info.current_parameter:
            # Fallback to step name with current parameter
            parameter_text = f"{progress_info.step_name}: {progress_info.current_parameter}"
            self.parameter_label.configure(text=parameter_text)
        elif progress_info.current_parameter:
            # Basic parameter processing message
            parameter_text = f"Processing: {progress_info.current_parameter}"
            self.parameter_label.configure(text=parameter_text)
        elif progress_info.step_name:
            # Just step name
            self.parameter_label.configure(text=progress_info.step_name)
        else:
            # Default message
            self.parameter_label.configure(text="Processing...")
        
        # Update status message with enhanced formatting
        if progress_info.status_message:
            self.status_label.configure(text=progress_info.status_message)
        else:
            # Default status based on current step
            default_status = self._get_default_status_message(progress_info)
            self.status_label.configure(text=default_status)
        
        # Update timing information if available
        if hasattr(self, 'timing_label'):
            timing_parts = []
            
            if progress_info.estimated_time_remaining:
                timing_parts.append(f"ETA: {progress_info.estimated_time_remaining}")
            
            if progress_info.operation_speed:
                timing_parts.append(f"Speed: {progress_info.operation_speed}")
            
            # Add step progress percentage if available and different from overall
            if (progress_info.step_progress_percentage > 0 and 
                abs(progress_info.step_progress_percentage - progress_info.progress_percentage) > 0.01):
                step_percent = int(progress_info.step_progress_percentage * 100)
                timing_parts.append(f"Step Progress: {step_percent}%")
            
            timing_text = " • ".join(timing_parts) if timing_parts else ""
            self.timing_label.configure(text=timing_text)
        
        # Start timeout monitoring if this is the first progress update
        if self.operation_start_time is None and progress_info.current_step > 0:
            self.start_timeout_monitoring()
        
        # Also start timeout monitoring if explicitly requested and not already started
        if (self.operation_start_time is None and 
            hasattr(progress_info, 'start_timeout_monitoring') and 
            progress_info.start_timeout_monitoring):
            self.start_timeout_monitoring()
        
        # Handle completion
        if progress_info.is_completed:
            self._on_completion(progress_info)
        
        # Handle cancellation
        if progress_info.is_cancelled:
            self._on_cancellation()
    
    def _on_completion(self, progress_info: ProfileProgressInfo):
        """Handle operation completion."""
        # Stop timeout monitoring
        self.stop_timeout_monitoring()
        
        # Update step indicators to show completion with consistent theming
        if hasattr(self, 'step_indicators'):
            for i, (circle, name) in enumerate(self.step_indicators):
                circle.configure(fg_color="#2AAA8A", text="✓", text_color="white")
                name.configure(text_color="#2AAA8A", font=ctk.CTkFont(size=11, weight="bold"))
        
        # Update UI for completion
        self.progress_bar.set(1.0)
        self.progress_bar.configure(progress_color="#2AAA8A")  # Green for success
        
        completion_title = "Operation Completed"
        if self.i18n:
            completion_title = self.i18n.get('operation_completed', completion_title)
        
        self.parameter_label.configure(text=completion_title, text_color="#2AAA8A")
        
        if progress_info.status_message:
            self.status_label.configure(text=progress_info.status_message, text_color="#2AAA8A")
        else:
            success_messages = {
                'device_to_profile': 'Configuration loaded from device successfully',
                'profile_to_device': 'Profile deployed to device successfully'
            }
            success_message = success_messages.get(self.operation_type, 'Operation completed successfully')
            if self.i18n:
                success_message = self.i18n.get(f'{self.operation_type}_success', success_message)
            
            self.status_label.configure(text=success_message, text_color="#2AAA8A")
        
        # Update percentage display
        if hasattr(self, 'percentage_text'):
            self.percentage_text.configure(text="100%", text_color="#2AAA8A")
        
        # Replace buttons with close button
        if hasattr(self, 'cancel_button'):
            self.cancel_button.grid_remove()
        if hasattr(self, 'confirm_button'):
            self.confirm_button.grid_remove()
        self.close_button.grid(row=0, column=2, padx=(10, 0), pady=0, sticky="e")
        
        # Auto-close after delay
        self.dialog.after(3000, self._on_close)
    
    def _on_cancellation(self):
        """Handle operation cancellation with enhanced cleanup."""
        # Stop timeout monitoring
        self.stop_timeout_monitoring()
        
        # Update step indicators to show cancellation state with consistent theming
        if hasattr(self, 'step_indicators'):
            for i, (circle, name) in enumerate(self.step_indicators):
                circle.configure(fg_color="#FF8C00", text="⏸", text_color="white")  # Orange with pause symbol
                name.configure(text_color="#FF8C00", font=ctk.CTkFont(size=11))
        
        # Update progress bar to show cancelled state
        self.progress_bar.configure(progress_color="#FFA500")
        
        # Update labels
        cancel_title = "Operation Cancelled"
        cancel_message = "The operation was cancelled by the user"
        
        if self.i18n:
            cancel_title = self.i18n.get('operation_cancelled', cancel_title)
            cancel_message = self.i18n.get('operation_cancelled_message', cancel_message)
        
        self.parameter_label.configure(text=cancel_title, text_color="#FFA500")
        self.status_label.configure(text=cancel_message, text_color="#FFA500")
        
        # Update percentage display
        if hasattr(self, 'percentage_text'):
            self.percentage_text.configure(text="Cancelled", text_color="#FFA500")
        
        # Replace buttons with close button
        if hasattr(self, 'cancel_button'):
            self.cancel_button.grid_remove()
        if hasattr(self, 'confirm_button'):
            self.confirm_button.grid_remove()
        self.close_button.grid(row=0, column=2, padx=(10, 0), pady=0, sticky="e")
        
        # Mark cancellation as completed
        self._cancellation_completed = True
        
        # Auto-close after delay
        self.dialog.after(2000, self._on_close)
    
    def _on_confirm(self):
        """Handle confirm button click."""
        # Hide the confirmation buttons
        self.cancel_button.grid_remove()
        self.confirm_button.grid_remove()
        
        # Update the UI to show progress
        self.parameter_label.configure(text="Starting deployment...")
        self.status_label.configure(text="Preparing to send parameters...")
        
        # In a real implementation, this would trigger the actual deployment process
        # For now, we'll just update the UI to reflect the operation has started
        
    def _on_cancel(self):
        """Handle cancel button click with enhanced cancellation logic."""
        if not self.is_cancelled:
            self.is_cancelled = True
            self.cancel_button.configure(text="Cancelling...", state="disabled")
            self.status_label.configure(text="Cancelling operation...")
            
            # Update progress bar to show cancellation state
            self.progress_bar.configure(progress_color="#FFA500")  # Orange for cancelling
            
            # Set a timeout for cancellation to prevent hanging
            self._cancellation_timeout = 10.0  # 10 seconds timeout
            self._cancellation_start_time = time.time()
            
            # Call the cancel callback if provided
            if self.cancel_callback:
                try:
                    self.cancel_callback()
                except Exception as e:
                    self._log_error(f"Error during cancellation callback: {str(e)}", "cancellation")
            
            # Start monitoring cancellation timeout
            self._monitor_cancellation_timeout()
    
    def _monitor_cancellation_timeout(self):
        """Monitor cancellation timeout and force close if needed."""
        if hasattr(self, '_cancellation_start_time') and hasattr(self, '_cancellation_timeout'):
            elapsed = time.time() - self._cancellation_start_time
            
            if elapsed >= self._cancellation_timeout:
                # Force close the dialog if cancellation takes too long
                self._log_error("Cancellation timeout reached, forcing dialog close", "timeout")
                self.show_error("Cancellation timed out. Forcing operation to stop.", "timeout")
                self.dialog.after(1000, self._on_close)  # Close after 1 second
            elif self.is_cancelled and not hasattr(self, '_cancellation_completed'):
                # Continue monitoring
                self.dialog.after(500, self._monitor_cancellation_timeout)
    
    def _complete_cancellation(self):
        """Mark cancellation as completed to stop timeout monitoring."""
        self._cancellation_completed = True
        self._on_cancellation()
    
    def _on_close(self):
        """Handle close button click with proper cleanup."""
        # Stop timeout monitoring
        self.stop_timeout_monitoring()
        
        # Cancel any pending after() calls
        if hasattr(self, 'timeout_after_id') and self.timeout_after_id:
            self.dialog.after_cancel(self.timeout_after_id)
        
        # Release grab and destroy dialog
        try:
            self.dialog.grab_release()
            self.dialog.destroy()
        except Exception as e:
            # Handle case where dialog is already destroyed
            self._log_error(f"Error during dialog cleanup: {str(e)}", "cleanup")
    
    def _on_window_close(self):
        """Handle window close event (X button)."""
        if not self.is_cancelled:
            self._on_cancel()
        else:
            self._on_close()
    
    def set_cancel_callback(self, callback: Callable):
        """
        Set the callback function to call when operation is cancelled.
        
        Args:
            callback: Function to call when cancelled
        """
        self.cancel_callback = callback
    
    def show_error(self, error_message: str, error_type: str = "general"):
        """
        Show an error state in the dialog with enhanced error display.
        
        Args:
            error_message: Error message to display
            error_type: Type of error (timeout, connection, validation, general)
        """
        # Update step indicators to show error state with consistent theming
        if hasattr(self, 'step_indicators'):
            for i, (circle, name) in enumerate(self.step_indicators):
                if i < len(self.step_indicators) - 1:  # Don't mark the last step as error
                    circle.configure(fg_color="#DC3545", text="✗", text_color="white")  # Red with X mark
                    name.configure(text_color="#DC3545", font=ctk.CTkFont(size=11))
        
        # Update progress bar to show error state
        self.progress_bar.configure(progress_color="#FF4444")
        
        # Set error-specific titles and messages
        error_titles = {
            "timeout": "Operation Timed Out",
            "connection": "Connection Error", 
            "validation": "Validation Error",
            "cancellation": "Operation Cancelled",
            "general": "Operation Failed"
        }
        
        error_title = error_titles.get(error_type, "Operation Failed")
        if self.i18n:
            error_title = self.i18n.get(f'error_{error_type}_title', error_title)
        
        self.parameter_label.configure(text=error_title, text_color="#FF4444")
        
        # Format error message with better readability
        formatted_message = self._format_error_message(error_message, error_type)
        self.status_label.configure(text=formatted_message, text_color="#FF4444")
        
        # Update percentage to show error state
        if hasattr(self, 'percentage_text'):
            self.percentage_text.configure(text="Error", text_color="#FF4444")
        
        # Replace cancel button with close button
        if hasattr(self, 'cancel_button'):
            self.cancel_button.grid_remove()
        if hasattr(self, 'confirm_button'):
            self.confirm_button.grid_remove()
            
        # Show close button
        self.close_button.grid(row=0, column=2, padx=(10, 0), pady=0, sticky="e")
        
        # Log the error for debugging
        self._log_error(error_message, error_type)
    
    def _format_error_message(self, error_message: str, error_type: str) -> str:
        """
        Format error message for better user readability.
        
        Args:
            error_message: Raw error message
            error_type: Type of error
            
        Returns:
            Formatted error message
        """
        # Truncate very long error messages
        if len(error_message) > 200:
            error_message = error_message[:197] + "..."
        
        # Add context based on error type
        if error_type == "timeout":
            return f"The operation timed out. {error_message}"
        elif error_type == "connection":
            return f"Connection lost. {error_message}"
        elif error_type == "validation":
            return f"Data validation failed. {error_message}"
        elif error_type == "cancellation":
            return f"Operation was cancelled. {error_message}"
        else:
            return error_message
    
    def _get_default_status_message(self, progress_info: ProfileProgressInfo) -> str:
        """
        Get default status message based on current progress.
        
        Args:
            progress_info: Current progress information
            
        Returns:
            Default status message
        """
        if progress_info.current_step == 0:
            return "Preparing to start operation..."
        elif progress_info.current_step == 1:
            return "Preparing device connection and validation..."
        elif progress_info.current_step == 2:
            return "Establishing connection with device..."
        elif progress_info.current_step == 3:
            if progress_info.total_parameters > 0:
                return f"Deploying configuration parameters ({progress_info.parameter_index}/{progress_info.total_parameters})..."
            else:
                return "Deploying configuration to device..."
        elif progress_info.current_step == 4:
            return "Verifying deployment and finalizing..."
        else:
            return "Processing operation..."
    
    def _log_error(self, error_message: str, error_type: str):
        """
        Log error information for debugging.
        
        Args:
            error_message: Error message
            error_type: Type of error
        """
        if hasattr(self.parent, '_log_message'):
            self.parent._log_message(f"ERROR [{error_type.upper()}]: {error_message}")
        else:
            print(f"ProfileProgressDialog ERROR [{error_type.upper()}]: {error_message}")
    
    def start_timeout_monitoring(self, timeout_seconds: float = None):
        """
        Start monitoring operation timeout.
        
        Args:
            timeout_seconds: Custom timeout in seconds (uses default if None)
        """
        if timeout_seconds:
            self.operation_timeout = timeout_seconds
        
        self.operation_start_time = time.time()
        self._schedule_timeout_check()
    
    def _schedule_timeout_check(self):
        """Schedule the next timeout check."""
        if not self.is_cancelled and not hasattr(self, '_cancellation_completed'):
            self.timeout_after_id = self.dialog.after(self.timeout_check_interval, self._check_operation_timeout)
    
    def _check_operation_timeout(self):
        """Check if the operation has timed out."""
        if self.operation_start_time is None:
            return
        
        elapsed_time = time.time() - self.operation_start_time
        
        if elapsed_time >= self.operation_timeout:
            # Operation has timed out
            timeout_message = f"Operation timed out after {int(self.operation_timeout)} seconds"
            if self.i18n:
                timeout_message = self.i18n.get('operation_timeout_message', timeout_message)
            
            self._log_error(f"Operation timeout after {elapsed_time:.1f} seconds", "timeout")
            
            # Cancel the operation
            if not self.is_cancelled:
                self.is_cancelled = True
                if self.cancel_callback:
                    try:
                        self.cancel_callback()
                    except Exception as e:
                        self._log_error(f"Error during timeout cancellation: {str(e)}", "timeout")
            
            # Show timeout error
            self.show_error(timeout_message, "timeout")
        else:
            # Schedule next check
            self._schedule_timeout_check()
    
    def stop_timeout_monitoring(self):
        """Stop timeout monitoring."""
        if self.timeout_after_id:
            self.dialog.after_cancel(self.timeout_after_id)
            self.timeout_after_id = None
    
    def set_operation_timeout(self, timeout_seconds: float):
        """
        Set custom timeout for the operation.
        
        Args:
            timeout_seconds: Timeout in seconds
        """
        self.operation_timeout = max(30.0, timeout_seconds)  # Minimum 30 seconds


class ProfileProgressManager:
    """Manager for profile operation progress dialogs."""
    
    def __init__(self, parent):
        """
        Initialize the progress manager.
        
        Args:
            parent: Parent window for dialogs
        """
        self.parent = parent
        self.active_dialogs = {}
    
    def create_progress_dialog(self, operation_type: str, title: str = None, profile_info: Dict[str, Any] = None) -> str:
        """
        Create a new progress dialog for a profile operation.
        
        Args:
            operation_type: Type of operation ('device_to_profile' or 'profile_to_device')
            title: Optional custom title
            profile_info: Optional dictionary with profile information
            
        Returns:
            Dialog ID for updating progress
        """
        # Generate unique dialog ID
        dialog_id = f"profile_progress_{operation_type}_{int(time.time())}"
        
        # Default titles
        if not title:
            titles = {
                'device_to_profile': 'Load from Device',
                'profile_to_device': 'Deploy to Device'
            }
            title = titles.get(operation_type, 'Profile Operation')
        
        # Create the dialog
        dialog = ProfileProgressDialog(self.parent, title, operation_type)
        
        # Initialize with profile information if available
        if profile_info and ProfileProgressInfo:
            # Create initial progress info with profile details
            progress_info = ProfileProgressInfo(
                operation_type=operation_type,
                current_step=0,
                total_steps=4,
                current_parameter=0,
                total_parameters=profile_info.get('parameter_count', 0),
                parameter_name="",
                status_message="Initializing...",
                step_name="Preparation",
                progress_percentage=0.0,
                profile_name=profile_info.get('name', ''),
                profile_created=profile_info.get('created', ''),
                profile_device_imei=profile_info.get('device_imei', ''),
                profile_parameter_count=profile_info.get('parameter_count', 0)
            )
            
            # Update the dialog with initial information
            dialog.update_progress(progress_info)
        
        # Store the dialog
        self.active_dialogs[dialog_id] = dialog
        
        return dialog_id
    
    def update_progress(self, dialog_id: str, progress_info: ProfileProgressInfo):
        """
        Update progress for a specific dialog.
        
        Args:
            dialog_id: Dialog ID returned from create_progress_dialog
            progress_info: Progress information
        """
        if dialog_id in self.active_dialogs:
            self.active_dialogs[dialog_id].update_progress(progress_info)
    
    def set_cancel_callback(self, dialog_id: str, callback: Callable):
        """
        Set cancel callback for a specific dialog.
        
        Args:
            dialog_id: Dialog ID
            callback: Callback function
        """
        if dialog_id in self.active_dialogs:
            self.active_dialogs[dialog_id].set_cancel_callback(callback)
    
    def show_error(self, dialog_id: str, error_message: str, error_type: str = "general"):
        """
        Show error in a specific dialog.
        
        Args:
            dialog_id: Dialog ID
            error_message: Error message
            error_type: Type of error (timeout, connection, validation, general)
        """
        if dialog_id in self.active_dialogs:
            self.active_dialogs[dialog_id].show_error(error_message, error_type)
    
    def close_dialog(self, dialog_id: str):
        """
        Close a specific dialog with proper cleanup.
        
        Args:
            dialog_id: Dialog ID to close
        """
        if dialog_id in self.active_dialogs:
            try:
                self.active_dialogs[dialog_id]._on_close()
            except Exception as e:
                print(f"Error closing dialog {dialog_id}: {str(e)}")
            finally:
                # Always remove from active dialogs
                del self.active_dialogs[dialog_id]
    
    def close_all_dialogs(self):
        """Close all active progress dialogs."""
        for dialog_id in list(self.active_dialogs.keys()):
            self.close_dialog(dialog_id)
    
    def set_operation_timeout(self, dialog_id: str, timeout_seconds: float):
        """
        Set operation timeout for a specific dialog.
        
        Args:
            dialog_id: Dialog ID
            timeout_seconds: Timeout in seconds
        """
        if dialog_id in self.active_dialogs:
            self.active_dialogs[dialog_id].set_operation_timeout(timeout_seconds)
    
    def start_timeout_monitoring(self, dialog_id: str, timeout_seconds: float = None):
        """
        Start timeout monitoring for a specific dialog.
        
        Args:
            dialog_id: Dialog ID
            timeout_seconds: Custom timeout in seconds (uses default if None)
        """
        if dialog_id in self.active_dialogs:
            self.active_dialogs[dialog_id].start_timeout_monitoring(timeout_seconds)