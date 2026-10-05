# syntax=docker/dockerfile:1.7
#
# KitchenAndConcert OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the KitchenAndConcert native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", KitchenAndConcert writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The KitchenAndConcert app + its autostart launcher.
COPY kitchenandconcert.py /opt/kitchenandconcert/kitchenandconcert.py
COPY start-kitchenandconcert.sh /opt/kitchenandconcert/start-kitchenandconcert.sh
RUN chmod +x /opt/kitchenandconcert/start-kitchenandconcert.sh

WORKDIR /app
