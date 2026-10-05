# syntax=docker/dockerfile:1.7
#
# SwapDesk OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SwapDesk native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book sessions", SwapDesk writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SwapDesk app + its autostart launcher.
COPY swapdesk.py /opt/swapdesk/swapdesk.py
COPY start-swapdesk.sh /opt/swapdesk/start-swapdesk.sh
RUN chmod +x /opt/swapdesk/start-swapdesk.sh

WORKDIR /app
