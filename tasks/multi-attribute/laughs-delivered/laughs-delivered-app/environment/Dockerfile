# syntax=docker/dockerfile:1.7
#
# SupperStream OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SupperStream native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book bundles", SupperStream writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SupperStream app + its autostart launcher.
COPY supperstream.py /opt/supperstream/supperstream.py
COPY start-supperstream.sh /opt/supperstream/start-supperstream.sh
RUN chmod +x /opt/supperstream/start-supperstream.sh

WORKDIR /app
