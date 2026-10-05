# syntax=docker/dockerfile:1.7
#
# SupperAndSet OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SupperAndSet native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", SupperAndSet writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SupperAndSet app + its autostart launcher.
COPY supperandset.py /opt/supperandset/supperandset.py
COPY start-supperandset.sh /opt/supperandset/start-supperandset.sh
RUN chmod +x /opt/supperandset/start-supperandset.sh

WORKDIR /app
