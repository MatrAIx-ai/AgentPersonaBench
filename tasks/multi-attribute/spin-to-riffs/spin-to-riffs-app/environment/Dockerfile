# syntax=docker/dockerfile:1.7
#
# ClassCredits OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ClassCredits native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book classes", ClassCredits writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ClassCredits app + its autostart launcher.
COPY classcredits.py /opt/classcredits/classcredits.py
COPY start-classcredits.sh /opt/classcredits/start-classcredits.sh
RUN chmod +x /opt/classcredits/start-classcredits.sh

WORKDIR /app
