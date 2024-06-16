from pathlib import Path
import json
import logging.config
import logging.handlers

def setup_logging(target):

    fn = '5-queued-stderr-json-file'
    config_file = Path(__file__).parent / "logging_configs" / f"{fn}.json"

    with open(config_file) as f_in:
        config = json.load(f_in)

    print(config.keys())
    config['handlers']['file_json']['filename'] = target

    Path(target).parent.mkdir(parents=True, exist_ok=True)

    Path(target).touch(exist_ok=True)
    logging.config.dictConfig(config)

if __name__ == '__main__':
    setup_logging('localdata/b/c/d.jsonl')
    logger = logging.getLogger()
    logger.warning('aa')