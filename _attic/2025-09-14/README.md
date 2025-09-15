# Attic - 2025-09-14

This directory contains code and files that were moved during cleanup but might be needed later.

## Files moved:
- `launch_webapp.py` - Redundant launcher (use `cd webapp && python run.py` instead)
- `test_endpoints.py` - Basic endpoint testing (webapp has proper tests)
- `test_webapp.py` - Basic webapp testing (webapp has proper tests)
- `verify_project.py` - Project verification script (functionality covered by proper tests)

## Reason for moving:
These files provided basic testing/launching functionality that is either:
1. Redundant with existing functionality
2. Not comprehensive enough for production use
3. Can be replaced with simpler commands

## Recovery:
If any of these files are needed, they can be restored from this attic directory.