from utils.enums import HeroEnum as Hero, RoleEnum as Role

# Your Steam ID in Steam 32 format
# You can find it as "Friend ID" in the Dota client under your own profile.
FRIEND_ID: int = 123_456_789

CONFIG_HEROES: dict[Hero, Role] = {
    # Carry
    Hero.DrowRanger: Role.Carry,
    Hero.PhantomAssassin: Role.Carry,
    # Mid
    Hero.Invoker: Role.Mid,
    # Offlane
    Hero.Mars: Role.Offlane,
    # Support
    Hero.Tusk: Role.Support,
    # Hard Support
    Hero.Chen: Role.HardSupport,
}
