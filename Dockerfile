# VERSION 1.0.0
# AUTHOR: Omid Moeini
# DESCRIPTION: Basic Airflow container including Hadoop and Spark
# SOURCE: https://github.com/omidmns/docker-airflow
# Credit: https://github.com/puckel/docker-airflow

FROM python:3.7-slim-buster
LABEL maintainer="omidmns"

# Never prompt the user for choices on installation/configuration of packages
ENV DEBIAN_FRONTEND noninteractive
ENV TERM linux

# Airflow
ARG AIRFLOW_VERSION=1.10.9
ARG AIRFLOW_USER_HOME=/usr/local/airflow
ARG AIRFLOW_DEPS=""
ARG PYTHON_DEPS=""
ENV AIRFLOW_HOME=${AIRFLOW_USER_HOME}

# Define en_US.
ENV LANGUAGE en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8
ENV LC_CTYPE en_US.UTF-8
ENV LC_MESSAGES en_US.UTF-8

# set environment vars
ENV HADOOP_HOME /usr/local/hadoop
ENV PATH $PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin

ENV JAVA_HOME /usr
ENV PATH $PATH:$JAVA_HOME/bin

ENV SPARK_HOME /usr/local/spark
ENV PATH $PATH:$SPARK_HOME/bin
ARG SPARK_LIB=${SPARK_HOME}/lib/

ARG HADOOP_VER=2.7.6
ARG SPARK_VER=2.3.1
ARG SPARK_HADOOP_VER=2.7

# Disable noisy "Handling signal" log messages:
# ENV GUNICORN_CMD_ARGS --log-level WARNING

RUN mkdir -p /usr/share/man/man1 \
    && echo "deb http://ftp.us.debian.org/debian sid main" >> /etc/apt/sources.list \
    && set -ex \
    && buildDeps=' \
        freetds-dev \
        libkrb5-dev \
        libsasl2-dev \
        libssl-dev \
        libffi-dev \
        libpq-dev \
        git \
    ' \
    && apt-get update -yqq \
    && apt-get upgrade -yqq \
    && apt-get install -yqq --no-install-recommends \
        $buildDeps \
        freetds-bin \
        build-essential \
        default-libmysqlclient-dev \
        apt-utils \
        curl \
        rsync \
        netcat \
        locales \
        wget \
        ssh \
        vim \
        openjdk-8-jdk \
        libgeoip-dev \
    && sed -i 's/^# en_US.UTF-8 UTF-8$/en_US.UTF-8 UTF-8/g' /etc/locale.gen \
    && locale-gen \
    && update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 \
    && useradd -ms /bin/bash -d ${AIRFLOW_USER_HOME} airflow \
    && pip install -U pip setuptools wheel \
    && pip install pytz \
    && pip install pyOpenSSL \
    && pip install ndg-httpsclient \
    && pip install pyasn1 \
    && pip uninstall sqlalchemy \
    && pip install sqlalchemy==1.3.15 \
    && pip install awscli \
    && pip install apache-airflow[crypto,celery,postgres,hive,jdbc,mysql,ssh${AIRFLOW_DEPS:+,}${AIRFLOW_DEPS}]==${AIRFLOW_VERSION} \
    && if [ -n "${PYTHON_DEPS}" ]; then pip install ${PYTHON_DEPS}; fi \
    && apt-get purge --auto-remove -yqq $buildDeps \
    && apt-get autoremove -yqq --purge \
    && apt-get clean \
    && rm -rf \
        /var/lib/apt/lists/* \
        /tmp/* \
        /var/tmp/* \
        /usr/share/doc \
        /usr/share/doc-base

RUN pip install warc \
    && pip install boto \
    && pip install geoip2 \
    && pip install https://github.com/commoncrawl/gzipstream/archive/master.zip

RUN \
  wget https://archive.apache.org/dist/hadoop/common/hadoop-$HADOOP_VER/hadoop-$HADOOP_VER.tar.gz \
  && tar -xzf hadoop-$HADOOP_VER.tar.gz -C /usr/local \
  && mv /usr/local/*hadoop* $HADOOP_HOME \
  && mkdir -p $HADOOP_HOME/hadoop_data/hdfs/datanode \
  && mkdir -p $HADOOP_HOME/hadoop_data/hdfs/namenode \
  && rm -rf hadoop-$HADOOP_VER.tar.gz

RUN \  
  wget https://archive.apache.org/dist/spark/spark-$SPARK_VER/spark-$SPARK_VER-bin-hadoop$SPARK_HADOOP_VER.tgz \
  && tar -xzf spark-$SPARK_VER-bin-hadoop$SPARK_HADOOP_VER.tgz -C /usr/local \
  && mv /usr/local/*spark* $SPARK_HOME \
  && mkdir $SPARK_LIB \
  && cp ${HADOOP_HOME}/share/hadoop/tools/lib/aws-java-sdk-*.jar $SPARK_LIB \
  && cp ${HADOOP_HOME}/share/hadoop/tools/lib/hadoop-aws-*.jar $SPARK_LIB \
  && rm -rf spark-$SPARK_VER-bin-hadoop$SPARK_HADOOP_VER.tgz

# create ssh keys
RUN \
  ssh-keygen -t rsa -P '' -f ~/.ssh/id_rsa \
  && cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys \
  && chmod 600 ~/.ssh/authorized_keys

COPY entrypoint.sh /entrypoint.sh
COPY airflow/airflow.cfg ${AIRFLOW_USER_HOME}/airflow.cfg

RUN chown -R airflow: ${AIRFLOW_USER_HOME}

EXPOSE 8080 5555 8793 8088

USER airflow
WORKDIR ${AIRFLOW_USER_HOME}
ENTRYPOINT ["/entrypoint.sh"]
CMD ["webserver"]
