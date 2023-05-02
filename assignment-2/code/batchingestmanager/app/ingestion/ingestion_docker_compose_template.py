def gen_ingestion_docker_compose_file(ingestion_docker_compose_config):
    return f"""
version: '3'
services:

  logstash:
    image: docker.elastic.co/logstash/logstash:8.6.1
    container_name: {ingestion_docker_compose_config["logstash_container_name"]}
    networks:
      - bdp-net
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