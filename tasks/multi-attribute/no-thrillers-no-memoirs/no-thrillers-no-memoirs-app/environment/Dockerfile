# syntax=docker/dockerfile:1.7
#
# ReadAndReel OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ReadAndReel native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", ReadAndReel writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ReadAndReel app + its autostart launcher.
COPY readandreel.py /opt/readandreel/readandreel.py
COPY start-readandreel.sh /opt/readandreel/start-readandreel.sh
RUN chmod +x /opt/readandreel/start-readandreel.sh

WORKDIR /app
