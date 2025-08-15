"""
Parameter Error Feedback Service

This service provides user feedback for parameter processing errors,
including summary feedback when multiple parameters fail to process.
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from services.parameter_processor import ProcessingSummary, ErrorSeverity

logger = logging.getLogger(__name__)


class FeedbackLevel(Enum):
    """Levels of user feedback."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class UserFeedback:
    """User feedback message."""
    level: FeedbackLevel
    title: str
    message: str
    details: Optional[List[str]] = None
    parameter_count: Optional[int] = None


class ParameterErrorFeedbackService:
    """
    Provides user feedback for parameter processing errors and warnings.
    
    This service analyzes parameter processing results and generates appropriate
    user feedback messages, including summary feedback for multiple failures.
    """
    
    def __init__(self):
        """Initialize the feedback service."""
        self.feedback_history = []
    
    def generate_processing_feedback(self, summary: ProcessingSummary) -> List[UserFeedback]:
        """
        Generate user feedback based on parameter processing summary.
        
        Args:
            summary: ProcessingSummary from parameter processing operation
            
        Returns:
            List of UserFeedback messages for the user
            
        Requirements: 5.4 - Provide summary feedback for multiple failures
        """
        feedback_messages = []
        
        # Generate overall summary feedback
        if summary.failed_parameters == 0:
            # All parameters processed successfully
            if summary.total_parameters > 0:
                feedback_messages.append(UserFeedback(
                    level=FeedbackLevel.INFO,
                    title="Parameter Processing Complete",
                    message=f"Successfully processed all {summary.total_parameters} parameters from device.",
                    parameter_count=summary.total_parameters
                ))
        else:
            # Some or all parameters failed
            success_rate = (summary.successful_parameters / summary.total_parameters) * 100
            
            if summary.successful_parameters == 0:
                # Complete failure
                feedback_messages.append(UserFeedback(
                    level=FeedbackLevel.ERROR,
                    title="Parameter Processing Failed",
                    message=f"Failed to process any of the {summary.total_parameters} parameters from device.",
                    details=summary.errors[:5] if summary.errors else None,  # Limit to first 5 errors
                    parameter_count=summary.total_parameters
                ))
            else:
                # Partial failure
                feedback_level = FeedbackLevel.WARNING if success_rate >= 50 else FeedbackLevel.ERROR
                
                feedback_messages.append(UserFeedback(
                    level=feedback_level,
                    title="Parameter Processing Partially Complete",
                    message=f"Processed {summary.successful_parameters} of {summary.total_parameters} parameters successfully ({success_rate:.1f}% success rate).",
                    details=self._format_failure_details(summary),
                    parameter_count=summary.total_parameters
                ))
        
        # Generate specific warnings if present
        if summary.warnings:
            warning_count = len(summary.warnings)
            if warning_count <= 3:
                # Show individual warnings for small numbers
                for warning in summary.warnings:
                    feedback_messages.append(UserFeedback(
                        level=FeedbackLevel.WARNING,
                        title="Parameter Processing Warning",
                        message=warning
                    ))
            else:
                # Summarize warnings for large numbers
                feedback_messages.append(UserFeedback(
                    level=FeedbackLevel.WARNING,
                    title="Parameter Processing Warnings",
                    message=f"Encountered {warning_count} warnings during parameter processing.",
                    details=summary.warnings[:5]  # Show first 5 warnings
                ))
        
        # Store feedback in history
        self.feedback_history.extend(feedback_messages)
        
        return feedback_messages
    
    def _format_failure_details(self, summary: ProcessingSummary) -> List[str]:
        """
        Format failure details for user feedback.
        
        Args:
            summary: ProcessingSummary with error information
            
        Returns:
            List of formatted error details
        """
        details = []
        
        # Add error summary
        if summary.errors:
            error_count = len(summary.errors)
            if error_count <= 5:
                details.extend(summary.errors)
            else:
                details.extend(summary.errors[:3])
                details.append(f"... and {error_count - 3} more errors")
        
        # Add warning summary if there are many warnings
        if summary.warnings and len(summary.warnings) > 3:
            details.append(f"Additionally, {len(summary.warnings)} warnings were encountered")
        
        return details
    
    def generate_ui_update_error_feedback(self, parameter_name: str, error_message: str) -> UserFeedback:
        """
        Generate feedback for UI update errors.
        
        Args:
            parameter_name: Name of parameter that failed to update in UI
            error_message: Error message from UI update failure
            
        Returns:
            UserFeedback for the UI update error
            
        Requirements: 5.3 - Log UI update errors and provide feedback
        """
        feedback = UserFeedback(
            level=FeedbackLevel.WARNING,
            title="UI Update Error",
            message=f"Parameter '{parameter_name}' was processed successfully but failed to update in the interface.",
            details=[f"Error: {error_message}", "The parameter value was saved but may not be visible until the interface is refreshed."]
        )
        
        self.feedback_history.append(feedback)
        logger.warning(f"UI update failed for parameter {parameter_name}: {error_message}")
        
        return feedback
    
    def generate_malformed_data_feedback(self, parameter_name: str, raw_data: str, error_details: str) -> UserFeedback:
        """
        Generate feedback for malformed parameter data.
        
        Args:
            parameter_name: Name of parameter with malformed data
            raw_data: The malformed raw data
            error_details: Details about what was malformed
            
        Returns:
            UserFeedback for the malformed data
            
        Requirements: 5.1 - Log appropriate error messages for malformed data
        """
        feedback = UserFeedback(
            level=FeedbackLevel.WARNING,
            title="Malformed Parameter Data",
            message=f"Parameter '{parameter_name}' contains malformed data and may not display correctly.",
            details=[f"Raw data: {raw_data[:100]}{'...' if len(raw_data) > 100 else ''}", f"Issue: {error_details}"]
        )
        
        self.feedback_history.append(feedback)
        logger.warning(f"Malformed data for parameter {parameter_name}: {error_details}")
        
        return feedback
    
    def get_feedback_summary(self) -> Dict[str, any]:
        """
        Get a summary of all feedback generated.
        
        Returns:
            Dictionary with feedback statistics and recent messages
        """
        if not self.feedback_history:
            return {
                'total_feedback': 0,
                'error_count': 0,
                'warning_count': 0,
                'info_count': 0,
                'recent_messages': []
            }
        
        error_count = sum(1 for f in self.feedback_history if f.level == FeedbackLevel.ERROR)
        warning_count = sum(1 for f in self.feedback_history if f.level == FeedbackLevel.WARNING)
        info_count = sum(1 for f in self.feedback_history if f.level == FeedbackLevel.INFO)
        
        return {
            'total_feedback': len(self.feedback_history),
            'error_count': error_count,
            'warning_count': warning_count,
            'info_count': info_count,
            'recent_messages': [
                {
                    'level': f.level.value,
                    'title': f.title,
                    'message': f.message,
                    'parameter_count': f.parameter_count
                }
                for f in self.feedback_history[-5:]  # Last 5 messages
            ]
        }
    
    def clear_feedback_history(self):
        """Clear the feedback history."""
        self.feedback_history.clear()
        logger.debug("Cleared parameter error feedback history")
    
    def format_feedback_for_display(self, feedback: UserFeedback) -> str:
        """
        Format feedback message for display to user.
        
        Args:
            feedback: UserFeedback to format
            
        Returns:
            Formatted string for display
        """
        formatted = f"[{feedback.level.value.upper()}] {feedback.title}: {feedback.message}"
        
        if feedback.details:
            formatted += "\nDetails:\n"
            for detail in feedback.details:
                formatted += f"  • {detail}\n"
        
        return formatted.strip()