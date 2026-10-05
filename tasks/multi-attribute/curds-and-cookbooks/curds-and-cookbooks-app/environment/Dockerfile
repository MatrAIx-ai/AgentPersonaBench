# syntax=docker/dockerfile:1.7
#
# KitchenCredit OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the KitchenCredit native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Enrol", KitchenCredit writes /app/output/enrolments.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The KitchenCredit app + its autostart launcher.
COPY kitchencredit.py /opt/kitchencredit/kitchencredit.py
COPY start-kitchencredit.sh /opt/kitchencredit/start-kitchencredit.sh
RUN chmod +x /opt/kitchencredit/start-kitchencredit.sh

WORKDIR /app
