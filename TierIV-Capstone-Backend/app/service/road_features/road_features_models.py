from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Tuple, Union
from enum import Enum


class HighwayType(Enum):
    """Car-accessible OSM highway classifications"""
    MOTORWAY = "motorway"
    MOTORWAY_LINK = "motorway_link"
    TRUNK="trunk"
    TRUNK_LINK = "trunk_link"
    PRIMARY = "primary"
    PRIMARY_LINK = "primary_link"
    SECONDARY = "secondary"
    SECONDARY_LINK = "secondary_link"
    TERTIARY = "tertiary"
    TERTIARY_LINK = "tertiary_link"
    RESIDENTIAL = "residential"
    ESCAPE = "escape"
    ROAD = "road"


class GeometryType(Enum):
    """Geometry types for road features"""
    LINESTRING = "LineString"
    MULTILINESTRING = "MultiLineString"
    POINT = "Point"


class LaneMarking(Enum):
    """Lane marking types based on OSM turn:lanes"""
    THROUGH = "through"
    LEFT = "left"
    RIGHT = "right"
    SLIGHT_LEFT = "slight_left"
    SLIGHT_RIGHT = "slight_right"
    SHARP_LEFT = "sharp_left"
    SHARP_RIGHT = "sharp_right"
    REVERSE = "reverse"
    MERGE_TO_LEFT = "merge_to_left"
    MERGE_TO_RIGHT = "merge_to_right"
    NONE = "none"
    UNKNOWN = "unknown"


class RoadFeature(BaseModel):
    """Model for individual road/edge features extracted from OSM graph"""
    
    # Graph topology
    node_from: int = Field(..., description="Source node ID")
    node_to: int = Field(..., description="Target node ID") 
    key: int = Field(..., description="Edge key for multi-edges")
    edge_id: str = Field(..., description="Unique edge identifier")
    
    # Road characteristics
    highway_type: HighwayType = Field(..., description="OSM highway classification")
    speed_limit: Optional[float] = Field(None, description="Speed limit in km/h")
    
    # Lane information
    total_lanes: Optional[int] = Field(None, description="Total number of lanes")
    lanes_forward: Optional[int] = Field(None, description="Number of forward lanes")
    lanes_backward: Optional[int] = Field(None, description="Number of backward lanes")
    lane_width: Optional[float] = Field(None, description="Lane width in meters")
    
    # Lane markings and turning
    lane_markings_forward: List[LaneMarking] = Field(default_factory=list, description="Forward lane markings")
    lane_markings_backward: List[LaneMarking] = Field(default_factory=list, description="Backward lane markings")
    turn_lanes_forward: Union[str, List[str], None] = Field(None, description="Raw turn:lanes:forward tag")
    turn_lanes_backward: Union[str, List[str], None] = Field(None, description="Raw turn:lanes:backward tag")
    
    # Geometry and location
    coordinates: List[Tuple[float, float]] = Field(..., description="Line coordinates as [(lon, lat), ...]")
    geometry_type: GeometryType = Field(..., description="Geometry type")
    
    # Basic attributes
    name: Union[str, List[str], None] = Field(None, description="Road name")
    oneway: bool = Field(False, description="Whether road is one-way")
    
    # Analysis metadata
    extraction_timestamp: str = Field(..., description="When this feature was extracted")
    
    @field_validator('edge_id')
    def validate_edge_id(cls, v):
        if not v or len(v) < 3:
            raise ValueError("Edge ID must be non-empty string")
        return v
    
    def get_lane_distribution(self) -> Dict[str, int]:
        """Get distribution of lane types from markings"""
        distribution = {}
        
        for marking in self.lane_markings_forward + self.lane_markings_backward:
            marking_str = marking.value
            distribution[marking_str] = distribution.get(marking_str, 0) + 1
            
        return distribution
    
    def is_major_road(self) -> bool:
        """Check if this is a major road type"""
        major_types = {
            HighwayType.MOTORWAY, HighwayType.MOTORWAY_LINK,
            HighwayType.PRIMARY, HighwayType.PRIMARY_LINK,
            HighwayType.SECONDARY, HighwayType.SECONDARY_LINK,
            HighwayType.TRUNK, HighwayType.TRUNK_LINK
        }
        return self.highway_type in major_types