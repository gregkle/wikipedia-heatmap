FROM python:3

RUN pip install --no-cache-dir google-cloud-bigquery
RUN pip install --no-cache-dir tornado
RUN pip install --no-cache-dir geopy

COPY article_geo_query.py .

RUN mkdir cache

CMD [ "python", "./article_geo_query.py" ]
