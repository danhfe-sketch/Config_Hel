"""
Profile Log Analyzer

This service provides tools for analyzing profile operation logs to identify
common issues, performance patterns, and troubleshooting insights.
"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from collections import defaultdict, Counter
from dataclasses import dataclass
import logging


@dataclass
class LogAnalysisResult:
    """Result of log analysis."""
    analysis_timestamp: datetime
    time_period: str
    total_entries: int
    error_count: int
    warning_count: int
    common_issues: List[Dict[str, Any]]
    performance_insights: Dict[str, Any]
    recommendations: List[str]


@dataclass
class CommonIssue:
    """Represents a common issue found in logs."""
    issue_type: str
    description: str
    frequency: int
    first_occurrence: datetime
    last_occurrence: datetime
    affected_operations: List[str]
    suggested_solution: str
    severity: str  # 'low', 'medium', 'high', 'critical'


class ProfileLogAnalyzer:
    """
    Analyzes profile operation logs to identify patterns, issues, and performance insights.
    """
    
    def __init__(self, log_directory: str = "logs"):
        """
        Initialize the log analyzer.
        
        Args:
            log_directory: Directory containing log files
        """
        self.log_directory = Path(log_directory)
        self.logger = logging.getLogger(__name__)
        
        # Define common error patterns
        self._error_patterns = {
            'file_not_found': {
                'pattern': r'FileNotFoundError|No such file or directory',
                'description': 'Profile file not found',
                'severity': 'high',
                'solution': 'Verify file path exists and is accessible'
            },
            'permission_denied': {
                'pattern': r'PermissionError|Permission denied',
                'description': 'File permission issues',
                'severity': 'high',
                'solution': 'Check file permissions and user access rights'
            },
            'invalid_format': {
                'pattern': r'Invalid profile format|Malformed profile|ConfigParser.*Error',
                'description': 'Invalid profile file format',
                'severity': 'medium',
                'solution': 'Validate profile file structure and content'
            },
            'validation_failure': {
                'pattern': r'VALIDATION_FAILURE|Validation failed',
                'description': 'Profile validation errors',
                'severity': 'medium',
                'solution': 'Review parameter values and ranges'
            },
            'memory_error': {
                'pattern': r'MemoryError|Out of memory',
                'description': 'Memory allocation issues',
                'severity': 'critical',
                'solution': 'Check available system memory and file sizes'
            },
            'timeout_error': {
                'pattern': r'TimeoutError|Operation timed out',
                'description': 'Operation timeout',
                'severity': 'medium',
                'solution': 'Check system performance and network connectivity'
            },
            'encoding_error': {
                'pattern': r'UnicodeDecodeError|Encoding error',
                'description': 'File encoding issues',
                'severity': 'medium',
                'solution': 'Ensure profile files use UTF-8 encoding'
            },
            'device_communication': {
                'pattern': r'Device not responding|Communication error|Serial.*Error',
                'description': 'Device communication problems',
                'severity': 'high',
                'solution': 'Check device connection and communication settings'
            }
        }
        
        # Performance thresholds
        self._performance_thresholds = {
            'slow_operation_ms': 5000,  # 5 seconds
            'very_slow_operation_ms': 10000,  # 10 seconds
            'high_memory_usage_mb': 100,  # 100 MB
            'high_cpu_usage_percent': 80  # 80%
        }
    
    def analyze_logs(self, hours: int = 24) -> LogAnalysisResult:
        """
        Perform comprehensive log analysis.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Analysis results
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Analyze different log files
        operation_logs = self._analyze_operation_logs(cutoff_time)
        performance_logs = self._analyze_performance_logs(cutoff_time)
        error_logs = self._analyze_error_logs(cutoff_time)
        
        # Identify common issues
        common_issues = self._identify_common_issues(operation_logs, error_logs)
        
        # Generate performance insights
        performance_insights = self._generate_performance_insights(performance_logs)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(common_issues, performance_insights)
        
        return LogAnalysisResult(
            analysis_timestamp=datetime.now(),
            time_period=f"{hours} hours",
            total_entries=len(operation_logs) + len(performance_logs) + len(error_logs),
            error_count=len(error_logs),
            warning_count=len([log for log in operation_logs if 'WARNING' in log.get('level', '')]),
            common_issues=[self._issue_to_dict(issue) for issue in common_issues],
            performance_insights=performance_insights,
            recommendations=recommendations
        )
    
    def _analyze_operation_logs(self, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Analyze profile operation logs."""
        log_file = self.log_directory / 'profile_operations.log'
        if not log_file.exists():
            return []
        
        logs = []
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        # Parse log line
                        parts = line.strip().split(' - ', 3)
                        if len(parts) >= 4:
                            timestamp_str = parts[0]
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                            
                            if timestamp >= cutoff_time:
                                logs.append({
                                    'timestamp': timestamp,
                                    'logger': parts[1],
                                    'level': parts[2],
                                    'message': parts[3]
                                })
                    except Exception:
                        continue  # Skip malformed lines
        except Exception as e:
            self.logger.warning(f"Failed to read operation logs: {e}")
        
        return logs
    
    def _analyze_performance_logs(self, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Analyze performance logs."""
        log_file = self.log_directory / 'profile_performance.log'
        if not log_file.exists():
            return []
        
        logs = []
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        timestamp = datetime.fromisoformat(data['timestamp'])
                        
                        if timestamp >= cutoff_time:
                            logs.append(data)
                    except Exception:
                        continue  # Skip malformed lines
        except Exception as e:
            self.logger.warning(f"Failed to read performance logs: {e}")
        
        return logs
    
    def _analyze_error_logs(self, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Analyze error logs."""
        log_file = self.log_directory / 'profile_errors.log'
        if not log_file.exists():
            return []
        
        logs = []
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        # Parse log line
                        parts = line.strip().split(' - ', 3)
                        if len(parts) >= 4:
                            timestamp_str = parts[0]
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                            
                            if timestamp >= cutoff_time:
                                logs.append({
                                    'timestamp': timestamp,
                                    'logger': parts[1],
                                    'level': parts[2],
                                    'message': parts[3]
                                })
                    except Exception:
                        continue  # Skip malformed lines
        except Exception as e:
            self.logger.warning(f"Failed to read error logs: {e}")
        
        return logs
    
    def _identify_common_issues(self, operation_logs: List[Dict[str, Any]], 
                              error_logs: List[Dict[str, Any]]) -> List[CommonIssue]:
        """Identify common issues from logs."""
        issues = []
        all_logs = operation_logs + error_logs
        
        for issue_type, pattern_info in self._error_patterns.items():
            pattern = re.compile(pattern_info['pattern'], re.IGNORECASE)
            matching_logs = []
            affected_operations = set()
            
            for log in all_logs:
                message = log.get('message', '')
                if pattern.search(message):
                    matching_logs.append(log)
                    
                    # Extract operation ID if present
                    op_match = re.search(r'OPERATION_\w+: (\w+_\d+)', message)
                    if op_match:
                        affected_operations.add(op_match.group(1))
            
            if matching_logs:
                issues.append(CommonIssue(
                    issue_type=issue_type,
                    description=pattern_info['description'],
                    frequency=len(matching_logs),
                    first_occurrence=min(log['timestamp'] for log in matching_logs),
                    last_occurrence=max(log['timestamp'] for log in matching_logs),
                    affected_operations=list(affected_operations),
                    suggested_solution=pattern_info['solution'],
                    severity=pattern_info['severity']
                ))
        
        # Sort by frequency (most common first)
        issues.sort(key=lambda x: x.frequency, reverse=True)
        return issues
    
    def _generate_performance_insights(self, performance_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate performance insights from logs."""
        if not performance_logs:
            return {'message': 'No performance data available'}
        
        # Calculate statistics
        durations = [log.get('duration_ms', 0) for log in performance_logs if log.get('duration_ms')]
        memory_usage = [log.get('memory_usage_mb', 0) for log in performance_logs if log.get('memory_usage_mb') is not None]
        cpu_usage = [log.get('cpu_usage_percent', 0) for log in performance_logs if log.get('cpu_usage_percent') is not None]
        
        # Operation type analysis
        operation_stats = defaultdict(list)
        for log in performance_logs:
            op_type = log.get('operation_type', 'unknown')
            if log.get('duration_ms'):
                operation_stats[op_type].append(log['duration_ms'])
        
        # Identify slow operations
        slow_operations = [
            log for log in performance_logs
            if log.get('duration_ms', 0) > self._performance_thresholds['slow_operation_ms']
        ]
        
        # Identify high resource usage
        high_memory_ops = [
            log for log in performance_logs
            if (log.get('memory_usage_mb') or 0) > self._performance_thresholds['high_memory_usage_mb']
        ]
        
        high_cpu_ops = [
            log for log in performance_logs
            if (log.get('cpu_usage_percent') or 0) > self._performance_thresholds['high_cpu_usage_percent']
        ]
        
        insights = {
            'total_operations': len(performance_logs),
            'average_duration_ms': round(sum(durations) / len(durations), 2) if durations else 0,
            'median_duration_ms': round(sorted(durations)[len(durations)//2], 2) if durations else 0,
            'max_duration_ms': max(durations) if durations else 0,
            'min_duration_ms': min(durations) if durations else 0,
            'slow_operations_count': len(slow_operations),
            'slow_operations_percentage': round(len(slow_operations) / len(performance_logs) * 100, 2),
            'average_memory_usage_mb': round(sum(memory_usage) / len(memory_usage), 2) if memory_usage else 0,
            'max_memory_usage_mb': max(memory_usage) if memory_usage else 0,
            'high_memory_operations_count': len(high_memory_ops),
            'average_cpu_usage_percent': round(sum(cpu_usage) / len(cpu_usage), 2) if cpu_usage else 0,
            'max_cpu_usage_percent': max(cpu_usage) if cpu_usage else 0,
            'high_cpu_operations_count': len(high_cpu_ops),
            'operation_type_performance': {}
        }
        
        # Add per-operation-type statistics
        for op_type, durations in operation_stats.items():
            insights['operation_type_performance'][op_type] = {
                'count': len(durations),
                'average_duration_ms': round(sum(durations) / len(durations), 2),
                'max_duration_ms': max(durations),
                'min_duration_ms': min(durations)
            }
        
        return insights
    
    def _generate_recommendations(self, common_issues: List[CommonIssue], 
                                performance_insights: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        # Issue-based recommendations
        critical_issues = [issue for issue in common_issues if issue.severity == 'critical']
        if critical_issues:
            recommendations.append(
                f"CRITICAL: Address {len(critical_issues)} critical issues immediately, "
                f"including: {', '.join(issue.description for issue in critical_issues[:3])}"
            )
        
        high_issues = [issue for issue in common_issues if issue.severity == 'high']
        if high_issues:
            recommendations.append(
                f"HIGH PRIORITY: Resolve {len(high_issues)} high-priority issues, "
                f"most common: {high_issues[0].description} ({high_issues[0].frequency} occurrences)"
            )
        
        # Performance-based recommendations
        if performance_insights.get('slow_operations_percentage', 0) > 20:
            recommendations.append(
                f"PERFORMANCE: {performance_insights['slow_operations_percentage']:.1f}% of operations "
                f"are slow (>{self._performance_thresholds['slow_operation_ms']}ms). "
                f"Consider optimizing profile processing logic."
            )
        
        if performance_insights.get('high_memory_operations_count', 0) > 0:
            recommendations.append(
                f"MEMORY: {performance_insights['high_memory_operations_count']} operations used "
                f"high memory (>{self._performance_thresholds['high_memory_usage_mb']}MB). "
                f"Review memory usage patterns and consider optimization."
            )
        
        if performance_insights.get('high_cpu_operations_count', 0) > 0:
            recommendations.append(
                f"CPU: {performance_insights['high_cpu_operations_count']} operations used "
                f"high CPU (>{self._performance_thresholds['high_cpu_usage_percent']}%). "
                f"Consider background processing or optimization."
            )
        
        # General recommendations
        if not recommendations:
            recommendations.append("System appears to be operating normally. Continue monitoring.")
        
        return recommendations
    
    def _issue_to_dict(self, issue: CommonIssue) -> Dict[str, Any]:
        """Convert CommonIssue to dictionary."""
        return {
            'issue_type': issue.issue_type,
            'description': issue.description,
            'frequency': issue.frequency,
            'first_occurrence': issue.first_occurrence.isoformat(),
            'last_occurrence': issue.last_occurrence.isoformat(),
            'affected_operations_count': len(issue.affected_operations),
            'suggested_solution': issue.suggested_solution,
            'severity': issue.severity
        }
    
    def generate_report(self, hours: int = 24, output_file: str = None) -> str:
        """
        Generate a comprehensive analysis report.
        
        Args:
            hours: Number of hours to analyze
            output_file: Optional file to save report
            
        Returns:
            Report content as string
        """
        analysis = self.analyze_logs(hours)
        
        report_lines = [
            "=" * 80,
            "PROFILE OPERATIONS LOG ANALYSIS REPORT",
            "=" * 80,
            f"Analysis Timestamp: {analysis.analysis_timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Time Period: {analysis.time_period}",
            f"Total Log Entries: {analysis.total_entries}",
            f"Error Count: {analysis.error_count}",
            f"Warning Count: {analysis.warning_count}",
            "",
            "COMMON ISSUES",
            "-" * 40
        ]
        
        if analysis.common_issues:
            for i, issue in enumerate(analysis.common_issues[:10], 1):  # Top 10 issues
                report_lines.extend([
                    f"{i}. {issue['description']} ({issue['severity'].upper()})",
                    f"   Frequency: {issue['frequency']} occurrences",
                    f"   First seen: {issue['first_occurrence']}",
                    f"   Last seen: {issue['last_occurrence']}",
                    f"   Solution: {issue['suggested_solution']}",
                    ""
                ])
        else:
            report_lines.append("No common issues identified.")
        
        report_lines.extend([
            "",
            "PERFORMANCE INSIGHTS",
            "-" * 40
        ])
        
        perf = analysis.performance_insights
        if 'message' not in perf:
            report_lines.extend([
                f"Total Operations: {perf.get('total_operations', 0)}",
                f"Average Duration: {perf.get('average_duration_ms', 0):.2f}ms",
                f"Median Duration: {perf.get('median_duration_ms', 0):.2f}ms",
                f"Slowest Operation: {perf.get('max_duration_ms', 0):.2f}ms",
                f"Slow Operations: {perf.get('slow_operations_count', 0)} ({perf.get('slow_operations_percentage', 0):.1f}%)",
                f"Average Memory Usage: {perf.get('average_memory_usage_mb', 0):.2f}MB",
                f"Peak Memory Usage: {perf.get('max_memory_usage_mb', 0):.2f}MB",
                f"High Memory Operations: {perf.get('high_memory_operations_count', 0)}",
                f"Average CPU Usage: {perf.get('average_cpu_usage_percent', 0):.2f}%",
                f"Peak CPU Usage: {perf.get('max_cpu_usage_percent', 0):.2f}%",
                f"High CPU Operations: {perf.get('high_cpu_operations_count', 0)}",
                ""
            ])
            
            # Operation type performance
            if perf.get('operation_type_performance'):
                report_lines.append("Performance by Operation Type:")
                for op_type, stats in perf['operation_type_performance'].items():
                    report_lines.append(
                        f"  {op_type}: {stats['count']} ops, "
                        f"avg {stats['average_duration_ms']:.2f}ms, "
                        f"max {stats['max_duration_ms']:.2f}ms"
                    )
                report_lines.append("")
        else:
            report_lines.append(perf['message'])
        
        report_lines.extend([
            "",
            "RECOMMENDATIONS",
            "-" * 40
        ])
        
        for i, recommendation in enumerate(analysis.recommendations, 1):
            report_lines.append(f"{i}. {recommendation}")
        
        report_lines.extend([
            "",
            "=" * 80,
            "End of Report",
            "=" * 80
        ])
        
        report_content = "\n".join(report_lines)
        
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                self.logger.info(f"Report saved to {output_file}")
            except Exception as e:
                self.logger.error(f"Failed to save report: {e}")
        
        return report_content
    
    def get_error_trends(self, days: int = 7) -> Dict[str, Any]:
        """
        Analyze error trends over time.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Error trend analysis
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        error_logs = self._analyze_error_logs(cutoff_time)
        
        if not error_logs:
            return {'message': 'No error data available for trend analysis'}
        
        # Group errors by day
        daily_errors = defaultdict(int)
        error_types = defaultdict(int)
        
        for log in error_logs:
            day = log['timestamp'].date()
            daily_errors[day] += 1
            
            # Classify error type
            message = log.get('message', '')
            for error_type, pattern_info in self._error_patterns.items():
                if re.search(pattern_info['pattern'], message, re.IGNORECASE):
                    error_types[error_type] += 1
                    break
            else:
                error_types['other'] += 1
        
        # Calculate trend
        sorted_days = sorted(daily_errors.keys())
        if len(sorted_days) > 1:
            recent_avg = sum(daily_errors[day] for day in sorted_days[-3:]) / min(3, len(sorted_days))
            older_avg = sum(daily_errors[day] for day in sorted_days[:-3]) / max(1, len(sorted_days) - 3)
            trend = "increasing" if recent_avg > older_avg else "decreasing" if recent_avg < older_avg else "stable"
        else:
            trend = "insufficient_data"
        
        return {
            'analysis_period_days': days,
            'total_errors': len(error_logs),
            'daily_average': round(len(error_logs) / days, 2),
            'trend': trend,
            'daily_breakdown': {str(day): count for day, count in daily_errors.items()},
            'error_type_breakdown': dict(error_types),
            'peak_error_day': str(max(daily_errors.keys(), key=daily_errors.get)) if daily_errors else None,
            'peak_error_count': max(daily_errors.values()) if daily_errors else 0
        }


# Global analyzer instance
_profile_log_analyzer = None

def get_profile_log_analyzer() -> ProfileLogAnalyzer:
    """Get the global profile log analyzer instance."""
    global _profile_log_analyzer
    if _profile_log_analyzer is None:
        _profile_log_analyzer = ProfileLogAnalyzer()
    return _profile_log_analyzer