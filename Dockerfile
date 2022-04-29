FROM python:3

RUN pip install --no-cache-dir google-cloud-bigquery
RUN pip install --no-cache-dir numpy
RUN pip install --no-cache-dir tornado
RUN pip install --no-cache-dir matplotlib
RUN pip install --no-cache-dir google-cloud-storage

COPY tile_renderer.py .

RUN mkdir cache

CMD [ "python", "./tile_renderer.py" ]
