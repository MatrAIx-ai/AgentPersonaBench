# syntax=docker/dockerfile:1.7
#
# NightsRooftop OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the NightsRooftop native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book nights", NightsRooftop writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The NightsRooftop app + its autostart launcher.
COPY nightsrooftop.py /opt/nightsrooftop/nightsrooftop.py
COPY start-nightsrooftop.sh /opt/nightsrooftop/start-nightsrooftop.sh
RUN chmod +x /opt/nightsrooftop/start-nightsrooftop.sh

WORKDIR /app
