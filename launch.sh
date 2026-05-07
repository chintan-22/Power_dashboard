#!/bin/bash
# Durable Power Dashboard - Launch Script

echo "🚀 Starting Durable Power Dashboard..."
echo ""

# Check if requirements are installed
python3 -c "import streamlit, pandas, plotly, pyarrow" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 Installing dependencies..."
    python3 -m pip install -q -r requirements.txt
    echo "✅ Dependencies installed"
    echo ""
fi

# Check if database exists
if [ ! -f "assignment.db" ]; then
    echo "❌ Error: assignment.db not found in current directory"
    echo "   Please ensure assignment.db is in the same directory as this script"
    exit 1
fi

echo "✅ Database found"
echo ""
echo "🌐 Launching dashboard at http://localhost:8501"
echo "   Press Ctrl+C to stop the server"
echo ""

# Launch Streamlit
python3 -m streamlit run app.py
