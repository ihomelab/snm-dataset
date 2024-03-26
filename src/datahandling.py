import dask.dataframe as dd
import glob
import os
import pandas as pd
from pathlib import Path
import sys
sys.path.append(os.getcwd())

from src import sensors


def save_to_hdf5(dfs, path_to_data_save):
    """Saves the provided dict of dask dataframes with the keys as the name of the building and the values as a list of
    dataframes, one per meter key.

    Every dataframe, there is one per meter, is stored in a hdf5 format in the directory
    path_to_data_save/building_xx/meter_key.h5

    Parameters:
        dfs: a dict of dask dataframes with the keys as the name of the building and the values as a list of
        dataframes, one per meter key.
        path_to_data_save: Folder in which the hdf5 files will be saved in the structure path_to_data_save/building_xx/
        meter.h5.
    Returns:
        The parameter dfs
    """
    # Add backslash if missing
    if path_to_data_save[-1] != ("\\" or "/"):
        path_to_data_save = path_to_data_save + "/"
    #  Check if path exist, else create it
    Path(path_to_data_save).mkdir(parents=True, exist_ok=True)
    # Go through every meter and store to hdf
    for building, meter_list in dfs.items():
        for sensor, df in meter_list.items():
            #  Check if path exist, else create it
            Path(path_to_data_save + building).mkdir(parents=True, exist_ok=True)
            # Save to hdf
            path = os.path.join(
                path_to_data_save, building, str(sensor.application) + ".h5"
            )
            #print("Repartition dataset")
            #df = df.repartition(npartitions=1)
            print("Saving the meter " + str(sensor.sensor_name) + " to " + str(path))
            if isinstance(df, pd.DataFrame):
                df.to_hdf(path, "data", mode="w", errors="ignore")
            elif isinstance(df, dd.DataFrame):
                df.to_hdf(path, "data", mode="w", errors="ignore", compute=True)


def load_from_hdf5(path_to_data: str, path_to_metadata: str, buildings=[]) -> dd:
    """Load the data from hdf5 files in the structure smart-me-data/building_xx/meter.h5

    Parameters:
        path_to_data: Path to the smart-me-data folder
        path_to_metadata: Path to the smart-me metadata to read the meter-type
    Returns:
        A dict where the key is the name of the building and the value is a List of dask dataframes, one dataframe
        per meter.
    """
    dfs = {}
    path_to_data = os.path.join(os.getcwd(), path_to_data)
    print("Loading the data from " + str(path_to_data))
    for building in glob.glob(path_to_data + r"/*"):
        # Get name of the building
        if buildings and int(building[-2:]) not in buildings:
            continue
        print("Found the building " + str(building))
        building_xx_index = building.find("building_")
        building_name = building[building_xx_index : building_xx_index + 11]
        dfs[building_name] = {}
        for application in glob.glob(building + r"/*"):
            print(" Reading", os.path.basename(application))
            df = dd.read_hdf(application, "data*", mode="r", sorted_index=True)
            #df = pd.read_hdf(application, "data*", 'mode="r", )
            # Repartition the dataframe
            df = df.repartition(partition_size="10MB")
            # Get path of the application
            application = os.path.basename(application)
            application = os.path.splitext(application)[0]
            # Get the sensor
            sensor = sensors.SensorFactory().make_metadata(
                building_name, application, metadata_path=path_to_metadata
            )
            dfs[building_name][sensor] = df
            #print(df.head())
    return dfs
