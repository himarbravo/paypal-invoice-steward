"""Data input/output.

Responsibility: everything that crosses the program's boundary: files,
network, databases and external APIs. Converts between external formats and
`core` objects.

Allowed dependencies: `core`. Neither `core` nor any other domain module
imports `persistence`.
"""
