# syntax=docker/dockerfile:1.7
#
# LearningSaturdaysLibrary OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the LearningSaturdaysLibrary native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", LearningSaturdaysLibrary writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The LearningSaturdaysLibrary app + its autostart launcher.
COPY learningsaturdayslibrary.py /opt/learningsaturdayslibrary/learningsaturdayslibrary.py
COPY start-learningsaturdayslibrary.sh /opt/learningsaturdayslibrary/start-learningsaturdayslibrary.sh
RUN chmod +x /opt/learningsaturdayslibrary/start-learningsaturdayslibrary.sh

WORKDIR /app
