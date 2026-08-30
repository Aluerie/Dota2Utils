from enum import IntEnum


class Role(IntEnum):
    Carry = 1
    Mid = 2
    Offlane = 3
    Support = 4
    HardSupport = 5


CONSUMABLES: list[str] = [
    "item_tpscroll",
    "item_flask",
    "item_tango",
    "item_faerie_fire",
    "item_blood_grenade",
    "item_clarity",
    "item_enchanted_mango",
    "item_infused_raindrop",
    "item_ward_observer",
    "item_ward_sentry",
    "item_dust",
    "item_smoke_of_deceit",
]
