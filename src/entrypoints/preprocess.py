import os
import sys
sys.path.append(os.getcwd())
from dask.distributed import Client
from datetime import datetime

from src import preprocessing, helpers
from src.datahandling import load_from_hdf5, save_to_hdf5


def main():
    # time.sleep(5)

    # Parse the config file
    config = helpers.parse_config("./config.ini")

    # Get the time to see how long the script took
    start_time = datetime.now()

    # Do the preprocessing
    print("Starting the preprocessing...")
    dfs = load_from_hdf5(config["path_to_hdf_raw"], config["path_to_metadata"])
    dfs = preprocessing.calculate_missing_power(dfs)
    dfs = preprocessing.handle_inconsistent_values(dfs)
    dfs = preprocessing.remove_NaN(dfs)
    dfs = preprocessing.remove_phase_changes(dfs)
    dfs = preprocessing.resample(dfs)
    save_to_hdf5(dfs, config["path_to_hdf_preprocessed"])

    # Print the runtime
    print("The script took " + str(datetime.now() - start_time) + " to finish")


if __name__ == "__main__":
    try:
        # Setup dask distributed client
        client = Client()
        print("The dask client dashboard can be found under " + str(client.dashboard_link))
        main()
    finally:
        client.shutdown()
