# Quick Start

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

## Launch `streamanalytics`

Go to `code/streamanalytics`, use docker compose to start the Apache Kafka and Flink container:

```bash
docker compose up
```

Then, open [http://localhost:8081](http://localhost:8081) in the browser. If you can see the frontpage of Flink, `streamanalytics` is succeessfully launched.

## Define schemas

Go to Kibana dev tools and create schemas for the output streaming data:
```json
PUT avg-geo-air-quality-stats
{
  "mappings": {
    "properties": {
      "sensorTimestamp": {
        "type": "date",
        "format": "epoch_millis"
      },
      "sensorLocation": {
        "type": "geo_point"
      },
      "countryCode": {
        "type": "keyword"
      },
      "avgP1": {
        "type": "double"
      },
      "avgP2": {
        "type": "double"
      }
    }
  }
}

PUT invalid-sensor-data
{
  "mappings": {
    "properties": {
      "sensorTimestamp": {
        "type": "date",
        "format": "epoch_millis"
      },
      "sensorData": {
        "type": "keyword"
      }
    }
  }
}
```

## Build Flink application

Go to `code/tenantstreamapp`, you will see a maven project `air-quality-monitor`. The project has already been built into `target/air-quality-monitor-1.16.0.jar`. If you want to build the project by yourself, you must have Java and maven properly installed and run `mvn clean package`.

## Launch data source

Go to `code/tenantdatasource`, and run the `air.py` to send data to Kafka:
```bash
python ./air.py
```
You should install packages required by the script before running.

## Submit the Flink application

Go to Flink webUI and submit `air-quality-monitor-1.16.0.jar` by upload the file then click submit button. You should see Flink app receiving and sending data in the dashboard.

## Visualization

After 5 to 10 minutes, go to Kibana dev tools and check that the output streaming data is successfully stored to Elasticsearch:
```json
GET /avg-geo-air-quality-stats/_count

GET /invalid-sensor-data/_count

GET /avg-geo-air-quality-stats/_search
{
  "query": {
    "match_all": {}
  }
}
```

Now you can go to Kibana Dashboard to create any kind of visualizations based on the data.
