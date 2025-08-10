"""
ValidationMixin - Enhanced reusable validation UI components for real-time parameter validation.

This mixin provides comprehensive validation UI functionality including:
- Progressive validation feedback with severity levels
- Contextual help tooltips
- Validation error recovery suggestions
- Validation history tracking
- Interactive APN format helper
"""

import customtkinter as ctk
from typing import Callable, Dict, Any, Optional, List
from dataclasses import dataclass
from components.apn_validation_component import APNValidationComponent, ValidationResult
from ui.apn_help_tooltip import APNHelpTooltip, APNCarrierHelper
from services.validation_history_tracker import ValidationHistoryTracker
from utils.widget_parent_resolver import (
    get_widget_parent, get_widget_parent_with_details, log_widget_access_debug,
    log_widget_access_failure, log_widget_access_warning, log_widget_hierarchy_analysis,
    ensure_application_continues
)


@dataclass
class ValidationState:
    """Represents the current validation state of a field"""
    is_valid: bool
    error_message: str = ""
    warning_message: str = ""
    info_message: str = ""
    suggestions: List[str] = None
    validation_level: str = "error"  # "error", "warning", "info", "success"
    severity_score: int = 0  # 0=info, 1=warning, 2=error, 3=critical
    recovery_suggestions: List[str] = None
    
    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []
        if self.recovery_suggestions is None:
            self.recovery_suggestions = []


class ValidationMixin:
    """Enhanced mixin class providing comprehensive validation UI components and functionality"""
    
    def __init__(self):
        # Initialize validation state tracking
        self._validation_states: Dict[str, ValidationState] = {}
        self._validation_callbacks: Dict[str, Callable] = {}
        self._validation_timers: Dict[str, str] = {}  # Store timer IDs for debouncing
        self._validation_widgets: Dict[str, Dict[str, Any]] = {}  # Store widget references
        self._validation_tooltips: Dict[str, APNHelpTooltip] = {}  # Store tooltip references
        self._validation_message_widgets: Dict[str, ctk.CTkLabel] = {}  # Store message label references
        
        # Initialize validation components
        self._apn_validator = APNValidationComponent()
        self._validation_history = ValidationHistoryTracker()
        self._carrier_helper = None  # Will be initialized when needed
        
    def _get_widget_value(self, widget: Any) -> str:
        """Get value from widget, handling different widget types."""
        try:
            # Try direct get() method first (CTkEntry, Entry, etc.)
            if hasattr(widget, 'get'):
                return widget.get()
            
            # Try StringVar if it exists
            if hasattr(widget, 'variable') and widget.variable is not None:
                return widget.variable.get()
            
            # Try text property (Text widgets)
            if hasattr(widget, 'get_text'):
                return widget.get_text()
            elif hasattr(widget, 'get_all_text'):
                return widget.get_all_text()
            elif hasattr(widget, 'get') and callable(widget.get):
                try:
                    value = widget.get('1.0', 'end-1c')
                    if isinstance(value, str):
                        return value
                except:
                    pass
            
            # Try value property
            if hasattr(widget, 'value'):
                return str(widget.value)
            
            # Try cget for some customtkinter widgets
            if hasattr(widget, 'cget'):
                try:
                    text = widget.cget('text')
                    if text:
                        return text
                except:
                    pass
            
            # Log failure but don't raise error
            print(f"Warning: Could not get value from widget {type(widget)}")
            print(f"Widget attributes: {dir(widget)}")
            return ""
            
        except Exception as e:
            print(f"Error getting widget value: {str(e)}")
            return ""
        
        # Progressive validation colors with severity levels
        self._validation_colors = {
            'error': '#ff4444',      # Red for errors
            'warning': '#ffaa00',    # Orange for warnings  
            'info': '#2196F3',       # Blue for info
            'success': '#00aa44',    # Green for success
            'normal': '#565b5e',     # Default border color
            'focus': '#1f538d',      # Focus color
            'critical': '#cc0000'    # Dark red for critical errors
        }
        
        # Validation message templates
        self._message_templates = {
            'progressive_help': "💡 {message}",
            'error_recovery': "🔧 Try: {suggestion}",
            'success_feedback': "✅ {message}",
            'learning_tip': "📚 Tip: {tip}"
        }
    
    @ensure_application_continues("setup_real_time_validation", critical=False)
    def setup_real_time_validation(self, field_name: str, widget: Any, validation_callback: Callable, 
                                 debounce_ms: int = 500, enable_tooltips: bool = True,
                                 enable_message_display: bool = True) -> None:
        """
        Set up enhanced real-time validation for a field with progressive feedback.
        
        Args:
            field_name: Unique identifier for the field
            widget: The UI widget to validate
            validation_callback: Function to call for validation
            debounce_ms: Debounce delay in milliseconds
            enable_tooltips: Whether to enable contextual help tooltips
            enable_message_display: Whether to show validation messages below field
        """
        try:
            # Log setup attempt
            log_widget_access_debug(widget, f"setup_validation_{field_name}")
            
            # Store validation callback
            self._validation_callbacks[field_name] = validation_callback
            
            # Store widget reference
            self._validation_widgets[field_name] = {
                'widget': widget,
                'debounce_ms': debounce_ms,
                'enable_tooltips': enable_tooltips,
                'enable_message_display': enable_message_display
            }
            
            # Initialize validation state
            self._validation_states[field_name] = ValidationState(is_valid=True)
            
            # Set up contextual help tooltip if enabled
            if enable_tooltips and field_name.startswith('apn'):
                try:
                    tooltip = APNHelpTooltip(widget, field_name, getattr(self, 'i18n', None))
                    self._validation_tooltips[field_name] = tooltip
                except Exception as tooltip_error:
                    log_widget_access_warning(
                        widget, 
                        f"tooltip_setup_{field_name}",
                        f"Failed to create tooltip: {str(tooltip_error)}",
                        "Continuing without tooltip"
                    )
            
            # Set up validation message display if enabled
            if enable_message_display:
                self._setup_validation_message_display(field_name, widget)
            
            # Bind events to widget
            self._bind_validation_events(field_name, widget, debounce_ms)
            
            print(f"Successfully set up validation for {field_name}")
            
        except Exception as e:
            log_widget_access_failure(
                widget=widget,
                context=f"setup_validation_{field_name}",
                exception=e,
                fallback_used=True,
                fallback_description="Validation setup skipped, field will work without enhanced validation"
            )
    
    @ensure_application_continues("setup_validation_message_display", critical=False)
    def _setup_validation_message_display(self, field_name: str, widget: Any) -> None:
        """
        Set up validation message display below field using robust parent resolution.
        
        This method implements multiple strategies to find a suitable parent container
        for the validation message display, with comprehensive error handling and
        graceful fallback when parent widgets cannot be accessed.
        
        Args:
            field_name: Unique identifier for the field
            widget: The UI widget to set up message display for
        """
        try:
            # Log detailed widget hierarchy for debugging
            log_widget_hierarchy_analysis(widget, f"message_display_setup_{field_name}")
            
            # Strategy 1: Use robust parent resolution utility
            parent_result = get_widget_parent_with_details(widget)
            
            if parent_result.success and parent_result.parent is not None:
                # Primary strategy succeeded
                parent = parent_result.parent
                
                try:
                    # Create message label widget
                    message_widget = self._create_validation_message_widget(parent, field_name)
                    
                    if message_widget:
                        self._validation_message_widgets[field_name] = message_widget
                        print(f"Successfully created message display for {field_name} using method '{parent_result.method_used}'")
                        return
                    else:
                        log_widget_access_warning(
                            widget,
                            f"message_widget_creation_{field_name}",
                            "Failed to create message widget despite finding parent",
                            "Trying alternative display modes"
                        )
                        
                except Exception as widget_creation_error:
                    log_widget_access_failure(
                        widget=parent,
                        context=f"message_widget_creation_{field_name}",
                        exception=widget_creation_error,
                        fallback_used=True,
                        fallback_description="Trying alternative message display strategies"
                    )
            else:
                # Parent resolution failed
                log_widget_access_warning(
                    widget,
                    f"parent_resolution_{field_name}",
                    f"Parent resolution failed using method '{parent_result.method_used}'",
                    "Trying alternative display strategies"
                )
            
            # Strategy 2: Try alternative display modes
            alternative_mode = self._setup_alternative_message_display(field_name, widget)
            
            if alternative_mode:
                self._validation_message_widgets[field_name] = alternative_mode
                log_widget_access_warning(
                    widget,
                    f"alternative_display_{field_name}",
                    f"Using alternative display mode: {alternative_mode}",
                    "Message display will work with reduced functionality"
                )
                return
            
            # Strategy 3: Final fallback to console mode
            self._validation_message_widgets[field_name] = "console_mode"
            log_widget_access_warning(
                widget,
                f"console_fallback_{field_name}",
                "All message display strategies failed",
                "Using console output for validation messages"
            )
            
        except Exception as e:
            # Ultimate fallback - log error and continue without message display
            log_widget_access_failure(
                widget=widget,
                context=f"setup_message_display_{field_name}",
                exception=e,
                fallback_used=True,
                fallback_description="Message display setup completely skipped"
            )
            
            # Ensure we don't break the application
            self._validation_message_widgets[field_name] = "console_mode"
    
    def _create_validation_message_widget(self, parent: Any, field_name: str) -> Any:
        """
        Create a validation message widget with error handling.
        
        Args:
            parent: Parent widget to create the message widget in
            field_name: Field name for the message widget
            
        Returns:
            Created message widget or None if creation failed
        """
        try:
            # Import here to avoid circular imports
            import customtkinter as ctk
            
            # Create message label
            message_widget = ctk.CTkLabel(
                parent,
                text="",
                font=ctk.CTkFont(size=10),
                text_color="#888888",
                anchor="w",
                justify="left"
            )
            
            # Try to position the widget
            positioning_success = self._position_message_widget(message_widget, parent, field_name)
            
            if not positioning_success:
                log_widget_access_warning(
                    parent,
                    f"message_positioning_{field_name}",
                    "Failed to position message widget",
                    "Widget created but may not be visible"
                )
            
            return message_widget
            
        except Exception as e:
            log_widget_access_failure(
                widget=parent,
                context=f"create_message_widget_{field_name}",
                exception=e,
                fallback_used=False,
                fallback_description=""
            )
            return None
    
    def _position_message_widget(self, message_widget: Any, parent: Any, field_name: str) -> bool:
        """
        Try to position a message widget using multiple strategies.
        
        Args:
            message_widget: The message widget to position
            parent: Parent widget
            field_name: Field name for logging
            
        Returns:
            True if positioning succeeded, False otherwise
        """
        positioning_strategies = [
            ("pack", lambda: message_widget.pack(anchor="w", padx=(5, 0), pady=(2, 5))),
            ("grid", lambda: message_widget.grid(sticky="w", padx=(5, 0), pady=(2, 5))),
            ("place", lambda: message_widget.place(x=5, y=0)),
        ]
        
        for strategy_name, strategy_func in positioning_strategies:
            try:
                strategy_func()
                print(f"Successfully positioned message widget for {field_name} using {strategy_name}")
                return True
            except Exception as pos_error:
                log_widget_access_warning(
                    message_widget,
                    f"positioning_{strategy_name}_{field_name}",
                    f"Positioning strategy '{strategy_name}' failed: {str(pos_error)}",
                    f"Trying next positioning strategy"
                )
                continue
        
        return False
    
    def _setup_alternative_message_display(self, field_name: str, widget: Any) -> Optional[str]:
        """
        Set up alternative message display modes when standard widget creation fails.
        
        Args:
            field_name: Field name
            widget: Original widget
            
        Returns:
            String identifier for alternative display mode or None if all failed
        """
        try:
            # Try tooltip mode if widget supports it
            if hasattr(widget, 'bind') and hasattr(widget, 'winfo_rootx'):
                try:
                    # Test if we can get widget position (needed for tooltips)
                    widget.winfo_rootx()
                    return "tooltip_mode"
                except Exception:
                    pass
            
            # Try status mode if we have access to a status bar
            if hasattr(self, 'master') and hasattr(self.master, 'status_bar'):
                return "status_mode"
            
            # Try floating mode for widgets that support geometry
            if hasattr(widget, 'winfo_x') and hasattr(widget, 'winfo_y'):
                try:
                    widget.winfo_x()
                    widget.winfo_y()
                    return "floating_mode"
                except Exception:
                    pass
            
            # Default to console mode
            return "console_mode"
            
        except Exception as e:
            log_widget_access_warning(
                widget,
                f"alternative_display_setup_{field_name}",
                f"Error setting up alternative display: {str(e)}",
                "Defaulting to console mode"
            )
            return "console_mode"
    
    @ensure_application_continues("bind_validation_events", critical=False)
    def _bind_validation_events(self, field_name: str, widget: Any, debounce_ms: int) -> None:
        """Bind validation events to a widget with comprehensive error handling"""
        try:
            events_bound = []
            
            # Try to bind to main widget
            if hasattr(widget, 'bind'):
                try:
                    widget.bind('<KeyRelease>', lambda e: self._schedule_validation(field_name, debounce_ms))
                    widget.bind('<FocusOut>', lambda e: self._validate_field_immediately(field_name))
                    widget.bind('<FocusIn>', lambda e: self._on_field_focus(field_name))
                    events_bound.append("main_widget")
                except Exception as bind_error:
                    log_widget_access_warning(
                        widget,
                        f"bind_main_events_{field_name}",
                        f"Failed to bind main widget events: {str(bind_error)}",
                        "Trying alternative binding methods"
                    )
            
            # For CustomTkinter widgets, also try to bind to internal entry
            if hasattr(widget, '_entry') and hasattr(widget._entry, 'bind'):
                try:
                    widget._entry.bind('<KeyRelease>', lambda e: self._schedule_validation(field_name, debounce_ms))
                    widget._entry.bind('<FocusOut>', lambda e: self._validate_field_immediately(field_name))
                    widget._entry.bind('<FocusIn>', lambda e: self._on_field_focus(field_name))
                    events_bound.append("internal_entry")
                except Exception as entry_bind_error:
                    log_widget_access_warning(
                        widget,
                        f"bind_entry_events_{field_name}",
                        f"Failed to bind internal entry events: {str(entry_bind_error)}",
                        "Validation will work with reduced event coverage"
                    )
            
            if events_bound:
                print(f"Successfully bound validation events for {field_name} using: {', '.join(events_bound)}")
            else:
                log_widget_access_warning(
                    widget,
                    f"event_binding_{field_name}",
                    "No event binding methods succeeded",
                    "Manual validation will still work"
                )
                
        except Exception as e:
            log_widget_access_failure(
                widget=widget,
                context=f"bind_events_{field_name}",
                exception=e,
                fallback_used=True,
                fallback_description="Event binding skipped, manual validation still available"
            )
    
    def _schedule_validation(self, field_name: str, debounce_ms: int) -> None:
        """Schedule validation with debouncing"""
        try:
            # Cancel previous timer if exists
            if field_name in self._validation_timers:
                if hasattr(self, 'after_cancel'):
                    self.after_cancel(self._validation_timers[field_name])
            
            # Schedule new validation
            if hasattr(self, 'after'):
                timer_id = self.after(debounce_ms, lambda: self._validate_field_immediately(field_name))
                self._validation_timers[field_name] = timer_id
            else:
                # Fallback to immediate validation if after method not available
                self._validate_field_immediately(field_name)
                
        except Exception as e:
            print(f"Error scheduling validation for {field_name}: {e}")
    
    def _validate_field_immediately(self, field_name: str) -> None:
        """Validate a field immediately and update UI feedback with progressive feedback"""
        try:
            if field_name not in self._validation_callbacks:
                return
            
            # Get current field value
            widget_info = self._validation_widgets.get(field_name)
            if not widget_info:
                return
                
            widget = widget_info['widget']
            value = self._get_widget_value(widget)
            
            # Call validation callback
            validation_callback = self._validation_callbacks[field_name]
            result = validation_callback(value)
            
            # Use progressive validation feedback
            if isinstance(result, ValidationResult):
                self.show_progressive_validation_feedback(field_name, result, value)
            else:
                # Handle simple boolean result - create ValidationResult
                simple_result = ValidationResult(
                    is_valid=bool(result),
                    error_message="Invalid input" if not bool(result) else "",
                    error_code="VALIDATION_FAILED" if not bool(result) else "",
                    suggestions=[],
                    field_name=field_name,
                    validated_value=value
                )
                self.show_progressive_validation_feedback(field_name, simple_result, value)
            
        except Exception as e:
            print(f"Error validating field {field_name}: {e}")
    
    def _on_field_focus(self, field_name: str) -> None:
        """Handle field focus event"""
        try:
            widget_info = self._validation_widgets.get(field_name)
            if not widget_info:
                return
                
            widget = widget_info['widget']
            
            # Update border color to focus color
            if hasattr(widget, 'configure'):
                widget.configure(border_color=self._validation_colors['focus'])
                
        except Exception as e:
            print(f"Error handling focus for {field_name}: {e}")
    
    def _get_widget_value(self, widget: Any) -> str:
        """Get value from a widget, handling different widget types"""
        try:
            if hasattr(widget, 'get_value'):
                return str(widget.get_value() or "")
            elif hasattr(widget, 'get'):
                return str(widget.get() or "")
            elif hasattr(widget, '_entry') and hasattr(widget._entry, 'get'):
                return str(widget._entry.get() or "")
            else:
                return ""
        except Exception:
            return ""
    
    def _update_validation_feedback(self, field_name: str) -> None:
        """Update visual validation feedback for a field"""
        try:
            state = self._validation_states.get(field_name)
            widget_info = self._validation_widgets.get(field_name)
            
            if not state or not widget_info:
                return
                
            widget = widget_info['widget']
            
            # Update widget border color based on validation state
            if hasattr(widget, 'configure'):
                if not state.is_valid:
                    color = self._validation_colors['error']
                elif state.validation_level == "warning":
                    color = self._validation_colors['warning']
                elif state.validation_level == "success" and self._get_widget_value(widget):
                    color = self._validation_colors['success']
                else:
                    color = self._validation_colors['normal']
                
                widget.configure(border_color=color)
            
            # Update tooltip or error message display if available
            self._update_validation_message_display(field_name, state)
            
        except Exception as e:
            print(f"Error updating validation feedback for {field_name}: {e}")
    
    def _update_validation_message_display(self, field_name: str, state: ValidationState) -> None:
        """Update validation message display with support for multiple display modes"""
        try:
            message_widget = self._validation_message_widgets.get(field_name)
            
            if message_widget is None:
                # No message display available, use console fallback
                self._update_console_validation_display(field_name, state)
                return
            
            # Handle different display modes
            if isinstance(message_widget, str):
                # Alternative display modes
                self._update_alternative_message_display(field_name, state, message_widget)
            else:
                # Standard CTkLabel widget
                self._update_standard_message_display(field_name, state, message_widget)
                
        except Exception as e:
            print(f"Error updating validation message display for {field_name}: {e}")
            # Fallback to console display
            self._update_console_validation_display(field_name, state)
    
    def _update_standard_message_display(self, field_name: str, state: ValidationState, message_widget: Any) -> None:
        """Update standard CTkLabel message display"""
        try:
            # Prepare message text and color
            message_text, message_color = self._prepare_validation_message(field_name, state)
            
            # Update the message widget
            try:
                message_widget.configure(text=message_text, text_color=message_color)
                
                # Show/hide the widget based on whether there's a message
                if message_text:
                    # Try different methods to show the widget
                    try:
                        message_widget.pack(anchor="w", padx=(5, 0), pady=(2, 5))
                    except Exception:
                        try:
                            message_widget.grid(sticky="w", padx=(5, 0), pady=(2, 5))
                        except Exception:
                            try:
                                message_widget.place(x=5, y=0)
                            except Exception:
                                pass  # Widget exists but can't be positioned
                else:
                    # Hide the widget
                    try:
                        message_widget.pack_forget()
                    except Exception:
                        try:
                            message_widget.grid_forget()
                        except Exception:
                            try:
                                message_widget.place_forget()
                            except Exception:
                                pass  # Can't hide widget, but that's okay
                        
            except Exception as widget_error:
                print(f"Error updating message widget for {field_name}: {widget_error}")
                # Fallback to console display
                self._update_console_validation_display(field_name, state)
                
        except Exception as e:
            print(f"Error in standard message display update for {field_name}: {e}")
    
    def _update_alternative_message_display(self, field_name: str, state: ValidationState, display_mode: str) -> None:
        """Update alternative message display modes"""
        try:
            message_text, message_color = self._prepare_validation_message(field_name, state)
            
            if display_mode == "tooltip_mode":
                self._update_tooltip_message_display(field_name, message_text, message_color)
            elif display_mode == "status_mode":
                self._update_status_message_display(field_name, message_text, message_color)
            elif display_mode == "floating_mode":
                self._update_floating_message_display(field_name, message_text, message_color)
            elif display_mode == "console_mode":
                self._update_console_validation_display(field_name, state)
            else:
                # Unknown mode, fallback to console
                self._update_console_validation_display(field_name, state)
                
        except Exception as e:
            print(f"Error updating alternative message display for {field_name}: {e}")
    
    def _prepare_validation_message(self, field_name: str, state: ValidationState) -> tuple:
        """Prepare validation message text and color based on state"""
        message_text = ""
        message_color = "#888888"  # Default gray
        
        if not state.is_valid and state.error_message:
            message_text = f"❌ {state.error_message}"
            message_color = self._validation_colors.get('error', '#ff4444')
            
            # Add first suggestion if available
            if state.suggestions and len(state.suggestions) > 0:
                message_text += f"\n💡 {state.suggestions[0]}"
                
            # Add recovery suggestions if available
            if state.recovery_suggestions and len(state.recovery_suggestions) > 0:
                message_text += f"\n🔧 {state.recovery_suggestions[0]}"
                
        elif state.warning_message:
            message_text = f"⚠️ {state.warning_message}"
            message_color = self._validation_colors.get('warning', '#ffaa00')
            
        elif state.info_message:
            message_text = f"ℹ️ {state.info_message}"
            message_color = self._validation_colors.get('info', '#2196F3')
            
        elif state.is_valid and state.validation_level == "success":
            # Show success message briefly for positive feedback
            widget_info = self._validation_widgets.get(field_name)
            if widget_info:
                widget = widget_info['widget']
                current_value = self._get_widget_value(widget)
                if current_value and current_value.strip():
                    message_text = "✅ Valid"
                    message_color = self._validation_colors.get('success', '#00aa44')
        
        return message_text, message_color
    
    def _update_tooltip_message_display(self, field_name: str, message_text: str, message_color: str) -> None:
        """Update tooltip-style message display"""
        try:
            if message_text:
                print(f"Tooltip for {field_name}: {message_text}")
        except Exception as e:
            print(f"Error updating tooltip display for {field_name}: {e}")
    
    def _update_status_message_display(self, field_name: str, message_text: str, message_color: str) -> None:
        """Update status bar message display"""
        try:
            if message_text:
                print(f"Status for {field_name}: {message_text}")
        except Exception as e:
            print(f"Error updating status display for {field_name}: {e}")
    
    def _update_floating_message_display(self, field_name: str, message_text: str, message_color: str) -> None:
        """Update floating message display"""
        try:
            if message_text:
                print(f"Floating message for {field_name}: {message_text}")
        except Exception as e:
            print(f"Error updating floating display for {field_name}: {e}")
    
    def _update_console_validation_display(self, field_name: str, state: ValidationState) -> None:
        """Update console-based validation display as final fallback"""
        try:
            if not state.is_valid and state.error_message:
                print(f"Validation error for {field_name}: {state.error_message}")
                if state.suggestions:
                    print(f"Suggestions for {field_name}: {', '.join(state.suggestions)}")
                if state.recovery_suggestions:
                    print(f"Recovery suggestions for {field_name}: {', '.join(state.recovery_suggestions)}")
            elif state.warning_message:
                print(f"Validation warning for {field_name}: {state.warning_message}")
            elif state.info_message:
                print(f"Validation info for {field_name}: {state.info_message}")
            elif state.is_valid and state.validation_level == "success":
                widget_info = self._validation_widgets.get(field_name)
                if widget_info:
                    widget = widget_info['widget']
                    current_value = self._get_widget_value(widget)
                    if current_value and current_value.strip():
                        print(f"Validation success for {field_name}: Valid input")
        except Exception as e:
            print(f"Error in console validation display for {field_name}: {e}")
    
    def show_progressive_validation_feedback(self, field_name: str, validation_result, user_input: str) -> None:
        """Show progressive validation feedback with enhanced recovery suggestions"""
        try:
            # Update validation state with progressive feedback
            severity_score = self._calculate_severity_score(validation_result)
            validation_level = self._determine_validation_level(validation_result, severity_score)
            
            # Get enhanced recovery suggestions
            recovery_suggestions = self._get_enhanced_recovery_suggestions(field_name, validation_result, user_input)
            
            # Create validation state
            self._validation_states[field_name] = ValidationState(
                is_valid=validation_result.is_valid,
                error_message=validation_result.error_message if not validation_result.is_valid else "",
                suggestions=validation_result.suggestions or [],
                validation_level=validation_level,
                severity_score=severity_score,
                recovery_suggestions=recovery_suggestions
            )
            
            # Update UI feedback
            self._update_validation_feedback(field_name)
            
        except Exception as e:
            print(f"Error showing progressive validation feedback for {field_name}: {e}")
    
    def _calculate_severity_score(self, validation_result) -> int:
        """Calculate severity score based on validation result"""
        if validation_result.is_valid:
            return 0  # Success
        
        # Check error code for severity hints
        error_code = getattr(validation_result, 'error_code', '')
        if 'CRITICAL' in error_code or 'SECURITY' in error_code:
            return 3  # Critical
        elif 'WARNING' in error_code or 'FORMAT' in error_code:
            return 1  # Warning
        else:
            return 2  # Error
    
    def _determine_validation_level(self, validation_result, severity_score: int) -> str:
        """Determine validation level based on result and severity"""
        if validation_result.is_valid:
            return "success"
        elif severity_score == 3:
            return "critical"
        elif severity_score == 1:
            return "warning"
        else:
            return "error"
    
    def _get_enhanced_recovery_suggestions(self, field_name: str, validation_result, user_input: str) -> List[str]:
        """Get enhanced contextual recovery suggestions"""
        recovery_suggestions = []
        
        # Add specific suggestions from validation result
        if hasattr(validation_result, 'suggestions') and validation_result.suggestions:
            recovery_suggestions.extend(validation_result.suggestions[:2])
        
        # Add field-specific suggestions
        if field_name.startswith('apn'):
            recovery_suggestions.extend([
                "Check APN format (e.g., internet.provider.com)",
                "Verify with your carrier's documentation"
            ])
        
        return recovery_suggestions[:3]  # Limit to 3 suggestions
    
    def is_form_valid(self) -> bool:
        """Check if all validated fields in the form are valid"""
        try:
            for state in self._validation_states.values():
                if not state.is_valid:
                    return False
            return True
        except Exception:
            return False
    
    def get_validation_errors(self) -> Dict[str, str]:
        """Get all current validation errors"""
        errors = {}
        try:
            for field_name, state in self._validation_states.items():
                if not state.is_valid and state.error_message:
                    errors[field_name] = state.error_message
        except Exception:
            pass
        return errors
    
    def prevent_form_submission_on_validation_errors(self) -> bool:
        """Check if form submission should be prevented due to validation errors"""
        return not self.is_form_valid()
    
    def validate_apn_field(self, value: str) -> ValidationResult:
        """Validate APN field using the APN validation component"""
        try:
            if not value or not value.strip():
                return ValidationResult(
                    is_valid=False,
                    error_message="APN cannot be empty",
                    error_code="EMPTY_APN",
                    suggestions=["Enter a valid APN like 'internet.provider.com'"],
                    field_name="apn",
                    validated_value=value
                )
            
            return self._apn_validator.validate_apn_configuration(value.strip())
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Validation error: {str(e)}",
                error_code="VALIDATION_ERROR",
                suggestions=[],
                field_name="apn",
                validated_value=value
            )