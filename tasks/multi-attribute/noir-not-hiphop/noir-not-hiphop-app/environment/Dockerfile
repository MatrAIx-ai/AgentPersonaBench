# syntax=docker/dockerfile:1.7
#
# RiffAndReel OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the RiffAndReel native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book nights", RiffAndReel writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The RiffAndReel app + its autostart launcher.
COPY riffandreel.py /opt/riffandreel/riffandreel.py
COPY start-riffandreel.sh /opt/riffandreel/start-riffandreel.sh
RUN chmod +x /opt/riffandreel/start-riffandreel.sh

WORKDIR /app
