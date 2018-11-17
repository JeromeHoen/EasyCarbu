import requests
import zipfile
import io
import xml.etree.ElementTree as ET
import datetime
import pandas as pd
import numpy as np
import config
import os
import unicodedata
import csv

def refresh_all_stations():
    gas_dict = config.GAS_DICT
    day_dict = config.DAY_DICT
    data_folder = config.DATA_FOLDER

    with requests.get(config.DAY_DATA_URL) as fetch_url:
        with zipfile.ZipFile(io.BytesIO(fetch_url.content)) as zf:
            xml_file = zipfile.ZipFile.namelist(zf)[0]
            with zf.open(xml_file) as xml_file:
                parsed_xml = ET.parse(xml_file)

    cols_all_stations = ['id', 'lat', 'lng', 
                         'adresse', 'cp', 'ville',
                         'services', 'automate_h24', 'active']
    ids = []
    lat = []
    lng = []
    adresse = []
    cp = []
    ville = []
    services = []
    automate_h24 = []
    active = []

    for pdv in parsed_xml.getroot().findall('pdv'):
        cp.append(pdv.get('cp'))
        lng.append(pdv.get('longitude'))
        lat.append(pdv.get('latitude'))
        ids.append(pdv.get('id'))
        adresse.append(
            (", ").join([address.text for address in pdv.findall('adresse')])
        )
        ville.append(pdv.find('ville').text)

        if pdv.find('services') is None:
            services.append(None)
        else:
            pdv_services = [service.text for service in pdv.find('services')]
            services.append(("|").join(pdv_services))

        if "Automate CB" in pdv_services:
            automate_h24.append(True)
        else:
            horaires_node = pdv.find('horaires')
            if horaires_node is None:
                automate_h24.append(False)
            else:
                automate_h24.append(bool(horaires_node.get('automate-24-24')))

        if pdv.find("prix") is not None:
            nb_jours = 0
            if pdv.find("horaires"):
                for jour in pdv.find("horaires").findall("jour"):
                    if jour.get("ferme") == "1":
                        nb_jours += 1
                if nb_jours == 7:
                    active.append(False)
                else:
                    active.append(True)
            else:
                active.append(True)
        else:
            active.append(False)

    all_stations = pd.DataFrame(np.array([ids, lat, lng,
                                          adresse, cp, ville,
                                          services, automate_h24, active]).T, 
                                columns=cols_all_stations)

    all_stations['lat'] = round(pd.to_numeric(all_stations['lat']) / 100000, 6)
    all_stations['lng'] = round(pd.to_numeric(all_stations['lng']) / 100000, 6)

    all_stations['address'] = all_stations.adresse.apply(lambda x: x.replace(",", "").replace("-", "")) + " " + all_stations.cp + " " + all_stations.ville
    all_stations['lower_address'] = all_stations['address'].str.lower()
    
    all_stations['address'].drop_duplicates().to_csv(
        config.ADDRESSES_CSV, index=False, encoding="utf-8", header='address'
    )

    all_stations.to_csv(config.STATIONS_CSV, index=False, 
                        quoting=csv.QUOTE_NONNUMERIC, encoding="utf-8")

def refresh_geocoded_addresses():

    url = config.BAN_API_URL
    csv_file = config.ADDRESSES_CSV

    with open(csv_file, 'rb') as f:
        data = {"data": (csv_file, f)}
        r = requests.post(url, files=data)

    data = [line.split("\r") for line in r.text.replace("\r\n", "\n").split("\n")]

    with open(config.GECODED_ADDRESSES_CSV, 'w', encoding="utf-8") as myfile:
        wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
        for line in data:
            wr.writerow(line)

def refresh_BAN():

    df_BAN = pd.read_csv(config.GECODED_ADDRESSES_CSV, encoding="utf-8", dtype="str") 

    df_BAN['low_input'] = df_BAN['address'].str.lower().apply(lambda x: unicodedata.normalize('NFD', str(x)).encode('ascii', 'ignore') )
    df_BAN['low_output'] = df_BAN['result_label'].str.lower().apply(lambda x: unicodedata.normalize('NFD', str(x)).encode('ascii', 'ignore') )
    df_BAN['match'] = df_BAN['low_input'] == df_BAN['low_output']
    df_BAN.rename(columns={"latitude": "result_lat", "longitude": "result_lng"}, inplace=True)

    df_BAN["result_lat"] = pd.to_numeric(df_BAN["result_lat"])
    df_BAN["result_lng"] = pd.to_numeric(df_BAN["result_lng"])
    df_BAN["result_score"] = pd.to_numeric(df_BAN["result_score"])

    df_BAN = df_BAN.xs(["address", "result_lat", "result_lng", "match"], axis=1)
    df_BAN.to_csv(config.BAN_ADDRESSES_CSV, index=False, 
                  quoting=csv.QUOTE_NONNUMERIC, encoding="utf-8")


def refresh_superseded():

    all_stations = pd.read_csv(config.STATIONS_CSV, encoding="utf-8")
    no_duplicate = all_stations.drop_duplicates(['lat', 'lng'], keep=False) \
                               .drop_duplicates(['lower_address'], keep=False)
    duplicate = all_stations[~all_stations.index.isin(no_duplicate.index)]
    
    data = []
    for i, row in duplicate.iterrows():
        dup_row = duplicate[((duplicate['lat'] == row['lat'])
                           &
                           (duplicate['lng'] == row['lng']))
                          | (duplicate['lower_address'] == row['lower_address'])]
        
        if not dup_row[dup_row['active']].empty:
            last_active = max(dup_row[dup_row['active']].index)
            if last_active != i and row['active'] == False:
                data.append([row['id'], all_stations.loc[last_active]['id']])

    superseded_df = pd.DataFrame(data, columns=["id", "superseded_by"])
    superseded_df.to_csv(config.SUPERSEDED_CSV, index=False, 
                         quoting=csv.QUOTE_NONNUMERIC, encoding="utf-8")

def refresh_osm_xml():
    over_pass_query = """http://overpass-api.de/api/interpreter?data=
    [out:xml][timeout:500];
    area[name=France]->.boundaryarea;(
        node(area.boundaryarea)[amenity=fuel];
        way(area.boundaryarea)[amenity=fuel];
        relation(area.boundaryarea)[amenity=fuel];
    );
    out%20geom;
    """

    with requests.get(over_pass_query) as response:
        with open(config.OSM_XML, "wb") as f:
            f.write(response.content)

def refresh_osm_df():
    tag_list = ["ref:FR:prix-carburants",
                "name", "brand", "operator",
                #"address", "addr:housenumber", "addr:street", "addr:postcode", "addr:city", "is_in",
                "opening_hours"]

    parsed_xml = ET.parse(config.OSM_XML)

    data = []
    for objects in ["node", "way", "relation"]:
        for obj in parsed_xml.getroot().findall(objects):
            data_row = []
            data_row.append(objects)
            data_row.append(obj.get("id"))
            if objects == "node":
                
                data_row.append(float(obj.get("lat")))
                data_row.append(float(obj.get("lon")))
            else:
                bounds = obj.find("bounds")
                avg_lat = 0.5 * (float(bounds.get("minlat")) + float(bounds.get("maxlat")))
                avg_lng = 0.5 * (float(bounds.get("minlon")) + float(bounds.get("maxlon")))

                data_row.append(round(avg_lat, 6))
                data_row.append(round(avg_lng, 6))
                
            for tag_to_get in tag_list:
                value = None
                for tag in obj.findall("tag"):
                    if tag.get("k") == tag_to_get:
                        value = tag.get("v")
                data_row.append(value)

            data.append(data_row)
            
    df_osm = pd.DataFrame(data, columns=["osm_obj", "osm_id", "osm_lat", "osm_lng"] + ["osm_" + tag for tag in tag_list])
    df_osm.drop_duplicates("osm_ref:FR:prix-carburants", inplace=True)

    superseded_df = pd.read_csv(config.SUPERSEDED_CSV, encoding="utf-8",
                                dtype=str)
    list_dep_id = superseded_df['id'].tolist()
    list_stations_id = df_osm['osm_ref:FR:prix-carburants'].tolist()
    new_stations = []

    for i, row in df_osm.iterrows():
        station_id = row['osm_ref:FR:prix-carburants']
        if station_id in list_dep_id:
            superseded_id = superseded_df.iloc[list_dep_id.index(station_id)]['superseded_by']
            if superseded_id not in list_stations_id:
                row_new = row
                row_new['osm_ref:FR:prix-carburants'] = superseded_id
                new_stations.append(row_new)

    osm_new = pd.DataFrame(new_stations, columns=df_osm.columns)
    df_osm = pd.concat((df_osm, osm_new))

    df_osm.to_csv(config.OSM_CSV, index=False, 
                  quoting=csv.QUOTE_NONNUMERIC, encoding="utf-8")

def refresh_gas_df():

    gas_dict = config.GAS_DICT
    day_dict = config.DAY_DICT
    data_folder = config.DATA_FOLDER

    
    with requests.get(config.INSTANT_DATA_URL) as fetch_url:
        download_time = datetime.datetime.now().strftime("%Y%m%d%H%M")
        with zipfile.ZipFile(io.BytesIO(fetch_url.content)) as zf:
            xml_file = zipfile.ZipFile.namelist(zf)[0]
            with zf.open(xml_file) as xml_file:
                parsed_xml = ET.parse(xml_file)

    ids = []
    opening_info = []
    gas_prices = []

    opening_info_cols = pd.MultiIndex.from_product(
                          [['is_closed_day', 'business_hours'],
                          list(day_dict.values())])
    gas_cols = pd.MultiIndex.from_product([['gas_price', 'gas_last_update'], 
                                          list(gas_dict.values())])


    for pdv in parsed_xml.getroot().findall('pdv'):
        ids.append(pdv.get('id'))
        opening_info_to_append = [[False for i in day_dict], 
                                  [None for i in day_dict]]
        
        
        horaires_node = pdv.find('horaires')
        if horaires_node is not None:
            for jour in horaires_node.findall('jour'):
                opening_info_to_append[0][int(jour.get('id')) - 1] \
                    = bool(jour.get('ferme'))
                openings_day = []
                closings_day = []
                
                for horaire in jour.findall('horaire'):
                    openings_day.append(
                        horaire.get('ouverture').replace(".", ":")
                    )
                    closings_day.append(
                        horaire.get('fermeture').replace(".", ":")
                    )
                
                    if (openings_day is not None \
                     and closings_day is not None \
                     and len(openings_day) == len(closings_day)):
                        openings_day.sort()
                        closings_day.sort()
                        hours_to_join = [f"{opening}-{closing}" 
                                         for index, (opening, closing)
                                         in enumerate(zip(openings_day, closings_day))]
                        opening_info_to_append[1][int(jour.get('id')) - 1] \
                            = ("|").join(hours_to_join)
        
        opening_info.append(
            [item for sublist in opening_info_to_append for item in sublist]
        )
        
        gas_to_append = [[None for i in gas_dict] 
                         for j
                         in ['gas price', 'last update']]

        for gas in pdv.findall('prix'):
            gas_to_append_index = int(gas.get('id')) - 1
            gas_to_append[0][gas_to_append_index] = float(gas.get('valeur'))
            gas_to_append[1][gas_to_append_index] \
                = datetime.datetime.strptime(
                    gas.get('maj'), "%Y-%m-%d %H:%M:%S"
                )

        gas_prices.append(
            [item for sublist in gas_to_append for item in sublist]
        )
        
    df_general_info = pd.read_csv(config.STATIONS_CSV, encoding="utf-8",
                                  dtype={"id": str})
    df_general_info = df_general_info[df_general_info['id'].isin(ids)]
    df_general_info.columns = pd.MultiIndex.from_product(
                                  [df_general_info.columns, [""]]
                              )

    df_opening_info = pd.DataFrame(opening_info, 
                                   columns=opening_info_cols,
                                   index=ids)
    df_gas_prices = pd.DataFrame(gas_prices, 
                                 columns=gas_cols,
                                 index=ids)

    df = pd.concat([df_opening_info, df_gas_prices], axis=1)
    df = pd.merge(df_general_info, df, how='right', right_index=True, left_on='id')

    brand = pd.read_csv(config.BRAND_CSV, encoding="utf-8",
                                    dtype={"Identifiant": str})
    brand_cols = pd.MultiIndex.from_product([brand.columns, [""]])
    brand.columns = brand_cols

    df = pd.merge(brand, df, how='right', 
                  left_on='Identifiant',
                  right_on='id')

    osm = pd.read_csv(config.OSM_CSV, encoding="utf-8",
                      dtype={"osm_ref:FR:prix-carburants": str})
    osm_cols = pd.MultiIndex.from_product([osm.columns, [""]])
    osm.columns = osm_cols

    df = pd.merge(osm, df, how='right', 
                  left_on='osm_ref:FR:prix-carburants', 
                  right_on='id')

    latitude = []
    longitude = []
    for i in df.index:
        if df.loc[i, ('osm_id', "")] is not None:
            latitude.append(df.loc[i, ('osm_lat', "")])
            longitude.append(df.loc[i, ('osm_lng', "")])
        elif df.loc[i, ('match', "")] == True:
            latitude.append(df.loc[i, ('result_lat', "")])
            longitude.append(df.loc[i, ('result_lng', "")])
        else:
            latitude.append(df.loc[i, ('lat', "")])
            longitude.append(df.loc[i, ('lng', "")])

    df[('latitude', "")] = latitude
    df[('longitude', "")] = longitude

    cols_to_keep = ['id', 'Nom', 'Marque', 'address', 'latitude', 'longitude',
                    'services', 'automate_h24', 'is_closed_day', 'business_hours',
                    'gas_price', 'gas_last_update']

    df = df.xs(cols_to_keep, axis=1)

    today_id = datetime.datetime.today().weekday() + 1
    days_cols_to_drop = [day_name 
                         for day_id, day_name
                         in day_dict.items()
                         if day_id != today_id]
    df_day = df.drop(labels=days_cols_to_drop, level=1, axis=1)


    for gas_to_save in gas_dict.values():
        gas_cols_to_drop = [gas_name
                            for gas_name
                            in gas_dict.values()
                            if gas_name != gas_to_save]
        
        df_filtered = df_day.drop(labels=gas_cols_to_drop, level=1, axis=1)
        df_filtered.columns = df_filtered.columns.droplevel(1)

        min_price = df_filtered.describe()['gas_price'].loc['25%'] * 0.8
        max_price = df_filtered.describe()['gas_price'].loc['75%'] * 1.5

        df_filtered = df_filtered[(df_filtered['gas_price'] > min_price) &
                                  (df_filtered['gas_price'] < max_price)]
        
        df_filtered = df_filtered[df_filtered['gas_last_update']
                        .apply(lambda x: (datetime.datetime.today() - x).days) < 45]

        df_filtered = df_filtered[(~df_filtered['is_closed_day']) |
                                  (df_filtered['automate_h24'])]
        
        csv_file_name = download_time + "_" + gas_to_save
        csv_path = data_folder + "/" + csv_file_name + ".csv"
        df_filtered.to_csv(csv_path, index=False,
                           encoding="utf-8", quoting=csv.QUOTE_NONNUMERIC)



    files_list = os.listdir(data_folder)

    files_date = []
    gas_files = []

    for file in files_list:
        if file[:12].isdigit():
            files_date.append(int(file[:12]))
            gas_files.append(file)

    # remove the oldest files from the folder
    # keep the last 2 set of files
    if len(files_date) > 2 * len(gas_dict):
        date_of_files_to_remove = min(files_date)
        for file in gas_files:
            if int(file[:12]) == date_of_files_to_remove:
                os.remove(data_folder + "/" + file)

def refresh_brand_csv():
    import math
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import Select
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import NoSuchElementException
    from selenium.common.exceptions import StaleElementReferenceException

    ignored_exceptions = (NoSuchElementException, StaleElementReferenceException)

    ids = []
    names = []
    brands = []

    browser = webdriver.Chrome()
    browser.get("https://www.prix-carburants.gouv.fr/")

    dpt_select_name = "_recherche_recherchertype[departement]"
    dpt_select_box = browser.find_element_by_name(dpt_select_name)
    submit_button = browser.find_element_by_class_name("submit_recherche")

    departements = [option.get_attribute("value") 
                    for option in dpt_select_box.find_elements_by_tag_name("option")
                    if option.get_attribute("value") != ""]

    for dpt in departements:
        dpt_select_box = WebDriverWait(browser, 15, ignored_exceptions=ignored_exceptions) \
                        .until(EC.presence_of_element_located((By.NAME, dpt_select_name)))

        Select(dpt_select_box).select_by_value(dpt)
        submit_button = browser.find_element_by_class_name("submit_recherche")
        browser.execute_script("arguments[0].click();", submit_button)
        
        results = browser.find_element_by_id("sectionNombreResultats").text
        nb_results = [int(s) for s in results.split() if s.isdigit()][0]
        nb_pages = math.ceil(nb_results / 100)

        for page in range(1, nb_pages + 1):
            url = ("https://www.prix-carburants.gouv.fr/recherche/?page="
                   + str(page)
                   + "&limit=100&sort=commune&direction=asc")
            browser.get(url)

            stations = browser.find_elements_by_class_name("data  ")
            for pdv in stations:
                ids.append(pdv.get_attribute("id"))
                title = pdv.find_element_by_class_name("title").text
                name, brand = title.split(" | ")
                names.append(name)
                brands.append(brand)
        
        browser.get("https://www.prix-carburants.gouv.fr/")
        
    stations_by_brand = pd.DataFrame({"Identifiant": ids,
                                      "Marque": brands,
                                      "Nom": names})

    stations_by_brand.to_csv("stations_by_brand.csv", index=False, encoding="utf-8")

if __name__ == "__main__":
    #refresh_all_stations()
    #refresh_geocoded_addresses()
    #refresh_BAN()
    #refresh_superseded()
    #refresh_osm_xml()
    #refresh_osm_df()
    refresh_gas_df()