import os
import sys

sys.path.append(os.getcwd())
from src.correlator.const import PHASE_CHANGES


def calculate_missing_power(dfs: dict) -> dict:
    """
    Calculate the missing power for all read sensors.

    Parameters:
        dfs: A dict of dask dataframes with all sensor data
        path_to_config (str): Path to the config file
    Returns:
        A dict of dask dataframes with added power values to the sensor data
    """
    print("Calculating the missing power values...")
    for building, meter_list in dfs.items():
        for sensor, df in meter_list.items():
            dfs[building][sensor] = sensor.calculate_missing_values(df)
    return dfs


def calculate_onoff_values(dfs: dict) -> dict:
    """
    Calculate the missing power for all read sensors.

    Parameters:
        dfs: A dict of dask dataframes with all sensor data
        path_to_config (str): Path to the config file
    Returns:
        A dict of dask dataframes with added power values to the sensor data
    """
    print("Calculating the missing power values...")
    for building, meter_list in dfs.items():
        for sensor, df in meter_list.items():
            dfs[building][sensor] = sensor.calculate_onoff_values(df)
    return dfs


def remove_duplicate_values(dfs: dict) -> dict:
    """
    Remove all duplicated values from the dataset

    In the case of connection issues, the measurement unit returnes the same value. These duplicated values with the
    same timestamp need to be removed, since they are not needed and take up disk space.

    Parameters:
        dfs: A dict of dask dataframes
    Returns:
        The dict of dask dataframes with removed duplicated values.
    """
    print("Removing duplicates...")
    for building, meter_list in dfs.items():
        for sensor, df in meter_list.items():
            old_length = df.shape[0].compute()
            df = df.drop_duplicates(subset=["timestamp"], split_out=10)
            dfs[building][sensor] = df
            new_length = df.shape[0].compute()
            print(
                " ",
                sensor.application,
                "dropped ",
                old_length - new_length,
                "values of",
                old_length,
            )
    return dfs


def remove_phase_changes(dfs: dict) -> dict:
    """
    In some buildings the meters are switched between appliances. Remove those buildings.

    Parameters:
        dfs: A dict of dask dataframes
    Returns:
        The dict of dask dataframes with removed values for phase changes.
    """
    print("Removing phase changes...")
    for building, meter_list in dfs.items():
        for sensor, df in meter_list.items():
            if (
                building in PHASE_CHANGES
                and sensor.application in PHASE_CHANGES[building]
            ):
                start = PHASE_CHANGES[building][sensor.application]["remove_start"]
                end = PHASE_CHANGES[building][sensor.application]["remove_end"]

                if start == "":
                    df = df.loc[end:]
                elif end == "":
                    df = df.loc[:start]
                else:
                    raise NotImplementedError(
                        "Cannot slice a middle part away currently!"
                    )

                dfs[building][sensor] = df
    return dfs


def handle_inconsistent_values(dfs: dict) -> dict:
    """
    Replace values with NaN in the following cases: 1) `power factor` < 0, 2) `power active` < 0

    Parameters:
        dfs: A dict of dask dataframes containing the data
    Return:
        A dask dataframe with the inconsistent values set to 0
    """
    print("Removing improbable values...")
    for building, meter_list in dfs.items():
        for sensor, df in meter_list.items():
            # Check for negative power factors
            if "Power Factor" in df.columns:
                locations = df["Power Factor"] < 0
                # Check if there are locations with inconsistent values, else skip
                num = locations.sum().compute()
                print(" Found {} power factor values < 0. Set them to NaN".format(num))
                if num > 0:
                    df["Power Factor"] = df["Power Factor"].where(~locations)
            # Check for negative active power
            if "Active Power" in df.columns:
                locations = df["Active Power"] < 0
                num = locations.sum().compute()
                print(" Found {} active power values < 0. Set them to NaN".format(num))
                if num > 0:
                    df["Active Power"] = df["Active Power"].where(~locations)
            dfs[building][sensor] = df
    return dfs


def remove_NaN(dfs: dict) -> dict:
    """
    Remove all rows with invalid (NaN) values

    Some values which could not be read or are faulty are saved as NaN. Since they are useless, the can be removed.

    Parameters:
        dfs: A dict of dataframes
    Returns:
        The dict of dataframes with removes NaN values
    """
    print("Removing NaN...")
    for building, meter_list in dfs.items():
        for sensor, df in meter_list.items():
            old_length = df.shape[0].compute()
            dfs[building][sensor] = df.dropna()
            print(
                " Dropped",
                old_length - df.shape[0].compute(),
                "lines of",
                old_length,
            )
    return dfs


def resample_mean(partition, freq):
    return partition.resample(freq).mean()

def interpolate(partition):
    return partition.interpolate(method='linear')

def resample(dfs: dict) -> dict:
    """
    Takes the dask dataframes and linearly interpolates the data, to get to a constant
    sampling time of 5s over all appliances.

    Parameters:
        dfs: A dict of dask dataframes
    Returns:
        A dict of pandas dataframes with resampled and interpolated values to 5s
    """
    print("Resampling...")
    for building, meter_list in dfs.items():
        for sensor, df in meter_list.items():
            df = df.map_partitions(lambda partition: resample_mean(partition, '100ms'))
            df = df.map_partitions(lambda partition: interpolate(partition))
            df = df.map_partitions(lambda partition: resample_mean(partition, '5s'))
            dfs[building][sensor] = df.compute()
    return dfs