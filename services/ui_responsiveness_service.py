"""
UI Responsiveness Service for ensuring consistent UI updates within 100ms.

This service provides batch UI updates, visual feedback during parameter processing,
and performance monitoring to meet the UI responsiveness requirements.
"""

import time
import threading
from typing import Dict, Any, List, Callable, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class UpdatePriority(Enum):
    """Priority levels for UI updates."""
    HIGH = "high"      # Critical parameters that need immediate update
    NORMAL = "normal"  # Standard parameters
    LOW = "low"        # Non-critical parameters that can be batched


@dataclass
class UIUpdateRequest:
    """Request for UI parameter update."""
    param_name: str
    value: Any
    priority: UpdatePriority = UpdatePriority.NORMAL
    highlight: bool = True
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class BatchUpdateResult:
    """Result of batch UI update operation."""
    total_updates: int
    successful_updates: int
    failed_updates: int
    update_duration_ms: float
    errors: List[str]
    warnings: List[str]


class UIResponsivenessService:
    """
    Service for ensuring consistent UI responsiveness with batch updates and visual feedback.
    
    This service manages UI parameter updates to ensure they complete within 100ms,
    provides visual feedback during processing, and handles large parameter sets efficiently.
    
    Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
    """
    
    def __init__(self, parameters_frame=None):
        """
        Initialize the UI responsiveness service.
        
        Args:
            parameters_frame: Reference to the parameters frame for UI updates
        """
        self.parameters_frame = parameters_frame
        self.update_queue = []
        self.batch_size = 10  # Maximum updates per batch
        self.max_update_time_ms = 100  # Maximum time for updates (Requirement 7.1)
        self.update_lock = threading.Lock()
        self.is_processing = False
        self.performance_metrics = []
        
        # Visual feedback state
        self.processing_indicators = {}
        self.update_highlights = {}
        
    def queue_parameter_update(self, param_name: str, value: Any, 
                             priority: UpdatePriority = UpdatePriority.NORMAL,
                             highlight: bool = True) -> None:
        """
        Queue a parameter update for batch processing.
        
        Args:
            param_name: Name of the parameter to update
            value: New value for the parameter
            priority: Update priority level
            highlight: Whether to highlight the updated parameter
            
        Requirements: 7.2
        """
        with self.update_lock:
            update_request = UIUpdateRequest(
                param_name=param_name,
                value=value,
                priority=priority,
                highlight=highlight
            )
            
            # Insert based on priority
            if priority == UpdatePriority.HIGH:
                self.update_queue.insert(0, update_request)
            else:
                self.update_queue.append(update_request)
            
            logger.debug(f"Queued parameter update: {param_name} = {value} (priority: {priority.value})")
    
    def queue_multiple_parameter_updates(self, parameters: Dict[str, Any], 
                                       priority: UpdatePriority = UpdatePriority.NORMAL,
                                       highlight: bool = True) -> None:
        """
        Queue multiple parameter updates for batch processing.
        
        Args:
            parameters: Dictionary of parameter names to values
            priority: Update priority level for all parameters
            highlight: Whether to highlight updated parameters
            
        Requirements: 7.2
        """
        with self.update_lock:
            for param_name, value in parameters.items():
                self.queue_parameter_update(param_name, value, priority, highlight)
            
            logger.info(f"Queued {len(parameters)} parameter updates for batch processing")
    
    def process_update_queue(self, force_immediate: bool = False) -> BatchUpdateResult:
        """
        Process queued parameter updates in batches with time constraints.
        
        Args:
            force_immediate: Whether to process all updates immediately
            
        Returns:
            BatchUpdateResult: Results of the batch update operation
            
        Requirements: 7.1, 7.2, 7.4
        """
        if self.is_processing and not force_immediate:
            logger.debug("Update processing already in progress, skipping")
            return BatchUpdateResult(0, 0, 0, 0.0, [], [])
        
        start_time = time.time()
        self.is_processing = True
        
        try:
            with self.update_lock:
                if not self.update_queue:
                    return BatchUpdateResult(0, 0, 0, 0.0, [], [])
                
                # Determine batch size based on time constraints
                batch_size = self._calculate_optimal_batch_size()
                updates_to_process = self.update_queue[:batch_size]
                self.update_queue = self.update_queue[batch_size:]
            
            # Show visual feedback for processing
            self._show_processing_feedback(len(updates_to_process))
            
            # Process updates in batch
            result = self._execute_batch_updates(updates_to_process)
            
            # Record performance metrics
            total_duration_ms = (time.time() - start_time) * 1000
            self._record_performance_metrics(result, total_duration_ms)
            
            # Hide processing feedback
            self._hide_processing_feedback()
            
            # Log performance
            if total_duration_ms > self.max_update_time_ms:
                logger.warning(f"Batch update took {total_duration_ms:.1f}ms, exceeding {self.max_update_time_ms}ms target")
            else:
                logger.debug(f"Batch update completed in {total_duration_ms:.1f}ms")
            
            return result
            
        finally:
            self.is_processing = False
    
    def _calculate_optimal_batch_size(self) -> int:
        """
        Calculate optimal batch size based on recent performance metrics.
        
        Returns:
            int: Optimal batch size for current conditions
        """
        if not self.update_queue:
            return 0
            
        if not self.performance_metrics:
            return min(self.batch_size, len(self.update_queue))
        
        # Use recent metrics to estimate processing time per update
        recent_metrics = self.performance_metrics[-5:]  # Last 5 batches
        avg_time_per_update = sum(m['duration_ms'] / max(1, m['total_updates']) 
                                for m in recent_metrics) / len(recent_metrics)
        
        # Calculate batch size to stay within time limit
        if avg_time_per_update > 0:
            optimal_size = int(self.max_update_time_ms / avg_time_per_update)
            return max(1, min(optimal_size, len(self.update_queue)))
        
        return min(self.batch_size, len(self.update_queue))
    
    def _execute_batch_updates(self, updates: List[UIUpdateRequest]) -> BatchUpdateResult:
        """
        Execute a batch of UI updates with error handling.
        
        Args:
            updates: List of update requests to process
            
        Returns:
            BatchUpdateResult: Results of the batch operation
        """
        start_time = time.time()
        successful_updates = 0
        failed_updates = 0
        errors = []
        warnings = []
        
        # Group updates by priority for processing order
        high_priority = [u for u in updates if u.priority == UpdatePriority.HIGH]
        normal_priority = [u for u in updates if u.priority == UpdatePriority.NORMAL]
        low_priority = [u for u in updates if u.priority == UpdatePriority.LOW]
        
        # Process in priority order
        for update_group in [high_priority, normal_priority, low_priority]:
            for update in update_group:
                try:
                    # Check if we're approaching time limit
                    elapsed_ms = (time.time() - start_time) * 1000
                    if elapsed_ms > self.max_update_time_ms * 0.9:  # 90% of time limit
                        warnings.append(f"Approaching time limit, deferring {len(updates) - successful_updates - failed_updates} updates")
                        # Re-queue remaining updates
                        remaining_updates = update_group[update_group.index(update):]
                        with self.update_lock:
                            self.update_queue = remaining_updates + self.update_queue
                        break
                    
                    # Execute the update
                    success = self._execute_single_update(update)
                    
                    if success:
                        successful_updates += 1
                        
                        # Apply highlighting if requested
                        if update.highlight:
                            self._apply_parameter_highlight(update.param_name, True)
                    else:
                        failed_updates += 1
                        errors.append(f"Failed to update parameter: {update.param_name}")
                        
                except Exception as e:
                    failed_updates += 1
                    error_msg = f"Error updating {update.param_name}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
        
        duration_ms = (time.time() - start_time) * 1000
        
        return BatchUpdateResult(
            total_updates=len(updates),
            successful_updates=successful_updates,
            failed_updates=failed_updates,
            update_duration_ms=duration_ms,
            errors=errors,
            warnings=warnings
        )
    
    def _execute_single_update(self, update: UIUpdateRequest) -> bool:
        """
        Execute a single parameter update.
        
        Args:
            update: Update request to execute
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.parameters_frame:
                logger.warning("No parameters frame available for UI updates")
                return False
            
            # Update the parameter value in the UI
            self.parameters_frame.update_parameter_value(update.param_name, update.value)
            
            logger.debug(f"Successfully updated parameter: {update.param_name} = {update.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute update for {update.param_name}: {str(e)}")
            return False
    
    def _show_processing_feedback(self, update_count: int) -> None:
        """
        Show visual feedback during parameter processing.
        
        Args:
            update_count: Number of updates being processed
            
        Requirements: 7.3
        """
        try:
            if self.parameters_frame and hasattr(self.parameters_frame, 'master'):
                # Schedule UI feedback on main thread
                self.parameters_frame.after_idle(
                    self._do_show_processing_feedback, update_count
                )
        except Exception as e:
            logger.debug(f"Could not show processing feedback: {str(e)}")
    
    def _do_show_processing_feedback(self, update_count: int) -> None:
        """
        Execute visual feedback display on main thread.
        
        Args:
            update_count: Number of updates being processed
        """
        try:
            # Change cursor to indicate processing
            if self.parameters_frame and hasattr(self.parameters_frame, 'configure'):
                self.parameters_frame.configure(cursor="watch")
            
            # Store processing state
            self.processing_indicators['active'] = True
            self.processing_indicators['count'] = update_count
            self.processing_indicators['start_time'] = time.time()
            
        except Exception as e:
            logger.debug(f"Error showing processing feedback: {str(e)}")
    
    def _hide_processing_feedback(self) -> None:
        """
        Hide visual feedback after processing completion.
        
        Requirements: 7.3
        """
        try:
            if self.parameters_frame and hasattr(self.parameters_frame, 'master'):
                # Schedule UI feedback removal on main thread
                self.parameters_frame.after_idle(self._do_hide_processing_feedback)
        except Exception as e:
            logger.debug(f"Could not hide processing feedback: {str(e)}")
    
    def _do_hide_processing_feedback(self) -> None:
        """
        Execute visual feedback removal on main thread.
        """
        try:
            # Reset cursor
            if self.parameters_frame and hasattr(self.parameters_frame, 'configure'):
                self.parameters_frame.configure(cursor="")
            
            # Clear processing state
            self.processing_indicators.clear()
            
        except Exception as e:
            logger.debug(f"Error hiding processing feedback: {str(e)}")
    
    def _apply_parameter_highlight(self, param_name: str, value_changed: bool) -> None:
        """
        Apply highlighting to updated parameter.
        
        Args:
            param_name: Name of the parameter to highlight
            value_changed: Whether the value actually changed
        """
        try:
            if self.parameters_frame and hasattr(self.parameters_frame, 'highlight_updated_parameter'):
                # Schedule highlighting on main thread
                self.parameters_frame.after_idle(
                    self.parameters_frame.highlight_updated_parameter,
                    param_name, value_changed
                )
                
                # Track highlight for cleanup
                self.update_highlights[param_name] = {
                    'timestamp': time.time(),
                    'value_changed': value_changed
                }
                
        except Exception as e:
            logger.debug(f"Could not apply parameter highlight: {str(e)}")
    
    def _record_performance_metrics(self, result: BatchUpdateResult, total_duration_ms: float) -> None:
        """
        Record performance metrics for optimization.
        
        Args:
            result: Batch update result
            total_duration_ms: Total duration of the operation
        """
        metric = {
            'timestamp': time.time(),
            'total_updates': result.total_updates,
            'successful_updates': result.successful_updates,
            'failed_updates': result.failed_updates,
            'duration_ms': total_duration_ms,
            'updates_per_second': result.successful_updates / (total_duration_ms / 1000) if total_duration_ms > 0 else 0
        }
        
        self.performance_metrics.append(metric)
        
        # Keep only recent metrics (last 20 batches)
        if len(self.performance_metrics) > 20:
            self.performance_metrics = self.performance_metrics[-20:]
    
    def process_large_parameter_set(self, parameters: Dict[str, Any], 
                                  progress_callback: Optional[Callable[[int, int], None]] = None) -> BatchUpdateResult:
        """
        Process large parameter sets with progress tracking and time management.
        
        Args:
            parameters: Large set of parameters to update
            progress_callback: Optional callback for progress updates
            
        Returns:
            BatchUpdateResult: Combined results of all batch operations
            
        Requirements: 7.4, 7.5
        """
        if not parameters:
            return BatchUpdateResult(0, 0, 0, 0.0, [], [])
        
        logger.info(f"Processing large parameter set with {len(parameters)} parameters")
        
        # Queue all parameters for batch processing
        self.queue_multiple_parameter_updates(parameters, UpdatePriority.NORMAL, True)
        
        # Process in batches with progress tracking
        total_processed = 0
        total_successful = 0
        total_failed = 0
        total_duration = 0.0
        all_errors = []
        all_warnings = []
        
        total_parameters = len(parameters)
        
        max_iterations = 100  # Safety limit to prevent infinite loops
        iteration_count = 0
        
        while self.update_queue and iteration_count < max_iterations:
            iteration_count += 1
            
            # Process next batch
            batch_result = self.process_update_queue()
            
            # If no updates were processed, break to prevent infinite loop
            if batch_result.total_updates == 0:
                logger.warning("No updates processed in batch, breaking to prevent infinite loop")
                break
            
            # Accumulate results
            total_processed += batch_result.total_updates
            total_successful += batch_result.successful_updates
            total_failed += batch_result.failed_updates
            total_duration += batch_result.update_duration_ms
            all_errors.extend(batch_result.errors)
            all_warnings.extend(batch_result.warnings)
            
            # Report progress
            if progress_callback:
                try:
                    progress_callback(total_processed, total_parameters)
                except Exception as e:
                    logger.debug(f"Progress callback error: {str(e)}")
            
            # Small delay between batches to prevent UI blocking
            if self.update_queue:  # More batches to process
                time.sleep(0.001)  # 1ms delay
        
        # Check if we hit the safety limit
        if iteration_count >= max_iterations:
            logger.warning(f"Hit maximum iteration limit ({max_iterations}) in process_large_parameter_set")
            all_warnings.append(f"Processing stopped at iteration limit ({max_iterations})")
        
        # Create combined result
        combined_result = BatchUpdateResult(
            total_updates=total_processed,
            successful_updates=total_successful,
            failed_updates=total_failed,
            update_duration_ms=total_duration,
            errors=all_errors,
            warnings=all_warnings
        )
        
        logger.info(f"Large parameter set processing completed: {total_successful}/{total_processed} successful in {total_duration:.1f}ms")
        
        return combined_result
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get performance summary for monitoring and optimization.
        
        Returns:
            Dict[str, Any]: Performance metrics summary
        """
        if not self.performance_metrics:
            return {
                'total_batches': 0,
                'avg_duration_ms': 0.0,
                'avg_updates_per_batch': 0.0,
                'avg_updates_per_second': 0.0,
                'max_duration_ms': 0.0,
                'min_duration_ms': 0.0
            }
        
        durations = [m['duration_ms'] for m in self.performance_metrics]
        update_counts = [m['total_updates'] for m in self.performance_metrics]
        update_rates = [m['updates_per_second'] for m in self.performance_metrics]
        
        return {
            'total_batches': len(self.performance_metrics),
            'avg_duration_ms': sum(durations) / len(durations),
            'avg_updates_per_batch': sum(update_counts) / len(update_counts),
            'avg_updates_per_second': sum(update_rates) / len(update_rates),
            'max_duration_ms': max(durations),
            'min_duration_ms': min(durations),
            'queue_size': len(self.update_queue),
            'is_processing': self.is_processing
        }
    
    def clear_update_queue(self) -> int:
        """
        Clear all pending updates from the queue.
        
        Returns:
            int: Number of updates that were cleared
        """
        with self.update_lock:
            cleared_count = len(self.update_queue)
            self.update_queue.clear()
            
        logger.info(f"Cleared {cleared_count} pending updates from queue")
        return cleared_count
    
    def set_parameters_frame(self, parameters_frame) -> None:
        """
        Set the parameters frame reference for UI updates.
        
        Args:
            parameters_frame: Reference to the parameters frame
        """
        self.parameters_frame = parameters_frame
        logger.debug("Parameters frame reference updated")