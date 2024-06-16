import pathlib

def setup_logging(target):
    fn = '5-queued-stderr-json-file'
    config_file = pathlib.Path(f"logging_configs/{fn}.json")

    with open(config_file) as f_in:
        config = json.load(f_in)
    config['handler']['file_json']['filename'] = target
    logging.config.dictConfig(config)
