import tornado.ioloop
import tornado.web
from google.cloud import bigquery
import geopy.distance
import json
import math


# https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Lon..2Flat._to_tile_numbers_2
def num2deg(xtile, ytile, zoom):
  n = 2.0 ** zoom
  lon_deg = xtile / n * 360.0 - 180.0
  lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
  lat_deg = math.degrees(lat_rad)
  return (lat_deg, lon_deg)


def get_all_articles_for_tile(xtile, ytile, zoom):
    if zoom < 9:
        return []
    (nw_lat, nw_lon) = num2deg(xtile, ytile, zoom)
    (se_lat, se_lon) = num2deg(xtile + 1, ytile + 1, zoom)
    print(f"{nw_lat}-{se_lat}, {nw_lon}-{se_lon}")
    query="""
        select lat, lon, id, name
        from (wikipedia.geo left outer join wikipedia.article_index
          USING (id))
        where lat < @nw_lat and lat > @se_lat 
        and lon > @nw_lon and lon < @se_lon
    """
    client=bigquery.Client()
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("nw_lat", "FLOAT", nw_lat),
            bigquery.ScalarQueryParameter("se_lat", "FLOAT", se_lat),
            bigquery.ScalarQueryParameter("nw_lon", "FLOAT", nw_lon),
            bigquery.ScalarQueryParameter("se_lon", "FLOAT", se_lon),
        ]
    )
    print(query)
    query_job = client.query(query, job_config=job_config)
    articles = []
    for q in query_job:
        articles.append({
            "lat": q[0],
            "lon": q[1],
            "id": q[2],
            "name": q[3],
        })
    return articles

def get_near_articles(lat, lon):
    client = bigquery.Client()
    max_dist = 0.1
    query = """
        select lat, lon, id, name
        from (wikipedia.geo left outer join wikipedia.article_index
          USING (id))
        WHERE abs(lat - @lat) < @max_dist
        AND abs(lon - @lon) < @max_dist;
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("lat", "FLOAT", lat),
            bigquery.ScalarQueryParameter("lon", "FLOAT", lon),
            bigquery.ScalarQueryParameter("max_dist", "FLOAT", max_dist)
        ]
    )
    print(query)
    query_job = client.query(query, job_config=job_config)  # Make an API request.
    return query_job

class ArticleHandler(tornado.web.RequestHandler):
    
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.set_header("Access-Control-Allow-Headers", "*") 


    def get(self):
        get_tile_articles = self.get_argument('tile', default=False)
        if get_tile_articles:
            x = int(self.get_argument("x"))
            y = int(self.get_argument("y"))
            z = int(self.get_argument("z"))
            self.write(json.dumps(get_all_articles_for_tile(x,y,z)))
        else:
            lat = self.get_argument("lat")
            lon = self.get_argument("lon")
            articles = get_near_articles(lat, lon)
        
            nearest_article = None
            nearest_distance = None
            for article in articles:
                (a_lat, a_lon, idx, name) = article
                distance = geopy.distance.geodesic((lat, lon), (a_lat, a_lon))
                if nearest_article is None or distance < nearest_distance:
                    nearest_article = {
                        "latitude": a_lat,
                        "longitude": a_lon,
                        "id": idx,
                        "name": name,
                    }
                    nearest_distance = distance
            self.write(json.dumps(nearest_article))
        
    def options(self, *args):
        self.set_status(204)
        self.finish()

def make_app():
    return tornado.web.Application([
        (r"/article", ArticleHandler),
    ])

if __name__ == "__main__":
    app = make_app()
    app.listen(8889)
    tornado.ioloop.IOLoop.current().start()
