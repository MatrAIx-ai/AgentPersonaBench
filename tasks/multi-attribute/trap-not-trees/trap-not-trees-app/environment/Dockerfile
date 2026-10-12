# syntax=docker/dockerfile:1.7
#
# CardSaturday OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the CardSaturday native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book bundles", CardSaturday writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The CardSaturday app + its autostart launcher.
COPY cardsaturday.py /opt/cardsaturday/cardsaturday.py
COPY start-cardsaturday.sh /opt/cardsaturday/start-cardsaturday.sh
RUN chmod +x /opt/cardsaturday/start-cardsaturday.sh

WORKDIR /app
