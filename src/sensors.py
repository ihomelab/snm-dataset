"""This module implements the different sensors used in the data logging and implements a factory method to chose the
right sensor class automatically."""

import csv
import dask.dataframe as dd
import numpy as np
import os
import sys
import yaml

sys.path.append(os.getcwd())
from src.helpers import parse_meter


class Sensor:
    """The Sensor class is the parent class for all sensors used in the data logging."""

    sensor_name = ""

    def __init__(self):
        """Sets the application name to the class

        Parameters:
            application (str): Name of the application
        """
        self.application = ""
        self.building = ""
        self.columns = None

    def set_application(self, application):
        self.application = application

    def set_building(self, building):
        self.building = building

    def get_datatype(self):
        datatype = {}
        for i, elem in enumerate(self.header):
            if i == 0:
                datatype[elem] = "str"
            else:
                datatype[elem] = "float64"
        return datatype

    def calculate_missing_values(self, df: dd) -> dd:
        """Calculate active, reactive power of SmartMe 3-phase plug (METER3)

        Each dataframe in the list contains at least the following columns:

        +----------------+--------------+----------------+
        | power apparent | power active | power reactive |
        +================+==============+================+
        |                |              |                |
        +----------------+--------------+----------------+

        Parameters:
            df: A dask dataframe with values to be calculated
        Returns:
            The dask dataframe with calculated and added power values
        """
        return df

    def calculate_onoff_values(self, df: dd) -> dd:
        """Calculate the onoff values by applying a threshold.

         Parameters:
            df: A dask dataframe with values to be calculated
        Returns:
            The dask dataframe with calculated and added power values
        """
        return df


class CIIAdapter(Sensor):
    """The CII subclass for the Sensor class. Specifies the length and the names of the header."""

    def __init__(self):
        Sensor.__init__(self)

    sensor_name = "smart-me-cii"
    header_length = 10
    header = [
        "timestamp",
        "Voltage L1",
        "Voltage L2",
        "Voltage L3",
        "Current L1",
        "Current L2",
        "Current L3",
        "Power Factor L1",
        "Power Factor L2",
        "Power Factor L3",
    ]

    def calculate_missing_values(self, df: dd) -> dd:
        """Calculate active, reactive power of cii (CII) interface for all three phases

        Each phase of the dataframe in the list contains the following columns:

        +------------+------------+--------------+----------------+--------------+----------------+
        | voltage    | current    | power factor | power apparent | power active | power reactive |
        +============+============+==============+================+==============+================+
        |            |            |              |                |              |                |
        +------------+------------+--------------+----------------+--------------+----------------+

        Parameters:
            df: The dask dataframe with the raw data
        Returns:
            A dask dataframe with the added calculated values
        """
        result = []
        for i in range(1, 4):
            # get voltage, current and power factor for each line
            df[f"Apparent Power L{i}"] = (
                df[f"Voltage L{i}"] * df[f"Current L{i}"]
            )
            df[f"Active Power L{i}"] = (
                df[f"Apparent Power L{i}"] * df[f"Power Factor L{i}"]
            )
            df[f"Reactive Power L{i}"] = np.sqrt(
                df[f"Apparent Power L{i}"] ** 2 - df[f"Active Power L{i}"] ** 2
            )
        return df


class SinglePhaseSensor(Sensor):
    """The CII subclass for the Sensor class. Specifies the length and the names of the header."""

    def __init__(self):
        Sensor.__init__(self)

    sensor_name = "smart-me-1-phase"
    header_length = 3
    header = ["timestamp", "Active Power", "Power Factor"]

    def calculate_missing_values(self, df: dd) -> dd:
        """Calculate active, reactive power of cii (CII) interface for all three phases

        Each dataframe in the list contains the following columns:
        +----------------+---------------+----------------+
        | Active Power   | Reactive Power| Apparent Power |
        +================+===============+================+
        |                |               |                |
        +----------------+---------------+----------------+

        Parameters:
            df: The dask dataframe with the raw data
        Returns:
            A dask dataframe with the added calculated values
        """
        # Calculate the missing values
        df["Apparent Power"] = df["Active Power"] / df["Power Factor"]
        # handle case where power factor is zero
        df[df["Active Power"] == 0]["Apparent Power"] = 0
        # Calculate missing reactive power
        df["Reactive Power"] = np.sqrt(
            df["Apparent Power"] ** 2 - df["Active Power"] ** 2
        )
        return df


class ThreePhaseSensor(Sensor):
    """The Three phase Sensor subclass for the Sensor class. Specifies the length and the names of the header."""

    def __init__(self):
        Sensor.__init__(self)

    sensor_name = "smart-me-3-phase"
    header_length = 7
    header = [
        "timestamp",
        "Active Power L1",
        "Active Power L2",
        "Active Power L3",
        "Reactive Power L1",
        "Reactive Power L2",
        "Reactive Power L3",
    ]

    def calculate_missing_values(self, df: dd) -> dd:
        """Calculate active, reactive power of SmartMe 3-phase plug (METER3)

        Each dataframe in the list contains the following columns:

        +----------------+--------------+----------------+
        | power apparent | power active | power reactive |
        +================+==============+================+
        |                |              |                |
        +----------------+--------------+----------------+

        Parameters:
            df: A dask dataframe with values to be calculated
        Returns:
            The dask dataframe with calculated and added power values
        """
        result = []
        # Calculate the missing apparent power for each phase
        for i in range(1, 4):
            df[f"Apparent Power L{i}"] = np.sqrt(
                df[f"Active Power L{i}"] ** 2 + df[f"Reactive Power L{i}"] ** 2
            )
        return df


class Plug(Sensor):
    """The Plug subclass for the Sensor class. Specifies the length and the names of the header."""

    def __init__(self):
        Sensor.__init__(self)

    sensor_name = "smart-me-plug"
    header_length = 3
    header = ["timestamp", "Active Power", "Power Factor"]

    def calculate_missing_values(self, df: dd) -> dd:
        """Calculate active, reactive power of SmartMe plug (PLUG)

        The resulting dataframe contains the following columns:

        +----------------+--------------+----------------+
        | power apparent | power active | power reactive |
        +================+==============+================+
        |                |              |                |
        +----------------+--------------+----------------+

        Parameters:
            df: A dask dataframe with missing power values
        Returns:
            A dask dataframe with calculated and added power values
        """
        # Calculate the missing values
        df["Apparent Power"] = df["Active Power"] / df["Power Factor"]
        # handle case where power factor is zero
        df["Apparent Power"] = df["Apparent Power"].where(
            df["Active Power"] > 0, other=0.0
        )
        df["Reactive Power"] = np.sqrt(
            df["Apparent Power"] ** 2 - df["Active Power"] ** 2
        )
        return df


class OnOffSensor(Sensor):
    """The On Off Sensor subclass for the Sensor class. Specifies the length and the names of the header."""

    def __init__(self):
        Sensor.__init__(self)
        self.threshold = None
        self.filter_length = None
        self.columns = ["timestamp", "ADC-Value"]

    def set_treshold(self, threshold):
        self.threshold = threshold

    def set_filter(self):
        # Read the configuration from the file configuration/onoff_threshold.csv and set the variables accordingly
        with open("configuration/onoff_threshold.csv", "r") as file:
            reader = csv.reader(file, skipinitialspace=True)
            found = False
            for row in reader:
                if row[0] == self.building and row[1] == self.application:
                    found = True
                    self.filter_length = None if row[3] == "None" else int(row[3])
                    self.threshold = int(row[2])
                    break
            if not found:
                print(
                    "Could not find the threshold for",
                    self.building,
                    self.application,
                )

    sensor_name = "on_off_sensor"
    header_length = 6
    header = ["timestamp", "UUID", "RSSI", "Counter", "Battery", "ADC-Value"]

    def calculate_onoff_values(self, df: dd) -> dd:
        """Function to handle missing values in the data of the OnOff plugs.

        This function deletes the not used columns (ADC-Value) of the provided dataframe.

        Parameters:
              df: Dask dataframe with values to be deleted
        Returns:
             A dask dataframe with deleted values
        """
        self.set_filter()
        f = (
            lambda x: True
            if self.threshold is not None and x > self.threshold
            else False
        )
        if self.filter_length:
            pass
            df["On"] = (
                df["ADC-Value"]
                .shift(int(-self.filter_length / 2))
                .rolling(self.filter_length)
                .median()
                .apply(f, meta=("ADC-Value", "bool"))
                .compute()
            )
        else:
            df["On"] = df["ADC-Value"].apply(f, meta=("ADC-Value", "bool")).compute()
        del df["ADC-Value"]
        return df


class SensorFactory:
    """This class implements the factory for the generation of the Sensor subclasses, depending on the name of the
    sensor. The mapping of the name to the corresponding subclass is specified in the variable mapping.
    """

    def __init__(self, path="smart-me-data-processing/data/config"):
        """Initiate the SensorFactory class with the path to the config file

        Parameters:
            path (str): Path to the config files of the buildings
        """
        self.path_to_config = path

    mapping = {
        "smart-me-cii": CIIAdapter,
        "smart-me-3-phase": ThreePhaseSensor,
        "smart-me-plug": Plug,
        "on_off_sensor": OnOffSensor,
        "smart-me-1-phase": SinglePhaseSensor,
    }

    mapping_metadata = {
        "CII-Adapter": CIIAdapter,
        "smart-me_3-phase": ThreePhaseSensor,
        "smart-me_plug": Plug,
        "on_off_sensor": OnOffSensor,
        "smart-me_1-phase": SinglePhaseSensor,
    }

    def make(
        self,
        building: str,
        meter_key: str,
        config_path="./data/config",
        use_config=True,
        configuration={},
    ) -> Sensor:
        """Make the subclass corresponding to the application name.

        This function creates the class according to the building and meter key by reading the config file from the
        building and getting the meter type from the respecting config key.

        Parameters:
            building (str): The number of the building in the form building_xx
            meter_key (str): The key of the installed meter
            config_path (str): The path to the directory with the config files (default=./data/config)
            use_config (bool): Determines if the config files are used or the specified meter_type
            meter_type (str): If use_config is false, then this string is used to determine the right sensor
        Returns:
            The Sensor subclass corresponding to the name, specified in SensorFactory.mapping. False if the meter can
            not be found in the config file.
        """
        # Get the sensor name from the json config
        configuration = parse_meter(config_path, building, meter_key)
        # Get the right class and extract the application from the meter type
        if configuration:
            new_class = self.mapping[configuration["meter-type"]]()
            application = configuration["meter-name"].split()[1]
            new_class.set_application(application)
            new_class.set_building(building)
        else:
            print("The meter " + str(meter_key) + " has no config entry!")
            new_class = False
        return new_class

    def make_metadata(
        self, building: str, application: str, metadata_path="data/metadata"
    ) -> Sensor:
        """Make the subclass corresponding to the application name.

        This function creates the class according to the building and meter key by reading the config file from the
        building and getting the meter type from the respecting config key.

        Parameters:
            building (str): The number of the building in the form building_xx
            application (str): The name of the measured application
            metadata_path (str): The path to the directory with the metadata files (default=./data/metadata)
        Returns:
            The Sensor subclass corresponding to the name, specified in SensorFactory.mapping.
        """
        # Create path
        metadata_path = os.path.join(
            metadata_path, "building" + str(int(building[-2:])) + ".yaml"
        )
        # Get the sensor name from the yaml file
        with open(metadata_path, "r") as stream:
            configuration = yaml.safe_load(stream)
        # Get the right meter
        meter_type = None
        for meter, data in configuration["elec_meters"].items():
            if data["data_location"] == building + "/" + application + ".h5":
                try:
                    meter_type = data["device_model"]
                    break
                except KeyError:
                    print("Meter: ", meter)
                    print("Data: ", data)
                    print("building: ", building)
                    print("Application: ", application)
        # Get the right class and extract the application from the meter type
        new_class = self.mapping_metadata[meter_type]()
        new_class.set_application(application)
        new_class.set_building(building)
        return new_class
