"""
spark job to investigate common crawl dataset
"""
import argparse
import time
import sys
import re
import os
import warc
import boto
from boto.s3.key import Key
from gzipstream import GzipStreamFile
from pyspark import SparkConf, SparkContext, SparkFiles
from pyspark.sql import  SparkSession  #SQLContext,
try:
    # Python2
    from urlparse import urljoin, urlparse
except ImportError:
    # Python3
    from urllib.parse import urljoin, urlparse
#%%
class cc_main(object):
    '''
    main class to run cookie consent job
    '''

    name = 'cc_job'
    def process_paths(self, id_, paths):
        '''
        connect to s3 and get the data
        '''
           
        conn = boto.connect_s3(anon=True, host='s3.amazonaws.com')
        bucket = conn.get_bucket('commoncrawl')
        
        for uri in paths:
            key_ = Key(bucket, uri)
            archive_iterator = warc.WARCFile(fileobj=GzipStreamFile(key_))
            for record in archive_iterator:
                for res in self.process_record(record):
                    yield res           
        
    def process_record(self, record):
        '''
        process the warc records
        '''
        html_cookie_tag_pattern = re.compile(
        b'<*(cookieconsent|cookie policy|privacy policy|cookie consent|cookiepolicy|privacypolicy|privacy act+)')
        if record['WARC-Type'] == 'response':
            try:
                ip_address= record['WARC-IP-Address']
                url= record['WARC-Target-URI']   

                if not ip_address or ip_address == '':
                 ip_address = 'None'
                host_name = 'None'
                if url:
                    try:
                       host_name = urlparse(url).hostname
                    except:
                       pass
    
            except KeyError:
               host_name = 'None'
               ip_address = 'None'
               
            data = record.payload.read()
            
            cookie_consent = html_cookie_tag_pattern.search(data)
            if cookie_consent:
                cookie_consent_name = cookie_consent.group(0)
            else:
                cookie_consent_name = 'None' 
            
            yield (host_name, ip_address, cookie_consent_name), 1
                   
    def geoip(self, iter):
        '''
        geolocation lookup api
        '''
        from geoip2 import database

        def ip2country(ip):
            try:
               country = reader.city(ip).country.name
                                                               
            except:
                country = 'not found'
            return country
    
        reader = database.Reader(SparkFiles.get("GeoLite2-City.mmdb"))

        return [(ip[0],ip2country(ip[1]),ip[2],ip[3]) for ip in iter]
      
    def run_job(self):
        '''
        main spark job
        '''
        start_time = time.time()
        
        parser = argparse.ArgumentParser(description='cookie_consent python module')
        parser.add_argument('--warc_paths_file_address',
                        type=str,
                        help='hdfs/s3 address for warc.paths.gz file')
        parser.add_argument('--geoip_table_address',
                        type=str,
                        help='hdfs/s3 address for geoip look-up table')
        parser.add_argument('--db_table',
                        default="temp",
                        type=str,
                        help='Database table name (default=temp)')
        parser.add_argument('--jdbc_url',
                        type=str,
                        help='Postgres Database url, pointing to database location')

        parsed_args = parser.parse_args()
        db_table = parsed_args.db_table
        warc_paths_file_address = parsed_args.warc_paths_file_address
        geoip_table_address = parsed_args.geoip_table_address
        jdbc_url = parsed_args.jdbc_url

        conf = SparkConf()
        sc = SparkContext(
                    appName="cookie_consent",
                    conf=conf)
        # geoip lookup tabel - dataset
        geoDBpath = geoip_table_address
        # add geoip table to spark context to be distributed 
        sc.addFile(geoDBpath) 
        # get the input file from console
        files = sc.textFile(warc_paths_file_address,minPartitions=400) 
      
        # main spark job
        rdd = files.mapPartitionsWithIndex(self.process_paths)\
        .reduceByKey(lambda x, y: x + y)\
        .map(lambda x: (x[0][0],x[0][1],x[0][2],x[1]))\
        .filter(lambda x: x[1] != 'None')\
        .mapPartitions(self.geoip)
     
        #%%
        # write the result in postgresql
        spark = SparkSession(sc)
        rdd_df = rdd.toDF()
        rdd_df = rdd_df.selectExpr("_1 as host_name",                                   
                                   "_2 as country_name",
                                   "_3 as cookie_keyword",
                                   "_4 as page_count")
               
        # retrieve postgresql credentials from environment variables
        jdbc_password = spark.conf.get("spark.yarn.appMasterEnv.POSTGRES_PASSWORD") #os.environ['POSTGRES_PASSWORD']
        jdbc_user = spark.conf.get("spark.yarn.appMasterEnv.POSTGRES_USER") #os.environ['POSTGRES_USER']
        mode = "append"
        url = jdbc_url
        properties = {"user": jdbc_user, "password": jdbc_password,
                    "driver": "org.postgresql.Driver"}
        
        # write to sql
        rdd_df.write.jdbc(url=url, table=db_table,
                           mode=mode, properties=properties) #option("numPartitions", 100)
       
        # calculate the run time
        run_time = time.time() - start_time
        print("Total script run time: {}".format(run_time))
  
#%%
if __name__ == "__main__":
   job = cc_main() 
   job.run_job()
