"""Mesh backend for Print Engine.

IMPORTANT: this package runs on the SYSTEM Python (which has numpy), not on
Fusion's bundled Python (which doesn't). The Fusion add-in never imports it -
it launches generate.py in a subprocess and reads back the STL it writes.
"""
