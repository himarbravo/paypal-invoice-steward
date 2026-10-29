"""Punto de entrada: `python -m my_project` o el comando `my-project`."""

from my_project import __version__


def main() -> None:
    print(f"my-project {__version__}")


if __name__ == "__main__":
    main()
