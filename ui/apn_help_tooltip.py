"""
APN Help Tooltip Component

Provides contextual help tooltips for APN fields with format examples
and interactive guidance for users.
"""

import customtkinter as ctk
import tkinter as tk
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class TooltipContent:
    """Content for tooltip display"""
    title: str
    description: str
    examples: List[str]
    tips: List[str]
    severity: str = "info"  # "info", "warning", "error"


class APNHelpTooltip:
    """Interactive tooltip for APN field help"""
    
    def __init__(self, parent_widget, field_name: str, i18n=None):
        self.parent_widget = parent_widget
        self.field_name = field_name
        self.i18n = i18n or self._get_default_i18n()
        
        self.tooltip_window = None
        self.is_visible = False
        self.hover_timer = None
        
        # Content for different field types
        self.tooltip_contents = self._initialize_tooltip_contents()
        
        # Bind events to parent widget
        self._bind_events()
    
    def _get_default_i18n(self):
        """Default i18n fallback"""
        class DefaultI18n:
            def get(self, key, default=None):
                return default or key
        return DefaultI18n()
    
    def _initialize_tooltip_contents(self) -> Dict[str, TooltipContent]:
        """Initialize tooltip content for different field types"""
        return {
            'apn': TooltipContent(
                title=self.i18n.get("apn_help_title", "APN Format Help"),
                description=self.i18n.get("apn_help_desc", "Access Point Name (APN) identifies the network gateway for data connections."),
                examples=[
                    "internet.provider.com",
                    "zap.vivo.com.br",
                    "tim.br",
                    "claro.com.br",
                    "192.168.1.1"
                ],
                tips=[
                    "Use domain format (e.g., provider.com) or IP address",
                    "No spaces or special characters except dots and hyphens",
                    "Maximum 100 characters",
                    "Contact your carrier for the correct APN"
                ]
            ),
            'apn_user': TooltipContent(
                title=self.i18n.get("apn_user_help_title", "APN Username Help"),
                description=self.i18n.get("apn_user_help_desc", "Username for APN authentication (optional for many carriers)."),
                examples=[
                    "user@provider.com",
                    "mobile",
                    "internet",
                    "(leave empty if not required)"
                ],
                tips=[
                    "Many carriers don't require a username",
                    "Maximum 64 characters",
                    "No quotes or angle brackets",
                    "If username is provided, password is usually required"
                ]
            ),
            'apn_password': TooltipContent(
                title=self.i18n.get("apn_password_help_title", "APN Password Help"),
                description=self.i18n.get("apn_password_help_desc", "Password for APN authentication (optional for many carriers)."),
                examples=[
                    "password123",
                    "mobile",
                    "internet",
                    "(leave empty if not required)"
                ],
                tips=[
                    "Many carriers don't require a password",
                    "Maximum 64 characters",
                    "No quotes or angle brackets",
                    "If password is provided, username is usually required"
                ]
            )
        }
    
    def _bind_events(self):
        """Bind mouse events to parent widget"""
        try:
            # Bind to the widget itself
            if hasattr(self.parent_widget, 'bind'):
                self.parent_widget.bind('<Enter>', self._on_enter)
                self.parent_widget.bind('<Leave>', self._on_leave)
                self.parent_widget.bind('<Button-1>', self._on_click)
            
            # Also try to bind to internal entry widget for CustomTkinter widgets
            if hasattr(self.parent_widget, '_entry'):
                self.parent_widget._entry.bind('<Enter>', self._on_enter)
                self.parent_widget._entry.bind('<Leave>', self._on_leave)
                self.parent_widget._entry.bind('<Button-1>', self._on_click)
                
        except Exception as e:
            print(f"Warning: Could not bind tooltip events: {e}")
    
    def _on_enter(self, event=None):
        """Handle mouse enter event"""
        if self.hover_timer:
            self.parent_widget.after_cancel(self.hover_timer)
        
        # Show tooltip after delay
        self.hover_timer = self.parent_widget.after(800, self._show_tooltip)
    
    def _on_leave(self, event=None):
        """Handle mouse leave event"""
        if self.hover_timer:
            self.parent_widget.after_cancel(self.hover_timer)
            self.hover_timer = None
        
        # Hide tooltip after short delay
        self.parent_widget.after(200, self._hide_tooltip)
    
    def _on_click(self, event=None):
        """Handle click event - toggle tooltip"""
        if self.is_visible:
            self._hide_tooltip()
        else:
            self._show_tooltip()
    
    def _show_tooltip(self):
        """Show the tooltip window"""
        if self.is_visible or not self.parent_widget.winfo_exists():
            return
        
        try:
            content = self.tooltip_contents.get(self.field_name)
            if not content:
                return
            
            # Create tooltip window
            self.tooltip_window = tk.Toplevel(self.parent_widget)
            self.tooltip_window.wm_overrideredirect(True)
            self.tooltip_window.configure(bg='#2b2b2b', relief='solid', borderwidth=1)
            
            # Position tooltip
            self._position_tooltip()
            
            # Create content frame
            main_frame = tk.Frame(self.tooltip_window, bg='#2b2b2b', padx=10, pady=8)
            main_frame.pack(fill='both', expand=True)
            
            # Title
            title_label = tk.Label(
                main_frame,
                text=content.title,
                font=('Arial', 10, 'bold'),
                fg='#ffffff',
                bg='#2b2b2b',
                anchor='w'
            )
            title_label.pack(fill='x', pady=(0, 5))
            
            # Description
            desc_label = tk.Label(
                main_frame,
                text=content.description,
                font=('Arial', 9),
                fg='#cccccc',
                bg='#2b2b2b',
                anchor='w',
                wraplength=300,
                justify='left'
            )
            desc_label.pack(fill='x', pady=(0, 8))
            
            # Examples section with enhanced formatting
            if content.examples:
                examples_label = tk.Label(
                    main_frame,
                    text="Examples:",
                    font=('Arial', 9, 'bold'),
                    fg='#4CAF50',
                    bg='#2b2b2b',
                    anchor='w'
                )
                examples_label.pack(fill='x', pady=(0, 2))
                
                for i, example in enumerate(content.examples[:4]):  # Limit to 4 examples
                    # Add context for examples
                    example_text = f"• {example}"
                    if self.field_name == 'apn' and i == 0:
                        example_text += " (Brazilian carrier)"
                    elif self.field_name == 'apn' and i == 1:
                        example_text += " (Vivo Brazil)"
                    elif self.field_name == 'apn' and i == 4:
                        example_text += " (IP address format)"
                    
                    example_label = tk.Label(
                        main_frame,
                        text=example_text,
                        font=('Arial', 8),
                        fg='#90EE90',
                        bg='#2b2b2b',
                        anchor='w'
                    )
                    example_label.pack(fill='x', padx=(10, 0))
            
            # Tips section
            if content.tips:
                tips_label = tk.Label(
                    main_frame,
                    text="Tips:",
                    font=('Arial', 9, 'bold'),
                    fg='#2196F3',
                    bg='#2b2b2b',
                    anchor='w'
                )
                tips_label.pack(fill='x', pady=(8, 2))
                
                for tip in content.tips[:3]:  # Limit to 3 tips
                    tip_label = tk.Label(
                        main_frame,
                        text=f"• {tip}",
                        font=('Arial', 8),
                        fg='#87CEEB',
                        bg='#2b2b2b',
                        anchor='w',
                        wraplength=280,
                        justify='left'
                    )
                    tip_label.pack(fill='x', padx=(10, 0))
            
            self.is_visible = True
            
            # Auto-hide after 10 seconds
            self.parent_widget.after(10000, self._hide_tooltip)
            
        except Exception as e:
            print(f"Error showing tooltip: {e}")
            self._hide_tooltip()
    
    def _position_tooltip(self):
        """Position tooltip relative to parent widget"""
        try:
            # Get parent widget position
            x = self.parent_widget.winfo_rootx()
            y = self.parent_widget.winfo_rooty()
            height = self.parent_widget.winfo_height()
            
            # Position tooltip below the widget
            tooltip_x = x
            tooltip_y = y + height + 5
            
            # Adjust if tooltip would go off screen
            screen_width = self.tooltip_window.winfo_screenwidth()
            screen_height = self.tooltip_window.winfo_screenheight()
            
            # Update tooltip to get its size
            self.tooltip_window.update_idletasks()
            tooltip_width = self.tooltip_window.winfo_reqwidth()
            tooltip_height = self.tooltip_window.winfo_reqheight()
            
            # Adjust horizontal position
            if tooltip_x + tooltip_width > screen_width:
                tooltip_x = screen_width - tooltip_width - 10
            
            # Adjust vertical position
            if tooltip_y + tooltip_height > screen_height:
                tooltip_y = y - tooltip_height - 5
            
            self.tooltip_window.geometry(f"+{tooltip_x}+{tooltip_y}")
            
        except Exception as e:
            print(f"Error positioning tooltip: {e}")
    
    def _hide_tooltip(self):
        """Hide the tooltip window"""
        if self.tooltip_window:
            try:
                self.tooltip_window.destroy()
            except:
                pass
            self.tooltip_window = None
        
        self.is_visible = False
    
    def update_content(self, content: TooltipContent):
        """Update tooltip content"""
        self.tooltip_contents[self.field_name] = content
        
        # Refresh tooltip if currently visible
        if self.is_visible:
            self._hide_tooltip()
            self.parent_widget.after(100, self._show_tooltip)
    
    def show_validation_help(self, validation_result):
        """Show validation-specific help"""
        if not validation_result or validation_result.is_valid:
            return
        
        # Create validation-specific content
        validation_content = TooltipContent(
            title=f"Validation Error: {self.field_name.replace('_', ' ').title()}",
            description=validation_result.error_message,
            examples=validation_result.suggestions[:3] if validation_result.suggestions else [],
            tips=[
                "Check the format requirements above",
                "Try one of the suggested corrections",
                "Contact your carrier for the correct settings"
            ],
            severity="error"
        )
        
        # Update content and show
        self.update_content(validation_content)
        self._show_tooltip()
    
    def destroy(self):
        """Clean up tooltip"""
        if self.hover_timer:
            self.parent_widget.after_cancel(self.hover_timer)
        self._hide_tooltip()


class APNCarrierHelper:
    """Interactive APN format helper with common carrier examples"""
    
    def __init__(self, parent, i18n=None):
        self.parent = parent
        self.i18n = i18n or self._get_default_i18n()
        
        # Common carrier configurations
        self.carrier_configs = {
            'Brazil': {
                'Vivo': [
                    {'apn': 'zap.vivo.com.br', 'user': 'vivo', 'password': 'vivo'},
                    {'apn': 'vivo.br', 'user': '', 'password': ''},
                ],
                'TIM': [
                    {'apn': 'tim.br', 'user': 'tim', 'password': 'tim'},
                    {'apn': 'tim.com.br', 'user': '', 'password': ''},
                ],
                'Claro': [
                    {'apn': 'claro.com.br', 'user': 'claro', 'password': 'claro'},
                    {'apn': 'bandalarga.claro.com.br', 'user': '', 'password': ''},
                ],
                'Oi': [
                    {'apn': 'gprs.oi.com.br', 'user': 'oi', 'password': 'oi'},
                    {'apn': 'oi.com.br', 'user': '', 'password': ''},
                ],
                'Allcom': [
                    {'apn': 'allcom.br', 'user': 'allcom', 'password': 'allcom'},
                ]
            },
            'United States': {
                'AT&T': [
                    {'apn': 'phone', 'user': '', 'password': ''},
                    {'apn': 'broadband', 'user': '', 'password': ''},
                ],
                'Verizon': [
                    {'apn': 'vzwinternet', 'user': '', 'password': ''},
                    {'apn': 'internet', 'user': '', 'password': ''},
                ],
                'T-Mobile': [
                    {'apn': 'fast.t-mobile.com', 'user': '', 'password': ''},
                    {'apn': 'epc.tmobile.com', 'user': '', 'password': ''},
                ]
            },
            'International': {
                'Vodafone': [
                    {'apn': 'internet', 'user': '', 'password': ''},
                    {'apn': 'live.vodafone.com', 'user': 'vodafone', 'password': 'vodafone'},
                ],
                'Orange': [
                    {'apn': 'orange', 'user': 'orange', 'password': 'orange'},
                    {'apn': 'orange.fr', 'user': '', 'password': ''},
                ],
                'Three': [
                    {'apn': '3internet', 'user': '', 'password': ''},
                    {'apn': 'three.co.uk', 'user': '', 'password': ''},
                ]
            }
        }
    
    def _get_default_i18n(self):
        """Default i18n fallback"""
        class DefaultI18n:
            def get(self, key, default=None):
                return default or key
        return DefaultI18n()
    
    def show_carrier_helper_dialog(self, callback=None):
        """Show interactive carrier helper dialog"""
        try:
            # Create dialog window
            dialog = ctk.CTkToplevel(self.parent)
            dialog.title(self.i18n.get("carrier_helper_title", "APN Carrier Helper"))
            dialog.geometry("600x500")
            dialog.transient(self.parent)
            dialog.grab_set()
            
            # Center the dialog
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (600 // 2)
            y = (dialog.winfo_screenheight() // 2) - (500 // 2)
            dialog.geometry(f"600x500+{x}+{y}")
            
            # Main frame
            main_frame = ctk.CTkFrame(dialog)
            main_frame.pack(fill='both', expand=True, padx=10, pady=10)
            
            # Title
            title_label = ctk.CTkLabel(
                main_frame,
                text=self.i18n.get("carrier_helper_desc", "Select your carrier to get pre-configured APN settings"),
                font=ctk.CTkFont(size=14, weight="bold")
            )
            title_label.pack(pady=(10, 20))
            
            # Create scrollable frame for carriers
            scroll_frame = ctk.CTkScrollableFrame(main_frame, height=350)
            scroll_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
            
            # Add carrier sections
            for country, carriers in self.carrier_configs.items():
                # Country header
                country_label = ctk.CTkLabel(
                    scroll_frame,
                    text=country,
                    font=ctk.CTkFont(size=16, weight="bold")
                )
                country_label.pack(anchor='w', pady=(15, 5))
                
                # Carriers in this country
                for carrier_name, configs in carriers.items():
                    # Carrier frame
                    carrier_frame = ctk.CTkFrame(scroll_frame)
                    carrier_frame.pack(fill='x', pady=2, padx=10)
                    
                    # Carrier name
                    carrier_label = ctk.CTkLabel(
                        carrier_frame,
                        text=carrier_name,
                        font=ctk.CTkFont(size=12, weight="bold")
                    )
                    carrier_label.pack(anchor='w', padx=10, pady=(5, 0))
                    
                    # Configuration options
                    for i, config in enumerate(configs):
                        config_text = f"APN: {config['apn']}"
                        if config['user']:
                            config_text += f" | User: {config['user']}"
                        if config['password']:
                            config_text += f" | Password: {config['password']}"
                        
                        config_button = ctk.CTkButton(
                            carrier_frame,
                            text=config_text,
                            command=lambda c=config: self._apply_carrier_config(c, callback, dialog),
                            height=30,
                            font=ctk.CTkFont(size=10)
                        )
                        config_button.pack(fill='x', padx=10, pady=2)
                    
                    # Add spacing after carrier
                    ctk.CTkLabel(carrier_frame, text="", height=5).pack()
            
            # Close button
            close_button = ctk.CTkButton(
                main_frame,
                text=self.i18n.get("close", "Close"),
                command=dialog.destroy
            )
            close_button.pack(pady=10)
            
        except Exception as e:
            print(f"Error showing carrier helper dialog: {e}")
    
    def _apply_carrier_config(self, config, callback, dialog):
        """Apply selected carrier configuration"""
        try:
            if callback:
                callback(config)
            dialog.destroy()
        except Exception as e:
            print(f"Error applying carrier config: {e}")
    
    def get_carrier_suggestions(self, partial_input: str) -> List[Dict[str, str]]:
        """Get carrier suggestions based on partial input"""
        suggestions = []
        partial_lower = partial_input.lower()
        
        for country, carriers in self.carrier_configs.items():
            for carrier_name, configs in carriers.items():
                # Check carrier name match
                if partial_lower in carrier_name.lower():
                    suggestions.extend(configs)
                else:
                    # Check APN match
                    for config in configs:
                        if partial_lower in config['apn'].lower():
                            suggestions.append(config)
        
        # Remove duplicates and limit results
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion not in unique_suggestions:
                unique_suggestions.append(suggestion)
        
        return unique_suggestions[:10]