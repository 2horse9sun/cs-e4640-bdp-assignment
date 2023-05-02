def gen_filebeat_config(filebeat_config_args):
    return f"""
http.enabled: true
http.host: "0.0.0.0"
http.port: {filebeat_config_args["http_port"]}

filebeat.inputs:
- type: filestream
  id: {filebeat_config_args["job_name"]}
  enabled: true
  paths:
    - /var/log/input_directory/{filebeat_config_args["filename_pattern"]}
    
logging.level: info
logging.to_files: true
logging.files:
  path: /var/log/filebeat
  name: filebeat
  keepfiles: 7
  permissions: 0640
    
filebeat.config.modules:
  path: ${{path.config}}/modules.d/*.yml
  reload.enabled: false

setup.template.settings:
  index.number_of_shards: 1
  
output.kafka:
  hosts: ["{filebeat_config_args["kafka_uri"]}"]
  topic: "filebeat"
  codec.json:
    pretty: false
    
# output.logstash:
#   hosts: ["{filebeat_config_args["logstash_uri"]}"]
  
processors:
  - script:
      lang: javascript
      source: >
        function process(event) {{
          var now = new Date();
          event.Put("start_time", now.toISOString());
        }}
  
"""
