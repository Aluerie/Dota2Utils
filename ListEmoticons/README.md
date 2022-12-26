# List Emoticons for Dota 2

This notebook is just a fork of [ListEmoticons.ipynb](https://github.com/rossengeorgiev/dota2_notebooks/blob/master/List%20Emoticons.ipynb) notebook by [rossengeorgiev](https://github.com/rossengeorgiev). So all credits to the original author. 

I brought back unicode column, rewrote the notebook for Windows Terminal/Python3, added some explanations, did some fixes and wrote Tutorial below.

### Tutorial

You can use those emoticons:
* in console for such binds as `bind o "say <copy_paste_unicode_char_here>"`.  
* in your nickname - note that then emoticons only show up in system-messages during the game such as "Player paused the game". It will not show in chat, kill-feed or anywhere else really, only system messages. 


You can copy & paste the character into Dota 2 to use the emoticon. It doesn't matter if you don't own the emoticon pack.



### TODO for myself or contributors:

- [ ] Deal with following warning for future work
    ```
    py DeprecationWarning: NEAREST is deprecated and will be removed in Pillow 10 (2023-07-01). Use Resampling.NEAREST or Dither.NONE instead.
      .resize((size, size), Image.NEAREST)\
    ```
- [ ] Find a way to show HTML elemts `<table>` even for github preview
- [ ] maybe add pictures of how to use it as in Tutorial for outsiders.






