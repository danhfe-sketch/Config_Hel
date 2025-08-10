"""
Widget Error Handling Service

Centralized service for handling widget access errors, logging failures,
and managing fallback strategies across the application.
"""

import logging
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class WidgetErrorReport:
    """Comprehensive widget error report"""
    timestamp: datetime
    context: str
    widget_type: str
    error_message: str
    exception_type: str
    severity: ErrorSeverity
    fallback_used: bool
    fallback_description: str
    widget_id: Optional[int] = None
    stack_trace: Optional[str] = None
    recovery_suggestions: List[str] = field(default_factory=list)
    user_impact: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error report to dictionary for logging"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'context': self.context,
            'widget_type': self.widget_type,
            'error_message': self.error_message,
            'exception_type': self.exception_type,
            'severity': self.severity.value,
            'fallback_used': self.fallback_used,
            'fallback_description': self.fallback_description,
            'widget_id': self.widget_id,
            'stack_trace': self.stack_trace,
            'recovery_suggestions': self.recovery_suggestions,
            'user_impact': self.user_impact
        }


class WidgetErrorHandlingService:
    """
    Centralized service for handling widget access errors and managing
    application stability when UI enhancements fail.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_reports: List[WidgetErrorReport] = []
        self.error_counts: Dict[str, int] = {}
        self.fallback_strategies: Dict[str, Callable] = {}
        self.max_error_reports = 1000  # Limit memory usage
        
        # Configure logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Set up comprehensive logging for widget errors"""
        # Create formatter for detailed error logs
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Create file handler for widget errors
        try:
            file_handler = logging.FileHandler('logs/widget_errors.log')
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.WARNING)
            self.logger.addHandler(file_handler)
        except Exception:
            # If we can't create log file, continue without file logging
            pass
        
        # Ensure console logging is available
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        self.logger.setLevel(logging.DEBUG)
    
    def report_widget_error(self, widget: Any, context: str, exception: Exception = None,
                           severity: ErrorSeverity = ErrorSeverity.ERROR,
                           fallback_used: bool = False, fallback_description: str = "",
                           user_impact: str = "", recovery_suggestions: List[str] = None) -> WidgetErrorReport:
        """
        Report a widget access error with comprehensive details.
        
        Args:
            widget: The widget that caused the error
            context: Context where the error occurred
            exception: The exception that occurred
            severity: Severity level of the error
            fallback_used: Whether a fallback strategy was used
            fallback_description: Description of fallback strategy
            user_impact: Description of impact on user experience
            recovery_suggestions: List of suggestions for recovery
            
        Returns:
            WidgetErrorReport with complete error details
        """
        if recovery_suggestions is None:
            recovery_suggestions = []
        
        # Create error report
        error_report = WidgetErrorReport(
            timestamp=datetime.now(),
            context=context,
            widget_type=type(widget).__name__ if widget else "Unknown",
            error_message=str(exception) if exception else "Unknown error",
            exception_type=type(exception).__name__ if exception else "Unknown",
            severity=severity,
            fallback_used=fallback_used,
            fallback_description=fallback_description,
            widget_id=id(widget) if widget else None,
            stack_trace=self._get_stack_trace(exception),
            recovery_suggestions=recovery_suggestions,
            user_impact=user_impact
        )
        
        # Store error report
        self._store_error_report(error_report)
        
        # Log error based on severity
        self._log_error_report(error_report)
        
        # Update error counts
        self._update_error_counts(context)
        
        # Check if we need to take action based on error frequency
        self._check_error_frequency(context)
        
        return error_report
    
    def _get_stack_trace(self, exception: Exception) -> Optional[str]:
        """Get formatted stack trace from exception"""
        if exception and hasattr(exception, '__traceback__'):
            try:
                return ''.join(traceback.format_tb(exception.__traceback__))
            except Exception:
                return None
        return None
    
    def _store_error_report(self, error_report: WidgetErrorReport):
        """Store error report with memory management"""
        self.error_reports.append(error_report)
        
        # Limit memory usage by removing old reports
        if len(self.error_reports) > self.max_error_reports:
            # Remove oldest 10% of reports
            remove_count = self.max_error_reports // 10
            self.error_reports = self.error_reports[remove_count:]
    
    def _log_error_report(self, error_report: WidgetErrorReport):
        """Log error report based on severity level"""
        log_message = self._format_error_log_message(error_report)
        
        if error_report.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif error_report.severity == ErrorSeverity.ERROR:
            self.logger.error(log_message)
        elif error_report.severity == ErrorSeverity.WARNING:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
        
        # Also print to console for immediate visibility
        severity_prefix = {
            ErrorSeverity.CRITICAL: "CRITICAL",
            ErrorSeverity.ERROR: "ERROR",
            ErrorSeverity.WARNING: "WARNING",
            ErrorSeverity.INFO: "INFO"
        }
        
        print(f"[{severity_prefix[error_report.severity]}] Widget Error in {error_report.context}: {error_report.error_message}")
        
        if error_report.fallback_used:
            print(f"  Fallback: {error_report.fallback_description}")
        
        if error_report.user_impact:
            print(f"  User Impact: {error_report.user_impact}")
    
    def _format_error_log_message(self, error_report: WidgetErrorReport) -> str:
        """Format error report for logging"""
        lines = [
            f"Widget Error Report - {error_report.context}",
            f"  Widget Type: {error_report.widget_type}",
            f"  Error: {error_report.error_message}",
            f"  Exception Type: {error_report.exception_type}",
            f"  Severity: {error_report.severity.value}",
            f"  Fallback Used: {error_report.fallback_used}",
        ]
        
        if error_report.fallback_description:
            lines.append(f"  Fallback: {error_report.fallback_description}")
        
        if error_report.user_impact:
            lines.append(f"  User Impact: {error_report.user_impact}")
        
        if error_report.recovery_suggestions:
            lines.append(f"  Recovery Suggestions: {', '.join(error_report.recovery_suggestions)}")
        
        if error_report.stack_trace:
            lines.append(f"  Stack Trace:\n{error_report.stack_trace}")
        
        return "\n".join(lines)
    
    def _update_error_counts(self, context: str):
        """Update error frequency counts"""
        self.error_counts[context] = self.error_counts.get(context, 0) + 1
    
    def _check_error_frequency(self, context: str):
        """Check if error frequency requires action"""
        count = self.error_counts.get(context, 0)
        
        # If we have too many errors in the same context, log a warning
        if count > 5:
            self.logger.warning(
                f"High error frequency detected in context '{context}': {count} errors. "
                f"Consider investigating the root cause."
            )
        
        # If we have excessive errors, suggest disabling the feature
        if count > 20:
            self.logger.critical(
                f"Excessive error frequency in context '{context}': {count} errors. "
                f"Consider disabling this feature to improve application stability."
            )
    
    def register_fallback_strategy(self, context: str, fallback_func: Callable):
        """
        Register a fallback strategy for a specific context.
        
        Args:
            context: Context identifier
            fallback_func: Function to call as fallback
        """
        self.fallback_strategies[context] = fallback_func
    
    def execute_fallback_strategy(self, context: str, *args, **kwargs) -> Any:
        """
        Execute registered fallback strategy for a context.
        
        Args:
            context: Context identifier
            *args, **kwargs: Arguments to pass to fallback function
            
        Returns:
            Result of fallback function or None if no fallback registered
        """
        fallback_func = self.fallback_strategies.get(context)
        if fallback_func:
            try:
                return fallback_func(*args, **kwargs)
            except Exception as e:
                self.report_widget_error(
                    widget=None,
                    context=f"fallback_{context}",
                    exception=e,
                    severity=ErrorSeverity.ERROR,
                    fallback_used=False,
                    user_impact="Fallback strategy also failed"
                )
        return None
    
    def get_error_summary(self) -> Dict[str, Any]:
        """
        Get summary of widget errors for debugging and monitoring.
        
        Returns:
            Dictionary with error summary statistics
        """
        if not self.error_reports:
            return {
                'total_errors': 0,
                'error_contexts': {},
                'severity_breakdown': {},
                'fallback_usage': 0,
                'recent_errors': []
            }
        
        # Calculate statistics
        total_errors = len(self.error_reports)
        error_contexts = {}
        severity_breakdown = {}
        fallback_usage = 0
        
        for report in self.error_reports:
            # Count by context
            error_contexts[report.context] = error_contexts.get(report.context, 0) + 1
            
            # Count by severity
            severity_key = report.severity.value
            severity_breakdown[severity_key] = severity_breakdown.get(severity_key, 0) + 1
            
            # Count fallback usage
            if report.fallback_used:
                fallback_usage += 1
        
        # Get recent errors (last 10)
        recent_errors = [
            {
                'context': report.context,
                'widget_type': report.widget_type,
                'error_message': report.error_message,
                'severity': report.severity.value,
                'timestamp': report.timestamp.isoformat()
            }
            for report in self.error_reports[-10:]
        ]
        
        return {
            'total_errors': total_errors,
            'error_contexts': error_contexts,
            'severity_breakdown': severity_breakdown,
            'fallback_usage': fallback_usage,
            'fallback_percentage': (fallback_usage / total_errors * 100) if total_errors > 0 else 0,
            'recent_errors': recent_errors
        }
    
    def export_error_log(self, file_path: str = None) -> str:
        """
        Export error log to file or return as string.
        
        Args:
            file_path: Optional file path to save the log
            
        Returns:
            Error log content as string
        """
        if not self.error_reports:
            return "No widget errors recorded."
        
        log_lines = [
            "Widget Error Log Export",
            f"Generated: {datetime.now().isoformat()}",
            f"Total Errors: {len(self.error_reports)}",
            "=" * 50,
            ""
        ]
        
        for report in self.error_reports:
            log_lines.extend([
                f"[{report.timestamp.isoformat()}] {report.severity.value.upper()}",
                f"Context: {report.context}",
                f"Widget: {report.widget_type}",
                f"Error: {report.error_message}",
                f"Fallback: {report.fallback_description if report.fallback_used else 'None'}",
                f"User Impact: {report.user_impact or 'None'}",
                "-" * 30,
                ""
            ])
        
        log_content = "\n".join(log_lines)
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                print(f"Error log exported to: {file_path}")
            except Exception as e:
                print(f"Failed to export error log to {file_path}: {e}")
        
        return log_content
    
    def clear_error_history(self):
        """Clear error history (useful for testing or after fixes)"""
        self.error_reports.clear()
        self.error_counts.clear()
        self.logger.info("Widget error history cleared")
    
    def get_recovery_suggestions(self, context: str) -> List[str]:
        """
        Get recovery suggestions for a specific error context.
        
        Args:
            context: Error context
            
        Returns:
            List of recovery suggestions
        """
        # Get recent errors for this context
        context_errors = [
            report for report in self.error_reports[-50:]  # Last 50 errors
            if report.context == context
        ]
        
        if not context_errors:
            return ["No specific suggestions available for this context"]
        
        # Collect all recovery suggestions for this context
        suggestions = set()
        for report in context_errors:
            suggestions.update(report.recovery_suggestions)
        
        # Add general suggestions based on error patterns
        general_suggestions = self._get_general_recovery_suggestions(context, context_errors)
        suggestions.update(general_suggestions)
        
        return list(suggestions) if suggestions else ["No recovery suggestions available"]
    
    def _get_general_recovery_suggestions(self, context: str, errors: List[WidgetErrorReport]) -> List[str]:
        """Get general recovery suggestions based on error patterns"""
        suggestions = []
        
        # Analyze error patterns
        widget_types = set(error.widget_type for error in errors)
        exception_types = set(error.exception_type for error in errors)
        
        # Widget-specific suggestions
        if 'TextInputElement' in widget_types:
            suggestions.append("Consider using alternative widget access methods for TextInputElement")
        
        if 'CTkButton' in widget_types:
            suggestions.append("Check parent widget availability before creating buttons")
        
        # Exception-specific suggestions
        if 'AttributeError' in exception_types:
            suggestions.append("Verify widget attributes exist before accessing them")
        
        if 'TclError' in exception_types:
            suggestions.append("Ensure widgets are properly initialized before use")
        
        # Context-specific suggestions
        if 'parent_resolution' in context:
            suggestions.extend([
                "Use robust parent resolution utilities",
                "Implement fallback strategies for parent access",
                "Consider alternative widget positioning methods"
            ])
        
        if 'validation' in context:
            suggestions.extend([
                "Implement graceful validation fallbacks",
                "Use console-based validation as last resort",
                "Check widget binding capabilities before setup"
            ])
        
        return suggestions


# Global instance for easy access
widget_error_service = WidgetErrorHandlingService()