import sys
import os
import logging

logging.basicConfig(stream=sys.stderr)
sys.stdout = sys.stderr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from main import app as application
