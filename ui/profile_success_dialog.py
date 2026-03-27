"""
Profile Success Dialog - Specialized dialog for showing profile operation success.

This module provides a success dialog specifically designed for profile operations
including device-to-profile and profile-to-device operations.
"""

import customtkinter as ctk
from typing import Callable


class ProfileSuccessDialog:
    """Success dialog specifically for profile operations."""
    
    def __init__(self, parent, title: str, success_message: str):
        """
        Initialize the profile success dialog.
        
        Args:
            parent: Parent window
            title: Dialog title
            success_message: Success message to display
        """
        self.parent = parent
        
        # Get i18n service from parent if available
        self.i18n = parent.i18n_service if hasattr(parent, 'i18n_service') else None
        
        # Create the dialog window
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x300")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Ensure dialog uses the same theme as the application
        # The main app uses dark theme with blue color theme
        # Get current theme from parent's theme service if available
        if hasattr(parent, 'theme_service'):
            current_theme = parent.theme_service.get_current_theme()
            ctk.set_appearance_mode(current_theme)
        else:
            # Fallback to dark theme if theme service not available
            ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Center the dialog
        self._center_dialog()
        
        # Create UI elements
        self._create_ui(success_message)
        
        # Handle window close event
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Wait for the dialog to be closed
        self.dialog.wait_window()
    
    def _center_dialog(self):
        """Center the dialog on the parent window."""
        if hasattr(self.parent, 'winfo_x') and hasattr(self.parent, 'winfo_y'):
            x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - 250
            y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - 150
            self.dialog.geometry(f"+{x}+{y}")
    
    def _create_ui(self, success_message: str):
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
        
        # Dialog title
        title_text = "Profile Deployment Complete"
        if self.i18n:
            title_text = self.i18n.get('profile_deployment_complete', 'Profile Deployment Complete')
            
        self.title_label = ctk.CTkLabel(
            header_frame, 
            text=title_text,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.title_label.grid(row=0, column=1, padx=0, pady=0, sticky="w")
        
        # Success information section
        info_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        info_frame.grid(row=1, column=0, padx=10, pady=(20, 10), sticky="ew")
        info_frame.grid_columnconfigure(1, weight=1)
        
        # Success icon
        success_icon = ctk.CTkLabel(
            info_frame,
            text="✓",
            width=60,
            height=60,
            fg_color="#2ECC71",  # Green success color
            corner_radius=30,
            text_color="white",
            font=ctk.CTkFont(size=30, weight="bold")
        )
        success_icon.grid(row=0, column=0, padx=(0, 20), pady=0, sticky="nw")
        
        # Success message
        success_label = ctk.CTkLabel(
            info_frame,
            text=success_message,
            font=ctk.CTkFont(size=14),
            justify="left",
            wraplength=380
        )
        success_label.grid(row=0, column=1, sticky="w")
        
        # Button frame
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.grid(row=2, column=0, padx=10, pady=(20, 0), sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        
        # OK button
        ok_text = "OK"
        if self.i18n:
            ok_text = self.i18n.get('ok', 'OK')
            
        self.ok_button = ctk.CTkButton(
            button_frame,
            text=ok_text,
            command=self._on_close,
            width=80
        )
        self.ok_button.grid(row=0, column=0, sticky="e")
    
    def _on_close(self):
        """Handle close button click."""
        self.dialog.destroy()


def show_profile_success_dialog(parent, title: str, success_message: str):
    """
    Show a profile success dialog.
    
    Args:
        parent: Parent window
        title: Dialog title
        success_message: Success message to display
    """
    ProfileSuccessDialog(parent, title, success_message)