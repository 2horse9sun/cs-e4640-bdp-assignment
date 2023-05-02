def gen_logstash_config(logstash_config_args):
    return f"""
api.http.host: 0.0.0.0
api.http.port: {logstash_config_args["logstash_output_port"]}

queue.type: {logstash_config_args["queue_type"]}

xpack.monitoring.enabled: false

log.level: info
path.logs: /var/log/logstash/

"""