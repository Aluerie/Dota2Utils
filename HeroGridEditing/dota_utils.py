"""
this is toned down non-async copy of code from my discord bot ;
but we also need it there for some sandbox snippets
"""
import requests


def opendota_constants_heroes():
    endpoint = 'https://api.opendota.com/api/constants/heroes'
    response = requests.get(endpoint)
    dic = response.json()

    data = {
        'id_by_npcname':
            {'': 0},
        'id_by_name':
            {'bot_game': 0},
        'name_by_id':
            {0: 'bot_game'},
        'iconurl_by_id':
            {0: "https://static.wikia.nocookie.net/dota2_gamepedia/images/3/3d/Greater_Mango_icon.png"}
    }
    for hero in dic:
        data['id_by_npcname'][dic[hero]['name']] = dic[hero]['id']
        data['id_by_name'][dic[hero]['localized_name']] = dic[hero]['id']
        data['name_by_id'][dic[hero]['id']] = dic[hero]['localized_name']
        data['iconurl_by_id'][dic[hero]['id']] = f"https://cdn.cloudflare.steamstatic.com/{dic[hero]['img']}"
    return data

hero_keys_cache = opendota_constants_heroes()

def id_by_npcname(value: str) -> int:
    """ Get hero id by npcname ;
    example: 'npc_dota_hero_antimage' -> 1 
    """
    return hero_keys_cache['id_by_npcname'][value]


def id_by_name(value: str) -> int:
    """ Get hero id by localized to english name ;
    example: 'Anti-Mage' -> 1 
    """
    return hero_keys_cache['id_by_name'][value]


def name_by_id(value: int) -> str:
    """ Get hero id by name ;
    example: 1 -> 'Anti-Mage' 
    """
    return hero_keys_cache['name_by_id'][value]


def iconurl_by_id(value: int) -> str:
    """ Get hero icon utl id by id ;
    example: 1 -> 'https://cdn.cloudflare.steamstatic.com//apps/dota2/images/dota_react/heroes/antimage.png?' 
    """
    return hero_keys_cache['iconurl_by_id'][value]


def amount_of_dota_heroes() -> int:
    """Get amount of heroes in Dota 2"""
    return len(hero_keys_cache['id_by_name']) - 1 # minus one for that zero value
