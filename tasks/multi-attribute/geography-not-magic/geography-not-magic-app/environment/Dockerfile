# syntax=docker/dockerfile:1.7
#
# PassesLearningFestival OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the PassesLearningFestival native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book day passes", PassesLearningFestival writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The PassesLearningFestival app + its autostart launcher.
COPY passeslearningfestival.py /opt/passeslearningfestival/passeslearningfestival.py
COPY start-passeslearningfestival.sh /opt/passeslearningfestival/start-passeslearningfestival.sh
RUN chmod +x /opt/passeslearningfestival/start-passeslearningfestival.sh

WORKDIR /app
