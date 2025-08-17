"""
Custom Confirmation Dialog - Modern confirmation dialog matching application design.

This module provides a confirmation dialog that matches the application's CustomTkinter
design and supports internationalization.
"""

import customtkinter as ctk
from typing import Optional


class CustomConfirmationDialog:
    """Custom confirmation dialog with modern design."""
    
    def __init__(self, parent, title: str, message: str, detail: str = "", icon_type: str = "warning"):
        """
        Initialize the custom confirmation dialog.
        
        Args:
            parent: Parent window
            title: Dialog title
            message: Main message text
            detail: Additional detail text
            icon_type: Type of icon ("warning", "question", "info", "error")
        """
        self.parent = parent
        self.result = False
        
        # Get i18n service from parent if available
        self.i18n = getattr(parent, 'i18n', None) or getattr(parent, 'i18n_service', None)
        
        # Create the dialog window
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x300")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Ensure dialog uses the same theme as the application
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Center the dialog
        self._center_dialog()
        
        # Create UI elements
        self._create_ui(title, message, detail, icon_type)
        
        # Handle window close event
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
        
        # Focus on the dialog
        self.dialog.focus()
        
        # Wait for the dialog to be closed
        self.dialog.wait_window()
    
    def _center_dialog(self):
        """Center the dialog on the parent window."""
        self.dialog.update_idletasks()
        
        if hasattr(self.parent, 'winfo_x') and hasattr(self.parent, 'winfo_y'):
            parent_x = self.parent.winfo_rootx()
            parent_y = self.parent.winfo_rooty()
            parent_width = self.parent.winfo_width()
            parent_height = self.parent.winfo_height()
            
            dialog_width = 500
            dialog_height = 300
            
            x = parent_x + (parent_width // 2) - (dialog_width // 2)
            y = parent_y + (parent_height // 2) - (dialog_height // 2)
            
            self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    def _create_ui(self, title: str, message: str, detail: str, icon_type: str):
        """Create the dialog UI elements."""
        # Configure grid
        self.dialog.grid_columnconfigure(0, weight=1)
        self.dialog.grid_rowconfigure(0, weight=1)
        
        # Create main frame
        main_frame = ctk.CTkFrame(self.dialog)
        main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        main_frame.grid_columnconfigure(1, weight=1)
        
        # Icon colors based on type
        icon_colors = {
            "warning": "#FFA500",  # Orange
            "question": "#3B8ED0",  # Blue
            "info": "#3B8ED0",     # Blue
            "error": "#FF4444"     # Red
        }
        
        # Icon symbols
        icon_symbols = {
            "warning": "!",
            "question": "?",
            "info": "i",
            "error": "×"
        }
        
        # Create icon
        icon_color = icon_colors.get(icon_type, "#FFA500")
        icon_symbol = icon_symbols.get(icon_type, "!")
        
        icon_label = ctk.CTkLabel(
            main_frame,
            text=icon_symbol,
            width=50,
            height=50,
            fg_color=icon_color,
            corner_radius=25,
            text_color="white" if icon_type != "warning" else "black",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        icon_label.grid(row=0, column=0, padx=(10, 20), pady=10, sticky="nw")
        
        # Create text frame
        text_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        text_frame.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="nsew")
        text_frame.grid_columnconfigure(0, weight=1)
        
        # Main message
        message_label = ctk.CTkLabel(
            text_frame,
            text=message,
            font=ctk.CTkFont(size=14),
            wraplength=350,
            justify="left"
        )
        message_label.grid(row=0, column=0, pady=(0, 10), sticky="ew")
        
        # Detail message (if provided)
        if detail:
            detail_label = ctk.CTkLabel(
                text_frame,
                text=detail,
                font=ctk.CTkFont(size=12),
                wraplength=350,
                justify="left",
                text_color="gray70"
            )
            detail_label.grid(row=1, column=0, pady=(0, 10), sticky="ew")
        
        # Button frame
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=(10, 10), sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        
        # Get button texts from i18n if available
        yes_text = "Sim"
        no_text = "Não"
        
        if self.i18n:
            yes_text = self.i18n.get("yes", "Sim")
            no_text = self.i18n.get("no", "Não")
        
        # No button (left)
        no_button = ctk.CTkButton(
            button_frame,
            text=no_text,
            command=self._on_cancel,
            width=100,
            height=35,
            fg_color="gray50",
            hover_color="gray40"
        )
        no_button.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="e")
        
        # Yes button (right)
        yes_button = ctk.CTkButton(
            button_frame,
            text=yes_text,
            command=self._on_confirm,
            width=100,
            height=35
        )
        yes_button.grid(row=0, column=1, padx=(10, 0), pady=0, sticky="w")
        
        # Set focus on Yes button
        yes_button.focus()
    
    def _on_confirm(self):
        """Handle confirm button click."""
        self.result = True
        self.dialog.destroy()
    
    def _on_cancel(self):
        """Handle cancel button click."""
        self.result = False
        self.dialog.destroy()
    
    def get_result(self) -> bool:
        """Get the dialog result."""
        return self.result


def show_confirmation_dialog(parent, title: str, message: str, detail: str = "", icon_type: str = "warning") -> bool:
    """
    Show a custom confirmation dialog.
    
    Args:
        parent: Parent window
        title: Dialog title
        message: Main message text
        detail: Additional detail text
        icon_type: Type of icon ("warning", "question", "info", "error")
        
    Returns:
        True if user confirmed, False otherwise
    """
    dialog = CustomConfirmationDialog(parent, title, message, detail, icon_type)
    return dialog.get_result()