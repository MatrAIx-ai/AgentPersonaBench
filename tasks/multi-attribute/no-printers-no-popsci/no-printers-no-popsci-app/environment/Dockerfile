# syntax=docker/dockerfile:1.7
#
# LibraryAndWorkshop OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the LibraryAndWorkshop native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book visits", LibraryAndWorkshop writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The LibraryAndWorkshop app + its autostart launcher.
COPY libraryandworkshop.py /opt/libraryandworkshop/libraryandworkshop.py
COPY start-libraryandworkshop.sh /opt/libraryandworkshop/start-libraryandworkshop.sh
RUN chmod +x /opt/libraryandworkshop/start-libraryandworkshop.sh

WORKDIR /app
