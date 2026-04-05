# Backend Development Guide

This folder contains everything the backend team needs to implement the API for the Software Complexity Analysis Platform.

## 📁 Folder Contents

```
backend_mock/
├── README_FOR_BACKEND_TEAM.md    # This file - start here!
├── API_SPECIFICATION.md           # Complete API documentation
├── mock_data.py                   # Mock data generator (reference implementation)
├── api_examples/
│   ├── example_request.json      # Sample API request
│   └── example_response.json     # Sample API response
```

## 🎯 Your Mission

Build a backend API that:
1. Accepts a GitHub repository URL
2. Analyzes the repository's code
3. Returns analysis data matching the structure in `API_SPECIFICATION.md`

## 📖 Getting Started

### Step 1: Read the API Specification
Start with `API_SPECIFICATION.md` - it contains:
- Endpoint details (POST /api/analyze)
- Request/response formats
- All data structures
- Error handling requirements

### Step 2: Understand the Data Structures
Look at `api_examples/example_response.json` to see a complete example of what the frontend expects.

### Step 3: Study the Mock Data Generator
Open `mock_data.py` to see:
- How data is structured
- What fields are required
- Example values and ranges
- Data validation logic

### Step 4: Choose Your Tools
See the "Suggested Tools and Libraries" section in `API_SPECIFICATION.md` for recommended libraries.

## 🛠️ Implementation Checklist

### Core Functionality
- [ ] Create POST `/api/analyze` endpoint
- [ ] Accept JSON with `github_url`, `branch`, `include_tests`
- [ ] Validate GitHub URL format
- [ ] Clone or fetch repository from GitHub
- [ ] Run code analysis tools
- [ ] Generate complexity metrics
- [ ] Calculate performance metrics
- [ ] Analyze disk space usage
- [ ] Aggregate code statistics
- [ ] Return formatted JSON response

### Error Handling
- [ ] Handle invalid URLs (400 Bad Request)
- [ ] Handle non-existent repositories (404 Not Found)
- [ ] Handle analysis errors (500 Internal Server Error)
- [ ] Add timeout for long-running analyses
- [ ] Log errors appropriately

### Performance Optimization
- [ ] Implement caching for analyzed repositories
- [ ] Add queue system for concurrent requests
- [ ] Set reasonable timeout limits
- [ ] Consider partial result streaming for large repos

## 📊 Required Metrics to Calculate

### 1. Complexity Analysis
You need to analyze each file and calculate:
- **Cyclomatic Complexity**: Measure code complexity (0-100 scale)
- **File Size**: Count lines of code per file

**Tools:**
- Python: `radon`, `mccabe`
- JavaScript: `eslint`, `complexity-report`

### 2. Performance Metrics
Analyze functions and determine:
- **Time Complexity**: Big-O notation (O(1), O(n), O(n²), etc.)
- **Space Complexity**: Memory usage patterns

**Approach:**
- Use static analysis to detect loops, recursion, data structures
- Categorize functions by complexity class

### 3. Disk Space Analysis
Calculate:
- **Total repository size**
- **Size per file type** (Python, JavaScript, CSS, etc.)
- **Largest files**

**Approach:**
- Scan directory tree
- Group files by extension
- Calculate cumulative sizes

### 4. Code Quality Metrics
Calculate:
- **Test Coverage**: % of code covered by tests
- **Documentation Coverage**: % of functions with docstrings/comments
- **Code Duplication**: % of duplicated code
- **Issues**: Count of warnings, errors, security issues

**Tools:**
- Python: `coverage.py`, `pylint`, `bandit`, `radon`
- JavaScript: `istanbul`, `eslint`, `jscpd`

### 5. Language Distribution
Determine:
- Percentage of each programming language
- Lines of code per language

**Approach:**
- Use file extensions to identify languages
- Count lines per file type

## 🧪 Testing Your Implementation

### Manual Testing
1. Use the example request in `api_examples/example_request.json`
2. Send POST request to your endpoint
3. Verify response matches `api_examples/example_response.json` structure

### Automated Testing
Create test cases for:
- Valid GitHub URLs
- Invalid URLs
- Private repositories
- Non-existent repositories
- Large repositories (>1000 files)
- Timeout scenarios

### Testing with Frontend
1. Update the frontend code in `app.py` line 42-45
2. Replace mock data calls with actual API calls:
```python
# Replace this:
st.session_state.analysis_data = {
    'complexity': generate_complexity_data(),
    ...
}

# With this:
import requests
response = requests.post('http://localhost:5000/api/analyze',
                        json={'github_url': st.session_state.github_url})
st.session_state.analysis_data = response.json()
```

## 🔧 Recommended Backend Stack

### Option 1: Python (Flask/FastAPI)
```python
from flask import Flask, request, jsonify
import radon, pylint, coverage

app = Flask(__name__)

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json
    github_url = data.get('github_url')

    # Your analysis logic here
    result = perform_analysis(github_url)

    return jsonify(result)
```

### Option 2: Node.js (Express)
```javascript
const express = require('express');
const eslint = require('eslint');

const app = express();

app.post('/api/analyze', async (req, res) => {
  const { github_url } = req.body;

  // Your analysis logic here
  const result = await performAnalysis(github_url);

  res.json(result);
});
```

## 📚 Recommended Libraries

### For Python Backend
```bash
pip install flask
pip install radon        # Complexity analysis
pip install pylint       # Code quality
pip install coverage     # Test coverage
pip install bandit       # Security analysis
pip install pygithub     # GitHub API
pip install gitpython    # Git operations
```

### For Node.js Backend
```bash
npm install express
npm install eslint
npm install complexity-report
npm install istanbul
npm install @octokit/rest   # GitHub API
npm install simple-git       # Git operations
```

## 🚀 Deployment

### Local Development
1. Run backend on `http://localhost:5000`
2. Update frontend to point to your API
3. Test integration

### Production Deployment
Consider:
- Docker containers
- API rate limiting
- Authentication (if needed)
- HTTPS/SSL
- CORS configuration
- Environment variables for secrets

## 💡 Tips

1. **Start Simple**: Begin with basic file counting and simple metrics
2. **Iterate**: Add more sophisticated analysis incrementally
3. **Use the Mock Data**: Reference `mock_data.py` for expected data formats
4. **Test Early**: Test with the frontend as soon as you have basic data
5. **Cache Results**: Analyzing repositories is expensive - cache when possible
6. **Handle Edge Cases**: Empty repos, binary files, very large files, etc.

## ❓ Questions?

If you need clarification on:
- **Data structures**: Check `api_examples/example_response.json`
- **API format**: Read `API_SPECIFICATION.md`
- **Implementation examples**: Study `mock_data.py`

## 📞 Integration Point

The frontend will call your API from `app.py` line 42-45. Currently it uses mock data:

```python
# CURRENT (Mock):
st.session_state.analysis_data = {
    'complexity': generate_complexity_data(),
    'performance': generate_performance_metrics(),
    'disk_space': generate_disk_space_data(),
    'code_analysis': generate_code_analysis_data(),
    'file_metrics': generate_file_metrics()
}

# FUTURE (Real API):
response = requests.post(
    'http://your-api-url/api/analyze',
    json={'github_url': st.session_state.github_url}
)
st.session_state.analysis_data = response.json()
```

---

**Good luck with the implementation! 🚀**
