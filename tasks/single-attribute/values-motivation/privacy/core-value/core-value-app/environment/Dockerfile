# syntax=docker/dockerfile:1.7
#
# NimbusSetup OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool
# + scrot) PLUS Python Tkinter and the NimbusSetup native GUI app baked in. The
# CUA agent (persona-computer-1) drives it by screenshot + coordinate click; when
# the user finishes setup, NimbusSetup writes /app/output/setup.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The NimbusSetup app + its autostart launcher.
COPY nimbussetup.py /opt/nimbussetup/nimbussetup.py
COPY start-nimbussetup.sh /opt/nimbussetup/start-nimbussetup.sh
RUN chmod +x /opt/nimbussetup/start-nimbussetup.sh

WORKDIR /app
