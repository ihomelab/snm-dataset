from configparser import ConfigParser


def parse_config(path_to_config="./config.ini") -> dict:
    """This module reads a config.ini file.

    Parameters:
        path_to_config (str): path to the config file. If none is specified, this defaults to
        smart_me_data_processing/config.ini

    Returns:
        A dict with all configuration parameters
    """
    print("Reading the configuration from " + str(path_to_config))
    parser = ConfigParser()
    parser.read(path_to_config)
    configuration = parser["Configuration"]
    return dict(configuration.items())