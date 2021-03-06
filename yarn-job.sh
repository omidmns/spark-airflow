#!/bin/bash
spark-submit \
--packages org.postgresql:postgresql:9.4.1207.jre7,org.apache.hadoop:hadoop-aws:2.7.0 \
--master yarn \
--deploy-mode cluster \
--executor-memory 2g \
--num-executors 4 \
--executors-cores 1 \
--driver-memory 4g \
--py-files deps.zip \
--verbose \
/src/cc-main_yarn.py \
--warc_paths_file_address hdfs://$1:9000/user/warc/warc.paths.2020.1.100.gz \
--geoip_table_address hdfs://$1:9000/user/geoip/GeoLite2-City.mmdb \
--jdbc_url jdbc:postgresql://$2:5432/cookie_consent \
--db_table cookie_table




