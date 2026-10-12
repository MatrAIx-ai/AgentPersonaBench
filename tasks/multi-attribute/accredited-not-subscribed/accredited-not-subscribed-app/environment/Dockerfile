# syntax=docker/dockerfile:1.7
#
# CourseTermThree OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the CourseTermThree native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Enrol", CourseTermThree writes /app/output/enrolments.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The CourseTermThree app + its autostart launcher.
COPY coursetermthree.py /opt/coursetermthree/coursetermthree.py
COPY start-coursetermthree.sh /opt/coursetermthree/start-coursetermthree.sh
RUN chmod +x /opt/coursetermthree/start-coursetermthree.sh

WORKDIR /app
