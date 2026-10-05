# syntax=docker/dockerfile:1.7
#
# ShopKeeper OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ShopKeeper native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user checks out, ShopKeeper writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ShopKeeper app + its autostart launcher.
COPY shopkeeper.py /opt/shopkeeper/shopkeeper.py
COPY start-shopkeeper.sh /opt/shopkeeper/start-shopkeeper.sh
RUN chmod +x /opt/shopkeeper/start-shopkeeper.sh

WORKDIR /app
