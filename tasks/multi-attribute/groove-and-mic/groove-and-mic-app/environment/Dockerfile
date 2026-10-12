# syntax=docker/dockerfile:1.7
#
# PackagesNight OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the PackagesNight native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book packages", PackagesNight writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The PackagesNight app + its autostart launcher.
COPY packagesnight.py /opt/packagesnight/packagesnight.py
COPY start-packagesnight.sh /opt/packagesnight/start-packagesnight.sh
RUN chmod +x /opt/packagesnight/start-packagesnight.sh

WORKDIR /app
