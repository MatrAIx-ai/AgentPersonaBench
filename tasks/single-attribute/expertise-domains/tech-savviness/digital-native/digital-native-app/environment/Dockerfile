# syntax=docker/dockerfile:1.7
#
# TaskFlow OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the TaskFlow native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, TaskFlow writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The TaskFlow app + its autostart launcher.
COPY taskflow.py /opt/taskflow/taskflow.py
COPY start-taskflow.sh /opt/taskflow/start-taskflow.sh
RUN chmod +x /opt/taskflow/start-taskflow.sh

WORKDIR /app
