# syntax=docker/dockerfile:1.7
#
# ProjectorAndAmp OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ProjectorAndAmp native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book nights", ProjectorAndAmp writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ProjectorAndAmp app + its autostart launcher.
COPY projectorandamp.py /opt/projectorandamp/projectorandamp.py
COPY start-projectorandamp.sh /opt/projectorandamp/start-projectorandamp.sh
RUN chmod +x /opt/projectorandamp/start-projectorandamp.sh

WORKDIR /app
