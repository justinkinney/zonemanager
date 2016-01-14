FROM ubuntu
MAINTAINER Justin Kinney

ENV DATA_DIR=/data \
    BIND_USER=bind

# install bind9
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y bind9

COPY bind_setup.sh /tmp/bind_setup.sh
RUN /tmp/bind_setup.sh

EXPOSE 53/udp
VOLUME ["${DATA_DIR}"]

CMD ["/usr/sbin/named"]
