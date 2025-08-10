"""
Parameter Operation Feedback Service for LT32 PRO Configurator

This module provides comprehensive user feedback for parameter operations including
success/failure feedback, summary feedback, detailed error reporting, and visual
indicators as specified in task 8.2.

Requirements addressed:
- 9.3: Summary feedback showing total parameters processed and results
- 9.5: Detailed error reporting for failed operations with specific causes
- 8.3: Visual indicators in UI to show which parameters were successfully updated
- 8.6: User-friendly error messages with suggested corrective actions
"""

import tkinter as tk
import customtkinter as ctk
from typing import Dict, Any, List, Optional, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import threading
import time
from collections import defaultdict


class FeedbackType(Enum):
    """Types of feedback that can be displayed."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    PROGRESS = "progress"


class FeedbackPriority(Enum):
    """Priority levels for feedback messages."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ParameterFeedback:
    """Individual parameter operation feedback."""
    parameter_name: str
    operation_type: str  # 'read', 'write', 'bulk_read', 'bulk_write'
    success: bool
    message: str
    details: Optional[str] = None
    timestamp: datetime = None
    duration_ms: float = 0.0
    retry_count: int = 0
    suggested_actions: List[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.suggested_actions is None:
            self.suggested_actions = []


@dataclass
class OperationSummary:
    """Summary of a parameter operation session."""
    operation_type: str
    total_parameters: int
    successful_parameters: int
    failed_parameters: int
    duration_seconds: float
    start_time: datetime
    end_time: datetime
    error_categories: Dict[str, int]
    success_rate: float
    parameters_processed: List[str]
    failed_parameter_details: List[ParameterFeedback]


class ParameterOperationFeedback:
    """
    Service for providing comprehensive user feedback on parameter operations.
    
    This service handles:
    - Individual parameter operation feedback
    - Bulk operation progress and summary feedback
    - Visual indicators for parameter status
    - Error reporting with suggested actions
    - Toast notifications and status updates
    """

    def __init__(self, app_instance=None, i18n_service=None):
        """
        Initialize the parameter operation feedback service.
        
        Args:
            app_instance: Main application instance for UI integration
            i18n_service: Internationalization service for localized messages
        """
        self.app = app_instance
        self.i18n = i18n_service
        
        # Feedback storage
        self.recent_feedback = []
        self.max_recent_feedback = 100
        
        # Visual indicators tracking
        self.parameter_status_indicators = {}
        self.status_update_callbacks = []
        
        # Toast notification system
        self.active_toasts = []
        self.toast_queue = []
        self.max_concurrent_toasts = 3
        
        # Summary tracking
        self.current_operation_summary = None
        self.operation_start_time = None
        
        # UI elements
        self.status_bar = None
        self.feedback_panel = None
        
        # Initialize feedback messages
        self._init_feedback_messages()

    def _init_feedback_messages(self):
        """Initialize localized feedback messages."""
        self.feedback_messages = {
            # Success messages
            'parameter_read_success': "Successfully read {parameter}: {value}",
            'parameter_write_success': "Successfully updated {parameter}",
            'bulk_read_success': "Successfully read {count} parameters",
            'bulk_write_success': "Successfully updated {count} parameters",
            'operation_complete': "Operation completed successfully",
            
            # Error messages
            'parameter_read_error': "Failed to read {parameter}: {error}",
            'parameter_write_error': "Failed to update {parameter}: {error}",
            'connection_error': "Device connection error: {error}",
            'timeout_error': "Operation timed out: {error}",
            'validation_error': "Invalid parameter value: {error}",
            'permission_error': "Permission denied: {error}",
            
            # Progress messages
            'operation_starting': "Starting {operation} operation...",
            'operation_progress': "Processing {current}/{total} parameters...",
            'operation_canceling': "Canceling operation...",
            
            # Summary messages
            'operation_summary': "{successful}/{total} parameters processed successfully",
            'partial_success': "Operation partially successful: {successful} succeeded, {failed} failed",
            'operation_failed': "Operation failed: {failed} parameters could not be processed",
            
            # Suggested actions
            'check_connection': "Check device connection and try again",
            'verify_parameters': "Verify parameter values are within valid ranges",
            'restart_application': "Restart the application and try again",
            'contact_support': "Contact technical support if the problem persists",
            'retry_operation': "Retry the operation after a short delay",
            'check_device_power': "Ensure the device is powered on and responsive"
        }

    def show_parameter_feedback(self, feedback: ParameterFeedback, show_toast: bool = True, update_indicator: bool = True):
        """
        Show feedback for an individual parameter operation.
        
        Args:
            feedback: ParameterFeedback object with operation details
            show_toast: Whether to show a toast notification
            update_indicator: Whether to update visual indicators
        """
        # Store feedback
        self.recent_feedback.append(feedback)
        if len(self.recent_feedback) > self.max_recent_feedback:
            self.recent_feedback.pop(0)
        
        # Update visual indicators
        if update_indicator:
            self._update_parameter_indicator(feedback)
        
        # Show toast notification
        if show_toast:
            self._show_toast_notification(feedback)
        
        # Update status bar
        self._update_status_bar(feedback)
        
        # Log to UI if available
        self._log_feedback_to_ui(feedback)

    def show_operation_summary(self, summary: OperationSummary, show_dialog: bool = True):
        """
        Show summary feedback for a completed operation.
        
        Args:
            summary: OperationSummary object with operation results
            show_dialog: Whether to show a summary dialog
        """
        self.current_operation_summary = summary
        
        # Create summary message
        summary_message = self._create_summary_message(summary)
        
        # Show summary dialog if requested
        if show_dialog and self.app:
            self._show_summary_dialog(summary, summary_message)
        
        # Show summary toast
        self._show_summary_toast(summary, summary_message)
        
        # Update status bar with summary
        self._update_status_bar_summary(summary)
        
        # Log summary to UI
        self._log_summary_to_ui(summary, summary_message)

    def start_operation_tracking(self, operation_type: str, parameter_count: int):
        """
        Start tracking a parameter operation for progress feedback.
        
        Args:
            operation_type: Type of operation ('bulk_read', 'bulk_write', etc.)
            parameter_count: Total number of parameters to process
        """
        self.operation_start_time = datetime.now()
        self.current_operation_summary = OperationSummary(
            operation_type=operation_type,
            total_parameters=parameter_count,
            successful_parameters=0,
            failed_parameters=0,
            duration_seconds=0.0,
            start_time=self.operation_start_time,
            end_time=self.operation_start_time,
            error_categories={},
            success_rate=0.0,
            parameters_processed=[],
            failed_parameter_details=[]
        )
        
        # Show operation start feedback
        start_message = self.feedback_messages['operation_starting'].format(operation=operation_type)
        self._update_status_bar_text(start_message)
        
        if self.app and hasattr(self.app, 'log_frame'):
            self.app.log_frame.log_message(f"INFO: {start_message}")

    def update_operation_progress(self, parameter_name: str, success: bool, error_message: Optional[str] = None):
        """
        Update progress for an ongoing operation.
        
        Args:
            parameter_name: Name of the parameter just processed
            success: Whether the parameter operation was successful
            error_message: Error message if operation failed
        """
        if not self.current_operation_summary:
            return
        
        # Update summary
        self.current_operation_summary.parameters_processed.append(parameter_name)
        
        if success:
            self.current_operation_summary.successful_parameters += 1
        else:
            self.current_operation_summary.failed_parameters += 1
            
            # Create feedback for failed parameter
            failed_feedback = ParameterFeedback(
                parameter_name=parameter_name,
                operation_type=self.current_operation_summary.operation_type,
                success=False,
                message=error_message or "Operation failed",
                suggested_actions=self._get_suggested_actions(error_message)
            )
            self.current_operation_summary.failed_parameter_details.append(failed_feedback)
            
            # Categorize error
            error_category = self._categorize_error(error_message or "unknown")
            self.current_operation_summary.error_categories[error_category] = \
                self.current_operation_summary.error_categories.get(error_category, 0) + 1
        
        # Update progress message
        processed = len(self.current_operation_summary.parameters_processed)
        total = self.current_operation_summary.total_parameters
        progress_message = self.feedback_messages['operation_progress'].format(
            current=processed, total=total
        )
        
        self._update_status_bar_text(progress_message)
        
        # Update success rate
        if processed > 0:
            self.current_operation_summary.success_rate = \
                (self.current_operation_summary.successful_parameters / processed) * 100

    def complete_operation_tracking(self) -> OperationSummary:
        """
        Complete operation tracking and return summary.
        
        Returns:
            OperationSummary object with final results
        """
        if not self.current_operation_summary:
            return None
        
        # Finalize summary
        self.current_operation_summary.end_time = datetime.now()
        self.current_operation_summary.duration_seconds = \
            (self.current_operation_summary.end_time - self.current_operation_summary.start_time).total_seconds()
        
        # Show summary
        self.show_operation_summary(self.current_operation_summary)
        
        summary = self.current_operation_summary
        self.current_operation_summary = None
        
        return summary

    def show_error_details(self, parameter_name: str, error_message: str, suggested_actions: List[str] = None):
        """
        Show detailed error information with suggested actions.
        
        Args:
            parameter_name: Name of the parameter that failed
            error_message: Detailed error message
            suggested_actions: List of suggested corrective actions
        """
        if not suggested_actions:
            suggested_actions = self._get_suggested_actions(error_message)
        
        # Create detailed error feedback
        error_feedback = ParameterFeedback(
            parameter_name=parameter_name,
            operation_type="error_details",
            success=False,
            message=error_message,
            suggested_actions=suggested_actions
        )
        
        # Show error dialog if app is available
        if self.app:
            self._show_error_dialog(error_feedback)
        
        # Show error toast
        self._show_toast_notification(error_feedback, priority=FeedbackPriority.HIGH)

    def add_parameter_status_indicator(self, parameter_name: str, widget, 
                                     success_color: str = "#4CAF50", error_color: str = "#F44336"):
        """
        Add a visual status indicator for a parameter.
        
        Args:
            parameter_name: Name of the parameter
            widget: UI widget to use as status indicator
            success_color: Color for successful operations
            error_color: Color for failed operations
        """
        self.parameter_status_indicators[parameter_name] = {
            'widget': widget,
            'success_color': success_color,
            'error_color': error_color,
            'default_color': widget.cget('fg_color') if hasattr(widget, 'cget') else None
        }

    def clear_parameter_indicators(self):
        """Clear all parameter status indicators."""
        for param_name, indicator in self.parameter_status_indicators.items():
            widget = indicator['widget']
            default_color = indicator['default_color']
            
            if default_color and hasattr(widget, 'configure'):
                try:
                    widget.configure(fg_color=default_color)
                except:
                    pass  # Ignore configuration errors

    def _update_parameter_indicator(self, feedback: ParameterFeedback):
        """Update visual indicator for a parameter."""
        if feedback.parameter_name not in self.parameter_status_indicators:
            return
        
        indicator = self.parameter_status_indicators[feedback.parameter_name]
        widget = indicator['widget']
        
        if not widget or not hasattr(widget, 'configure'):
            return
        
        try:
            if feedback.success:
                color = indicator['success_color']
            else:
                color = indicator['error_color']
            
            widget.configure(fg_color=color)
            
            # Reset color after a delay
            def reset_color():
                time.sleep(3.0)
                if hasattr(widget, 'configure') and indicator['default_color']:
                    try:
                        widget.configure(fg_color=indicator['default_color'])
                    except:
                        pass
            
            threading.Thread(target=reset_color, daemon=True).start()
            
        except Exception as e:
            # Silently handle widget configuration errors
            pass

    def _show_toast_notification(self, feedback: ParameterFeedback, priority: FeedbackPriority = FeedbackPriority.MEDIUM):
        """Show a toast notification for parameter feedback."""
        if not self.app or len(self.active_toasts) >= self.max_concurrent_toasts:
            # Queue the toast if we have too many active
            self.toast_queue.append((feedback, priority))
            return
        
        # Create toast message
        if feedback.success:
            if feedback.operation_type in ['read', 'bulk_read']:
                message = f"✓ Read {feedback.parameter_name}"
            else:
                message = f"✓ Updated {feedback.parameter_name}"
            toast_type = FeedbackType.SUCCESS
        else:
            message = f"✗ Failed: {feedback.parameter_name}"
            if feedback.details:
                message += f" - {feedback.details}"
            toast_type = FeedbackType.ERROR
        
        # Show toast using app's notification system if available
        if hasattr(self.app, 'show_toast'):
            toast_id = self.app.show_toast(message, toast_type.value, duration=3000)
            self.active_toasts.append(toast_id)
            
            # Remove from active toasts after duration
            def remove_toast():
                time.sleep(3.5)
                if toast_id in self.active_toasts:
                    self.active_toasts.remove(toast_id)
                self._process_toast_queue()
            
            threading.Thread(target=remove_toast, daemon=True).start()
        else:
            # Fallback to status bar update
            self._update_status_bar_text(message)

    def _show_summary_toast(self, summary: OperationSummary, message: str):
        """Show a toast notification for operation summary."""
        if summary.failed_parameters == 0:
            toast_type = FeedbackType.SUCCESS
        elif summary.successful_parameters > 0:
            toast_type = FeedbackType.WARNING
        else:
            toast_type = FeedbackType.ERROR
        
        # Create summary toast
        summary_feedback = ParameterFeedback(
            parameter_name="Operation Summary",
            operation_type=summary.operation_type,
            success=summary.failed_parameters == 0,
            message=message
        )
        
        self._show_toast_notification(summary_feedback, priority=FeedbackPriority.HIGH)

    def _process_toast_queue(self):
        """Process queued toast notifications."""
        if self.toast_queue and len(self.active_toasts) < self.max_concurrent_toasts:
            feedback, priority = self.toast_queue.pop(0)
            self._show_toast_notification(feedback, priority)

    def _update_status_bar(self, feedback: ParameterFeedback):
        """Update status bar with parameter feedback."""
        if feedback.success:
            if feedback.operation_type in ['read', 'bulk_read']:
                message = f"Read {feedback.parameter_name} successfully"
            else:
                message = f"Updated {feedback.parameter_name} successfully"
        else:
            message = f"Failed to process {feedback.parameter_name}: {feedback.message}"
        
        self._update_status_bar_text(message)

    def _update_status_bar_summary(self, summary: OperationSummary):
        """Update status bar with operation summary."""
        message = self._create_summary_message(summary)
        self._update_status_bar_text(message)

    def _update_status_bar_text(self, message: str):
        """Update status bar text."""
        if self.app and hasattr(self.app, 'status_bar'):
            try:
                self.app.status_bar.configure(text=message)
            except:
                pass
        elif self.status_bar:
            try:
                self.status_bar.configure(text=message)
            except:
                pass

    def _log_feedback_to_ui(self, feedback: ParameterFeedback):
        """Log parameter feedback to UI log frame."""
        if not self.app or not hasattr(self.app, 'log_frame'):
            return
        
        try:
            timestamp = feedback.timestamp.strftime("%H:%M:%S")
            
            if feedback.success:
                if feedback.operation_type in ['read', 'bulk_read']:
                    message = f"INFO: [{timestamp}] Successfully read {feedback.parameter_name}"
                else:
                    message = f"INFO: [{timestamp}] Successfully updated {feedback.parameter_name}"
            else:
                message = f"ERROR: [{timestamp}] Failed to process {feedback.parameter_name}: {feedback.message}"
                
                # Add suggested actions
                if feedback.suggested_actions:
                    for action in feedback.suggested_actions:
                        self.app.log_frame.log_message(f"INFO: Suggested action: {action}")
            
            self.app.log_frame.log_message(message)
            
        except Exception as e:
            # Don't let logging errors break the feedback system
            pass

    def _log_summary_to_ui(self, summary: OperationSummary, message: str):
        """Log operation summary to UI log frame."""
        if not self.app or not hasattr(self.app, 'log_frame'):
            return
        
        try:
            timestamp = summary.end_time.strftime("%H:%M:%S")
            log_message = f"INFO: [{timestamp}] Operation Summary: {message}"
            self.app.log_frame.log_message(log_message)
            
            # Log error details if any
            if summary.failed_parameter_details:
                self.app.log_frame.log_message(f"INFO: Failed parameters:")
                for failed in summary.failed_parameter_details:
                    self.app.log_frame.log_message(f"  - {failed.parameter_name}: {failed.message}")
            
        except Exception as e:
            # Don't let logging errors break the feedback system
            pass

    def _create_summary_message(self, summary: OperationSummary) -> str:
        """Create a human-readable summary message."""
        if summary.failed_parameters == 0:
            return self.feedback_messages['operation_complete']
        elif summary.successful_parameters > 0:
            return self.feedback_messages['partial_success'].format(
                successful=summary.successful_parameters,
                failed=summary.failed_parameters
            )
        else:
            return self.feedback_messages['operation_failed'].format(
                failed=summary.failed_parameters
            )

    def _show_summary_dialog(self, summary: OperationSummary, message: str):
        """Show a dialog with operation summary."""
        if not self.app:
            return
        
        try:
            # Create summary dialog
            dialog = ctk.CTkToplevel(self.app)
            dialog.title("Operation Summary")
            dialog.geometry("500x400")
            dialog.transient(self.app)
            dialog.grab_set()
            
            # Center the dialog
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
            y = (dialog.winfo_screenheight() // 2) - (400 // 2)
            dialog.geometry(f"500x400+{x}+{y}")
            
            # Main frame
            main_frame = ctk.CTkFrame(dialog)
            main_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Title
            title_label = ctk.CTkLabel(
                main_frame, 
                text="Parameter Operation Summary",
                font=ctk.CTkFont(size=18, weight="bold")
            )
            title_label.pack(pady=(0, 20))
            
            # Summary stats
            stats_frame = ctk.CTkFrame(main_frame)
            stats_frame.pack(fill="x", pady=(0, 20))
            
            stats_text = (
                f"Operation: {summary.operation_type}\n"
                f"Total Parameters: {summary.total_parameters}\n"
                f"Successful: {summary.successful_parameters}\n"
                f"Failed: {summary.failed_parameters}\n"
                f"Success Rate: {summary.success_rate:.1f}%\n"
                f"Duration: {summary.duration_seconds:.1f} seconds"
            )
            
            stats_label = ctk.CTkLabel(stats_frame, text=stats_text, justify="left")
            stats_label.pack(padx=20, pady=20)
            
            # Error details if any
            if summary.failed_parameter_details:
                error_frame = ctk.CTkFrame(main_frame)
                error_frame.pack(fill="both", expand=True, pady=(0, 20))
                
                error_title = ctk.CTkLabel(
                    error_frame, 
                    text="Failed Parameters:",
                    font=ctk.CTkFont(weight="bold")
                )
                error_title.pack(pady=(10, 5))
                
                # Scrollable text for errors
                error_text = ctk.CTkTextbox(error_frame, height=150)
                error_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
                
                for failed in summary.failed_parameter_details:
                    error_text.insert("end", f"• {failed.parameter_name}: {failed.message}\n")
                    if failed.suggested_actions:
                        for action in failed.suggested_actions:
                            error_text.insert("end", f"  → {action}\n")
                        error_text.insert("end", "\n")
                
                error_text.configure(state="disabled")
            
            # Close button
            close_button = ctk.CTkButton(
                main_frame,
                text="Close",
                command=dialog.destroy
            )
            close_button.pack(pady=(0, 10))
            
        except Exception as e:
            # Fallback to simple message if dialog creation fails
            print(f"Failed to create summary dialog: {str(e)}")

    def _show_error_dialog(self, feedback: ParameterFeedback):
        """Show a detailed error dialog."""
        if not self.app:
            return
        
        try:
            # Create error dialog
            dialog = ctk.CTkToplevel(self.app)
            dialog.title("Parameter Operation Error")
            dialog.geometry("450x350")
            dialog.transient(self.app)
            dialog.grab_set()
            
            # Center the dialog
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (450 // 2)
            y = (dialog.winfo_screenheight() // 2) - (350 // 2)
            dialog.geometry(f"450x350+{x}+{y}")
            
            # Main frame
            main_frame = ctk.CTkFrame(dialog)
            main_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Error icon and title
            title_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            title_frame.pack(fill="x", pady=(0, 20))
            
            title_label = ctk.CTkLabel(
                title_frame,
                text=f"❌ Error: {feedback.parameter_name}",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color="#F44336"
            )
            title_label.pack()
            
            # Error message
            message_frame = ctk.CTkFrame(main_frame)
            message_frame.pack(fill="x", pady=(0, 20))
            
            message_label = ctk.CTkLabel(
                message_frame,
                text=feedback.message,
                wraplength=400,
                justify="left"
            )
            message_label.pack(padx=20, pady=20)
            
            # Suggested actions
            if feedback.suggested_actions:
                actions_frame = ctk.CTkFrame(main_frame)
                actions_frame.pack(fill="both", expand=True, pady=(0, 20))
                
                actions_title = ctk.CTkLabel(
                    actions_frame,
                    text="Suggested Actions:",
                    font=ctk.CTkFont(weight="bold")
                )
                actions_title.pack(pady=(10, 5))
                
                actions_text = ctk.CTkTextbox(actions_frame, height=120)
                actions_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
                
                for i, action in enumerate(feedback.suggested_actions, 1):
                    actions_text.insert("end", f"{i}. {action}\n")
                
                actions_text.configure(state="disabled")
            
            # Buttons
            button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            button_frame.pack(fill="x")
            
            retry_button = ctk.CTkButton(
                button_frame,
                text="Retry",
                command=lambda: self._retry_parameter_operation(feedback, dialog)
            )
            retry_button.pack(side="left", padx=(0, 10))
            
            close_button = ctk.CTkButton(
                button_frame,
                text="Close",
                command=dialog.destroy
            )
            close_button.pack(side="right")
            
        except Exception as e:
            # Fallback to simple error message
            print(f"Failed to create error dialog: {str(e)}")

    def _retry_parameter_operation(self, feedback: ParameterFeedback, dialog):
        """Handle retry button click in error dialog."""
        dialog.destroy()
        
        # Emit retry signal if app supports it
        if self.app and hasattr(self.app, 'retry_parameter_operation'):
            self.app.retry_parameter_operation(feedback.parameter_name, feedback.operation_type)

    def _get_suggested_actions(self, error_message: str) -> List[str]:
        """Get suggested actions based on error message."""
        if not error_message:
            return [self.feedback_messages['contact_support']]
        
        error_lower = error_message.lower()
        actions = []
        
        if 'timeout' in error_lower or 'no response' in error_lower:
            actions.extend([
                self.feedback_messages['check_connection'],
                self.feedback_messages['check_device_power'],
                self.feedback_messages['retry_operation']
            ])
        elif 'connection' in error_lower or 'disconnected' in error_lower:
            actions.extend([
                self.feedback_messages['check_connection'],
                self.feedback_messages['check_device_power'],
                self.feedback_messages['restart_application']
            ])
        elif 'invalid' in error_lower or 'format' in error_lower or 'validation' in error_lower:
            actions.extend([
                self.feedback_messages['verify_parameters'],
                self.feedback_messages['contact_support']
            ])
        elif 'permission' in error_lower or 'access' in error_lower:
            actions.extend([
                self.feedback_messages['restart_application'],
                self.feedback_messages['contact_support']
            ])
        else:
            actions.extend([
                self.feedback_messages['retry_operation'],
                self.feedback_messages['check_connection'],
                self.feedback_messages['contact_support']
            ])
        
        return actions

    def _categorize_error(self, error_message: str) -> str:
        """Categorize error message for statistics."""
        error_lower = error_message.lower()
        
        if 'timeout' in error_lower or 'no response' in error_lower:
            return 'timeout'
        elif 'connection' in error_lower or 'disconnected' in error_lower:
            return 'connection'
        elif 'invalid' in error_lower or 'format' in error_lower:
            return 'format'
        elif 'permission' in error_lower or 'access' in error_lower:
            return 'permission'
        elif 'validation' in error_lower or 'range' in error_lower:
            return 'validation'
        else:
            return 'other'

    def get_recent_feedback(self, count: int = 10) -> List[ParameterFeedback]:
        """
        Get recent parameter feedback.
        
        Args:
            count: Number of recent feedback items to return
            
        Returns:
            List of recent ParameterFeedback objects
        """
        return self.recent_feedback[-count:]

    def get_failed_operations(self, time_range: timedelta = None) -> List[ParameterFeedback]:
        """
        Get failed parameter operations within a time range.
        
        Args:
            time_range: Time range to filter operations (default: last hour)
            
        Returns:
            List of failed ParameterFeedback objects
        """
        if time_range is None:
            time_range = timedelta(hours=1)
        
        cutoff_time = datetime.now() - time_range
        
        return [
            feedback for feedback in self.recent_feedback
            if not feedback.success and feedback.timestamp >= cutoff_time
        ]

    def clear_feedback_history(self):
        """Clear all stored feedback history."""
        self.recent_feedback.clear()
        self.parameter_status_indicators.clear()
        self.active_toasts.clear()
        self.toast_queue.clear()

    def set_status_bar(self, status_bar_widget):
        """
        Set the status bar widget for feedback display.
        
        Args:
            status_bar_widget: Status bar widget to use for feedback
        """
        self.status_bar = status_bar_widget

    def add_status_update_callback(self, callback: Callable[[str, bool], None]):
        """
        Add a callback for status updates.
        
        Args:
            callback: Function to call with (parameter_name, success) when status changes
        """
        self.status_update_callbacks.append(callback)

    def _notify_status_callbacks(self, parameter_name: str, success: bool):
        """Notify all status update callbacks."""
        for callback in self.status_update_callbacks:
            try:
                callback(parameter_name, success)
            except Exception as e:
                # Don't let callback errors break the feedback system
                pass