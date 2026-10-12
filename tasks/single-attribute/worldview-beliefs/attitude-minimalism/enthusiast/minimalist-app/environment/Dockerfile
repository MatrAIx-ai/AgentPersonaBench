# syntax=docker/dockerfile:1.7
#
# CartPop OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the CartPop native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user places an order, CartPop writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The CartPop app + its autostart launcher.
COPY cartpop.py /opt/cartpop/cartpop.py
COPY start-cartpop.sh /opt/cartpop/start-cartpop.sh
RUN chmod +x /opt/cartpop/start-cartpop.sh

WORKDIR /app
