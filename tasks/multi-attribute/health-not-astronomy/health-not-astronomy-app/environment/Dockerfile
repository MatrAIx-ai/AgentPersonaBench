# syntax=docker/dockerfile:1.7
#
# PassesScienceFestival OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the PassesScienceFestival native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book day passes", PassesScienceFestival writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The PassesScienceFestival app + its autostart launcher.
COPY passessciencefestival.py /opt/passessciencefestival/passessciencefestival.py
COPY start-passessciencefestival.sh /opt/passessciencefestival/start-passessciencefestival.sh
RUN chmod +x /opt/passessciencefestival/start-passessciencefestival.sh

WORKDIR /app
