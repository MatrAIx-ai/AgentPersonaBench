# syntax=docker/dockerfile:1.7
#
# MealMate OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the MealMate native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user places an order, MealMate writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The MealMate app + its autostart launcher.
COPY mealmate.py /opt/mealmate/mealmate.py
COPY start-mealmate.sh /opt/mealmate/start-mealmate.sh
RUN chmod +x /opt/mealmate/start-mealmate.sh

WORKDIR /app
