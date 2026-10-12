# syntax=docker/dockerfile:1.7
#
# NookFit OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the NookFit native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Fit nook", NookFit writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The NookFit app + its autostart launcher.
COPY nookfit.py /opt/nookfit/nookfit.py
COPY start-nookfit.sh /opt/nookfit/start-nookfit.sh
RUN chmod +x /opt/nookfit/start-nookfit.sh

WORKDIR /app
