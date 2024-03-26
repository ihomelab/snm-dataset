#FROM continuumio/miniconda3:4.8.2
FROM continuumio/miniconda3:23.10.0-1

RUN apt-get update 
RUN apt-get -y install gcc
COPY requirements.txt .
RUN pip install -r requirements.txt

ARG USER="ihl"
ARG UID="1000"
ARG GID="100"

ENV SHELL=/bin/bash \
    USER=$USER \
    HOME=/home/$USER \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US.UTF-8

RUN useradd -m -s /bin/bash -N -u $UID $USER

WORKDIR /home/$USER/snm-data-publication_code

ENV PYTHONPATH "${PYTHONPATH}:/home/$USER/snm-data-publication_code"