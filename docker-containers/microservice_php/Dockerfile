FROM microservice
MAINTAINER Cerebro <cerebro@ganymede.eu>

ENV MICROSERVICE_PHP_APT_GET_UPDATE_DATE 2015-05-25
RUN apt-get update

RUN apt-get install -y apache2 php5 php5-mysql php5-curl

# Apache configuration.
ADD ./supervisor/apache2.conf /etc/supervisor/conf.d/
ADD ./apache2_vhost.conf /etc/apache2/sites-available/apache2_vhost.conf
RUN ln -s /etc/apache2/sites-available/apache2_vhost.conf /etc/apache2/sites-enabled/apache2_vhost.conf
RUN rm -f /etc/apache2/sites-enabled/000-default.conf
RUN echo "StartServers 1\nMinSpareServers 1\nMaxSpareServers 3" >> /etc/apache2/apache2.conf

ADD . /opt/microservice_php
RUN chmod +x /opt/microservice_php/run_apache2.sh

EXPOSE 80
