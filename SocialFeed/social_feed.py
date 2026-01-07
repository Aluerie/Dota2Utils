import logging

from config import STEAM_LGN, STEAM_PSW
from dota2.client import Dota2Client
from dota2.enums import EDOTAGCMsg
from steam.client import SteamClient

logging.basicConfig(format="[%(asctime)s] %(levelname)s %(name)s: %(message)s", level=logging.INFO)

MSG = "You can see me drinking Cherry Cola... Sweet serial killer, I left a love note..."


class TestDota:
    def __init__(self, client, dota):
        self.client = client
        self.dota = dota
        self._StartDota = self.client.on("logged_on")(self.StartDota)
        self._LobbyLoop = self.dota.on("ready")(self.mypc)
        self.mypc_response = self.dota.on(EDOTAGCMsg.EMsgGCToClientSocialFeedPostMessageResponse)(self.__handle_mypc)

    def mypc(self):
        print(MSG)
        self.dota.send(EDOTAGCMsg.EMsgClientToGCSocialFeedPostMessageRequest, {"message": MSG})

    def __handle_mypc(self, message):
        print(message)
        self.dota.emit("my_message_sent", message)

    def StartDota(self):
        print("Starting Dota GC communication")
        self.dota.launch()


client = SteamClient()
dota = Dota2Client(client)

test_dota = TestDota(client, dota)
client.cli_login(username=STEAM_LGN, password=STEAM_PSW)
client.run_forever()
