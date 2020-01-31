#!/bin/bash

# Copyright 2015 Insight Data Science
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This script is a part of InsightDataScience Pegasus project
# https://github.com/InsightDataScience/pegasus

CLUSTER_NAME=$1 #spark-cluster
AWS_CMD="aws ec2 --region ${AWS_DEFAULT_REGION:=us-west-2} --output text"
function get_instance_ids_with_name_and_role {
	local cluster_name=$1
	local cluster_role=$2
	if [ -z ${cluster_role} ]; then
	   ${AWS_CMD} describe-instances \
	   --filters Name=tag:Name,Values=${cluster_name} \
	             Name=instance-state-name,Values=running,stopped \
	   --query Reservations[].Instances[].InstanceId
	else
	   ${AWS_CMD} describe-instances \
	   --filters Name=tag:Name,Values=${cluster_name} \
	             Name=tag:Role,Values=${cluster_role} \
	             Name=instance-state-name,Values=running,stopped \
	   --query Reservations[].Instances[].InstanceId
	fi
	}
function stop_instance {
      local cluster_name=$1
      local instance_ids=$(get_instance_ids_with_name_and_role ${cluster_name})
 	${AWS_CMD} stop-instances \
	   --instance-ids ${instance_ids}
	}
stop_instance ${CLUSTER_NAME}

