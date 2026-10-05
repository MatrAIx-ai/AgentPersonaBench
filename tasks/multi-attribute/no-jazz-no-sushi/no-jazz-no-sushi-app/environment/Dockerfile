# syntax=docker/dockerfile:1.7
#
# KitchenAndHall OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the KitchenAndHall native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", KitchenAndHall writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The KitchenAndHall app + its autostart launcher.
COPY kitchenandhall.py /opt/kitchenandhall/kitchenandhall.py
COPY start-kitchenandhall.sh /opt/kitchenandhall/start-kitchenandhall.sh
RUN chmod +x /opt/kitchenandhall/start-kitchenandhall.sh

WORKDIR /app
