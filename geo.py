from math import sin, cos, sqrt, asin, radians
from . import config
import numpy as np

def exact_distance(lat1, lng1, lat2, lng2):
    """Optimized calculation of distance in m between two points using coordinates in decimal degrees."""
    
    # average radius of earth in km in France: R = 6367.5
    
    p = 0.017453292519943295     #Pi/180
    a = 0.5 - cos((lat2 - lat1) * p)/2 + cos(lat1 * p) * cos(lat2 * p) * (1 - cos((lng2 - lng1) * p)) / 2
    return 12735000 * asin(sqrt(a)) #2*R*asin...
    
    #--------------OLD comprehensive function--------------
    
    # average radius of earth in km in France
    #R = 6367.5
    #
    #if degrees:
    #    lat1, lng1, lat2, lng2 = [radians(x) for x in [lat1, lng1, lat2, lng2]]

    #dlng = lng2 - lng1
    #dlat = lat2 - lat1
    
    #a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlng / 2)**2
    #c = 2 * atan2(sqrt(a), sqrt(1 - a))

    #return R * c

def coord_to_x_y(origin_lat, origin_lng, pt_lat, pt_lng):
    return (pt_lng - origin_lng) * cos(radians(origin_lat)) * 110574, (pt_lat - origin_lat) * 111320 
    
    
def equirectangular_dist(lat1, lng1, lat2, lng2):
    """Calculate the distance in m using the equirectangular projection. Point 1 is used as the origin."""
    #x1 = 0
    #y1 = 0
    x2 = (lng2 - lng1) * cos(radians(lat1)) * 110574
    y2 = (lat2 - lat1) * 111320
    return sqrt(x2 ** 2 + y2 ** 2) 
    
    
def distance_matrix(lat1_col, lng1_col, lat2_col, lng2_col, distance_fn=equirectangular_dist):
    """Return list of lists of size n*n for n coordinates in decimal degrees."""
    if len(lat1_col) != len(lat1_col) or len(lat2_col) != len(lat2_col):
        raise ValueError("Error, latitude and longitude columns have different lengths")
    
    #return a comprehension list iterated on both rows and columns
    return [[distance_fn(lat1_col[i], lng1_col[i], lat2_col[j], lng2_col[j])
                if isinstance(lat1_col[i] / lng1_col[i] / lat2_col[j] / lng2_col[j], float)
                else None
                for i in range(len(lat1_col))] for j in range(len(lat2_col))]

def distance_to_segments_matrix(points_lat, points_lng, lat_list, lng_list):
    if len(points_lat) != len(points_lng):
        raise ValueError("Error, latitude and longitude columns have different lengths")
    else:
        return [[point_to_line_segment(points_lat[i], points_lng[i],
                                       lat_list[j], lng_list[j],
                                       lat_list[j + 1], lng_list[j + 1])
                for i in range(len(points_lat))] for j in range(len(lat_list) - 1)]

def min_row(row):
    m = min(row) 
    if m < DIST_TO_CHECK * 1000:
        return m
    else:
        return np.NaN
    
def extend_bounds(northeast_lat, northeast_lng, southwest_lat, southwest_lng, dist_to_extend=config.DIST_TO_CHECK):
    """Extend a bounding box of a gps route by defined distance in km.
    To create a bounding box for one point, pass northeast_lat, northeast_lng = southwest_lat, southwest_lng.
    """
    #Latitude: 1 deg = 110.574 km
    #Longitude: 1 deg = 111.320 * cos(latitude in radians) km
    
    new_northeast_lat = northeast_lat + dist_to_extend / 110.574
    new_northeast_lng = northeast_lng + dist_to_extend / (111.320 * cos(radians(northeast_lat)))
    new_southwest_lat = southwest_lat - dist_to_extend / 110.574
    new_southwest_lng = southwest_lng - dist_to_extend / (111.320 * cos(radians(southwest_lat)))
    
    return new_northeast_lat, new_northeast_lng, new_southwest_lat, new_southwest_lng

def equirect_proj(origin_lat, origin_lng, pt_lat, pt_lng):
    """Compute x, y distance in m using the equirectangular projection.
    Return pt_x, pt_y
    """
    pt_x = (pt_lng - first_line_pt_lng) * cos(radians(origin_lat)) * 110574
    pt_y = (pt_lat - first_line_pt_lat) * 111133
    
    return pt_x, pt_y

def point_to_line_segment(pt_lat, pt_lng, line_pt_1_lat, line_pt_1_lng, line_pt_2_lat, line_pt_2_lng):
    """Calculate the distance between a point and a line segment.

    To calculate the closest distance to a line segment, we first need to check
    if the point projects onto the line segment.  If it does, then we calculate
    the orthogonal distance from the point to the line.
    If the point does not project to the line segment, we calculate the 
    distance to both endpoints and take the shortest distance.

    :param point: Numpy array of form [x,y], describing the point.
    :type point: numpy.core.multiarray.ndarray
    :param line: list of endpoint arrays of form [P1, P2]
    :type line: list of numpy.core.multiarray.ndarray
    :return: The minimum distance to a point.
    :rtype: float
    """
    line_vector = np.array(coord_to_x_y(line_pt_1_lat, line_pt_1_lng, line_pt_2_lat, line_pt_2_lng))
    point = np.array(coord_to_x_y(line_pt_1_lat, line_pt_1_lng, pt_lat, pt_lng))
    
    # unit vector
    norm_unit_line = line_vector / np.linalg.norm(line_vector)


    diff = norm_unit_line[0] * point[0] + norm_unit_line[1] * point[1]

    #x_seg = norm_unit_line[0] * diff
    #y_seg = norm_unit_line[1] * diff

    # decide if the intersection point falls on the line segment

    #is_betw_x = lp1_x <= x_seg <= lp2_x or lp2_x <= x_seg <= lp1_x
    #is_betw_y = lp1_y <= y_seg <= lp2_y or lp2_y <= y_seg <= lp1_y
    #if is_betw_x and is_betw_y:
        #return segment_dist
    
    if (abs(norm_unit_line[0] * diff) <= abs(line_vector[0])) and (abs(norm_unit_line[1] * diff) <= abs(line_vector[1])):
        # compute the perpendicular distance to the theoretical infinite line
        return np.linalg.norm(np.cross(line_vector, - point)) / np.linalg.norm(line_vector)
    
    else:
        # if not, then return the minimum distance to the segment endpoints
        return min(np.linalg.norm(point), np.linalg.norm(line_vector - point))

def exact_dist_to_segments(row, route):
    i = int(row['closest_smoothed_pt'])
    if i == 0:
        dist_to_prev_seg = np.inf
    else:
        dist_to_prev_seg = point_to_line_segment(row['latitude'], row['longitude'],
                                                 route.lat[i - 1], route.lng[i - 1],
                                                 route.lat[i], route.lng[i])
    if i == len(smoothed_points_lat) - 1:
        dist_to_next_seg = np.inf
    else:
        dist_to_next_seg = point_to_line_segment(row['latitude'], row['longitude'], 
                                             route.lat[i], route.lng[i],
                                             route.lat[i + 1], route.lng[i + 1])
    return min(dist_to_prev_seg, dist_to_next_seg)