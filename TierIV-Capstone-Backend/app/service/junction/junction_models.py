from enum import Enum, auto

# ------ JUNCTION DOMAIN SPECIFIC ------ #
class JunctionType(Enum):
    # Tag in edges
    ROUNDABOUT      = auto()
    CIRCULAR        = auto()
    JUGHANDLE       = auto()
    # Tag in nodes
    MINI_ROUNDABOUT = auto()
    TURNING_CIRCLE  = auto()
    TURNING_LOOP    = auto()
    MOTORWAY_JUNCTION = auto()
    ISLAND          = auto()
    PASSING_PLACE   = auto()
    # Self-defined
    T_JUNCTION      = auto()
    Y_JUNCTION      = auto()
    CROSSROAD       = auto()

class Direction(Enum):
    THRU        = auto()
    TURN        = auto()
    CROSS       = auto()
    REVERSE     = auto()

class NbrPosition(Enum):
    OPP     = auto()
    NEAR    = auto()
    FAR     = auto()

class JuncConflict(Enum):
    INTERSECT       = auto()
    MERGE           = auto()
    NO_CONFLICT     = auto()

class LaneTurn(Enum):
    THROUGH         = auto()
    LEFT            = auto()
    SLIGHT_LEFT     = auto()
    SHARP_LEFT      = auto()
    RIGHT           = auto()
    SLIGHT_RIGHT    = auto()
    SHARP_RIGHT     = auto()
    REVERSE         = auto()
    MERGE_TO_LEFT   = auto()
    MERGE_TO_RIGHT  = auto()

class GeomRelation(Enum):
    OPPOSITE    = auto()
    ADJACENT    = auto()
    OTHER       = auto()