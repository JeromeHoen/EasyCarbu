from functions.url import unshorten_url, extract_directions, encode_url
from functions.data import MapsRoute, get_last_update
from functions import config
from functions.geo import *
import pandas as pd
import re

def get_results(
    input_url,
    gas,
    consumption_per_100km,
    liters_to_fill_up, 
    trade_off, 
    km_start = 0, 
    km_end = 200
):

    gas_dict = config.GAS_DICT
    data_folder = config.DATA_FOLDER

    gas_chosen = gas_dict[int(gas)]
    gas_consumption = consumption_per_100km / 100000
    trade_off_fn = trade_off / (15 * 60)

    regex_lat_lng = "^(\d*\.)?\d+,(\d*\.)?\d+$"

    if re.match(regex_lat_lng, input_url):
        origin = input_url
        waypoints = []
        destination = origin
        alternative_route = 0
    else:
        url = unshorten_url(input_url)
        origin, waypoints, destination, alternative_route = extract_directions(url)

    route = MapsRoute(
        origin=origin, 
        waypoints=waypoints,
        destination=destination,
        alternative_route=alternative_route,
        km_start=km_start,
        km_end=km_end
    )

    route.get_section_coord()
    route.get_full_smoothed_route()
    route.transform_coord_to_smoothed()
    route.get_bounds()
    route.extend_bounds()

    last_update = get_last_update(data_folder)

    csv_name = data_folder + "/" + last_update + "_" + gas_chosen + ".csv"

    df_filtered = pd.read_csv(csv_name)

    df_filtered = df_filtered[(df_filtered['latitude'] < route.NE_lat) & 
                              (df_filtered['latitude'] > route.SW_lat) & 
                              (df_filtered['longitude'] < route.NE_lng) &
                              (df_filtered['longitude'] > route.SW_lng)]

    dist_mat = pd.DataFrame(distance_matrix(route.lat,
                                            route.lng,
                                            df_filtered['latitude'].tolist(),
                                            df_filtered['longitude'].tolist()),
                            index=df_filtered.index)

    dist_mat['closest_pt'] = dist_mat.idxmin(axis=1)
    dist_mat['latitude'] = df_filtered['latitude']
    dist_mat['longitude'] = df_filtered['longitude']

    df_filtered['fill_up_cost'] = df_filtered['gas_price'] * liters_to_fill_up

    min_detour_dist =[]
    for index, row in dist_mat.iterrows():
        if len(route.lat) > 1 and len(route.lng) > 1:
            i = int(row['closest_pt'])
            if i == 0:
                dist_to_prev_seg = np.inf
            else:
                dist_to_prev_seg = point_to_line_segment(row['latitude'],
                                                         row['longitude'],
                                                         route.lat[i - 1],
                                                         route.lng[i - 1],
                                                         route.lat[i],
                                                         route.lng[i])
            if i == len(route.lat) - 1:
                dist_to_next_seg = np.inf
            else:
                dist_to_next_seg = point_to_line_segment(row['latitude'],
                                                         row['longitude'], 
                                                         route.lat[i],
                                                         route.lng[i],
                                                         route.lat[i + 1],
                                                         route.lng[i + 1])

            min_detour_dist.append(2 * min(dist_to_prev_seg, dist_to_next_seg))
        else:
            min_detour_dist.append(2 * exact_distance(row['latitude'],
                                                      row['longitude'],
                                                      route.lat[0],
                                                      route.lng[0]))

    df_filtered['min_detour_dist'] = min_detour_dist

    df_filtered = df_filtered[pd.notna(df_filtered['min_detour_dist'])]

    df_filtered['min_detour_cost'] = (gas_consumption
                                      * df_filtered['gas_price']
                                      * df_filtered['min_detour_dist'])
    df_filtered['min_detour_duration'] = (df_filtered['min_detour_dist']
                                          / config.MAX_SPEED)
    df_filtered['min_trade_off_cost'] = \
        (df_filtered['fill_up_cost']
         + df_filtered['min_detour_cost']
         + df_filtered['min_detour_duration'] * trade_off_fn)

    df_filtered = df_filtered.nsmallest(n=10, columns='min_trade_off_cost')

    df_trade_off = pd.DataFrame(columns=['detour_distance',
                                         'detour_duration',
                                         'detour_speed',
                                         'revised_detour_cost',
                                         'revised_trade_off_cost',
                                         'output_url'])

    for index, row in df_filtered.iterrows():


        waypoint = (df_filtered['Nom'].loc[index] + ", "
                    + str(df_filtered['address'].loc[index]))

        result_route = MapsRoute(origin=origin,
                                 waypoints=waypoint,
                                 destination=destination,
                                 alternative_route=0)
        
        detour_distance = result_route.distance - route.distance    
        detour_duration = result_route.duration - route.duration
        if detour_duration == 0:
            detour_speed = 0
        else:
            detour_speed = detour_distance / detour_duration
        
        revised_detour_cost = (gas_consumption
                               * df_filtered['gas_price'].loc[index]
                               * detour_distance)
            
        revised_trade_off_cost = (df_filtered['fill_up_cost'].loc[index]
                                  + revised_detour_cost
                                  + detour_duration * trade_off_fn)
        
        output_url = encode_url(origin=result_route.origin,
                                waypoints=result_route.waypoints,
                                destination=result_route.destination)

        df_trade_off.loc[index] = [detour_distance,
                                   detour_duration,
                                   detour_speed,
                                   revised_detour_cost,
                                   revised_trade_off_cost,
                                   output_url]

        if min(df_trade_off['revised_trade_off_cost']) \
           < min(df_filtered[~df_filtered.index.isin(df_trade_off.index)]['min_trade_off_cost']):
            break


    df_results = pd.concat(
        (df_filtered, df_trade_off), join="outer", axis=1
    ).sort_values(by=['revised_trade_off_cost', 'min_trade_off_cost']) 

    with pd.option_context('display.max_colwidth', -1):
        return df_results.to_html()

        