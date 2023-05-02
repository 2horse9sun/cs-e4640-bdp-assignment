from flask import Flask, jsonify, request
from pymongo import MongoClient
import os
import docker
import time
from bson import ObjectId
import json
import uuid
import random
import subprocess
import requests
import socket
from elasticsearch import Elasticsearch
from filebeat.filebeat_config_template import gen_filebeat_config
from logstash.logstash_config_template import gen_logstash_config
from logstash.logstash_pipeline_config_template import gen_logstash_pipeline_config
from ingestion.ingestion_docker_compose_template import gen_ingestion_docker_compose_file
from profile.client_profile_template import gen_client_profile

app = Flask(__name__)

mongo_uri = "mongodb://localhost:27018"
db_client = MongoClient(mongo_uri)
db = db_client["streamingestjob"]
client_collection = db["client"]
job_collection = db["job"]

docker_client = docker.from_env()

es = Elasticsearch(["http://localhost:9200"])


@app.route('/create_client_profile', methods=['POST'])
def create_client_profile():
    client_info = request.json
    client_profile = gen_client_profile(client_info)
    client_collection.insert_one(client_profile)
    return {"client_id": client_profile["client_id"]}


@app.route('/create_streamingestjob', methods=['POST'])
def create_streamingestjob():
    job_spec = request.json
        
    job = {
        "status": "created",
        "client_id": job_spec["client_id"],
        "job_name": job_spec["job_name"],
        "filebeat_config_args": job_spec["filebeat_config_args"],
        "logstash_config_args": job_spec["logstash_config_args"],
        "logstash_pipeline_config_args": job_spec["logstash_pipeline_config_args"],
        "elasticsearch_index_config": job_spec["elasticsearch_index_config"],
        "index_name": job_spec["logstash_pipeline_config_args"]["index_name"]
    }
    job_collection.insert_one(job) 
    job_id = str(job["_id"])
    
    # create folder for a client to upload files
    client_ingest_dir = f'../../client-staging-input-directory/{job["client_id"]}/{job_id}/'
    if not os.path.exists(client_ingest_dir):
        os.makedirs(client_ingest_dir)
    return {"job_id": job_id}

def create_file(path, file_content):
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        os.makedirs(directory)
    with open(path, 'w') as f:
        f.write(file_content)
        
def get_free_port(lb, ub):
    for port in range(lb, ub):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) != 0:
                return port
    return 8080


@app.route('/start_job', methods=['GET'])
def start_job():
    job_id = request.args.get('job_id')
    job = job_collection.find_one({"_id": ObjectId(job_id)})
    client_app_dir = f'../../clientstreamingestapp/{job["client_id"]}/{job_id}/'
        
    # generate config files for filebeat, logstash and docker-compose
    filebeat_container_name = f'filebeat-{job_id}'
    filebeat_port = get_free_port(5066, 5076)
    logstash_container_name = f'logstash-{job_id}'
    logstash_input_port = get_free_port(5044, 5054)
    logstash_output_port = get_free_port(9600, 9610)
    zookeeper_container_name = f'zookeeper-{job_id}'
    zookeeper_client_port = get_free_port(2181, 2191)
    zookeeper_tick_port = get_free_port(2000, 2010)
    kafka_container_name = f'kafka-{job_id}'
    kafka_port = get_free_port(9092, 9099)
    
    job_collection.update_one({"_id": ObjectId(job_id)}, 
                              { "$set": 
                                  {
                                    "filebeat_container_name": filebeat_container_name,
                                    "logstash_container_name": logstash_container_name,
                                    "filebeat_port": filebeat_port,
                                    "logstash_input_port": logstash_input_port,
                                    "logstash_output_port": logstash_output_port,
                                    "elasticsearch_api": 'http://es01:9200',
                                    "zookeeper_container_name": zookeeper_container_name,
                                    "zookeeper_client_port": zookeeper_client_port,
                                    "zookeeper_tick_port": zookeeper_tick_port,
                                    "kafka_container_name": kafka_container_name,
                                    "kafka_port": kafka_port,
                                }
                               })
    
    job["filebeat_config_args"]["http_port"] = filebeat_port
    job["filebeat_config_args"]["logstash_uri"] = f'{logstash_container_name}:{logstash_input_port}'
    job["filebeat_config_args"]["kafka_uri"] = f'{kafka_container_name}:{kafka_port}'
    job["logstash_config_args"]["logstash_output_port"] = logstash_output_port
    job["logstash_pipeline_config_args"]["input_port"] = logstash_input_port
    job["logstash_pipeline_config_args"]["kafka_uri"] = f'{kafka_container_name}:{kafka_port}'
    job["logstash_pipeline_config_args"]["elasticsearch_uri"] = "http://es01:9200"
     
    filebeat_config_path = f'{client_app_dir}filebeat/filebeat.yml'
    create_file(filebeat_config_path, gen_filebeat_config(job["filebeat_config_args"]))
    logstash_config_path = f'{client_app_dir}logstash/config/logstash.yml'
    create_file(logstash_config_path, gen_logstash_config(job["logstash_config_args"]))
    logstash_pipeline_config_path = f'{client_app_dir}logstash/pipeline/pipeline.conf'
    create_file(logstash_pipeline_config_path, gen_logstash_pipeline_config(job["logstash_pipeline_config_args"]))
    logstash_logging_config_path = f'{client_app_dir}logstash/config/log4j2.properties'
    logstash_logging_config = ""
    with open('./logstash/log4j2.properties', 'r') as file:
        logstash_logging_config = file.read()
    create_file(logstash_logging_config_path, logstash_logging_config)
    
    ingestion_docker_compose_config = {
        "logstash_container_name": logstash_container_name,
        "logstash_input_port": logstash_input_port,
        "logstash_output_port": logstash_output_port,
        "filebeat_container_name": filebeat_container_name,
        "filebeat_port": filebeat_port,
        "client_staging_input_directory": f'../../../client-staging-input-directory/{job["client_id"]}/{job_id}/',
        "zookeeper_container_name": zookeeper_container_name,
        "zookeeper_client_port": zookeeper_client_port,
        "zookeeper_tick_port": zookeeper_tick_port,
        "kafka_container_name": kafka_container_name,
        "kafka_port": kafka_port,
    }
    create_file(f'{client_app_dir}docker-compose.yml', gen_ingestion_docker_compose_file(ingestion_docker_compose_config))
    
    try:
        # create index in elasticsearch
        if es.indices.exists(index=job["index_name"]):
            es.indices.delete(index=job["index_name"])
        timestamp_pipeline = {
                                "description": "Add timestamp to documents",
                                "processors": [
                                    {
                                        "set": {
                                            "field": "finish_time",
                                            "value": "{{_ingest.timestamp}}"
                                        }
                                    }
                                ]
                            }
        if not es.ingest.get_pipeline(id="timestamp_pipeline", ignore=404):
            es.ingest.put_pipeline(id="timestamp_pipeline", body=timestamp_pipeline)
        es.indices.create(index=job["index_name"], mappings=job["elasticsearch_index_config"]["mappings"])
    except:
        pass
    
    # start filebeat, kafka and logstash container
    command = f'docker-compose -f {client_app_dir}docker-compose.yml up -d --build'
    process = subprocess.Popen(command.split())
    
    job_collection.update_one({"_id": ObjectId(job_id)}, { "$set": { "status": "starting" } })

    return { "status": "starting" }


@app.route('/stop_job', methods=['GET'])
def stop_job():
    job_id = request.args.get('job_id')
    job = job_collection.find_one({"_id": ObjectId(job_id)})
    
    filebeat_container = docker_client.containers.get(job["filebeat_container_name"])
    filebeat_container.stop()
    filebeat_container.remove()
    kafka_container = docker_client.containers.get(job["kafka_container_name"])
    kafka_container.stop()
    kafka_container.remove()
    zookeeper_container = docker_client.containers.get(job["zookeeper_container_name"])
    zookeeper_container.stop()
    zookeeper_container.remove()
    logstash_container = docker_client.containers.get(job["logstash_container_name"])
    logstash_container.stop()
    logstash_container.remove()
    
    job_collection.update_one({"_id": job["_id"]}, { "$set": { "status": "stopped" } })
    return { "status": "stopped" }


def get_job_stats(job_id):
    job = job_collection.find_one({"_id": job_id})
    filebeat_stats = requests.get(f'http://localhost:{job["filebeat_port"]}/stats').json()
    logstash_stats = requests.get(f'http://localhost:{job["logstash_output_port"]}/_node/stats').json()
    index_stats = dict(es.indices.stats(index=job["index_name"]))
    
    job_stats = {
        "filebeat_stats": {
            "event": filebeat_stats["filebeat"]["events"]
        },
        "logstash_stats": {
            "event": logstash_stats["events"],
            "flow": logstash_stats["flow"]
        },
        "index_stats": {
            "indexing": index_stats["indices"][job["index_name"]]["total"]["indexing"]
        }
    }
    
    job_stats_detail = {
        "filebeat_stats": filebeat_stats,
        "logstash_stats": logstash_stats,
        "index_stats": index_stats
    }

    return job_stats, job_stats_detail


def gen_report_query(mode):
    query = {
            "size": 0,
            "aggs": {
                "avg_ingestion_time": {
                    "avg": {
                        "script": {
                            "source": "doc['finish_time'].value.toInstant().toEpochMilli() - doc['start_time'].value.toInstant().toEpochMilli()"
                        }
                    }
                },
                "num_of_msg" : {
                "value_count" : {
                    "field" : "finish_time" 
                } 
                }
            }
        }
    if mode != "all":
        query["query"] = {
            "range": {
                "finish_time": {
                    "gte": f"now-{mode}"
                }
            }
        }   
    return query
        


import atexit
from apscheduler.schedulers.background import BackgroundScheduler

def job_monitor():
    # check if the filebeat, kafka and logstash is built and launched
    starting_jobs = job_collection.find({"status": "starting"})
    for starting_job in starting_jobs:
        filebeat_container_status = ""
        try:
            filebeat_container = docker_client.containers.get(starting_job["filebeat_container_name"])
            filebeat_container_status = filebeat_container.status
        except:
            filebeat_container_status = "building"
        if filebeat_container_status == "running":
            job_collection.update_one({"_id": starting_job["_id"]}, { "$set": { "status": "running" } })
            
    # gather metrics
    running_jobs = job_collection.find({"status": "running"})
    for running_job in running_jobs:
        running_job_stats, running_job_stats_detail = get_job_stats(running_job["_id"])
        filebeat_added = running_job_stats["filebeat_stats"]["event"]["added"]
        filebeat_out = running_job_stats["filebeat_stats"]["event"]["done"]
        logstash_in = running_job_stats["logstash_stats"]["event"]["in"]
        logstash_out = running_job_stats["logstash_stats"]["event"]["out"]
        elasticsearch_in = running_job_stats["index_stats"]["indexing"]["index_total"]
                
        last_1_min_report = es.search(index=running_job["index_name"], body=gen_report_query("1m"))
        last_10_min_report = es.search(index=running_job["index_name"], body=gen_report_query("10m"))
        last_60_min_report = es.search(index=running_job["index_name"], body=gen_report_query("60m"))
        all_report = es.search(index=running_job["index_name"], body=gen_report_query("all"))
        
        report = {
                "total_ingestion_size": running_job_stats_detail["index_stats"]["indices"][running_job["index_name"]]["total"]["store"]["size_in_bytes"],
                "last_1_min": {
                    "avg_ingestion_time": last_1_min_report["aggregations"]["avg_ingestion_time"]["value"],
                    "num_of_msg": last_1_min_report["aggregations"]["num_of_msg"]["value"]
                },
                "last_10_min": {
                    "avg_ingestion_time": last_10_min_report["aggregations"]["avg_ingestion_time"]["value"],
                    "num_of_msg": last_10_min_report["aggregations"]["num_of_msg"]["value"]
                },
                "last_60_min": {
                    "avg_ingestion_time": last_60_min_report["aggregations"]["avg_ingestion_time"]["value"],
                    "num_of_msg": last_60_min_report["aggregations"]["num_of_msg"]["value"]
                },
                "all": {
                    "avg_ingestion_time": all_report["aggregations"]["avg_ingestion_time"]["value"],
                    "num_of_msg": all_report["aggregations"]["num_of_msg"]["value"]
                },
        }
        
        if report["last_1_min"]["num_of_msg"] == "null" or report["last_1_min"]["num_of_msg"] < 100:
            print("There are very few rows ingested in the last one minute!")
        
        job_collection.update_one({"_id": running_job["_id"]}, { "$set": { "job_stats": running_job_stats, "job_stats_detail": running_job_stats_detail, "report": report } })    
        print(filebeat_added, filebeat_out, logstash_in, logstash_out, elasticsearch_in)
            

scheduler = BackgroundScheduler()
scheduler.add_job(func=job_monitor, trigger="interval", seconds=5, max_instances=10)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
