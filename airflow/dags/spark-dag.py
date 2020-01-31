import os
from datetime import timedelta, datetime
from airflow import DAG
from airflow.contrib.operators.spark_submit_operator import SparkSubmitOperator
from airflow.operators.bash_operator import BashOperator
from airflow.utils.trigger_rule import TriggerRule

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2020,2,7),
    'email': ['airflow@example.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 0,    
}
dag = DAG(
    'spark_operator',
    default_args=default_args,
    schedule_interval=None,
)

# replace cluster-name with the name of your cluster
bash_cmd = """
cd /home/ubuntu/cookie_consent/
./stop_cluster.sh cluster-name > EndTask.log
"""

last_task=BashOperator(
        task_id='last_task',
        bash_command=bash_cmd,
        dag=dag,
        trigger_rule=TriggerRule.ALL_DONE)


hdfs_ip = 'master_node_private_ip'
db_ip = 'postgres_private_ip'

data_list = ['warc.paths.2020.1.100.gz','warc.paths.2020.101.200.gz']

t = []
for i in range(len(data_list)):
    t.append(SparkSubmitOperator(
    task_id='spark_submit_'+str(i),
    conn_id='spark_default',
    deploy_mode='cluster',
    packages='org.postgresql:postgresql:9.4.1207.jre7,org.apache.hadoop:hadoop-aws:2.7.0',
    application='file:///home/ubuntu/cookie_consent/src/cc-main.py',
    application_args=['--warc_paths_file_address', 'hdfs://{}:9000/user/warc/{}'.format(hdfs_ip,data_list[i]),
            '--geoip_table_address', 'hdfs://{}:9000/user/geoip/GeoLite2-City.mmdb'.format(hdfs_ip),
            '--jdbc_url', 'jdbc:postgresql://{}:5432/cookie_consent'.format(db_ip),
            '--db_table', 'cookie_table'],
    executor_memory='2g',
    num_executors='4',
    executor_cores='1',
    driver_memory='4g',
    verbose=True,
    py_files='file:///home/ubuntu/cookie_consent/deps.zip',
    dag=dag,
    ))
    if i != 0:
        t[i-1] >> t[i]
t[i] >> last_task
