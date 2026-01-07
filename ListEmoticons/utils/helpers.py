import pathlib

__all__ = ("create_dir_if_not_exists",)


def create_dir_if_not_exists(dir_name: str) -> None:
    if not pathlib.Path(dir_name).is_dir():
        pathlib.Path(dir_name).mkdir()
