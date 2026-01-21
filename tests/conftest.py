# tests/conftest.py
import sys, pathlib
# Add the project root (the folder that contains graph/, processing/, scripts/) to sys.path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
# Now imports from graph, processing, scripts, etc. should work normally    
