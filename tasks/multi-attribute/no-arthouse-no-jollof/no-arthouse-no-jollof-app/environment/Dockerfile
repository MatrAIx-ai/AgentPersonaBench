# syntax=docker/dockerfile:1.7
#
# SupperClubScreen OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SupperClubScreen native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", SupperClubScreen writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SupperClubScreen app + its autostart launcher.
COPY supperclubscreen.py /opt/supperclubscreen/supperclubscreen.py
COPY start-supperclubscreen.sh /opt/supperclubscreen/start-supperclubscreen.sh
RUN chmod +x /opt/supperclubscreen/start-supperclubscreen.sh

WORKDIR /app
