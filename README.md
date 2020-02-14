# Cookie Consent
** Who complies with Privacy Act **

## Motivation
* The General Data Protection Regulation (GDPR) was adopted by European countires in 2016 and became enforceable on May 25, 2018. 
* According to this law, companies must infrom the customers what data of theirs has been collected, delete it and stop selling it if the customer requests. 
* The fine for GDPR violators could by up to €20 million in some cases.
* Similar regulations have been adapted by other countries outside EU, including Chile, Japan, Brazil, South Korea, Argentina and Kenya. 
* The California Consumer Privacy Act (CCPA), adopted on 28 June 2018, has a lot of similarities with GDPR. It became effective on Jan 1st, 2020.
* The fines for CCPA violetors could add up — $7,500 per violation if intentional, $2,500 for those lacking intent and $750 per affected user in civil damages.

## Approach
Cookie consent pipeline first catagorizes the webpages collected by Common Crawl project ( > 2.5 bilion webpages, > 47 TB data) based on their host IP addresses then check if the websites are comply with privacy act by searching certain keywords such as `cookie consent, cookie policy, privacy policy, privacy act and etc`. It also counts the number of pages for each website as an index of their sizes. 

## Pipeline

<img src="./image/cc-pipeline.png" alt="cc Pipeline" width="800"/><br> 

## Data
Common Crawl dataset is used for this project ([Common Crawl database](https://commoncrawl.org/)). Common Crawl project crawls the webpages globaly every month. The data are stored on an AWS S3 database.

## Results

Following is an example of the output:

<img src="./image/cc_result.png" width="800"/><br>  


## Configuration
The cookie consent is configured and run on AWS provisioned resouces but it can be run on any resource that supposts the applications used in the pipeline.

Spark cluster can be set up using AWS EMR or [Insight Data Science Pegasus package](https://github.com/InsightDataScience/pegasus). AWS RDS can be used to set up PostgreSQL. It also can be set up on an EC2 instance using instruction provided [here](#postgres).

Setting up the airflow and also the edge node can be skipped and the application can be run on the master node of the cluster using `spark-job.sh` script.

The airflow server, postgres database and hadoop and spark edge nodes can be set up using a pre-baked [Docker image](#docker).

Following, steps are explained to set up the pipeline using `AWS EMR cluster` or `pegasus cluster`.

### AWS EMR cluster

* [Bootstrap the cluster](#bootstrap)
* Set up AWS EMR running Spark
* Set up AWS RDS running PostgreSQL
* [Set up apache Airflow](#airflow)
* [Configure hadoop and spark edge node](#edge)
* [Create and put input data onto HDFS](#input)
* [Download and put Geoip2 table onto HDFS](#geoip2)
* [Submit spark job](#submit)

### Pegasus cluster
* Download and install Pegasus from [here](https://github.com/InsightDataScience/pegasus).
* ‌[Bootstrap the cluster](#bootstrap)
* Set up a spark cluster using the example script provided by the Pegasus at `$PEGASUS_HOME/example/spark`
* [Set up PostgreSQL](#postgres)
* [Set up apache airflow](#airflow)
* [Configure hadoop and spark edge node](#edge)
* [Create and put input data onto HDFS](#input)
* [Download and put Geoip2 table onto HDFS](#geoip2)
* [Submit spark job](#submit)

<a name="bootstrap" />

### 1. Bootstrap the cluster

#### 1.1. EMR

Put `cc_bootstrap_emr.sh` onto AWS S3 and add it during setting up the EMR cluster.

#### 1.2. Pegasus

Before setting up the spark cluster using Pegasus package, edit `$PEGASUS_HOME/install/environment/install_env.sh` and add the lines in `cc_bootstrap_emr.sh` into this file. So, during setting up the environment, the libs are installed on the nodes. 

The dependencies can also be installed after setting up the cluster using `install_bootstrap.sh`:
```bash
$ ./install_bootstrap.sh cluster-name
```

change `cluster-name` with the name of your cluster (e.g. `spark-cluster`)

<a name="postgres" />

### 2. Setting up PostgreSQL

Install PostgreSQL:

```bash
$ sudo apt-get install postgresql postgresql-contrib
```
Update `pg_hba.conf` most likely at `/etc/postgresql/10/main/pg_hba.conf` which will read something like this, by default:

```
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# "local" is for Unix domain socket connections only
local   all             all                                     ident
# IPv4 local connections:
host    all             all             127.0.0.1/32            ident
# IPv6 local connections:
host    all             all             ::1/128                 ident
```
to read this:
```
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# "local" is for Unix domain socket connections only
local   all             all                                     trust
# IPv4 local connections:
host    all             postgres_user   0.0.0.0/0               md5
# IPv6 local connections:
host    all             all             ::1/128                 md5
```
Update `postgresql.conf` most likely at `/etc/postgresql/10/main/postgresql.conf` and uncomment line 59:

```
#listen_addresses = 'localhost'          # what IP address(es) to listen on;
```

Update the line to enable connections from any IP address:

```
listen_addresses='*'
```

Uncomment line 63:

```bash
#port = 5432
```

so it reads as:

```bash
port = 5432
```

Make postgres start at boot:
```bash
$ sudo systemctl enable postgresql
```

Restart PostgreSQL:
```bash
$ sudo /etc/init.d/postgresql restart
```

Log into PostgreSQL:
```bash
$ sudo su - postgres
$ psql
```

Add a password for your PostgreSQL admin:
 ```sql
ALTER USER postgres WITH PASSWORD 'password';
```

Update your Postgres user credentials (Superusers will be able to do anything (these are really admins)):

```sql
CREATE USER postgres_user SUPERUSER;
ALTER USER postgres_user WITH PASSWORD 'postgres_password';
```

Create databases:
```sql
CREATE DATABASE airflow;
CREATE DATABASE cookie_consent;
\q
```
<a name="airflow" />

### 3. Setting up Airflow
Install airflow on EC2 instance with ubuntu 18.04.

To connect airflow with postgres the `psycopg2` is requiered.
```bash
$ sudo apt-get install libpq-dev
$ pip install psycopg2
```
Edit and set up `AIRFLOW_HOME` in `$HOME/.bashrc` file:
```bash
export AIRFLOW_HOME=~/airflow
```

Run following commands:
```bash
$ sudo add-apt-repository universe
$ sudo apt-get update
$ sudo apt install python-pip
$ sudo pip install --upgrade pip

$ sudo apt-get install libmysqlclient-dev
$ sudo apt-get install libssl-dev
$ sudo apt-get install libkrb5-dev
$ sudo apt-get install libsasl2-dev
$ sudo pip install apache-airflow
$ airflow initdb
```
Edit airflow configuration file in airflow folder `$AIRFLOW_HOME/airflow.cfg` to connect airflow to postgres.

Comment line:
```
#sql_alchemy_conn = sqlite:////home/ubuntu/airflow/airflow.db
```
Add:
```
sql_alchemy_conn = postgresql://postgres_user:postgres_password@localhost/airflow
```
#### 3.1. Airflow - DAG

Airflow dag that is used for this project (`spark-dag.py`) can be found in `/airflow/dags` folder.
Number of tasks in `spark_operator` dag depends on the number of path files generated in [input data](#input) section. 

#### 3.2. Airflow - last task

Last task in `spark_operator` dag runs a bash script (`stop_cluster.sh`) which turns down the cluster no matter all previous tasks were `SUCCESS` or `FAIL`. Whenever one of the tasks is failed the rest would not be run and the last task would turn the cluster down to prevent wasting money. 

#### 3.3. Airflow - example

Following figure shows the airflow `tree view` for the `saprk_operator` dag:
<img src="./image/airflow_tree_view.png" width="800"/><br>  

<a name="edge" />

### 4. Setting up Spark and Hadoop edge node

To submit and monitor the spark job, airflow needs to have access to hadoop and spark bineraies. The EC2 instance with airflow and postgres should be configured to serve as spark and haddop edge node. The same version of Hadoop and Spark as the master node of the cluster should be installed on edge node. The Hadoop and Spark configuration folders should be copied and used by the edge node. [EMR remote cluster](https://aws.amazon.com/premiumsupport/knowledge-center/emr-submit-spark-job-remote-cluster/) explains how this procedure should be done for EMR cluster. The same method can be used for costumized cluster configured using Pegasus or other applications.

#### 4.1. Spark - log

Edit and add following lines to the spark configuration files (master node only) at `$SPAKR_HOME/conf/Spark-defaullts.conf` to save the spark logs.
```
spark.yarn.am.waitTime            3600s
spark.eventLog.enabled            true
spark.eventLog.dir                hdfs://master_node_private_ip:9000/app-logs
spark.history.provider            org.apache.spark.deploy.history.FsHistoryProvider
spark.history.fs.logDirectory     hdfs://master_node_private_ip:9000/app-logs
spark.history.fs.update.interval  10s
spark.history.ui.port             18080
```
Create `app-logs` folder on the hdfs:

```bash
$ hdfs dfs -mkdir /app-logs
```
Spark application logs are saved on `hdfs://app-logs/`.

#### 4.2. Yarn - postgres credentials

Edit and add following lines to the spark configuration file at `$SPAKR_HOME/conf/Spark-defaullts.conf` to pass the postgres credentials as environment variables to yarn application.
```    
spark.yarn.appMasterEnv.POSTGRES_PASSWORD   postgres_password
spark.yarn.appMasterEnv.POSTGRES_USER       postgres_user
spark.yarn.appMasterEnv.POSTGRES_LOCATION   postgres_private_ip
```
`postgres_private_ip` is the private ip address of the postgres server (EC2).

#### 4.3. Yarn - setup dependencies

The dependencies for this application should be zipped in a file and pass to the yarn application using `--py-file` option.

Install these libs first on master node (skip this part if dependencies are already installed in bootstrap mode):
```bash
$ sudo apt-get install -y git
$ sudo apt-get install libgeoip-dev 
$ sudo pip install geoip2
$ sudo pip install boto
$ sudo pip install warc
$ sudo pip install https://github.com/commoncrawl/gzipstream/archive/master.zip
```
then (it is necessary that `deps.zip` is generated and passed to spark application for yarn `cluster` mode):
```bash
$ cd .local/lib/python2.7/site-packages/
$ zip -r ../deps.zip .
```
#### 4.4. Yarn - log

Edit and add following lines to `yarn-site.xml` at `$HADOOP_HOME/etc/hadoop/yarn-site.xml` to save the yarn application logs.
```
<property>
    <name>yarn.resourcemanager.hostname</name>
    <value>master_node_public_ip</value>
</property>
<property>
    <name>yarn.log-aggregation-enable</name>
    <value>true</value>
</property>
<property>
    <name>yarn.nodemanager.remote-app-log-dir</name>
    <value>/app-logs</value>
</property>
<property>
    <name>yarn.nodemanager.remote-app-log-dir-suffix</name>
    <value>yarn-logs</value>
</property>
<property>
    <name>yarn.log-aggregation.retain-seconds</name>
    <value>604800</value>
</property>
```
Replace `master_node_public_ip` with the ip address of the cluster master node.
Yarn logs are saved on `hdfs://app-logs/yarn-logs`.

<a name="input" />

### 5. Input data

Common Crawl project crawls the internet once every month. The data including the request, reponse and contents for each page are stored in a `warc.gz` file using WARC format. Each `warc.gz` contains many webpages and has a size around 1 GB. For each month there could be up to 60,000 `warc.gz` files. The paths (URI) to the `warc.gz` files are soterd in a file (`warc.paths.gz`) for each month. For example the path file for the January 2020 Crawl is in the following address:

https://commoncrawl.s3.amazonaws.com/crawl-data/CC-MAIN-2020-05/warc.paths.gz

Cookie Consent application needs to have access to the path file. The path file could be seperated into several smaller size files to perform batch processing. For example the paths for the 60,000 `warc.gz` files could be stored in 10 files, each contians 6000 lines where each line is a single URI of a `warc.gz`.
As an example `warc.paths.2020.1.100.gz` and `warc.paths.2020.101.200.gz` are two path files, each contains the URIs for 100 `warc.gz` file for January 2020 Crawl.
These files should be saved onto HDFS.
```bash
$ hdfs dfs -mkdir -p /user/warc
$ hdfs dfs -copyFromLocal warc.paths.2020.1.100.gz /user/warc/
$ hdfs dfs -copyFromLocal warc.paths.2020.101.200.gz /user/warc/
```
<a name="geoip2" />

### 6. Geoip2 table

Geoip2 application is used to retrieve the country name from the ip address for each webpage. Each month [MAXMIND](https://dev.maxmind.com/geoip/geoip2/geolite2/) provides the most updated data in a table. Geoip2 application requiers this table to function. The most recent table (GeoLite2-City.mmdb) can be downloaded from this site for free. This table should be saved onto HDFS.
```bash
$ hdfs dfs -mkdir /user/geoip/
$ hdfs dfs -copyFromLocal GeoLite2-City.mmdb /user/geoip/
```
<a name="submit" />

### 7. Submit spark job
The spark job could be either submit by airflow scheduler or using one of the two scripts: `spark-job.sh` and `yarn-job.sh` as:
```bash
$ ./spark-job master_node_private_ip postgres_private_ip
$ ./yarn-job master_node_private_ip postgres_private_ip
```

<a name="docker" />

## DOCKER VERSION

Setting up the airflow server, postgres database, hadoop and spark edge nodes can be done using docker image.
Use following steps to set up airflow with postgres, hadoop and spark.
 * Set up the cluster ethier using Pegasus or AWS EMR
 * Set up an EC2 instance and clone the `spark-airflow` project:

```bash
$ git clone https://github.com/omidmns/spark-airflow.git
```
* Set AWS and database credentials in your `~/.bashrc`

```bash
export POSTGRES_USER=postgres_user
export POSTGRES_PASSWORD=postgres_password
export POSTGRES_AIRFLOW_DB=airflow

export AWS_SECRET_ACCESS_KEY=xxxxxx
export AWS_ACCESS_KEY_ID=xxxxxxxx
export AWS_DEFAULT_REGION=xxxxxxxxx
```
** As you pass the credentials to the docker image, be carefull that never push it to public repository **
 
* Transfer hadoop and spark config files from the cluster master node to the deignated folder on the EC2 instance:

```bash
$ scp user@master_node_private_ip:/path/to/spark/conf/* /home/ubuntu/spark-airflow/spark/

$ scp user@master_node_private_ip:/path/to/hadoop/etc/hadoop/* /home/ubuntu/spark-airflow/hadoop/
```
replace `user` and `master_private_ip` with `username` and `ip address` of the cluster master node.

* Check which version of hadoop and spark are running on the cluster
* Edit `Dockefile` with your cluster hadoop and spark version
* Run docker-compose:
```bash
$ docker-compose -f airflow-postgres.yml up -d
```
* Create `cookie_consent` database:
```bash
$ psql --host=localhost --port=5432 --username=postgres_user --password --dbname=airflow
```
```sql
CREATE DATABASE cookie_consent;
\q
```
* Follow other sections to prepare the input data and Geoip2 table, and put them on HDFS.  


## Credit

* https://tech.marksblogg.com/petabytes-of-website-data-spark-emr.html
* https://github.com/InsightDataScience/pegasus
* https://blog.insightdatascience.com/how-to-get-hadoop-and-spark-up-and-running-on-aws-7a1b0ab55459
* https://commoncrawl.org/the-data/get-started/
* https://github.com/commoncrawl/cc-pyspark
* https://github.com/snowplow/snowplow/wiki/Setting-up-PostgreSQL
* https://github.com/puckel/docker-airflow







