# syntax=docker/dockerfile:1.7
#
# CareerPath OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the CareerPath native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, CareerPath writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The CareerPath app + its autostart launcher.
COPY careerpath.py /opt/careerpath/careerpath.py
COPY start-careerpath.sh /opt/careerpath/start-careerpath.sh
RUN chmod +x /opt/careerpath/start-careerpath.sh

WORKDIR /app
