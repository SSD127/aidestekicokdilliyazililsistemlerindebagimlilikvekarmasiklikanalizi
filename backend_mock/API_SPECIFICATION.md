# Backend API Specification

This document describes the API endpoints that the backend team needs to implement.

## Overview

The frontend sends a GitHub repository URL and expects to receive analysis data in the formats described below.

---

## Endpoint: Analyze Repository

### Request

**Endpoint:** `POST /api/analyze`

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "github_url": "https://github.com/username/repository",
  "branch": "main",  // optional, defaults to main
  "include_tests": true  // optional, defaults to true
}
```

### Response

**Status Code:** `200 OK`

**Body:** JSON object containing the following keys:

```json
{
  "complexity": [...],
  "performance": {...},
  "disk_space": {...},
  "code_analysis": {...},
  "file_metrics": [...]
}
```

---

## Data Structures

### 1. Complexity Data (`complexity`)

**Type:** Array of objects

**Description:** List of files with their complexity scores

**Structure:**
```json
[
  {
    "name": "api/routes.py",
    "complexity": 45,
    "lines": 234
  },
  {
    "name": "models/user.py",
    "complexity": 72,
    "lines": 456
  }
]
```

**Fields:**
- `name` (string): File path relative to repository root
- `complexity` (integer): Complexity score from 0-100
- `lines` (integer): Number of lines in the file

---

### 2. Performance Metrics (`performance`)

**Type:** Object

**Description:** Time and space complexity analysis

**Structure:**
```json
{
  "time_complexity": [
    {
      "complexity": "O(1)",
      "count": 180,
      "description": "Constant time"
    },
    {
      "complexity": "O(n)",
      "count": 95,
      "description": "Linear"
    }
  ],
  "space_complexity": [
    {
      "complexity": "O(1)",
      "count": 230,
      "description": "Constant space"
    }
  ],
  "avg_execution_time": 25,
  "memory_usage": 128.5,
  "optimizable_functions": 32
}
```

**Fields:**
- `time_complexity` (array): Distribution of time complexity classes
  - `complexity` (string): Big-O notation (e.g., "O(1)", "O(n)", "O(n²)")
  - `count` (integer): Number of functions with this complexity
  - `description` (string): Human-readable description
- `space_complexity` (array): Distribution of space complexity classes
- `avg_execution_time` (number): Average execution time in milliseconds
- `memory_usage` (number): Memory usage in MB
- `optimizable_functions` (integer): Count of functions that could be optimized

---

### 3. Disk Space Data (`disk_space`)

**Type:** Object

**Description:** Disk usage breakdown by file type

**Structure:**
```json
{
  "file_types": [
    {
      "type": "Python",
      "size_mb": 15.8,
      "count": 234
    },
    {
      "type": "JavaScript",
      "size_mb": 8.3,
      "count": 89
    }
  ],
  "largest_files": [
    {
      "file": "static/images/banner_large.png",
      "size_mb": 12.4
    }
  ],
  "total_size_mb": 48.6,
  "file_count": 456
}
```

**Fields:**
- `file_types` (array): Breakdown by file type
  - `type` (string): File type name
  - `size_mb` (number): Total size in megabytes
  - `count` (integer): Number of files
- `largest_files` (array): Top 5-10 largest files
  - `file` (string): File path
  - `size_mb` (number): File size in megabytes
- `total_size_mb` (number): Total repository size
- `file_count` (integer): Total number of files

---

### 4. Code Analysis Data (`code_analysis`)

**Type:** Object

**Description:** Comprehensive code quality metrics

**Structure:**
```json
{
  "total_files": 234,
  "total_lines": 45678,
  "total_functions": 1234,
  "total_classes": 156,
  "code_quality_score": 82,
  "test_coverage": 75,
  "documentation_coverage": 68,
  "duplication_rate": 8.5,
  "languages": [
    {
      "language": "Python",
      "percentage": 65.4,
      "lines": 29873
    }
  ],
  "issues": {
    "critical": 2,
    "warnings": 28,
    "code_smells": 45,
    "security_hotspots": 6
  },
  "dependencies": {
    "total": 142,
    "direct": 38,
    "outdated": 12,
    "vulnerable": 3
  }
}
```

**Fields:**
- `total_files` (integer): Total number of code files
- `total_lines` (integer): Total lines of code
- `total_functions` (integer): Total number of functions
- `total_classes` (integer): Total number of classes
- `code_quality_score` (integer): Overall quality score (0-100)
- `test_coverage` (integer): Test coverage percentage
- `documentation_coverage` (integer): Documentation coverage percentage
- `duplication_rate` (number): Code duplication percentage
- `languages` (array): Language distribution
  - `language` (string): Programming language name
  - `percentage` (number): Percentage of codebase
  - `lines` (integer): Lines of code
- `issues` (object): Code quality issues
  - `critical` (integer): Critical issues count
  - `warnings` (integer): Warnings count
  - `code_smells` (integer): Code smells count
  - `security_hotspots` (integer): Security issues count
- `dependencies` (object): Dependency information
  - `total` (integer): Total dependencies
  - `direct` (integer): Direct dependencies
  - `outdated` (integer): Outdated dependencies
  - `vulnerable` (integer): Dependencies with vulnerabilities

---

### 5. File Metrics (`file_metrics`)

**Type:** Array of objects

**Description:** Detailed metrics for individual files

**Structure:**
```json
[
  {
    "file": "src/api/routes/user_routes.py",
    "lines": 345,
    "complexity": 67,
    "maintainability": 45,
    "functions": 18,
    "classes": 2
  }
]
```

**Fields:**
- `file` (string): File path
- `lines` (integer): Lines of code
- `complexity` (integer): Complexity score (0-100)
- `maintainability` (integer): Maintainability score (0-100)
- `functions` (integer): Number of functions
- `classes` (integer): Number of classes

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "Invalid GitHub URL",
  "message": "The provided URL is not a valid GitHub repository"
}
```

### 404 Not Found
```json
{
  "error": "Repository not found",
  "message": "The specified repository does not exist or is private"
}
```

### 500 Internal Server Error
```json
{
  "error": "Analysis failed",
  "message": "An error occurred while analyzing the repository",
  "details": "Optional error details"
}
```

---

## Implementation Notes

### Suggested Tools and Libraries

**For Python Backend:**
- `radon` - Cyclomatic complexity analysis
- `pylint` - Code quality checking
- `coverage.py` - Test coverage
- `bandit` - Security analysis
- GitHub API - Repository information

**For Node.js Backend:**
- `eslint` - Code quality
- `complexity-report` - Complexity analysis
- `istanbul/nyc` - Test coverage
- Octokit - GitHub API client

### Processing Flow

1. Receive GitHub URL from frontend
2. Clone or fetch repository (or use GitHub API)
3. Run static analysis tools
4. Calculate metrics (complexity, coverage, etc.)
5. Aggregate results into the response format
6. Return JSON response to frontend

### Performance Considerations

- Cache analysis results for frequently requested repositories
- Implement queue system for long-running analyses
- Return partial results with status updates for large repositories
- Set timeout limits for analysis (e.g., 5 minutes)

---

## Testing

See `api_examples/` folder for sample request/response JSON files that you can use for testing.

Use the mock data generator in `mock_data.py` to understand the expected data structure.
