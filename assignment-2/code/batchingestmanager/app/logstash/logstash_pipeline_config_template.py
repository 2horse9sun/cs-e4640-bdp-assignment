def gen_logstash_pipeline_config(logstash_pipeline_config_args):
    return f"""

input {{
  beats{{port => {logstash_pipeline_config_args["input_port"]}}}
}}


filter {{
  
{logstash_pipeline_config_args["filter"]}

date {{
  match => [ "start_time", "ISO8601" ]
  target => "start_time"
}}

mutate {{
  remove_field => [ "message", "agent", "host", "input", "event", "log", "ecs", "tags", "@version", "@timestamp" ]
}}


}}


# output {{
#   stdout {{ codec => rubydebug {{ metadata => true }} }}
# }}

output {{
  elasticsearch {{
    hosts => ["{logstash_pipeline_config_args["elasticsearch_uri"]}"]
    index => "{logstash_pipeline_config_args["index_name"]}"
    pipeline => "timestamp_pipeline"
  }}
}}

"""