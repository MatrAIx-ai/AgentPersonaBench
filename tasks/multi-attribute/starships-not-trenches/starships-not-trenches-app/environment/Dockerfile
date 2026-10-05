# syntax=docker/dockerfile:1.7
#
# ProjectorAndPage OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ProjectorAndPage native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", ProjectorAndPage writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ProjectorAndPage app + its autostart launcher.
COPY projectorandpage.py /opt/projectorandpage/projectorandpage.py
COPY start-projectorandpage.sh /opt/projectorandpage/start-projectorandpage.sh
RUN chmod +x /opt/projectorandpage/start-projectorandpage.sh

WORKDIR /app
