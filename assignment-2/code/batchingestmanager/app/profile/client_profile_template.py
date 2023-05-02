import uuid

def gen_client_profile(client_info):
    return {
        "client_id": str(uuid.uuid4()),
        "client_name": client_info["name"],
        "max_file_size": 500000000,
        "max_number_of_files": 100,
        "file_format": ["csv", "txt"],
        "max_filebeat_workers": 1,
        "max_logstash_workers": 1
    }