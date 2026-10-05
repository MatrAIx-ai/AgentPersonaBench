# syntax=docker/dockerfile:1.7
#
# SkillPath OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SkillPath native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# persona confirms enrollment, SkillPath writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SkillPath app + its autostart launcher.
COPY skillpath.py /opt/skillpath/skillpath.py
COPY start-skillpath.sh /opt/skillpath/start-skillpath.sh
RUN chmod +x /opt/skillpath/start-skillpath.sh

WORKDIR /app
