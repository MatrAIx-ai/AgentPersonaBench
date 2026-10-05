# syntax=docker/dockerfile:1.7
#
# BillDouble OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the BillDouble native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book nights", BillDouble writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The BillDouble app + its autostart launcher.
COPY billdouble.py /opt/billdouble/billdouble.py
COPY start-billdouble.sh /opt/billdouble/start-billdouble.sh
RUN chmod +x /opt/billdouble/start-billdouble.sh

WORKDIR /app
