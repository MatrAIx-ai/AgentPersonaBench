# syntax=docker/dockerfile:1.7
#
# ClassPairsSaturday OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ClassPairsSaturday native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", ClassPairsSaturday writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ClassPairsSaturday app + its autostart launcher.
COPY classpairssaturday.py /opt/classpairssaturday/classpairssaturday.py
COPY start-classpairssaturday.sh /opt/classpairssaturday/start-classpairssaturday.sh
RUN chmod +x /opt/classpairssaturday/start-classpairssaturday.sh

WORKDIR /app
