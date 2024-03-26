# smartMe data processing
This python code serves the purpose of preprocessing the data collected in the
context of the smartNIALMeter dataset. The relevant publication is provided at
the bottom of the page.

The preprocessing consists of following steps:  
1. For each file per meter, missing power values are calulated and rows with power factor or active power values below zero are dropped. Additional cleaning is performed

    
### Generate the preprocessed dataset
The 'raw' data is loaded and the following preprocessing steps are applied:
- Load data
- Calculate missing power values. 
- Remove all inconsistent values: rows with a power factor or an active power
  below zero are dropped.
- Remove all rows containing NAN values
- Resample data to even seconds, for example 07:00:03.345 to 07:00:05
- Save data

Details to the processing steps can be found in the publication, see below.
The output of this processing step is referred to as 'preprocessed' data in the
publication.

To run the preprocessing in a docker container, refer to the below command.

    docker-compose run --rm -- preprocess

**Configuration**:  
The script requires `h5`-files. The path to these files as well as the path to the output directory can be adjusted in the file `config.ini` using the variables: 
* `path_to_raw` - location of the raw data in `.h5`-format.
* `path_to_preprocessed` - path for the output.
* `path_to_metadata` - path to the metadata. Required that correct missing
  power values get calculated.

You should be aware that the paths need to be relative to the current folder
because the current folder will be mounted as a volume in the docker container.

**Data structure**:  
The files generated after the main preprocessing step are saved in 
*data/preprocessed/building_xx/Application.h5*.

## Adapting the preprocessing
If you want to adapt the preprocessing you can adapt the preprocessing steps in the `src/entrypoints/preprocess.py` file. 
       
## Dependencies
The dependencies of the script can be found in the requirements.txt file.

## Publication
10.5281/zenodo.10875988
