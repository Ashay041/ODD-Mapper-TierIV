import osmnx as ox
import networkx as nx
import numpy as np
from shapely.geometry import Point, LineString, Polygon, MultiLineString, MultiPolygon
from shapely.geometry.base import BaseGeometry
from shapely import wkt
from shapely.ops import linemerge, unary_union
from typing import List, Optional, Union, Counter
import itertools
import re
import json
import math

from .junction_models import *


# ---------- Junction type classification ---------- #
def _calculate_angle(p1: tuple, p2: tuple, p3: tuple) -> float:
    '''
    Calculate angles in degree between vectors p1 to p2 and p3 to p2
    
    Inputs:
    `p2`:       junction node coordinate
    `p1`, `p2`: neighbor node coordinates

    Outputs:
    Interior angle
    '''
    vec1 = np.array([p2[0] - p1[0], p2[1] - p1[1]])
    vec2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])

    dot_product = np.dot(vec1, vec2)

    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    cos_angle = dot_product / (norm1 * norm2)
    angle = np.arccos(np.clip(cos_angle, -1.0, 1.0))  # in radians

    return np.degrees(angle)


def classify_edge_tag(G: nx.MultiDiGraph, node_id: int) -> Optional[JunctionType]:
    '''
    Identify junction type by tag of the edge
        - roundabout
        - circular
        - jughandle
    
    Inputs:
    `node_id`:    junction node of interest

    Outputs:
    Predefined `JunctionType` or None
    '''
    # Tags for edges
    for _, _, _, data in G.edges([node_id], data=True, keys=True):
        raw = data.get("junction")
        if not raw:
            continue
        key = raw.replace(":", "_").upper()
        if key in JunctionType.__members__:
            return JunctionType[key]
    return None


def classify_node_tag(G: nx.MultiDiGraph, node_id: int) -> Optional[JunctionType]:
    '''
    Identify junction type by tag of the node
        - mini_roundabout
        - turning_circle
        - turning_loop
        - motorway_junction
        - island
        - passing_place
    
    Inputs:
    `node_id`:  junction node of interest

    Outputs:
    Predefined `JunctionType` or None
    '''
    # Tags for nodes
    data = G.nodes[node_id]
    raw = data.get('junction')

    if raw is None:
        raw = data.get('highway')
    if raw is None:
        return None
    
    tags = raw if isinstance(raw, list) else [raw]

    for t in tags:
        key = t.replace(':', '_').upper()
        if key in JunctionType.__members__:
            return JunctionType[key]
    
    return None


def classify_node_other(G: nx.MultiDiGraph, node_id: int, angle_threshold: float) -> Optional[JunctionType]:
    '''
    Classify junction type by degree and angle
        - 2 or less degrees: no junction (look at stop/traffic signal instead)
        - 4 or more degrees: `CROSSROAD`
        - 3: If angle is larger than defined threshold, classify as `T_JUNCTION`; otherwise, `Y_JUNCTION`
    
    Inputs:
    `node_id`:  junction node of interest

    Outputs:
    Predefined `JunctionType` or None
    '''
    # use an undirected view so degree = len(neighbors)
    und = G.to_undirected()
    nbrs = list(und.neighbors(node_id))
    deg = len(nbrs)

    if deg <= 2:
        return None
    if deg >= 4:
        return JunctionType.CROSSROAD

    # exactly 3 distinct legs
    x0, y0 = G.nodes[node_id]["x"], G.nodes[node_id]["y"]
    pts = [(G.nodes[n]["x"], G.nodes[n]["y"]) for n in nbrs]

    # compute the three interior angles
    angles = [
        _calculate_angle(pts[i], (x0, y0), pts[(i + 1) % 3])
        for i in range(3)
    ]
    if max(angles) <= angle_threshold:
        return JunctionType.T_JUNCTION
    else:
        return JunctionType.Y_JUNCTION


def classify_all(G: nx.MultiDiGraph, junc_ty_angle_threshold: float):
    '''
    Call (in priority order):
        - `classify_edge_tag`
        - `classify_node_tag`
        - `classify_node_other`

    Tag self.G.nodes with a `tier4_junction_type` attribute
    '''
    for node_id in G.nodes:
        # 1) edge‐tag
        junc_type = classify_edge_tag(G, node_id)
        # 2) node‐tag
        if junc_type is None:
            junc_type = classify_node_tag(G, node_id)
        # 3) degree/angle
        if junc_type is None:
            junc_type = classify_node_other(G, node_id, junc_ty_angle_threshold)

        G.nodes[node_id]['tier4_junction_type'] = junc_type


# ---------- Junction interaction analysis ---------- #
def _parse_lane_data(data: dict) -> tuple[set[LaneTurn], int, bool]:
    '''
    Based on the passed data attribute of an edge,
    Retrieve the allowed turns for the edge
    Retrieve or estimate the number of lanes for the edge

    Inputs:
    `data`:     data attributes of an edge

    Outputs:
    Set of `LaneTurn` on the directed edge
    Number of lanes
    Whether the number of lanes is an estimate
    '''
    # determine the direction of the edge
    side = 'backward' if data.get('reversed') else 'forward'

    # retrieve the relevant turn tag
    turn_key = f'turn:lanes:{side}'
    tag_raw = data.get(turn_key, '')

    # parse the turn movements
    turns: set[LaneTurn] = set()

    ## DEBUG
    # if tag_raw:
    #     print(tag_raw) ##
    
    if not tag_raw:
        lanes = []
    elif isinstance(tag_raw, list):
        lanes = tag_raw
    else:
        lanes = tag_raw.split('|')

    for lane_str in map(str, lanes):
        for direction in lane_str.split(';'):
            d = direction.strip().upper()
            if not d:
                continue
            try:
                turns.add(LaneTurn[d])
            except KeyError:
                # unknown turn code, skip
                continue
    # if no explicit turn lanes, assume a single through‐lane
    if not turns:
        turns.add(LaneTurn.THROUGH)

    # retrieve the relevant lanes tag
    lanes_key = f'lanes:{side}'
    lanes_val = data.get(lanes_key)
    estimate = False

    if isinstance(lanes_val, list):
        # if we have an explicit turn:lanes tag, count its segments
        if tag_raw:
            num_lanes = len(tag_raw)
        else:
            # fallback: take the first entry in the list
            try:
                num_lanes = int(lanes_val[0])
            except (ValueError, TypeError, IndexError):
                num_lanes = 1
            estimate = True

    elif lanes_val is not None:
        # single-value lanes tag
        try:
            num_lanes = int(lanes_val)
        except (ValueError, TypeError):
            num_lanes = 1
            estimate = True
    else:
        # no lanes: value, assume 1 and mark estimate
        num_lanes = 1
        estimate = True

    return turns, num_lanes, estimate


def fill_edge_geom(G: nx.MultiDiGraph):
    '''
    Assume & add straight-line `LineString` for all self.G.edges without 'geometry' attribute
    In current implementation: replaced by `configure_graph` in query
    '''
    for u, v, key, data in G.edges(data=True, keys=True):
        if 'geometry' not in data:
            x0, y0 = G.nodes[u]['x'], G.nodes[u]['y']
            x1, y1 = G.nodes[v]['x'], G.nodes[v]['y']
            data['geometry'] = LineString([(x0, y0), (x1, y1)])


def get_legs(G: nx.MultiDiGraph, node_id: int) -> list[dict]:
    '''
    Get a metadata for neighbor edges of a node
        - neighbor node id
        - neighbor node coordinates
        - allowed turns from neighbor node to this node
        - geometry (LineString) of the neighbor edge
    
    Inputs:
    `node_id`:  junction node of interest

    Outputs:
    List of dictionaries, one for each leg
    '''
    legs: list[dict] = []
    seen = set()

    # incoming edges: neighbor to this
    for u, v, key, data in G.in_edges(node_id, data=True, keys=True):
        if not v == node_id:
            continue

        # get neighbor node info
        nbr_id = u
        coord = (G.nodes[nbr_id]['x'], G.nodes[nbr_id]['y'])
        turns, lanes, est = _parse_lane_data(data)
        geom = data.get('geometry')

        legs.append({'nbr_id': nbr_id, 'nbr_coord': coord, 'in_turns': turns, 'geom': geom})
        seen.add(nbr_id)

    # outgoing edges: this to neighbor
    for u, v, key, data in G.out_edges(node_id, data=True, keys=True):
        if not u == node_id:
            continue
        
        # get neighbor node info
        nbr_id = v
        if nbr_id in seen:
            continue
        
        coord = (G.nodes[nbr_id]['x'], G.nodes[nbr_id]['y'])
        raw_geom = data.get('geometry')
        if isinstance(raw_geom, str):
            geom = wkt.loads(raw_geom)
        else:
            geom = raw_geom

        legs.append({'nbr_id': nbr_id, 'nbr_coord': coord, 'in_turns': None, 'geom': geom})
        seen.add(nbr_id)

    return legs


def get_position(G: nx.MultiDiGraph, node_id: int, leg1: dict, leg2: dict,
    angle_threshold: float, right_lane_drive: bool = True) -> NbrPosition:
    '''
    Get the relative position of leg2 relative to leg1 depending on angle and driving side
        - NEAR: leg2 on the nearside (right-side in right-drive, left-side in left-drive) of leg1
        - FAR:  leg2 on the farside of leg1
        - OPP:  leg2 is roughly straight across leg1
    
    Inputs:
    `node_id`:          junction node of interest
    `leg1`:             edge 1 connected to junction node
    `leg2`:             edge 2 connected to junction node
    `angle_threshold`:  angle threshold for determining neighbor edge position
    `right_lane_drive`: whether drive on the right lane

    Outputs:
    Leg2's position to Leg1 defined by `NbrPosition`
    '''

    def get_dir_vector(leg):
        '''
        Based on the LineString from leg['geom']
        Find the point on the line nearest to the junction node
        Get a direction vector based on the segment
        '''
        geom: LineString = leg.get('geom')
        
        # project junction node onto the line
        proj_dist = geom.project(node_pt)
        pt_on = geom.interpolate(proj_dist)
        eps = min(geom.length * 0.01, 1e-3) # approximate

        # choose a second point slightly further along the line
        if proj_dist + eps <= geom.length:
            # step forward if near the front
            pt2 = geom.interpolate(proj_dist + eps)
        else:
            # step backward if near the end
            pt2 = geom.interpolate(proj_dist - eps)
        
        return (pt2.x - pt_on.x, pt2.y - pt_on.y)


    x0, y0 = G.nodes[node_id]['x'], G.nodes[node_id]['y']
    node_pt = Point(x0, y0)

    # get direction vectors for each leg
    v1 = get_dir_vector(leg1)
    v2 = get_dir_vector(leg2)

    # compute angle between v1 and v2
    dot = v1[0]*v2[0] + v1[1]*v2[1]
    mag1 = (v1[0]**2 + v1[1]**2)**0.5
    mag2 = (v2[0]**2 + v2[1]**2)**0.5
    # guard against zero-length
    if mag1 == 0 or mag2 == 0:
        return NbrPosition.FAR
    cosang = max(-1.0, min(1.0, dot/(mag1*mag2)))
    angle = math.degrees(math.acos(cosang))

    # OPPOSITE if almost straight
    if angle > (180 - angle_threshold):
        return NbrPosition.OPP

    # RIGHT‐ANGLE region: distinguish near/far by cross‐product sign
    if abs(angle - 90) < angle_threshold:
        cross = v1[0]*v2[1] - v1[1]*v2[0]
        # for right‐side driving, negative cross means leg2 is on v1’s right (near)
        if right_lane_drive:
            return NbrPosition.NEAR if cross < 0 else NbrPosition.FAR
        else:
            return NbrPosition.NEAR if cross > 0 else NbrPosition.FAR

    # everything else is considered far‐side
    return NbrPosition.FAR


def get_conflict_type(G: nx.MultiDiGraph, this_move: Direction, other_move: Direction, 
                      nbr_pos: NbrPosition, conflict_classifier: list[dict]) -> JuncConflict:
    '''
    Look up conflict type from the JSON-like classifier table (passed to analyzer at init)
    
    Inputs:
    `this_move`:    movement of this vehicle
    `other_move`:   movement of another vehicle on another neighbor edge
    `nbr_pos`:      neighbor edge position relative to this vehicle's edge
    '''
    for entry in conflict_classifier:
        if (
            Direction[entry['this_move']] == this_move and
            Direction[entry['other_move']] == other_move and
            NbrPosition[entry['nbr_pos']] == nbr_pos
        ):
            return JuncConflict[entry['conflict']]
    # Default fallback (should not happen if table is complete)
    return JuncConflict.NO_CONFLICT


def count_pair_interaction(G: nx.MultiDiGraph, node_id: int, leg1: dict, leg2: dict,
    conflict_counter: Counter[JuncConflict], conflict_classifier: list[dict],
    angle_threshold: float, right_lane_drive: bool = True):
    '''
    Count the potential conflicts between every pair of allowed turns on leg1 and leg2 at a junction node

    Inputs:
    `node_id`:              junction node of interest
    `leg1`:                 edge 1 connected to junction node
    `leg2`:                 edge 2 connected to junction node
    `conflict_counter`:     counter for collection of conflicts
    `angle_threshold`:      angle threshold for determining neighbor edge position
    `right_lane_drive`:     whether drive on the right lane
    '''
    # group left‐ vs right‐turn variants
    left_variants = {
        LaneTurn.LEFT,
        LaneTurn.SLIGHT_LEFT,
        LaneTurn.SHARP_LEFT,
        LaneTurn.MERGE_TO_LEFT,
    }
    right_variants = {
        LaneTurn.RIGHT,
        LaneTurn.SLIGHT_RIGHT,
        LaneTurn.SHARP_RIGHT,
        LaneTurn.MERGE_TO_RIGHT,
    }

    # map a lane‐turn to Direction based on driving side
    def _to_direction(turn: LaneTurn) -> Direction:
        # map through and reverse turns to direction
        if turn is LaneTurn.THROUGH:
            return Direction.THRU
        if turn is LaneTurn.REVERSE:
            return Direction.REVERSE
        # classify turn/cross based on driving side
        if turn in (right_variants if right_lane_drive else left_variants):
            return Direction.TURN
        return Direction.CROSS

    # check if either leg has no incoming turns and mark NO_CONFLICT
    leg1_in_turns = leg1.get('in_turns')
    leg2_in_turns = leg2.get('in_turns')

    if leg1_in_turns is None or leg2_in_turns is None:
        conflict_counter[JuncConflict.NO_CONFLICT] += 1
        return
    
    # determine position of leg2 relative to leg1
    nbr_pos = get_position(G,
        node_id, leg1, leg2,
        angle_threshold,
        right_lane_drive
    )

    # iterate every combo of movements
    for t1, t2 in itertools.product(leg1_in_turns, leg2_in_turns):
        # classify each movement
        this_move  = _to_direction(t1)
        other_move = _to_direction(t2)

        # look up the conflict via JSON-formatted conflict_classifier
        conflict = get_conflict_type(G, this_move, other_move, nbr_pos, conflict_classifier)
        conflict_counter[conflict] += 1


# ---------- Junction geometry analysis ---------- #
def _convert_to_meters(val: str) -> float:
    '''
    Parse a width string into numeric (in meters):
        - "12m", "12 m"
        - "40ft", "40  ft"
        - "16'3\"", "16' 3\"", "16 ' 3"
        - "5mi", "5 mi"
        - "2km", "2 km"
        - bare number (assume meter)
    '''
    s = str(val).strip().lower()

    # feet + inches, e.g. 16'3", 16' 3", 16 ' 3"
    m = re.match(r"^(\d+)\s*'\s*(\d+)", s)
    if m:
        ft   = float(m.group(1))
        inch = float(m.group(2))
        return ft * 0.3048 + inch * 0.0254

    # number + unit (allowing whitespace), capture unit letters
    m = re.match(r"^([\d\.]+)\s*([a-z]+)", s)
    if m:
        num, unit = m.group(1), m.group(2)
        f = float(num)
        if unit in ("m", "meter", "meters"):
            return f
        if unit in ("km", "kilometer", "kilometre"):
            return f * 1000.0
        if unit in ("mi", "mile", "miles"):
            return f * 1609.344
        if unit in ("ft", "feet"):
            return f * 0.3048
        if unit in ("in", "inch", "inches"):
            return f * 0.0254

    # bare number
    try:
        return float(s)
    except ValueError:
        return 0.0


def _get_main_line(geom: Union[LineString, MultiLineString]) -> LineString:
    '''
    Merge, simplify, and pick longest connected network
    
    Input:
    `geom`: LineString/MultiLineString
    
    Output: 
    A single LineString
    '''
    # If single LineString
    if isinstance(geom, LineString):
        return geom
    
    # Merge connected segments into as few lines as possible if MultiLineString
    merged = linemerge(geom)
    if isinstance(merged, LineString):
        return merged
    elif isinstance(merged, MultiLineString):
        # Return the longest LineString in the MultiLineString
        return max(merged.geoms, key=lambda g: g.length)
    else:
        raise TypeError('Input geometry could not be converted to a LineString')


def _orient_and_trim(geom: LineString, node_pt: Point, trim_dist: float) -> LineString:
    '''
    Orient 1st point of LineString to junction node
    Trim segment with specified distance from the node

    Inputs:
    `geom`:         LineString geometry of an edge, in default crs (geographic)
    `node_pt:       junction node coordinate
    `trim_dist`:    distance of the trim, in meters

    Outputs:
    A re-oriented and trimmed LineString segment at junction node
    '''
    # Project geom to UTM
    geom_utm, utm_crs = ox.projection.project_geometry(geom)
    # node_utm, _       = ox.projection.project_geometry(node_pt)

    # Place junction node coordinate at the first point
    if not isinstance(geom_utm, LineString):
        raise TypeError('Projected geometry is not a LineString')

    coords = list(geom_utm.coords)
    if Point(coords[-1]).equals(node_pt):
        coords.reverse()
    line = LineString(coords)

    # Trim to the specified distance in meters
    if line.length > trim_dist:
        cut = line.interpolate(trim_dist)
        trimmed_utm = LineString(([line.coords[0], (cut.x, cut.y)]))
    else:
        trimmed_utm = line
    
    # Convert back to default crs (geographic)
    trimmed_geo, _ = ox.projection.project_geometry(trimmed_utm, crs=utm_crs, to_latlong=True)
    
    if not isinstance(trimmed_geo, LineString):
        raise TypeError('Projected geometry is not a LineString')
    return trimmed_geo


def _parse_edge_width(data: dict, default_lane_width: float) -> tuple[float, bool]:
    '''
    Determine total width for this edge (bidirectional combined):

        - if data['width'] exists:          parse it, estimate=False.
        - elif data['est_width'] exists:    parse it, estimate=True.
        - else, fallback to (num_lanes * default_lane_width), estimate=True, where num_lanes is:
            a) if data['lanes'] is an int or numeric string: return
            b) else if data['lanes'] is a list or missing: use `parse_lane_data(data)[1]`.
            c) else if `parse_lane_data(data)[2]` gave `True` and data['lanes'] is a list: first list element as int
            d) else: 1
    '''
    # explicit width
    if 'width' in data:
        w = _convert_to_meters(data['width'])
        return w, False

    # estimated width
    if 'est_width' in data:
        w = _convert_to_meters(data['est_width'])
        return w, True

    # fallback: compute lanes count
    lanes_val = data.get('lanes')
    num_lanes = None
    parsed_est = None

    # a) single int or numeric string
    if not isinstance(lanes_val, list) and lanes_val is not None:
        try:
            nl = int(lanes_val)
            if nl >= 1:
                num_lanes = nl
        except (ValueError, TypeError):
            pass

    # b) use parse_lane_data
    if num_lanes is None:
        _, parsed_lanes, parsed_est = _parse_lane_data(data)
        if parsed_lanes >= 1:
            num_lanes = parsed_lanes

    # c) if parsed_estimate and original lanes was a list
    if num_lanes is None and isinstance(lanes_val, list) and parsed_est:
        try:
            nl = int(lanes_val[0])
            if nl >= 1:
                num_lanes = nl
        except (ValueError, TypeError, IndexError):
            pass

    # d) final fallback
    if num_lanes is None or num_lanes < 1:
        num_lanes = 1

    # total width = lanes * default width, and it's an estimate
    return default_lane_width * num_lanes, True


def _build_corridor(centerline: LineString, total_width: float) -> Optional[Polygon]:
    '''
    Buffer the centerline equally on both sides by half the total width
    '''
    # project centerline into UTM
    line_utm, utm_crs = ox.projection.project_geometry(centerline)

    if not isinstance(line_utm, LineString):
        return None

    # offset to generate polygon
    half = total_width / 2.0
    left_raw  = line_utm.parallel_offset(half, 'left',  join_style='mitre')
    right_raw = line_utm.parallel_offset(half, 'right', join_style='mitre')
    left  = _get_main_line(left_raw)
    right = _get_main_line(right_raw)
    coords = list(left.coords) + list(right.coords)[::-1]

    # convert coords back to default crs (lat/lon)
    poly_utm = Polygon(coords)
    poly_geo, crs = ox.projection.project_geometry(poly_utm, crs=utm_crs, to_latlong=True)

    if isinstance(poly_geo, Polygon):
        return poly_geo
    else:
        return None


def get_node_corridors(G: nx.MultiDiGraph, node_id: int, trim_dist: float, 
                        default_lane_width: float) -> tuple[BaseGeometry, BaseGeometry]:
    '''
    For each edge connected to junction node, trim back `trim_dist` meters
    Build a corridor polygon using the total carriageway width
    Union all corridors into one/multiple non-overlapping polygon(s)

    Return 
        - Underlying central lines: LingString | MultiLineString
        - Corridor: Polygon | MultiPolygon
    '''
    node_pt = Point(G.nodes[node_id]['x'], G.nodes[node_id]['y'])
    lines = []
    corridors = []
    trimmed = None  # Initialize trimmed to None

    for u, v, key, data in G.edges(node_id, data=True, keys=True):
        # skip the reversed duplicate of bidirectional edges - COMMENT OUT: affect polygon display
        # if not data.get('oneway', False) and data.get('reversed', False):
        #     continue
        if node_id not in (u, v):
            continue

        # get or synthesize the geometry
        geom = data.get('geometry')

        ## DEBUG
        # print(geom) ##

        if geom is None:
            p0 = (G.nodes[u]['x'], G.nodes[u]['y'])
            p1 = (G.nodes[v]['x'], G.nodes[v]['y'])
            geom = LineString([p0, p1])

        # orient & trim off the first `trim_dist` meters
        trimmed = _orient_and_trim(geom, node_pt, trim_dist)
        lines.append(trimmed)

        # parse out the total width of this carriageway
        total_width, width_est = _parse_edge_width(data, default_lane_width)

        # build the corridor polygon
        corridors.append(_build_corridor(trimmed, total_width))
    
    multi_lines = MultiLineString(lines)
    union_line = linemerge(multi_lines)
    union_poly = unary_union(corridors)

    ## DEBUG
    # print(union_line)
    # print(union_poly) ##

    return union_line, union_poly #type:ignore


# ------ FINAL OUTPUT ------ #
def analyze_output_all(G: nx.MultiDiGraph, output_path, junc_ty_angle_threshold: float, lane_pos_threshold: float, trim_dist: float, lane_width: float, conflict_classifier: list[dict]):
    '''
    Deprecated in current pipeline but may useful for debugging and external utility
    '''
    # Tag junction type
    classify_all(G, junc_ty_angle_threshold)
    fill_edge_geom(G)  

    class JunctionAnalysisResult:
        def __init__(self, node_id, node_coord, junc_type, conflict_counter, polygon):
            self.node_id = node_id
            self.node_coord = node_coord
            self.junc_type = junc_type
            self.conflict_counter = dict(conflict_counter)
            # Serialize polygon to WKT or GeoJSON
            self.polygon = polygon.wkt if polygon is not None else None

        def to_dict(self):
            return {
                'node_id': self.node_id,
                'node_coord': self.node_coord,
                'junc_type': self.junc_type.name,
                'conflict_counter': {conflict.name: count for conflict, count in self.conflict_counter.items()},
                'polygon': self.polygon,
            }

    results = []
    for node_id in G.nodes:
        junc_type = G.nodes[node_id]['tier4_junction_type']
        if junc_type is None:
            continue

        node_coord = (G.nodes[node_id]['x'], G.nodes[node_id]['y'])

        conflict_counter: Counter[JuncConflict] = Counter()
        # interaction_counter: Counter[dict] = Counter()
        legs = get_legs(G, node_id)
        for leg1, leg2 in itertools.combinations(legs, 2):
            count_pair_interaction(G, node_id, leg1, leg2, conflict_counter, conflict_classifier, lane_pos_threshold, True)

        polygon = get_node_corridors(G, node_id, trim_dist, lane_width)

        result = JunctionAnalysisResult(node_id, node_coord, junc_type, conflict_counter, polygon)
        results.append(result.to_dict())

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
