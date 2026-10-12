# syntax=docker/dockerfile:1.7
#
# BookshelfAndBeach OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the BookshelfAndBeach native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book meetups", BookshelfAndBeach writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The BookshelfAndBeach app + its autostart launcher.
COPY bookshelfandbeach.py /opt/bookshelfandbeach/bookshelfandbeach.py
COPY start-bookshelfandbeach.sh /opt/bookshelfandbeach/start-bookshelfandbeach.sh
RUN chmod +x /opt/bookshelfandbeach/start-bookshelfandbeach.sh

WORKDIR /app
