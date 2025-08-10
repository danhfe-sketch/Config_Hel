"""
Widget Parent Resolution Utility

This module provides utilities for safely resolving parent widgets from various
UI element types, including custom UI elements that don't follow standard tkinter
patterns.
"""

from typing import Any, Optional, List, Dict
from dataclasses import dataclass
import logging
import traceback
import sys
from datetime import datetime


@dataclass
class ParentResolutionResult:
    """Result of parent widget resolution attempt"""
    parent: Optional[Any]
    method_used: str
    success: bool
    fallback_available: bool


@dataclass
class WidgetIntrospectionInfo:
    """Information about widget structure and available attributes"""
    widget_type: str
    available_attributes: List[str]
    parent_access_methods: List[str]
    hierarchy_depth: int


def get_widget_parent(widget: Any) -> Optional[Any]:
    """
    Safely get the parent container of a widget using multiple strategies.
    
    This function attempts various methods to find the parent widget, handling
    different UI element types including custom elements that don't follow
    standard tkinter patterns.
    
    Args:
        widget: The widget to find the parent for
        
    Returns:
        Parent widget or None if not found
    """
    if widget is None:
        return None
    
    # Strategy 1: Try standard tkinter master attribute
    try:
        if hasattr(widget, 'master'):
            parent = widget.master
            if parent is not None and parent != "" and parent is not False:
                return parent
    except (AttributeError, Exception):
        pass
    
    # Strategy 2: Try winfo_parent() for tkinter widgets
    try:
        if hasattr(widget, 'winfo_parent'):
            parent_name = widget.winfo_parent()
            if parent_name and parent_name != "":
                # Get the actual parent widget from the name
                if hasattr(widget, 'nametowidget'):
                    parent = widget.nametowidget(parent_name)
                    if parent is not None:
                        return parent
    except (AttributeError, Exception):
        pass
    
    # Strategy 3: Try custom _parent attribute
    try:
        if hasattr(widget, '_parent'):
            parent = widget._parent
            if parent is not None and parent != "" and parent is not False:
                return parent
    except (AttributeError, Exception):
        pass
    
    # Strategy 4: Try container attribute (for parameter UI elements)
    try:
        if hasattr(widget, 'container'):
            parent = widget.container
            if parent is not None and parent != "" and parent is not False:
                return parent
    except (AttributeError, Exception):
        pass
    
    # Strategy 5: Try container_frame attribute (for BaseUIElement derivatives)
    try:
        if hasattr(widget, 'container_frame'):
            parent = widget.container_frame
            if parent is not None and parent != "" and parent is not False:
                return parent
    except (AttributeError, Exception):
        pass
    
    # Strategy 6: Try parent attribute (alternative naming)
    try:
        if hasattr(widget, 'parent'):
            parent = widget.parent
            if parent is not None and parent != "" and parent is not False:
                return parent
    except (AttributeError, Exception):
        pass
    
    # Strategy 7: For custom UI elements, try accessing the actual tkinter widget
    try:
        if hasattr(widget, 'widget'):
            actual_widget = widget.widget
            if actual_widget is not None and hasattr(actual_widget, 'master'):
                parent = actual_widget.master
                if parent is not None and parent != "" and parent is not False:
                    return parent
    except (AttributeError, Exception):
        pass
    
    # Strategy 8: Try winfo_parent on the wrapped widget
    try:
        if hasattr(widget, 'widget'):
            actual_widget = widget.widget
            if actual_widget is not None and hasattr(actual_widget, 'winfo_parent'):
                parent_name = actual_widget.winfo_parent()
                if parent_name and parent_name != "":
                    if hasattr(actual_widget, 'nametowidget'):
                        parent = actual_widget.nametowidget(parent_name)
                        if parent is not None:
                            return parent
    except (AttributeError, Exception):
        pass
    
    # No parent found
    return None


def get_widget_parent_with_details(widget: Any) -> ParentResolutionResult:
    """
    Get widget parent with detailed information about the resolution process.
    
    Args:
        widget: The widget to find the parent for
        
    Returns:
        ParentResolutionResult with details about the resolution attempt
    """
    if widget is None:
        return ParentResolutionResult(
            parent=None,
            method_used="none",
            success=False,
            fallback_available=False
        )
    
    # Try each strategy and record which one worked
    def _safe_get_attr(w, attr):
        """Safely get attribute and check for valid values"""
        if not hasattr(w, attr):
            return None
        value = getattr(w, attr, None)
        if value is not None and value != "" and value is not False:
            return value
        return None
    
    strategies = [
        ("master", lambda w: _safe_get_attr(w, 'master')),
        ("winfo_parent", _try_winfo_parent),
        ("_parent", lambda w: _safe_get_attr(w, '_parent')),
        ("container", lambda w: _safe_get_attr(w, 'container')),
        ("container_frame", lambda w: _safe_get_attr(w, 'container_frame')),
        ("parent", lambda w: _safe_get_attr(w, 'parent')),
        ("widget.master", _try_widget_master),
        ("widget.winfo_parent", _try_widget_winfo_parent),
    ]
    
    for method_name, strategy_func in strategies:
        try:
            parent = strategy_func(widget)
            if parent is not None:
                return ParentResolutionResult(
                    parent=parent,
                    method_used=method_name,
                    success=True,
                    fallback_available=True
                )
        except Exception:
            continue
    
    return ParentResolutionResult(
        parent=None,
        method_used="none",
        success=False,
        fallback_available=False
    )


def _try_winfo_parent(widget: Any) -> Optional[Any]:
    """Try to get parent using winfo_parent method"""
    if not hasattr(widget, 'winfo_parent'):
        return None
    
    parent_name = widget.winfo_parent()
    if not parent_name or parent_name == "":
        return None
    
    if hasattr(widget, 'nametowidget'):
        parent = widget.nametowidget(parent_name)
        if parent is not None:
            return parent
    
    return None


def _try_widget_master(widget: Any) -> Optional[Any]:
    """Try to get parent from wrapped widget's master attribute"""
    if not hasattr(widget, 'widget'):
        return None
    
    actual_widget = widget.widget
    if actual_widget is None:
        return None
    
    if hasattr(actual_widget, 'master'):
        parent = actual_widget.master
        if parent is not None and parent != "" and parent is not False:
            return parent
    
    return None


def _try_widget_winfo_parent(widget: Any) -> Optional[Any]:
    """Try to get parent from wrapped widget's winfo_parent method"""
    if not hasattr(widget, 'widget'):
        return None
    
    actual_widget = widget.widget
    if actual_widget is None:
        return None
    
    return _try_winfo_parent(actual_widget)


def inspect_widget_attributes(widget: Any) -> WidgetIntrospectionInfo:
    """
    Analyze widget structure and available attributes for debugging.
    
    Args:
        widget: The widget to inspect
        
    Returns:
        WidgetIntrospectionInfo with analysis results
    """
    if widget is None:
        return WidgetIntrospectionInfo(
            widget_type="None",
            available_attributes=[],
            parent_access_methods=[],
            hierarchy_depth=0
        )
    
    widget_type = type(widget).__name__
    available_attributes = [attr for attr in dir(widget) if not attr.startswith('__')]
    
    # Check which parent access methods are available
    parent_access_methods = []
    
    if hasattr(widget, 'master'):
        parent_access_methods.append('master')
    if hasattr(widget, 'winfo_parent'):
        parent_access_methods.append('winfo_parent')
    if hasattr(widget, '_parent'):
        parent_access_methods.append('_parent')
    if hasattr(widget, 'container'):
        parent_access_methods.append('container')
    if hasattr(widget, 'container_frame'):
        parent_access_methods.append('container_frame')
    if hasattr(widget, 'parent'):
        parent_access_methods.append('parent')
    if hasattr(widget, 'widget'):
        parent_access_methods.append('widget (wrapped)')
        # Check wrapped widget
        try:
            wrapped = widget.widget
            if wrapped and hasattr(wrapped, 'master'):
                parent_access_methods.append('widget.master')
            if wrapped and hasattr(wrapped, 'winfo_parent'):
                parent_access_methods.append('widget.winfo_parent')
        except:
            pass
    
    # Calculate hierarchy depth
    hierarchy_depth = _calculate_hierarchy_depth(widget)
    
    return WidgetIntrospectionInfo(
        widget_type=widget_type,
        available_attributes=available_attributes,
        parent_access_methods=parent_access_methods,
        hierarchy_depth=hierarchy_depth
    )


def _calculate_hierarchy_depth(widget: Any, max_depth: int = 10) -> int:
    """Calculate widget hierarchy depth"""
    depth = 0
    current = widget
    
    while current and depth < max_depth:
        parent = get_widget_parent(current)
        if parent is None or parent == current:
            break
        current = parent
        depth += 1
    
    return depth


def get_widget_hierarchy_info(widget: Any, max_levels: int = 5) -> Dict[str, Any]:
    """
    Get detailed information about widget hierarchy for debugging.
    
    Args:
        widget: The widget to analyze
        max_levels: Maximum levels to traverse up the hierarchy
        
    Returns:
        Dictionary with hierarchy information
    """
    hierarchy = []
    current = widget
    level = 0
    
    while current and level < max_levels:
        info = inspect_widget_attributes(current)
        hierarchy.append({
            'level': level,
            'widget_type': info.widget_type,
            'available_methods': info.parent_access_methods,
            'widget_id': id(current)
        })
        
        parent = get_widget_parent(current)
        if parent is None or parent == current:
            break
        
        current = parent
        level += 1
    
    return {
        'hierarchy': hierarchy,
        'total_levels': level,
        'root_found': level < max_levels
    }


def log_widget_access_debug(widget: Any, context: str = "") -> None:
    """
    Log detailed debugging information about widget access attempts.
    
    Args:
        widget: The widget being accessed
        context: Additional context for the log message
    """
    logger = logging.getLogger(__name__)
    
    if widget is None:
        logger.warning(f"Widget access debug [{context}]: Widget is None")
        return
    
    info = inspect_widget_attributes(widget)
    resolution_result = get_widget_parent_with_details(widget)
    
    logger.debug(f"Widget access debug [{context}]:")
    logger.debug(f"  Widget type: {info.widget_type}")
    logger.debug(f"  Available parent methods: {info.parent_access_methods}")
    logger.debug(f"  Resolution success: {resolution_result.success}")
    logger.debug(f"  Method used: {resolution_result.method_used}")
    logger.debug(f"  Parent found: {resolution_result.parent is not None}")
    
    if not resolution_result.success:
        logger.warning(f"Failed to resolve parent for {info.widget_type} widget in context: {context}")
        hierarchy_info = get_widget_hierarchy_info(widget)
        logger.debug(f"  Hierarchy info: {hierarchy_info}")


def log_widget_access_failure(widget: Any, context: str, exception: Exception = None, 
                             fallback_used: bool = False, fallback_description: str = "") -> None:
    """
    Log detailed information about widget access failures with comprehensive error details.
    
    Args:
        widget: The widget that failed to be accessed
        context: Context where the failure occurred
        exception: The exception that occurred (if any)
        fallback_used: Whether a fallback strategy was used
        fallback_description: Description of the fallback strategy used
    """
    logger = logging.getLogger(__name__)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create detailed error report
    error_report = [
        f"=== Widget Access Failure Report [{timestamp}] ===",
        f"Context: {context}",
        f"Fallback Used: {fallback_used}",
    ]
    
    if fallback_used and fallback_description:
        error_report.append(f"Fallback Strategy: {fallback_description}")
    
    # Widget information
    if widget is not None:
        try:
            info = inspect_widget_attributes(widget)
            error_report.extend([
                f"Widget Type: {info.widget_type}",
                f"Available Attributes: {len(info.available_attributes)} attributes",
                f"Parent Access Methods: {info.parent_access_methods}",
                f"Hierarchy Depth: {info.hierarchy_depth}",
            ])
            
            # Try to get more detailed widget information
            widget_details = _get_detailed_widget_info(widget)
            if widget_details:
                error_report.append(f"Widget Details: {widget_details}")
                
        except Exception as info_error:
            error_report.append(f"Failed to get widget info: {str(info_error)}")
    else:
        error_report.append("Widget: None")
    
    # Exception information
    if exception:
        error_report.extend([
            f"Exception Type: {type(exception).__name__}",
            f"Exception Message: {str(exception)}",
        ])
        
        # Add traceback if available
        if hasattr(exception, '__traceback__') and exception.__traceback__:
            tb_lines = traceback.format_tb(exception.__traceback__)
            error_report.append("Traceback:")
            error_report.extend([f"  {line.strip()}" for line in tb_lines])
    
    # Resolution attempt details
    if widget is not None:
        try:
            resolution_result = get_widget_parent_with_details(widget)
            error_report.extend([
                f"Resolution Attempted: {resolution_result.method_used}",
                f"Resolution Success: {resolution_result.success}",
                f"Fallback Available: {resolution_result.fallback_available}",
            ])
        except Exception as res_error:
            error_report.append(f"Failed to get resolution details: {str(res_error)}")
    
    error_report.append("=" * 50)
    
    # Log the complete error report
    full_report = "\n".join(error_report)
    
    if fallback_used:
        logger.warning(f"Widget access failure with fallback in context '{context}':\n{full_report}")
    else:
        logger.error(f"Widget access failure in context '{context}':\n{full_report}")
    
    # Also print to console for immediate visibility during development
    print(f"WIDGET ACCESS FAILURE [{context}]: {exception if exception else 'Unknown error'}")
    if fallback_used:
        print(f"  Fallback strategy used: {fallback_description}")


def log_widget_access_warning(widget: Any, context: str, warning_message: str, 
                             fallback_strategy: str = "") -> None:
    """
    Log warning messages for widget access issues that don't prevent functionality.
    
    Args:
        widget: The widget being accessed
        context: Context where the warning occurred
        warning_message: The warning message
        fallback_strategy: Description of fallback strategy being used
    """
    logger = logging.getLogger(__name__)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    warning_details = [
        f"Widget Access Warning [{timestamp}]",
        f"Context: {context}",
        f"Warning: {warning_message}",
    ]
    
    if fallback_strategy:
        warning_details.append(f"Fallback Strategy: {fallback_strategy}")
    
    if widget is not None:
        try:
            info = inspect_widget_attributes(widget)
            warning_details.extend([
                f"Widget Type: {info.widget_type}",
                f"Available Methods: {info.parent_access_methods}",
            ])
        except Exception:
            warning_details.append("Widget Info: Unable to retrieve")
    
    full_warning = " | ".join(warning_details)
    logger.warning(full_warning)
    
    # Print abbreviated warning to console
    print(f"WARNING [{context}]: {warning_message}")
    if fallback_strategy:
        print(f"  Using fallback: {fallback_strategy}")


def log_widget_hierarchy_analysis(widget: Any, context: str = "", max_levels: int = 5) -> None:
    """
    Log detailed widget hierarchy analysis for debugging complex widget structures.
    
    Args:
        widget: The widget to analyze
        context: Context for the analysis
        max_levels: Maximum hierarchy levels to analyze
    """
    logger = logging.getLogger(__name__)
    
    if widget is None:
        logger.debug(f"Hierarchy analysis [{context}]: Widget is None")
        return
    
    try:
        hierarchy_info = get_widget_hierarchy_info(widget, max_levels)
        
        analysis_report = [
            f"=== Widget Hierarchy Analysis [{context}] ===",
            f"Total Levels Found: {hierarchy_info['total_levels']}",
            f"Root Found: {hierarchy_info['root_found']}",
            "Hierarchy Details:",
        ]
        
        for level_info in hierarchy_info['hierarchy']:
            level = level_info['level']
            widget_type = level_info['widget_type']
            methods = level_info['available_methods']
            widget_id = level_info['widget_id']
            
            analysis_report.append(
                f"  Level {level}: {widget_type} (ID: {widget_id}) - Methods: {methods}"
            )
        
        analysis_report.append("=" * 50)
        
        full_analysis = "\n".join(analysis_report)
        logger.debug(full_analysis)
        
    except Exception as e:
        logger.error(f"Failed to analyze widget hierarchy for context '{context}': {str(e)}")


def _get_detailed_widget_info(widget: Any) -> str:
    """
    Get detailed information about a widget for error reporting.
    
    Args:
        widget: The widget to analyze
        
    Returns:
        String with detailed widget information
    """
    details = []
    
    try:
        # Basic widget information
        details.append(f"Type: {type(widget).__name__}")
        details.append(f"ID: {id(widget)}")
        
        # Try to get widget name/title if available
        for attr in ['_name', 'name', 'title', '_title']:
            if hasattr(widget, attr):
                try:
                    value = getattr(widget, attr)
                    if value:
                        details.append(f"{attr}: {value}")
                        break
                except Exception:
                    continue
        
        # Check for common widget properties
        for prop in ['width', 'height', 'x', 'y']:
            if hasattr(widget, prop):
                try:
                    value = getattr(widget, prop)
                    details.append(f"{prop}: {value}")
                except Exception:
                    continue
        
        # Check if widget is visible/mapped
        for visibility_attr in ['winfo_viewable', 'winfo_ismapped', 'winfo_exists']:
            if hasattr(widget, visibility_attr):
                try:
                    value = getattr(widget, visibility_attr)()
                    details.append(f"{visibility_attr}: {value}")
                except Exception:
                    continue
        
        return " | ".join(details) if details else "No details available"
        
    except Exception as e:
        return f"Error getting details: {str(e)}"


def ensure_application_continues(operation_name: str, critical: bool = False) -> callable:
    """
    Decorator to ensure application continues functioning even when UI enhancements fail.
    
    Args:
        operation_name: Name of the operation being performed
        critical: Whether this operation is critical to application functionality
        
    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Log the error with full details
                context = f"{operation_name}_operation"
                
                # Get widget from args if available
                widget = None
                if args and hasattr(args[0], '__class__'):
                    # First arg might be self, second might be widget
                    if len(args) > 1:
                        widget = args[1]
                    elif len(args) > 0 and hasattr(args[0], 'widget'):
                        widget = args[0].widget
                
                log_widget_access_failure(
                    widget=widget,
                    context=context,
                    exception=e,
                    fallback_used=True,
                    fallback_description="Operation skipped to maintain application stability"
                )
                
                # Also report to error handling service if available
                try:
                    from services.widget_error_handling_service import widget_error_service, ErrorSeverity
                    widget_error_service.report_widget_error(
                        widget=widget,
                        context=context,
                        exception=e,
                        severity=ErrorSeverity.CRITICAL if critical else ErrorSeverity.WARNING,
                        fallback_used=True,
                        fallback_description="Operation skipped to maintain application stability",
                        user_impact="UI enhancement unavailable but core functionality preserved"
                    )
                except ImportError:
                    pass  # Error service not available
                
                if critical:
                    # For critical operations, re-raise the exception
                    raise
                else:
                    # For non-critical operations, return None and continue
                    print(f"Non-critical operation '{operation_name}' failed but application continues")
                    return None
        
        return wrapper
    return decorator