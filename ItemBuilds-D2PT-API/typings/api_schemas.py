from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict

from steam import Inventory

__all__ = (
    "ItemOverview",
    "Patches",
)


# ITEM OVERVIEW


class ItemOverview(TypedDict):
    overviewRows: list[Item]
    recommendedItems: list[RecommendedItem]
    period: Literal["full"]  # Idk what other periods exist


class Item(TypedDict):
    item_id: int
    matches: int
    wins: int
    win_rate: float
    avg_minute: float
    baseline: float
    lift: float
    hero_purchase_rate: float
    hero_total_matches: int
    orders: list[Order]
    best_order: Order
    global_presence_wr: float
    global_advantage_wr: float
    global_avg_minute: float
    global_team_games_present: float
    global_team_games_adv: int


class Order(TypedDict):
    order: int
    matches: int
    wins: int
    win_rate: float
    avg_minute: float
    list: float


class RecommendedItem(TypedDict):
    item_id: int
    order: int
    matches: int
    avg_minute: float
    lift: float
    overall_lift: float


# PATCHES

type Patches = list[Patch]


class Patch(TypedDict):
    patch_id: int
    version: str
    release_date_ts: int
    release_data: str


# PATCHES

type Matches = list[Match]


class Match(TypedDict):
    match_id: int
    activate_time: int
    mmr: int
    account_id: int
    hero_id: int
    position: str
    won: bool
    data: MatchData
    created_at: str


class MatchData(TypedDict):
    imp: float
    kda: float
    mmr: int
    npc: str
    pmp: float
    won: int  # 0 / 1
    lane: str
    name: str
    role: str
    items: list[MatchItem]
    kills: int
    level: int
    patch: str
    deaths: int
    denies: int
    is_pro: int  # 0 / 1
    assists: int
    est_mmr: int
    hero_id: int
    partyId: int
    players: list[MatchPlayer]
    duration: int
    lobby_id: int
    match_id: int
    neutrals: list[MatchNeutral]
    num_pros: int
    position: str
    abilities: list[MatchAbility]
    clusterId: int
    game_time: int
    is_public: int
    last_hits: int
    moonshard: int  # 0 / 1
    net_worth: int
    account_id: int
    dire_score: int
    flagBotted: int  # 0 / 1
    is_radiant: int  # 0 / 1
    lobby_type: int
    xp_per_min: int
    displayName: str
    from_upload: int  # 0 / 1
    hero_damage: int
    is_dotaflow: int  # 0 / 1
    radiant_win: int  # 0 / 1
    talent_data: list[MatchTalent]
    gold_per_min: int
    hero_variant: int
    item_neutral: int
    tower_damage: int
    activate_time: int
    camps_stacked: int
    external_info: int  # 0 / 1
    radiant_score: int
    stun_duration: float
    aghanims_shard: int  # 0 / 1
    external_source: bool  # idk
    player_networth: list[int]
    runes_picked_up: int
    server_steam_id: int
    aghanims_scepter: int  # 0 / 1
    match_performance: MatchPerformance
    time_series_denies: list[int]
    external_source_url: bool  # idk
    radiantNetworthLeads: str
    observer_wards_placed: int
    time_series_last_hits: list[int]
    aghanims_shard_variant: bool  # idk
    match_performance_tier: str
    utility_item_purchases: MatchUtilityPurchases
    match_performance_score: float
    radiant_draft_advantage: float
    aghanims_scepter_variant: None
    external_source_internal_id: None
    match_performance_score_centered: float
    leaderboard_rank: bool  # idk
    leaderboard_region: bool  # idk
    leaderboard_name: bool  # idk
    league: bool  # idk
    league_d2pt_tier: bool  # idk


class MatchItem(TypedDict):
    slot: str
    minute: int
    charges: int
    item_id: int
    neutral: int
    important: bool
    Inventory: int


class MatchPlayer(TypedDict):
    pmp: float
    items: list[int]  # I think all of them are []
    is_pro: int  # 0 / 1
    twitch: str
    exclude: int
    hero_npc: str
    position: str
    abilities: list[int]  # I think all of them are []
    is_public: int  # 0 / 1
    account_id: int
    is_private: int  # 0 / 1
    is_radiant: int  # 0 / 1
    hero_damage: int
    networth_10: list[int]
    player_name: str
    hero_displayName: str


class MatchNeutral(TypedDict):
    tier: int
    time: int
    enchantment_id: int
    neutral_item_id: int


class MatchAbility(TypedDict):
    time: int
    level: int
    ability: int


class MatchTalent(TypedDict):
    lvl: int
    left: MatchTalentDetails
    slot: int
    right: MatchTalentDetails
    choice: str  # rt / None / lt


class MatchTalentDetails(TypedDict):
    name: str
    slot: int
    isInnate: bool
    isTalent: bool
    ability_id: int
    description: list[str]
    displayName: str


class MatchPerformance(TypedDict):
    score: float
    score_centered: float
    tier: str
    context: str
    source: str


class MatchUtilityPurchases(TypedDict):
    dust: int
    smoke: int
    total: int
    sentry_wards: int
    observer_wards: int
    ward_dispenser: int


####################
#   2. OPENDOTA    #
####################

# ITEMS

type OpendotaItemsQuery = dict[str, OpendotaItem]


class OpendotaItem(TypedDict):
    hint: list[str]
    id: int
    img: str
    dname: str
    qual: str
    cost: int
    notes: str
    attrib: list[OpendotaItemAttrib]
    mc: Literal[False] | int
    cd: float
    lore: str
    components: list[str]
    created: bool
    charges: bool


class OpendotaItemAttrib(TypedDict):
    key: str
    header: str
    value: str
    generated: NotRequired[bool]
