from enum import Enum, auto

class MapLocation(Enum):
    BBOX    = auto()
    POINT   = auto()
    ADDRESS = auto()
    PLACE   = auto()

class Boundary(Enum):
    DEFAULT = auto()
    ADMIN   = auto() # admin_level = [1, 10] for most; [1,11] for Bolivia, Germany, Mozambique, Netherlands, Philippines, Poland, Turkmenistan, Venezuela