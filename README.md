# Dota2Utils

Utilities and useful code snippets for Dota 2

* Dota Plus quests refresh AutoClicker (`_quest_refresh.py`)

* Sending SocialFeed messages in your profile (`DotaUtils.ipynb`)

* Python Hero Custom Grid Editor (`DotaUtils.ipynb`)

* My AutoHotkey Script (`AHKScript.ahk`)

* My autoexec file (`autoexec.cfg`)

* Toned down `D2RoshTimer.exe` of [Fjara's project](https://github.com/Fjara-h/D2RoshTimer)

---

## Dota Plus quests refresh AutoClicker

Press "Refresh challenges" button for all your heroes.

## Sending SocialFeed messages in your profile

Send message in your profile feed like it was possible a few years ago.

## Python  Hero Custom Grid Editor

We can use python script to make pixel-perfect alignemnt and stuff which is not possible with manual mouse movements in Dota 2 client.

## My AutoHotkey Script

Just a github copy for my personal ahk script.

## My autoexec file

Note that currently I do not have autoexec file in steam folder because all console commands used in it seems to be persistent per Dota 2 Client launches. But still, let's keep it as memory/reminder of commands I am using.

### autoexec.cfg location

`C:\Program Files (x86)\Steam\steamapps\common\dota 2 beta\game\dota\cfg`

important thing to note that I added

```cfg
"/"     "demo_goto 1800 relative"
```

into following file manually: `C:\Program Files (x86)\Steam\userdata\YOUR_FRIEND_ID\570\remote\user_keys.vcfg` (because idk - it seems to be a bit buggy bcs chat shortcuts intersect with it so it does not work through console)
and it seems like it is working without `autoexec.cfg` but if it ever fails then just make autoexec

## Toned down `D2RoshTimer.exe` of [Fjara's project](https://github.com/Fjara-h/D2RoshTimer)

You really should check [Fjara's project](https://github.com/Fjara-h/D2RoshTimer) yourself. It uses GameState Integration to allow user to make a keybind which quickly calculates Rosh timers and puts it into your Copypaste buffer. I do not advise using `.exe` file provided in this repo but instead go check out Fjara's original project. I mainly posted it for "cloud" storage reasons.
