# syntax=docker/dockerfile:1.7
#
# AppHarbor OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE +
# xdotool + scrot) PLUS Python Tkinter and the AppHarbor native GUI app
# baked in. The CUA agent (persona-computer-1) drives it by screenshot +
# coordinate click; on confirm the app writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY app.py /opt/opensourcefan/app.py
COPY start-app.sh /opt/opensourcefan/start-app.sh
RUN chmod +x /opt/opensourcefan/start-app.sh

WORKDIR /app
