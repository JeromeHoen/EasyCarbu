GOOGLE_API_KEY = "AIzaSyA02P9NLGJjaw5z-0nPFcN250jTiLcyQRU"
DIST_TO_CHECK = 30
MAX_SPEED = 60 / 3.6
INSTANT_DATA_URL = "https://donnees.roulez-eco.fr/opendata/instantane"
DAY_DATA_URL = "https://donnees.roulez-eco.fr/opendata/jour"
SHORTENED_GOOGLE_URL = "https://goo.gl/"
STATIONS_BY_BRAND_URL = "https://public.opendatasoft.com/explore/dataset/prix_des_carburants_stations/download/?format=csv&timezone=Europe/Berlin&use_labels_for_header=true"
BAN_API_URL = "https://api-adresse.data.gouv.fr/search/csv/"
DATA_FOLDER = "C:/Users/Jerome/Dropbox/Python/Station essence/station_webapp/files"

STATIONS_CSV = DATA_FOLDER + "/" + "all_stations.csv"
ADDRESSES_CSV = DATA_FOLDER + "/" + "addresses.csv"
GECODED_ADDRESSES_CSV = DATA_FOLDER + "/" + "addresses_geocoded.csv"
BAN_ADDRESSES_CSV = DATA_FOLDER + "/" + "addresses_BAN.csv"
SUPERSEDED_CSV = DATA_FOLDER + "/" + "superseded.csv"
BRAND_CSV = DATA_FOLDER + "/" + "stations_by_brand.csv"
OSM_XML = DATA_FOLDER + "/" + "osm_stations.xml"
OSM_CSV = DATA_FOLDER + "/" + "osm.csv"
DAY_DICT = {1: 'Lun', 2:'Mar', 3: 'Mer', 4: 'Jeu', 5: 'Ven', 6: 'Sam', 7: 'Dim'}
GAS_DICT = {1: 'Gazole', 2: 'SP95', 3: 'E85', 4: 'GPLc', 5: 'E10', 6: 'SP98'}