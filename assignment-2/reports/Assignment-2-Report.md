# Second Assignment - Working on Data Ingestion Pipelines

## Part 1 - Batch data ingestion pipeline

> 1. The ingestion will be applied to files of data. Define a set of constraints for files that mysimbdp will support for ingestion. Design a configuration model for the tenant service profile that can be used to specify a set of constraints for ingestion (e.g., maximum number of files and amount of data). Explain why you as a platform provider decide such constraints. Implement these constraints into simple configuration files and provide examples (e.g., JSON or YAML). 

Here are some constraints that mysimbdp will support for ingestion:
1. File size: In this part, the scenario for `mysimbdp` is to ingest batch trace files into elasticsearch, so there's no max size limit for a single file (because filebeat reads files row by row and traces are independent of each other). Instead, `mysimbdp` sets a total file size limit on a single batch data ingestion job. Therefore, a client will not ingest data which exceeds the provisioned size of `coredms`. Also, if the file size is too large, it is costly to rerun the ingestion job in case some errors occur. Some additional work like setting checkpoints must be done if the client wants to resume the job from where it stops. Smaller file size allows quick job rerun and flexible data migration.
2. Number of files: `mysimbdp` restricts the number of files for a single ingestion job. When ingesting a large number of files, the platform needs to allocate system resources such as memory, CPU, and storage. If too many files are ingested at once, the platform may become overwhelmed and experience performance degradation or failure.
3. File format: `mysimbdp` supports mulitiple log file format, such csv format, as long as clients define the logstash pipeline for processing the specified file format. The purpose is to enable multiple plugins or middlewares to parse and process data before it is stored into `coredms`. Sometimes, the platform should support common compression format to reduce file sizes.
4. File ingestion speed: `mysimbdp` supports different file ingestion speed by adjusting number of ingestion workers, such as launching more/less filebeat and logstash workders. The purpose is to meet different requirements of clients.

An example of JSON configuration files for a client profile:
```json
{
    "client_id": "3iecnbgkro302knejhg8gi5n4gidn",
    "client_name": "test",
    "max_file_size": 500000000, // bytes
    "max_number_of_files": 100,
    "file_format": ["csv", "txt"],
    "max_filebeat_workers": 1,
    "max_logstash_workers": 1
}
```
The configuration file shows that the client can ingest at most 100 csv or txt files with a total size of 500MB, using at most one filebeat and one logstash worker for a singe batch ingestion job. For simplicity, `mysimbdp` only launch one filebeat and logstash container for all clients. Tools like Kubernetes can be used to manage multiple containers.



> 2. Each tenant will put the tenant's data files to be ingested into a staging directory, client-staging-input-directory within mysimbdp (the staging directory is managed by the platform). Each tenant provides its ingestion programs/pipelines, clientbatchingestapp, which will take the tenant's files as input, in client-staging-input-directory, and ingest the files into mysimbdp-coredms. Any clientbatchingestapp must perform at least one type of data wrangling to transform data elements in files to another structure for ingestion. As a tenant, explain the design of clientbatchingestapp and provide one implementation. Note that clientbatchingestapp follows the guideline of mysimbdp given in the next Point 3. 

In my design of `mysimbdp`, `clientbatchingestapp` is simply a batch job specification provided by the client. A high level view of how a batch data ingestion job is executed:
1. The client defines a job specification (`clientbatchingestapp`) and creates a batch job at `batchingestmanager`. The specification contains all neccessary information about the ingestion, such as data collection, data wrangling and possibly a schema.
2. The client puts data into a specified place in `client-staging-input-directory`.
3. The client tells `batchingestmanager` to start the job.
4. `batchingestmanager` retrieves and parses the job specification. Then, it launches filebeat and logstash workers.
5. The filebeat and logstash workers will work as the client defined in the job specification.
6. After all the data has been ingested into elasticsearch, `batchingestmanager` releases the allocated resources and notifies the client.

Here's one example for the job specification:
```json
{
    "client_id": "jsjhfx",
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
            }
            }
        }
        }
}
```
The specification shows that the client "jsjhfx" will start a batch job called "test". All the csv files will be collected and parsed by Filebeat, and sent to a persist Logstash pipeline. Logstash will transform each received row in a way defined by the "filter". At last, all the data will be stored into Elasticsearch with the defined mappings and settings.



> 3. As the mysimbdp provider, design and implement a component mysimbdp-batchingestmanager that invokes tenant's clientbatchingestapp to perform the ingestion for available files in client-staging-input-directory. mysimbdp imposes the model that clientbatchingestapp has to follow but clientbatchingestapp is, in principle, a blackbox to mysimbdp-batchingestmanager. Explain how mysimbdp-batchingestmanager knows the list of clientbatchingestapp and decides/schedules the execution of clientbatchingestapp for tenants. 

My `batchingestmanager` consists of a Flask service and a MongoDB. Clients can create, start, and monitor batch job status via the Flask service. MongoDB stores all the jobs (`clientbatchingestapp`) created by the clients.

Here are some details about how `batchingestmanager` works:
1. The client calls `/create_batchingestjob` to upload the job specification and creat a batch job. All neccessary job information will be stored as an item to MongoDB. Now the job status is "created".
2. The client calls `/start_job` with a specified `job_id` to manually start a job. `batchingestmanager` retrieves job information from MongoDB and starts to build Filebeat and Logstash containers to run the ingestion job (config files for containers are generated into dedicated places in folder `clientbatchingestapp`). Now the job status is "starting".
3. The `job_monitor` background service in `batchingestmanager` periodically scans the job list and update job information and status. If the containers are built, the job status is updated to "running". If a job is running, `batchingestmanager` gathers different kinds of metrics from Filebeat, Logstash and Elasticsearch, and adds them to the job information. If all the data is ingested, `batchingestmanager` destroys previously created containers. The job status is "finished".
4. The client can monitor the job status and key metrics during the job execution.

In the above process, `clientbatchingestapp` is transparent to `batchingestmanager` because `batchingestmanager` simply generates config files from the templated `clientbatchingestapp` and runs containers. Also, the underlying infrastructure is transparent to clients because clients simply define what to do and do not care how to implement.

For simplicity, in my design, the client manually tells `batchingestmanager` to execute the `clientbatchingestapp`. However, in real world, `batchingestmanager` can use some scheduling algorithms to execute created jobs based on the current free resources to achieve high efficiency.



> 4. Explain your design for the multi-tenancy model in mysimbdp: which parts of mysimbdp will be shared for all tenants, which parts will be dedicated for individual tenants so that you as a platform provider can add and remove tenants based on the principle of pay-per-use. Develop test clientbatchingestapp, test data, and test constraints of files, and test service profiles for tenants according your deployment. Show the performance of ingestion tests, including failures and exceptions, for at least 2 different tenants in your test environment and constraints. Demonstrate examples in which data will not be ingested due to a violation of constraints. Present and discuss the maximum amount of data per second you can ingest in your tests. 

The client has dedicated place in `client-staging-input-directory` for file staging. Each job created by the client has its own job information entry in `batchingestmanager`, dedicated Filebeat and Logstash container (`clientbatchingestapp`). Each client have its dedicated elasticsearch instance for data storage (here I just use one instance for simplicity). All clients interacts with the big data platform by `batchingestmanager`.

Now, I'm going to show a complete ingestion test, where two clients ingest their trace files.

First, create client profiles for the two new clients: Alice and Bob. Their profiles are below:

```json
{
  "_id": {
    "$oid": "64101fe4db6c780efed3cebe"
  },
  "client_id": "1d1dab7d-7f6d-4501-9c15-6587f1039bd2",
  "client_name": "Bob",
  "max_file_size": 500000000,
  "max_number_of_files": 100,
  "file_format": [
    "csv",
    "txt"
  ],
  "max_filebeat_workers": 1,
  "max_logstash_workers": 1
}

{
  "_id": {
    "$oid": "64101fe8db6c780efed3cebf"
  },
  "client_id": "a7db9d1e-27a8-4c8e-a7ea-479455c8dec5",
  "client_name": "Alice",
  "max_file_size": 500000000,
  "max_number_of_files": 100,
  "file_format": [
    "csv",
    "txt"
  ],
  "max_filebeat_workers": 1,
  "max_logstash_workers": 1
}
```

Then, each client creates their ingestion job, where the trace files are sent to Logstash for transformation and then stored in Elasticsearch. Two jobs with id `641022b2db6c780efed3cec0` and `641022c2db6c780efed3cec1` are created.


Next, each client puts their trace files into the dedicated folder in `client-staging-input-directory`. Then, each client manually starts the job. One example of the trace file:
```
71fJw0x+SDRdAxKPwLyHZhTgQpYw2afS6tjJhfT6kHnmLH54/rl2etJKUpSFKoTB,GB6uQC1NSArW5n+TtOybL7GQ1yByjuWtZnsj+5QccZ525R2wi5t9jPe8K5tU8MjR,2sh/ZjaYdfpslv4iYBfNzFe4rs982kHVvNGJGeQ8MIBCDr3EBYlXlNvViSonMAjfFuCpsbEPDDfydWwf/naB5Q==,558300,1673700,91.776885421193157,0.72887880462586729,20.759629514971522,Delay-insensitive,32,128
```
Each row of the file will be parsed into a few fields, which will be type converted by Logstash.


After a while, the first client's job failed because of the violation against the constraints. The response shows that: 
```json
{
    "error": "Total file size exceeds limit",
    "status": "failed"
}
```

The second client's job succeeded. It is easy to gather different kinds of metrics and performance information from the Elasticsearch APIs. Based on the `job_stats` of the job in MongoDB, we can get the following information which is extracted from Elasticsearch HTTP API:
```json
"store": {
    "size_in_bytes": 250480148,
    "total_data_set_size_in_bytes": 250480148,
    "reserved_in_bytes": 0
},
"indexing": {
    "index_total": 500000,
    "index_time_in_millis": 17070,
    "index_current": 0,
    "index_failed": 0,
    "delete_total": 0,
    "delete_time_in_millis": 0,
    "delete_current": 0,
    "noop_update_total": 0,
    "is_throttled": false,
    "throttle_time_in_millis": 0,
    "write_load": 0.061868237147982216
}
```
Based on the statistical data above, we can conclude that the processing rate is 500000/17.07 ≈ 29411 rows per second, the throughput is 250480148/17.07 ≈ 14.73 MB per second.


> 5. Implement and provide logging features for capturing successful/failed ingestion as well as metrics about ingestion time, data size, etc., for files which have been ingested into mysimbdp. Logging information must be stored in separate files, databases or a monitoring system for analytics of ingestion. Explain how mysimbdp could use such logging information. Show and explain simple statistical data extracted from logs for individual tenants and for the whole platform with your tests. 

Filebeat and Logstash will automatically dump log files into dedicated places for each job created by the client in folder `clientbatchingestapp`, which contain basic info and error level logs. The logging information is mainly used for error tracking if the job fails.

Here are some sample logs extracted from Filebeat. The logs show that Filebeat has successfully read 500000 rows and sent 500000 rows of data at `2023-03-14T10:53:29.532Z` without errors:
```json
{
  "log.level": "info",
  "@timestamp": "2023-03-14T10:53:29.532Z",
  "log.logger": "monitoring",
  "log.origin": {
    "file.name": "log/log.go",
    "file.line": 195
  },
  "message": "Total metrics",
  "service.name": "filebeat",
  "monitoring": {
    "metrics": {
      "beat": {
        "cpu": {
          "system": {
            "ticks": 12440,
            "time": {
              "ms": 12440
            }
          },
          "total": {
            "ticks": 40750,
            "time": {
              "ms": 40750
            },
            "value": 40750
          },
          "user": {
            "ticks": 28310,
            "time": {
              "ms": 28310
            }
          }
        },
        "memstats": {
          "gc_next": 58400168,
          "memory_alloc": 32046592,
          "memory_sys": 93442072,
          "memory_total": 5622258616,
          "rss": 163573760
        },
        "runtime": {
          "goroutines": 14
        }
      },
      "filebeat": {
        "events": {
          "active": 0,
          "added": 500000,
          "done": 500000
        },
        "harvester": {
          "closed": 0,
          "open_files": 0,
          "running": 0,
          "skipped": 0,
          "started": 0
        },
        "input": {
          "log": {
            "files": {
              "renamed": 0,
              "truncated": 0
            }
          },
          "netflow": {
            "flows": 0,
            "packets": {
              "dropped": 0,
              "received": 0
            }
          }
        }
      },
      "libbeat": {
        "config": {
          "module": {
            "running": 0,
            "starts": 0,
            "stops": 0
          },
          "reloads": 1,
          "scans": 1
        },
        "output": {
          "events": {
            "acked": 500000,
            "active": 0,
            "batches": 245,
            "dropped": 0,
            "duplicates": 0,
            "failed": 0,
            "toomany": 0,
            "total": 500000
          },
          "read": {
            "bytes": 1470,
            "errors": 0
          },
          "type": "logstash",
          "write": {
            "bytes": 110288741,
            "errors": 0
          }
        },
        "pipeline": {
          "clients": 0,
          "events": {
            "active": 0,
            "dropped": 0,
            "failed": 0,
            "filtered": 0,
            "published": 500000,
            "retry": 8192,
            "total": 500000
          },
          "queue": {
            "acked": 500000,
            "max_events": 4096
          }
        }
      },
    },
    "ecs.version": "1.6.0"
  }
}
```


Here are some sample logs extracted from Logstash. The logs show that Logstash has successfully started and shut down without errors.
```
[2023-03-14T10:52:27,456][INFO ][logstash.inputs.beats    ][main] Starting input listener {:address=>"0.0.0.0:5044"}
[2023-03-14T10:52:27,460][INFO ][logstash.javapipeline    ][main] Pipeline started {"pipeline.id"=>"main"}
[2023-03-14T10:52:27,470][INFO ][logstash.agent           ] Pipelines running {:count=>1, :running_pipelines=>[:main], :non_running_pipelines=>[]}
[2023-03-14T10:52:27,501][INFO ][org.logstash.beats.Server][main][7170923a0903400c6b5e2ab0586eda90e080fa27bc714389f0795f173b44c853] Starting server on port: 5044
[2023-03-14T10:53:29,844][WARN ][logstash.runner          ] SIGTERM received. Shutting down.
[2023-03-14T10:53:37,965][INFO ][logstash.javapipeline    ][main] Pipeline terminated {"pipeline.id"=>"main"}
[2023-03-14T10:53:38,892][INFO ][logstash.pipelinesregistry] Removed pipeline from registry successfully {:pipeline_id=>:main}
[2023-03-14T10:53:38,896][INFO ][logstash.runner          ] Logstash shut down.
```

Metrics about ingestion time, data size, etc., are collected via Filebeats, Logstash, and Elasticsearch HTTP APIs.

Here are some metrics extracted:
```json
{
  "job_stats": {
    "filebeat_stats": {
      "event": {
        "active": 0,
        "added": 500000,
        "done": 500000
      }
    },
    "logstash_stats": {
      "event": {
        "in": 500000,
        "filtered": 500000,
        "out": 500000,
        "duration_in_millis": 123979,
        "queue_push_duration_in_millis": 11351
      },
      "flow": {
        "input_throughput": {
          "current": 8912,
          "last_1_minute": 7866,
          "lifetime": 7866
        },
        "filter_throughput": {
          "current": 8933,
          "last_1_minute": 7867,
          "lifetime": 7867
        },
        "output_throughput": {
          "current": 8933,
          "last_1_minute": 7867,
          "lifetime": 7867
        },
        "queue_backpressure": {
          "current": 0.1912,
          "last_1_minute": 0.1786,
          "lifetime": 0.1786
        },
        "worker_concurrency": {
          "current": 1.747,
          "last_1_minute": 1.951,
          "lifetime": 1.951
        }
      }
    },
    "index_stats": {
      "indexing": {
        "index_total": 500000,
        "index_time_in_millis": 17070,
        "index_current": 0,
        "index_failed": 0,
        "delete_total": 0,
        "delete_time_in_millis": 0,
        "delete_current": 0,
        "noop_update_total": 0,
        "is_throttled": false,
        "throttle_time_in_millis": 0,
        "write_load": 0.23435317182668233
      }
    }
  }
}
```




## Part 2 - Near-realtime data ingestion


> 1. Tenants will put their data into messages and send the messages to a messaging system, mysimbdp-messagingsystem (provisioned by mysimbdp) and tenants will develop ingestion programs, clientstreamingestapp, which read data from the messaging system and ingest the data into mysimbdp-coredms. For near-realtime ingestion, explain your design for the multi-tenancy model in mysimbdp: which parts of the mysimbdp will be shared for all tenants, which parts will be dedicated for individual tenants so that mysimbdp can add and remove tenants based on the principle of pay-per-use. 

The overall architecture for near-realtime data ingestion is much similar to that in part 1. The biggest differece is that there's a Kafka broker (`messagingsystem`) between Filebeat and Logstash. I keep the `client-staging-input-directory` instead of writing an client app for sending data to `messagingsystem`, because in real world, trace logs are streamed into a specific folder and Filebeat can detect and send those logs in real time. The client may have multiple data sources to be sent into `messagingsystem`. For simplicity, I only use the same `client-staging-input-directory` strategy as part 1 to simulate mulitple sources.

Like part 1, the client has dedicated place in `client-staging-input-directory` for file streaming. Each job created by the client has its own job information entry in `batchingestmanager`, dedicated Filebeat, Kafka (`messagingsystem`) and Logstash container (`clientstreamingestapp`). Each client have its dedicated elasticsearch instance for data storage (here I just use one instance for simplicity). All clients interacts with the big data platform by `streamingestmanager`.



> 2. Design and implement a component mysimbdp-streamingestmanager, which can start and stop clientstreamingestapp instances on-demand. mysimbdp imposes the model that clientstreamingestapp has to follow so that mysimbdp-streamingestmanager can invoke clientstreamingestapp as a blackbox, explain the model. 

Like part 1, my `streamingestmanager` consists of a Flask service and a MongoDB. Clients can create, start, stop, and monitor stream job status via the Flask service. MongoDB stores all the jobs (`clientstreamingestapp`) created by the clients.

Here are some details about how `streamingestmanager` works:
1. The client calls `/create_streamingestjob` to upload the job specification and creat a stream job. All neccessary job information will be stored as an item to MongoDB. Now the job status is "created".
2. The client calls `/start_job` with a specified `job_id` to manually start a job. `streamingestmanager` retrieves job information from MongoDB and starts to build Filebeat, Kafka, and Logstash containers to run the ingestion job (config files for containers are generated into dedicated places in folder `clientstreamingestapp`). Now the job status is "starting".
3. The `job_monitor` background service in `streamingestmanager` periodically scans the job list and update job information and status. If the containers are built, the job status is updated to "running". If a job is running, `streamingestmanager` gathers different kinds of metrics from Filebeat, Kafka, Logstash and Elasticsearch, and adds them to the job information. 
4. The client calls `/stop_job` with a specified `job_id` to manually stop a job. `streamingestmanager` destroys previously created containers. The job status is "stopped".
5. The client can monitor the job status and key metrics during the job execution.

In the above process, `clientstreamingestapp` is transparent to `streamingestmanager` because `streamingestmanager` simply generates config files from the templated `clientstreamingestapp` and runs containers. Also, the underlying infrastructure is transparent to clients because clients simply define what to do and do not care how to implement.


> 3. Develop test ingestion programs (clientstreamingestapp), which must include one type of data wrangling (transforming the received message to a new structure). Show the performance of ingestion tests, including failures and exceptions, for at least 2 different tenants in your test environment, explain also the data used for testing. What is the maximum throughput of the ingestion in your tests? 

Now, I'm going to show a complete ingestion test, where two clients ingest their trace files by streaming.

First, create client profiles for the two new clients: Alice and Bob. Their profiles are below:

```json
{
  "_id": {
    "$oid": "6410649a51a5d2b52785434e"
  },
  "client_id": "200c100b-bfdc-4e6f-9f33-95d9ae37226b",
  "client_name": "Alice",
  "max_file_size": 500000000,
  "max_number_of_files": 100,
  "file_format": [
    "csv",
    "txt"
  ],
  "max_filebeat_workers": 1,
  "max_logstash_workers": 1
}

{
  "_id": {
    "$oid": "641064a051a5d2b52785434f"
  },
  "client_id": "e299d8bd-178d-4c04-aba9-94a2a17ee3a2",
  "client_name": "Bob",
  "max_file_size": 500000000,
  "max_number_of_files": 100,
  "file_format": [
    "csv",
    "txt"
  ],
  "max_filebeat_workers": 1,
  "max_logstash_workers": 1
}
```

Then, each client creates their ingestion job, where the trace files are sent to Logstash for transformation and then stored in Elasticsearch. Two jobs with id `64106aa7b8b8d0b7eba3d292` and `64106aa7b8b8d0b8b3a3d293` are created.


Next, each client puts their trace files into the dedicated folder in `client-staging-input-directory` to simulate sending messages to Kafka. Then, each client manually starts the job. One example of the trace file:
```
71fJw0x+SDRdAxKPwLyHZhTgQpYw2afS6tjJhfT6kHnmLH54/rl2etJKUpSFKoTB,GB6uQC1NSArW5n+TtOybL7GQ1yByjuWtZnsj+5QccZ525R2wi5t9jPe8K5tU8MjR,2sh/ZjaYdfpslv4iYBfNzFe4rs982kHVvNGJGeQ8MIBCDr3EBYlXlNvViSonMAjfFuCpsbEPDDfydWwf/naB5Q==,558300,1673700,91.776885421193157,0.72887880462586729,20.759629514971522,Delay-insensitive,32,128
```
Each row of the file will be parsed into a few fields, which will be type converted by Logstash.


When the two jobs are running, it is easy to gather different kinds of metrics and performance information from the Elasticsearch APIs. Based on the `job_stats` of the job in MongoDB, we can get the following information which is extracted from Elasticsearch HTTP API:
```json
"store": {
  "size_in_bytes": 248866355,
  "total_data_set_size_in_bytes": 248866355,
  "reserved_in_bytes": 0
},
"indexing": {
  "index_total": 500000,
  "index_time_in_millis": 16984,
  "index_current": 0,
  "index_failed": 0,
  "delete_total": 0,
  "delete_time_in_millis": 0,
  "delete_current": 0,
  "noop_update_total": 0,
  "is_throttled": false,
  "throttle_time_in_millis": 0,
  "write_load": 0.004520971813126703
},
```
Based on the statistical data above, we can conclude that the processing rate is 500000/16.98 ≈ 29446 rows per second, the throughput is 248866355/16.98 ≈ 14.65 MB per second.


> 4. clientstreamingestapp decides to report the its processing rate, including average ingestion time, total ingestion data size, and number of messages to mysimbdp-streamingestmonitor within a pre-defined period of time. Design the report format and explain possible components, flows and the mechanism for reporting. 



Average ingestion time: when Filebeat reads a row, it attaches a `start_time` timestamp to the row. When the row is stored into Elasticsearch, a `finish_time` is attached. The ingestion time for a row is `start_time - finish_time`. The average ingestion time would be the average of all the rows' ingestion time within a pre-defined period of time. This can be easily computed with the Elasticsearch aggregation feature.

Total ingestion data size and number of messages: Elasticsearch HTTP API can give us the information.

In my design, `streamingestmonitor` is actually the `job_monitor` background service in `clientstreamingestmanager`, which can already periodically collect the above metrics by HTTP APIs and update them into the job information during the job execution. Therefore, `clientstreamingestmanager` does not have to actively report the metrics.

One example of the report extracted from the job information:
```json
"report": {
  "total_ingestion_size": 248866355,
  "last_1_min": {
    "avg_ingestion_time": null,
    "num_of_msg": 0
  },
  "last_10_min": {
    "avg_ingestion_time": null,
    "num_of_msg": 0
  },
  "last_60_min": {
    "avg_ingestion_time": 21853.485348,
    "num_of_msg": 500000
  },
  "all": {
    "avg_ingestion_time": 21853.485348,
    "num_of_msg": 500000
  }
}
```

> 5. Implement a feature in mysimbdp-streamingestmonitor to receive the report from clientstreamingestapp. Based on the report from clientstreamingestapp, when the performance is below a threshold, e.g., average ingestion time is too low, mysimbdp-streamingestmonitor decides to inform mysimbdp-streamingestmanager about the situation. Implementation a feature in mysimbdp-streamingestmanager to receive information informed by mysimbdp-streamingestmonitor. 

Just as the Q4 says, `job_monitor` background service can already periodically collect the above metrics by HTTP APIs and update them into the job information during the job execution. `streamingestmanager` can easily be notified when some performance is below a threshold.

For example, in my design, if the number of rows ingested in the last one minute is below, like 100, the console just simply print a warning message:
```
There are very few rows ingested in the last one minute!
```




## Part 3 - Integration and Extension



> 1. Produce an integrated architecture for the logging and monitoring of both batch and near-realtime ingestion features (Part 1, Point 5 and Part 2, Points 4-5) so that you as a platform provider could know the amount of data ingested and existing errors/performance for individual tenants. 

My solution is to set up another Elasticsearch cluster and Kibana dedicated for monitoring the ingestion system. Logs and metrics from Filebeats, Kafka, Logstash, and Elasticsearch are collected and sent to the above monitoring system for centralized analysis. Each client is assigned an endpoint to the monitoring system and can have a full picture of the job execution process. If some errors or performance problems occur, the client or the monitoring system can give quick response.


> 2. In the stream ingestion pipeline, assume that a tenant has to ingest the same data but to different sinks, e.g., mybdp-coredms for storage and a new mybdp-streamdataprocessing component, what features/solutions you can provide and recommend to your tenant? 

My solution is to provide a visualized window for clients to define their workflows. Resources like Logstash and Elasticsearch are represented as individual components, which clients can arrange and connect them with each other flexibly to create their own workflows. Connections between components represent the data flow. For each component, the clients themselves define functions to process data. After clients submit their workflow, our platform will parse the workflow and allocate associated resources to execute the job.

> 3. The tenant wants to protect the data during the ingestion by using some encryption mechanisms to encrypt data in files. Thus, clientbatchingestapp has to deal with encrypted data. Which features/solutions you recommend the tenants and which services you might support them for this goal? 

Two types of data encryption mechanisms could be provided: client-side and server side. Out platform will provide built-in server side data encryption, which means clients' data is automatically encrypted by our service during the lifecycle of the data ingestion. When clients retrieve data, the data is automatically decrypted. Additional services like key management could also be provided. Another option is client-side encryption, where clients implement the data encryption themselves. In such case, out platform can provide some useful encryption SDKs for clients.

> 4. In the case of near-realtime ingestion, we want to (i) detect the quality of data to allow ingestion only for data with a pre-defined quality of data condition and (ii) store metadata, including detected quality, into the platform, how would you suggest a design/change of your design for achieving this? 

Some designs for monitoring data quality:
1. Define the quality metrics about the data quality, such as completeness, accuracy, consistency, timeliness, etc.
2. Develop data quality checks based on the defined quality metrics. These checks should be implemented as part of the ingestion pipeline and should be designed to assess the quality of data before it is ingested into the platform.
3. Set quality thresholds for each metric. Data that falls within the acceptable range will be considered of sufficient quality to be ingested into the platform.
4. Once the data has been ingested, store the metadata including the detected quality information in a metadata repository. This repository should be designed to support fast querying and analysis of the metadata.
5. Set up monitoring and alerting to detect and alert you when data quality thresholds are not met. This will allow you to quickly identify and address data quality issues.

> 5. If a tenant has multiple clientbatchingestapp, each is suitable for a type of data and has different workloads, such as complex transformation or feature engineering (e.g., different CPUs, memory consumption and execution time), how would you extend your design and implementation in Part 1 (only explain the concept/design) to support this requirement? 

Clients could provide the types of data or workflows in the job specification. And, our platform could pre-define different configs for different types of data or workflows. When a job is processed, the platform will allocate different amounts of resources (different CPUs, memory consumption) for job execution. Some scheduling algorithms can take advantage of the given execution time to achieve better performance.











