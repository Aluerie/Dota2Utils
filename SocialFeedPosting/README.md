### SocialFeedPosting

With this you can send message in your profile feed like it was possible a few years ago.

Valve removed UI to send messages in your profile Social Feed 
but GameCoordinator Proto messages are still there and still functioning. 

---

To use it change `MSG` to what you want to post 
and create `config.py` with your credentials like i.e.

```py
# STEAM
STEAM_LGN = 'lgn'
STEAM_PSW = 'psw'

# TEST STEAM
STEAM_TEST_LGN = 'lgn'
STEAM_TEST_PSW = 'psw'

# MY STEAM
STEAM_MY_LGN = 'lgn'
STEAM_MY_PSW = 'psw'
```