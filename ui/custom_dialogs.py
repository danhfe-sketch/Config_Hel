"""
Custom dialog utilities that match CustomTkinter theme.
These replace standard tkinter messageboxes with themed versions.
"""

import customtkinter as ctk
from typing import Optional, Literal


class CTkMessageBox(ctk.CTkToplevel):
    """
    Custom message box that matches CustomTkinter theme.
    """
    
    def __init__(
        self,
        parent,
        title: str = "Message",
        message: str = "",
        icon: Literal["info", "warning", "error", "question"] = "info",
        option_1: str = "OK",
        option_2: Optional[str] = None,
        option_3: Optional[str] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        
        self.title(title)
        self.lift()  # Lift window on top
        self.attributes("-topmost", True)  # Stay on top
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.after(10, self._create_widgets)  # Create widgets after window is created
        self.resizable(False, False)
        self.grab_set()  # Make dialog modal
        
        # Store options and result
        self.option_1 = option_1
        self.option_2 = option_2
        self.option_3 = option_3
        self.result = None
        
        # Store message and icon - ensure they are set before any async operations
        self.message = message
        self.icon = icon
        
        # Calculate window size based on message length
        self._calculate_size()
        
        # Center the window
        self._center_window()
    
    def _calculate_size(self):
        """Calculate appropriate window size based on message length."""
        # Base dimensions
        base_width = 400
        base_height = 150
        
        # Adjust width based on message length
        message_lines = self.message.split('\n')
        max_line_length = max(len(line) for line in message_lines) if message_lines else 0
        
        if max_line_length > 50:
            base_width = min(600, base_width + (max_line_length - 50) * 8)
        
        # Adjust height based on number of lines
        num_lines = len(message_lines)
        if num_lines > 3:
            base_height += (num_lines - 3) * 20
        
        self.window_width = base_width
        self.window_height = base_height
        
        self.geometry(f"{self.window_width}x{self.window_height}")
    
    def _center_window(self):
        """Center the window on the parent or screen."""
        self.update_idletasks()
        
        # Get parent window position and size
        if self.master:
            parent_x = self.master.winfo_rootx()
            parent_y = self.master.winfo_rooty()
            parent_width = self.master.winfo_width()
            parent_height = self.master.winfo_height()
            
            # Calculate center position
            x = parent_x + (parent_width // 2) - (self.window_width // 2)
            y = parent_y + (parent_height // 2) - (self.window_height // 2)
        else:
            # Center on screen
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            x = (screen_width // 2) - (self.window_width // 2)
            y = (screen_height // 2) - (self.window_height // 2)
        
        self.geometry(f"{self.window_width}x{self.window_height}+{x}+{y}")
    
    def _create_widgets(self):
        """Create the dialog widgets."""
        # Safety check to ensure all attributes are initialized
        if not hasattr(self, 'message'):
            self.message = ""
        if not hasattr(self, 'icon'):
            self.icon = "info"
        if not hasattr(self, 'window_width'):
            self.window_width = 400
        if not hasattr(self, 'window_height'):
            self.window_height = 150
        if not hasattr(self, 'option_1'):
            self.option_1 = "OK"
        if not hasattr(self, 'option_2'):
            self.option_2 = None
        if not hasattr(self, 'option_3'):
            self.option_3 = None
        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Icon and message frame
        content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        # Icon
        icon_text = self._get_icon_text()
        if icon_text:
            icon_label = ctk.CTkLabel(
                content_frame,
                text=icon_text,
                font=ctk.CTkFont(size=24),
                width=40
            )
            icon_label.pack(side="left", padx=(10, 20), pady=10)
        
        # Message
        # Safety check for window_width attribute
        window_width = getattr(self, 'window_width', 400)
        
        message_label = ctk.CTkLabel(
            content_frame,
            text=self.message,
            font=ctk.CTkFont(size=14),
            wraplength=window_width - 120,
            justify="left"
        )
        message_label.pack(side="left", fill="both", expand=True, pady=10)
        
        # Button frame
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(10, 0))
        
        # Create buttons
        buttons = []
        if self.option_3:
            buttons = [self.option_1, self.option_2, self.option_3]
        elif self.option_2:
            buttons = [self.option_1, self.option_2]
        else:
            buttons = [self.option_1]
        
        # Pack buttons from right to left
        for i, button_text in enumerate(reversed(buttons)):
            btn = ctk.CTkButton(
                button_frame,
                text=button_text,
                command=lambda text=button_text: self._button_click(text),
                width=80,
                height=32
            )
            btn.pack(side="right", padx=(10, 0) if i > 0 else (10, 10))
        
        # Focus on the first button
        if hasattr(self, '_buttons') and self._buttons:
            self._buttons[0].focus()
    
    def _get_icon_text(self) -> str:
        """Get icon text based on icon type."""
        icon_map = {
            "info": "ℹ️",
            "warning": "⚠️", 
            "error": "❌",
            "question": "❓"
        }
        # Safety check in case icon attribute is not set yet
        icon_type = getattr(self, 'icon', 'info')
        return icon_map.get(icon_type, "ℹ️")
    
    def _button_click(self, button_text: str):
        """Handle button click."""
        self.result = button_text
        self._on_closing()
    
    def _on_closing(self):
        """Handle window closing."""
        self.grab_release()
        self.destroy()
    
    def get_result(self) -> Optional[str]:
        """Get the result after the dialog is closed."""
        self.master.wait_window(self)
        return self.result


def show_info(parent, title: str, message: str) -> None:
    """Show an info message dialog (localized buttons if available)."""
    # Prefer i18n service attached to the parent under common attribute names
    i18n = None
    if hasattr(parent, 'i18n'):
        i18n = getattr(parent, 'i18n')
    elif hasattr(parent, 'i18n_service'):
        i18n = getattr(parent, 'i18n_service')
    
    # Fix common hardcoded strings by translating them when possible
    try:
        if i18n:
            # Translate known profile-load messages if they were passed as English literals
            if title == "Profile Loaded":
                title = i18n.get("profile_loaded_title", title)
            if isinstance(message, str) and "Profile successfully loaded" in message:
                message = i18n.get("profile_loaded_successfully", "Profile successfully loaded from {file_path}").format(file_path=message.splitlines()[-1] if "\n" in message else message)
    except Exception:
        # If translation lookup fails, keep original title/message
        pass

    ok_label = i18n.get('ok', 'OK') if i18n else 'OK'
    dialog = CTkMessageBox(
        parent=parent,
        title=title,
        message=message,
        icon="info",
        option_1=ok_label
    )
    dialog.get_result()


def show_warning(parent, title: str, message: str) -> None:
    """Show a warning message dialog (localized buttons if available)."""
    i18n = getattr(parent, 'i18n_service', None)
    ok_label = i18n.get('ok', 'OK') if i18n else 'OK'
    dialog = CTkMessageBox(
        parent=parent,
        title=title,
        message=message,
        icon="warning",
        option_1=ok_label
    )
    dialog.get_result()


def show_error(parent, title: str, message: str) -> None:
    """Show an error message dialog (localized buttons if available)."""
    i18n = getattr(parent, 'i18n_service', None)
    ok_label = i18n.get('ok', 'OK') if i18n else 'OK'
    dialog = CTkMessageBox(
        parent=parent,
        title=title,
        message=message,
        icon="error",
        option_1=ok_label
    )
    dialog.get_result()


def ask_yes_no(parent, title: str, message: str) -> bool:
    """Show a confirmation dialog with localized Confirm/Cancel if available."""
    i18n = getattr(parent, 'i18n_service', None)
    if i18n:
        confirm_label = i18n.get('confirm', 'Confirm')
        cancel_label = i18n.get('cancel', 'Cancel')
    else:
        confirm_label = 'Confirm'
        cancel_label = 'Cancel'
    dialog = CTkMessageBox(
        parent=parent,
        title=title,
        message=message,
        icon="question",
        option_1=confirm_label,
        option_2=cancel_label
    )
    result = dialog.get_result()
    return result == confirm_label


def ask_ok_cancel(parent, title: str, message: str) -> bool:
    """Show an OK/Cancel dialog (localized buttons if available)."""
    i18n = getattr(parent, 'i18n_service', None)
    if i18n:
        ok_label = i18n.get('ok', 'OK')
        cancel_label = i18n.get('cancel', 'Cancel')
    else:
        ok_label = 'OK'
        cancel_label = 'Cancel'
    dialog = CTkMessageBox(
        parent=parent,
        title=title,
        message=message,
        icon="question",
        option_1=ok_label,
        option_2=cancel_label
    )
    result = dialog.get_result()
    return result == ok_label


def ask_yes_no_cancel(parent, title: str, message: str) -> Optional[bool]:
    """Show a yes/no/cancel dialog (localized buttons if available)."""
    i18n = getattr(parent, 'i18n_service', None)
    if i18n:
        yes_label = i18n.get('yes', 'Yes')
        no_label = i18n.get('no', 'No')
        cancel_label = i18n.get('cancel', 'Cancel')
    else:
        yes_label = 'Yes'
        no_label = 'No'
        cancel_label = 'Cancel'
    dialog = CTkMessageBox(
        parent=parent,
        title=title,
        message=message,
        icon="question",
        option_1=yes_label,
        option_2=no_label,
        option_3=cancel_label
    )
    result = dialog.get_result()
    if result == yes_label:
        return True
    elif result == no_label:
        return False
    else:
        return None  # Cancel