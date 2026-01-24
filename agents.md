Rules

- make ci must pass before committing any change (run `make ci`, fix failures).
- Keep all imports at the top of each file (after module docstring if present).
- Place public methods first in classes; put private helper methods (starting with `_`) at the bottom of the class.