# syntax=docker/dockerfile:1.7
#
# PlateAndPicture OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the PlateAndPicture native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", PlateAndPicture writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The PlateAndPicture app + its autostart launcher.
COPY plateandpicture.py /opt/plateandpicture/plateandpicture.py
COPY start-plateandpicture.sh /opt/plateandpicture/start-plateandpicture.sh
RUN chmod +x /opt/plateandpicture/start-plateandpicture.sh

WORKDIR /app
