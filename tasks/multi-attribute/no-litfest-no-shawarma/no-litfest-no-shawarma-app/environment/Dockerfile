# syntax=docker/dockerfile:1.7
#
# SupperSessionThursday OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SupperSessionThursday native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Thursdays", SupperSessionThursday writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SupperSessionThursday app + its autostart launcher.
COPY suppersessionthursday.py /opt/suppersessionthursday/suppersessionthursday.py
COPY start-suppersessionthursday.sh /opt/suppersessionthursday/start-suppersessionthursday.sh
RUN chmod +x /opt/suppersessionthursday/start-suppersessionthursday.sh

WORKDIR /app
