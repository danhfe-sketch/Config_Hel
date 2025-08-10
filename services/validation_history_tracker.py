"""
Validation History Tracker

Tracks validation attempts and errors to help users learn from past mistakes
and improve their input patterns over time.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter


@dataclass
class ValidationHistoryEntry:
    """Single validation history entry"""
    timestamp: str
    field_name: str
    input_value: str
    is_valid: bool
    error_code: str
    error_message: str
    suggestions: List[str]
    user_action: str  # "corrected", "ignored", "accepted_suggestion", "manual_fix"
    final_value: str = ""
    session_id: str = ""


@dataclass
class ValidationPattern:
    """Pattern of validation errors for learning"""
    error_type: str
    frequency: int
    common_inputs: List[str]
    successful_corrections: List[str]
    last_occurrence: str
    improvement_trend: float  # Positive = improving, negative = getting worse


class ValidationHistoryTracker:
    """Tracks and analyzes validation history for user learning"""
    
    HISTORY_FILE = "validation_history.json"
    MAX_HISTORY_ENTRIES = 1000
    MAX_ANALYSIS_DAYS = 30
    
    def __init__(self):
        self.history: List[ValidationHistoryEntry] = []
        self.session_id = self._generate_session_id()
        self._load_history()
    
    def record_validation_attempt(self, field_name: str, input_value: str, 
                                validation_result, user_action: str = "pending",
                                final_value: str = "") -> None:
        """
        Record a validation attempt
        
        Args:
            field_name: Name of the field being validated
            input_value: User's input value
            validation_result: ValidationResult object
            user_action: What the user did after validation
            final_value: Final value user settled on
        """
        try:
            entry = ValidationHistoryEntry(
                timestamp=datetime.now().isoformat(),
                field_name=field_name,
                input_value=input_value,
                is_valid=validation_result.is_valid if validation_result else True,
                error_code=validation_result.error_code if validation_result else "",
                error_message=validation_result.error_message if validation_result else "",
                suggestions=validation_result.suggestions if validation_result else [],
                user_action=user_action,
                final_value=final_value,
                session_id=self.session_id
            )
            
            self.history.append(entry)
            
            # Limit history size
            if len(self.history) > self.MAX_HISTORY_ENTRIES:
                self.history = self.history[-self.MAX_HISTORY_ENTRIES:]
            
            # Save periodically
            if len(self.history) % 10 == 0:
                self._save_history()
                
        except Exception as e:
            print(f"Error recording validation attempt: {e}")
    
    def update_user_action(self, input_value: str, field_name: str, 
                          user_action: str, final_value: str = "") -> None:
        """
        Update the user action for a recent validation entry
        
        Args:
            input_value: Original input value to find
            field_name: Field name to match
            user_action: Action the user took
            final_value: Final value user used
        """
        try:
            # Find the most recent matching entry
            for entry in reversed(self.history):
                if (entry.input_value == input_value and 
                    entry.field_name == field_name and 
                    entry.user_action == "pending"):
                    entry.user_action = user_action
                    entry.final_value = final_value
                    break
            
            self._save_history()
            
        except Exception as e:
            print(f"Error updating user action: {e}")
    
    def get_common_errors(self, field_name: str = None, days: int = 30) -> List[ValidationPattern]:
        """
        Get common validation error patterns
        
        Args:
            field_name: Optional field name to filter by
            days: Number of days to analyze
            
        Returns:
            List of ValidationPattern objects
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Filter recent entries
            recent_entries = [
                entry for entry in self.history
                if (datetime.fromisoformat(entry.timestamp) > cutoff_date and
                    (not field_name or entry.field_name == field_name) and
                    not entry.is_valid)
            ]
            
            if not recent_entries:
                return []
            
            # Group by error code
            error_groups = defaultdict(list)
            for entry in recent_entries:
                error_groups[entry.error_code].append(entry)
            
            patterns = []
            for error_code, entries in error_groups.items():
                if not entries:
                    continue
                
                # Analyze this error pattern
                common_inputs = [entry.input_value for entry in entries]
                input_counter = Counter(common_inputs)
                
                # Find successful corrections
                successful_corrections = []
                for entry in entries:
                    if entry.user_action in ["corrected", "accepted_suggestion"] and entry.final_value:
                        successful_corrections.append(entry.final_value)
                
                # Calculate improvement trend
                improvement_trend = self._calculate_improvement_trend(entries)
                
                pattern = ValidationPattern(
                    error_type=error_code,
                    frequency=len(entries),
                    common_inputs=list(input_counter.most_common(5)),
                    successful_corrections=list(set(successful_corrections)),
                    last_occurrence=max(entry.timestamp for entry in entries),
                    improvement_trend=improvement_trend
                )
                patterns.append(pattern)
            
            # Sort by frequency
            patterns.sort(key=lambda p: p.frequency, reverse=True)
            return patterns
            
        except Exception as e:
            print(f"Error getting common errors: {e}")
            return []
    
    def get_learning_suggestions(self, field_name: str) -> List[str]:
        """
        Get enhanced personalized learning suggestions based on history
        
        Args:
            field_name: Field name to get suggestions for
            
        Returns:
            List of learning suggestions with actionable advice
        """
        try:
            suggestions = []
            
            # Get common errors for this field
            patterns = self.get_common_errors(field_name, days=30)
            
            if not patterns:
                return [
                    "Keep practicing! Your validation history will help provide personalized tips.",
                    "Try using the carrier helper for pre-configured APN settings.",
                    "Hover over fields for format examples and tips."
                ]
            
            # Analyze patterns and provide enhanced suggestions
            for pattern in patterns[:3]:  # Top 3 error patterns
                if pattern.error_type == "CONSECUTIVE_DOTS":
                    suggestions.append("💡 Tip: Avoid typing multiple dots in a row (like '..') in domain names")
                    if pattern.frequency > 3:
                        suggestions.append("⚠️ You've made this error multiple times - slow down when typing domains")
                        
                elif pattern.error_type == "MALFORMED_DOMAIN":
                    suggestions.append("💡 Tip: Check for corrupted domain endings like '.t.t.t' - these are usually typos")
                    suggestions.append("🔧 Try copying APN settings from the carrier helper instead of typing manually")
                    
                elif pattern.error_type == "EMPTY_APN":
                    suggestions.append("💡 Tip: APN field cannot be empty - try common values like 'internet' or contact your carrier")
                    if pattern.frequency > 2:
                        suggestions.append("📋 Consider using the carrier helper to avoid leaving fields empty")
                        
                elif pattern.error_type == "INVALID_CREDENTIALS":
                    suggestions.append("💡 Tip: Username and password should both be provided or both left empty")
                    suggestions.append("ℹ️ Many carriers don't require credentials - try leaving both empty first")
                
                # Add successful correction examples with context
                if pattern.successful_corrections:
                    example = pattern.successful_corrections[0]
                    suggestions.append(f"✅ What worked before: '{example}' - try similar formats")
            
            # Add improvement encouragement and specific advice
            improving_patterns = [p for p in patterns if p.improvement_trend > 0]
            if improving_patterns:
                suggestions.append("🎉 Great progress! You're making fewer validation errors over time.")
            else:
                # Provide specific improvement advice
                total_errors = sum(p.frequency for p in patterns)
                if total_errors > 10:
                    suggestions.append("📚 Consider reviewing the format examples in tooltips before typing")
                    suggestions.append("🐌 Take your time - most errors are from typing too quickly")
            
            # Add field-specific advanced tips
            if field_name == 'apn':
                suggestions.append("🌐 Pro tip: Most APNs are either domain names (like provider.com) or simple words (like 'internet')")
            elif field_name in ['apn_user', 'apn_password']:
                suggestions.append("🔐 Pro tip: Many carriers work without username/password - try leaving them empty first")
            
            return suggestions[:6]  # Limit to 6 suggestions for better UX
            
        except Exception as e:
            print(f"Error getting learning suggestions: {e}")
            return [
                "Error generating suggestions. Please try again.",
                "Use the carrier helper for reliable APN configurations.",
                "Check tooltips for format examples and guidance."
            ]
    
    def get_success_rate(self, field_name: str = None, days: int = 7) -> Dict[str, float]:
        """
        Get validation success rate statistics
        
        Args:
            field_name: Optional field name to filter by
            days: Number of days to analyze
            
        Returns:
            Dictionary with success rate statistics
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Filter recent entries
            recent_entries = [
                entry for entry in self.history
                if (datetime.fromisoformat(entry.timestamp) > cutoff_date and
                    (not field_name or entry.field_name == field_name))
            ]
            
            if not recent_entries:
                return {
                    'total_attempts': 0,
                    'successful_attempts': 0,
                    'success_rate': 0.0,
                    'improvement_trend': 0.0
                }
            
            total_attempts = len(recent_entries)
            successful_attempts = sum(1 for entry in recent_entries if entry.is_valid)
            success_rate = (successful_attempts / total_attempts) * 100
            
            # Calculate improvement trend
            improvement_trend = self._calculate_success_trend(recent_entries)
            
            return {
                'total_attempts': total_attempts,
                'successful_attempts': successful_attempts,
                'success_rate': round(success_rate, 1),
                'improvement_trend': round(improvement_trend, 1)
            }
            
        except Exception as e:
            print(f"Error calculating success rate: {e}")
            return {'error': str(e)}
    
    def get_field_statistics(self) -> Dict[str, Dict]:
        """
        Get statistics for all fields
        
        Returns:
            Dictionary with statistics per field
        """
        try:
            field_stats = {}
            
            # Group entries by field
            field_groups = defaultdict(list)
            for entry in self.history:
                field_groups[entry.field_name].append(entry)
            
            for field_name, entries in field_groups.items():
                total = len(entries)
                valid = sum(1 for entry in entries if entry.is_valid)
                
                # Most common errors
                error_counter = Counter(
                    entry.error_code for entry in entries 
                    if not entry.is_valid and entry.error_code
                )
                
                field_stats[field_name] = {
                    'total_attempts': total,
                    'success_rate': round((valid / total) * 100, 1) if total > 0 else 0,
                    'most_common_errors': list(error_counter.most_common(3)),
                    'last_attempt': max(entry.timestamp for entry in entries) if entries else None
                }
            
            return field_stats
            
        except Exception as e:
            print(f"Error getting field statistics: {e}")
            return {}
    
    def export_history(self, file_path: str = None) -> str:
        """
        Export validation history to file
        
        Args:
            file_path: Optional file path to save to
            
        Returns:
            Export status message
        """
        try:
            if not file_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = f"validation_history_export_{timestamp}.json"
            
            export_data = {
                'export_date': datetime.now().isoformat(),
                'total_entries': len(self.history),
                'history': [asdict(entry) for entry in self.history]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return f"History exported successfully to {file_path}"
            
        except Exception as e:
            return f"Error exporting history: {e}"
    
    def clear_old_history(self, days: int = 90) -> int:
        """
        Clear history entries older than specified days
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of entries removed
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            original_count = len(self.history)
            
            self.history = [
                entry for entry in self.history
                if datetime.fromisoformat(entry.timestamp) > cutoff_date
            ]
            
            removed_count = original_count - len(self.history)
            
            if removed_count > 0:
                self._save_history()
            
            return removed_count
            
        except Exception as e:
            print(f"Error clearing old history: {e}")
            return 0
    
    def _calculate_improvement_trend(self, entries: List[ValidationHistoryEntry]) -> float:
        """Calculate improvement trend for error pattern"""
        if len(entries) < 2:
            return 0.0
        
        try:
            # Sort by timestamp
            sorted_entries = sorted(entries, key=lambda e: e.timestamp)
            
            # Split into first and second half
            mid_point = len(sorted_entries) // 2
            first_half = sorted_entries[:mid_point]
            second_half = sorted_entries[mid_point:]
            
            if not first_half or not second_half:
                return 0.0
            
            # Calculate error rate for each half
            first_half_errors = len(first_half)
            second_half_errors = len(second_half)
            
            # Positive trend means fewer errors in second half (improvement)
            if first_half_errors == 0:
                return -1.0 if second_half_errors > 0 else 0.0
            
            trend = (first_half_errors - second_half_errors) / first_half_errors
            return trend
            
        except Exception:
            return 0.0
    
    def _calculate_success_trend(self, entries: List[ValidationHistoryEntry]) -> float:
        """Calculate success rate trend"""
        if len(entries) < 4:
            return 0.0
        
        try:
            # Sort by timestamp
            sorted_entries = sorted(entries, key=lambda e: e.timestamp)
            
            # Split into first and second half
            mid_point = len(sorted_entries) // 2
            first_half = sorted_entries[:mid_point]
            second_half = sorted_entries[mid_point:]
            
            # Calculate success rates
            first_success_rate = sum(1 for e in first_half if e.is_valid) / len(first_half)
            second_success_rate = sum(1 for e in second_half if e.is_valid) / len(second_half)
            
            # Return improvement (positive = better)
            return (second_success_rate - first_success_rate) * 100
            
        except Exception:
            return 0.0
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        import hashlib
        timestamp = datetime.now().isoformat()
        return hashlib.md5(timestamp.encode()).hexdigest()[:8]
    
    def _load_history(self) -> None:
        """Load history from file"""
        try:
            history_path = self._get_history_file_path()
            if os.path.exists(history_path):
                with open(history_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.history = []
                for entry_data in data.get('history', []):
                    try:
                        entry = ValidationHistoryEntry(**entry_data)
                        self.history.append(entry)
                    except Exception as e:
                        print(f"Error loading history entry: {e}")
                        continue
                
                print(f"Loaded {len(self.history)} validation history entries")
            else:
                self.history = []
                
        except Exception as e:
            print(f"Error loading validation history: {e}")
            self.history = []
    
    def _save_history(self) -> None:
        """Save history to file"""
        try:
            history_path = self._get_history_file_path()
            history_dir = os.path.dirname(history_path)
            
            # Ensure directory exists
            if history_dir and not os.path.exists(history_dir):
                os.makedirs(history_dir, exist_ok=True)
            
            # Prepare data for saving
            save_data = {
                'version': '1.0',
                'last_updated': datetime.now().isoformat(),
                'total_entries': len(self.history),
                'history': [asdict(entry) for entry in self.history]
            }
            
            # Save to file
            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            print(f"Error saving validation history: {e}")
    
    def _get_history_file_path(self) -> str:
        """Get the path to the history file"""
        try:
            # Use same pattern as other config files
            user_home = os.path.expanduser("~")
            app_config_dir = os.path.join(user_home, ".lt32pro_config")
            
            # Test if we can write to this directory
            if not os.path.exists(app_config_dir):
                try:
                    os.makedirs(app_config_dir, exist_ok=True)
                    return os.path.join(app_config_dir, self.HISTORY_FILE)
                except (PermissionError, OSError):
                    pass
            else:
                return os.path.join(app_config_dir, self.HISTORY_FILE)
            
            # Fall back to application directory
            base_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
            return os.path.join(base_dir, self.HISTORY_FILE)
            
        except Exception as e:
            print(f"Error determining history path: {e}")
            return self.HISTORY_FILE