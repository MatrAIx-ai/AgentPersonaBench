# syntax=docker/dockerfile:1.7
#
# PlatesAndPages OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the PlatesAndPages native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", PlatesAndPages writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The PlatesAndPages app + its autostart launcher.
COPY platesandpages.py /opt/platesandpages/platesandpages.py
COPY start-platesandpages.sh /opt/platesandpages/start-platesandpages.sh
RUN chmod +x /opt/platesandpages/start-platesandpages.sh

WORKDIR /app
