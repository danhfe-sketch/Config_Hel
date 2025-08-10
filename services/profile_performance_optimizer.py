"""
Profile Performance Optimizer

This module provides performance optimization utilities for LT32Pro profile operations
including batch processing, memory management, and operation caching.
"""

import time
import threading
import gc
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger(__name__)


@dataclass
class OptimizationConfig:
    """Configuration for performance optimization."""
    enable_batch_processing: bool = True
    batch_size: int = 10
    enable_caching: bool = True
    cache_size: int = 100
    enable_parallel_processing: bool = True
    max_workers: int = 3
    enable_memory_optimization: bool = True
    gc_threshold: int = 50  # Number of operations before forcing garbage collection


class ProfilePerformanceOptimizer:
    """
    Performance optimizer for LT32Pro profile operations.
    
    Provides optimization strategies including:
    - Batch processing for large parameter sets
    - Memory management and garbage collection
    - Operation result caching
    - Parallel processing for independent operations
    """
    
    def __init__(self, config: OptimizationConfig = None):
        """Initialize the performance optimizer."""
        self.config = config or OptimizationConfig()
        self.operation_cache: Dict[str, Any] = {}
        self.operation_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self._lock = threading.Lock()
        
        logger.info(f"ProfilePerformanceOptimizer initialized with config: {self.config}")
    
    def optimize_parameter_processing(self, parameters: Dict[str, str], 
                                    processor_func: Callable[[Dict[str, str]], Any]) -> Any:
        """
        Optimize parameter processing using batch processing and caching.
        
        Args:
            parameters: Dictionary of parameters to process
            processor_func: Function to process parameters
            
        Returns:
            Processing result
        """
        if not self.config.enable_batch_processing or len(parameters) <= self.config.batch_size:
            return self._process_with_caching(parameters, processor_func)
        
        # Process in batches
        logger.info(f"Processing {len(parameters)} parameters in batches of {self.config.batch_size}")
        
        parameter_items = list(parameters.items())
        batches = [
            dict(parameter_items[i:i + self.config.batch_size])
            for i in range(0, len(parameter_items), self.config.batch_size)
        ]
        
        batch_results = []
        
        if self.config.enable_parallel_processing and len(batches) > 1:
            # Process batches in parallel
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                future_to_batch = {
                    executor.submit(self._process_with_caching, batch, processor_func): batch
                    for batch in batches
                }
                
                for future in as_completed(future_to_batch):
                    try:
                        result = future.result()
                        batch_results.append(result)
                    except Exception as e:
                        logger.error(f"Batch processing failed: {e}")
                        batch_results.append(None)
        else:
            # Process batches sequentially
            for batch in batches:
                try:
                    result = self._process_with_caching(batch, processor_func)
                    batch_results.append(result)
                except Exception as e:
                    logger.error(f"Batch processing failed: {e}")
                    batch_results.append(None)
        
        # Combine batch results
        return self._combine_batch_results(batch_results)
    
    def _process_with_caching(self, parameters: Dict[str, str], 
                            processor_func: Callable[[Dict[str, str]], Any]) -> Any:
        """Process parameters with caching support."""
        if not self.config.enable_caching:
            return processor_func(parameters)
        
        # Generate cache key
        cache_key = self._generate_cache_key(parameters)
        
        with self._lock:
            # Check cache
            if cache_key in self.operation_cache:
                self.cache_hits += 1
                logger.debug(f"Cache hit for key: {cache_key[:20]}...")
                return self.operation_cache[cache_key]
            
            self.cache_misses += 1
        
        # Process parameters
        result = processor_func(parameters)
        
        with self._lock:
            # Store in cache
            if len(self.operation_cache) >= self.config.cache_size:
                # Remove oldest entry (simple FIFO)
                oldest_key = next(iter(self.operation_cache))
                del self.operation_cache[oldest_key]
            
            self.operation_cache[cache_key] = result
        
        logger.debug(f"Cache miss for key: {cache_key[:20]}...")
        return result
    
    def _generate_cache_key(self, parameters: Dict[str, str]) -> str:
        """Generate a cache key for parameters."""
        # Sort parameters for consistent key generation
        sorted_params = sorted(parameters.items())
        return str(hash(tuple(sorted_params)))
    
    def _combine_batch_results(self, batch_results: List[Any]) -> Any:
        """Combine results from batch processing."""
        # This is a generic implementation - specific processors may need custom logic
        if not batch_results:
            return None
        
        # Filter out None results
        valid_results = [r for r in batch_results if r is not None]
        
        if not valid_results:
            return None
        
        # If results are dictionaries, merge them
        if all(isinstance(r, dict) for r in valid_results):
            combined = {}
            for result in valid_results:
                combined.update(result)
            return combined
        
        # If results are lists, concatenate them
        if all(isinstance(r, list) for r in valid_results):
            combined = []
            for result in valid_results:
                combined.extend(result)
            return combined
        
        # For other types, return the first valid result
        return valid_results[0]
    
    def optimize_memory_usage(self):
        """Optimize memory usage by forcing garbage collection."""
        if not self.config.enable_memory_optimization:
            return
        
        self.operation_count += 1
        
        if self.operation_count >= self.config.gc_threshold:
            logger.debug("Forcing garbage collection for memory optimization")
            gc.collect()
            self.operation_count = 0
    
    def optimize_device_communication(self, commands: List[str], 
                                    communication_func: Callable[[str], str]) -> Dict[str, str]:
        """
        Optimize device communication by batching commands and parallel execution.
        
        Args:
            commands: List of commands to send to device
            communication_func: Function to send individual commands
            
        Returns:
            Dictionary of command -> response mappings
        """
        if not commands:
            return {}
        
        logger.info(f"Optimizing communication for {len(commands)} commands")
        
        if not self.config.enable_parallel_processing or len(commands) <= 2:
            # Sequential processing for small command sets
            results = {}
            for command in commands:
                try:
                    response = communication_func(command)
                    results[command] = response
                except Exception as e:
                    logger.error(f"Command {command} failed: {e}")
                    results[command] = f"ERROR: {str(e)}"
            return results
        
        # Parallel processing for larger command sets
        results = {}
        
        with ThreadPoolExecutor(max_workers=min(self.config.max_workers, len(commands))) as executor:
            future_to_command = {
                executor.submit(communication_func, command): command
                for command in commands
            }
            
            for future in as_completed(future_to_command):
                command = future_to_command[future]
                try:
                    response = future.result()
                    results[command] = response
                except Exception as e:
                    logger.error(f"Command {command} failed: {e}")
                    results[command] = f"ERROR: {str(e)}"
        
        return results
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization statistics."""
        with self._lock:
            total_cache_requests = self.cache_hits + self.cache_misses
            cache_hit_rate = (self.cache_hits / total_cache_requests * 100) if total_cache_requests > 0 else 0
            
            return {
                'cache_hits': self.cache_hits,
                'cache_misses': self.cache_misses,
                'cache_hit_rate': cache_hit_rate,
                'cache_size': len(self.operation_cache),
                'operation_count': self.operation_count,
                'config': {
                    'batch_processing': self.config.enable_batch_processing,
                    'batch_size': self.config.batch_size,
                    'caching': self.config.enable_caching,
                    'parallel_processing': self.config.enable_parallel_processing,
                    'max_workers': self.config.max_workers
                }
            }
    
    def clear_cache(self):
        """Clear the operation cache."""
        with self._lock:
            self.operation_cache.clear()
            logger.info("Operation cache cleared")
    
    def reset_stats(self):
        """Reset optimization statistics."""
        with self._lock:
            self.cache_hits = 0
            self.cache_misses = 0
            self.operation_count = 0
            logger.info("Optimization statistics reset")


class MemoryOptimizer:
    """Memory optimization utilities for profile operations."""
    
    @staticmethod
    def optimize_parameter_dict(parameters: Dict[str, str]) -> Dict[str, str]:
        """Optimize parameter dictionary for memory usage."""
        if not parameters:
            return parameters
        
        # Remove empty values
        optimized = {k: v for k, v in parameters.items() if v and v.strip()}
        
        # Intern string values for memory efficiency
        optimized = {k: str(v).strip() for k, v in optimized.items()}
        
        return optimized
    
    @staticmethod
    def estimate_memory_usage(data: Any) -> int:
        """Estimate memory usage of data in bytes."""
        import sys
        
        if isinstance(data, dict):
            return sum(sys.getsizeof(k) + sys.getsizeof(v) for k, v in data.items())
        elif isinstance(data, (list, tuple)):
            return sum(sys.getsizeof(item) for item in data)
        else:
            return sys.getsizeof(data)
    
    @staticmethod
    def optimize_for_large_datasets(data: Any, chunk_size: int = 1000) -> List[Any]:
        """Optimize large datasets by chunking."""
        if isinstance(data, dict):
            items = list(data.items())
            return [dict(items[i:i + chunk_size]) for i in range(0, len(items), chunk_size)]
        elif isinstance(data, list):
            return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
        else:
            return [data]


class ConcurrencyOptimizer:
    """Concurrency optimization utilities for profile operations."""
    
    def __init__(self, max_workers: int = 3):
        """Initialize concurrency optimizer."""
        self.max_workers = max_workers
        self.active_operations = 0
        self._lock = threading.Lock()
    
    def execute_concurrent_operations(self, operations: List[Callable], 
                                    timeout: float = 30.0) -> List[Tuple[bool, Any]]:
        """
        Execute multiple operations concurrently.
        
        Args:
            operations: List of callable operations
            timeout: Timeout for each operation
            
        Returns:
            List of (success, result) tuples
        """
        if not operations:
            return []
        
        results = []
        
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(operations))) as executor:
            future_to_index = {
                executor.submit(self._execute_with_timeout, op, timeout): i
                for i, op in enumerate(operations)
            }
            
            # Initialize results list with None values
            results = [None] * len(operations)
            
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    success, result = future.result()
                    results[index] = (success, result)
                except Exception as e:
                    results[index] = (False, str(e))
        
        return results
    
    def _execute_with_timeout(self, operation: Callable, timeout: float) -> Tuple[bool, Any]:
        """Execute operation with timeout."""
        try:
            with self._lock:
                self.active_operations += 1
            
            start_time = time.time()
            result = operation()
            duration = time.time() - start_time
            
            if duration > timeout:
                return False, f"Operation timed out after {duration:.2f}s"
            
            return True, result
            
        except Exception as e:
            return False, str(e)
        finally:
            with self._lock:
                self.active_operations -= 1
    
    def get_active_operations(self) -> int:
        """Get number of active operations."""
        with self._lock:
            return self.active_operations