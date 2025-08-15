"""
UI Error Handler for Parameter Updates

This service provides safe UI update methods with comprehensive error handling
to prevent crashes when parameter updates fail in the UI.
"""

import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass

from services.parameter_error_feedback_service import ParameterErrorFeedbackService, UserFeedback

logger = logging.getLogger(__name__)


@dataclass
class UIUpdateResult:
    """Result of a UI update operation."""
    parameter_name: str
    success: bool
    error_message: Optional[str] = None
    original_value: Optional[str] = None
    attempted_value: Optional[str] = None


class UIErrorHandler:
    """
    Handles UI update errors with comprehensive error handling and user feedback.
    
    This class provides safe methods for updating UI parameters that prevent
    application crashes when individual parameter updates fail.
    """
    
    def __init__(self, feedback_service: Optional[ParameterErrorFeedbackService] = None):
        """
        Initialize the UI error handler.
        
        Args:
            feedback_service: Optional feedback service for user notifications
        """
        self.feedback_service = feedback_service or ParameterErrorFeedbackService()
        self.failed_updates = []
        self.successful_updates = []
        self.update_warnings = []
    
    def safe_update_parameter_ui(self, 
                                parameter_name: str, 
                                parameter_value: str, 
                                ui_update_function: Callable[[str, str], None],
                                original_value: Optional[str] = None) -> UIUpdateResult:
        """
        Safely update a parameter in the UI with error handling.
        
        Args:
            parameter_name: Name of the parameter being updated
            parameter_value: New value for the parameter
            ui_update_function: Function to call for UI update
            original_value: Original parameter value for fallback
            
        Returns:
            UIUpdateResult with success status and error information
            
        Requirements: 5.3 - Prevent crashes and log UI update errors
        """
        try:
            # Attempt the UI update
            ui_update_function(parameter_name, parameter_value)
            
            # Record successful update
            result = UIUpdateResult(
                parameter_name=parameter_name,
                success=True,
                original_value=original_value,
                attempted_value=parameter_value
            )
            
            self.successful_updates.append(result)
            logger.debug(f"Successfully updated UI for parameter: {parameter_name}")
            
            return result
            
        except Exception as e:
            # Handle UI update failure
            error_msg = f"UI update failed: {str(e)}"
            logger.error(f"Failed to update UI for parameter {parameter_name}: {error_msg}")
            
            # Create failure result
            result = UIUpdateResult(
                parameter_name=parameter_name,
                success=False,
                error_message=error_msg,
                original_value=original_value,
                attempted_value=parameter_value
            )
            
            self.failed_updates.append(result)
            
            # Generate user feedback
            try:
                feedback = self.feedback_service.generate_ui_update_error_feedback(
                    parameter_name, 
                    error_msg
                )
                logger.info(f"Generated user feedback for UI update failure: {feedback.title}")
            except Exception as feedback_error:
                logger.error(f"Failed to generate feedback for UI update error: {feedback_error}")
            
            return result
    
    def safe_batch_update_parameters_ui(self, 
                                       parameters: Dict[str, str], 
                                       ui_update_function: Callable[[str, str], None],
                                       original_parameters: Optional[Dict[str, str]] = None) -> List[UIUpdateResult]:
        """
        Safely update multiple parameters in the UI with error handling.
        
        Args:
            parameters: Dictionary of parameter names to values
            ui_update_function: Function to call for each UI update
            original_parameters: Original parameter values for fallback
            
        Returns:
            List of UIUpdateResult for each parameter update attempt
            
        Requirements: 5.2, 5.3 - Continue processing other parameters, prevent crashes
        """
        results = []
        
        for param_name, param_value in parameters.items():
            original_value = original_parameters.get(param_name) if original_parameters else None
            
            result = self.safe_update_parameter_ui(
                param_name, 
                param_value, 
                ui_update_function, 
                original_value
            )
            
            results.append(result)
        
        # Generate summary feedback if there were failures
        failed_count = sum(1 for r in results if not r.success)
        if failed_count > 0:
            self._generate_batch_update_feedback(results)
        
        return results
    
    def _generate_batch_update_feedback(self, results: List[UIUpdateResult]):
        """
        Generate summary feedback for batch UI updates.
        
        Args:
            results: List of UIUpdateResult from batch update
        """
        failed_results = [r for r in results if not r.success]
        successful_results = [r for r in results if r.success]
        
        if not failed_results:
            return
        
        try:
            # Create summary message
            total_count = len(results)
            failed_count = len(failed_results)
            success_count = len(successful_results)
            
            if failed_count == total_count:
                # All updates failed
                summary_msg = f"All {total_count} parameter UI updates failed. Parameters were processed successfully but are not visible in the interface."
            else:
                # Partial failure
                summary_msg = f"{failed_count} of {total_count} parameter UI updates failed. {success_count} parameters are visible, {failed_count} may require interface refresh."
            
            # Log the summary
            logger.warning(summary_msg)
            
            # Add to warnings for user visibility
            self.update_warnings.append(summary_msg)
            
            # Log details of failed updates
            for result in failed_results[:5]:  # Log first 5 failures
                logger.warning(f"UI update failed for {result.parameter_name}: {result.error_message}")
                
        except Exception as e:
            logger.error(f"Failed to generate batch update feedback: {e}")
    
    def safe_update_with_fallback(self, 
                                 parameter_name: str, 
                                 parameter_value: str, 
                                 ui_update_function: Callable[[str, str], None],
                                 fallback_function: Optional[Callable[[str, str], None]] = None,
                                 original_value: Optional[str] = None) -> UIUpdateResult:
        """
        Safely update parameter UI with fallback mechanism.
        
        Args:
            parameter_name: Name of the parameter being updated
            parameter_value: New value for the parameter
            ui_update_function: Primary function to call for UI update
            fallback_function: Optional fallback function if primary fails
            original_value: Original parameter value
            
        Returns:
            UIUpdateResult with success status and error information
        """
        # Try primary update function
        result = self.safe_update_parameter_ui(
            parameter_name, 
            parameter_value, 
            ui_update_function, 
            original_value
        )
        
        # If primary failed and fallback is available, try fallback
        if not result.success and fallback_function:
            logger.info(f"Attempting fallback UI update for parameter: {parameter_name}")
            
            try:
                fallback_function(parameter_name, parameter_value)
                
                # Update result to reflect successful fallback
                result.success = True
                result.error_message = None
                
                logger.info(f"Fallback UI update successful for parameter: {parameter_name}")
                
            except Exception as fallback_error:
                # Fallback also failed
                fallback_msg = f"Fallback UI update also failed: {str(fallback_error)}"
                result.error_message = f"{result.error_message}; {fallback_msg}"
                logger.error(f"Fallback failed for parameter {parameter_name}: {fallback_msg}")
        
        return result
    
    def get_update_summary(self) -> Dict[str, Any]:
        """
        Get a summary of UI update operations.
        
        Returns:
            Dictionary with update statistics and error information
        """
        total_updates = len(self.successful_updates) + len(self.failed_updates)
        
        return {
            'total_updates': total_updates,
            'successful_updates': len(self.successful_updates),
            'failed_updates': len(self.failed_updates),
            'success_rate': (len(self.successful_updates) / total_updates * 100) if total_updates > 0 else 0,
            'failed_parameter_names': [r.parameter_name for r in self.failed_updates],
            'update_warnings': self.update_warnings.copy(),
            'recent_failures': [
                {
                    'parameter': r.parameter_name,
                    'error': r.error_message,
                    'attempted_value': r.attempted_value
                }
                for r in self.failed_updates[-5:]  # Last 5 failures
            ]
        }
    
    def clear_update_history(self):
        """Clear the update history and reset counters."""
        self.failed_updates.clear()
        self.successful_updates.clear()
        self.update_warnings.clear()
        logger.debug("Cleared UI update history")
    
    def has_update_failures(self) -> bool:
        """Check if there have been any UI update failures."""
        return len(self.failed_updates) > 0
    
    def get_failed_parameters(self) -> List[str]:
        """Get list of parameter names that failed to update in UI."""
        return [result.parameter_name for result in self.failed_updates]