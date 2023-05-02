# Quick Start

## Prerequisites

The recommended way to deploy the assignment is using Docker and Docker Compose. 

First, you need to install [Docker](https://docs.docker.com/get-docker/) on your machine. To test whether it is successful, execute the following command:
```bash
docker compose
```
If a list of docker compose options is outputed, the installation is successful.

Then, you need to create a container network called `bdp-net` for communications between `dataingest` and `coredms`:
```bash
docker network create bdp-net
```

At last, you must update the max virtual memory size for Elasticsearch otherwise Elasticsearch would fail to launch in container environment. Please follow the instructions [here](https://www.elastic.co/guide/en/elasticsearch/reference/current/docker.html#_set_vm_max_map_count_to_at_least_262144).

For Windows users, here's a simple way to temporarily update the max virtual memory:

Open powershell, run
```bash
wsl -d docker-desktop
```
then
```bash
sysctl -w vm.max_map_count=262144
```

## Launching `coredms`

First, let's launch the `coredms` module, which contains a three-node Elasticsearch cluster and Kibana.
```bash
cd code/coredms
docker compose up
```
It may take five to ten minutes to launch `coredms`. When it is done, go to [http://localhost:5601](http://localhost:5601). If you can successful enter Kibana home page, it means the `coredms` is successfully launched.

In Kibana home page, click into the `Dev Tools` at the bottom of the left sidebar. Now, we'd better create an index mapping for the incoming trace data. Execute the following JSON query request in the Dev Tool:
```json
PUT /vmtable
{
  "settings": {
    "index": {
      "number_of_shards": 5,
      "number_of_replicas": 2
    }
  },
  "mappings": {
    "properties": {
      "average_cpu": {
        "type": "double",
        "index":false
      },
      "deployment_id": {
        "type": "keyword"
      },
      "max_cpu": {
        "type": "double",
        "index":false
      },
      "p96_max_cpu": {
        "type": "double",
        "index":false
      },
      "subscription_id": {
        "type": "keyword"
      },
      "timestamp_vm_created": {
        "type": "integer",
        "index":false
      },
      "timestamp_vm_deleted": {
        "type": "integer",
        "index":false
      },
      "vm_category": {
        "type": "keyword"
      },
      "vm_id": {
        "type": "keyword"
      },
      "vm_memory_bucket": {
        "type": "integer"
      },
      "vm_virtual_core_count_bucket": {
        "type": "integer"
      },
      "@timestamp": {
        "type": "date"
      }
    }
  }
}
```
Then you can execute:
```json
GET /vmtable/_mapping
```
to make sure the above step is successful.

## Launching `dataingest`

Then, it's time to launch the `dataingest` module, which contains Filebeats, a three-node Kafka cluster, and Logstash.
```bash
cd code/dataingest
docker compose up
```
It may take five to ten minutes to launch `dataingest`.

Now, Filebeats should be listening all .csv files in `data/` folder. To test whether the ingestion pipeline works, copy `data/test/test_vmtable.csv` to `data/` folder. Once a new .csv file is added, the pipeline should start to work. Go back to the 'Dev Tool' at Kibana, execute the following request:
```json
GET /vmtable/_search
{
    "query" : {
        "match_all" : {}
    }
}
```
If it outputs ten trace data elements, then the whole deployment is successful. Congratulations!