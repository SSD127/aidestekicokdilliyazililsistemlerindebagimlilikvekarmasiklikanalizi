#!/bin/bash

# Software Complexity Analysis Platform - Run Script (Linux/Mac)

echo "=========================================="
echo "Software Complexity Analysis Platform"
echo "=========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null
then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✓ Python 3 found"

# Check if pip is installed
if ! command -v pip3 &> /dev/null
then
    echo "❌ pip is not installed. Please install pip."
    exit 1
fi

echo "✓ pip found"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✓ Dependencies installed successfully"
    echo ""

    # Run the Streamlit app
    echo "🚀 Starting Streamlit application..."
    echo "   Opening browser at http://localhost:8501"
    echo ""
    echo "   Press Ctrl+C to stop the application"
    echo ""
    streamlit run app.py
else
    echo "❌ Failed to install dependencies"
    exit 1
fi
