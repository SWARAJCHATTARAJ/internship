import os
import sys

# Ensure the nested internship package root is available on sys.path
ROOT_DIR = os.path.dirname(__file__)
PROJECT_SOURCE = os.path.join(ROOT_DIR, "internship")
if PROJECT_SOURCE not in sys.path:
    sys.path.insert(0, PROJECT_SOURCE)
