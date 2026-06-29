"""PyInstaller entry shim — same entry as pyproject [project.scripts] infinite-canvas."""

from infinite_canvas.main import main

if __name__ == "__main__":
    main()
