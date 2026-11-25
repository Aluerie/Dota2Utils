# 🧦 SocialFeed

With this you can send messages to your profile feed like it was possible a few years ago.

Valve removed the UI to send messages to your profile User Feed widget, but the Game Coordinator proto messages are still there and still work.

![User Feed Showcase](./readme.png)

## 🚀 Usage

1. Follow the setup in the [main README](../README.md#-setup) and set `username` and `password` under `[steam]` in `config.toml`.
2. Edit the messages (`LYRICS`) in [main.py](./src/social_feed/main.py).
3. Run:

```sh
uv run SocialFeed
```

If your account uses Steam Guard, the script asks for the code in the terminal.
