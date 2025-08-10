"""
Unit tests for validation result data models.
"""

import unittest
from models.validation_result import ValidationResult


class TestValidationResult(unittest.TestCase):
    """Test cases for ValidationResult class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.valid_result = ValidationResult(is_valid=True)
        self.invalid_result = ValidationResult(
            is_valid=False,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"]
        )
    
    def test_creation_valid(self):
        """Test creation of valid result."""
        self.assertTrue(self.valid_result.is_valid)
        self.assertEqual(len(self.valid_result.errors), 0)
        self.assertEqual(len(self.valid_result.warnings), 0)
        self.assertEqual(len(self.valid_result.details), 0)
    
    def test_creation_invalid(self):
        """Test creation of invalid result."""
        self.assertFalse(self.invalid_result.is_valid)
        self.assertEqual(len(self.invalid_result.errors), 2)
        self.assertEqual(len(self.invalid_result.warnings), 1)
        self.assertIn("Error 1", self.invalid_result.errors)
        self.assertIn("Warning 1", self.invalid_result.warnings)
    
    def test_add_error(self):
        """Test adding errors."""
        result = ValidationResult(is_valid=True)
        self.assertTrue(result.is_valid)
        
        result.add_error("New error")
        self.assertFalse(result.is_valid)
        self.assertIn("New error", result.errors)
    
    def test_add_warning(self):
        """Test adding warnings."""
        result = ValidationResult(is_valid=True)
        
        result.add_warning("New warning")
        self.assertTrue(result.is_valid)  # Warnings don't affect validity
        self.assertIn("New warning", result.warnings)
    
    def test_add_detail(self):
        """Test adding details."""
        result = ValidationResult(is_valid=True)
        
        result.add_detail("key1", "value1")
        result.add_detail("key2", 42)
        
        self.assertEqual(result.details["key1"], "value1")
        self.assertEqual(result.details["key2"], 42)
    
    def test_merge_valid_results(self):
        """Test merging two valid results."""
        result1 = ValidationResult(is_valid=True, warnings=["Warning 1"])
        result2 = ValidationResult(is_valid=True, warnings=["Warning 2"])
        
        merged = result1.merge(result2)
        
        self.assertTrue(merged.is_valid)
        self.assertEqual(len(merged.warnings), 2)
        self.assertIn("Warning 1", merged.warnings)
        self.assertIn("Warning 2", merged.warnings)
    
    def test_merge_invalid_results(self):
        """Test merging results where one is invalid."""
        result1 = ValidationResult(is_valid=True)
        result2 = ValidationResult(is_valid=False, errors=["Error 1"])
        
        merged = result1.merge(result2)
        
        self.assertFalse(merged.is_valid)
        self.assertIn("Error 1", merged.errors)
    
    def test_merge_details(self):
        """Test merging details from two results."""
        result1 = ValidationResult(is_valid=True, details={"key1": "value1"})
        result2 = ValidationResult(is_valid=True, details={"key2": "value2"})
        
        merged = result1.merge(result2)
        
        self.assertEqual(merged.details["key1"], "value1")
        self.assertEqual(merged.details["key2"], "value2")
    
    def test_merge_overlapping_details(self):
        """Test merging with overlapping detail keys."""
        result1 = ValidationResult(is_valid=True, details={"key": "value1"})
        result2 = ValidationResult(is_valid=True, details={"key": "value2"})
        
        merged = result1.merge(result2)
        
        # Second result should override
        self.assertEqual(merged.details["key"], "value2")
    
    def test_has_errors(self):
        """Test has_errors method."""
        self.assertFalse(self.valid_result.has_errors())
        self.assertTrue(self.invalid_result.has_errors())
    
    def test_has_warnings(self):
        """Test has_warnings method."""
        self.assertFalse(self.valid_result.has_warnings())
        self.assertTrue(self.invalid_result.has_warnings())
    
    def test_get_summary_valid_no_warnings(self):
        """Test summary for valid result with no warnings."""
        summary = self.valid_result.get_summary()
        self.assertEqual(summary, "Validation passed")
    
    def test_get_summary_valid_with_warnings(self):
        """Test summary for valid result with warnings."""
        result = ValidationResult(is_valid=True, warnings=["Warning 1", "Warning 2"])
        summary = result.get_summary()
        self.assertEqual(summary, "Validation passed with 2 warning(s)")
    
    def test_get_summary_invalid(self):
        """Test summary for invalid result."""
        summary = self.invalid_result.get_summary()
        self.assertEqual(summary, "Validation failed with 2 error(s)")
    
    def test_str_representation_valid(self):
        """Test string representation of valid result."""
        result_str = str(self.valid_result)
        self.assertIn("Validation passed", result_str)
    
    def test_str_representation_invalid(self):
        """Test string representation of invalid result."""
        result_str = str(self.invalid_result)
        self.assertIn("Validation failed", result_str)
        self.assertIn("Error 1", result_str)
        self.assertIn("Error 2", result_str)
        self.assertIn("Warning 1", result_str)
    
    def test_str_representation_with_warnings_only(self):
        """Test string representation with warnings only."""
        result = ValidationResult(is_valid=True, warnings=["Warning 1"])
        result_str = str(result)
        self.assertIn("Validation passed with 1 warning(s)", result_str)
        self.assertIn("Warning 1", result_str)
    
    def test_default_factory_fields(self):
        """Test that default factory fields work correctly."""
        result1 = ValidationResult(is_valid=True)
        result2 = ValidationResult(is_valid=True)
        
        result1.add_error("Error 1")
        
        # result2 should not be affected by changes to result1
        self.assertEqual(len(result2.errors), 0)
        self.assertEqual(len(result1.errors), 1)


if __name__ == '__main__':
    unittest.main()