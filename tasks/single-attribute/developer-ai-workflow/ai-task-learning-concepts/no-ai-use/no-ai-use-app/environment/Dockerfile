# syntax=docker/dockerfile:1.7
#
# SkillHub OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SkillHub native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# persona confirms enrollment, SkillHub writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SkillHub app + its autostart launcher.
COPY skillhub.py /opt/skillhub/skillhub.py
COPY start-skillhub.sh /opt/skillhub/start-skillhub.sh
RUN chmod +x /opt/skillhub/start-skillhub.sh

WORKDIR /app
