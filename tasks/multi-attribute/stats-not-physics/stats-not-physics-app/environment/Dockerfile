# syntax=docker/dockerfile:1.7
#
# LecturesTuesday OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the LecturesTuesday native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Tuesdays", LecturesTuesday writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The LecturesTuesday app + its autostart launcher.
COPY lecturestuesday.py /opt/lecturestuesday/lecturestuesday.py
COPY start-lecturestuesday.sh /opt/lecturestuesday/start-lecturestuesday.sh
RUN chmod +x /opt/lecturestuesday/start-lecturestuesday.sh

WORKDIR /app
