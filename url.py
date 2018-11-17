import requests
from urllib.parse import unquote_plus, quote_plus, urlencode

def unshorten_url(url):
    session = requests.Session()  # so connections are recycled
    resp = session.head(url, allow_redirects=True)
    return resp.url

def extract_directions(url):
    """Extract parameters from Google Maps direction URL. 
    
    Return:
    
    origin -- formated address or coordinates 
    wapypoints -- list of waypoints in the order 
    destination -- formated address or coordinates
    alternative_route -- int, 0 if it's the default route, 1 or 2 if it's an alternative
    """
    if "maps/dir/" in url:
        _parameters_ = url.split("maps/dir/")[1]
        
        if "/@" in _parameters_:
            _route_ = _parameters_.split("/@")[0]
        else:
            _route_ = _parameters_.rstrip('/')
                        
        _route_ = _route_.split("/")
        _origin_ = unquote_plus(_route_[0])
        _destination_ = unquote_plus(_route_[-1])
        _waypoints_ = [unquote_plus(wp) for wp in _route_[1:-1]]
        
        if "!3e0" in url:
            _alternative_route_ = int(url[-1])
        else:
            _alternative_route_ = 0
    
        return _origin_, _waypoints_, _destination_, _alternative_route_
    else:
        raise ValueError("Url is not a Google Maps direction")

def encode_url(origin, waypoints, destination):

    param_dict = {
        "origin": origin,
        "waypoints": waypoints,
        "destination": destination
    }

    if isinstance(waypoints, list):
        param_dict['waypoints'] = ("|").join(waypoints)

    base_url = "https://www.google.com/maps/dir/?api=1&"
    output_url = (base_url
                  + urlencode(param_dict,
                              quote_via=quote_plus,
                              doseq=True,
                              safe=',')
                  )

    #return f'<a target="_blank" href="{output_url}">Lien Google Maps</a>'
    return output_url