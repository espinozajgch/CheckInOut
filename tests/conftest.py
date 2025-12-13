import sys, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_PATH = os.path.join(ROOT, "src")

print(">> PYTEST LOADING CONFTEXT — ADDING:", SRC_PATH)
sys.path.insert(0, SRC_PATH)