"""
Parameter UI Element Factory

This module provides a factory class for creating all UI element types specified
in the Parameter UI List document. It supports text_input, number_input, dropdown,
toggle_switch, slider, and password_input elements with proper validation, styling,
and configuration.
"""

import customtkinter as ctk
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass
import re


@dataclass
class UIElementConfig:
    """Configuration for a UI element"""
    element_type: str
    label: str
    validation_rules: Optional[Dict[str, Any]] = None
    default_value: Optional[Any] = None
    options: Optional[List[str]] = None
    range_config: Optional[Dict[str, Any]] = None
    unit: Optional[str] = None
    visibility_condition: Optional[str] = None
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    translation_key: Optional[str] = None


class BaseUIElement(ABC):
    """Base class for all UI elements with common functionality"""
    
    def __init__(self, config: UIElementConfig, i18n_service, validation_callback: Optional[Callable] = None):
        self.config = config
        self.i18n = i18n_service
        self.validation_callback = validation_callback
        self.value_change_callback = None
        self.widget = None
        self.label_widget = None
        self.error_label = None
        self.container_frame = None
        self.visible = True
        self._validation_error = None
        self._validation_level = "info"
        
    @abstractmethod
    def create_widget(self, parent) -> ctk.CTkFrame:
        """Create the UI widget for this element"""
        pass
    
    @abstractmethod
    def get_value(self) -> Any:
        """Get the current value from the widget"""
        pass
    
    @abstractmethod
    def set_value(self, value: Any) -> None:
        """Set the value in the widget"""
        pass
    
    def validate(self) -> bool:
        """Validate the current element value"""
        if not self.config.validation_rules:
            return True
            
        value = self.get_value()
        validation_result = self._validate_value(value)
        
        if validation_result['is_valid']:
            self._clear_error()
            return True
        else:
            self._show_error(validation_result['error_message'])
            # Store validation level for visual feedback
            self._validation_level = validation_result.get('validation_level', 'error')
            return False
    
    def _validate_value(self, value: Any) -> Dict[str, Any]:
        """Internal validation logic with enhanced feedback"""
        if not self.config.validation_rules:
            return {'is_valid': True, 'error_message': None, 'validation_level': 'info'}
        
        rules = self.config.validation_rules
        
        # Check required validation
        if rules.get('required', False) and (value is None or str(value).strip() == ''):
            return {
                'is_valid': False,
                'error_message': f"{self.config.label} is required",
                'validation_level': 'error'
            }
        
        # Skip other validations if value is empty and not required
        if value is None or str(value).strip() == '':
            return {'is_valid': True, 'error_message': None, 'validation_level': 'info'}
        
        # Numeric range validation with progressive feedback
        if rules.get('type') == 'numeric_range':
            try:
                num_value = float(value) if not rules.get('integer', True) else int(value)
                min_val = rules.get('min')
                max_val = rules.get('max')
                
                if min_val is not None and num_value < min_val:
                    # Check if close to valid range
                    if max_val is not None:
                        range_size = max_val - min_val
                        diff = min_val - num_value
                        if diff <= range_size * 0.1:  # Within 10% of range
                            return {
                                'is_valid': False,
                                'error_message': rules.get('error_message', f"Value must be at least {min_val}"),
                                'validation_level': 'warning'
                            }
                    
                    return {
                        'is_valid': False,
                        'error_message': rules.get('error_message', f"Value must be at least {min_val}"),
                        'validation_level': 'error'
                    }
                
                if max_val is not None and num_value > max_val:
                    # Check if close to valid range
                    if min_val is not None:
                        range_size = max_val - min_val
                        diff = num_value - max_val
                        if diff <= range_size * 0.1:  # Within 10% of range
                            return {
                                'is_valid': False,
                                'error_message': rules.get('error_message', f"Value must be at most {max_val}"),
                                'validation_level': 'warning'
                            }
                    
                    return {
                        'is_valid': False,
                        'error_message': rules.get('error_message', f"Value must be at most {max_val}"),
                        'validation_level': 'error'
                    }
                    
            except (ValueError, TypeError):
                return {
                    'is_valid': False,
                    'error_message': f"{self.config.label} must be a valid number",
                    'validation_level': 'error'
                }
        
        # Format validation (regex patterns)
        elif rules.get('type') == 'format_validation':
            patterns = rules.get('patterns', [])
            if patterns and not any(re.match(pattern, str(value)) for pattern in patterns):
                return {
                    'is_valid': False,
                    'error_message': rules.get('error_message', f"Invalid format for {self.config.label}"),
                    'validation_level': 'error'
                }
        
        # Allowed values validation
        elif rules.get('allowed_values'):
            if str(value) not in rules['allowed_values']:
                return {
                    'is_valid': False,
                    'error_message': f"{self.config.label} must be one of: {', '.join(rules['allowed_values'])}",
                    'validation_level': 'error'
                }
        
        return {'is_valid': True, 'error_message': None, 'validation_level': 'info'}
    
    def _show_error(self, message: str) -> None:
        """Show validation error message"""
        self._validation_error = message
        if self.error_label and hasattr(self.error_label, 'configure'):
            try:
                self.error_label.configure(text=message, text_color="red")
            except Exception:
                print(f"DEBUG: Error label does not support configure method")
    
    def _clear_error(self) -> None:
        """Clear validation error message"""
        self._validation_error = None
        if self.error_label and hasattr(self.error_label, 'configure'):
            try:
                self.error_label.configure(text="", text_color="gray")
            except Exception:
                print(f"DEBUG: Error label does not support configure method")
    
    def _update_visual_feedback(self, is_valid: bool, validation_level: str = "error") -> None:
        """Update visual feedback based on validation state and level"""
        if not self.widget:
            return
            
        # Update border color based on validation state and level
        if hasattr(self.widget, 'configure'):
            try:
                if is_valid:
                    # Valid state - green border or default
                    if self._validation_error is None:
                        self.widget.configure(border_color="gray", border_width=1)
                    else:
                        # Was invalid but now valid - show green briefly
                        self.widget.configure(border_color="green", border_width=2)
                        # Schedule return to normal after 1 second
                        if hasattr(self.widget, 'after'):
                            self.widget.after(1000, lambda: self._reset_border_color())
                else:
                    # Invalid state - color based on validation level
                    if validation_level == "warning":
                        # Warning state - orange/yellow border
                        self.widget.configure(border_color="orange", border_width=2)
                    else:
                        # Error state - red border
                        self.widget.configure(border_color="red", border_width=2)
            except Exception as e:
                # Silently handle configure errors for custom widgets
                widget_type = type(self.widget).__name__
                print(f"DEBUG: Widget {widget_type} does not support visual feedback configuration")
    
    def _reset_border_color(self) -> None:
        """Reset border color to default"""
        if self.widget and hasattr(self.widget, 'configure'):
            try:
                self.widget.configure(border_color="gray", border_width=1)
            except:
                pass  # Widget may have been destroyed
    
    def set_visibility(self, visible: bool) -> None:
        """Set element visibility"""
        self.visible = visible
        if self.container_frame:
            if visible:
                self.container_frame.grid()
            else:
                self.container_frame.grid_remove()
    
    def get_validation_error(self) -> Optional[str]:
        """Get current validation error message"""
        return self._validation_error
    
    def _create_base_frame(self, parent) -> ctk.CTkFrame:
        """Create the base frame with label and error display"""
        self.container_frame = ctk.CTkFrame(parent)
        self.container_frame.grid_columnconfigure(1, weight=1)
        
        # Create label
        label_text = self.config.label
        if self.config.unit:
            label_text += f" ({self.config.unit})"
            
        self.label_widget = ctk.CTkLabel(
            self.container_frame, 
            text=label_text
        )
        self.label_widget.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        # Create error label (initially empty)
        self.error_label = ctk.CTkLabel(
            self.container_frame, 
            text="", 
            text_color="red"
        )
        self.error_label.grid(row=2, column=0, columnspan=2, padx=10, pady=(0, 5), sticky="w")
        
        return self.container_frame
    
    def set_value_change_callback(self, callback: Callable[[Any], None]) -> None:
        """Set callback for value changes"""
        self.value_change_callback = callback
    
    def _notify_value_change(self, value: Any) -> None:
        """Notify about value changes"""
        if self.value_change_callback:
            self.value_change_callback(value)
    
    def update_language_display(self, i18n_service) -> None:
        """Update element language display"""
        self.i18n = i18n_service
        if self.label_widget:
            # Use translation key if available, otherwise use original label
            if self.config.translation_key:
                label_text = i18n_service.get(self.config.translation_key, self.config.label)
            else:
                label_text = self.config.label
            
            # Add unit if present
            if self.config.unit:
                unit_text = i18n_service.get(self.config.unit, self.config.unit)
                label_text += f" ({unit_text})"
            
            self.label_widget.configure(text=label_text)


class TextInputElement(BaseUIElement):
    """Text input UI element"""
    
    def create_widget(self, parent) -> ctk.CTkFrame:
        frame = self._create_base_frame(parent)
        
        # Create text entry
        self.widget = ctk.CTkEntry(
            frame,
            width=200,
            placeholder_text=self.config.placeholder or ""
        )
        self.widget.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        
        # Set default value
        if self.config.default_value is not None:
            self.widget.insert(0, str(self.config.default_value))
        
        # Bind validation events
        self.widget.bind("<FocusOut>", self._on_focus_out)
        self.widget.bind("<KeyRelease>", self._on_key_release)
        
        return frame
    
    def get_value(self) -> Optional[str]:
        if not self.widget:
            return None
        text = self.widget.get().strip()
        return text if text else None
    
    def set_value(self, value: Any) -> None:
        if self.widget:
            self.widget.delete(0, ctk.END)
            if value is not None:
                self.widget.insert(0, str(value))
    
    def _on_focus_out(self, event) -> None:
        """Validate on focus out"""
        is_valid = self.validate()
        self._update_visual_feedback(is_valid, getattr(self, '_validation_level', 'error'))
        if self.validation_callback:
            self.validation_callback(self)
        # Notify value change
        self._notify_value_change(self.get_value())
    
    def _on_key_release(self, event) -> None:
        """Validate on key release with real-time feedback"""
        # Perform real-time validation
        is_valid = self.validate()
        self._update_visual_feedback(is_valid, getattr(self, '_validation_level', 'error'))
        # Notify value change
        self._notify_value_change(self.get_value())


class NumberInputElement(BaseUIElement):
    """Number input UI element with range validation"""
    
    def create_widget(self, parent) -> ctk.CTkFrame:
        frame = self._create_base_frame(parent)
        
        # Create number entry
        self.widget = ctk.CTkEntry(
            frame,
            width=150,
            placeholder_text=self.config.placeholder or "Enter number"
        )
        self.widget.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        
        # Set default value
        if self.config.default_value is not None:
            self.widget.insert(0, str(self.config.default_value))
        
        # Bind validation events
        self.widget.bind("<FocusOut>", self._on_focus_out)
        self.widget.bind("<KeyRelease>", self._on_key_release)
        
        # Add range info if available
        if self.config.range_config:
            range_info = self._create_range_info()
            range_info.grid(row=3, column=0, columnspan=2, padx=10, pady=(0, 5), sticky="w")
        
        return frame
    
    def get_value(self) -> Optional[Union[int, float]]:
        if not self.widget:
            return None
        
        text = self.widget.get().strip()
        if not text:
            return None
        
        try:
            # Check if integer is expected
            if self.config.validation_rules and self.config.validation_rules.get('integer', True):
                return int(text)
            else:
                return float(text)
        except ValueError:
            return None
    
    def set_value(self, value: Any) -> None:
        if self.widget:
            self.widget.delete(0, ctk.END)
            if value is not None:
                self.widget.insert(0, str(value))
    
    def _create_range_info(self) -> ctk.CTkLabel:
        """Create range information label"""
        range_config = self.config.range_config
        min_val = range_config.get('min')
        max_val = range_config.get('max')
        
        range_text = ""
        if min_val is not None and max_val is not None:
            range_text = f"Range: {min_val} - {max_val}"
        elif min_val is not None:
            range_text = f"Minimum: {min_val}"
        elif max_val is not None:
            range_text = f"Maximum: {max_val}"
        
        return ctk.CTkLabel(
            self.container_frame,
            text=range_text,
            text_color="gray"
        )
    
    def _on_focus_out(self, event) -> None:
        """Validate on focus out"""
        is_valid = self.validate()
        self._update_visual_feedback(is_valid, getattr(self, '_validation_level', 'error'))
        if self.validation_callback:
            self.validation_callback(self)
        # Notify value change
        self._notify_value_change(self.get_value())
    
    def _on_key_release(self, event) -> None:
        """Validate numeric input on key release with real-time feedback"""
        text = self.widget.get().strip()
        
        if not text:
            # Empty field - clear error and reset visual state
            self._clear_error()
            self._update_visual_feedback(True, 'info')
            self._notify_value_change(None)
            return
        
        # Check if it's a valid number format first
        try:
            if self.config.validation_rules and self.config.validation_rules.get('integer', True):
                int(text)
            else:
                float(text)
            
            # Valid number format - now validate range and other rules
            is_valid = self.validate()
            self._update_visual_feedback(is_valid, getattr(self, '_validation_level', 'error'))
            # Notify value change for valid numbers
            self._notify_value_change(self.get_value())
            
        except ValueError:
            # Invalid number format
            self._show_error(f"{self.config.label} must be a valid number")
            self._validation_level = 'error'
            self._update_visual_feedback(False, 'error')


class DropdownElement(BaseUIElement):
    """Dropdown selection UI element"""
    
    def create_widget(self, parent) -> ctk.CTkFrame:
        frame = self._create_base_frame(parent)
        
        # Create dropdown
        options = self.config.options or []
        self.widget = ctk.CTkComboBox(
            frame,
            values=options,
            state="readonly",
            width=200
        )
        self.widget.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        
        # Set default value
        if self.config.default_value and self.config.default_value in options:
            self.widget.set(self.config.default_value)
        elif options:
            self.widget.set(options[0])
        
        # Bind selection event
        self.widget.bind("<<ComboboxSelected>>", self._on_selection_change)
        
        return frame
    
    def get_value(self) -> Optional[str]:
        if not self.widget:
            return None
        return self.widget.get()
    
    def set_value(self, value: Any) -> None:
        if self.widget and value is not None:
            if str(value) in (self.config.options or []):
                self.widget.set(str(value))
    
    def _on_selection_change(self, event) -> None:
        """Handle selection change with real-time validation"""
        is_valid = self.validate()
        self._update_visual_feedback(is_valid, getattr(self, '_validation_level', 'error'))
        if self.validation_callback:
            self.validation_callback(self)
        # Notify value change
        self._notify_value_change(self.get_value())


class ToggleSwitchElement(BaseUIElement):
    """Toggle switch UI element for boolean values"""
    
    def __init__(self, config: UIElementConfig, i18n_service, validation_callback: Optional[Callable] = None):
        super().__init__(config, i18n_service, validation_callback)
        self.switch_var = None
        self.status_label = None
    
    def create_widget(self, parent) -> ctk.CTkFrame:
        frame = self._create_base_frame(parent)
        
        # Create switch variable
        self.switch_var = ctk.BooleanVar()
        
        # Create toggle switch
        self.widget = ctk.CTkSwitch(
            frame,
            text="",
            variable=self.switch_var,
            command=self._on_toggle_change
        )
        self.widget.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        # Add status label
        self.status_label = ctk.CTkLabel(
            frame,
            text="Disabled",
            text_color="gray"
        )
        self.status_label.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        # Set default value
        if self.config.default_value is not None:
            self.switch_var.set(bool(self.config.default_value))
            self._update_status_label()
        
        return frame
    
    def get_value(self) -> Optional[bool]:
        if not self.switch_var:
            return None
        return self.switch_var.get()
    
    def set_value(self, value: Any) -> None:
        if self.switch_var:
            self.switch_var.set(bool(value) if value is not None else False)
            self._update_status_label()
    
    def _on_toggle_change(self) -> None:
        """Handle toggle change with real-time validation"""
        self._update_status_label()
        is_valid = self.validate()
        self._update_visual_feedback(is_valid, getattr(self, '_validation_level', 'error'))
        if self.validation_callback:
            self.validation_callback(self)
        # Notify value change
        self._notify_value_change(self.get_value())
    
    def _update_status_label(self) -> None:
        """Update status label text"""
        if self.status_label:
            status = self.i18n.get("enabled", "Enabled") if self.switch_var.get() else self.i18n.get("disabled", "Disabled")
            color = "green" if self.switch_var.get() else "gray"
            self.status_label.configure(text=status, text_color=color)
    
    def update_language_display(self, i18n_service) -> None:
        """Update element language display"""
        super().update_language_display(i18n_service)
        # Update status label with new language
        self._update_status_label()


class SliderElement(BaseUIElement):
    """Slider UI element for range values"""
    
    def __init__(self, config: UIElementConfig, i18n_service, validation_callback: Optional[Callable] = None):
        super().__init__(config, i18n_service, validation_callback)
        self.slider_var = None
        self.value_label = None
    
    def create_widget(self, parent) -> ctk.CTkFrame:
        frame = self._create_base_frame(parent)
        
        # Get range configuration
        range_config = self.config.range_config or {}
        min_val = range_config.get('min', 1)
        max_val = range_config.get('max', 6)
        
        # Create slider
        self.widget = ctk.CTkSlider(
            frame,
            from_=min_val,
            to=max_val,
            number_of_steps=max_val - min_val,
            command=self._on_slider_change
        )
        self.widget.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        # Create value display label
        self.value_label = ctk.CTkLabel(
            frame,
            text=str(int(min_val)),
            width=40
        )
        self.value_label.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        # Set default value
        if self.config.default_value is not None:
            self.widget.set(self.config.default_value)
            self.value_label.configure(text=str(int(self.config.default_value)))
        else:
            self.widget.set(min_val)
            self.value_label.configure(text=str(int(min_val)))
        
        # Add range info
        range_info = ctk.CTkLabel(
            frame,
            text=f"Range: {min_val} (Low) - {max_val} (High)",
            text_color="gray"
        )
        range_info.grid(row=3, column=0, columnspan=2, padx=10, pady=(0, 5), sticky="w")
        
        return frame
    
    def get_value(self) -> Optional[int]:
        if not self.widget:
            return None
        return int(self.widget.get())
    
    def set_value(self, value: Any) -> None:
        if self.widget and value is not None:
            try:
                int_value = int(value)
                self.widget.set(int_value)
                self.value_label.configure(text=str(int_value))
            except (ValueError, TypeError):
                pass
    
    def _on_slider_change(self, value) -> None:
        """Handle slider value change with real-time validation"""
        int_value = int(value)
        self.value_label.configure(text=str(int_value))
        is_valid = self.validate()
        self._update_visual_feedback(is_valid, getattr(self, '_validation_level', 'error'))
        if self.validation_callback:
            self.validation_callback(self)
        # Notify value change
        self._notify_value_change(self.get_value())


class PasswordInputElement(BaseUIElement):
    """Password input UI element with show/hide functionality"""
    
    def __init__(self, config: UIElementConfig, i18n_service, validation_callback: Optional[Callable] = None):
        super().__init__(config, i18n_service, validation_callback)
        self.show_password = False
        self.toggle_button = None
    
    def create_widget(self, parent) -> ctk.CTkFrame:
        frame = self._create_base_frame(parent)
        
        # Create password entry frame
        entry_frame = ctk.CTkFrame(frame)
        entry_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        entry_frame.grid_columnconfigure(0, weight=1)
        
        # Create password entry
        self.widget = ctk.CTkEntry(
            entry_frame,
            show="*",
            placeholder_text=self.config.placeholder or "Enter password"
        )
        self.widget.grid(row=0, column=0, padx=(0, 5), pady=0, sticky="ew")
        
        # Create show/hide toggle button
        self.toggle_button = ctk.CTkButton(
            entry_frame,
            text="👁",
            width=30,
            command=self._toggle_password_visibility
        )
        self.toggle_button.grid(row=0, column=1, padx=0, pady=0)
        
        # Set default value
        if self.config.default_value is not None:
            self.widget.insert(0, str(self.config.default_value))
        
        # Bind validation events
        self.widget.bind("<FocusOut>", self._on_focus_out)
        self.widget.bind("<KeyRelease>", self._on_key_release)
        
        return frame
    
    def get_value(self) -> Optional[str]:
        if not self.widget:
            return None
        text = self.widget.get().strip()
        return text if text else None
    
    def set_value(self, value: Any) -> None:
        if self.widget:
            self.widget.delete(0, ctk.END)
            if value is not None:
                self.widget.insert(0, str(value))
    
    def _toggle_password_visibility(self) -> None:
        """Toggle password visibility"""
        self.show_password = not self.show_password
        if self.show_password:
            self.widget.configure(show="")
            self.toggle_button.configure(text="🙈")
        else:
            self.widget.configure(show="*")
            self.toggle_button.configure(text="👁")
    
    def _on_focus_out(self, event) -> None:
        """Validate on focus out"""
        is_valid = self.validate()
        self._update_visual_feedback(is_valid, getattr(self, '_validation_level', 'error'))
        if self.validation_callback:
            self.validation_callback(self)
        # Notify value change
        self._notify_value_change(self.get_value())
    
    def _on_key_release(self, event) -> None:
        """Validate on key release with real-time feedback"""
        is_valid = self.validate()
        self._update_visual_feedback(is_valid, getattr(self, '_validation_level', 'error'))
        # Notify value change
        self._notify_value_change(self.get_value())


class ParameterUIElementFactory:
    """Factory class for creating parameter UI elements"""
    
    def __init__(self, i18n_service):
        self.i18n_service = i18n_service
        self._element_classes = {
            'text_input': TextInputElement,
            'number_input': NumberInputElement,
            'dropdown': DropdownElement,
            'toggle_switch': ToggleSwitchElement,
            'slider': SliderElement,
            'password_input': PasswordInputElement
        }
    
    def create_element(self, element_type: str, config: UIElementConfig, 
                      validation_callback: Optional[Callable] = None) -> BaseUIElement:
        """
        Create a UI element of the specified type.
        
        Args:
            element_type: Type of UI element to create
            config: Configuration for the element
            validation_callback: Optional callback for validation events
            
        Returns:
            BaseUIElement instance
            
        Raises:
            ValueError: If element_type is not supported
        """
        if element_type not in self._element_classes:
            raise ValueError(f"Unsupported element type: {element_type}. "
                           f"Supported types: {list(self._element_classes.keys())}")
        
        element_class = self._element_classes[element_type]
        return element_class(config, self.i18n_service, validation_callback)
    
    def create_element_from_field_config(self, field_config, validation_rules: Optional[Dict] = None,
                                       validation_callback: Optional[Callable] = None) -> BaseUIElement:
        """
        Create a UI element from a field configuration.
        
        Args:
            field_config: Field configuration from parameter specification
            validation_rules: Optional validation rules
            validation_callback: Optional callback for validation events
            
        Returns:
            BaseUIElement instance
        """
        # Build range config for sliders and number inputs
        range_config = None
        if hasattr(field_config, 'validation') and field_config.validation:
            # Parse validation string like "1-6" or "5-600"
            if '-' in field_config.validation:
                try:
                    min_val, max_val = field_config.validation.split('-')
                    range_config = {'min': int(min_val), 'max': int(max_val)}
                except ValueError:
                    pass
        
        # Create UI element configuration
        ui_config = UIElementConfig(
            element_type=field_config.ui_element,
            label=field_config.label,
            validation_rules=validation_rules,
            options=getattr(field_config, 'options', None),
            range_config=range_config,
            unit=getattr(field_config, 'unit', None),
            visibility_condition=getattr(field_config, 'visibility_condition', None)
        )
        
        return self.create_element(field_config.ui_element, ui_config, validation_callback)
    
    def get_supported_element_types(self) -> List[str]:
        """Get list of supported UI element types"""
        return list(self._element_classes.keys())
    
    def validate_element_type(self, element_type: str) -> bool:
        """Check if an element type is supported"""
        return element_type in self._element_classes