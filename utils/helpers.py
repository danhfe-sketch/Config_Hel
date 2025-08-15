# -*- coding: utf-8 -*-

import sys
import os
import logging

# Set up logging for helpers
logger = logging.getLogger(__name__)

def resource_path(relative_path):
    """ 
    Get absolute path to an asset, which works for development and for PyInstaller.
    Enhanced with better error handling and debugging information.
    
    Args:
        relative_path: Relative path to the resource
        
    Returns:
        Absolute path to the resource
        
    Raises:
        ValueError: If relative_path is None or empty
        OSError: If there are issues with path resolution
    """
    if not relative_path:
        raise ValueError("relative_path cannot be None or empty")
    
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
            logger.debug(f"Using PyInstaller base path: {base_path}")
        else:
            base_path = os.path.abspath(".")
            logger.debug(f"Using development base path: {base_path}")
        
        # Join the paths
        full_path = os.path.join(base_path, relative_path)
        
        # Normalize the path (resolve .. and . components)
        normalized_path = os.path.normpath(full_path)
        
        logger.debug(f"Resource path resolution: {relative_path} -> {normalized_path}")
        
        return normalized_path
        
    except Exception as e:
        logger.error(f"Error resolving resource path for '{relative_path}': {e}")
        raise OSError(f"Failed to resolve resource path: {relative_path}") from e

def validate_resource_exists(relative_path):
    """
    Validate that a resource exists and return its absolute path.
    
    Args:
        relative_path: Relative path to validate
        
    Returns:
        Absolute path if resource exists, None otherwise
    """
    try:
        full_path = resource_path(relative_path)
        
        if os.path.exists(full_path):
            logger.debug(f"Resource exists: {full_path}")
            return full_path
        else:
            logger.debug(f"Resource does not exist: {full_path}")
            return None
            
    except Exception as e:
        logger.warning(f"Error validating resource '{relative_path}': {e}")
        return None

def get_resource_info(relative_path):
    """
    Get detailed information about a resource.
    
    Args:
        relative_path: Relative path to analyze
        
    Returns:
        Dictionary with resource information
    """
    info = {
        'relative_path': relative_path,
        'absolute_path': None,
        'exists': False,
        'is_file': False,
        'is_directory': False,
        'size': None,
        'error': None
    }
    
    try:
        full_path = resource_path(relative_path)
        info['absolute_path'] = full_path
        
        if os.path.exists(full_path):
            info['exists'] = True
            info['is_file'] = os.path.isfile(full_path)
            info['is_directory'] = os.path.isdir(full_path)
            
            if info['is_file']:
                try:
                    info['size'] = os.path.getsize(full_path)
                except OSError as e:
                    info['error'] = f"Could not get file size: {e}"
                    
    except Exception as e:
        info['error'] = str(e)
        logger.error(f"Error getting resource info for '{relative_path}': {e}")
    
    return info