# syntax=docker/dockerfile:1.7
#
# SourceRack OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SourceRack native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Set sources", SourceRack writes /app/output/setup.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SourceRack app + its autostart launcher.
COPY sourcerack.py /opt/sourcerack/sourcerack.py
COPY start-sourcerack.sh /opt/sourcerack/start-sourcerack.sh
RUN chmod +x /opt/sourcerack/start-sourcerack.sh

WORKDIR /app
