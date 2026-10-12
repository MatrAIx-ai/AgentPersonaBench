# syntax=docker/dockerfile:1.7
#
# ClassPicker OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ClassPicker native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Enrol", ClassPicker writes /app/output/enrolments.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ClassPicker app + its autostart launcher.
COPY classpicker.py /opt/classpicker/classpicker.py
COPY start-classpicker.sh /opt/classpicker/start-classpicker.sh
RUN chmod +x /opt/classpicker/start-classpicker.sh

WORKDIR /app
