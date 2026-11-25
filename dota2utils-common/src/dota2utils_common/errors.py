__all__ = (
    "ConfigError",
    "Dota2UtilsError",
    "SteamNotFoundError",
)


class Dota2UtilsError(Exception):
    """Base class for errors that should be shown to the user as a plain message."""


class ConfigError(Dota2UtilsError):
    """`config.toml` is missing a required setting or has an invalid one."""


class SteamNotFoundError(Dota2UtilsError):
    """Steam, a Steam account or the Dota 2 install could not be found."""
