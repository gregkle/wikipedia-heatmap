import math
import re
from google.cloud import bigquery
from google.cloud import storage
import numpy as np
import tornado.ioloop
import tornado.web
import os


import matplotlib.pyplot as plt


# tiles are 256x256

# https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Lon..2Flat._to_tile_numbers_2
def num2deg(xtile, ytile, zoom):
  n = 2.0 ** zoom
  lon_deg = xtile / n * 360.0 - 180.0
  lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
  lat_deg = math.degrees(lat_rad)
  return (lat_deg, lon_deg)

def deg2num(lat_deg, lon_deg, zoom):
  lat_rad = math.radians(lat_deg)
  n = 2.0 ** zoom
  xtile = ((lon_deg + 180.0) / 360.0 * n)
  ytile = ((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
  return (xtile, ytile)

def get_all_articles(xtile, ytile, zoom):
    (nw_lat, nw_lon) = num2deg(xtile, ytile, zoom)
    (se_lat, se_lon) = num2deg(xtile + 1, ytile + 1, zoom)
    print(f"{nw_lat}-{se_lat}, {nw_lon}-{se_lon}")
    query=f"select lat, lon, id from wikipedia.geo where lat < {nw_lat} and lat > {se_lat} and lon > {nw_lon} and lon < {se_lon}"
    print(query)
    client=bigquery.Client()
    q = client.query(query)
    return q
    #for res in q:
    # 	print(res[:3])
    	
def render_tile(zoom, x_tile, y_tile):
    articles = get_all_articles(x_tile, y_tile, zoom)
    (nw_lat, nw_lon) = num2deg(x_tile, y_tile, zoom)
    (se_lat, se_lon) = num2deg(x_tile + 1, y_tile + 1, zoom)
    lat_range = abs(nw_lat - se_lat)
    lon_range = abs(nw_lon - se_lon)
    tile = np.zeros((256, 256), dtype='double')
    total_articles = 0
    for article in articles:
        lat = article[0]
        lon = article[1]

        (tile_x, tile_y) = deg2num(lat, lon, zoom)
        tile_x = tile_x - int(tile_x)
        tile_y = tile_y - int(tile_y)
        tile_x *= 256
        tile_y *= 256

        tile[int(tile_y)][int(tile_x)] += 1
        total_articles += 1
    print(f"{total_articles} in tile")
    tile += 0.01
    tile = np.log(tile)
    fig = plt.figure(figsize=(1, 1), dpi=256)
    ax = plt.Axes(fig, [0., 0., 1., 1.])
    ax.set_axis_off()
    ax.margins(x=0, y=0, tight=True)
    fig.add_axes(ax)
    plt.set_cmap('viridis')
    ax.imshow(tile, aspect='equal')
    fname = file_name(zoom, x_tile, y_tile)
    plt.savefig(fname)
    plt.close(fig)
    return fname

def file_name(z, x, y):
  return f"cache/{z}T{x}T{y}.png"


class MainHandler(tornado.web.RequestHandler):
    
    def get(self, args):
        should_cache = True
        #self.write(f"Hello, world {self.request.uri}  - {args}")
        r = re.match("(\d+)/(\d+)/(\d+)", args)
        (zoom, x, y) = (int(r.group(1)), int(r.group(2)), int(r.group(3)))
        fname = file_name(zoom, x, y)
        
        storage_client = storage.Client()
        bucket_name = 'wiki-tile-cache-reproject'
        bucket = storage_client.bucket(bucket_name)
        blob = storage.Blob(bucket=bucket, name=fname)
        if blob.exists(storage_client) and should_cache:
           # cache hit
           blob.download_to_filename(fname)
           print("cache hit")
        else:
           print("cache miss")
           fname = render_tile(zoom, x, y)
           if should_cache:
            blob.upload_from_filename(fname)
        with open(fname, "rb") as source_file:
            self.write(source_file.read())
        self.set_header("Content-type",  "image/png")
        os.remove(fname)

        
def make_app():
    return tornado.web.Application([
        (r"/tile/(.*)", MainHandler),
    ])

if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()

