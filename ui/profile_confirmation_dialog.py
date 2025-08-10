"""
Profile Confirmation Dialog - Specialized dialog for confirming profile operations.

This module provides a confirmation dialog specifically designed for profile operations
including device-to-profile and profile-to-device operations.
"""

import customtkinter as ctk
import os
from typing import Callable, Dict, Any, Optional


class ProfileConfirmationDialog:
    """Confirmation dialog specifically for profile operations."""
    
    def __init__(self, parent, title: str, operation_type: str, profile_info: Dict[str, Any] = None):
        """
        Initialize the profile confirmation dialog.
        
        Args:
            parent: Parent window
            title: Dialog title
            operation_type: Type of operation ('device_to_profile' or 'profile_to_device')
            profile_info: Optional dictionary with profile information
        """
        self.parent = parent
        self.operation_type = operation_type
        self.result = False
        
        # Get i18n service from parent if available
        self.i18n = parent.i18n_service if hasattr(parent, 'i18n_service') else None
        
        # Create the dialog window
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x400")  # Increased height to accommodate new layout
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Ensure dialog uses the same theme as the application
        # The main app uses dark theme with blue color theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Center the dialog
        self._center_dialog()
        
        # Create UI elements
        self._create_ui(profile_info)
        
        # Handle window close event
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
        
        # Wait for the dialog to be closed
        self.dialog.wait_window()
    
    def _center_dialog(self):
        """Center the dialog on the parent window."""
        if hasattr(self.parent, 'winfo_x') and hasattr(self.parent, 'winfo_y'):
            x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - 250
            y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - 200
            self.dialog.geometry(f"+{x}+{y}")
    
    def _create_ui(self, profile_info: Dict[str, Any] = None):
        """Create the dialog UI elements."""
        # Configure grid
        self.dialog.grid_columnconfigure(0, weight=1)
        
        # Create main frame to hold all content with consistent padding
        main_frame = ctk.CTkFrame(self.dialog)
        main_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Add icon and title in a header frame
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        # Icon (using a label with a circle as a placeholder)
        icon_label = ctk.CTkLabel(
            header_frame,
            text="",
            width=30,
            height=30,
            fg_color="#3B8ED0",  # Blue circle
            corner_radius=15,
            text_color=None
        )
        icon_label.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="w")
        
        # Operation title
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
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.title_label.grid(row=0, column=1, padx=0, pady=0, sticky="w")
        
        # Profile information section
        info_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        info_frame.grid(row=1, column=0, padx=10, pady=(10, 5), sticky="ew")
        info_frame.grid_columnconfigure(0, weight=1)
        
        # Warning icon
        warning_icon = ctk.CTkLabel(
            info_frame,
            text="!",
            width=30,
            height=30,
            fg_color="#FFA500",  # Orange warning color
            corner_radius=15,
            text_color="black",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        warning_icon.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="nw")
        
        # Profile information text frame
        profile_info_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        profile_info_frame.grid(row=0, column=1, sticky="ew")
        
        # Profile information label
        profile_info_text = "Profile Information:"
        if self.i18n:
            profile_info_text = self.i18n.get('profile_information', 'Profile Information:')
            
        profile_info_label = ctk.CTkLabel(
            profile_info_frame,
            text=profile_info_text,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        profile_info_label.grid(row=0, column=0, sticky="w")
        
        # Profile details
        profile_name = profile_info.get('name', '[Profile Name]') if profile_info else '[Profile Name]'
        profile_created = profile_info.get('created', '[Date]') if profile_info else '[Date]'
        profile_device_imei = profile_info.get('device_imei', '[IMEI]') if profile_info else '[IMEI]'
        profile_parameter_count = profile_info.get('parameter_count', 0) if profile_info else 0
        
        profile_details = ctk.CTkLabel(
            profile_info_frame,
            text=f"Name: {profile_name}\n"
                 f"Created: {profile_created}\n"
                 f"Original Device IMEI: {profile_device_imei}\n"
                 f"Parameters: {profile_parameter_count}",
            font=ctk.CTkFont(size=12),
            justify="left"
        )
        profile_details.grid(row=1, column=0, sticky="w")
        
        # Description text
        description_str = "This will deploy the profile configuration to the connected device.\n\n" \
                         "The device must be connected and responding.\n" \
                         "Existing device settings will be overwritten."
        
        if self.i18n:
            description_str = self.i18n.get('profile_deploy_description',
                "This will deploy the profile configuration to the connected device.\n\n" \
                "The device must be connected and responding.\n" \
                "Existing device settings will be overwritten.")
        
        description_text = ctk.CTkLabel(
            main_frame,
            text=description_str,
            font=ctk.CTkFont(size=12),
            justify="left",
            wraplength=450
        )
        description_text.grid(row=2, column=0, padx=10, pady=(20, 20), sticky="w")
        
        # Continue question
        continue_text = "Continue?"
        if self.i18n:
            continue_text = self.i18n.get('continue_question', 'Continue?')
            
        continue_label = ctk.CTkLabel(
            main_frame,
            text=continue_text,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        continue_label.grid(row=3, column=0, padx=10, pady=(10, 10), sticky="w")
        
        # Button frame
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.grid(row=4, column=0, padx=10, pady=(10, 0), sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=0)
        button_frame.grid_columnconfigure(2, weight=0)
        
        # Cancel button (No)
        cancel_text = "Não"
        if self.i18n:
            cancel_text = self.i18n.get('no', 'Não')
            
        self.cancel_button = ctk.CTkButton(
            button_frame,
            text=cancel_text,
            command=self._on_cancel,
            width=80
        )
        self.cancel_button.grid(row=0, column=2, padx=(10, 0), pady=0, sticky="e")
        
        # Confirm button (Yes)
        confirm_text = "Sim"
        if self.i18n:
            confirm_text = self.i18n.get('yes', 'Sim')
            
        self.confirm_button = ctk.CTkButton(
            button_frame,
            text=confirm_text,
            command=self._on_confirm,
            width=80
        )
        self.confirm_button.grid(row=0, column=1, padx=(0, 0), pady=0, sticky="e")
    
    def _on_confirm(self):
        """Handle confirm button click."""
        self.result = True
        self.dialog.destroy()
    
    def _on_cancel(self):
        """Handle cancel button click."""
        self.result = False
        self.dialog.destroy()


def show_profile_confirmation_dialog(parent, title: str, operation_type: str, profile_info: Dict[str, Any] = None) -> bool:
    """
    Show a profile confirmation dialog and return the result.
    
    Args:
        parent: Parent window
        title: Dialog title
        operation_type: Type of operation ('device_to_profile' or 'profile_to_device')
        profile_info: Optional dictionary with profile information
        
    Returns:
        True if confirmed, False if cancelled
    """
    dialog = ProfileConfirmationDialog(parent, title, operation_type, profile_info)
    return dialog.result