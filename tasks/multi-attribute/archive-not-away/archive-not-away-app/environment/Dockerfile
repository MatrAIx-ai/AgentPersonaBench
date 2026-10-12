# syntax=docker/dockerfile:1.7
#
# ReadersDiary OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ReadersDiary native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book events", ReadersDiary writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ReadersDiary app + its autostart launcher.
COPY readersdiary.py /opt/readersdiary/readersdiary.py
COPY start-readersdiary.sh /opt/readersdiary/start-readersdiary.sh
RUN chmod +x /opt/readersdiary/start-readersdiary.sh

WORKDIR /app
