FROM postgres:16

# The official image runs these scripts only while initializing a fresh named
# volume, which makes creation of the isolated pytest database idempotent.
COPY init/ /docker-entrypoint-initdb.d/
