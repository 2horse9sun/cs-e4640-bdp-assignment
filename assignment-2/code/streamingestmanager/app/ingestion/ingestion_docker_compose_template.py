def gen_ingestion_docker_compose_file(ingestion_docker_compose_config):
    return f"""
version: '3'
services:

  zookeeper:
    image: confluentinc/cp-zookeeper:7.3.0
    networks:
      - bdp-net
    container_name: {ingestion_docker_compose_config["zookeeper_container_name"]}
    environment:
      ZOOKEEPER_CLIENT_PORT: {ingestion_docker_compose_config["zookeeper_client_port"]}
      ZOOKEEPER_TICK_TIME: {ingestion_docker_compose_config["zookeeper_tick_port"]}

  kafka01:
    image: confluentinc/cp-kafka:7.3.0
    networks:
      - bdp-net
    container_name: {ingestion_docker_compose_config["kafka_container_name"]}
    ports:
      - "{ingestion_docker_compose_config["kafka_port"]}:{ingestion_docker_compose_config["kafka_port"]}"
    depends_on:
      - zookeeper
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: 'zookeeper:{ingestion_docker_compose_config["zookeeper_client_port"]}'
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_INTERNAL:PLAINTEXT
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://{ingestion_docker_compose_config["kafka_container_name"]}:{ingestion_docker_compose_config["kafka_port"]},PLAINTEXT_INTERNAL://broker:29092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
    volumes:
      - ./kafka/log:/var/lib/kafka/data

  logstash:
    image: docker.elastic.co/logstash/logstash:8.6.1
    container_name: {ingestion_docker_compose_config["logstash_container_name"]}
    networks:
      - bdp-net
    depends_on:
      - kafka01
    ports:
      - "{ingestion_docker_compose_config["logstash_input_port"]}:{ingestion_docker_compose_config["logstash_input_port"]}"
      - "{ingestion_docker_compose_config["logstash_output_port"]}:{ingestion_docker_compose_config["logstash_output_port"]}"
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline
      - ./logstash/config/logstash.yml:/usr/share/logstash/config/logstash.yml:ro
      - ./logstash/log/:/var/log/logstash/:rw
      - ./logstash/config/log4j2.properties:/usr/share/logstash/config/log4j2.properties:ro

    environment:
      LS_JAVA_OPTS: "-Xmx512m -Xms512m"

  filebeat:
    image: docker.elastic.co/beats/filebeat:8.6.1
    container_name: {ingestion_docker_compose_config["filebeat_container_name"]}
    command: filebeat -strict.perms=false
    networks:
      - bdp-net
    depends_on:
      - logstash
      - kafka01
    ports:
      - "{ingestion_docker_compose_config["filebeat_port"]}:{ingestion_docker_compose_config["filebeat_port"]}"
    volumes:
      - ./filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
      - {ingestion_docker_compose_config["client_staging_input_directory"]}:/var/log/input_directory/:rw
      - ./filebeat/log/:/var/log/filebeat/:rw

networks:
  bdp-net:
    external: true
"""