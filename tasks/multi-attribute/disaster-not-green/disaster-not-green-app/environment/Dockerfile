# syntax=docker/dockerfile:1.7
#
# TicketsSunday OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the TicketsSunday native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book tickets", TicketsSunday writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The TicketsSunday app + its autostart launcher.
COPY ticketssunday.py /opt/ticketssunday/ticketssunday.py
COPY start-ticketssunday.sh /opt/ticketssunday/start-ticketssunday.sh
RUN chmod +x /opt/ticketssunday/start-ticketssunday.sh

WORKDIR /app
