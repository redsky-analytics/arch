from pathlib import Path

def setup_logging(target):

    fn = '5-queued-stderr-json-file'
    config_file = Path(__file__).parent / "logging_configs" / f"{fn}.json"

    with open(config_file) as f_in:
        config = json.load(f_in)

    config['handler']['file_json']['filename'] = target


    Path(target).touch(exist_ok=True)
    logging.config.dictConfig(config)
