# Quick Start

Before the deployment, you have to install the following tools on your machine:
* Docker
* Python
* Postman or other API tools
* MongoDBCompass (optional)

## Launch `coredms`

You need to create a container network called `bdp-net` for inter-container communications before all other steps:

```bash
docker network create bdp-net
```

Go to `code/coredms`, use docker compose to start the Elasticsearch and Kibana container:
```bash
docker compose up
```
Then, open [http://localhost:5601](http://localhost:5601) in the browser. If you can see the frontpage of Kibana, `coredms` is succeessfully launched.

## Launch `batchingestmanager`

Go to `code/batchingestmanager`, use docker compose to start the MongoDB container:
```bash
docker compose up
```
Then, use MongoDBCompass or other ways to connect to `mongodb://localhost:27017`. If the connection is okay, the MongoDB is up.

Go to `code/batchingestmanager/app`, install Python packages:
```bash
pip install -r requirements.txt
```
Then, start the flask application:
```bash
flask --app app.py --debug run
or
python app.py
```

## Create client profile

Open Postman or other tools and send a request to create a client profile:
```bash
POST http://localhost:5000/create_client_profile Content-Type:application/json
{
    "name": "Alice"
}
```
You should see the profile in `client` collection of `batchingestjob` database in MongoDB. The `client_id` is generated.

## Create a batch ingestion job

Open Postman or other tools and send a request to create a batch ingestion job as a client (You should copy the generated `client_id`):
```bash
POST http://localhost:5000/create_batchingestjob Content-Type:application/json
{
    "client_id": ${generated client_id},
    "job_name": "test",
    "filebeat_config_args": {
        "job_name": "vmtable",
        "filename_pattern": "*.csv"
    },
    "logstash_config_args": {
        "queue_type": "persisted"
    },
    "logstash_pipeline_config_args": {
        "filter": "  csv {\r\n    separator => \",\"\r\n    columns => [\"vm_id\",\"subscription_id\",\"deployment_id\",\"timestamp_vm_created\",\"timestamp_vm_deleted\",\"max_cpu\", \"average_cpu\" ,\"p96_max_cpu\",\"vm_category\",\"vm_virtual_core_count_bucket\",\"vm_memory_bucket\"]\r\n  }\r\n  \r\n  mutate {\r\n    convert => {\r\n      \"timestamp_vm_created\" => \"integer\"\r\n      \"timestamp_vm_deleted\" => \"integer\"\r\n      \"max_cpu\" => \"float\"\r\n      \"average_cpu\" => \"float\"\r\n      \"p96_max_cpu\" => \"float\"\r\n      \"vm_virtual_core_count_bucket\" => \"integer\"\r\n      \"vm_memory_bucket\" => \"integer\"\r\n    }\r\n  }",
        "index_name": "vmtable"
    },
    "elasticsearch_index_config": {
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
            "start_time": {
                "type": "date"
            },
            "finish_time": {
                "type": "date"
            }
            }
        }
        }
}
```
Then, you should see the created job in the `job` collection in MongoDB and can copy the generated `job_id`. Besides, a dedicated folder in `code/client-staging-input-directory` should be created with the formatt of `client-staging-input-directory/${client_id}/${job_id}`. This is where the client should put their data files.

## Input staging

Go to `code/client-staging-input-directory/${client_id}/${job_id}`, copy `data/vmtable_5w.csv` into that folder.

## Start batch ingestion job

Send a request to start the job:
```bash
GET http://localhost:5000/start_job?job_id=${job_id}
```
Then, keep an eye on the Docker Desktop and MongoDBCompass. A Filebeat and Logstash container should be created with the job status being "starting". After the containers are running, the job status becomes "running". At last, the two containers will be destroyed with the job status being "finished".

After the job is done, go to Kibana Dev tools and query the number of items ingested:
```json
GET /vmtable/_count
```
If it shows there are 50000 items, then the job is indeed successful. You can also query the items stored in Elasticsearch:
```json
GET /vmtable/_search
{
    "query" : {
        "match_all" : {}
    }
}
```

## Logs and Metrics

All Filebeat and Logstash config files as well as log files are generated into `code/clientbatchingestapp/${client_id}/${job_id}`.

Metrics about the job are stored into the `job_stats` and `job_stats_detail` fields in `job` collection of `batchingestjob` database in MongoDB.

## Stream ingestion job

The steps to perform a stream ingestion job is almost the same as the batch ingestion job.
