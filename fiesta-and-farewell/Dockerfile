FROM ubuntu

RUN apt-get update && apt-get install -y socat && rm -rf /var/lib/apt/lists/* && \
  useradd --system --create-home --home-dir /home/blackbox --shell /usr/sbin/nologin blackbox && \
  mkdir -p /srv/app

WORKDIR /srv/app

COPY challenge/ /srv/app/
RUN mv /srv/app/blackbox /usr/local/bin/blackbox

RUN chmod 0555 /srv/app/run.sh /usr/local/bin/blackbox && chown -R blackbox:blackbox /srv/app

USER blackbox
EXPOSE 1337

ENTRYPOINT ["/srv/app/run.sh"]