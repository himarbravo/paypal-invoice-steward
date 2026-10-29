"""User interface.

Responsibility: command line, presentation and any other form of
interaction. Takes the request, calls `core` and `persistence`, and presents
the result; it contains no domain rules.

Allowed dependencies: any subpackage. Nobody imports `ui`.
"""
