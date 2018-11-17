from . import config
import googlemaps
import polyline
from .geo import *
import numpy as np
import pandas as pd
import datetime
import os

def get_last_update(directory):
    
    files_dir = os.listdir(directory)

    # Get the most recent df saved in csv files
    # df file names start with the date in format YYYYMMDDhhmm
    files_date = []
    for file in files_dir:
        try:
            files_date.append(int(file[:12]))
        except ValueError:
            continue
        
    return str(max(files_date)) 


class MapsRoute:

    def __init__(self, origin, waypoints, destination, alternative_route,
                 km_start=0, km_end=10000):
        self.origin = origin
        self.waypoints = waypoints
        self.destination = destination
        self.alternative_route = alternative_route
        self.km_start = km_start
        self.km_end = km_end

        if self.destination == self.origin and waypoints is None:
            self.parsed = None
            self.duration = 0
            self.distance = 0
        else:
            gmaps = googlemaps.Client(key=config.GOOGLE_API_KEY)
                
            api_result = gmaps.directions(origin=origin,
                                          waypoints=waypoints,
                                          destination=destination,
                                          alternatives=(alternative_route > 0))

            self.parsed = api_result[alternative_route]
            self.duration = sum([leg['duration']['value']
                                 for leg
                                 in self.parsed['legs']])
            self.distance = sum([leg['distance']['value']
                                 for leg
                                 in self.parsed['legs']])

    def get_section_coord(self):

        if self.destination == self.origin:
            self.lat = [float(self.origin.split(",")[0])]
            self.lng = [float(self.origin.split(",")[1])]
        else:
            lat = []
            lng = []
            distance_to_next_pt = []

            first_leg = True

            for leg in self.parsed['legs']:
                if first_leg:
                    lat.append(leg['start_location']['lat'])
                    lng.append(leg['start_location']['lng'])
                    first_leg = False
                for step in leg['steps']:
                    first_tuple = True
                    for tup in polyline.decode(step['polyline']['points']):
                        if first_tuple:
                            first_tuple = False
                        else:
                            lat.append(tup[0])
                            lng.append(tup[1])
                            distance_to_next_pt.append(exact_distance(lat[-2],
                                                                      lng[-2],
                                                                      lat[-1],
                                                                      lng[-1]))

                    lat.append(step['end_location']['lat'])
                    lng.append(step['end_location']['lng'])
                    distance_to_next_pt.append(exact_distance(lat[-2], 
                                                              lng[-2],
                                                              lat[-1],
                                                              lng[-1]))
                    
            distance_to_next_pt.insert(0, 0)

            cumul_dist = np.cumsum(distance_to_next_pt)

            self.lat = [lat_pt 
                        for i, lat_pt 
                        in enumerate(lat)
                        if (cumul_dist[i] >= self.km_start * 1000 
                        and cumul_dist[i] <= self.km_end * 1000)]

            self.lng = [lng_pt 
                        for i, lng_pt 
                        in enumerate(lng)
                        if (cumul_dist[i] >= self.km_start * 1000 
                        and cumul_dist[i] <= self.km_end * 1000)]

    def get_full_smoothed_route(self):
        if len(self.lat) > 1 and len(self.lat) > 1:
            smoothed_polyline = self.parsed['overview_polyline']['points']
            self.smoothed_points_lat, self.smoothed_points_lng = \
                list(zip(*polyline.decode(smoothed_polyline)))
        else:
            self.smoothed_points_lat = self.lat
            self.smoothed_points_lng = self.lng

    def transform_coord_to_smoothed(self):
        if len(self.lat) > 1 and len(self.lat) > 1:
            start = np.argmin([point_to_line_segment(self.lat[0],
                                                     self.lng[0],
                                                     self.smoothed_points_lat[i],
                                                     self.smoothed_points_lng[i],
                                                     self.smoothed_points_lat[i + 1],
                                                     self.smoothed_points_lng[i + 1])
                               for i in range(len(self.smoothed_points_lat) - 1)])

            end = np.argmin([point_to_line_segment(self.lat[-1],
                                                   self.lng[-1],
                                                   self.smoothed_points_lat[i],
                                                   self.smoothed_points_lng[i],
                                                   self.smoothed_points_lat[i + 1],
                                                   self.smoothed_points_lng[i + 1])
                              for i in range(len(self.smoothed_points_lat) - 1)])

            self.lat = ([self.lat[0]]
                        + list(self.smoothed_points_lat[start + 1 : end + 1])
                        + [self.lat[-1]])

            self.lng = ([self.lng[0]] 
                        + list(self.smoothed_points_lng[start + 1 : end + 1])
                        + [self.lng[-1]])

    def get_bounds(self):
        self.NE_lat = max(self.lat)
        self.NE_lng = max(self.lng)
        self.SW_lat = min(self.lat)
        self.SW_lng = min(self.lng)

    def extend_bounds(self, dist_to_extend=float(config.DIST_TO_CHECK)):
        """Extend a bounding box of a gps route by a defined distance in km."""
        #Latitude: 1 deg = 110.574 km
        #Longitude: 1 deg = 111.320 * cos(latitude in radians) km
        
        self.NE_lat = self.NE_lat + dist_to_extend / 110.574
        self.NE_lng = self.NE_lng + dist_to_extend / (111.320 * cos(radians(self.NE_lat)))
        self.SW_lat = self.SW_lat - dist_to_extend / 110.574
        self.SW_lng = self.SW_lng - dist_to_extend / (111.320 * cos(radians(self.SW_lat)))