# Start with the ZED SDK Docker image
FROM stereolabs/zed:4.1-py-devel-jetson-jp6.0.0 AS zed-sdk
FROM stereolabs/zed:4.1-tools-devel-jetson-jp6.0.0 AS zed-sdk-tools

#FROM docker.cuauv.org/phusion-baseimage-aarch64:0.11 as cuauv
FROM py310:r36.3.0 AS cuauv 

RUN rm -f /etc/apt/.apt.conf.d/docker-clean

# setup pip caching
ENV PIP_CACHE_DIR=/var/cache/buildkit/pip
RUN mkdir -p ${PIP_CACHE_DIR}

# MERGE IMPLEMENTATION
COPY --from=zed-sdk /usr/local/zed /usr/local/zed
COPY --from=zed-sdk-tools /usr/local/zed /usr/local/zed

# 5/4/24 : reverted to r35.4.1 because im guessing this doesnt have zed bullsht - Anthony
RUN rm -f /etc/service/sshd/down && \
    sed -i'' 's/http:\/\/archive.ubuntu.com/http:\/\/us.archive.ubuntu.com/' /etc/apt/sources.list && \
    sed -i'' 's/http:\/\/ports.ubuntu.com/http:\/\/us.ports.ubuntu.com/' /etc/apt/sources.list

RUN mkdir /dependencies && chmod -R 755 /dependencies

COPY ./install /dependencies

RUN bash /dependencies/aptstrap.sh /dependencies/foundation-install.sh

RUN bash /dependencies/aptstrap.sh /dependencies/python-latest-install.sh

RUN bash /dependencies/aptstrap.sh /dependencies/python-latest-pip-install.sh

RUN bash /dependencies/aptstrap.sh /dependencies/ueye-install.sh

RUN bash /dependencies/zed-install.sh

# RUN bash /dependencies/aptstrap.sh /dependencies/jetson-install.sh

# RUN bash /dependencies/aptstrap.sh /dependencies/opencv-install.sh

# We don't currently use caffe and build is failing with Python 3.8.
#RUN bash /dependencies/aptstrap.sh /dependencies/caffe-install.sh

RUN bash /dependencies/setup-user.sh

# RUN bash /dependencies/aptstrap.sh /dependencies/ocaml-install.sh
# RUN setuser software /dependencies/ocaml-user-install.sh

RUN bash /dependencies/aptstrap.sh /dependencies/node-install.sh

RUN /dependencies/ripgrep-install.sh

RUN bash /dependencies/aptstrap.sh /dependencies/apt-install.sh

RUN bash /dependencies/aptstrap.sh /dependencies/pip-install.sh

RUN bash /dependencies/aptstrap.sh /dependencies/misc-install.sh

RUN cp -r /dependencies/runit/* /etc/service/

RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache/ /dependencies/
    
USER software
WORKDIR /home/software/cuauv/software_stack

RUN echo "CUAUV Docker container should be started through a wrapping tool (cdw or docker-helper.sh)"

CMD ["/home/software/cuauv/workspaces/repo/link-stage/trogdor start"]